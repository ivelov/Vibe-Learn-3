"""Structured output schemas for the LLM chat engine.

These Pydantic models define the JSON contract the LLM must respond with, and
are also used as the ``response_format`` passed to LiteLLM for structured output.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TradeAction(BaseModel):
    """A single trade the LLM wants to execute on the user's behalf."""

    ticker: str = Field(description="Stock ticker symbol, e.g. AAPL")
    side: Literal["buy", "sell"] = Field(description="buy or sell")
    quantity: float = Field(gt=0, description="Number of shares (fractional allowed)")


class WatchlistChange(BaseModel):
    """A single watchlist modification the LLM wants to make."""

    ticker: str = Field(description="Stock ticker symbol")
    action: Literal["add", "remove"] = Field(description="add or remove from watchlist")


class ChatResponse(BaseModel):
    """The complete structured response returned by the LLM for a chat turn."""

    message: str = Field(description="Conversational response shown to the user")
    trades: list[TradeAction] = Field(
        default_factory=list, description="Trades to auto-execute"
    )
    watchlist_changes: list[WatchlistChange] = Field(
        default_factory=list, description="Watchlist changes to apply"
    )
