"""Chat endpoint: converse with the FinAlly AI assistant.

Flow (PLAN.md section 9):
  1. Build context (portfolio, watchlist w/ live prices, recent history).
  2. Ask the LLM for a structured response {message, trades, watchlist_changes}.
  3. Auto-execute any trades and watchlist changes (errors captured, not fatal).
  4. Persist the user message and assistant response (with executed actions).
  5. Return the message plus per-action outcomes.

The LLM response may be a dict or a model; ``_field`` reads either. The engine's
``get_response`` is synchronous and blocking (it makes the OpenRouter HTTP call),
so it runs on a worker thread via ``asyncio.to_thread`` to keep the event loop —
and the SSE price stream — responsive.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.config import DEFAULT_USER_ID
from app.deps import (
    get_chat_engine,
    get_chat_service,
    get_db_manager,
    get_market_source,
    get_portfolio_service,
    get_price_cache,
    get_watchlist_repo,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])

RECENT_HISTORY_LIMIT = 20


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)


def _field(obj: Any, key: str, default: Any = None) -> Any:
    """Read ``key`` from a dict or attribute from an object."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


async def _gather_context(
    portfolio_service: Any,
    watchlist_repo: Any,
    chat_service: Any,
    db_manager: Any,
    price_cache: Any,
) -> tuple[dict, list[dict], list[dict]]:
    """Assemble the (portfolio, watchlist, history) context for the LLM engine.

    Shapes match what ``ChatEngine.get_response`` / ``build_user_message`` expect.
    """
    view = await portfolio_service.get_portfolio(DEFAULT_USER_ID)
    history = await chat_service.get_history(DEFAULT_USER_ID, RECENT_HISTORY_LIMIT)
    async with db_manager.connect() as conn:
        watch_items = await watchlist_repo.get_watchlist(conn, DEFAULT_USER_ID)

    portfolio_context = {
        "cash_balance": round(view.cash_balance, 2),
        "total_value": round(view.total_value, 2),
        "total_unrealized_pnl": round(view.total_unrealized_pnl, 2),
        "positions": [
            {
                "ticker": p.ticker,
                "quantity": p.quantity,
                "avg_cost": round(p.avg_cost, 4),
                "current_price": round(p.current_price, 2),
                "unrealized_pnl": round(p.unrealized_pnl, 2),
                "pnl_pct": round(p.pnl_pct, 2),
            }
            for p in view.positions
        ],
    }

    watchlist_context = []
    for item in watch_items:
        update = price_cache.get(item.ticker)
        watchlist_context.append(
            {
                "ticker": item.ticker,
                "price": update.price if update else None,
                "change_percent": update.change_percent if update else 0.0,
                "direction": update.direction if update else "flat",
            }
        )

    conversation_history = [{"role": m.role, "content": m.content} for m in history]
    return portfolio_context, watchlist_context, conversation_history


async def _execute_trades(
    trades: list[Any],
    portfolio_service: Any,
    price_cache: Any,
) -> list[dict]:
    results: list[dict] = []
    for t in trades:
        ticker = str(_field(t, "ticker", "")).strip().upper()
        side = _field(t, "side")
        quantity = _field(t, "quantity")
        if not ticker or side not in ("buy", "sell") or not quantity:
            results.append(
                {"ticker": ticker, "side": side, "quantity": quantity,
                 "success": False, "error": "Invalid trade instruction"}
            )
            continue
        price = price_cache.get_price(ticker)
        if price is None:
            results.append(
                {"ticker": ticker, "side": side, "quantity": quantity,
                 "success": False, "error": f"No live price for {ticker}"}
            )
            continue
        result = await portfolio_service.execute_trade(
            DEFAULT_USER_ID, ticker, side, float(quantity), price
        )
        entry = {"ticker": ticker, "side": side, "quantity": float(quantity),
                 "success": bool(result.success)}
        if not result.success:
            entry["error"] = result.message
        results.append(entry)
    return results


async def _apply_watchlist_changes(
    changes: list[Any],
    watchlist_repo: Any,
    db_manager: Any,
    market_source: Any,
) -> list[dict]:
    results: list[dict] = []
    for c in changes:
        ticker = str(_field(c, "ticker", "")).strip().upper()
        action = _field(c, "action")
        if not ticker or action not in ("add", "remove"):
            results.append({"ticker": ticker, "action": action, "success": False})
            continue
        async with db_manager.connect() as conn:
            if action == "add":
                changed = await watchlist_repo.add_ticker(conn, DEFAULT_USER_ID, ticker) is not None
            else:
                changed = await watchlist_repo.remove_ticker(conn, DEFAULT_USER_ID, ticker)
        if changed:
            if action == "add":
                await market_source.add_ticker(ticker)
            else:
                await market_source.remove_ticker(ticker)
        results.append({"ticker": ticker, "action": action, "success": bool(changed)})
    return results


@router.post("/chat")
async def chat(
    body: ChatRequest,
    chat_engine: Annotated[Any, Depends(get_chat_engine)],
    portfolio_service: Annotated[Any, Depends(get_portfolio_service)],
    watchlist_repo: Annotated[Any, Depends(get_watchlist_repo)],
    chat_service: Annotated[Any, Depends(get_chat_service)],
    market_source: Annotated[Any, Depends(get_market_source)],
    db_manager: Annotated[Any, Depends(get_db_manager)],
    price_cache: Annotated[Any, Depends(get_price_cache)],
) -> dict:
    portfolio_ctx, watchlist_ctx, history_ctx = await _gather_context(
        portfolio_service, watchlist_repo, chat_service, db_manager, price_cache
    )

    # ChatEngine.get_response is synchronous and blocking — run it off the event
    # loop. It is contractually non-raising, but we stay defensive at the boundary.
    try:
        raw = await asyncio.to_thread(
            chat_engine.get_response, portfolio_ctx, watchlist_ctx, history_ctx, body.message
        )
    except Exception:
        logger.exception("LLM call failed")
        return {
            "message": "Sorry, I ran into an error contacting the AI assistant. Please try again.",
            "trades": [],
            "watchlist_changes": [],
            "error": "llm_error",
        }

    reply = _field(raw, "message", "") or ""
    trades_in = _field(raw, "trades") or []
    changes_in = _field(raw, "watchlist_changes") or []

    trade_results = await _execute_trades(trades_in, portfolio_service, price_cache)
    change_results = await _apply_watchlist_changes(
        changes_in, watchlist_repo, db_manager, market_source
    )

    if any(r.get("success") for r in trade_results):
        try:
            await portfolio_service.record_snapshot(DEFAULT_USER_ID)
        except Exception:
            logger.exception("Post-chat snapshot failed")

    actions = {"trades": trade_results, "watchlist_changes": change_results}
    try:
        await chat_service.save_message(DEFAULT_USER_ID, "user", body.message, None)
        await chat_service.save_message(
            DEFAULT_USER_ID, "assistant", reply, json.dumps(actions)
        )
    except Exception:
        logger.exception("Saving chat messages failed")

    return {
        "message": reply,
        "trades": trade_results,
        "watchlist_changes": change_results,
        "error": None,
    }
