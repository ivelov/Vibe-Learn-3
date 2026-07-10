"""Dataclass models for FinAlly database entities.

Each model mirrors one table. Timestamps are stored in the database as ISO-8601
UTC strings and hydrated back into ``datetime`` objects via ``from_row``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional

import aiosqlite


def _parse_dt(value: str) -> datetime:
    """Parse an ISO-8601 timestamp string into a datetime."""
    return datetime.fromisoformat(value)


@dataclass
class UserProfile:
    id: str
    cash_balance: float
    created_at: datetime

    @classmethod
    def from_row(cls, row: aiosqlite.Row) -> UserProfile:
        return cls(
            id=row["id"],
            cash_balance=row["cash_balance"],
            created_at=_parse_dt(row["created_at"]),
        )


@dataclass
class WatchlistItem:
    id: str
    user_id: str
    ticker: str
    added_at: datetime

    @classmethod
    def from_row(cls, row: aiosqlite.Row) -> WatchlistItem:
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            ticker=row["ticker"],
            added_at=_parse_dt(row["added_at"]),
        )


@dataclass
class Position:
    id: str
    user_id: str
    ticker: str
    quantity: float
    avg_cost: float
    updated_at: datetime

    @classmethod
    def from_row(cls, row: aiosqlite.Row) -> Position:
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            ticker=row["ticker"],
            quantity=row["quantity"],
            avg_cost=row["avg_cost"],
            updated_at=_parse_dt(row["updated_at"]),
        )


@dataclass
class Trade:
    id: str
    user_id: str
    ticker: str
    side: Literal["buy", "sell"]
    quantity: float
    price: float
    executed_at: datetime

    @classmethod
    def from_row(cls, row: aiosqlite.Row) -> Trade:
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            ticker=row["ticker"],
            side=row["side"],
            quantity=row["quantity"],
            price=row["price"],
            executed_at=_parse_dt(row["executed_at"]),
        )


@dataclass
class PortfolioSnapshot:
    id: str
    user_id: str
    total_value: float
    recorded_at: datetime

    @classmethod
    def from_row(cls, row: aiosqlite.Row) -> PortfolioSnapshot:
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            total_value=row["total_value"],
            recorded_at=_parse_dt(row["recorded_at"]),
        )


@dataclass
class ChatMessage:
    id: str
    user_id: str
    role: Literal["user", "assistant"]
    content: str
    actions: Optional[str]  # JSON string, or None for user messages
    created_at: datetime

    @classmethod
    def from_row(cls, row: aiosqlite.Row) -> ChatMessage:
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            role=row["role"],
            content=row["content"],
            actions=row["actions"],
            created_at=_parse_dt(row["created_at"]),
        )
