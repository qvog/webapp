"""Shared Polymarket order helpers used by trade API and position workers."""
from __future__ import annotations

import logging
import re
from typing import Any

from py_clob_client_v2 import OrderArgs, OrderType, PartialCreateOrderOptions
from py_clob_client_v2.order_builder.constants import SELL

from src.api.client import get_clob_client, run_sync
from src.config import settings

logger = logging.getLogger(__name__)

# Polymarket binary outcome prices: open interval edges are untradeable / resolved.
MIN_LIMIT_PRICE = 0.01
MAX_LIMIT_PRICE = 0.99


def validate_limit_price(price: float) -> float:
    """
    Reject limit prices outside the tradable band [0.01, 0.99].

    Raises:
        ValueError: if price is below 0.01 or above 0.99 (or non-numeric).
    """
    try:
        p = float(price)
    except (TypeError, ValueError) as exc:
        raise ValueError("Цена ордера должна быть числом") from exc
    if p < MIN_LIMIT_PRICE or p > MAX_LIMIT_PRICE:
        raise ValueError(
            f"Цена ордера {p} вне допустимого диапазона "
            f"[{MIN_LIMIT_PRICE}, {MAX_LIMIT_PRICE}]"
        )
    return p


class OrderProxy:
    """Adapter for clob client cancel methods that expect an object with orderID."""

    def __init__(self, order_id: str) -> None:
        self.orderID = order_id
        self.id = order_id


def cancel_order_sync(client: Any, order_id: str) -> bool:
    """Cancel a single order; tries cancel / cancel_order with str or proxy."""
    for method_name in ("cancel", "cancel_order"):
        method = getattr(client, method_name, None)
        if not callable(method):
            continue
        try:
            method(order_id)
            return True
        except (AttributeError, TypeError):
            try:
                method(OrderProxy(order_id))
                return True
            except Exception:
                continue
        except Exception as exc:
            logger.debug("cancel %s failed: %s", order_id, exc)
    return False


async def cancel_order(order_id: str) -> bool:
    client = get_clob_client()
    return await run_sync(cancel_order_sync, client, order_id)


async def get_neg_risk_options(token_id: str) -> PartialCreateOrderOptions:
    client = get_clob_client()
    is_neg_risk = await run_sync(client.get_neg_risk, str(token_id))
    return PartialCreateOrderOptions(tick_size="0.01", neg_risk=is_neg_risk)


def parse_order_payload(order_info: Any) -> dict | None:
    if order_info is None:
        return None
    if isinstance(order_info, list):
        return order_info[0] if order_info else None
    return order_info if isinstance(order_info, dict) else None


def extract_order_id(resp: Any) -> str | None:
    if not isinstance(resp, dict):
        return None
    return resp.get("orderID") or resp.get("id")


def is_resolved_error(message: str) -> bool:
    msg = message.lower()
    return any(
        token in msg
        for token in ("invalid token id", "invalid_token", "resolved", "closed")
    )


def parse_balance_from_error(err: str) -> float | None:
    match = re.search(r"balance:\s*(\d+)", err)
    if not match:
        return None
    return int(int(match.group(1)) / 1_000_000.0 * 100) / 100.0


async def market_sell(
    token_id: str,
    size: float,
    options: PartialCreateOrderOptions,
    price: float = 0.01,
    retries: int = 2,
) -> dict | None:
    """Post a low-price GTC sell (market-like dump) with balance retry."""
    client = get_clob_client()
    current_size = size

    for _ in range(retries):
        try:
            args = OrderArgs(
                price=price,
                size=current_size,
                side=SELL,
                token_id=str(token_id),
                builder_code=settings.builder_code,
            )
            resp = await run_sync(
                client.create_and_post_order,
                order_args=args,
                options=options,
                order_type=OrderType.GTC,
            )
            if isinstance(resp, dict) and resp.get("error"):
                err = str(resp.get("error"))
                if "balance" in err.lower():
                    adjusted = parse_balance_from_error(err)
                    if adjusted is None or adjusted <= 0:
                        return None
                    current_size = adjusted
                    continue
            return resp if isinstance(resp, dict) else None
        except Exception as exc:
            err = str(exc)
            if "balance" in err.lower():
                adjusted = parse_balance_from_error(err)
                if adjusted is None or adjusted <= 0:
                    return None
                current_size = adjusted
                continue
            logger.warning("market_sell failed: %s", exc)
            return None
    return None


async def best_bid_price(token_id: str, default: float = 0.01) -> float:
    client = get_clob_client()
    try:
        ob = await run_sync(client.get_order_book, str(token_id))
        bids = ob.get("bids", []) if isinstance(ob, dict) else []
        if not bids:
            return default
        return max(float(b["price"]) for b in bids)
    except Exception:
        return default
