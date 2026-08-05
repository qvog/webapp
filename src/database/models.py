from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String

from .db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)

    order_id = Column(String, index=True, nullable=False, unique=True)
    token_id = Column(String, index=True, nullable=False)
    condition_id = Column(String, nullable=True)
    strategy = Column(String, nullable=False)  # custom | 4c | 8c | match

    side = Column(String)

    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    size = Column(Float, nullable=False)

    tp_price = Column(Float, nullable=True)
    tp_order_id = Column(String, nullable=True)
    sl_trigger_price = Column(Float, nullable=True)

    # OPEN | PENDING | CLOSED_TP | CLOSED_SL | PANIC_SELL | CANCELED | RESOLVED | EXPIRED
    status = Column(String, default="OPEN")

    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)