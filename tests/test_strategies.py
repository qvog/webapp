"""Strategy presets: Fix / All-In-Half / resolve + SL radar exclusion."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.api.trade import resolve_strategy_levels


class TestResolveStrategyLevels:
    def test_fix_uses_manual_tp_disables_sl(self) -> None:
        tp, sl = resolve_strategy_levels("fix", 0.40, 0.55, 0.30)
        assert tp == 0.55
        assert sl is None

    def test_fix_without_tp(self) -> None:
        tp, sl = resolve_strategy_levels("fix", 0.40, None, 0.20)
        assert tp is None
        assert sl is None

    def test_draft_win_no_levels(self) -> None:
        assert resolve_strategy_levels("draft_win", 0.50, 0.60, 0.40) == (None, None)

    def test_short_range(self) -> None:
        assert resolve_strategy_levels("short_range", 0.50, None, None) == (0.54, 0.44)

    def test_high_range(self) -> None:
        assert resolve_strategy_levels("high_range", 0.50, None, None) == (0.56, 0.42)

    def test_all_in_half_no_levels(self) -> None:
        assert resolve_strategy_levels("all_in_half", 0.50, 0.70, 0.20) == (None, None)

    def test_no_draft_early_preset(self) -> None:
        # draft_early must not exist as a special-cased strategy
        tp, sl = resolve_strategy_levels("draft_early", 0.50, 0.55, 0.40)
        # Falls through to custom: honours request TP/SL
        assert tp == 0.55
        assert sl == 0.40


class TestAllInHalfSizing:
    """ALL IN HALF invests exactly Volume/2 at the limit price."""

    def _payload(self, **overrides) -> dict:
        data = {
            "token_id": "tok-half",
            "condition_id": "cond-half",
            "price": 0.50,
            "side": "BUY",
            "bankroll": 20.0,  # Volume UI field
            "risk_percent": 100,
            "is_custom_limit": True,
            "strategy": "all_in_half",
        }
        data.update(overrides)
        return data

    def test_size_is_half_volume(
        self,
        client,
        mock_clob_client: MagicMock,
        mocker,
    ) -> None:
        mocker.patch("src.api.trade.setup_order_lifecycle", new=mocker.AsyncMock())
        mocker.patch("src.api.trade.token_sl_radar", new=mocker.AsyncMock())
        mocker.patch(
            "src.api.trade.get_neg_risk_options",
            new=mocker.AsyncMock(
                return_value=MagicMock(tick_size="0.01", neg_risk=False)
            ),
        )

        async def _run_sync(fn, *a, **k):
            return fn(*a, **k)

        mocker.patch("src.api.trade.run_sync", side_effect=_run_sync)

        class _FakeDB:
            def add(self, *_a, **_k):
                return None

            def commit(self):
                return None

            def rollback(self):
                return None

        from src.database.db import get_db
        from src.main import app

        def _override_db():
            yield _FakeDB()

        app.dependency_overrides[get_db] = _override_db
        try:
            # Volume $20 → invest $10 @ 0.50 → size 20.0 shares
            resp = client.post("/api/order", json=self._payload(bankroll=20.0, price=0.50))
            assert resp.status_code == 200
            assert resp.json().get("success") is True
            call_kwargs = mock_clob_client.create_and_post_order.call_args
            order_args = call_kwargs.kwargs.get("order_args") or call_kwargs.args[0]
            assert float(order_args.price) == 0.50
            assert float(order_args.size) == 20.0  # 10 / 0.50
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_limit_price_from_request_not_market(
        self,
        client,
        mock_clob_client: MagicMock,
        mocker,
    ) -> None:
        """Clicked order-book price must be used as a strict limit (e.g. 0.42)."""
        mocker.patch("src.api.trade.setup_order_lifecycle", new=mocker.AsyncMock())
        mocker.patch("src.api.trade.token_sl_radar", new=mocker.AsyncMock())
        mocker.patch(
            "src.api.trade.get_neg_risk_options",
            new=mocker.AsyncMock(
                return_value=MagicMock(tick_size="0.01", neg_risk=False)
            ),
        )

        async def _run_sync(fn, *a, **k):
            return fn(*a, **k)

        mocker.patch("src.api.trade.run_sync", side_effect=_run_sync)

        class _FakeDB:
            def add(self, *_a, **_k):
                return None

            def commit(self):
                return None

            def rollback(self):
                return None

        from src.database.db import get_db
        from src.main import app

        def _override_db():
            yield _FakeDB()

        app.dependency_overrides[get_db] = _override_db
        try:
            resp = client.post(
                "/api/order", json=self._payload(bankroll=10.0, price=0.42)
            )
            assert resp.status_code == 200
            assert resp.json().get("success") is True
            call_kwargs = mock_clob_client.create_and_post_order.call_args
            order_args = call_kwargs.kwargs.get("order_args") or call_kwargs.args[0]
            assert float(order_args.price) == 0.42
            # $10 / 2 = $5 invest → 5 / 0.42 ≈ 11.90 shares
            assert float(order_args.size) == round(5.0 / 0.42, 2)
        finally:
            app.dependency_overrides.pop(get_db, None)


class TestFixStrategyOrder:
    def test_fix_requires_tp(
        self,
        client,
        mock_clob_client: MagicMock,
        mocker,
    ) -> None:
        mocker.patch(
            "src.api.trade.get_neg_risk_options",
            new=mocker.AsyncMock(
                return_value=MagicMock(tick_size="0.01", neg_risk=False)
            ),
        )
        resp = client.post(
            "/api/order",
            json={
                "token_id": "tok-fix",
                "condition_id": "cond-fix",
                "price": 0.40,
                "side": "BUY",
                "bankroll": 15.0,
                "risk_percent": 100,
                "strategy": "fix",
                "take_profit_price": None,
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("success") is False
        assert "Take Profit" in (body.get("error") or "")
        mock_clob_client.create_and_post_order.assert_not_called()


class TestManualResolve:
    def test_resolve_sets_status_and_exit(self, client, mocker) -> None:
        pos = MagicMock()
        pos.order_id = "ord-resolve-1"
        pos.status = "OPEN"
        pos.entry_price = 0.45
        pos.tp_order_id = None
        pos.strategy = "short_range"

        query = MagicMock()
        query.filter.return_value.first.return_value = pos

        fake_db = MagicMock()
        fake_db.query.return_value = query

        from src.database.db import get_db
        from src.main import app

        mocker.patch("src.api.trade.cancel_order", new=mocker.AsyncMock())

        def _override():
            yield fake_db

        app.dependency_overrides[get_db] = _override
        try:
            resp = client.post(
                "/api/positions/ord-resolve-1/resolve",
                json={"exit_price": 1.0},
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert body["status"] == "RESOLVED"
            assert body["exit_price"] == 1.0
            assert pos.status == "RESOLVED"
            assert pos.exit_price == 1.0
            fake_db.commit.assert_called()
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_resolve_drop_at_entry(self, client, mocker) -> None:
        pos = MagicMock()
        pos.order_id = "ord-drop"
        pos.status = "OPEN"
        pos.entry_price = 0.33
        pos.tp_order_id = None
        pos.strategy = "fix"

        query = MagicMock()
        query.filter.return_value.first.return_value = pos
        fake_db = MagicMock()
        fake_db.query.return_value = query

        from src.database.db import get_db
        from src.main import app

        mocker.patch("src.api.trade.cancel_order", new=mocker.AsyncMock())

        def _override():
            yield fake_db

        app.dependency_overrides[get_db] = _override
        try:
            resp = client.post(
                "/api/positions/ord-drop/resolve",
                json={"exit_price": 0.33},
            )
            assert resp.status_code == 200
            assert resp.json()["success"] is True
            assert pos.exit_price == 0.33
            assert pos.status == "RESOLVED"
        finally:
            app.dependency_overrides.pop(get_db, None)


class TestFixExcludedFromSlRadar:
    def test_get_open_sl_positions_skips_fix(self, mocker) -> None:
        from src.workers import monitor

        fix_pos = MagicMock()
        fix_pos.order_id = "fix-1"
        fix_pos.sl_trigger_price = 0.30  # even if set by mistake
        fix_pos.size = 10.0
        fix_pos.strategy = "fix"
        fix_pos.tp_order_id = "tp-1"

        custom_pos = MagicMock()
        custom_pos.order_id = "custom-1"
        custom_pos.sl_trigger_price = 0.40
        custom_pos.size = 5.0
        custom_pos.strategy = "short_range"
        custom_pos.tp_order_id = "tp-2"

        db = MagicMock()
        q = MagicMock()
        q.filter.return_value.all.return_value = [fix_pos, custom_pos]
        db.query.return_value = q

        # Patch db_session context manager
        class _Ctx:
            def __enter__(self):
                return db

            def __exit__(self, *a):
                return False

        mocker.patch.object(monitor, "db_session", return_value=_Ctx())
        rows = monitor._get_open_sl_positions("tok-x")
        assert len(rows) == 1
        assert rows[0]["order_id"] == "custom-1"
        assert rows[0]["strategy"] == "short_range"
