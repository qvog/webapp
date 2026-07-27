"""Filter and normalize Polymarket Gamma events for the UI."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.core.mappings import (
    CRYPTO_TAGS,
    ESPORTS_TAGS,
    OTHERS_TAGS,
    SPORTS_TAGS,
    SUBCATEGORY_ALIASES,
    GENERIC_SUBS,
)
from src.utils.json_parse import safe_parse


def _parse_event_time(date_str: str | None) -> datetime | None:
    if not date_str:
        return None
    try:
        cleaned = date_str.split(".")[0].replace("Z", "")
        return datetime.strptime(cleaned, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def _tags_lower(ev: dict) -> list[str]:
    tags = []
    for t in ev.get("tags", []) or []:
        if isinstance(t, dict):
            tags.append(t.get("label", "").lower())
        else:
            tags.append(str(t).lower())
    return tags


def _category_tag_match(category: str, tags_lower: list[str]) -> bool:
    if category == "crypto":
        return any(t in tags_lower for t in CRYPTO_TAGS)
    if category == "sports":
        return any(t in tags_lower for t in SPORTS_TAGS)
    if category == "esports":
        return any(t in tags_lower for t in ESPORTS_TAGS)
    if category == "others":
        return any(t in tags_lower for t in OTHERS_TAGS)
    return True


def _subcategory_match(
    category: str,
    sub: str,
    target_slugs: list[str | None],
    tags_lower: list[str],
    title_lower: str,
) -> bool:
    if sub in GENERIC_SUBS or category in ("most_traded", "live"):
        return True

    has_match = any(ts and ts in tags_lower for ts in target_slugs)

    if not has_match:
        match_words = [sub, sub.replace(" ", "-")] + SUBCATEGORY_ALIASES.get(sub, [])
        for word in match_words:
            if word in title_lower or any(word in t for t in tags_lower):
                has_match = True
                break

    if category == "crypto" and ("min" in sub or "hour" in sub):
        num = sub.split()[0]
        if f"{num}m" not in title_lower and f"{num} min" not in title_lower and f"{num}h" not in title_lower:
            has_match = False

    return has_match


def _build_sub_markets(ev: dict) -> list[dict]:
    sub_markets = []
    for m in ev.get("markets", []) or []:
        if str(m.get("closed", "false")).lower() == "true":
            continue

        outcomes = safe_parse(m.get("outcomes", []))
        prices = safe_parse(m.get("outcomePrices", []))
        token_ids = safe_parse(m.get("clobTokenIds", []))

        if len(outcomes) < 2 or len(token_ids) < 2:
            continue

        try:
            p_yes = float(prices[0]) if prices else 0.5
            p_no = float(prices[1]) if len(prices) > 1 else 0.5
        except (TypeError, ValueError):
            p_yes, p_no = 0.5, 0.5

        if p_yes >= 0.99 or p_yes <= 0.01:
            continue

        sub_markets.append({
            "condition_id": str(m.get("conditionId", "")),
            "question": m.get("question", ev.get("title", "Unknown")),
            "token_id_yes": str(token_ids[0]),
            "token_id_no": str(token_ids[1]),
            "out1": str(outcomes[0]).upper(),
            "out2": str(outcomes[1]).upper(),
            "price_yes": p_yes,
            "price_no": p_no,
        })
    return sub_markets


def filter_events(
    raw_data: list[dict],
    category: str,
    subcategory: str,
    target_slugs: list[str | None],
) -> list[dict[str, Any]]:
    """Filter Gamma events into the UI payload shape."""
    sub = subcategory.lower()
    cat = category.lower()
    events: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)

    for ev in raw_data:
        target_date_str = ev.get("endDate") or ev.get("resolutionDate") or ev.get("startDate")
        tags_lower = _tags_lower(ev)
        title_lower = (ev.get("title") or "").lower()

        if not _category_tag_match(cat, tags_lower):
            continue

        if not _subcategory_match(cat, sub, target_slugs, tags_lower, title_lower):
            continue

        is_live = "live" in tags_lower
        target_time = _parse_event_time(target_date_str)
        if target_time and cat in ("sports", "esports", "live"):
            diff_seconds = (target_time - now).total_seconds()
            if -14400 <= diff_seconds <= 7200:
                is_live = True
            if cat in ("sports", "esports") and diff_seconds < -7 * 86400:
                continue

        if cat == "live" and not is_live:
            continue
        if sub == "live" and not is_live:
            continue

        sub_markets = _build_sub_markets(ev)
        if not sub_markets:
            continue

        try:
            total_volume = float(
                ev.get("volume_24hr") or ev.get("volumeNum") or ev.get("volume") or 0
            )
        except (TypeError, ValueError):
            total_volume = 0.0

        events.append({
            "event_id": ev.get("id"),
            "title": ev.get("title"),
            "image": ev.get("image"),
            "total_volume": total_volume,
            "start_date": target_date_str,
            "is_live": is_live,
            "sub_markets": sub_markets,
        })

    events.sort(key=lambda x: x["total_volume"], reverse=True)
    return events
