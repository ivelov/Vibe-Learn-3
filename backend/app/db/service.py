"""High-level services combining repositories with portfolio business logic.

``PortfolioService`` owns trade execution and valuation; it reads live prices
from the market ``PriceCache`` (duck-typed on ``get_price(ticker) -> float | None``)
to enrich positions with market value and unrealized P&L. ``ChatService`` is a
thin wrapper over the chat message log.

All multi-step writes run inside a single ``DbManager.connect()`` unit of work so
cash, position, and trade updates commit atomically.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional, Protocol

from .connection import DbManager
from .models import ChatMessage, PortfolioSnapshot, Position, Trade, WatchlistItem
from .repositories import (
    ChatRepository,
    PositionRepository,
    SnapshotRepository,
    TradeRepository,
    UserRepository,
    WatchlistRepository,
)

# Tolerance for float comparisons on cash/share balances.
_EPS = 1e-9


class PriceSource(Protocol):
    """Minimal interface required from the market price cache."""

    def get_price(self, ticker: str) -> float | None: ...


@dataclass
class EnrichedPosition:
    ticker: str
    quantity: float
    avg_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    pnl_pct: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PortfolioView:
    cash_balance: float
    positions: list[EnrichedPosition]
    total_value: float
    total_unrealized_pnl: float

    def to_dict(self) -> dict:
        return {
            "cash_balance": self.cash_balance,
            "positions": [p.to_dict() for p in self.positions],
            "total_value": self.total_value,
            "total_unrealized_pnl": self.total_unrealized_pnl,
        }


@dataclass
class TradeResult:
    success: bool
    message: str
    trade: Optional[Trade] = None
    cash_balance: Optional[float] = None
    position: Optional[Position] = None


class PortfolioService:
    def __init__(self, db_manager: DbManager, price_cache: PriceSource | None = None) -> None:
        self.db = db_manager
        self.price_cache = price_cache
        self.users = UserRepository()
        self.positions = PositionRepository()
        self.trades = TradeRepository()
        self.snapshots = SnapshotRepository()
        self.watchlist = WatchlistRepository()

    def _current_price(self, ticker: str, fallback: float) -> float:
        """Latest cached price for a ticker, falling back to avg cost if unknown."""
        if self.price_cache is None:
            return fallback
        price = self.price_cache.get_price(ticker)
        return price if price is not None else fallback

    async def get_portfolio(self, user_id: str = "default") -> PortfolioView:
        async with self.db.connect() as conn:
            user = await self.users.get_or_create_default_user(conn, user_id)
            positions = await self.positions.get_positions(conn, user_id)

        enriched: list[EnrichedPosition] = []
        total_market_value = 0.0
        total_pnl = 0.0
        for pos in positions:
            current_price = self._current_price(pos.ticker, pos.avg_cost)
            market_value = current_price * pos.quantity
            cost_basis = pos.avg_cost * pos.quantity
            unrealized_pnl = market_value - cost_basis
            pnl_pct = (unrealized_pnl / cost_basis * 100.0) if cost_basis else 0.0
            enriched.append(
                EnrichedPosition(
                    ticker=pos.ticker,
                    quantity=pos.quantity,
                    avg_cost=pos.avg_cost,
                    current_price=current_price,
                    market_value=market_value,
                    unrealized_pnl=unrealized_pnl,
                    pnl_pct=pnl_pct,
                )
            )
            total_market_value += market_value
            total_pnl += unrealized_pnl

        return PortfolioView(
            cash_balance=user.cash_balance,
            positions=enriched,
            total_value=user.cash_balance + total_market_value,
            total_unrealized_pnl=total_pnl,
        )

    async def execute_trade(
        self,
        user_id: str,
        ticker: str,
        side: str,
        quantity: float,
        price: float,
    ) -> TradeResult:
        ticker = ticker.upper()
        side = side.lower()

        if side not in ("buy", "sell"):
            return TradeResult(False, f"Invalid side '{side}'. Must be 'buy' or 'sell'.")
        if quantity <= 0:
            return TradeResult(False, "Quantity must be greater than zero.")
        if price <= 0:
            return TradeResult(False, "Price must be greater than zero.")

        async with self.db.connect() as conn:
            user = await self.users.get_or_create_default_user(conn, user_id)
            position = await self.positions.get_position(conn, user_id, ticker)

            if side == "buy":
                cost = price * quantity
                if cost > user.cash_balance + _EPS:
                    return TradeResult(
                        False,
                        f"Insufficient cash: buying {quantity} {ticker} costs "
                        f"${cost:,.2f} but only ${user.cash_balance:,.2f} available.",
                    )
                new_cash = user.cash_balance - cost
                if position is not None:
                    total_qty = position.quantity + quantity
                    new_avg_cost = (
                        position.avg_cost * position.quantity + price * quantity
                    ) / total_qty
                else:
                    total_qty = quantity
                    new_avg_cost = price
                await self.users.update_cash_balance(conn, user_id, new_cash)
                await self.positions.upsert_position(
                    conn, user_id, ticker, total_qty, new_avg_cost
                )
            else:  # sell
                held = position.quantity if position is not None else 0.0
                if position is None or held < quantity - _EPS:
                    return TradeResult(
                        False,
                        f"Insufficient shares: selling {quantity} {ticker} but only "
                        f"{held} held.",
                    )
                new_cash = user.cash_balance + price * quantity
                remaining = held - quantity
                await self.users.update_cash_balance(conn, user_id, new_cash)
                if remaining <= _EPS:
                    await self.positions.remove_position(conn, user_id, ticker)
                else:
                    await self.positions.upsert_position(
                        conn, user_id, ticker, remaining, position.avg_cost
                    )

            trade = await self.trades.record_trade(
                conn, user_id, ticker, side, quantity, price
            )
            updated_position = await self.positions.get_position(conn, user_id, ticker)

        verb = "Bought" if side == "buy" else "Sold"
        return TradeResult(
            success=True,
            message=f"{verb} {quantity} {ticker} @ ${price:,.2f}.",
            trade=trade,
            cash_balance=new_cash,
            position=updated_position,
        )

    async def record_snapshot(self, user_id: str = "default") -> PortfolioSnapshot:
        view = await self.get_portfolio(user_id)
        async with self.db.connect() as conn:
            return await self.snapshots.record_snapshot(conn, user_id, view.total_value)

    async def get_history(
        self, user_id: str = "default", limit: int = 500
    ) -> list[PortfolioSnapshot]:
        async with self.db.connect() as conn:
            return await self.snapshots.get_snapshots(conn, user_id, limit)


class ChatService:
    def __init__(self, db_manager: DbManager) -> None:
        self.db = db_manager
        self.chat = ChatRepository()

    async def save_message(
        self,
        user_id: str,
        role: str,
        content: str,
        actions: str | None = None,
    ) -> ChatMessage:
        async with self.db.connect() as conn:
            return await self.chat.save_message(conn, user_id, role, content, actions)

    async def get_history(
        self, user_id: str = "default", limit: int = 20
    ) -> list[ChatMessage]:
        async with self.db.connect() as conn:
            return await self.chat.get_recent_messages(conn, user_id, limit)


class WatchlistService:
    """Transaction-owning wrapper over WatchlistRepository for thin routers.

    Owns only the database side of the watchlist. Routers remain responsible for
    wiring the market data source (``source.add_ticker`` / ``source.remove_ticker``)
    and for enriching tickers with live prices from the ``PriceCache``.
    """

    def __init__(self, db_manager: DbManager) -> None:
        self.db = db_manager
        self.watchlist = WatchlistRepository()

    async def get_watchlist(self, user_id: str = "default") -> list[WatchlistItem]:
        async with self.db.connect() as conn:
            return await self.watchlist.get_watchlist(conn, user_id)

    async def add_ticker(
        self, ticker: str, user_id: str = "default"
    ) -> WatchlistItem | None:
        """Add a ticker. Returns the new item, or None if already present."""
        async with self.db.connect() as conn:
            return await self.watchlist.add_ticker(conn, user_id, ticker)

    async def remove_ticker(self, ticker: str, user_id: str = "default") -> bool:
        """Remove a ticker. Returns True if a row was deleted, else False."""
        async with self.db.connect() as conn:
            return await self.watchlist.remove_ticker(conn, user_id, ticker)

    async def ticker_exists(self, ticker: str, user_id: str = "default") -> bool:
        async with self.db.connect() as conn:
            return await self.watchlist.ticker_exists(conn, user_id, ticker)
