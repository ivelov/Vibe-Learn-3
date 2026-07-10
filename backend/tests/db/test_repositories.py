"""Tests for the async repositories."""

from __future__ import annotations

from app.db import (
    ChatRepository,
    PositionRepository,
    SnapshotRepository,
    TradeRepository,
    UserRepository,
    WatchlistRepository,
)


async def test_get_user_returns_seeded_default(manager):
    repo = UserRepository()
    async with manager.connect() as conn:
        user = await repo.get_user(conn, "default")
    assert user is not None
    assert user.cash_balance == 10000.0


async def test_get_or_create_default_user_creates(db_path):
    # Fresh, unseeded database.
    from app.db import DbManager

    mgr = DbManager(db_path)
    async with mgr.connect() as conn:
        await conn.executescript(
            "CREATE TABLE IF NOT EXISTS users_profile "
            "(id TEXT PRIMARY KEY, cash_balance REAL, created_at TEXT)"
        )
    repo = UserRepository()
    async with mgr.connect() as conn:
        user = await repo.get_or_create_default_user(conn, "default")
    assert user.cash_balance == 10000.0
    async with mgr.connect() as conn:
        again = await repo.get_user(conn, "default")
    assert again is not None


async def test_update_cash_balance(manager):
    repo = UserRepository()
    async with manager.connect() as conn:
        await repo.update_cash_balance(conn, "default", 5000.0)
    async with manager.connect() as conn:
        user = await repo.get_user(conn, "default")
    assert user.cash_balance == 5000.0


async def test_watchlist_crud(manager):
    repo = WatchlistRepository()

    async with manager.connect() as conn:
        added = await repo.add_ticker(conn, "default", "pypl")  # lowercase in
    assert added is not None
    assert added.ticker == "PYPL"  # normalized to uppercase

    async with manager.connect() as conn:
        exists = await repo.ticker_exists(conn, "default", "PYPL")
    assert exists

    # Adding an existing ticker returns None (idempotent).
    async with manager.connect() as conn:
        dup = await repo.add_ticker(conn, "default", "PYPL")
    assert dup is None

    async with manager.connect() as conn:
        items = await repo.get_watchlist(conn, "default")
    assert "PYPL" in {i.ticker for i in items}

    async with manager.connect() as conn:
        removed = await repo.remove_ticker(conn, "default", "pypl")
    assert removed is True

    async with manager.connect() as conn:
        removed_again = await repo.remove_ticker(conn, "default", "PYPL")
    assert removed_again is False


async def test_position_upsert_and_get(manager):
    repo = PositionRepository()

    async with manager.connect() as conn:
        await repo.upsert_position(conn, "default", "AAPL", 10, 190.0)
    async with manager.connect() as conn:
        pos = await repo.get_position(conn, "default", "AAPL")
    assert pos is not None
    assert pos.quantity == 10
    assert pos.avg_cost == 190.0

    # Upsert updates in place (no duplicate row).
    async with manager.connect() as conn:
        await repo.upsert_position(conn, "default", "AAPL", 15, 200.0)
    async with manager.connect() as conn:
        positions = await repo.get_positions(conn, "default")
        pos = await repo.get_position(conn, "default", "AAPL")
    assert len([p for p in positions if p.ticker == "AAPL"]) == 1
    assert pos.quantity == 15
    assert pos.avg_cost == 200.0

    async with manager.connect() as conn:
        await repo.remove_position(conn, "default", "AAPL")
    async with manager.connect() as conn:
        gone = await repo.get_position(conn, "default", "AAPL")
    assert gone is None


async def test_trade_records(manager):
    repo = TradeRepository()

    async with manager.connect() as conn:
        trade = await repo.record_trade(conn, "default", "AAPL", "buy", 5, 190.0)
    assert trade.side == "buy"
    assert trade.ticker == "AAPL"

    async with manager.connect() as conn:
        await repo.record_trade(conn, "default", "GOOGL", "sell", 2, 175.0)
        trades = await repo.get_trades(conn, "default")
    assert len(trades) == 2
    # Most recent first.
    assert trades[0].ticker == "GOOGL"


async def test_snapshot_records(manager):
    repo = SnapshotRepository()

    async with manager.connect() as conn:
        await repo.record_snapshot(conn, "default", 10000.0)
        await repo.record_snapshot(conn, "default", 10500.0)
        snaps = await repo.get_snapshots(conn, "default")
    assert len(snaps) == 2
    # Oldest first (chronological, for charting).
    assert snaps[0].total_value == 10000.0
    assert snaps[1].total_value == 10500.0


async def test_chat_messages(manager):
    repo = ChatRepository()

    async with manager.connect() as conn:
        await repo.save_message(conn, "default", "user", "Hello")
        await repo.save_message(
            conn, "default", "assistant", "Hi there", actions='{"trades": []}'
        )
        messages = await repo.get_recent_messages(conn, "default", limit=20)

    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[0].content == "Hello"
    assert messages[1].role == "assistant"
    assert messages[1].actions == '{"trades": []}'
