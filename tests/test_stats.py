"""Stats period filtering: rolling 24h / today alias (no calendar-day UTC bugs)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.api import stats as stats_mod


def _pos(
    *,
    updated_at: datetime | None,
    created_at: datetime | None = None,
    status: str = "CLOSED_TP",
    strategy: str = "custom",
    entry: float = 0.40,
    exit_: float = 0.50,
    size: float = 10.0,
    order_id: str = "ord-1",
    id_: int = 1,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=id_,
        order_id=order_id,
        token_id="tok-1",
        condition_id="cond-1",
        strategy=strategy,
        entry_price=entry,
        exit_price=exit_,
        size=size,
        status=status,
        created_at=created_at,
        updated_at=updated_at,
    )


class TestPeriodCutoff:
    def test_today_is_rolling_24h(self) -> None:
        before = datetime.now(timezone.utc)
        cutoff = stats_mod._period_cutoff("today")
        after = datetime.now(timezone.utc)
        assert cutoff is not None
        # Cutoff ≈ now - 24h (allow tiny clock skew from call timing)
        expected_lo = before - timedelta(hours=24) - timedelta(seconds=2)
        expected_hi = after - timedelta(hours=24) + timedelta(seconds=2)
        assert expected_lo <= cutoff <= expected_hi

    def test_24h_matches_today(self) -> None:
        c_today = stats_mod._period_cutoff("today")
        c_24h = stats_mod._period_cutoff("24h")
        assert c_today is not None and c_24h is not None
        assert abs((c_today - c_24h).total_seconds()) < 1.0

    def test_all_has_no_cutoff(self) -> None:
        assert stats_mod._period_cutoff("all") is None

    def test_normalize_accepts_today(self) -> None:
        assert stats_mod._normalize_period("today") == "today"
        assert stats_mod._normalize_period("TODAY") == "today"
        assert stats_mod._normalize_period("24h") == "24h"
        assert stats_mod._normalize_period("nope") == stats_mod.DEFAULT_PERIOD


class TestFilterByPeriod:
    def test_includes_recent_excludes_old(self) -> None:
        now = datetime.now(timezone.utc)
        recent = _pos(updated_at=now - timedelta(hours=2), id_=1, order_id="recent")
        old = _pos(updated_at=now - timedelta(hours=30), id_=2, order_id="old")
        out = stats_mod._filter_by_period([recent, old], "today")
        assert [p.order_id for p in out] == ["recent"]

    def test_includes_trade_just_inside_window(self) -> None:
        now = datetime.now(timezone.utc)
        edge = _pos(updated_at=now - timedelta(hours=23, minutes=50), id_=1)
        out = stats_mod._filter_by_period([edge], "24h")
        assert len(out) == 1

    def test_excludes_trade_just_outside_window(self) -> None:
        now = datetime.now(timezone.utc)
        outside = _pos(updated_at=now - timedelta(hours=24, minutes=5), id_=1)
        out = stats_mod._filter_by_period([outside], "today")
        assert out == []

    def test_naive_datetime_treated_as_utc(self) -> None:
        """SQLite often returns naive datetimes — must not drop them via tz mismatch."""
        now_utc = datetime.now(timezone.utc)
        # Store as naive UTC (no tzinfo) — classic SQLite round-trip
        naive_recent = (now_utc - timedelta(hours=1)).replace(tzinfo=None)
        pos = _pos(updated_at=naive_recent, id_=1, order_id="naive")
        out = stats_mod._filter_by_period([pos], "today")
        assert len(out) == 1
        assert out[0].order_id == "naive"

    def test_keeps_undated_rows(self) -> None:
        pos = _pos(updated_at=None, created_at=None, id_=9, order_id="undated")
        out = stats_mod._filter_by_period([pos], "today")
        assert len(out) == 1

    def test_falls_back_to_created_at(self) -> None:
        now = datetime.now(timezone.utc)
        pos = _pos(
            updated_at=None,
            created_at=now - timedelta(hours=3),
            id_=3,
            order_id="created-only",
        )
        out = stats_mod._filter_by_period([pos], "today")
        assert [p.order_id for p in out] == ["created-only"]

    def test_all_period_keeps_everything(self) -> None:
        now = datetime.now(timezone.utc)
        positions = [
            _pos(updated_at=now - timedelta(days=100), id_=1, order_id="ancient"),
            _pos(updated_at=now, id_=2, order_id="now"),
        ]
        out = stats_mod._filter_by_period(positions, "all")
        assert len(out) == 2


class TestStatsApiPeriod:
    """HTTP-level: /api/stats/summary respects rolling today/24h window."""

    def _override_closed(self, client, mocker, positions: list):
        """Stub DB query chain used by _load_closed_positions."""
        fake_db = MagicMock()
        # db.query(Position).filter(...).order_by(...).all()
        q = MagicMock()
        q.filter.return_value = q
        q.order_by.return_value = q
        q.all.return_value = positions
        fake_db.query.return_value = q

        from src.database.db import get_db
        from src.main import app

        def _override():
            yield fake_db

        app.dependency_overrides[get_db] = _override
        # Avoid Gamma enrichment network paths in history (summary doesn't need it)
        mocker.patch(
            "src.api.stats._build_token_meta_index_from_cache",
            return_value={},
        )
        return app

    def test_summary_today_filters_old(
        self, client, mocker
    ) -> None:
        now = datetime.now(timezone.utc)
        positions = [
            _pos(
                updated_at=now - timedelta(hours=1),
                id_=1,
                order_id="in-window",
                entry=0.40,
                exit_=0.50,
                size=10.0,
            ),
            _pos(
                updated_at=now - timedelta(days=3),
                id_=2,
                order_id="too-old",
                entry=0.40,
                exit_=0.60,
                size=10.0,
            ),
        ]
        app = self._override_closed(client, mocker, positions)
        try:
            resp = client.get("/api/stats/summary?period=today")
            assert resp.status_code == 200
            body = resp.json()
            assert body["period"] == "today"
            # Only the in-window trade: pnl = (0.50-0.40)*10 = 1.0
            assert body["overall"]["total_trades"] == 1
            assert body["overall"]["total_pnl"] == 1.0
        finally:
            from src.database.db import get_db

            app.dependency_overrides.pop(get_db, None)

    def test_summary_24h_alias(
        self, client, mocker
    ) -> None:
        now = datetime.now(timezone.utc)
        positions = [
            _pos(updated_at=now - timedelta(hours=5), id_=1, order_id="a"),
        ]
        app = self._override_closed(client, mocker, positions)
        try:
            resp = client.get("/api/stats/summary?period=24h")
            assert resp.status_code == 200
            assert resp.json()["overall"]["total_trades"] == 1
        finally:
            from src.database.db import get_db

            app.dependency_overrides.pop(get_db, None)
