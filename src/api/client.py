"""Polymarket CLOB client singleton and async bridge."""
from __future__ import annotations

import asyncio
import functools
import logging
import os
from typing import Any, Callable, TypeVar

from py_clob_client_v2 import ApiCreds, ClobClient, SignatureTypeV2

from src.config import settings

logger = logging.getLogger(__name__)

# Inject proxy into process env early for libraries that read it
if settings.poly_proxy:
    for key in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"):
        os.environ[key] = settings.poly_proxy

_clob_client: ClobClient | None = None
T = TypeVar("T")


def get_clob_client() -> ClobClient:
    """Initialize ClobClient once (singleton)."""
    global _clob_client
    if _clob_client is not None:
        return _clob_client

    if not settings.poly_private_key or not settings.poly_funder_address:
        raise ValueError("POLY_PRIVATE_KEY / POLY_FUNDER_ADDRESS are not configured in .env")

    _clob_client = ClobClient(
        host=settings.poly_host,
        key=settings.poly_private_key,
        chain_id=settings.poly_chain_id,
        signature_type=SignatureTypeV2.POLY_1271,
        funder=settings.poly_funder_address,
    )
    _clob_client.set_api_creds(
        ApiCreds(
            api_key=settings.poly_api_key,
            api_secret=settings.poly_api_secret,
            api_passphrase=settings.poly_api_passphrase,
        )
    )

    if settings.poly_proxy:
        try:
            _clob_client.session.proxies = {
                "http": settings.poly_proxy,
                "https": settings.poly_proxy,
            }
            logger.info("[PROXY] CLOB session proxies configured")
        except Exception as exc:
            logger.warning("[PROXY] bind failed: %s", exc)

    return _clob_client


async def run_sync(func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Run a blocking ClobClient call in the default executor."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, functools.partial(func, *args, **kwargs))
