"""Background position workers: REST lifecycle + singleton SL radar per token."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from contextlib import contextmanager
from typing import Any

import websockets
from py_clob_client_v2 import OrderArgs, OrderType, PartialCreateOrderOptions
from py_clob_client_v2.order_builder.constants import SELL

from src.api.client import get_clob_client, run_sync
from src.config import settings
from src.core.order_logger import order_audit
from src.database.db import SessionLocal
from src.database.models import Position
from src.services.orders import (
    cancel_order,
    get_neg_risk_options,
    market_sell,
    parse_order_payload,
)

logger = logging.getLogger(__name__)

# Avoid routing WS through HTTP proxy
os.environ.setdefault("no_proxy", "ws-subscriptions-clob.polymarket.com")

# draft_early: SL disabled for this many seconds after first radar sight
DRAFT_EARLY_SL_DELAY_SEC = 960  # 16 minutes
# Consecutive ticks with best_bid <= SL before market sell
SL_TICK_CONFIRMATIONS = 3


@contextmanager
def db_session():
    """Short-lived session: commit on success, always close (no locks in WS loop)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _update_position(order_id: str, **fields: Any) -> None:
    with db_session() as db:
        pos = db.query(Position).filter(Position.order_id == order_id).first()
        if not pos:
            return
        for key, value in fields.items():
            setattr(pos, key, value)


def _get_position_fields(order_id: str) -> dict[str, Any]:
    with db_session() as db:
        pos = db.query(Position).filter(Position.order_id == order_id).first()
        if not pos:
            return {}
        return {
            "entry_price": float(pos.entry_price) if pos.entry_price is not None else None,
            "tp_order_id": pos.tp_order_id,
            "status": pos.status,
        }


def _get_position_entry(order_id: str) -> float | None:
    fields = _get_position_fields(order_id)
    entry = fields.get("entry_price")
    return float(entry) if entry is not None else None


def _get_open_sl_positions(token_id: str) -> list[dict[str, Any]]:
    """Snapshot open SL positions; values are plain Python (session closed after)."""
    with db_session() as db:
        rows = (
            db.query(Position)
            .filter(
                Position.token_id == token_id,
                Position.status == "OPEN",
                Position.sl_trigger_price.isnot(None),
            )
            .all()
        )
        return [
            {
                "order_id": p.order_id,
                "sl_trigger_price": float(p.sl_trigger_price),
                "size": float(p.size),
                "strategy": p.strategy or "custom",
                "tp_order_id": p.tp_order_id,
            }
            for p in rows
        ]


def _get_open_tp_positions(token_id: str) -> list[dict[str, Any]]:
    """Snapshot open positions that have a live TP order id."""
    with db_session() as db:
        rows = (
            db.query(Position)
            .filter(
                Position.token_id == token_id,
                Position.status == "OPEN",
                Position.tp_order_id.isnot(None),
            )
            .all()
        )
        return [
            {"order_id": p.order_id, "tp_order_id": p.tp_order_id}
            for p in rows
        ]


def _split_tp_ids(tp_order_id: str | None) -> list[str]:
    if not tp_order_id:
        return []
    return [part.strip() for part in str(tp_order_id).split(",") if part.strip()]


def _apply_book_snapshot(bids: dict, asks: dict, payload: dict) -> None:
    bids.clear()
    asks.clear()
    for b in payload.get("bids", []) or []:
        bids[float(b["price"])] = float(b["size"])
    for a in payload.get("asks", []) or []:
        asks[float(a["price"])] = float(a["size"])


def _apply_price_change(bids: dict, asks: dict, ev: dict) -> None:
    changes = ev.get("changes") or []
    if not changes:
        for b in ev.get("bids", []) or []:
            p, s = float(b["price"]), float(b["size"])
            if s == 0:
                bids.pop(p, None)
            else:
                bids[p] = s
        for a in ev.get("asks", []) or []:
            p, s = float(a["price"]), float(a["size"])
            if s == 0:
                asks.pop(p, None)
            else:
                asks[p] = s
        return

    for ch in changes:
        p, s = float(ch["price"]), float(ch["size"])
        side = ch.get("side")
        book = bids if side == "BUY" else asks if side == "SELL" else None
        if book is None:
            continue
        if s == 0:
            book.pop(p, None)
        else:
            book[p] = s


