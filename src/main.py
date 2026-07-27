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
from src.config import settings
from src.database.db import Base, SessionLocal, engine
from src.database.models import Position
from src.services.market_cache import market_cache
from src.workers.monitor import monitor_and_manage_position

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)


async def restore_open_positions() -> None:
    """Re-attach monitors for OPEN/PENDING positions after process restart."""
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

        logger.warning("[SYSTEM] Restoring %s workers", len(open_positions))
        client = get_clob_client()

        for pos in open_positions:
            try:
                is_neg_risk = await run_sync(client.get_neg_risk, str(pos.token_id))
                options = PartialCreateOrderOptions(tick_size="0.01", neg_risk=is_neg_risk)
                asyncio.create_task(
                    monitor_and_manage_position(
                        order_id=pos.order_id,
                        entry_price=pos.entry_price,
                        tp_price=pos.tp_price,
                        sl_price=pos.sl_trigger_price,
                        original_size=pos.size,
                        token_id=pos.token_id,
                        options=options,
                        strategy=pos.strategy,
                    )
                )
                logger.info("[SYSTEM] Radar restarted for %s", pos.order_id)
            except Exception as exc:
                logger.error("[SYSTEM] Failed to restore %s: %s", pos.order_id, exc)
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


@app.get("/health")
async def health():
    return {"status": "ok", "markets_cached": market_cache.size}
