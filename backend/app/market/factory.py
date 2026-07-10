"""Factory for creating market data sources."""

from __future__ import annotations

import logging
import os

from .cache import PriceCache
from .interface import MarketDataSource
from .simulator import SimulatorDataSource

_MassiveDataSource: type | None = None

logger = logging.getLogger(__name__)


def create_market_data_source(price_cache: PriceCache) -> MarketDataSource:
    """Create the appropriate market data source based on environment variables.

    - MASSIVE_API_KEY set and non-empty → MassiveDataSource (real market data)
    - Otherwise → SimulatorDataSource (GBM simulation)

    Returns an unstarted source. Caller must await source.start(tickers).
    """
    api_key = os.environ.get("MASSIVE_API_KEY", "").strip()

    if api_key:
        global _MassiveDataSource
        if _MassiveDataSource is None:
            from .massive_client import MassiveDataSource as _MDS  # noqa: N814
            _MassiveDataSource = _MDS
        logger.info("Market data source: Massive API (real data)")
        return _MassiveDataSource(api_key=api_key, price_cache=price_cache)
    else:
        logger.info("Market data source: GBM Simulator")
        return SimulatorDataSource(price_cache=price_cache)
