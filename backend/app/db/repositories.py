"""Async repositories wrapping raw SQL for each table.

Every method takes an open ``aiosqlite.Connection`` as its first argument and
executes statements without committing — the enclosing ``get_db()`` unit of work
owns the transaction boundary (see connection.py). Tickers are normalized to
uppercase so lookups and uniqueness are case-insensitive.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import aiosqlite

from .models import (
    ChatMessage,
    PortfolioSnapshot,
    Position,
    Trade,
    UserProfile,
    WatchlistItem,
)

DEFAULT_USER_ID = "default"
DEFAULT_CASH_BALANCE = 10000.0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class UserRepository:
    async def get_user(
        self, conn: aiosqlite.Connection, user_id: str = DEFAULT_USER_ID
    ) -> UserProfile | None:
        async with conn.execute(
            "SELECT * FROM users_profile WHERE id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
        return UserProfile.from_row(row) if row else None

    async def get_or_create_default_user(
        self, conn: aiosqlite.Connection, user_id: str = DEFAULT_USER_ID
    ) -> UserProfile:
        user = await self.get_user(conn, user_id)
        if user is not None:
            return user
        now = _now_iso()
        await conn.execute(
            "INSERT INTO users_profile (id, cash_balance, created_at) VALUES (?, ?, ?)",
            (user_id, DEFAULT_CASH_BALANCE, now),
        )
        return UserProfile(
            id=user_id,
            cash_balance=DEFAULT_CASH_BALANCE,
            created_at=datetime.fromisoformat(now),
        )

    async def update_cash_balance(
        self, conn: aiosqlite.Connection, user_id: str, new_balance: float
    ) -> None:
        await conn.execute(
            "UPDATE users_profile SET cash_balance = ? WHERE id = ?",
            (new_balance, user_id),
        )


class WatchlistRepository:
    async def get_watchlist(
        self, conn: aiosqlite.Connection, user_id: str = DEFAULT_USER_ID
    ) -> list[WatchlistItem]:
        async with conn.execute(
            "SELECT * FROM watchlist WHERE user_id = ? ORDER BY added_at, rowid",
            (user_id,),
        ) as cur:
            rows = await cur.fetchall()
        return [WatchlistItem.from_row(r) for r in rows]

    async def add_ticker(
        self, conn: aiosqlite.Connection, user_id: str, ticker: str
    ) -> WatchlistItem | None:
        ticker = ticker.upper()
        if await self.ticker_exists(conn, user_id, ticker):
            return None
        item_id = uuid.uuid4().hex
        now = _now_iso()
        await conn.execute(
            "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
            (item_id, user_id, ticker, now),
        )
        return WatchlistItem(
            id=item_id, user_id=user_id, ticker=ticker, added_at=datetime.fromisoformat(now)
        )

    async def remove_ticker(
        self, conn: aiosqlite.Connection, user_id: str, ticker: str
    ) -> bool:
        cur = await conn.execute(
            "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?",
            (user_id, ticker.upper()),
        )
        return cur.rowcount > 0

    async def ticker_exists(
        self, conn: aiosqlite.Connection, user_id: str, ticker: str
    ) -> bool:
        async with conn.execute(
            "SELECT 1 FROM watchlist WHERE user_id = ? AND ticker = ?",
            (user_id, ticker.upper()),
        ) as cur:
            return await cur.fetchone() is not None


class PositionRepository:
    async def get_positions(
        self, conn: aiosqlite.Connection, user_id: str = DEFAULT_USER_ID
    ) -> list[Position]:
        async with conn.execute(
            "SELECT * FROM positions WHERE user_id = ? ORDER BY ticker",
            (user_id,),
        ) as cur:
            rows = await cur.fetchall()
        return [Position.from_row(r) for r in rows]

    async def get_position(
        self, conn: aiosqlite.Connection, user_id: str, ticker: str
    ) -> Position | None:
        async with conn.execute(
            "SELECT * FROM positions WHERE user_id = ? AND ticker = ?",
            (user_id, ticker.upper()),
        ) as cur:
            row = await cur.fetchone()
        return Position.from_row(row) if row else None

    async def upsert_position(
        self,
        conn: aiosqlite.Connection,
        user_id: str,
        ticker: str,
        quantity: float,
        avg_cost: float,
    ) -> None:
        now = _now_iso()
        await conn.execute(
            """
            INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, ticker) DO UPDATE SET
                quantity = excluded.quantity,
                avg_cost = excluded.avg_cost,
                updated_at = excluded.updated_at
            """,
            (uuid.uuid4().hex, user_id, ticker.upper(), quantity, avg_cost, now),
        )

    async def remove_position(
        self, conn: aiosqlite.Connection, user_id: str, ticker: str
    ) -> None:
        await conn.execute(
            "DELETE FROM positions WHERE user_id = ? AND ticker = ?",
            (user_id, ticker.upper()),
        )


class TradeRepository:
    async def record_trade(
        self,
        conn: aiosqlite.Connection,
        user_id: str,
        ticker: str,
        side: str,
        quantity: float,
        price: float,
    ) -> Trade:
        trade_id = uuid.uuid4().hex
        ticker = ticker.upper()
        now = _now_iso()
        await conn.execute(
            """
            INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (trade_id, user_id, ticker, side, quantity, price, now),
        )
        return Trade(
            id=trade_id,
            user_id=user_id,
            ticker=ticker,
            side=side,  # type: ignore[arg-type]
            quantity=quantity,
            price=price,
            executed_at=datetime.fromisoformat(now),
        )

    async def get_trades(
        self, conn: aiosqlite.Connection, user_id: str = DEFAULT_USER_ID, limit: int = 100
    ) -> list[Trade]:
        async with conn.execute(
            "SELECT * FROM trades WHERE user_id = ? ORDER BY executed_at DESC, rowid DESC LIMIT ?",
            (user_id, limit),
        ) as cur:
            rows = await cur.fetchall()
        return [Trade.from_row(r) for r in rows]


