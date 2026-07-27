"""Category / slug / tag mappings for Polymarket market discovery."""
from __future__ import annotations

CRYPTO_SLUG_MAP = {
    "5 min": "5m",
    "15 min": "15m",
    "hourly": "1h",
    "4 hour": "4h",
    "daily": "1d",
    "weekly": "1w",
    "monthly": "1mo",
    "pre-market": "pre-market",
    "etf": "etf",
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

CRYPTO_TAGS = [
    "crypto", "prices", "bitcoin", "ethereum", "solana",
    "5m", "15m", "1h", "4h", "1d", "1w", "1mo",
]
SPORTS_TAGS = [
    "sports", "soccer", "basketball", "tennis", "mma",
    "nfl", "mlb", "nhl", "f1", "champions-league",
]
ESPORTS_TAGS = [
    "esports", "dota-2", "csgo", "cs2", "counter-strike", "valorant",
    "league-of-legends", "starcraft-2", "rainbow-six", "call-of-duty",
    "mobile-legends", "honor-of-kings",
]
OTHERS_TAGS = ["politics", "pop-culture", "business", "science"]

SUBCATEGORY_ALIASES: dict[str, list[str]] = {
    "ucl": ["champions league", "champions-league"],
    "footbal": ["football", "soccer"],
    "football": ["soccer"],
    "cs2": ["csgo", "counter-strike", "cs2"],
    "league of legend": ["league of legends", "lol", "league-of-legends"],
    "dota 2": ["dota", "dota-2"],
    "starcraft ii": ["starcraft", "starcraft-2", "sc2"],
    "rainbow six siege": ["rainbow six", "rainbow-six", "r6"],
    "mobile legends: bang bang": ["mobile legends", "mobile-legends"],
    "honor of kings": ["honor of kings", "honor-of-kings"],
    "call of duty": ["call of duty", "call-of-duty"],
    "formula 1": ["f1", "formula 1"],
}

# Pool of tags polled by the background cache refresher
CACHE_POOL_SLUGS: list[str | None] = [
    None,
    "crypto", "bitcoin", "ethereum", "solana", "prices", "5m", "15m", "1h", "4h", "1d",
    "sports", "soccer", "basketball", "tennis", "mma", "nfl", "mlb", "nhl", "f1", "champions-league",
    "esports", "dota-2", "cs2", "csgo", "counter-strike", "valorant", "league-of-legends",
    "starcraft-2", "rainbow-six", "call-of-duty",
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
            return ["crypto", "bitcoin", "ethereum", "solana", "prices"]
        return [CRYPTO_SLUG_MAP.get(sub, sub.replace(" ", "-"))]

    if cat == "sports":
        if sub in GENERIC_SUBS:
            return ["sports", "soccer", "basketball", "tennis"]
        return [SPORTS_SLUG_MAP.get(sub, sub.replace(" ", "-"))]

    if cat == "esports":
        if sub in GENERIC_SUBS:
            return ["esports", "dota-2", "cs2", "csgo"]
        mapped = ESPORTS_SLUG_MAP.get(sub, sub.replace(" ", "-"))
        if mapped == "cs2":
            return ["cs2", "csgo", "counter-strike"]
        return [mapped]

    if cat == "others":
        if sub == "all":
            return ["politics", "pop-culture", "business", "science"]
        return [sub.replace(" ", "-")]

    return [None]
