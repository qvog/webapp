"""Background position monitor: fill wait → TP order → SL via WebSocket."""
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
from src.database.db import SessionLocal
from src.database.models import Position
from src.services.orders import cancel_order, market_sell, parse_order_payload

logger = logging.getLogger(__name__)

# Avoid routing WS through HTTP proxy
os.environ.setdefault("no_proxy", "ws-subscriptions-clob.polymarket.com")


@contextmanager
def db_session():
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
                logger.info("[Worker] filled %s size=%s", order_id, size)
                _update_position(order_id, status="OPEN", size=size)
                return size

            if status in ("CANCELED", "EXPIRED"):
                if size_matched and float(size_matched) > 0:
                    size = int(float(size_matched) * 100) / 100.0
                    logger.warning("[Worker] partial fill on cancel: %s", size)
                    _update_position(order_id, status="OPEN", size=size)
                    return size
                logger.warning("[Worker] order cancelled empty: %s", order_id)
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
                logger.info("[Worker] TP placed: %s", tp_id)
                return tp_id
        except Exception:
            pass
        await asyncio.sleep(2)
    return None


async def _seed_order_book(client: Any, token_id: str, bids: dict, asks: dict) -> None:
    try:
        ob = await run_sync(client.get_order_book, token_id)
        if isinstance(ob, dict):
            _apply_book_snapshot(bids, asks, ob)
    except Exception:
        pass


async def _check_tp_status(client: Any, order_id: str, tp_order_id: str) -> bool:
    """Return True if monitoring should stop (TP filled or market resolved)."""
    try:
        tp_info = await run_sync(client.get_order, tp_order_id)
        tp_data = parse_order_payload(tp_info)
        if not isinstance(tp_data, dict):
            return False

        status = tp_data.get("status")
        if status in ("MATCHED", "FILLED"):
            logger.info("[Worker] TP hit for %s", order_id)
            _update_position(
                order_id,
                status="CLOSED_TP",
                exit_price=float(tp_data.get("price") or 0),
            )
            return True
        if status in ("CANCELED", "EXPIRED"):
            logger.info("[Worker] TP cancelled (resolved) for %s", order_id)
            _update_position(order_id, status="RESOLVED", exit_price=1.0)
            return True
    except Exception:
        pass
    return False


async def monitor_and_manage_position(
    order_id: str,
    entry_price: float,
    tp_price: float | None,
    sl_price: float | None,
    original_size: float,
    token_id: str,
    options: PartialCreateOrderOptions,
    strategy: str,
) -> None:
    logger.info("[Worker] watching %s strategy=%s", order_id, strategy.upper())
    client = get_clob_client()

    actual_size = await _wait_for_fill(client, order_id, original_size)
    if not actual_size:
        _update_position(order_id, status="EXPIRED")
        return

    tp_order_id = None
    if tp_price:
        tp_order_id = await _place_take_profit(
            client, token_id, actual_size, tp_price, options
        )

    sell_ratio = 0.5 if strategy == "match" else 1.0
    sl_trigger = max(0.01, round(float(sl_price or (entry_price - 0.12)), 2))
    logger.info("[Worker] SL active @ %s for %s", sl_trigger, order_id)

    bids_book: dict[float, float] = {}
    asks_book: dict[float, float] = {}
    sl_confirmations = 0
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
                        if time.time() - last_tp_check > 15:
                            last_tp_check = time.time()
                            if tp_order_id and await _check_tp_status(client, order_id, tp_order_id):
                                return
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
                                logger.info("[Worker] empty book → RESOLVED %s", order_id)
                                _update_position(order_id, status="RESOLVED", exit_price=1.0)
                                return
                            continue
                        empty_book_count = 0

                        best_bid = max(bids_book) if bids_book else 0
                        best_ask = min(asks_book) if asks_book else 1
                        if best_ask - best_bid > 0.15:
                            sl_confirmations = 0
                            continue

                        if 0 < best_bid <= sl_trigger:
                            sl_confirmations += 1
                            if sl_confirmations < 2:
                                continue

                            logger.warning("[Worker] SL hit @ %s for %s", best_bid, order_id)
                            if tp_order_id:
                                await cancel_order(tp_order_id)

                            shares = round(actual_size * sell_ratio, 2)
                            sl_resp = await market_sell(token_id, shares, options)

                            if sl_resp and (
                                sl_resp.get("success")
                                or sl_resp.get("orderID")
                                or sl_resp.get("id")
                            ):
                                logger.info("[Worker] SL filled for %s", order_id)
                                _update_position(
                                    order_id, status="CLOSED_SL", exit_price=best_bid
                                )
                            else:
                                logger.error("[Worker] SL order failed for %s", order_id)
                            return

                        sl_confirmations = 0
                finally:
                    ping_task.cancel()
        except Exception as exc:
            logger.debug("[Worker] WS reconnect %s: %s", order_id, exc)
            await asyncio.sleep(2)
