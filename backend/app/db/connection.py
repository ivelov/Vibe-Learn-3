"""Async SQLite connection management and lazy database initialization.

The database lives at ``db/finally.db`` relative to the backend project root,
which maps to the volume-mounted ``/app/db`` inside the container. The path can
be overridden with the ``FINALLY_DB_PATH`` environment variable (used by tests
and alternate deployments).

``get_db()`` is a unit-of-work context manager: it opens a connection, enables
foreign keys, and commits on clean exit / rolls back on exception. Repositories
therefore never commit themselves — the enclosing ``get_db()`` block defines the
transaction boundary, which keeps multi-step operations (e.g. a trade updating
cash + position + trade log) atomic.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

# backend/app/db/connection.py -> parents[2] == backend/
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_DB_PATH = _BACKEND_ROOT / "db" / "finally.db"

# Default watchlist seeded on a fresh database (matches PLAN.md section 7).
DEFAULT_WATCHLIST: list[str] = [
    "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA",
    "NVDA", "META", "JPM", "V", "NFLX",
]

DEFAULT_CASH_BALANCE = 10000.0
DEFAULT_USER_ID = "default"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users_profile (
    id TEXT PRIMARY KEY DEFAULT 'default',
    cash_balance REAL NOT NULL DEFAULT 10000.0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS watchlist (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    ticker TEXT NOT NULL,
    added_at TEXT NOT NULL,
    UNIQUE(user_id, ticker)
);

CREATE TABLE IF NOT EXISTS positions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    ticker TEXT NOT NULL,
    quantity REAL NOT NULL,
    avg_cost REAL NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(user_id, ticker)
);

CREATE TABLE IF NOT EXISTS trades (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    ticker TEXT NOT NULL,
    side TEXT NOT NULL CHECK(side IN ('buy', 'sell')),
    quantity REAL NOT NULL,
    price REAL NOT NULL,
    executed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    total_value REAL NOT NULL,
    recorded_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    actions TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_trades_user ON trades(user_id, executed_at);
CREATE INDEX IF NOT EXISTS idx_snapshots_user ON portfolio_snapshots(user_id, recorded_at);
CREATE INDEX IF NOT EXISTS idx_chat_user ON chat_messages(user_id, created_at);
"""


def resolve_db_path(db_path: str | Path | None = None) -> Path:
    """Resolve the database path from an explicit arg, env var, or default."""
    if db_path is not None:
        return Path(db_path)
    env = os.environ.get("FINALLY_DB_PATH")
    if env:
        return Path(env)
    return _DEFAULT_DB_PATH


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@asynccontextmanager
async def get_db(db_path: str | Path | None = None) -> AsyncIterator[aiosqlite.Connection]:
    """Yield an aiosqlite connection scoped as a single unit of work.

    Enables foreign keys, sets a Row factory for name-based column access, and
    commits on a clean exit (rolling back on exception). Always closes.
    """
    path = resolve_db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = await aiosqlite.connect(path)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        await conn.commit()
    except Exception:
        await conn.rollback()
        raise
    finally:
        await conn.close()


class DbManager:
    """Owns database configuration and lifecycle (init + seed).

    Repositories and services receive a ``DbManager`` and obtain connections via
    ``connect()`` so the whole application shares one resolved path.
    """

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = resolve_db_path(db_path)

    def connect(self):
        """Return a ``get_db`` unit-of-work context manager for this db."""
        return get_db(self.db_path)

    async def init_db(self) -> None:
        """Create all tables (if missing) and seed defaults on an empty db.

        Safe to call repeatedly — uses ``CREATE TABLE IF NOT EXISTS`` and only
        seeds when no user rows exist.
        """
        async with self.connect() as conn:
            await conn.executescript(SCHEMA_SQL)
            await self._seed(conn)

    async def seed_if_empty(self) -> None:
        """Insert default seed data only if the database has no users."""
        async with self.connect() as conn:
            await self._seed(conn)

    async def _seed(self, conn: aiosqlite.Connection) -> None:
        async with conn.execute("SELECT COUNT(*) AS n FROM users_profile") as cur:
            row = await cur.fetchone()
        if row["n"] > 0:
            return

        now = _now_iso()
        await conn.execute(
            "INSERT INTO users_profile (id, cash_balance, created_at) VALUES (?, ?, ?)",
            (DEFAULT_USER_ID, DEFAULT_CASH_BALANCE, now),
        )
        for ticker in DEFAULT_WATCHLIST:
            await conn.execute(
                "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
                (uuid.uuid4().hex, DEFAULT_USER_ID, ticker, now),
            )


async def init_db(db_path: str | Path | None = None) -> DbManager:
    """Convenience: build a ``DbManager``, initialize the schema, and return it."""
    manager = DbManager(db_path)
    await manager.init_db()
    return manager
