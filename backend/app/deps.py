"""Shared FastAPI dependencies.

Services are created once in the app lifespan (``main.py``) and stashed on
``app.state``. These accessors read them back, raising a clear 503 when a
subsystem (DB or LLM) is unavailable so routers don't each re-implement the
guard. Tests can inject fakes by setting the corresponding ``app.state`` attrs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import HTTPException, Request

if TYPE_CHECKING:
    from app.market import PriceCache


def get_price_cache(request: Request) -> PriceCache:
    cache = getattr(request.app.state, "price_cache", None)
    if cache is None:
        raise HTTPException(status_code=503, detail="Market data not initialized")
    return cache


def get_market_source(request: Request) -> Any:
    source = getattr(request.app.state, "market_source", None)
    if source is None:
        raise HTTPException(status_code=503, detail="Market data not initialized")
    return source


def get_db_manager(request: Request) -> Any:
    manager = getattr(request.app.state, "db_manager", None)
    if manager is None:
        raise HTTPException(status_code=503, detail="Database not available")
    return manager


def get_portfolio_service(request: Request) -> Any:
    service = getattr(request.app.state, "portfolio_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="Database not available")
    return service


def get_watchlist_repo(request: Request) -> Any:
    repo = getattr(request.app.state, "watchlist_repo", None)
    if repo is None:
        raise HTTPException(status_code=503, detail="Database not available")
    return repo


def get_chat_service(request: Request) -> Any:
    service = getattr(request.app.state, "chat_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="Database not available")
    return service


def get_chat_engine(request: Request) -> Any:
    engine = getattr(request.app.state, "chat_engine", None)
    if engine is None:
        raise HTTPException(status_code=503, detail="LLM assistant not available")
    return engine
