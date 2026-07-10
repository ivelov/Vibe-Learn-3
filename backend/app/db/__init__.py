"""Database layer for FinAlly.

Public API:
    get_db              - Async unit-of-work connection context manager
    init_db             - Convenience: build a DbManager and create the schema
    DbManager           - Owns db path, initialization, and seeding
    resolve_db_path     - Resolve the on-disk database path

    Models: UserProfile, WatchlistItem, Position, Trade, PortfolioSnapshot, ChatMessage

    Repositories: UserRepository, WatchlistRepository, PositionRepository,
        TradeRepository, SnapshotRepository, ChatRepository

    Services: PortfolioService, ChatService
    Views:    PortfolioView, EnrichedPosition, TradeResult
"""

from .connection import DbManager, get_db, init_db, resolve_db_path
from .models import (
    ChatMessage,
    PortfolioSnapshot,
    Position,
    Trade,
    UserProfile,
    WatchlistItem,
)
from .repositories import (
    ChatRepository,
    PositionRepository,
    SnapshotRepository,
    TradeRepository,
    UserRepository,
    WatchlistRepository,
)
from .service import (
    ChatService,
    EnrichedPosition,
    PortfolioService,
    PortfolioView,
    TradeResult,
    WatchlistService,
)

__all__ = [
    # connection
    "get_db",
    "init_db",
    "DbManager",
    "resolve_db_path",
    # models
    "UserProfile",
    "WatchlistItem",
    "Position",
    "Trade",
    "PortfolioSnapshot",
    "ChatMessage",
    # repositories
    "UserRepository",
    "WatchlistRepository",
    "PositionRepository",
    "TradeRepository",
    "SnapshotRepository",
    "ChatRepository",
    # services + views
    "PortfolioService",
    "ChatService",
    "WatchlistService",
    "PortfolioView",
    "EnrichedPosition",
    "TradeResult",
]
