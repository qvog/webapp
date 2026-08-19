"""Category / slug / tag mappings for Polymarket market discovery."""
from __future__ import annotations

CRYPTO_SLUG_MAP = {
    "5 min": "5m",
    "15 min": "15m",
    "hourly": "1h",
    "4 hour": "4h",
    "daily": "daily",
    "weekly": "weekly",
    "monthly": "monthly",
    "pre-market": "pre-market",
    "etf": "etf",
}

# Strict timeframe → tag tokens that MUST be present (like Polymarket UI buckets).
# Do not include shared tags like "up-or-down" — those appear on every short window.
CRYPTO_TIMEFRAME_TAGS: dict[str, frozenset[str]] = {
    "5 min": frozenset({"5m"}),
    "15 min": frozenset({"15m"}),
    "hourly": frozenset({"1h"}),
    "4 hour": frozenset({"4h"}),
}

# Extra tag_slugs to fetch alongside the primary mapped slug (UI sub → related API tags).
# Short crypto: only the exclusive timeframe slug — never "up-or-down" (pollutes all buckets).
CRYPTO_EXTRA_SLUGS: dict[str, list[str]] = {
    "5 min": ["5m"],
    "15 min": ["15m"],
    "hourly": ["1h"],
    "4 hour": ["4h"],
    "daily": ["daily", "crypto-prices"],
    "weekly": ["weekly"],
    "monthly": ["monthly"],
}

SPORTS_SLUG_MAP = {
    "ucl": "champions-league",
    "footbal": "soccer",
    "football": "soccer",
    "basketbal": "basketball",
    "formula 1": "f1",
    "hockey": "nhl",
    "baseball": "mlb",
}

ESPORTS_SLUG_MAP = {
    "league of legend": "league-of-legends",
    "cs2": "cs2",
    "rainbow six siege": "rainbow-six",
    "starcraft ii": "starcraft-2",
    "mobile legends: bang bang": "mobile-legends",
    "honor of kings": "honor-of-kings",
    "call of duty": "call-of-duty",
}

CRYPTO_TAGS = {
    "crypto", "prices", "crypto-prices", "bitcoin", "ethereum", "solana",
    "xrp", "dogecoin", "up-or-down", "recurring",
    "5m", "15m", "1h", "4h", "1d", "1w", "1mo",
    "daily", "weekly", "monthly", "pre-market", "etf",
}
SPORTS_TAGS = {
    "sports", "soccer", "basketball", "tennis", "mma",
    "nfl", "mlb", "nhl", "f1", "champions-league", "sport",
}
ESPORTS_TAGS = {
    "esports", "dota-2", "dota 2", "csgo", "cs2", "counter-strike",
    "counter-strike-2", "counter strike 2", "counter stike 2",
    "valorant", "league-of-legends", "league of legends", "lol",
    "starcraft-2", "rainbow-six", "call-of-duty",
    "mobile-legends", "honor-of-kings",
}
OTHERS_TAGS = {"politics", "pop-culture", "business", "science"}

# Subcategory → normalized tokens that may appear in tag slug/label or title
SUBCATEGORY_ALIASES: dict[str, list[str]] = {
    "ucl": ["champions league", "champions-league"],
    "footbal": ["football", "soccer"],
    "football": ["soccer"],
    "cs2": [
        "csgo", "cs2", "cs 2",
        "counter-strike", "counter strike",
        "counter-strike-2", "counter strike 2",
        "counter-stike-2", "counter stike 2",
    ],
    "league of legend": ["league of legends", "lol", "league-of-legends"],
    "dota 2": ["dota", "dota-2", "dota 2"],
    "starcraft ii": ["starcraft", "starcraft-2", "sc2"],
    "rainbow six siege": ["rainbow six", "rainbow-six", "r6"],
    "mobile legends: bang bang": ["mobile legends", "mobile-legends"],
    "honor of kings": ["honor of kings", "honor-of-kings"],
    "call of duty": ["call of duty", "call-of-duty"],
    "formula 1": ["f1", "formula 1"],
    "5 min": ["5m", "5 min", "5-min", "5 minute"],
    "15 min": ["15m", "15 min", "15-min", "15 minute"],
    "hourly": ["1h", "1 h", "hourly", "1 hour", "1-hour"],
    "4 hour": ["4h", "4 h", "4 hour", "4-hour", "4hr"],
    "daily": ["daily", "1d", "1 day"],
    "weekly": ["weekly", "1w", "1 week"],
    "monthly": ["monthly", "1mo", "1 month"],
}

# Pool of tags polled by the background cache refresher
CACHE_POOL_SLUGS: list[str | None] = [
    None,
    "crypto", "bitcoin", "ethereum", "solana", "xrp", "dogecoin",
    "crypto-prices", "up-or-down", "prices",
    "5m", "15m", "1h", "4h", "daily", "weekly", "monthly", "pre-market",
    "sports", "soccer", "basketball", "tennis", "mma", "nfl", "mlb", "nhl", "f1", "champions-league",
    "esports", "dota-2", "cs2", "counter-strike", "counter-strike-2",
    "valorant", "league-of-legends", "starcraft-2", "rainbow-six", "call-of-duty",
    "politics", "business",
]

GENERIC_SUBS = frozenset({"all", "live", "starting soon"})


def get_slugs_for_request(category: str, subcategory: str) -> list[str | None]:
    """Map UI category/subcategory to Polymarket tag_slug values."""
    sub = subcategory.lower()
    cat = category.lower()

    if cat in ("most_traded", "live"):
        return [None]

    if cat == "crypto":
        if sub == "all":
            return [
                "crypto", "bitcoin", "ethereum", "solana", "xrp",
                "crypto-prices", "up-or-down", "5m", "15m", "1h", "4h",
            ]
        if sub in CRYPTO_EXTRA_SLUGS:
            return list(CRYPTO_EXTRA_SLUGS[sub])
        mapped = CRYPTO_SLUG_MAP.get(sub, sub.replace(" ", "-"))
        return [mapped]

    if cat == "sports":
        if sub in GENERIC_SUBS:
            return ["sports", "soccer", "basketball", "tennis"]
        return [SPORTS_SLUG_MAP.get(sub, sub.replace(" ", "-"))]

    if cat == "esports":
        if sub in GENERIC_SUBS:
            return ["esports", "dota-2", "cs2", "counter-strike-2", "counter-strike"]
        mapped = ESPORTS_SLUG_MAP.get(sub, sub.replace(" ", "-"))
        if mapped == "cs2":
            return ["cs2", "counter-strike-2", "counter-strike", "csgo"]
        return [mapped]

    if cat == "others":
        if sub == "all":
            return ["politics", "pop-culture", "business", "science"]
        return [sub.replace(" ", "-")]

    return [None]
