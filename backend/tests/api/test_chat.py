"""Tests for the chat router."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from tests.api.conftest import client_for, make_app


def _empty_view() -> SimpleNamespace:
    return SimpleNamespace(
        cash_balance=10000.0, total_value=10000.0, total_unrealized_pnl=0.0, positions=[]
    )


def _base_state(price_cache, db_manager, engine_response):
    portfolio_service = MagicMock()
    portfolio_service.get_portfolio = AsyncMock(return_value=_empty_view())
    portfolio_service.execute_trade = AsyncMock(
        return_value=SimpleNamespace(success=True, message="ok", trade=None, cash_balance=9050.0)
    )
    portfolio_service.record_snapshot = AsyncMock()

    chat_service = MagicMock()
    chat_service.get_history = AsyncMock(return_value=[])
    chat_service.save_message = AsyncMock()

    watchlist_repo = MagicMock()
    watchlist_repo.get_watchlist = AsyncMock(return_value=[])
    watchlist_repo.add_ticker = AsyncMock(return_value=SimpleNamespace(ticker="PYPL"))
    watchlist_repo.remove_ticker = AsyncMock(return_value=True)

    market_source = MagicMock()
    market_source.add_ticker = AsyncMock()
    market_source.remove_ticker = AsyncMock()

    engine = MagicMock()
    engine.get_response = MagicMock(return_value=engine_response)

    return {
        "chat_engine": engine,
        "portfolio_service": portfolio_service,
        "watchlist_repo": watchlist_repo,
        "chat_service": chat_service,
        "market_source": market_source,
        "db_manager": db_manager,
        "price_cache": price_cache,
    }


def test_chat_returns_response(price_cache, db_manager):
    state = _base_state(
        price_cache,
        db_manager,
        {"message": "Your portfolio looks healthy.", "trades": [], "watchlist_changes": []},
    )
    app = make_app(**state)

    resp = client_for(app).post("/api/chat", json={"message": "How am I doing?"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["message"] == "Your portfolio looks healthy."
    assert data["trades"] == []
    assert data["error"] is None
    # Both user + assistant messages persisted.
    assert state["chat_service"].save_message.await_count == 2


def test_chat_executes_trade(price_cache, db_manager):
    state = _base_state(
        price_cache,
        db_manager,
        {
            "message": "Buying 5 AAPL for you.",
            "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 5}],
            "watchlist_changes": [],
        },
    )
    app = make_app(**state)

    resp = client_for(app).post("/api/chat", json={"message": "Buy 5 AAPL"})

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["trades"]) == 1
    assert data["trades"][0]["success"] is True
    assert data["trades"][0]["ticker"] == "AAPL"
    state["portfolio_service"].execute_trade.assert_awaited_once()
    # A snapshot is recorded after a successful trade.
    state["portfolio_service"].record_snapshot.assert_awaited_once()


def test_chat_executes_watchlist_change(price_cache, db_manager):
    state = _base_state(
        price_cache,
        db_manager,
        {
            "message": "Added PYPL to your watchlist.",
            "trades": [],
            "watchlist_changes": [{"ticker": "PYPL", "action": "add"}],
        },
    )
    app = make_app(**state)

    resp = client_for(app).post("/api/chat", json={"message": "Watch PYPL"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["watchlist_changes"][0]["success"] is True
    state["market_source"].add_ticker.assert_awaited_once_with("PYPL")


def test_chat_handles_llm_error(price_cache, db_manager):
    state = _base_state(price_cache, db_manager, {})
    state["chat_engine"].get_response = MagicMock(side_effect=RuntimeError("boom"))
    app = make_app(**state)

    resp = client_for(app).post("/api/chat", json={"message": "hi"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["error"] == "llm_error"
    assert "error" in data["message"].lower()


def test_chat_503_when_llm_unavailable(price_cache, db_manager):
    # No chat_engine on state -> dependency raises 503.
    app = make_app(price_cache=price_cache, db_manager=db_manager)
    resp = client_for(app).post("/api/chat", json={"message": "hi"})
    assert resp.status_code == 503
