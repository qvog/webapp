"""Markets HTTP routes — thin layer over cache + filter services."""
from __future__ import annotations

from fastapi import APIRouter, Query

from src.core.mappings import get_slugs_for_request
from src.services.market_cache import market_cache
from src.services.market_filter import filter_events

router = APIRouter(tags=["markets"])


@router.get("/markets")
async def get_markets(
    category: str = Query("most_traded"),
    subcategory: str = Query("all"),
):
    market_cache.ensure_background_updater()

    target_slugs = get_slugs_for_request(category, subcategory)
    events = filter_events(market_cache.values(), category, subcategory, target_slugs)

    # Cold start / empty filter: pull only the needed tags on demand
    if not events:
        fast_data = await market_cache.fetch_specific_slugs(target_slugs, limit=100)
        events = filter_events(fast_data, category, subcategory, target_slugs)

    limit = 50 if category == "most_traded" else 100
    return events[:limit]
