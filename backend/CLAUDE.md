# Backend — Developer Guide

## Project Setup

This project uses **poetry 2.x** for Python dependency management — Poetry 1.7.1 does not support PEP 621 `[project]` format. Add deps with `poetry add <pkg>` and run commands with `poetry run <cmd>`.

```bash
cd backend
poetry install              # Install all deps from poetry.lock
poetry add <pkg>            # Add a new dependency
poetry add --group dev pytest httpx ruff  # Add a dev dependency
```

> Note: `package-mode = false` and `requires-python = ">=3.12,<4.0"` are set in pyproject.toml. Use `poetry install --no-root` if you see "no file/folder found for package finally-backend". The old `uv.lock` is removed; use `poetry.lock` only.

## Market Data API

The market data subsystem lives in `app/market/`. Use these imports:

```python
from app.market import PriceCache, PriceUpdate, MarketDataSource, create_market_data_source
```

### Core Types

- **`PriceUpdate`** — Immutable dataclass: `ticker`, `price`, `previous_price`, `timestamp`, plus properties `change`, `change_percent`, `direction` ("up"/"down"/"flat"), and `to_dict()` for JSON serialization.

- **`PriceCache`** — Thread-safe in-memory store. Key methods:
  - `update(ticker, price, timestamp=None) -> PriceUpdate`
  - `get(ticker) -> PriceUpdate | None`
  - `get_price(ticker) -> float | None`
  - `get_all() -> dict[str, PriceUpdate]`
  - `remove(ticker)`
  - `version` property — monotonic counter, increments on every update (for SSE change detection)

- **`MarketDataSource`** — Abstract interface implemented by `SimulatorDataSource` and `MassiveDataSource`. Lifecycle: `start(tickers)` -> `add_ticker()` / `remove_ticker()` -> `stop()`.

- **`create_market_data_source(cache)`** — Factory. Returns `MassiveDataSource` if `MASSIVE_API_KEY` is set, otherwise `SimulatorDataSource`.

### SSE Streaming

```python
from app.market import create_stream_router

router = create_stream_router(price_cache)  # Returns FastAPI APIRouter
# Endpoint: GET /api/stream/prices (text/event-stream)
```

### Seed Data

Default tickers: AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX. Seed prices and per-ticker volatility/drift params are in `app/market/seed_prices.py`.

## Running Tests

```bash
poetry run pytest -v              # All tests
poetry run pytest --cov=app       # With coverage
poetry run ruff check app/ tests/ # Lint
```

## Demo

```bash
poetry run python market_data_demo.py   # Live terminal dashboard with simulated prices
```
