"""Application configuration from environment."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _clean_env(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip().strip("'").strip('"')
    return cleaned or None


@dataclass(frozen=True)
class Settings:
    poly_host: str = os.getenv("POLY_HOST", "https://clob.polymarket.com")
    poly_chain_id: int = int(os.getenv("POLY_CHAIN_ID", "137"))
    poly_private_key: str | None = _clean_env(os.getenv("POLY_PRIVATE_KEY"))
    poly_funder_address: str | None = _clean_env(os.getenv("POLY_FUNDER_ADDRESS"))
    poly_api_key: str | None = _clean_env(os.getenv("POLY_API_KEY"))
    poly_api_secret: str | None = _clean_env(os.getenv("POLY_API_SECRET"))
    poly_api_passphrase: str | None = _clean_env(os.getenv("POLY_API_PASSPHRASE"))
    poly_proxy: str | None = _clean_env(os.getenv("POLY_PROXY"))
    builder_code: str = os.getenv(
        "BUILDER_CODE",
        "0x0000000000000000000000000000000000000000000000000000000000000000",
    )
    gamma_api_url: str = "https://gamma-api.polymarket.com/events"
    poly_ws_url: str = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
    market_cache_interval_sec: int = 15
    cors_origins: list[str] | None = None

    def __post_init__(self) -> None:
        # dataclasses with frozen=True can't assign normally; use object.__setattr__
        if self.cors_origins is None:
            object.__setattr__(self, "cors_origins", ["*"])


settings = Settings()
