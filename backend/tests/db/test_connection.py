"""Tests for connection management, schema init, and seeding."""

from __future__ import annotations

from app.db import DbManager, get_db, init_db

EXPECTED_TABLES = {
    "users_profile",
    "watchlist",
    "positions",
    "trades",
    "portfolio_snapshots",
    "chat_messages",
}


async def _table_names(conn) -> set[str]:
    async with conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ) as cur:
        rows = await cur.fetchall()
    return {r["name"] for r in rows}


async def test_init_db_creates_tables(db_path):
    manager = DbManager(db_path)
    await manager.init_db()

    async with get_db(db_path) as conn:
        tables = await _table_names(conn)
    assert EXPECTED_TABLES.issubset(tables)


async def test_init_db_is_idempotent(db_path):
    manager = DbManager(db_path)
    await manager.init_db()
    # Second call must not raise and must not duplicate seed data.
    await manager.init_db()

    async with get_db(db_path) as conn:
        async with conn.execute("SELECT COUNT(*) AS n FROM users_profile") as cur:
            users = (await cur.fetchone())["n"]
        async with conn.execute("SELECT COUNT(*) AS n FROM watchlist") as cur:
            tickers = (await cur.fetchone())["n"]
    assert users == 1
    assert tickers == 10


async def test_seed_data_inserts_defaults(db_path):
    manager = DbManager(db_path)
    await manager.init_db()

    async with get_db(db_path) as conn:
        async with conn.execute("SELECT * FROM users_profile") as cur:
            user = await cur.fetchone()
        async with conn.execute("SELECT ticker FROM watchlist") as cur:
            tickers = {r["ticker"] for r in await cur.fetchall()}

    assert user["id"] == "default"
    assert user["cash_balance"] == 10000.0
    assert tickers == {
        "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA",
        "NVDA", "META", "JPM", "V", "NFLX",
    }


async def test_init_db_convenience_function(db_path):
    manager = await init_db(db_path)
    assert isinstance(manager, DbManager)
    async with get_db(db_path) as conn:
        tables = await _table_names(conn)
    assert EXPECTED_TABLES.issubset(tables)


async def test_get_db_enables_foreign_keys(db_path):
    await init_db(db_path)
    async with get_db(db_path) as conn:
        async with conn.execute("PRAGMA foreign_keys") as cur:
            row = await cur.fetchone()
    assert row[0] == 1


async def test_get_db_rolls_back_on_exception(db_path):
    await init_db(db_path)
    try:
        async with get_db(db_path) as conn:
            await conn.execute(
                "INSERT INTO watchlist (id, user_id, ticker, added_at) "
                "VALUES ('x', 'default', 'ZZZZ', '2026-01-01T00:00:00+00:00')"
            )
            raise RuntimeError("boom")
    except RuntimeError:
        pass

    async with get_db(db_path) as conn:
        async with conn.execute(
            "SELECT COUNT(*) AS n FROM watchlist WHERE ticker = 'ZZZZ'"
        ) as cur:
            n = (await cur.fetchone())["n"]
    assert n == 0


async def test_seed_if_empty_skips_when_populated(db_path):
    manager = DbManager(db_path)
    await manager.init_db()
    # Remove all watchlist rows but keep the user; seed_if_empty should be a no-op.
    async with get_db(db_path) as conn:
        await conn.execute("DELETE FROM watchlist")
    await manager.seed_if_empty()

    async with get_db(db_path) as conn:
        async with conn.execute("SELECT COUNT(*) AS n FROM watchlist") as cur:
            n = (await cur.fetchone())["n"]
    assert n == 0  # user still exists, so no reseed happened
