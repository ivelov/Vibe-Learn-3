"""FinAlly FastAPI application.

Wires together the three subsystems:
  * market data (``app.market``) — the in-process price simulator/poller
  * database    (``app.db``)     — SQLite portfolio/watchlist/chat state
  * LLM chat    (``app.llm``)    — the AI trading assistant

Services are constructed once in the lifespan and stored on ``app.state``;
routers read them back via ``app.deps``. The DB init and LLM engine are guarded
at runtime so a locked volume or a missing API key degrades the affected
endpoints to 503 rather than taking down live price streaming.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import (
    DB_PATH,
    DEFAULT_TICKERS,
    DEFAULT_USER_ID,
    LLM_MOCK,
    OPENROUTER_API_KEY,
    SNAPSHOT_INTERVAL_SECONDS,
)
from app.db import ChatService, DbManager, PortfolioService, WatchlistRepository
from app.llm import ChatEngine
from app.market import PriceCache, create_market_data_source, create_stream_router
from app.routers import chat as chat_router
from app.routers import health as health_router
from app.routers import portfolio as portfolio_router
from app.routers import watchlist as watchlist_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# The price cache is process-global and cheap; create it at import so the SSE
# router can bind to it and the market source can write to the same instance.
price_cache = PriceCache()


async def _snapshot_loop(app: FastAPI) -> None:
    """Periodically record total portfolio value for the P&L chart.

    ``PortfolioService.record_snapshot`` marks positions to market internally via
    the injected price cache. Best-effort: any error is logged and the loop
    continues.
    """
    while True:
        await asyncio.sleep(SNAPSHOT_INTERVAL_SECONDS)
        service = getattr(app.state, "portfolio_service", None)
        if service is None:
            continue
        try:
            await service.record_snapshot(DEFAULT_USER_ID)
        except Exception:
            logger.exception("Snapshot recording failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.price_cache = price_cache
    app.state.db_available = False
    app.state.llm_available = False
    app.state.db_manager = None
    app.state.portfolio_service = None
    app.state.watchlist_repo = None
    app.state.chat_service = None
    app.state.chat_engine = None
    app.state.snapshot_task = None

    # --- Database ---------------------------------------------------------
    tickers = list(DEFAULT_TICKERS)
    try:
        db_manager = DbManager(str(DB_PATH))
        await db_manager.init_db()
        app.state.db_manager = db_manager
        app.state.portfolio_service = PortfolioService(db_manager, price_cache)
        app.state.watchlist_repo = WatchlistRepository()
        app.state.chat_service = ChatService(db_manager)
        app.state.db_available = True
        logger.info("Database initialized at %s", DB_PATH)

        # Prefer the persisted watchlist for the initial ticker set.
        async with db_manager.connect() as conn:
            items = await app.state.watchlist_repo.get_watchlist(conn, DEFAULT_USER_ID)
        loaded = [item.ticker for item in items]
        if loaded:
            tickers = loaded
    except Exception:
        logger.exception("Database initialization failed — running without DB")
        app.state.db_available = False

    # --- Market data ------------------------------------------------------
    market_source = create_market_data_source(price_cache)
    await market_source.start(tickers)
    app.state.market_source = market_source
    logger.info("Market data source started with %d tickers", len(tickers))

    # --- LLM --------------------------------------------------------------
    # Enable chat only when it can actually work: mock mode, or a real API key.
    if LLM_MOCK or OPENROUTER_API_KEY:
        try:
            app.state.chat_engine = ChatEngine(api_key=OPENROUTER_API_KEY, mock=LLM_MOCK)
            app.state.llm_available = True
            logger.info("LLM chat engine ready (mock=%s)", LLM_MOCK)
        except Exception:
            logger.exception("LLM engine init failed — chat endpoint disabled")
            app.state.llm_available = False
    else:
        logger.warning("No OPENROUTER_KEY and LLM_MOCK is off — chat endpoint disabled")

    # --- Background snapshot task ----------------------------------------
    if app.state.db_available:
        app.state.snapshot_task = asyncio.create_task(_snapshot_loop(app), name="snapshot-loop")

    try:
        yield
    finally:
        task = app.state.snapshot_task
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        source = getattr(app.state, "market_source", None)
        if source:
            await source.stop()
        logger.info("Shutdown complete")


app = FastAPI(title="FinAlly API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API routers (registered before the static mount so /api/* wins) -------
app.include_router(create_stream_router(price_cache))
app.include_router(health_router.router)
app.include_router(portfolio_router.router)
app.include_router(watchlist_router.router)
app.include_router(chat_router.router)

# --- Static frontend (Next.js export) --------------------------------------
# Mounted last, at "/", so it only handles paths not claimed by the API.
_static_path = Path(__file__).resolve().parent.parent / "static"
if _static_path.exists():
    app.mount("/", StaticFiles(directory=str(_static_path), html=True), name="static")
    logger.info("Serving static frontend from %s", _static_path)
else:
    logger.info("No static/ directory — frontend not bundled (API-only mode)")
