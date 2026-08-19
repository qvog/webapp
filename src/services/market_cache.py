"""In-memory market cache with background refresh from Gamma API."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from src.config import settings
from src.core.mappings import CACHE_POOL_SLUGS

logger = logging.getLogger(__name__)

_HEADERS = {"Accept": "application/json"}


class MarketCache:
    """Thread-safe-ish async cache of Polymarket Gamma events."""

    def __init__(self) -> None:
        self._events: dict[str, dict] = {}
        self._lock = asyncio.Lock()
        self._fetching = False
        self._updater_task: asyncio.Task | None = None
        self._client: httpx.AsyncClient | None = None

    @property
    def size(self) -> int:
        return len(self._events)

    def values(self) -> list[dict]:
        return list(self._events.values())

    def upsert_many(self, events: list[dict]) -> None:
        for ev in events:
            event_id = ev.get("id")
            if event_id is not None:
                self._events[str(event_id)] = ev

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers=_HEADERS,
                timeout=httpx.Timeout(8.0, connect=5.0),
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            )
        return self._client

    async def close(self) -> None:
        if self._updater_task and not self._updater_task.done():
            self._updater_task.cancel()
            try:
                await self._updater_task
            except asyncio.CancelledError:
                pass
            self._updater_task = None
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def ensure_background_updater(self) -> None:
        if self._updater_task is None or self._updater_task.done():
            self._updater_task = asyncio.create_task(self._background_loop())

    async def _background_loop(self) -> None:
        # First refresh soon after start; then on interval
        await asyncio.sleep(1)
        while True:
            try:
                await self.refresh_pool()
            except Exception as exc:
                logger.error("[SYNC ERROR] %s", exc)
            await asyncio.sleep(settings.market_cache_interval_sec)

    async def _fetch_slug(self, client: httpx.AsyncClient, slug: str | None, limit: int = 100) -> list[dict]:
        params: dict[str, Any] = {
            "active": "true",
            "closed": "false",
            "limit": str(limit),
            # Gamma accepts volume24hr (not volume_24hr) — invalid order → 422 empty cache
            "order": "volume24hr",
            "ascending": "false",
        }
        if slug:
            params["tag_slug"] = slug

        for attempt in range(2):
            try:
                resp = await client.get(settings.gamma_api_url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    return data if isinstance(data, list) else []
            except (httpx.HTTPError, ValueError):
                if attempt == 0:
                    await asyncio.sleep(0.5)
        return []

    async def refresh_pool(self) -> None:
        if self._fetching:
            return
        self._fetching = True
        try:
            client = await self._get_client()
            semaphore = asyncio.Semaphore(10)

            async def safe_fetch(slug: str | None) -> list[dict]:
                async with semaphore:
                    return await self._fetch_slug(client, slug)

            responses = await asyncio.gather(
                *[safe_fetch(s) for s in CACHE_POOL_SLUGS],
                return_exceptions=True,
            )

            added = 0
            async with self._lock:
                for data in responses:
                    if isinstance(data, Exception) or not data:
                        continue
                    for ev in data:
                        eid = ev.get("id")
                        if eid is not None:
                            self._events[str(eid)] = ev
                            added += 1

            if added > 0:
                logger.info("[SYNC] RAM cache: %s unique markets", len(self._events))
        finally:
            self._fetching = False

    async def fetch_specific_slugs(self, slugs: list[str | None], limit: int = 100) -> list[dict]:
        client = await self._get_client()
        semaphore = asyncio.Semaphore(10)

        async def one(slug: str | None) -> list[dict]:
            async with semaphore:
                params: dict[str, Any] = {
                    "active": "true",
                    "closed": "false",
                    "limit": str(limit),
                }
                if slug:
                    params["tag_slug"] = slug
                try:
                    resp = await client.get(settings.gamma_api_url, params=params, timeout=5.0)
                    if resp.status_code == 200:
                        data = resp.json()
                        return data if isinstance(data, list) else []
                except (httpx.HTTPError, ValueError):
                    return []
                return []

        results: list[dict] = []
        chunks = await asyncio.gather(*[one(s) for s in slugs])
        for chunk in chunks:
            results.extend(chunk)

        self.upsert_many(results)
        return results


# Process-wide singleton
market_cache = MarketCache()
