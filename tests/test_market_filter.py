"""Unit tests for crypto short-window market filtering (market_filter.py)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.services.market_filter import (
    _CRYPTO_LIVE_WINDOW_LIMIT,
    _select_live_crypto_window,
    filter_events,
    normalize_event,
)


def _iso(dt: datetime) -> str:
    """UTC ISO string with Z suffix (Gamma-style)."""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _make_15m_event(
    eid: str,
    *,
    start: datetime,
    end: datetime,
    volume: float = 1000.0,
    asset: str = "BTC",
    price_yes: float = 0.55,
) -> dict:
    """Build a Gamma-shaped crypto 15m event dict."""
    return {
        "id": eid,
        "title": f"{asset} Up or Down - 15 min window",
        "image": f"https://mock.cdn/{asset.lower()}.png",
        "volume24hr": volume,
        "endDate": _iso(end),
        "tags": [
            {"slug": "crypto", "label": "Crypto"},
            {"slug": "15m", "label": "15m"},
            {"slug": "crypto-prices", "label": "Crypto Prices"},
            {"slug": asset.lower(), "label": asset},
            {"slug": "up-or-down", "label": "Up or Down"},
        ],
        "markets": [
            {
                "conditionId": f"cond-{eid}",
                "question": f"Will {asset} go up?",
                "closed": "false",
                "eventStartTime": _iso(start),
                "outcomes": '["Yes", "No"]',
                "outcomePrices": f'["{price_yes}", "{1.0 - price_yes:.4f}"]',
                "clobTokenIds": f'["yes-{eid}", "no-{eid}"]',
            }
        ],
    }


def _build_20_fake_15m_markets(now: datetime) -> list[dict]:
    """
    20 fake 15m markets:
      - 5 completed in the past (ended before now; 4 of them >15m ago)
      - 2 active concurrent assets in the *current* 15m slot
      - 13 future windows with staggered endDate
    """
    events: list[dict] = []
    assets = ["BTC", "ETH", "SOL", "XRP", "DOGE", "ADA", "AVAX", "LINK", "DOT", "MATIC"]

    # --- 5 completed (past) ---
    # 4 older than 15 minutes (must be hard-dropped), 1 just-ended
    for i in range(4):
        end = now - timedelta(minutes=20 + i * 15)
        start = end - timedelta(minutes=15)
        events.append(
            _make_15m_event(
                f"past-old-{i}",
                start=start,
                end=end,
                volume=500 + i,
                asset=assets[i % len(assets)],
            )
        )
    # Most recent completed window (ended ~2 min ago)
    end_last = now - timedelta(minutes=2)
    start_last = end_last - timedelta(minutes=15)
    events.append(
        _make_15m_event(
            "past-last",
            start=start_last,
            end=end_last,
            volume=8000,
            asset="BTC",
        )
    )

    # --- 2 active in the *current* slot (same start minute) ---
    # Window: started 7 min ago, ends in 8 min
    active_start = now - timedelta(minutes=7)
    active_end = now + timedelta(minutes=8)
    for i, asset in enumerate(["BTC", "ETH"]):
        events.append(
            _make_15m_event(
                f"active-{i}",
                start=active_start,
                end=active_end,
                volume=50_000 - i * 1000,
                asset=asset,
            )
        )

    # --- 13 future markets (different upcoming slots) ---
    for i in range(13):
        # Next slots every 15 minutes starting after the current window
        start = active_end + timedelta(minutes=i * 15)
        end = start + timedelta(minutes=15)
        events.append(
            _make_15m_event(
                f"future-{i}",
                start=start,
                end=end,
                volume=1000 + i * 10,
                asset=assets[i % len(assets)],
            )
        )

    assert len(events) == 20
    return events


class TestCryptoSlidingWindowFilter:
    """Crypto 15m live-window selection (Polymarket-style ~7 assets)."""

    def test_crypto_sliding_window_filter(self) -> None:
        """
        filter_events for crypto / 15 min must:
          - drop resolved / past windows (including markets older than 15 min)
          - keep only the current active time-slot assets
          - cap the result at ~7 markets (_CRYPTO_LIVE_WINDOW_LIMIT)
        """
        now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        raw = _build_20_fake_15m_markets(now)

        # Extra assets in the *same* active slot so the limit-7 path is exercised
        active_start = now - timedelta(minutes=7)
        active_end = now + timedelta(minutes=8)
        for i, asset in enumerate(["SOL", "XRP", "DOGE", "ADA", "AVAX", "LINK", "DOT"]):
            raw.append(
                _make_15m_event(
                    f"active-extra-{i}",
                    start=active_start,
                    end=active_end,
                    volume=40_000 - i * 500,
                    asset=asset,
                )
            )

        result = filter_events(
            raw_data=raw,
            category="crypto",
            subcategory="15 min",
            target_slugs=["15m"],
        )

        # Strict cap: current live window only, max 7 concurrent assets
        assert len(result) == _CRYPTO_LIVE_WINDOW_LIMIT == 7

        result_ids = {str(e["event_id"]) for e in result}

        # Markets older than 15 minutes (past-old-*) must be gone
        for i in range(4):
            assert f"past-old-{i}" not in result_ids

        # Fully completed windows (end <= now) are excluded by live-window path
        assert "past-last" not in result_ids

        # Future slots are excluded while an in-progress window exists
        for i in range(13):
            assert f"future-{i}" not in result_ids

        # Only current-slot markets remain (active-* / active-extra-*)
        for eid in result_ids:
            assert eid.startswith("active-"), f"unexpected event in window: {eid}"

        # Highest volume first within the slot
        volumes = [e["total_volume"] for e in result]
        assert volumes == sorted(volumes, reverse=True)

        # Schema shape expected by the terminal UI
        for ev in result:
            assert "event_id" in ev
            assert "title" in ev
            assert "sub_markets" in ev
            assert isinstance(ev["sub_markets"], list)
            assert len(ev["sub_markets"]) >= 1
            sm = ev["sub_markets"][0]
            for key in (
                "condition_id",
                "token_id_yes",
                "token_id_no",
                "price_yes",
                "price_no",
            ):
                assert key in sm

    def test_past_windows_hard_cut_when_nothing_live(self) -> None:
        """If nothing is in progress, only the nearest *upcoming* slot is kept."""
        now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        events = []

        # Past only
        for i in range(3):
            end = now - timedelta(minutes=30 + i * 15)
            start = end - timedelta(minutes=15)
            events.append(
                _make_15m_event(f"only-past-{i}", start=start, end=end, volume=100)
            )

        # One future slot with 3 assets
        fut_start = now + timedelta(minutes=10)
        fut_end = fut_start + timedelta(minutes=15)
        for i, asset in enumerate(["BTC", "ETH", "SOL"]):
            events.append(
                _make_15m_event(
                    f"soon-{i}",
                    start=fut_start,
                    end=fut_end,
                    volume=9000 - i,
                    asset=asset,
                )
            )

        # Later future slot (must NOT leak in)
        later_start = fut_end + timedelta(minutes=15)
        later_end = later_start + timedelta(minutes=15)
        events.append(
            _make_15m_event(
                "later",
                start=later_start,
                end=later_end,
                volume=99_999,
                asset="XRP",
            )
        )

        result = filter_events(events, "crypto", "15 min", ["15m"])
        ids = {str(e["event_id"]) for e in result}

        assert "later" not in ids
        assert all(i.startswith("soon-") for i in ids)
        assert len(result) == 3

    def test_select_live_crypto_window_limit(self) -> None:
        """Direct unit test of the window selector + volume ranking."""
        now = datetime.now(timezone.utc)
        start = now - timedelta(minutes=3)
        end = now + timedelta(minutes=12)

        normalized = []
        for i in range(10):
            raw = _make_15m_event(
                f"vol-{i}",
                start=start,
                end=end,
                volume=float(i * 100),
                asset=f"A{i}",
            )
            n = normalize_event(raw)
            assert n is not None
            normalized.append(n)

        window = _select_live_crypto_window(normalized, now, limit=7)
        assert len(window) == 7
        # Top 7 by volume: vol-9 … vol-3
        assert [e["event_id"] for e in window] == [f"vol-{i}" for i in range(9, 2, -1)]