async def _wait_for_fill(
    client: Any,
    order_id: str,
    original_size: float,
    max_polls: int = 86400,
    poll_interval: float = 5.0,
    strategy: str = "custom",
    token_id: str = "",
) -> float | None:
    """Return filled size, or None if order cancelled/expired empty."""
    for _ in range(max_polls):
        try:
            order_info = await run_sync(client.get_order, order_id)
            order_data = parse_order_payload(order_info) or {}
            status = order_data.get("status", "")
            size_matched = order_data.get("size_matched")

            if status in ("MATCHED", "FILLED"):
                size = (
                    int(float(size_matched) * 100) / 100.0
                    if size_matched and float(size_matched) > 0
                    else original_size
                )
                size = round(float(size), 2)
                logger.info("[Lifecycle] filled %s size=%s", order_id, size)
                _update_position(order_id, status="OPEN", size=size)
                order_audit.info(
                    "FILLED/OPEN | order_id=%s token_id=%s size=%s strategy=%s",
                    order_id,
                    token_id,
                    size,
                    strategy,
                )
                return size

            if status in ("CANCELED", "EXPIRED"):
                if size_matched and float(size_matched) > 0:
                    size = round(int(float(size_matched) * 100) / 100.0, 2)
                    logger.warning("[Lifecycle] partial fill on cancel: %s", size)
                    _update_position(order_id, status="OPEN", size=size)
                    order_audit.info(
                        "FILLED/OPEN (partial) | order_id=%s token_id=%s size=%s strategy=%s",
                        order_id,
                        token_id,
                        size,
                        strategy,
                    )
                    return size
                logger.warning("[Lifecycle] order cancelled empty: %s", order_id)
                _update_position(order_id, status="CANCELED")
                return None
        except Exception:
            pass
        await asyncio.sleep(poll_interval)
    return None


async def _place_take_profit(
    client: Any,
    token_id: str,
    size: float,
    tp_price: float,
    options: PartialCreateOrderOptions,
    attempts: int = 10,
) -> str | None:
    size = round(float(size), 2)
    tp_price = round(float(tp_price), 2)
    last_error = None
    
    for _ in range(attempts):
        try:
            args = OrderArgs(
                price=tp_price,
                size=size,
                side=SELL,
                token_id=token_id,
                builder_code=settings.builder_code,
            )
            resp = await run_sync(
                client.create_and_post_order,
                order_args=args,
                options=options,
                order_type=OrderType.GTC,
            )
            if resp and resp.get("success"):
                tp_id = resp.get("orderID")
                logger.info("[Lifecycle] TP placed: %s @ %s size=%s", tp_id, tp_price, size)
                return tp_id
            
            # Some responses omit success but still return orderID
            if isinstance(resp, dict):
                tp_id = resp.get("orderID") or resp.get("id")
                if tp_id:
                    logger.info("[Lifecycle] TP placed: %s @ %s size=%s", tp_id, tp_price, size)
                    return tp_id
                last_error = resp.get("errorMsg", str(resp))
        except Exception as exc:
            last_error = str(exc)
            
        await asyncio.sleep(2)
        
    order_audit.error(f"TP PLACEMENT FAILED | size={size} price={tp_price} error={last_error}")
    return None


async def _seed_order_book(client: Any, token_id: str, bids: dict, asks: dict) -> None:
    try:
        ob = await run_sync(client.get_order_book, token_id)
        if isinstance(ob, dict):
            _apply_book_snapshot(bids, asks, ob)
    except Exception:
        pass


