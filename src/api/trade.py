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
from src.core.order_logger import order_audit
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

# Known strategy identifiers (presets + custom)
PRESET_STRATEGIES = frozenset(
    {
        "fix",
        "draft_win",
        "short_range",
        "high_range",
    }
)


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

    @field_validator("strategy")
    @classmethod
    def strategy_known(cls, value: str) -> str:
        s = (value or "custom").strip().lower()
        # Allow custom + presets + legacy strings still used by older clients
        allowed = PRESET_STRATEGIES | {"custom", "4c", "8c", "match"}
        if s not in allowed:
            # Soft-accept unknown strategies as custom labels for forward compat
            return s
        return s


def resolve_strategy_levels(
    strategy: str,
    entry: float,
    req_tp: float | None,
    req_sl: float | None,
) -> tuple[float | None, float | None]:
    """
    Compute TP / SL for known presets on the backend (all values rounded to 2dp).

    Presets ignore client-supplied TP/SL to avoid floating-point drift.
    Custom / legacy strategies honour request fields (with default SL fallback).
    """
    entry = round(float(entry), 2)
    strategy = (strategy or "custom").lower()

    if strategy == "fix":
        # req_tp is a relative offset in dollars (e.g. 0.12 = +12¢), not an absolute price.
        # SL completely disabled.
        if req_tp is None:
            return None, None
        offset = float(req_tp)
        if offset <= 0:
            return None, None
        tp = round(entry + offset, 2)
        # Hard ceiling: never place TP at or above 1.0
        if tp >= 1.0:
            tp = MAX_LIMIT_PRICE
        else:
            tp = min(MAX_LIMIT_PRICE, tp)
        return tp, None

    if strategy == "draft_win":
        return None, None

    if strategy == "short_range":
        return round(entry + 0.04, 2), round(entry - 0.06, 2)

    if strategy == "high_range":
        return round(entry + 0.06, 2), round(entry - 0.08, 2)

    # custom + legacy (4c / 8c / match / …)
    tp = round(float(req_tp), 2) if req_tp is not None else None
    if req_sl is not None:
        sl = round(float(req_sl), 2)
    else:
        sl = max(0.01, round(entry - 0.12, 2))
    return tp, sl


def _clamp_price(price: float | None) -> float | None:
    if price is None:
        return None
    return max(MIN_LIMIT_PRICE, min(MAX_LIMIT_PRICE, round(float(price), 2)))


def _split_tp_ids(tp_order_id: str | None) -> list[str]:
    """Parse comma-separated tp_order_id field into individual ids."""
    if not tp_order_id:
        return []
    return [part.strip() for part in str(tp_order_id).split(",") if part.strip()]


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
    strategy = (req.strategy or "custom").lower()

    if req.bankroll < 5.00:
        return {"success": False, "error": f"Банкролл ({req.bankroll}$) меньше $5."}

    target_invest = req.bankroll * (req.risk_percent / 100)
    actual_invest = min(req.bankroll, max(5.00, target_invest))

    if actual_invest <= 0:
        return {"success": False, "error": "Размер позиции должен быть > 0."}

    safe_size = round(actual_invest / safe_price, 2)

    # Backend-owned TP/SL for presets (rounded to 2dp)
    # Fix: take_profit_price is a relative +¢ offset in dollars (e.g. 0.12 = +12¢)
    raw_tp, raw_sl = resolve_strategy_levels(
        strategy,
        safe_price,
        req.take_profit_price,
        req.stop_loss_price,
    )
    safe_tp = _clamp_price(raw_tp)
    # fix requires a manual relative TP offset from the UI
    if strategy == "fix" and safe_tp is None:
        return {
            "success": False,
            "error": "Fix strategy requires a Take Profit offset (+¢).",
        }
    # SL may be below 0.01 after subtract — clamp to tradable floor when set
    # fix / draft_win: SL is None → radar ignores
    if raw_sl is not None:
        sl_price = max(0.01, round(float(raw_sl), 2))
    else:
        sl_price = None

    order_audit.info(
        "INTENT place_order | strategy=%s token_id=%s size=%s price=%s "
        "tp=%s sl=%s bankroll=%s invest=%s",
        strategy,
        req.token_id,
        safe_size,
        safe_price,
        safe_tp,
        sl_price,
        req.bankroll,
        actual_invest,
    )

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
            order_audit.error(
                "ERROR place_order no order_id | strategy=%s token_id=%s size=%s "
                "price=%s detail=%s",
                strategy,
                req.token_id,
                safe_size,
                safe_price,
                err_msg,
            )
            return {"success": False, "error": err_msg}

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
            entry_price=safe_price,
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
        order_audit.error(
            "ERROR place_order exception | strategy=%s token_id=%s size=%s "
            "price=%s error=%s",
            strategy,
            req.token_id,
            safe_size,
            safe_price,
            exc,
        )
        return {"success": False, "error": str(exc)}


