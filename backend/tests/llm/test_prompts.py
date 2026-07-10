"""Tests for prompt construction."""

from __future__ import annotations

from app.llm import build_system_prompt, build_user_message


def _sample_portfolio() -> dict:
    return {
        "cash_balance": 8500.0,
        "total_value": 10250.0,
        "positions": [
            {
                "ticker": "AAPL",
                "quantity": 10,
                "avg_cost": 190.0,
                "current_price": 195.0,
                "unrealized_pnl": 50.0,
                "pnl_pct": 2.63,
            }
        ],
    }


def _sample_watchlist() -> list[dict]:
    return [
        {"ticker": "TSLA", "price": 250.0, "direction": "up", "change_percent": 1.2},
        {"ticker": "NVDA", "price": 120.0, "direction": "down", "change_percent": -0.5},
    ]


def test_prompt_contains_portfolio_data():
    msg = build_user_message(_sample_portfolio(), _sample_watchlist(), [], "How am I doing?")
    assert "8,500.00" in msg
    assert "10,250.00" in msg
    assert "AAPL" in msg


def test_prompt_contains_watchlist():
    msg = build_user_message(_sample_portfolio(), _sample_watchlist(), [], "Anything interesting?")
    assert "TSLA" in msg
    assert "NVDA" in msg
    assert "WATCHLIST" in msg


def test_prompt_contains_new_message():
    msg = build_user_message(_sample_portfolio(), _sample_watchlist(), [], "Buy me some AAPL")
    assert "Buy me some AAPL" in msg


def test_prompt_includes_conversation_history():
    history = [
        {"role": "user", "content": "What's my cash?"},
        {"role": "assistant", "content": "You have $8,500."},
    ]
    msg = build_user_message(_sample_portfolio(), _sample_watchlist(), history, "Thanks")
    assert "CONVERSATION HISTORY" in msg
    assert "What's my cash?" in msg


def test_prompt_handles_empty_portfolio_gracefully():
    msg = build_user_message({}, [], [], "hi")
    assert "No open positions." in msg
    assert "$0.00" in msg


def test_build_system_prompt_contains_rules():
    prompt = build_system_prompt()
    assert "FinAlly" in prompt
    assert "JSON" in prompt
    # Key behavioral rules should be present.
    assert "watchlist" in prompt.lower()
    assert "trade" in prompt.lower()