class SnapshotRepository:
    async def record_snapshot(
        self, conn: aiosqlite.Connection, user_id: str, total_value: float
    ) -> PortfolioSnapshot:
        snap_id = uuid.uuid4().hex
        now = _now_iso()
        await conn.execute(
            """
            INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at)
            VALUES (?, ?, ?, ?)
            """,
            (snap_id, user_id, total_value, now),
        )
        return PortfolioSnapshot(
            id=snap_id,
            user_id=user_id,
            total_value=total_value,
            recorded_at=datetime.fromisoformat(now),
        )

    async def get_snapshots(
        self, conn: aiosqlite.Connection, user_id: str = DEFAULT_USER_ID, limit: int = 500
    ) -> list[PortfolioSnapshot]:
        # Fetch the most recent `limit` rows, then return them oldest-first for charting.
        async with conn.execute(
            """
            SELECT * FROM portfolio_snapshots
            WHERE user_id = ?
            ORDER BY recorded_at DESC, rowid DESC
            LIMIT ?
            """,
            (user_id, limit),
        ) as cur:
            rows = await cur.fetchall()
        return [PortfolioSnapshot.from_row(r) for r in reversed(rows)]


class ChatRepository:
    async def save_message(
        self,
        conn: aiosqlite.Connection,
        user_id: str,
        role: str,
        content: str,
        actions: str | None = None,
    ) -> ChatMessage:
        msg_id = uuid.uuid4().hex
        now = _now_iso()
        await conn.execute(
            """
            INSERT INTO chat_messages (id, user_id, role, content, actions, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (msg_id, user_id, role, content, actions, now),
        )
        return ChatMessage(
            id=msg_id,
            user_id=user_id,
            role=role,  # type: ignore[arg-type]
            content=content,
            actions=actions,
            created_at=datetime.fromisoformat(now),
        )

    async def get_recent_messages(
        self, conn: aiosqlite.Connection, user_id: str = DEFAULT_USER_ID, limit: int = 20
    ) -> list[ChatMessage]:
        # Most recent `limit` messages returned oldest-first for prompt context.
        async with conn.execute(
            """
            SELECT * FROM chat_messages
            WHERE user_id = ?
            ORDER BY created_at DESC, rowid DESC
            LIMIT ?
            """,
            (user_id, limit),
        ) as cur:
            rows = await cur.fetchall()
        return [ChatMessage.from_row(r) for r in reversed(rows)]