@router.post("/flatten/{token_id}")
async def flatten_token(token_id: str, db: Session = Depends(get_db)):
    """
    Panic-flatten all OPEN positions for a token (F10).

    - Only status == OPEN (executed buys); PENDING limit entries are ignored.
    - Cancels associated TP order(s) to unfreeze balance.
    - Market-sells the summed size once, marks positions PANIC_SELL.
    """
    token_id = str(token_id)
    try:
        open_positions = (
            db.query(Position)
            .filter(
                Position.token_id == token_id,
                Position.status == "OPEN",
            )
            .all()
        )

        if not open_positions:
            return {
                "success": False,
                "error": "Нет OPEN позиций по этому токену",
            }

        total_size = round(sum(float(p.size or 0) for p in open_positions), 2)
        order_ids = [p.order_id for p in open_positions]

        order_audit.info(
            "FLATTEN start | token_id=%s positions=%s total_size=%s order_ids=%s",
            token_id,
            len(open_positions),
            total_size,
            ",".join(order_ids),
        )

        # Cancel all TP legs (supports comma-separated dual TPs)
        for pos in open_positions:
            for tp_id in _split_tp_ids(getattr(pos, "tp_order_id", None)):
                try:
                    logger.info(
                        "[Flatten] cancel TP %s for order %s", tp_id, pos.order_id
                    )
                    await cancel_order(tp_id)
                except Exception as exc:
                    logger.warning(
                        "[Flatten] TP cancel failed %s: %s", tp_id, exc
                    )

        await asyncio.sleep(0.5)

        if total_size <= 0:
            for pos in open_positions:
                pos.status = "PANIC_SELL"
            db.commit()
            order_audit.info(
                "FLATTEN done (zero size) | token_id=%s", token_id
            )
            return {"success": True, "message": "Позиции закрыты (size=0)."}

        try:
            options = await get_neg_risk_options(token_id)
            resp = await market_sell(token_id, total_size, options)

            if resp and extract_order_id(resp):
                bid = await best_bid_price(token_id)
                for pos in open_positions:
                    pos.status = "PANIC_SELL"
                    pos.exit_price = bid
                db.commit()
                order_audit.info(
                    "FLATTEN executed | token_id=%s total_size=%s exit=%s "
                    "order_ids=%s",
                    token_id,
                    total_size,
                    bid,
                    ",".join(order_ids),
                )
                return {
                    "success": True,
                    "message": f"Flatten: продано {total_size} @ market",
                    "size": total_size,
                }

            if resp and is_resolved_error(str(resp)):
                for pos in open_positions:
                    pos.status = "RESOLVED"
                    pos.exit_price = 1.0
                db.commit()
                return {"success": True, "message": "Очищено (рынок завершен)."}

            err = str(resp) if resp else "empty response"
            order_audit.error(
                "FLATTEN market_sell failed | token_id=%s size=%s detail=%s",
                token_id,
                total_size,
                err,
            )
            return {"success": False, "error": f"Ошибка market sell: {err}"}

        except Exception as exc:
            if is_resolved_error(str(exc)):
                for pos in open_positions:
                    pos.status = "RESOLVED"
                    pos.exit_price = 1.0
                db.commit()
                return {"success": True, "message": "Очищено (рынок завершен)."}
            order_audit.error(
                "FLATTEN exception | token_id=%s size=%s error=%s",
                token_id,
                total_size,
                exc,
            )
            return {"success": False, "error": f"Ошибка Polymarket: {exc}"}

    except Exception as exc:
        logger.exception("flatten failed")
        order_audit.error(
            "FLATTEN internal error | token_id=%s error=%s", token_id, exc
        )
        return {"success": False, "error": f"Внутренняя ошибка сервера: {exc}"}


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
            for tp_id in _split_tp_ids(getattr(pos, "tp_order_id", None)):
                logger.info("Отменяем Тейк-Профит %s для разблокировки баланса", tp_id)
                await cancel_order(tp_id)
            if getattr(pos, "tp_order_id", None):
                await asyncio.sleep(0.5)

        except Exception as exc:
            logger.warning("Не удалось отменить ТП перед паникой: %s", exc)

        await asyncio.sleep(1.0)

        try:
            options = await get_neg_risk_options(token_id)
            resp = await market_sell(token_id, size_to_sell, options)

            if resp and extract_order_id(resp):
                bid = await best_bid_price(token_id)
                pos.status = "PANIC_SELL"
                pos.exit_price = bid
                db.commit()
                order_audit.info(f"PANIC SELL EXECUTED | order_id={order_id} size_dumped={size_to_sell} exit_price={bid}")
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


