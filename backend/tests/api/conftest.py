"""Shared fixtures/fakes for API router tests.

These tests exercise the routers in isolation: a fresh FastAPI app with only the
routers mounted and mock services set on ``app.state``. No market/DB/LLM layers
are imported, so the suite runs with just fastapi + pydantic + httpx. This keeps
the API contract tests fast and decoupled from the other subsystems.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import chat, health, portfolio, watchlist


class FakeConnCtx:
    """Async context manager standing in for ``db_manager.connect()``."""

    async def __aenter__(self) -> object:
        return object()

    async def __aexit__(self, *exc: Any) -> bool:
        return False


class FakeDbManager:
    def connect(self) -> FakeConnCtx:
        return FakeConnCtx()


class FakePriceCache:
    """Minimal PriceCache stand-in: ``get_price`` + ``get`` (PriceUpdate-like)."""

    def __init__(self, prices: dict[str, float] | None = None) -> None:
        self._prices = prices or {}

    def get_price(self, ticker: str) -> float | None:
        return self._prices.get(ticker)

    def get(self, ticker: str) -> SimpleNamespace | None:
        price = self._prices.get(ticker)
        if price is None:
            return None
        return SimpleNamespace(
            ticker=ticker,
            price=price,
            previous_price=price,
            change=0.0,
            change_percent=0.0,
            direction="flat",
        )


def make_app(**state: Any) -> FastAPI:
    """Build a router-only app with the given ``app.state`` attributes."""
    app = FastAPI()
    app.include_router(health.router)
    app.include_router(portfolio.router)
    app.include_router(watchlist.router)
    app.include_router(chat.router)
    for key, value in state.items():
        setattr(app.state, key, value)
    return app


@pytest.fixture
def price_cache() -> FakePriceCache:
    return FakePriceCache({"AAPL": 190.0, "GOOGL": 175.0, "TSLA": 250.0})


@pytest.fixture
def db_manager() -> FakeDbManager:
    return FakeDbManager()


def client_for(app: FastAPI) -> TestClient:
    return TestClient(app)
