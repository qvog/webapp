"""FastAPI application entrypoint."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from py_clob_client_v2 import PartialCreateOrderOptions

from src.api import markets, trade
from src.api.client import get_clob_client, run_sync
from src.api.stats import router as stats_router
from src.api.trade import active_token_radars
from src.config import settings
from src.database.db import SessionLocal, ensure_schema
from src.database.models import Position
from src.services.market_cache import market_cache
from src.workers.monitor import setup_order_lifecycle, token_sl_radar

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

ensure_schema()


async def restore_open_positions() -> None:
    """
    After process restart:
      - Re-run REST lifecycle for PENDING/OPEN positions (fill wait + TP if needed).
      - Start one singleton SL radar per distinct token_id.
    """
    logger.info("[SYSTEM] Restoring open positions...")
    db = SessionLocal()
    try:
        open_positions = (
            db.query(Position)
            .filter(Position.status.in_(["OPEN", "PENDING"]))
            .all()
        )
        if not open_positions:
            logger.info("[SYSTEM] No open positions")
            return

        logger.warning("[SYSTEM] Restoring %s positions", len(open_positions))
        client = get_clob_client()
        tokens_needed: set[str] = set()

        for pos in open_positions:
            try:
                is_neg_risk = await run_sync(client.get_neg_risk, str(pos.token_id))
                options = PartialCreateOrderOptions(tick_size="0.01", neg_risk=is_neg_risk)

                # Lifecycle: wait for fill (no-op if already filled) + ensure TP exists
                # For draft_early, dual TPs are rebuilt from entry when tp_order_id is missing
                asyncio.create_task(
                    setup_order_lifecycle(
                        order_id=pos.order_id,
                        original_size=pos.size,
                        token_id=pos.token_id,
                        tp_price=pos.tp_price if not pos.tp_order_id else None,
                        sl_price=pos.sl_trigger_price,
                        options=options,
                        strategy=pos.strategy,
                        entry_price=pos.entry_price,
                    )
                )
                tokens_needed.add(str(pos.token_id))
                logger.info("[SYSTEM] Lifecycle restored for %s", pos.order_id)
            except Exception as exc:
                logger.error("[SYSTEM] Failed to restore %s: %s", pos.order_id, exc)

        for token_id in tokens_needed:
            if token_id not in active_token_radars:
                active_token_radars.add(token_id)
                asyncio.create_task(token_sl_radar(token_id))
                logger.info("[SYSTEM] SL radar started for token %s", token_id)
    except Exception as exc:
        logger.error("[SYSTEM] Restore failed: %s", exc)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    market_cache.ensure_background_updater()
    await restore_open_positions()
    yield
    await market_cache.close()


app = FastAPI(title="qScalp Terminal API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(trade.router, prefix="/api")
app.include_router(markets.router, prefix="/api")
app.include_router(stats_router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok", "markets_cached": market_cache.size}
