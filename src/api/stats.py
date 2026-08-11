"""Read-only PnL / statistics analytics endpoints.

Pure analytics layer over closed positions. Does not touch trading logic
or the position monitor.
"""
from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, nullslast
from sqlalchemy.orm import Session

from src.database.db import get_db
from src.database.models import Position
from src.services.market_cache import market_cache
from src.utils.json_parse import safe_parse

router = APIRouter(tags=["stats"])
logger = logging.getLogger(__name__)

# Terminal statuses that represent a fully closed / resolved trade.
CLOSED_STATUSES = ("CLOSED_TP", "CLOSED_SL", "PANIC_SELL", "RESOLVED")

# Cap used when gross loss is zero (infinite profit factor).
INFINITE_PROFIT_FACTOR = 999.0

# Time-range filters for stats (query param `period`)
PERIOD_DELTAS: dict[str, timedelta | None] = {
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
    "90d": timedelta(days=90),
    "1y": timedelta(days=365),
    "all": None,
}
DEFAULT_PERIOD = "all"

GAMMA_MARKETS_URL = "https://gamma-api.polymarket.com/markets"

# Process-local meta cache: condition_id / token_id → meta dict
_meta_cache: dict[str, dict[str, Any]] = {}
_meta_lock = threading.Lock()
_META_TTL_SEC = 60 * 60  # 1 hour
_meta_fetched_at: dict[str, float] = {}


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Coerce nullable / bad numeric fields to float without raising."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _iso_ts(value: Any) -> str | None:
    """Serialize datetime to ISO-8601 UTC string for the frontend."""
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    try:
        return str(value)
    except Exception:
        return None


