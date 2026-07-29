"""Unit & API tests for risk guards on limit orders (orders.py / trade.py)."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from src.api.trade import TradeRequest
from src.services.orders import (
    MAX_LIMIT_PRICE,
    MIN_LIMIT_PRICE,
    validate_limit_price,
)


class TestValidateLimitPrice:
    """Pure unit tests for the shared price band guard."""

    @pytest.mark.parametrize("price", [0.01, 0.5, 0.99, 0.0100001, 0.9899])
    def test_accepts_in_band(self, price: float) -> None:
        assert validate_limit_price(price) == float(price)

    @pytest.mark.parametrize("price", [0.0, 0.009, -0.01, 1.0, 0.991, 1.5, 100])
    def test_rejects_out_of_band(self, price: float) -> None:
        with pytest.raises(ValueError, match="диапазона|range|вне"):
            validate_limit_price(price)

    def test_rejects_non_numeric(self) -> None:
        with pytest.raises(ValueError):
            validate_limit_price("not-a-price")  # type: ignore[arg-type]


class TestTradeRequestValidation:
    """Pydantic model must refuse limit prices outside [0.01, 0.99]."""

    def _base(self, **overrides):
        data = {
            "token_id": "tok-yes-1",
            "condition_id": "cond-1",
            "price": 0.50,
            "side": "BUY",
            "bankroll": 20.0,
            "risk_percent": 100,
            "is_custom_limit": True,
            "strategy": "custom",
        }
        data.update(overrides)
        return data

    def test_valid_price_builds(self) -> None:
        req = TradeRequest(**self._base(price=0.42))
        assert req.price == 0.42

    @pytest.mark.parametrize("price", [0.009, 0.0, 0.991, 1.0, -1])
    def test_invalid_price_raises(self, price: float) -> None:
        with pytest.raises(ValidationError):
            TradeRequest(**self._base(price=price))


class TestPlaceOrderPriceGuard:
    """HTTP-level: POST /api/order rejects out-of-band prices without posting."""

    def _payload(self, price: float) -> dict:
        return {
            "token_id": "tok-yes-test",
            "condition_id": "cond-test",
            "price": price,
            "side": "BUY",
            "bankroll": 25.0,
            "risk_percent": 100,
            "is_custom_limit": True,
            "strategy": "custom",
        }

    @pytest.mark.parametrize("price", [0.009, 0.0, 0.991, 1.0])
    def test_limit_order_out_of_band_rejected(
        self,
        client: TestClient,
        mock_clob_client: MagicMock,
        price: float,
    ) -> None:
        resp = client.post("/api/order", json=self._payload(price))
        # Pydantic / FastAPI validation → 422; never reaches CLOB
        assert resp.status_code == 422
        mock_clob_client.create_and_post_order.assert_not_called()

    def test_limit_order_in_band_reaches_client(
        self,
        client: TestClient,
        mock_clob_client: MagicMock,
        mocker,
    ) -> None:
        # Avoid real background monitor / DB side effects beyond commit path
        mocker.patch("src.api.trade.monitor_and_manage_position", new=mocker.AsyncMock())
        mocker.patch(
            "src.api.trade.get_neg_risk_options",
            new=mocker.AsyncMock(
                return_value=MagicMock(tick_size="0.01", neg_risk=False)
            ),
        )
        # run_sync should just call the mock client method directly
        async def _run_sync(fn, *a, **k):
            return fn(*a, **k)

        mocker.patch("src.api.trade.run_sync", side_effect=_run_sync)

        # Use in-memory-ish DB session stub so place_order can complete
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
            resp = client.post("/api/order", json=self._payload(0.55))
            assert resp.status_code == 200
            body = resp.json()
            assert body.get("success") is True
            assert body.get("order_id") == "mock-order-001"
            mock_clob_client.create_and_post_order.assert_called()
            # Price argument stayed inside the band
            call_kwargs = mock_clob_client.create_and_post_order.call_args
            order_args = call_kwargs.kwargs.get("order_args") or (
                call_kwargs.args[0] if call_kwargs.args else None
            )
            if order_args is not None and hasattr(order_args, "price"):
                assert MIN_LIMIT_PRICE <= float(order_args.price) <= MAX_LIMIT_PRICE
        finally:
            app.dependency_overrides.pop(get_db, None)
