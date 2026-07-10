"""Tests for PortfolioService and ChatService business logic."""

from __future__ import annotations

import pytest

from app.db import ChatService, PortfolioService, WatchlistService

from .conftest import FakePriceCache


async def test_portfolio_service_pnl_calculation(manager):
    prices = FakePriceCache({"AAPL": 200.0})
    service = PortfolioService(manager, price_cache=prices)

    # Buy 10 AAPL @ 190 -> avg cost 190, current price 200.
    result = await service.execute_trade("default", "AAPL", "buy", 10, 190.0)
    assert result.success

    view = await service.get_portfolio("default")
    assert view.cash_balance == pytest.approx(10000.0 - 1900.0)

    pos = next(p for p in view.positions if p.ticker == "AAPL")
    assert pos.current_price == 200.0
    assert pos.market_value == pytest.approx(2000.0)
    assert pos.unrealized_pnl == pytest.approx(100.0)  # (200-190)*10
    assert pos.pnl_pct == pytest.approx(100.0 / 1900.0 * 100.0)

    assert view.total_unrealized_pnl == pytest.approx(100.0)
    assert view.total_value == pytest.approx(8100.0 + 2000.0)


async def test_buy_updates_cash_and_position(manager):
    service = PortfolioService(manager, price_cache=FakePriceCache())
    result = await service.execute_trade("default", "MSFT", "buy", 2, 400.0)

    assert result.success
    assert result.cash_balance == pytest.approx(10000.0 - 800.0)
    assert result.position is not None
    assert result.position.quantity == 2
    assert result.position.avg_cost == 400.0


async def test_buy_averages_cost(manager):
    service = PortfolioService(manager, price_cache=FakePriceCache())
    await service.execute_trade("default", "NVDA", "buy", 10, 100.0)
    await service.execute_trade("default", "NVDA", "buy", 10, 200.0)

    view = await service.get_portfolio("default")
    pos = next(p for p in view.positions if p.ticker == "NVDA")
    assert pos.quantity == 20
    assert pos.avg_cost == pytest.approx(150.0)  # (10*100 + 10*200) / 20


async def test_buy_insufficient_cash_fails(manager):
    service = PortfolioService(manager, price_cache=FakePriceCache())
    result = await service.execute_trade("default", "AAPL", "buy", 1000, 190.0)

    assert not result.success
    assert "Insufficient cash" in result.message

    # Cash unchanged, no position created.
    view = await service.get_portfolio("default")
    assert view.cash_balance == 10000.0
    assert view.positions == []


async def test_sell_reduces_position(manager):
    service = PortfolioService(manager, price_cache=FakePriceCache())
    await service.execute_trade("default", "TSLA", "buy", 10, 250.0)
    result = await service.execute_trade("default", "TSLA", "sell", 4, 260.0)

    assert result.success
    assert result.position is not None
    assert result.position.quantity == 6
    # Cash: 10000 - 2500 (buy) + 1040 (sell) = 8540
    assert result.cash_balance == pytest.approx(8540.0)


async def test_sell_entire_position_removes_it(manager):
    service = PortfolioService(manager, price_cache=FakePriceCache())
    await service.execute_trade("default", "META", "buy", 3, 500.0)
    result = await service.execute_trade("default", "META", "sell", 3, 520.0)

    assert result.success
    assert result.position is None
    view = await service.get_portfolio("default")
    assert all(p.ticker != "META" for p in view.positions)


async def test_sell_more_than_held_fails(manager):
    service = PortfolioService(manager, price_cache=FakePriceCache())
    await service.execute_trade("default", "V", "buy", 2, 280.0)
    result = await service.execute_trade("default", "V", "sell", 5, 290.0)

    assert not result.success
    assert "Insufficient shares" in result.message


async def test_invalid_side_and_quantity(manager):
    service = PortfolioService(manager, price_cache=FakePriceCache())

    r1 = await service.execute_trade("default", "AAPL", "hold", 1, 190.0)
    assert not r1.success

    r2 = await service.execute_trade("default", "AAPL", "buy", 0, 190.0)
    assert not r2.success

    r3 = await service.execute_trade("default", "AAPL", "buy", 1, 0.0)
    assert not r3.success


async def test_snapshot_and_history(manager):
    prices = FakePriceCache({"AAPL": 190.0})
    service = PortfolioService(manager, price_cache=prices)
    await service.execute_trade("default", "AAPL", "buy", 10, 190.0)

    snap = await service.record_snapshot("default")
    assert snap.total_value == pytest.approx(10000.0)  # cash 8100 + 1900 position

    prices.set("AAPL", 200.0)
    await service.record_snapshot("default")

    history = await service.get_history("default")
    assert len(history) == 2
    assert history[0].total_value == pytest.approx(10000.0)
    assert history[1].total_value == pytest.approx(10100.0)


async def test_get_portfolio_without_price_cache_uses_avg_cost(manager):
    # No price cache -> current price falls back to avg cost, P&L is zero.
    service = PortfolioService(manager, price_cache=None)
    await service.execute_trade("default", "AAPL", "buy", 5, 190.0)

    view = await service.get_portfolio("default")
    pos = next(p for p in view.positions if p.ticker == "AAPL")
    assert pos.current_price == 190.0
    assert pos.unrealized_pnl == pytest.approx(0.0)


async def test_chat_service(manager):
    service = ChatService(manager)
    await service.save_message("default", "user", "What should I buy?")
    await service.save_message(
        "default", "assistant", "Consider AAPL.", actions='{"trades": []}'
    )

    history = await service.get_history("default")
    assert len(history) == 2
    assert history[0].content == "What should I buy?"
    assert history[1].actions == '{"trades": []}'


async def test_watchlist_service(manager):
    service = WatchlistService(manager)

    # Seeded default watchlist has 10 tickers.
    initial = await service.get_watchlist("default")
    assert len(initial) == 10

    added = await service.add_ticker("pypl")
    assert added is not None and added.ticker == "PYPL"
    assert await service.ticker_exists("PYPL")

    dup = await service.add_ticker("PYPL")
    assert dup is None

    assert await service.remove_ticker("pypl") is True
    assert await service.remove_ticker("PYPL") is False


async def test_portfolio_view_to_dict(manager):
    service = PortfolioService(manager, price_cache=FakePriceCache({"AAPL": 200.0}))
    await service.execute_trade("default", "AAPL", "buy", 1, 190.0)

    view = await service.get_portfolio("default")
    data = view.to_dict()
    assert set(data.keys()) == {
        "cash_balance",
        "positions",
        "total_value",
        "total_unrealized_pnl",
    }
    assert data["positions"][0]["ticker"] == "AAPL"
