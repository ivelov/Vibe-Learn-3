"""Portfolio endpoints: holdings valuation, trade execution, value history.

``PortfolioService`` owns its own DB transactions and is constructed with the
live ``PriceCache``, so ``get_portfolio`` already returns positions marked to
market. This router just serializes those views and translates trade requests.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.config import DEFAULT_USER_ID
from app.deps import get_portfolio_service, get_price_cache

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


class TradeRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=10)
    quantity: float = Field(..., gt=0)
    side: Literal["buy", "sell"]

    def normalized_ticker(self) -> str:
        return self.ticker.strip().upper()


def _serialize_portfolio(view: Any) -> dict:
    return {
        "cash_balance": round(view.cash_balance, 2),
        "positions": [
            {
                "ticker": p.ticker,
                "quantity": p.quantity,
                "avg_cost": round(p.avg_cost, 4),
                "current_price": round(p.current_price, 2),
                "market_value": round(p.market_value, 2),
                "unrealized_pnl": round(p.unrealized_pnl, 2),
                "pnl_pct": round(p.pnl_pct, 2),
            }
            for p in view.positions
        ],
        "total_value": round(view.total_value, 2),
        "total_unrealized_pnl": round(view.total_unrealized_pnl, 2),
    }


@router.get("")
async def get_portfolio(
    service: Annotated[Any, Depends(get_portfolio_service)],
) -> dict:
    view = await service.get_portfolio(DEFAULT_USER_ID)
    return _serialize_portfolio(view)


@router.post("/trade")
async def execute_trade(
    body: TradeRequest,
    service: Annotated[Any, Depends(get_portfolio_service)],
    price_cache: Annotated[Any, Depends(get_price_cache)],
) -> dict:
    ticker = body.normalized_ticker()
    price = price_cache.get_price(ticker)
    if price is None:
        return {"success": False, "error": f"No live price available for {ticker}"}

    result = await service.execute_trade(DEFAULT_USER_ID, ticker, body.side, body.quantity, price)
    if not result.success:
        return {"success": False, "error": result.message}

    # Record a snapshot immediately so the P&L chart reflects the trade.
    await service.record_snapshot(DEFAULT_USER_ID)

    trade = result.trade
    return {
        "success": True,
        "trade": {
            "ticker": trade.ticker,
            "side": trade.side,
            "quantity": trade.quantity,
            "price": round(trade.price, 2),
            "executed_at": trade.executed_at.isoformat(),
        },
        "cash_balance": round(result.cash_balance, 2),
    }


@router.get("/history")
async def get_history(
    service: Annotated[Any, Depends(get_portfolio_service)],
    limit: int = 500,
) -> list[dict]:
    limit = max(1, min(limit, 5000))
    snapshots = await service.get_history(DEFAULT_USER_ID, limit)
    return [
        {"total_value": round(s.total_value, 2), "recorded_at": s.recorded_at.isoformat()}
        for s in snapshots
    ]