def _as_utc(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    return None


def _trade_ts(pos: Position) -> datetime | None:
    """Best timestamp for filtering / sorting a closed trade."""
    return _as_utc(getattr(pos, "updated_at", None)) or _as_utc(
        getattr(pos, "created_at", None)
    )


def _period_cutoff(period: str) -> datetime | None:
    key = (period or DEFAULT_PERIOD).strip().lower()
    delta = PERIOD_DELTAS.get(key, PERIOD_DELTAS[DEFAULT_PERIOD])
    if delta is None:
        return None
    return datetime.now(timezone.utc) - delta


def _filter_by_period(positions: list[Position], period: str) -> list[Position]:
    cutoff = _period_cutoff(period)
    if cutoff is None:
        return list(positions)
    out: list[Position] = []
    for pos in positions:
        ts = _trade_ts(pos)
        if ts is None:
            # Keep undated rows so we never silently drop data
            out.append(pos)
            continue
        if ts >= cutoff:
            out.append(pos)
    return out


def _trade_pnl(pos: Position) -> float:
    """PnL for a single closed position: (exit - entry) * size."""
    entry = _safe_float(pos.entry_price)
    exit_ = _safe_float(pos.exit_price)
    size = _safe_float(pos.size)
    return (exit_ - entry) * size


def _empty_bucket() -> dict[str, Any]:
    return {
        "total_trades": 0,
        "wins": 0,
        "losses": 0,
        "winrate": 0.0,
        "total_pnl": 0.0,
        "gross_profit": 0.0,
        "gross_loss": 0.0,
        "profit_factor": 0.0,
    }


def _finalize_metrics(bucket: dict[str, Any]) -> dict[str, Any]:
    """Derive winrate + profit factor with division-by-zero protection."""
    total = int(bucket["total_trades"])
    wins = int(bucket["wins"])
    gross_profit = float(bucket["gross_profit"])
    gross_loss = float(bucket["gross_loss"])

    if total > 0:
        bucket["winrate"] = round((wins / total) * 100.0, 2)
    else:
        bucket["winrate"] = 0.0

    if gross_loss > 0:
        bucket["profit_factor"] = round(gross_profit / gross_loss, 2)
    elif gross_profit > 0:
        bucket["profit_factor"] = INFINITE_PROFIT_FACTOR
    else:
        bucket["profit_factor"] = 0.0

    bucket["total_pnl"] = round(float(bucket["total_pnl"]), 4)
    bucket["gross_profit"] = round(gross_profit, 4)
    bucket["gross_loss"] = round(gross_loss, 4)
    return bucket


def _accumulate(bucket: dict[str, Any], pnl: float) -> None:
    bucket["total_trades"] += 1
    bucket["total_pnl"] += pnl
    if pnl > 0:
        bucket["wins"] += 1
        bucket["gross_profit"] += pnl
    else:
        bucket["losses"] += 1
        if pnl < 0:
            bucket["gross_loss"] += abs(pnl)


def _meta_from_market(market: dict[str, Any], token_id: str | None = None) -> dict[str, Any]:
    """Extract display fields from a Gamma market payload."""
    events = market.get("events") or []
    event = events[0] if events and isinstance(events[0], dict) else {}

    match_title = (
        event.get("title")
        or market.get("question")
        or market.get("groupItemTitle")
        or None
    )
    image = (
        event.get("image")
        or event.get("icon")
        or market.get("image")
        or market.get("icon")
        or None
    )
    question = market.get("question") or match_title

    outcome = None
    token_ids = [str(t) for t in safe_parse(market.get("clobTokenIds", []))]
    outcomes = safe_parse(market.get("outcomes", []))
    if token_id:
        tid = str(token_id)
        if tid in token_ids:
            idx = token_ids.index(tid)
            if idx < len(outcomes) and outcomes[idx] is not None:
                outcome = str(outcomes[idx]).upper()

    return {
        "match_title": match_title,
        "image": image,
        "outcome": outcome,
        "question": question,
    }


def _build_token_meta_index_from_cache() -> dict[str, dict[str, Any]]:
    """Index token_id → meta from the in-memory market cache (active events)."""
    index: dict[str, dict[str, Any]] = {}
    try:
        events = market_cache.values() or []
    except Exception:
        return index

    for ev in events:
        if not isinstance(ev, dict):
            continue
        # Wrap raw Gamma event as a pseudo-market for _meta_from_market
        base_title = ev.get("title")
        base_image = ev.get("image") or ev.get("icon")
        for m in ev.get("markets") or []:
            if not isinstance(m, dict):
                continue
            # Attach parent event so image/title resolve
            market = dict(m)
            market.setdefault("events", [ev])
            token_ids = [str(t) for t in safe_parse(m.get("clobTokenIds", []))]
            for tid in token_ids:
                if not tid or tid in index:
                    continue
                meta = _meta_from_market(market, tid)
                if not meta.get("match_title"):
                    meta["match_title"] = base_title
                if not meta.get("image"):
                    meta["image"] = base_image
                index[tid] = meta
    return index


def _gamma_fetch_market(
    *,
    condition_id: str | None = None,
    token_id: str | None = None,
) -> dict[str, Any] | None:
    """
    Look up a single market on Gamma. Closed historical markets require closed=true.
    Tries open first, then closed.
    """
    if not condition_id and not token_id:
        return None

    attempts: list[dict[str, Any]] = []
    if condition_id:
        attempts.append({"condition_ids": condition_id, "limit": 3})
        attempts.append({"condition_ids": condition_id, "closed": "true", "limit": 3})
    if token_id:
        attempts.append({"clob_token_ids": token_id, "limit": 3})
        attempts.append({"clob_token_ids": token_id, "closed": "true", "limit": 3})

    try:
        with httpx.Client(timeout=httpx.Timeout(6.0, connect=4.0)) as client:
            for params in attempts:
                try:
                    resp = client.get(GAMMA_MARKETS_URL, params=params)
                    if resp.status_code != 200:
                        continue
                    data = resp.json()
                    if not isinstance(data, list) or not data:
                        continue
                    # Prefer exact condition_id match when available
                    if condition_id:
                        for m in data:
                            if str(m.get("conditionId") or "") == str(condition_id):
                                return m
                    return data[0] if isinstance(data[0], dict) else None
                except (httpx.HTTPError, ValueError, TypeError):
                    continue
    except Exception as exc:
        logger.debug("[stats] gamma lookup failed: %s", exc)
    return None


def _cache_get(key: str) -> dict[str, Any] | None:
    if not key:
        return None
    with _meta_lock:
        ts = _meta_fetched_at.get(key)
        if ts is None:
            return None
        if time.time() - ts > _META_TTL_SEC:
            return None
        return _meta_cache.get(key)


def _cache_set(key: str, meta: dict[str, Any]) -> None:
    if not key:
        return
    with _meta_lock:
        _meta_cache[key] = meta
        _meta_fetched_at[key] = time.time()


def _resolve_meta(
    *,
    token_id: str,
    condition_id: str | None,
    cache_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """
    Resolve match title / image / outcome for a trade.
    Order: process cache → live market_cache index → Gamma API.
    """
    empty = {
        "match_title": None,
        "image": None,
        "outcome": None,
        "question": None,
    }

    # 1) Live RAM market cache
    if token_id and token_id in cache_index:
        return {**empty, **cache_index[token_id]}

    # 2) Process-local TTL cache (by condition, then token)
    for key in (condition_id or "", token_id or ""):
        hit = _cache_get(key)
        if hit:
            # Re-bind outcome to this token if cached without it
            if token_id and not hit.get("outcome") and hit.get("_market"):
                return {**empty, **_meta_from_market(hit["_market"], token_id)}
            return {**empty, **{k: hit.get(k) for k in empty}}

    # 3) Gamma API (handles closed/historical markets)
    market = _gamma_fetch_market(condition_id=condition_id, token_id=token_id or None)
    if not market:
        # Cache negative result briefly to avoid hammering
        stub = dict(empty)
        if condition_id:
            _cache_set(condition_id, stub)
        if token_id:
            _cache_set(token_id, stub)
        return empty

    meta = _meta_from_market(market, token_id or None)
    # Store full market for outcome re-binding across tokens of same condition
    stored = {**meta, "_market": market}
    if condition_id:
        _cache_set(condition_id, stored)
    # Index every token on this market
    for tid in [str(t) for t in safe_parse(market.get("clobTokenIds", []))]:
        tmeta = _meta_from_market(market, tid)
        _cache_set(tid, {**tmeta, "_market": market})
        cache_index[tid] = tmeta

    return meta


def _sort_key_newest_first(pos: Position) -> tuple:
    """Robust newest-first key: prefer updated_at, then created_at, then id."""

    def _ts(value: Any) -> float:
        dt = _as_utc(value)
        if dt is None:
            return 0.0
        try:
            return dt.timestamp()
        except Exception:
            return 0.0

    return (
        _ts(getattr(pos, "updated_at", None)),
        _ts(getattr(pos, "created_at", None)),
        int(getattr(pos, "id", 0) or 0),
    )


def _load_closed_positions(db: Session, period: str) -> list[Position]:
    positions = (
        db.query(Position)
        .filter(Position.status.in_(list(CLOSED_STATUSES)))
        .order_by(
            nullslast(desc(Position.updated_at)),
            nullslast(desc(Position.created_at)),
            desc(Position.id),
        )
        .all()
    )
    positions = _filter_by_period(positions, period)
    positions = sorted(positions, key=_sort_key_newest_first, reverse=True)
    return positions


def _normalize_period(period: str | None) -> str:
    key = (period or DEFAULT_PERIOD).strip().lower()
    if key not in PERIOD_DELTAS:
        return DEFAULT_PERIOD
    return key


@router.get("/stats/summary")
def get_stats_summary(
    period: str = Query(
        DEFAULT_PERIOD,
        description="Time window: 24h | 7d | 30d | 90d | 1y | all",
    ),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Overall + per-strategy PnL / winrate / profit-factor metrics."""
    period = _normalize_period(period)
    positions = _load_closed_positions(db, period)

    overall = _empty_bucket()
    by_strategy: dict[str, dict[str, Any]] = defaultdict(_empty_bucket)

    for pos in positions:
        pnl = _trade_pnl(pos)
        strategy = (pos.strategy or "custom").strip() or "custom"
        _accumulate(overall, pnl)
        _accumulate(by_strategy[strategy], pnl)

    strategies = {
        name: _finalize_metrics(bucket) for name, bucket in sorted(by_strategy.items())
    }

    return {
        "period": period,
        "overall": _finalize_metrics(overall),
        "strategies": strategies,
    }


@router.get("/stats/history")
def get_stats_history(
    period: str = Query(
        DEFAULT_PERIOD,
        description="Time window: 24h | 7d | 30d | 90d | 1y | all",
    ),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Closed trade history, newest first, enriched with match names/images."""
    period = _normalize_period(period)
    positions = _load_closed_positions(db, period)

    cache_index = _build_token_meta_index_from_cache()

    trades: list[dict[str, Any]] = []
    for pos in positions:
        entry = _safe_float(pos.entry_price)
        exit_ = _safe_float(pos.exit_price)
        size = _safe_float(pos.size)
        pnl = (exit_ - entry) * size
        token_id = str(pos.token_id) if pos.token_id is not None else ""
        condition_id = str(pos.condition_id) if pos.condition_id else None

        meta = _resolve_meta(
            token_id=token_id,
            condition_id=condition_id,
            cache_index=cache_index,
        )

        created_at = _iso_ts(pos.created_at)
        updated_at = _iso_ts(pos.updated_at)
        timestamp = updated_at or created_at

        trades.append(
            {
                "id": pos.id,
                "order_id": pos.order_id,
                "token_id": token_id,
                "condition_id": condition_id,
                "strategy": (pos.strategy or "custom").strip() or "custom",
                "entry_price": entry,
                "exit_price": exit_,
                "size": size,
                "pnl": round(pnl, 4),
                "status": pos.status,
                "created_at": created_at,
                "updated_at": updated_at,
                "timestamp": timestamp,
                "match_title": meta.get("match_title"),
                "image": meta.get("image"),
                "outcome": meta.get("outcome"),
                "question": meta.get("question"),
            }
        )

    return {"period": period, "trades": trades}
