"""Filter and normalize Polymarket Gamma events for the UI."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from src.core.mappings import (
    CRYPTO_TAGS,
    CRYPTO_TIMEFRAME_TAGS,
    ESPORTS_TAGS,
    OTHERS_TAGS,
    SPORTS_TAGS,
    SUBCATEGORY_ALIASES,
    GENERIC_SUBS,
)
from src.utils.json_parse import safe_parse

# Short crypto windows that should not show after resolution
_CRYPTO_SHORT_SUBS = frozenset({"5 min", "15 min", "hourly", "4 hour", "daily"})

# Polymarket-style live buckets: only the current window (~7 assets)
_CRYPTO_LIVE_WINDOW_SUBS = frozenset(CRYPTO_TIMEFRAME_TAGS.keys())
_CRYPTO_LIVE_WINDOW_LIMIT = 7

# All exclusive timeframe tokens — used to reject cross-bucket leakage
_ALL_TIMEFRAME_TOKENS = frozenset().union(*CRYPTO_TIMEFRAME_TAGS.values()) if CRYPTO_TIMEFRAME_TAGS else frozenset()


def _parse_event_time(date_str: str | None) -> datetime | None:
    if not date_str:
        return None
    raw = str(date_str).strip()
    try:
        # "2026-03-10 11:40:00+00" → normalize
        normalized = raw.replace(" ", "T", 1) if " " in raw and "T" not in raw else raw
        if normalized.endswith("+00"):
            normalized = normalized[:-3] + "+00:00"
        if normalized.endswith("Z"):
            cleaned = normalized[:-1]
            return datetime.strptime(cleaned.split(".")[0], "%Y-%m-%dT%H:%M:%S").replace(
                tzinfo=timezone.utc
            )
        if "+" in normalized[10:] or normalized.count("-") > 2:
            # has explicit offset
            return datetime.fromisoformat(normalized).astimezone(timezone.utc)
        cleaned = normalized.split(".")[0]
        return datetime.strptime(cleaned, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def _norm_tag(value: str) -> str:
    """Lowercase and collapse separators for loose tag comparisons."""
    return re.sub(r"[\s_]+", "-", (value or "").strip().lower())


def _tags_tokens(ev: dict) -> set[str]:
    """Collect normalized tag slugs + labels from an event."""
    tokens: set[str] = set()
    for t in ev.get("tags", []) or []:
        if isinstance(t, dict):
            for key in ("slug", "label"):
                val = t.get(key)
                if val:
                    raw = str(val).lower().strip()
                    tokens.add(raw)
                    tokens.add(_norm_tag(raw))
        else:
            raw = str(t).lower().strip()
            tokens.add(raw)
            tokens.add(_norm_tag(raw))
    return tokens


def _category_tag_match(category: str, tags: set[str]) -> bool:
    def has_any(pool: set[str]) -> bool:
        for p in pool:
            pn = _norm_tag(p)
            if p in tags or pn in tags:
                return True
        return False

    if category == "crypto":
        return has_any(CRYPTO_TAGS)
    if category == "sports":
        return has_any(SPORTS_TAGS)
    if category == "esports":
        return has_any(ESPORTS_TAGS)
    if category == "others":
        return has_any(OTHERS_TAGS)
    return True


def _token_in_text(token: str, text: str) -> bool:
    """Word-ish containment: token appears as substring in normalized text."""
    if not token:
        return False
    t = token.lower()
    if t in text:
        return True
    tn = _norm_tag(t)
    text_n = _norm_tag(text)
    return bool(tn) and tn in text_n


def _has_tag(tags: set[str], token: str) -> bool:
    if not token:
        return False
    t = token.lower()
    return t in tags or _norm_tag(t) in tags


def _crypto_timeframe_match(sub: str, tags: set[str]) -> bool | None:
    """
    Strict Polymarket-style bucket filter for 5m / 15m / 1h / 4h.
    Returns True/False when sub is a timeframe bucket, else None (use generic matching).
    """
    required = CRYPTO_TIMEFRAME_TAGS.get(sub)
    if required is None:
        return None

    has_required = any(_has_tag(tags, tok) for tok in required)
    if not has_required:
        return False

    # Reject events that also carry a *different* exclusive timeframe tag
    other_tfs = _ALL_TIMEFRAME_TOKENS - set(required)
    if any(_has_tag(tags, tok) for tok in other_tfs):
        # Prefer the most specific required match only; dual-tagged is rare — drop to be safe
        return False

    return True


def _subcategory_match(
    category: str,
    sub: str,
    target_slugs: list[str | None],
    tags: set[str],
    title_lower: str,
) -> bool:
    if sub in GENERIC_SUBS or category in ("most_traded", "live"):
        return True

    # Crypto short windows: exclusive tag only (never generic "up-or-down" / title heuristics)
    if category == "crypto":
        tf = _crypto_timeframe_match(sub, tags)
        if tf is not None:
            return tf

    # Direct slug hits from API request mapping
    for ts in target_slugs:
        if not ts:
            continue
        # Shared crypto tags must not act as subcategory keys
        if ts.lower() in ("up-or-down", "crypto", "crypto-prices", "prices", "recurring"):
            continue
        if _has_tag(tags, ts):
            return True

    # Aliases + raw subcategory against tags and title
    match_words = [sub, sub.replace(" ", "-"), _norm_tag(sub)]
    match_words += SUBCATEGORY_ALIASES.get(sub, [])
    for word in match_words:
        w = word.lower()
        if _has_tag(tags, w):
            return True
        if _token_in_text(w, title_lower):
            return True

    return False


def _pick_display_date(ev: dict) -> str | None:
    """Prefer actual event/game start over resolution endDate (often +hours later)."""
    for m in ev.get("markets") or []:
        for key in ("eventStartTime", "gameStartTime"):
            val = m.get(key)
            if val:
                return str(val)
    for key in ("gameStartTime", "eventDate"):
        val = ev.get(key)
        if val:
            # eventDate is often date-only; skip pure dates without time for display preference
            if key == "eventDate" and isinstance(val, str) and "T" not in val and " " not in val:
                continue
            return str(val)
    return ev.get("endDate") or ev.get("resolutionDate") or ev.get("startDate")


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

        # Only drop fully resolved / dead markets (was 0.01/0.99 — too aggressive for short crypto)
        if p_yes >= 0.995 or p_yes <= 0.005:
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


def _event_volume(ev: dict) -> float:
    try:
        return float(
            ev.get("volume24hr")
            or ev.get("volume_24hr")
            or ev.get("volumeNum")
            or ev.get("volume")
            or 0
        )
    except (TypeError, ValueError):
        return 0.0


def normalize_event(ev: dict) -> dict[str, Any] | None:
    """Convert a raw Gamma event into the UI payload shape, or None if untradeable."""
    sub_markets = _build_sub_markets(ev)
    if not sub_markets:
        return None

    target_date_str = _pick_display_date(ev)
    end_str = ev.get("endDate") or ev.get("resolutionDate")
    tags = _tags_tokens(ev)
    is_live = "live" in tags

    return {
        "event_id": ev.get("id"),
        "title": ev.get("title"),
        "image": ev.get("image"),
        "total_volume": _event_volume(ev),
        "start_date": target_date_str,
        "end_date": end_str,
        "is_live": is_live,
        "sub_markets": sub_markets,
    }


def _slot_key(dt: datetime) -> datetime:
    """Bucket window starts to the minute (align multi-asset slots)."""
    return dt.replace(second=0, microsecond=0)


def _select_live_crypto_window(
    events: list[dict[str, Any]],
    now: datetime,
    limit: int = _CRYPTO_LIVE_WINDOW_LIMIT,
) -> list[dict[str, Any]]:
    """
    Like Polymarket crypto 5m/15m/1h/4h: only assets for the single current
    (or next imminent) time window — typically ~7 markets, not the full history.
    """
    if not events:
        return []

    enriched: list[tuple[dict[str, Any], datetime, datetime | None]] = []
    for e in events:
        start = _parse_event_time(e.get("start_date"))
        end = _parse_event_time(e.get("end_date"))
        if not start:
            continue
        # Drop resolved windows
        if end and end <= now:
            continue
        # Without endDate, treat as expired if start is far in the past
        if not end and start < now - timedelta(hours=2):
            continue
        enriched.append((e, start, end))

    if not enriched:
        return []

    # Currently trading: started and not yet ended
    in_progress = [
        (e, s, en)
        for e, s, en in enriched
        if s <= now and (en is None or en > now)
    ]

    if in_progress:
        # Latest slot that already started = the active window
        window_key = max(_slot_key(s) for _, s, _ in in_progress)
        bucket = [e for e, s, _ in in_progress if _slot_key(s) == window_key]
    else:
        # Nothing live yet — take the nearest upcoming window only
        upcoming = [(e, s, en) for e, s, en in enriched if s > now]
        if not upcoming:
            return []
        window_key = min(_slot_key(s) for _, s, _ in upcoming)
        bucket = [e for e, s, _ in upcoming if _slot_key(s) == window_key]

    bucket.sort(key=lambda x: x.get("total_volume") or 0, reverse=True)
    return bucket[:limit]


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
    seen_ids: set[str] = set()

    for ev in raw_data:
        eid = str(ev.get("id", ""))
        if eid and eid in seen_ids:
            continue

        tags = _tags_tokens(ev)
        title_lower = (ev.get("title") or "").lower()

        if not _category_tag_match(cat, tags):
            continue

        if not _subcategory_match(cat, sub, target_slugs, tags, title_lower):
            continue

        target_date_str = _pick_display_date(ev)
        end_time = _parse_event_time(ev.get("endDate"))
        is_live = "live" in tags
        target_time = _parse_event_time(target_date_str)

        # Short crypto: drop anything already ended (strict — window selector does the rest)
        if cat == "crypto" and sub in _CRYPTO_LIVE_WINDOW_SUBS:
            expiry = end_time or target_time
            if expiry and expiry <= now:
                continue
        elif cat == "crypto" and sub in _CRYPTO_SHORT_SUBS:
            expiry = end_time or target_time
            if expiry and expiry < now - timedelta(minutes=15):
                continue

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

        normalized = normalize_event(ev)
        if not normalized:
            continue
        normalized["is_live"] = is_live or normalized["is_live"]

        if eid:
            seen_ids.add(eid)
        events.append(normalized)

    # Polymarket 5m/15m/1h/4h: only the current time-window's assets (~7)
    if cat == "crypto" and sub in _CRYPTO_LIVE_WINDOW_SUBS:
        return _select_live_crypto_window(events, now)

    events.sort(key=lambda x: x["total_volume"], reverse=True)
    return events


def search_events(raw_data: list[dict], query: str, limit: int = 20) -> list[dict[str, Any]]:
    """Title search over cached Gamma events for the UI search bar."""
    q = (query or "").strip().lower()
    if not q:
        return []

    now = datetime.now(timezone.utc)
    hits: list[dict[str, Any]] = []
    seen: set[str] = set()

    for ev in raw_data:
        title = (ev.get("title") or "")
        if q not in title.lower():
            continue
        eid = str(ev.get("id", ""))
        if eid and eid in seen:
            continue

        # Skip long-expired events
        end_t = _parse_event_time(ev.get("endDate"))
        if end_t and end_t < now - timedelta(days=1):
            continue

        normalized = normalize_event(ev)
        if not normalized:
            continue
        if eid:
            seen.add(eid)
        hits.append(normalized)

    hits.sort(key=lambda x: x["total_volume"], reverse=True)
    return hits[:limit]
