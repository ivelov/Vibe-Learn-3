"""Tests for MassiveDataSource (mocked)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def _try_import_massive() -> bool:
    """Return True if massive is importable."""
    try:
        import massive  # noqa: F401
        return True
    except ImportError:
        return False


# Skip entire module if massive is not installed
pytestmark = pytest.mark.skipif(
    not _try_import_massive(),
    reason="massive package not installed",
)


if _try_import_massive():
    from app.market.cache import PriceCache
    from app.market.massive_client import MassiveDataSource

    def _make_snapshot(ticker: str, price: float, timestamp_ms: int) -> MagicMock:
        """Create a mock Massive snapshot object."""
        snap = MagicMock()
        snap.ticker = ticker
        snap.last_trade = MagicMock()
        snap.last_trade.price = price
        snap.last_trade.timestamp = timestamp_ms
        return snap

    @pytest.mark.asyncio
    class TestMassiveDataSource:
        """Unit tests for MassiveDataSource with mocked API."""

        async def test_parses_snapshot_ticker(self):
            """Test that the client parses ticker from snapshot."""
            cache = PriceCache()
            source = MassiveDataSource(api_key="test-key", price_cache=cache, poll_interval=60.0)
            mock_snap = _make_snapshot("AAPL", 190.50, 1707580800000)

            with patch.object(source, "_fetch_snapshots", return_value=[mock_snap]):
                await source.start(["AAPL"])

            update = cache.get("AAPL")
            assert update is not None
            assert update.price == 190.50
            await source.stop()

        async def test_parses_multiple_tickers(self):
            """Test parsing multiple tickers."""
            cache = PriceCache()
            source = MassiveDataSource(api_key="test-key", price_cache=cache, poll_interval=60.0)
            mock_snap1 = _make_snapshot("AAPL", 190.50, 1707580800000)
            mock_snap2 = _make_snapshot("GOOGL", 175.00, 1707580800000)

            with patch.object(source, "_fetch_snapshots", return_value=[mock_snap1, mock_snap2]):
                await source.start(["AAPL", "GOOGL"])

            assert cache.get_price("AAPL") == 190.50
            assert cache.get_price("GOOGL") == 175.00
            await source.stop()

        async def test_handles_missing_price_data(self):
            """Test that missing price data is handled gracefully."""
            cache = PriceCache()
            source = MassiveDataSource(api_key="test-key", price_cache=cache, poll_interval=60.0)
            bad_snap = MagicMock()
            bad_snap.ticker = "BAD"
            bad_snap.last_trade = None

            with patch.object(source, "_fetch_snapshots", return_value=[bad_snap]):
                await source.start(["BAD"])
                assert cache.get_price("BAD") is None
            await source.stop()

        async def test_api_error_does_not_crash(self):
            """Test that API errors don't crash the poller."""
            cache = PriceCache()
            source = MassiveDataSource(api_key="test-key", price_cache=cache, poll_interval=60.0)

            with patch.object(source, "_fetch_snapshots", side_effect=Exception("network error")):
                await source.start(["AAPL"])
            await source.stop()

        async def test_stop_cancels_task(self):
            """Test that stop() cancels the polling task."""
            cache = PriceCache()
            source = MassiveDataSource(api_key="test-key", price_cache=cache, poll_interval=60.0)
            mock_snap = _make_snapshot("AAPL", 190.50, 1707580800000)

            with patch.object(source, "_fetch_snapshots", return_value=mock_snap):
                await source.start(["AAPL"])

            assert source._task is not None
            assert not source._task.done()

            await source.stop()
            assert source._task is None

        async def test_start_immediate_poll(self):
            """Test that start() does an immediate poll before starting the loop."""
            cache = PriceCache()
            source = MassiveDataSource(api_key="test-key", price_cache=cache, poll_interval=60.0)

            mock_snapshots = [_make_snapshot("AAPL", 190.50, 1707580800000)]

            with patch.object(source, "_fetch_snapshots", return_value=mock_snapshots):
                await source.start(["AAPL"])

            assert cache.get_price("AAPL") == 190.50
            await source.stop()
