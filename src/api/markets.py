"""Markets HTTP routes — thin layer over cache + filter services."""
from __future__ import annotations

from fastapi import APIRouter, Query

from src.core.mappings import CRYPTO_TIMEFRAME_TAGS, get_slugs_for_request
from src.services.market_cache import market_cache
from src.services.market_filter import filter_events, search_events

router = APIRouter(tags=["markets"])


@router.get("/markets")
async def get_markets(
    category: str = Query("most_traded"),
    subcategory: str = Query("all"),
):
    market_cache.ensure_background_updater()

    target_slugs = get_slugs_for_request(category, subcategory)
    sub_l = subcategory.lower()
    cat_l = category.lower()

    # Short crypto windows rotate constantly — always pull fresh Gamma data
    force_fresh = cat_l == "crypto" and sub_l in CRYPTO_TIMEFRAME_TAGS

    if force_fresh:
        fast_data = await market_cache.fetch_specific_slugs(target_slugs, limit=100)
        events = filter_events(fast_data, category, subcategory, target_slugs)
        if not events:
            events = filter_events(market_cache.values(), category, subcategory, target_slugs)
    else:
        events = filter_events(market_cache.values(), category, subcategory, target_slugs)
        # Cold start / empty filter: pull only the needed tags on demand
        if not events:
            fast_data = await market_cache.fetch_specific_slugs(target_slugs, limit=100)
            events = filter_events(fast_data, category, subcategory, target_slugs)

    # Live crypto window already capped at ~7; other lists keep normal limits
    if force_fresh:
        return events
    limit = 50 if category == "most_traded" else 100
    return events[:limit]


@router.get("/markets/search")
async def search_markets(q: str = Query("", min_length=0)):
    """Search markets by title in the RAM cache (for the header search bar)."""
    query = (q or "").strip()
    if len(query) < 1:
        return {"markets": []}

    market_cache.ensure_background_updater()
    markets = search_events(market_cache.values(), query, limit=20)

    # If cache is cold, try a broad pull once
    if not markets and market_cache.size < 20:
        await market_cache.fetch_specific_slugs([None], limit=50)
        markets = search_events(market_cache.values(), query, limit=20)

    return {"markets": markets}
