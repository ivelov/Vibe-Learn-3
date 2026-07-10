"""Tests for the portfolio router."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from tests.api.conftest import client_for, make_app


def _view() -> SimpleNamespace:
    return SimpleNamespace(
        cash_balance=8115.0,
        positions=[
            SimpleNamespace(
                ticker="AAPL",
                quantity=10,
                avg_cost=185.0,
                current_price=190.5,
                market_value=1905.0,
                unrealized_pnl=55.0,
                pnl_pct=2.9729,
            )
        ],
        total_value=10020.0,
        total_unrealized_pnl=55.0,
    )


def test_portfolio_returns_positions(price_cache):
    service = MagicMock()
    service.get_portfolio = AsyncMock(return_value=_view())
    app = make_app(portfolio_service=service, price_cache=price_cache)

    resp = client_for(app).get("/api/portfolio")

    assert resp.status_code == 200
    data = resp.json()
    assert data["cash_balance"] == 8115.0
    assert data["total_value"] == 10020.0
    assert len(data["positions"]) == 1
    pos = data["positions"][0]
    assert pos["ticker"] == "AAPL"
    assert pos["current_price"] == 190.5
    assert pos["pnl_pct"] == 2.97  # rounded to 2dp by the router


def test_trade_buy_success(price_cache):
    trade = SimpleNamespace(
        ticker="AAPL",
        side="buy",
        quantity=10,
        price=190.0,
        executed_at=datetime(2026, 7, 10, 12, 0, tzinfo=timezone.utc),
    )
    service = MagicMock()
    service.execute_trade = AsyncMock(
        return_value=SimpleNamespace(
            success=True, message="Bought 10 AAPL", trade=trade, cash_balance=8100.0
        )
    )
    service.record_snapshot = AsyncMock()
    app = make_app(portfolio_service=service, price_cache=price_cache)

    resp = client_for(app).post(
        "/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 10, "side": "buy"}
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["cash_balance"] == 8100.0
    assert data["trade"]["ticker"] == "AAPL"
    # Trade executed at the live cache price (190.0) and a snapshot recorded.
    service.execute_trade.assert_awaited_once()
    assert service.execute_trade.await_args.args[4] == 190.0
    service.record_snapshot.assert_awaited_once()


def test_trade_insufficient_cash(price_cache):
    service = MagicMock()
    service.execute_trade = AsyncMock(
        return_value=SimpleNamespace(
            success=False,
            message="Insufficient cash: buying 1000 AAPL costs $190,000.00 but only $8,100.00 available.",
            trade=None,
            cash_balance=None,
        )
    )
    service.record_snapshot = AsyncMock()
    app = make_app(portfolio_service=service, price_cache=price_cache)

    resp = client_for(app).post(
        "/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1000, "side": "buy"}
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert "Insufficient cash" in data["error"]
    service.record_snapshot.assert_not_awaited()


def test_trade_unknown_ticker_no_price(price_cache):
    service = MagicMock()
    service.execute_trade = AsyncMock()
    app = make_app(portfolio_service=service, price_cache=price_cache)

    resp = client_for(app).post(
        "/api/portfolio/trade", json={"ticker": "ZZZZ", "quantity": 1, "side": "buy"}
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert "No live price" in data["error"]
    service.execute_trade.assert_not_awaited()


def test_history_returns_snapshots():
    snapshots = [
        SimpleNamespace(total_value=10000.0, recorded_at=datetime(2026, 7, 10, 11, 0)),
        SimpleNamespace(total_value=10020.0, recorded_at=datetime(2026, 7, 10, 11, 30)),
    ]
    service = MagicMock()
    service.get_history = AsyncMock(return_value=snapshots)
    app = make_app(portfolio_service=service)

    resp = client_for(app).get("/api/portfolio/history?limit=100")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["total_value"] == 10000.0
    assert data[1]["total_value"] == 10020.0
    service.get_history.assert_awaited_once()


def test_portfolio_503_when_db_unavailable():
    app = make_app()  # no portfolio_service on state
    resp = client_for(app).get("/api/portfolio")
    assert resp.status_code == 503