async def _check_tp_status(client: Any, order_id: str, tp_order_id: str) -> bool:
    """
    Return True if position closed via TP fill or market resolve.

    Supports comma-separated dual TP ids (draft_early): closes only when
    every live TP leg is MATCHED/FILLED (or any is CANCELED/EXPIRED → RESOLVED).
    """
    tp_ids = _split_tp_ids(tp_order_id)
    if not tp_ids:
        return False

    try:
        statuses: list[str] = []
        exit_prices: list[float] = []

        for tid in tp_ids:
            tp_info = await run_sync(client.get_order, tid)
            tp_data = parse_order_payload(tp_info)
            if not isinstance(tp_data, dict):
                return False
            st = tp_data.get("status") or ""
            statuses.append(st)
            if st in ("MATCHED", "FILLED"):
                exit_prices.append(float(tp_data.get("price") or 0))
            if st in ("CANCELED", "EXPIRED"):
                logger.info("[Radar] TP cancelled (resolved) for %s (%s)", order_id, tid)
                _update_position(order_id, status="RESOLVED", exit_price=1.0)
                return True

        if all(s in ("MATCHED", "FILLED") for s in statuses):
            logger.info("[Radar] TP hit for %s (legs=%s)", order_id, len(tp_ids))
            exit_px = exit_prices[-1] if exit_prices else 0.0
            _update_position(
                order_id,
                status="CLOSED_TP",
                exit_price=exit_px,
            )
            return True
    except Exception:
        pass
    return False


async def _place_draft_early_tps(
    client: Any,
    order_id: str,
    token_id: str,
    actual_size: float,
    entry_price: float,
    options: PartialCreateOrderOptions,
    strategy: str,
) -> None:
    """
    draft_early: two sequential REST take-profits.
    """
    entry = round(float(entry_price), 2)
    size = round(float(actual_size), 2)
    
    if size < 10.0:
        logger.warning(f"[Lifecycle] Size {size} is too small to split. Placing single TP.")
        tp1_size = size
        tp2_size = 0.0
    else:
        tp1_size = round(size * 0.5, 2)
        tp2_size = round(size - tp1_size, 2)
    
    tp1_price = round(entry + 0.06, 2)
    tp2_price = round(entry + 0.12, 2)
    
    tp1_price = max(0.01, min(0.99, tp1_price))
    tp2_price = max(0.01, min(0.99, tp2_price))

    tp_ids: list[str] = []

    if tp1_size > 0:
        tp1_id = await _place_take_profit(client, token_id, tp1_size, tp1_price, options)
        if tp1_id:
            tp_ids.append(tp1_id)
            order_audit.info(
                "TP PLACED | order_id=%s token_id=%s tp_order_id=%s size=%s price=%s strategy=%s leg=1",
                order_id, token_id, tp1_id, tp1_size, tp1_price, strategy,
            )
        else:
            order_audit.error("TP1 FAILED | order_id=%s strategy=%s size=%s price=%s", order_id, strategy, tp1_size, tp1_price)

    if tp2_size > 0:
        tp2_id = await _place_take_profit(client, token_id, tp2_size, tp2_price, options)
        if tp2_id:
            tp_ids.append(tp2_id)
            order_audit.info(
                "TP PLACED | order_id=%s token_id=%s tp_order_id=%s size=%s price=%s strategy=%s leg=2",
                order_id, token_id, tp2_id, tp2_size, tp2_price, strategy,
            )
        else:
            order_audit.error("TP2 FAILED | order_id=%s strategy=%s size=%s price=%s", order_id, strategy, tp2_size, tp2_price)

    if tp_ids:
        _update_position(order_id, tp_order_id=",".join(tp_ids))
    else:
        order_audit.error("DRAFT_EARLY FATAL | No TP legs placed for %s", order_id)