class ResolveRequest(BaseModel):
    """Manual resolve for stuck/ended markets — feeds PnL/stats."""

    exit_price: float = Field(..., description="Exit price in [0.0, 1.0]")

    @field_validator("exit_price")
    @classmethod
    def exit_in_band(cls, value: float) -> float:
        v = float(value)
        if v < 0.0 or v > 1.0:
            raise ValueError("exit_price must be between 0.0 and 1.0")
        return round(v, 4)


@router.post("/positions/{order_id}/resolve")
async def resolve_position(
    order_id: str,
    req: ResolveRequest,
    db: Session = Depends(get_db),
):
    """
    Manually mark a stuck OPEN/PENDING position as RESOLVED with a given exit_price.

    Used for ended markets where auto-resolve failed (Win 100¢ / Loss 0¢ / Drop @ entry).
    Cancels any live TP legs so balance is unfrozen, then updates DB for stats/PnL.
    """
    try:
        pos = db.query(Position).filter(Position.order_id == order_id).first()
        if not pos:
            return {"success": False, "error": "Позиция не найдена в базе данных"}

        if pos.status not in ("OPEN", "PENDING"):
            return {
                "success": False,
                "error": f"Позиция уже закрыта (status={pos.status})",
            }

        # Cancel live TP legs if any (best-effort)
        for tp_id in _split_tp_ids(getattr(pos, "tp_order_id", None)):
            try:
                await cancel_order(tp_id)
            except Exception as exc:
                logger.warning(
                    "[Resolve] TP cancel failed %s for %s: %s", tp_id, order_id, exc
                )

        # Best-effort cancel unfilled entry if still PENDING
        if pos.status == "PENDING":
            try:
                await cancel_order(order_id)
            except Exception as exc:
                logger.warning(
                    "[Resolve] entry cancel failed for %s: %s", order_id, exc
                )

        pos.status = "RESOLVED"
        pos.exit_price = float(req.exit_price)
        db.commit()

        order_audit.info(
            "MANUAL RESOLVE | order_id=%s exit_price=%s strategy=%s",
            order_id,
            req.exit_price,
            pos.strategy,
        )
        return {
            "success": True,
            "message": f"Resolved @ {req.exit_price}",
            "order_id": order_id,
            "exit_price": req.exit_price,
            "status": "RESOLVED",
        }
    except Exception as exc:
        logger.exception("resolve_position failed")
        db.rollback()
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
