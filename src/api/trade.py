"""Trade / positions HTTP routes."""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from py_clob_client_v2 import OrderArgs, OrderType
from py_clob_client_v2.order_builder.constants import BUY, SELL
from sqlalchemy.orm import Session

from src.api.client import get_clob_client, run_sync
from src.config import settings
from src.database.db import get_db
from src.database.models import Position
from src.services.orders import (
    best_bid_price,
    cancel_order,
    extract_order_id,
    get_neg_risk_options,
    is_resolved_error,
    market_sell,
    parse_order_payload,
    validate_limit_price,
)
from src.workers.monitor import setup_order_lifecycle, token_sl_radar

router = APIRouter(tags=["trade"])
logger = logging.getLogger(__name__)

# Singleton guard: at most one SL radar task per token_id
active_token_radars: set[str] = set()

# Polymarket CLOB limit prices must stay inside the tradable tick band.
MIN_LIMIT_PRICE = 0.01
MAX_LIMIT_PRICE = 0.99


class TradeRequest(BaseModel):
    token_id: str
    condition_id: str
    price: float = Field(..., description="Limit price in [0.01, 0.99]")
    side: str
    bankroll: float
    risk_percent: float = 100
    is_custom_limit: bool = False
    take_profit_price: float | None = None
    stop_loss_price: float | None = None
    strategy: str = "custom"

    @field_validator("price")
    @classmethod
    def price_in_band(cls, value: float) -> float:
        validate_limit_price(value)
        return value


@router.post("/order")
async def place_order(
    req: TradeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    safe_price = round(float(req.price), 2)
    # Defense in depth: reject out-of-band prices even if model validation is bypassed.
    try:
        validate_limit_price(safe_price)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    side_const = BUY if req.side.upper() == "BUY" else SELL
    strategy = req.strategy

    if req.bankroll < 5.00:
        return {"success": False, "error": f"Банкролл ({req.bankroll}$) меньше $5."}

    target_invest = req.bankroll * (req.risk_percent / 100)
    actual_invest = min(req.bankroll, max(5.00, target_invest))
    safe_size = round(actual_invest / safe_price, 2)

    try:
        client = get_clob_client()
        options = await get_neg_risk_options(req.token_id)

        main_args = OrderArgs(
            price=safe_price,
            size=safe_size,
            side=side_const,
            token_id=str(req.token_id),
            builder_code=settings.builder_code,
        )
        resp = await run_sync(
            client.create_and_post_order,
            order_args=main_args,
            options=options,
            order_type=OrderType.GTC,
        )

        main_order_id = extract_order_id(resp)
        if not main_order_id:
            err_msg = resp.get("errorMsg", str(resp)) if isinstance(resp, dict) else str(resp)
            return {"success": False, "error": err_msg}

        safe_tp = round(float(req.take_profit_price), 2) if req.take_profit_price else None
        sl_price = (
            round(float(req.stop_loss_price), 2)
            if req.stop_loss_price is not None
            else max(0.01, safe_price - 0.12)
        )

        token_id = str(req.token_id)

        try:
            # Always PENDING until setup_order_lifecycle confirms fill → OPEN.
            # Prevents the token radar from SL-evaluating unfilled entries.
            db.add(
                Position(
                    order_id=main_order_id,
                    token_id=token_id,
                    condition_id=req.condition_id,
                    strategy=strategy,
                    entry_price=safe_price,
                    size=safe_size,
                    tp_price=safe_tp,
                    sl_trigger_price=sl_price,
                    status="PENDING",
                )
            )
            db.commit()
        except Exception as exc:
            db.rollback()
            logger.warning("DB insert failed for %s: %s", main_order_id, exc)

        # Phase 1–2: per-order REST lifecycle (fill wait + TP placement)
        background_tasks.add_task(
            setup_order_lifecycle,
            order_id=main_order_id,
            original_size=safe_size,
            token_id=token_id,
            tp_price=safe_tp,
            sl_price=sl_price,
            options=options,
            strategy=strategy,
        )

        # Phase 3: singleton WS radar per token (shared by all orders on that token)
        if token_id not in active_token_radars:
            active_token_radars.add(token_id)
            background_tasks.add_task(token_sl_radar, token_id)
            logger.info("[Trade] started SL radar for token %s", token_id)
        else:
            logger.info("[Trade] SL radar already running for token %s", token_id)

        return {"success": True, "order_id": main_order_id}

    except Exception as exc:
        logger.exception("place_order failed")
        return {"success": False, "error": str(exc)}


@router.post("/panic_sell/{order_id}")
async def panic_sell_position(order_id: str, db: Session = Depends(get_db)):
    try:
        pos = db.query(Position).filter(Position.order_id == order_id).first()
        if not pos:
            return {"success": False, "error": "Позиция не найдена в базе данных"}

        client = get_clob_client()
        token_id = pos.token_id
        size_to_sell = pos.size

        try:
            order_info = await run_sync(client.get_order, order_id)
            order_data = parse_order_payload(order_info)

            if order_data:
                matched = float(order_data.get("size_matched", 0) or 0)
                status = order_data.get("status")

                if matched == 0 and status in ("LIVE", "OPEN"):
                    await cancel_order(order_id)
                    pos.status = "CANCELED"
                    db.commit()
                    return {"success": True, "message": "Отменено (покупок не было)."}
                if matched > 0:
                    size_to_sell = matched
        except Exception as exc:
            if is_resolved_error(str(exc)):
                pos.status = "RESOLVED"
                pos.exit_price = 1.0
                db.commit()
                return {"success": True, "message": "Очищено (токен сгорел/рынок закрыт)."}

        try:
            await run_sync(client.cancel_market_orders, asset_id=str(token_id))
        except Exception:
            pass

        await asyncio.sleep(1.0)

        try:
            options = await get_neg_risk_options(token_id)
            resp = await market_sell(token_id, size_to_sell, options)

            if resp and extract_order_id(resp):
                bid = await best_bid_price(token_id)
                pos.status = "PANIC_SELL"
                pos.exit_price = bid
                db.commit()
                return {"success": True, "message": "Сброшено по рынку!"}

            if resp and is_resolved_error(str(resp)):
                pos.status = "RESOLVED"
                pos.exit_price = 1.0
                db.commit()
                return {"success": True, "message": "Очищено (рынок завершен)."}

        except Exception as exc:
            if is_resolved_error(str(exc)):
                pos.status = "RESOLVED"
                pos.exit_price = 1.0
                db.commit()
                return {"success": True, "message": "Очищено (продано вручную)."}
            return {"success": False, "error": f"Ошибка Polymarket: {exc}"}

        return {"success": False, "error": "Неизвестная ошибка при отправке ордера"}

    except Exception as exc:
        logger.exception("panic_sell failed")
        return {"success": False, "error": f"Внутренняя ошибка сервера: {exc}"}


@router.get("/positions")
async def get_open_positions(db: Session = Depends(get_db)):
    try:
        positions = (
            db.query(Position)
            .filter(Position.status.in_(["OPEN", "PENDING"]))
            .all()
        )
        return {
            "success": True,
            "positions": [
                {
                    "order_id": p.order_id,
                    "token_id": p.token_id,
                    "entry_price": p.entry_price,
                    "size": p.size,
                    "tp_price": p.tp_price,
                    "sl_trigger_price": p.sl_trigger_price,
                    "strategy": p.strategy,
                    "status": p.status,
                }
                for p in positions
            ],
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}
