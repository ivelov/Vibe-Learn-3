"""Watchlist endpoints: list tickers with live prices, add, remove.

``WatchlistRepository`` is a stateless repository whose methods take an open
connection, so this router opens a ``db_manager.connect()`` unit of work per
call. Add/remove also update the market source's active ticker set so streaming
starts/stops immediately.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.config import DEFAULT_USER_ID
from app.deps import (
    get_db_manager,
    get_market_source,
    get_price_cache,
    get_watchlist_repo,
)

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


class WatchlistAddRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=10)

    def normalized_ticker(self) -> str:
        return self.ticker.strip().upper()


@router.get("")
async def get_watchlist(
    repo: Annotated[Any, Depends(get_watchlist_repo)],
    db_manager: Annotated[Any, Depends(get_db_manager)],
    price_cache: Annotated[Any, Depends(get_price_cache)],
) -> list[dict]:
    async with db_manager.connect() as conn:
        items = await repo.get_watchlist(conn, DEFAULT_USER_ID)

    result = []
    for item in items:
        update = price_cache.get(item.ticker)
        result.append(
            {
                "ticker": item.ticker,
                "price": update.price if update else None,
                "change": update.change if update else 0.0,
                "change_percent": update.change_percent if update else 0.0,
                "direction": update.direction if update else "flat",
            }
        )
    return result


@router.post("")
async def add_ticker(
    body: WatchlistAddRequest,
    repo: Annotated[Any, Depends(get_watchlist_repo)],
    db_manager: Annotated[Any, Depends(get_db_manager)],
    market_source: Annotated[Any, Depends(get_market_source)],
) -> dict:
    ticker = body.normalized_ticker()
    async with db_manager.connect() as conn:
        item = await repo.add_ticker(conn, DEFAULT_USER_ID, ticker)

    if item is None:
        return {"ticker": ticker, "added": False, "reason": "already exists"}

    await market_source.add_ticker(ticker)
    return {"ticker": ticker, "added": True}


@router.delete("/{ticker}")
async def remove_ticker(
    ticker: str,
    repo: Annotated[Any, Depends(get_watchlist_repo)],
    db_manager: Annotated[Any, Depends(get_db_manager)],
    market_source: Annotated[Any, Depends(get_market_source)],
) -> dict:
    ticker = ticker.strip().upper()
    async with db_manager.connect() as conn:
        removed = await repo.remove_ticker(conn, DEFAULT_USER_ID, ticker)

    if removed:
        await market_source.remove_ticker(ticker)
    return {"ticker": ticker, "removed": bool(removed)}
