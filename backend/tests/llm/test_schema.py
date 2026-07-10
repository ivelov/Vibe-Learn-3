"""Tests for the LLM structured-output schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.llm import ChatResponse, TradeAction, WatchlistChange


def test_chat_response_parses_valid_json():
    raw = '{"message": "Hello", "trades": [], "watchlist_changes": []}'
    resp = ChatResponse.model_validate_json(raw)
    assert resp.message == "Hello"
    assert resp.trades == []
    assert resp.watchlist_changes == []


def test_chat_response_defaults_are_empty():
    resp = ChatResponse(message="hi")
    assert resp.trades == []
    assert resp.watchlist_changes == []


def test_chat_response_parses_nested_actions():
    raw = (
        '{"message": "Buying", '
        '"trades": [{"ticker": "AAPL", "side": "buy", "quantity": 10}], '
        '"watchlist_changes": [{"ticker": "PYPL", "action": "add"}]}'
    )
    resp = ChatResponse.model_validate_json(raw)
    assert len(resp.trades) == 1
    assert resp.trades[0].ticker == "AAPL"
    assert resp.trades[0].side == "buy"
    assert resp.trades[0].quantity == 10
    assert resp.watchlist_changes[0].action == "add"


def test_chat_response_validates_fields():
    with pytest.raises(ValidationError):
        ChatResponse.model_validate(
            {"message": "x", "trades": [{"ticker": "AAPL", "side": "hold", "quantity": 1}]}
        )


def test_trade_action_validation():
    with pytest.raises(ValidationError):
        TradeAction(ticker="AAPL", side="hold", quantity=1)


def test_trade_action_rejects_non_positive_quantity():
    with pytest.raises(ValidationError):
        TradeAction(ticker="AAPL", side="buy", quantity=0)


def test_watchlist_change_validates_action():
    with pytest.raises(ValidationError):
        WatchlistChange(ticker="AAPL", action="delete")

    ok = WatchlistChange(ticker="AAPL", action="remove")
    assert ok.action == "remove"