async def setup_order_lifecycle(
    order_id: str,
    original_size: float,
    token_id: str,
    tp_price: float | None,
    sl_price: float | None,
    options: PartialCreateOrderOptions,
    strategy: str,
    entry_price: float | None = None,
) -> None:
    """
    REST-only lifecycle for a single order (Phase 1–2).

    Waits for fill, marks OPEN, places TP limit(s), stores tp_order_id, then exits.
    SL monitoring is owned by the singleton token_sl_radar for this token.
    """
    strategy = (strategy or "custom").lower()
    logger.info(
        "[Lifecycle] start %s strategy=%s sl=%s",
        order_id,
        strategy.upper(),
        sl_price,
    )
    client = get_clob_client()

    # Phase 1: wait for entry fill
    actual_size = await _wait_for_fill(
        client,
        order_id,
        original_size,
        strategy=strategy,
        token_id=token_id,
    )
    if not actual_size:
        _update_position(order_id, status="EXPIRED")
        return

    # Ensure SL trigger is persisted (radar reads it from DB)
    if sl_price is not None:
        _update_position(
            order_id,
            sl_trigger_price=max(0.01, round(float(sl_price), 2)),
        )

    # Resolve entry / existing TP for dual-TP math and restore safety
    pos_fields = _get_position_fields(order_id)
    entry = entry_price if entry_price is not None else pos_fields.get("entry_price")
    if entry is None:
        entry = 0.0
    entry = round(float(entry), 2)
    existing_tp = pos_fields.get("tp_order_id")

    # Phase 2: place Take Profit limit(s) — skip if restore already has TP ids
    if existing_tp:
        logger.info(
            "[Lifecycle] TP already set for %s (%s) — skip place",
            order_id,
            existing_tp,
        )
    elif strategy == "draft_early":
        await _place_draft_early_tps(
            client,
            order_id,
            token_id,
            actual_size,
            entry,
            options,
            strategy,
        )
    elif tp_price:
        tp_order_id = await _place_take_profit(
            client, token_id, actual_size, round(float(tp_price), 2), options
        )
        if tp_order_id:
            _update_position(order_id, tp_order_id=tp_order_id)
            order_audit.info(
                "TP placed | order_id=%s token_id=%s tp_order_id=%s "
                "size=%s price=%s strategy=%s",
                order_id,
                token_id,
                tp_order_id,
                round(float(actual_size), 2),
                round(float(tp_price), 2),
                strategy,
            )
        else:
            logger.error("[Lifecycle] failed to place TP for %s", order_id)

    logger.info(
        "[Lifecycle] done %s size=%s (SL radar owns Phase 3)",
        order_id,
        actual_size,
    )


