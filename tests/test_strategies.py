"""Strategy presets: Fix relative TP / resolve + SL radar exclusion."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.api.trade import resolve_strategy_levels


class TestResolveStrategyLevels:
    def test_fix_relative_offset(self) -> None:
        # entry 0.40 + 0.12 (+12¢) → 0.52; SL disabled
        tp, sl = resolve_strategy_levels("fix", 0.40, 0.12, 0.30)
        assert tp == 0.52
        assert sl is None

    def test_fix_caps_at_0_99(self) -> None:
        # entry 0.95 + 0.12 → would be 1.07 → hard-capped at 0.99
        tp, sl = resolve_strategy_levels("fix", 0.95, 0.12, None)
        assert tp == 0.99
        assert sl is None

    def test_fix_exact_1_0_caps(self) -> None:
        # entry 0.90 + 0.10 → 1.00 → capped at 0.99
        tp, sl = resolve_strategy_levels("fix", 0.90, 0.10, None)
        assert tp == 0.99
        assert sl is None

    def test_fix_without_tp(self) -> None:
        tp, sl = resolve_strategy_levels("fix", 0.40, None, 0.20)
        assert tp is None
        assert sl is None

    def test_fix_zero_or_negative_offset(self) -> None:
        assert resolve_strategy_levels("fix", 0.40, 0.0, None) == (None, None)
        assert resolve_strategy_levels("fix", 0.40, -0.05, None) == (None, None)

    def test_draft_win_no_levels(self) -> None:
        assert resolve_strategy_levels("draft_win", 0.50, 0.60, 0.40) == (None, None)

    def test_short_range(self) -> None:
        assert resolve_strategy_levels("short_range", 0.50, None, None) == (0.54, 0.44)

    def test_high_range(self) -> None:
        assert resolve_strategy_levels("high_range", 0.50, None, None) == (0.56, 0.42)

    def test_unknown_all_in_half_falls_through_to_custom(self) -> None:
        # all_in_half removed — treated as custom/legacy (honours request TP/SL)
        tp, sl = resolve_strategy_levels("all_in_half", 0.50, 0.70, 0.20)
        assert tp == 0.70
        assert sl == 0.20

    def test_no_draft_early_preset(self) -> None:
        # draft_early must not exist as a special-cased strategy
        tp, sl = resolve_strategy_levels("draft_early", 0.50, 0.55, 0.40)
        # Falls through to custom: honours request TP/SL
        assert tp == 0.55
        assert sl == 0.40


class TestFixStrategyOrder:
    def _patch_order_deps(self, mocker):
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

    def test_fix_relative_tp_stored(
        self,
        client,
        mock_clob_client: MagicMock,
        mocker,
    ) -> None:
        """take_profit_price=0.12 means +12¢ → TP at entry+0.12, capped ≤0.99."""
        self._patch_order_deps(mocker)

        saved = {}

        class _FakeDB:
            def add(self, pos, *_a, **_k):
                saved["tp_price"] = pos.tp_price
                saved["sl_trigger_price"] = pos.sl_trigger_price
                saved["strategy"] = pos.strategy

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
                "/api/order",
                json={
                    "token_id": "tok-fix-rel",
                    "condition_id": "cond-fix-rel",
                    "price": 0.40,
                    "side": "BUY",
                    "bankroll": 15.0,
                    "risk_percent": 100,
                    "strategy": "fix",
                    "take_profit_price": 0.12,  # +12¢ offset
                },
            )
            assert resp.status_code == 200
            assert resp.json().get("success") is True
            assert saved["tp_price"] == 0.52
            assert saved["sl_trigger_price"] is None
            assert saved["strategy"] == "fix"
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_fix_relative_tp_ceiling(
        self,
        client,
        mock_clob_client: MagicMock,
        mocker,
    ) -> None:
        self._patch_order_deps(mocker)

        saved = {}

        class _FakeDB:
            def add(self, pos, *_a, **_k):
                saved["tp_price"] = pos.tp_price

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
                "/api/order",
                json={
                    "token_id": "tok-fix-cap",
                    "condition_id": "cond-fix-cap",
                    "price": 0.95,
                    "side": "BUY",
                    "bankroll": 15.0,
                    "risk_percent": 100,
                    "strategy": "fix",
                    "take_profit_price": 0.12,  # 0.95+0.12 → cap 0.99
                },
            )
            assert resp.status_code == 200
            assert resp.json().get("success") is True
            assert saved["tp_price"] == 0.99
        finally:
            app.dependency_overrides.pop(get_db, None)


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

    def test_resolve_not_found(self, client, mocker) -> None:
        query = MagicMock()
        query.filter.return_value.first.return_value = None
        fake_db = MagicMock()
        fake_db.query.return_value = query

        from src.database.db import get_db
        from src.main import app

        def _override():
            yield fake_db

        app.dependency_overrides[get_db] = _override
        try:
            resp = client.post(
                "/api/positions/missing-id/resolve",
                json={"exit_price": 1.0},
            )
            assert resp.status_code == 200
            assert resp.json()["success"] is False
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_resolve_rejects_already_closed(self, client, mocker) -> None:
        pos = MagicMock()
        pos.order_id = "ord-closed"
        pos.status = "CLOSED_TP"
        pos.tp_order_id = None

        query = MagicMock()
        query.filter.return_value.first.return_value = pos
        fake_db = MagicMock()
        fake_db.query.return_value = query

        from src.database.db import get_db
        from src.main import app

        def _override():
            yield fake_db

        app.dependency_overrides[get_db] = _override
        try:
            resp = client.post(
                "/api/positions/ord-closed/resolve",
                json={"exit_price": 0.5},
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is False
            assert "already closed" in (body.get("error") or "").lower() or "status" in (
                body.get("error") or ""
            ).lower()
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_resolve_cancels_tp_legs(self, client, mocker) -> None:
        pos = MagicMock()
        pos.order_id = "ord-with-tp"
        pos.status = "OPEN"
        pos.entry_price = 0.40
        pos.tp_order_id = "tp-a,tp-b"
        pos.strategy = "fix"

        query = MagicMock()
        query.filter.return_value.first.return_value = pos
        fake_db = MagicMock()
        fake_db.query.return_value = query

        from src.database.db import get_db
        from src.main import app

        cancel = mocker.patch("src.api.trade.cancel_order", new=mocker.AsyncMock())

        def _override():
            yield fake_db

        app.dependency_overrides[get_db] = _override
        try:
            resp = client.post(
                "/api/positions/ord-with-tp/resolve",
                json={"exit_price": 0.0},
            )
            assert resp.status_code == 200
            assert resp.json()["success"] is True
            assert cancel.await_count == 2
            assert pos.exit_price == 0.0
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
