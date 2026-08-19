"""Dedicated noise-free order audit logger (orders.log only, never stdout)."""
from __future__ import annotations

import logging
import traceback
from pathlib import Path

# Project root: src/core/order_logger.py → ../../
_ORDERS_LOG_PATH = Path(__file__).resolve().parents[2] / "orders.log"

_order_audit: logging.Logger | None = None


def get_order_audit_logger() -> logging.Logger:
    """
    Return the singleton ``order_audit`` logger.

    - FileHandler only → ``orders.log``
    - ``propagate = False`` so uvicorn / root handlers never see these lines
    """
    global _order_audit
    if _order_audit is not None:
        return _order_audit

    logger = logging.getLogger("order_audit")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Avoid duplicate handlers if module is reloaded
    if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
        handler = logging.FileHandler(_ORDERS_LOG_PATH, encoding="utf-8")
        handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        )
        logger.addHandler(handler)

    _order_audit = logger
    return logger


def log_order_exception(message: str, *args) -> None:
    """Log an order failure with the full Python stack trace for deep debugging."""
    get_order_audit_logger().error(
        "%s\n%s",
        message % args if args else message,
        traceback.format_exc(),
    )


# Convenience module-level alias
order_audit = get_order_audit_logger()
