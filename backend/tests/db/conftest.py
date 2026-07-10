"""Shared fixtures for database tests."""

from __future__ import annotations

import pytest

from app.db import DbManager


@pytest.fixture
def db_path(tmp_path):
    """Path to a throwaway SQLite file inside the test's temp dir."""
    return tmp_path / "test_finally.db"


@pytest.fixture
async def manager(db_path):
    """An initialized DbManager backed by a temp database."""
    mgr = DbManager(db_path)
    await mgr.init_db()
    return mgr


class FakePriceCache:
    """Minimal price source stub for portfolio valuation tests."""

    def __init__(self, prices: dict[str, float] | None = None) -> None:
        self._prices = prices or {}

    def set(self, ticker: str, price: float) -> None:
        self._prices[ticker.upper()] = price

    def get_price(self, ticker: str) -> float | None:
        return self._prices.get(ticker.upper())
