"""
Global test fixtures — network isolation and Polymarket client stubs.

CRITICAL SAFETY: no test may hit real Polymarket / Gamma endpoints or use
production private keys. All outbound HTTP and CLOB client calls are mocked.
"""
from __future__ import annotations

import os
from typing import Any, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest

# Ensure no real credentials leak into the process under test.
# Values are disposable fakes — never real Polymarket keys.
os.environ["POLY_PRIVATE_KEY"] = "0x" + "11" * 32
os.environ["POLY_FUNDER_ADDRESS"] = "0x" + "22" * 20
os.environ["POLY_API_KEY"] = "test-api-key"
os.environ["POLY_API_SECRET"] = "test-api-secret"
os.environ["POLY_API_PASSPHRASE"] = "test-passphrase"
os.environ["POLY_HOST"] = "https://mock-clob.test"
os.environ["POLY_PROXY"] = ""


class NetworkBlockedError(RuntimeError):
    """Raised when a test accidentally attempts a real network call."""


def _block_network(*_args: Any, **_kwargs: Any) -> None:
    raise NetworkBlockedError(
        "Real network access is blocked in tests. "
        "Mock httpx/requests or use fixtures from conftest.py."
    )


def _is_testclient_url(url: Any) -> bool:
    """Starlette/FastAPI TestClient talks to http://testserver in-process."""
    s = str(url)
    return "testserver" in s or s.startswith("/")