async def token_sl_radar(token_id: str) -> None:
    """
    Singleton WebSocket worker for one token (Phase 3).

    One connection per token_id. On each book tick, evaluates every OPEN
    position with an SL independently (per-order confirmation counters).
    Sequential SL execution is intentional — no order queues.
    """
    logger.info("[Radar] starting singleton SL radar for token %s", token_id)
    client = get_clob_client()
    options = await get_neg_risk_options(token_id)

    bids_book: dict[float, float] = {}
    asks_book: dict[float, float] = {}
    # Key: order_id → consecutive ticks where best_bid is at/below SL
    sl_confirmations: dict[str, int] = {}
    # Key: order_id → monotonic timestamp of first radar sight (draft_early SL delay)
    pos_start_times: dict[str, float] = {}
    empty_book_count = 0
    last_tp_check = time.time()

    await _seed_order_book(client, token_id, bids_book, asks_book)

    while True:
        try:
            async with websockets.connect(settings.poly_ws_url, ping_interval=None) as ws:
                await ws.send(json.dumps({"assets_ids": [token_id], "type": "market"}))

                async def ping_loop() -> None:
                    while True:
                        await asyncio.sleep(10)
                        try:
                            await ws.send("PING")
                        except Exception:
                            break

                ping_task = asyncio.create_task(ping_loop())
                try:
                    while True:
                        # Periodic TP fill / resolve check (preserves original behavior)
                        if time.time() - last_tp_check > 15:
                            last_tp_check = time.time()
                            for tp_pos in _get_open_tp_positions(token_id):
                                closed = await _check_tp_status(
                                    client, tp_pos["order_id"], tp_pos["tp_order_id"]
                                )
                                if closed:
                                    sl_confirmations.pop(tp_pos["order_id"], None)
                                    pos_start_times.pop(tp_pos["order_id"], None)
                            await _seed_order_book(client, token_id, bids_book, asks_book)

                        try:
                            msg = await asyncio.wait_for(ws.recv(), timeout=30.0)
                        except asyncio.TimeoutError:
                            continue

                        if msg == "PONG":
                            continue

                        data = json.loads(msg)
                        events = data if isinstance(data, list) else [data]

                        for ev in events:
                            if ev.get("asset_id") and ev.get("asset_id") != token_id:
                                continue
                            etype = ev.get("event_type")
                            if etype == "book":
                                _apply_book_snapshot(bids_book, asks_book, ev)
                            elif etype == "price_change":
                                _apply_price_change(bids_book, asks_book, ev)

                        if not bids_book and not asks_book:
                            empty_book_count += 1
                            if empty_book_count > 20:
                                logger.info(
                                    "[Radar] empty book → RESOLVED all OPEN on %s",
                                    token_id,
                                )
                                for pos in _get_open_sl_positions(token_id):
                                    _update_position(
                                        pos["order_id"],
                                        status="RESOLVED",
                                        exit_price=1.0,
                                    )
                                sl_confirmations.clear()
                                pos_start_times.clear()
                                empty_book_count = 0
                            continue
                        empty_book_count = 0

                        # --- a. Top of book ---
                        best_bid = max(bids_book) if bids_book else 0
                        best_ask = min(asks_book) if asks_book else 1

                        # --- b. SPREAD PROTECTION (exact: 0.15) ---
                        if best_ask - best_bid > 0.15:
                            sl_confirmations.clear()
                            continue

                        # --- c. Active OPEN positions with SL for this token ---
                        positions = _get_open_sl_positions(token_id)
                        active_ids = {p["order_id"] for p in positions}
                        # Drop confirmations / start times for positions no longer OPEN
                        for oid in list(sl_confirmations.keys()):
                            if oid not in active_ids:
                                sl_confirmations.pop(oid, None)
                        for oid in list(pos_start_times.keys()):
                            if oid not in active_ids:
                                pos_start_times.pop(oid, None)

                        # --- d. Per-order SL evaluation (independent counters) ---
                        for pos in positions:
                            order_id = pos["order_id"]
                            sl_trigger = pos["sl_trigger_price"]
                            strategy = (pos.get("strategy") or "custom").lower()

                            # draft_early: record first sight; block SL for 16 minutes
                            if strategy == "draft_early":
                                if order_id not in pos_start_times:
                                    pos_start_times[order_id] = time.monotonic()
                                age = time.monotonic() - pos_start_times[order_id]
                                if age <= DRAFT_EARLY_SL_DELAY_SEC:
                                    # SL disabled until 16m elapsed
                                    sl_confirmations.pop(order_id, None)
                                    continue

                            if 0 < best_bid <= sl_trigger:
                                sl_confirmations[order_id] = (
                                    sl_confirmations.get(order_id, 0) + 1
                                )
                                # 3-tick confirmation for standard + short_range / high_range
                                if sl_confirmations[order_id] < SL_TICK_CONFIRMATIONS:
                                    continue

                                # TRIGGER FIRED
                                logger.warning(
                                    "[Radar] SL hit @ %s for %s (token %s) ticks=%s",
                                    best_bid,
                                    order_id,
                                    token_id,
                                    sl_confirmations[order_id],
                                )

                                for tp_id in _split_tp_ids(pos.get("tp_order_id")):
                                    await cancel_order(tp_id)

                                # match strategy sells half; others full size
                                sell_ratio = 0.5 if strategy == "match" else 1.0
                                shares_to_sell = round(pos["size"] * sell_ratio, 2)

                                # Sequential market sell; balance auto-correct is inside market_sell
                                sl_resp = await market_sell(
                                    token_id, shares_to_sell, options
                                )

                                if sl_resp and (
                                    sl_resp.get("success")
                                    or sl_resp.get("orderID")
                                    or sl_resp.get("id")
                                ):
                                    logger.info("[Radar] SL filled for %s", order_id)
                                    order_audit.info(
                                        "SL triggered market_sell | order_id=%s "
                                        "token_id=%s size=%s price=%s strategy=%s",
                                        order_id,
                                        token_id,
                                        shares_to_sell,
                                        best_bid,
                                        strategy,
                                    )
                                    _update_position(
                                        order_id,
                                        status="CLOSED_SL",
                                        exit_price=best_bid,
                                    )
                                    sl_confirmations.pop(order_id, None)
                                    pos_start_times.pop(order_id, None)
                                else:
                                    logger.error(
                                        "[Radar] SL order failed for %s", order_id
                                    )
                                    order_audit.error(
                                        "SL market_sell failed | order_id=%s "
                                        "token_id=%s size=%s strategy=%s resp=%s",
                                        order_id,
                                        token_id,
                                        shares_to_sell,
                                        strategy,
                                        sl_resp,
                                    )
                                # Continue loop for remaining positions (no queue)
                            else:
                                # Price bounced back above SL
                                sl_confirmations.pop(order_id, None)
                finally:
                    ping_task.cancel()
        except Exception as exc:
            logger.debug("[Radar] WS reconnect token %s: %s", token_id, exc)
            await asyncio.sleep(2)
