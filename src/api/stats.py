"""Read-only PnL / statistics analytics endpoints.

Pure analytics layer over closed positions. Does not touch trading logic
or the position monitor.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.database.db import get_db
from src.database.models import Position

router = APIRouter(tags=["stats"])

# Terminal statuses that represent a fully closed / resolved trade.
CLOSED_STATUSES = ("CLOSED_TP", "CLOSED_SL", "PANIC_SELL", "RESOLVED")

# Cap used when gross loss is zero (infinite profit factor).
INFINITE_PROFIT_FACTOR = 999.0


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Coerce nullable / bad numeric fields to float without raising."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


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
        # No losses but some profit → infinite PF
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
        # Break-even and losers count as losses for winrate
        bucket["losses"] += 1
        if pnl < 0:
            bucket["gross_loss"] += abs(pnl)


@router.get("/stats/summary")
def get_stats_summary(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Overall + per-strategy PnL / winrate / profit-factor metrics."""
    positions = (
        db.query(Position)
        .filter(Position.status.in_(list(CLOSED_STATUSES)))
        .all()
    )

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
        "overall": _finalize_metrics(overall),
        "strategies": strategies,
    }


@router.get("/stats/history")
def get_stats_history(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Closed trade history, newest first."""
    positions = (
        db.query(Position)
        .filter(Position.status.in_(list(CLOSED_STATUSES)))
        .order_by(Position.id.desc())
        .all()
    )

    trades: list[dict[str, Any]] = []
    for pos in positions:
        entry = _safe_float(pos.entry_price)
        exit_ = _safe_float(pos.exit_price)
        size = _safe_float(pos.size)
        pnl = (exit_ - entry) * size
        trades.append(
            {
                "order_id": pos.order_id,
                "token_id": pos.token_id,
                "strategy": (pos.strategy or "custom").strip() or "custom",
                "entry_price": entry,
                "exit_price": exit_,
                "size": size,
                "pnl": round(pnl, 4),
                "status": pos.status,
            }
        )

    return {"trades": trades}
