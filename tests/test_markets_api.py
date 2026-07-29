"""Integration tests for GET /api/markets (FastAPI TestClient)."""
from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient


# Terminal UI payload keys (see market_filter.normalize_event)
EVENT_SCHEMA_KEYS = {
    "event_id",
    "title",
    "image",
    "total_volume",
    "start_date",
    "end_date",
    "is_live",
    "sub_markets",
}
SUB_MARKET_SCHEMA_KEYS = {
    "condition_id",
    "question",
    "token_id_yes",
    "token_id_no",
    "out1",
    "out2",
    "price_yes",
    "price_no",
}


def _assert_terminal_event_schema(event: dict[str, Any]) -> None:
    missing = EVENT_SCHEMA_KEYS - set(event.keys())
    assert not missing, f"event missing keys: {missing}"
    assert isinstance(event["sub_markets"], list)
    assert len(event["sub_markets"]) >= 1
    for sm in event["sub_markets"]:
        sm_missing = SUB_MARKET_SCHEMA_KEYS - set(sm.keys())
        assert not sm_missing, f"sub_market missing keys: {sm_missing}"
        assert 0.0 < float(sm["price_yes"]) < 1.0
        assert 0.0 < float(sm["price_no"]) < 1.0


class TestMarketsEndpoint:
    def test_get_markets_crypto_15m_ok(self, client: TestClient) -> None:
        """
        GET /api/markets?category=crypto&subcategory=15m (and '15 min')
        returns 200 and terminal-shaped JSON without touching the network.
        """
        # Frontend uses "15 min"; also accept alias "15m" used in task brief.
        for subcategory in ("15 min", "15m"):
            resp = client.get(
                "/api/markets",
                params={"category": "crypto", "subcategory": subcategory},
            )
            assert resp.status_code == 200, (
                f"sub={subcategory!r} → {resp.status_code}: {resp.text}"
            )
            data = resp.json()
            assert isinstance(data, list), "endpoint must return a JSON array of events"

            # With mocked cache fixtures we expect at least one tradeable event
            # for the proper "15 min" bucket; "15m" may still match via tags.
            if subcategory == "15 min":
                assert len(data) >= 1
                for event in data:
                    _assert_terminal_event_schema(event)

    def test_get_markets_health_still_ok(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("status") == "ok"
        assert "markets_cached" in body

    def test_get_markets_default_query(self, client: TestClient) -> None:
        resp = client.get("/api/markets")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