@pytest.fixture(autouse=True)
def isolate_from_network(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """
    Autouse fixture: block real outbound HTTP via httpx and requests.

    FastAPI TestClient uses httpx.Client against host ``testserver`` with an
    ASGI transport — those in-process calls are allowed. Everything else is
    blocked so tests never touch Polymarket / Gamma / the public internet.
    """
    import httpx

    _orig_client_request = httpx.Client.request
    _orig_client_send = httpx.Client.send

    def _guarded_client_request(self, method, url, *args, **kwargs):  # noqa: ANN001
        # Prefer allowing ASGI / TestClient transports regardless of URL form.
        transport = getattr(self, "_transport", None)
        if transport is None:
            transport = getattr(self, "transport", None)
        tname = type(transport).__name__ if transport is not None else ""
        if tname in ("ASGITransport", "WSGITransport") or _is_testclient_url(url):
            return _orig_client_request(self, method, url, *args, **kwargs)
        raise NetworkBlockedError(
            f"Blocked outbound httpx.Client request: {method} {url}"
        )

    def _guarded_client_send(self, request, *args, **kwargs):  # noqa: ANN001
        transport = getattr(self, "_transport", None)
        if transport is None:
            transport = getattr(self, "transport", None)
        tname = type(transport).__name__ if transport is not None else ""
        url = getattr(request, "url", "")
        if tname in ("ASGITransport", "WSGITransport") or _is_testclient_url(url):
            return _orig_client_send(self, request, *args, **kwargs)
        raise NetworkBlockedError(f"Blocked outbound httpx.Client send: {url}")

    monkeypatch.setattr(httpx.Client, "request", _guarded_client_request)
    monkeypatch.setattr(httpx.Client, "send", _guarded_client_send)

    # Top-level helpers always go to the real network — block them.
    for name in ("get", "post", "put", "patch", "delete", "head", "request", "stream"):
        if hasattr(httpx, name):
            monkeypatch.setattr(httpx, name, _block_network)

    # --- httpx AsyncClient (market_cache / Gamma) — always block ---
    async def _async_block(*_a: Any, **_k: Any) -> None:
        _block_network()

    monkeypatch.setattr(httpx.AsyncClient, "request", _async_block)
    monkeypatch.setattr(httpx.AsyncClient, "send", _async_block)
    monkeypatch.setattr(httpx.AsyncClient, "get", _async_block)
    monkeypatch.setattr(httpx.AsyncClient, "post", _async_block)

    # --- requests (CLOB / py_clob_client_v2 paths) ---
    try:
        import requests  # noqa: F401

        monkeypatch.setattr("requests.sessions.Session.request", _block_network)
        monkeypatch.setattr("requests.api.request", _block_network)
        monkeypatch.setattr("requests.get", _block_network)
        monkeypatch.setattr("requests.post", _block_network)
    except ImportError:
        pass

    yield


def _build_mock_clob_client() -> MagicMock:
    """Factory for a virtual py_clob_client_v2 ClobClient."""
    client = MagicMock(name="MockClobClient")
    client.get_neg_risk.return_value = False
    client.create_and_post_order.return_value = {
        "orderID": "mock-order-001",
        "status": "LIVE",
    }
    client.get_order.return_value = {
        "id": "mock-order-001",
        "status": "LIVE",
        "size_matched": 0,
    }
    client.get_order_book.return_value = {
        "bids": [{"price": "0.45", "size": "100"}],
        "asks": [{"price": "0.55", "size": "100"}],
    }
    client.cancel.return_value = True
    client.cancel_order.return_value = True
    client.cancel_market_orders.return_value = True
    client.set_api_creds.return_value = None
    return client


@pytest.fixture(autouse=True)
def stub_py_clob_client(monkeypatch: pytest.MonkeyPatch) -> Generator[MagicMock, None, None]:
    """
    Autouse: replace py_clob_client_v2 / get_clob_client with virtual stubs.

    No test path may construct a real ClobClient or hit Polymarket CLOB.
    """
    client = _build_mock_clob_client()

    # Null out any pre-existing singleton before tests.
    try:
        import src.api.client as client_mod

        monkeypatch.setattr(client_mod, "_clob_client", None)
        monkeypatch.setattr(client_mod, "ClobClient", MagicMock(return_value=client))
        monkeypatch.setattr(client_mod, "get_clob_client", lambda: client)
    except Exception:
        pass

    for target in (
        "src.api.trade.get_clob_client",
        "src.services.orders.get_clob_client",
        "src.main.get_clob_client",
    ):
        try:
            monkeypatch.setattr(target, lambda: client)
        except Exception:
            pass

    yield client


@pytest.fixture
def mock_clob_client(stub_py_clob_client: MagicMock) -> MagicMock:
    """Explicit alias for tests that need to assert on CLOB call history."""
    stub_py_clob_client.reset_mock()
    # Re-apply default return values after reset_mock clears them.
    stub_py_clob_client.get_neg_risk.return_value = False
    stub_py_clob_client.create_and_post_order.return_value = {
        "orderID": "mock-order-001",
        "status": "LIVE",
    }
    stub_py_clob_client.get_order.return_value = {
        "id": "mock-order-001",
        "status": "LIVE",
        "size_matched": 0,
    }
    stub_py_clob_client.get_order_book.return_value = {
        "bids": [{"price": "0.45", "size": "100"}],
        "asks": [{"price": "0.55", "size": "100"}],
    }
    return stub_py_clob_client


@pytest.fixture
def sample_crypto_15m_events() -> list[dict]:
    """Minimal Gamma-shaped events for markets API integration tests."""
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    start = now - timedelta(minutes=5)
    end = now + timedelta(minutes=10)
    events = []
    for i in range(3):
        events.append(
            {
                "id": f"evt-api-{i}",
                "title": f"BTC Up or Down 15m #{i}",
                "image": f"https://mock.cdn/img/{i}.png",
                "volume24hr": 10_000 - i * 100,
                "endDate": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "tags": [
                    {"slug": "crypto", "label": "Crypto"},
                    {"slug": "15m", "label": "15m"},
                    {"slug": "bitcoin", "label": "Bitcoin"},
                ],
                "markets": [
                    {
                        "conditionId": f"cond-api-{i}",
                        "question": f"Will BTC go up? #{i}",
                        "closed": "false",
                        "eventStartTime": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "outcomes": '["Yes", "No"]',
                        "outcomePrices": '["0.52", "0.48"]',
                        "clobTokenIds": f'["yes-api-{i}", "no-api-{i}"]',
                    }
                ],
            }
        )
    return events


@pytest.fixture
def client(mock_clob_client: MagicMock, sample_crypto_15m_events: list[dict], mocker):
    """
    FastAPI TestClient with lifespan side-effects disabled and cache mocked.

    Uses httpx.ASGITransport so the request stays in-process (no real sockets).
    """
    from contextlib import asynccontextmanager

    from fastapi.testclient import TestClient

    # Stub market cache so /api/markets never fetches Gamma.
    async def fake_fetch(slugs, limit=100):
        return list(sample_crypto_15m_events)

    mocker.patch(
        "src.services.market_cache.market_cache.fetch_specific_slugs",
        side_effect=fake_fetch,
    )
    mocker.patch(
        "src.services.market_cache.market_cache.values",
        return_value=list(sample_crypto_15m_events),
    )
    mocker.patch(
        "src.services.market_cache.market_cache.ensure_background_updater",
        return_value=None,
    )
    mocker.patch(
        "src.services.market_cache.market_cache.close",
        new_callable=AsyncMock,
    )
    # Seed in-memory cache so size / values stay consistent without network.
    market_cache_mod = __import__(
        "src.services.market_cache", fromlist=["market_cache"]
    )
    market_cache_mod.market_cache._events = {
        str(ev["id"]): ev for ev in sample_crypto_15m_events
    }
    # Also patch names imported into the markets router module.
    mocker.patch(
        "src.api.markets.market_cache.fetch_specific_slugs",
        side_effect=fake_fetch,
    )
    mocker.patch(
        "src.api.markets.market_cache.values",
        return_value=list(sample_crypto_15m_events),
    )
    mocker.patch(
        "src.api.markets.market_cache.ensure_background_updater",
        return_value=None,
    )

    # Skip DB restore / real lifespan work on app startup.
    mocker.patch("src.main.restore_open_positions", new_callable=AsyncMock)

    @asynccontextmanager
    async def _noop_lifespan(app):
        yield

    mocker.patch("src.main.lifespan", _noop_lifespan)

    # Re-import app after patches where needed; lifespan is bound at creation.
    from src.main import app

    # Replace lifespan with no-op so TestClient context doesn't start workers.
    app.router.lifespan_context = _noop_lifespan

    with TestClient(app, raise_server_exceptions=True) as test_client:
        yield test_client
