"""Tests for the watchlist router."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from tests.api.conftest import client_for, make_app


def test_watchlist_returns_tickers(price_cache, db_manager):
    repo = MagicMock()
    repo.get_watchlist = AsyncMock(
        return_value=[SimpleNamespace(ticker="AAPL"), SimpleNamespace(ticker="GOOGL")]
    )
    app = make_app(watchlist_repo=repo, db_manager=db_manager, price_cache=price_cache)

    resp = client_for(app).get("/api/watchlist")

    assert resp.status_code == 200
    data = resp.json()
    assert [row["ticker"] for row in data] == ["AAPL", "GOOGL"]
    assert data[0]["price"] == 190.0
    assert data[0]["direction"] == "flat"


def test_watchlist_add_success(db_manager):
    repo = MagicMock()
    repo.add_ticker = AsyncMock(return_value=SimpleNamespace(ticker="TSLA"))
    market = MagicMock()
    market.add_ticker = AsyncMock()
    app = make_app(watchlist_repo=repo, db_manager=db_manager, market_source=market)

    resp = client_for(app).post("/api/watchlist", json={"ticker": "tsla"})

    assert resp.status_code == 200
    data = resp.json()
    assert data == {"ticker": "TSLA", "added": True}
    market.add_ticker.assert_awaited_once_with("TSLA")


def test_watchlist_add_duplicate(db_manager):
    repo = MagicMock()
    repo.add_ticker = AsyncMock(return_value=None)  # already exists
    market = MagicMock()
    market.add_ticker = AsyncMock()
    app = make_app(watchlist_repo=repo, db_manager=db_manager, market_source=market)

    resp = client_for(app).post("/api/watchlist", json={"ticker": "AAPL"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["added"] is False
    assert data["reason"] == "already exists"
    market.add_ticker.assert_not_awaited()


def test_watchlist_remove(db_manager):
    repo = MagicMock()
    repo.remove_ticker = AsyncMock(return_value=True)
    market = MagicMock()
    market.remove_ticker = AsyncMock()
    app = make_app(watchlist_repo=repo, db_manager=db_manager, market_source=market)

    resp = client_for(app).delete("/api/watchlist/AAPL")

    assert resp.status_code == 200
    data = resp.json()
    assert data == {"ticker": "AAPL", "removed": True}
    market.remove_ticker.assert_awaited_once_with("AAPL")


def test_watchlist_remove_absent(db_manager):
    repo = MagicMock()
    repo.remove_ticker = AsyncMock(return_value=False)
    market = MagicMock()
    market.remove_ticker = AsyncMock()
    app = make_app(watchlist_repo=repo, db_manager=db_manager, market_source=market)

    resp = client_for(app).delete("/api/watchlist/ZZZZ")

    assert resp.status_code == 200
    assert resp.json()["removed"] is False
    market.remove_ticker.assert_not_awaited()
