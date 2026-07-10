"""Tests for the ChatEngine (mock mode + response parsing)."""

from __future__ import annotations

from app.llm import ChatEngine, ChatResponse

PORTFOLIO = {"cash_balance": 10000.0, "total_value": 10000.0, "positions": []}
WATCHLIST = [{"ticker": "AAPL", "price": 195.0, "direction": "up", "change_percent": 0.5}]


def _engine() -> ChatEngine:
    return ChatEngine(api_key="test-key", mock=True)


def test_mock_response_returns_valid_chat_response():
    resp = _engine().get_response(PORTFOLIO, WATCHLIST, [], "How is my portfolio?")
    assert isinstance(resp, ChatResponse)
    assert isinstance(resp.message, str)
    assert resp.message
    assert resp.trades == []
    assert resp.watchlist_changes == []


def test_mock_response_is_deterministic():
    e1 = _engine()
    e2 = _engine()
    msgs1 = [e1.get_response(PORTFOLIO, WATCHLIST, [], "analyze").message for _ in range(3)]
    msgs2 = [e2.get_response(PORTFOLIO, WATCHLIST, [], "analyze").message for _ in range(3)]
    assert msgs1 == msgs2


def test_mock_response_rotates_canned_messages():
    e = _engine()
    first = e.get_response(PORTFOLIO, WATCHLIST, [], "analyze").message
    second = e.get_response(PORTFOLIO, WATCHLIST, [], "analyze").message
    assert first != second


def test_mock_detects_buy_trade():
    resp = _engine().get_response(PORTFOLIO, WATCHLIST, [], "Please buy 10 AAPL")
    assert len(resp.trades) == 1
    assert resp.trades[0].side == "buy"
    assert resp.trades[0].ticker == "AAPL"
    assert resp.trades[0].quantity == 10


def test_mock_detects_sell_trade_with_fractional_quantity():
    resp = _engine().get_response(PORTFOLIO, WATCHLIST, [], "sell 2.5 shares of TSLA now")
    assert len(resp.trades) == 1
    assert resp.trades[0].side == "sell"
    assert resp.trades[0].ticker == "TSLA"
    assert resp.trades[0].quantity == 2.5


def test_mock_detects_watchlist_add():
    resp = _engine().get_response(PORTFOLIO, WATCHLIST, [], "add PYPL to my watchlist")
    assert len(resp.watchlist_changes) == 1
    assert resp.watchlist_changes[0].action == "add"
    assert resp.watchlist_changes[0].ticker == "PYPL"


def test_parse_response_handles_plain_json():
    engine = ChatEngine(api_key="x", mock=False)
    resp = engine._parse_response('{"message": "ok", "trades": [], "watchlist_changes": []}')
    assert resp.message == "ok"


def test_parse_response_extracts_json_from_wrapping_text():
    engine = ChatEngine(api_key="x", mock=False)
    content = 'Sure! ```json\n{"message": "hi", "trades": []}\n``` hope that helps'
    resp = engine._parse_response(content)
    assert resp.message == "hi"


def test_parse_response_empty_content_is_graceful():
    engine = ChatEngine(api_key="x", mock=False)
    resp = engine._parse_response("")
    assert isinstance(resp, ChatResponse)
    assert resp.message


def test_parse_response_unparseable_content_is_graceful():
    engine = ChatEngine(api_key="x", mock=False)
    resp = engine._parse_response("this is not json at all")
    assert isinstance(resp, ChatResponse)
    assert resp.message
