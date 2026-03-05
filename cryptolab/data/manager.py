"""DataManager: unified entry point for historical and live data."""

import logging
from typing import Optional

import pandas as pd

from cryptolab.utils import interval_to_ms, utc_now_ms
from cryptolab.data.cache import ParquetCache
from cryptolab.data.fetchers.okx import OKXFetcher
from cryptolab.data.fetchers.binance import BinanceFetcher
from cryptolab.data.fetchers.hyperliquid import HyperliquidFetcher
from cryptolab.data.validate import validate_ohlcv, ValidationReport

logger = logging.getLogger(__name__)


class DataManager:
    """
    Unified data access layer.
    - get_historical(): cache-through, gap-fill fetch
    - get_live(): always fresh from HL
    - seed(): bulk download for backtesting
    """

    def __init__(self, cache_dir: Optional[str] = None):
        self.cache = ParquetCache(cache_dir) if cache_dir else ParquetCache()
        self._fetchers = {
            "okx": OKXFetcher(),
            "binance": BinanceFetcher(),
            "hl": HyperliquidFetcher(),
        }

    def get_historical(
        self,
        symbol: str,
        interval: str,
        start_ms: int,
        end_ms: int,
        source: str = "okx",
    ) -> pd.DataFrame:
        """
        Get historical OHLCV data. Checks cache first, fetches missing ranges.
        """
        cached = self.cache.read(source, symbol, interval)
        iv_ms = interval_to_ms(interval)

        if not cached.empty:
            cached_min = int(cached["timestamp"].min().timestamp() * 1000)
            cached_max = int(cached["timestamp"].max().timestamp() * 1000)

            need_before = start_ms < cached_min
            need_after = end_ms > cached_max + iv_ms

            fetcher = self._fetchers.get(source)
            if not fetcher:
                raise ValueError(f"Unknown source: {source}")

            if need_before:
                logger.info(f"Fetching {symbol} {interval} before cache: {start_ms} -> {cached_min}")
                df_before = fetcher.fetch_ohlcv(symbol, interval, start_ms, cached_min)
                if not df_before.empty:
                    self.cache.merge_and_write(source, symbol, interval, df_before)

            if need_after:
                fetch_start = cached_max + iv_ms
                logger.info(f"Fetching {symbol} {interval} after cache: {fetch_start} -> {end_ms}")
                df_after = fetcher.fetch_ohlcv(symbol, interval, fetch_start, end_ms)
                if not df_after.empty:
                    self.cache.merge_and_write(source, symbol, interval, df_after)

            # Re-read merged cache
            cached = self.cache.read(source, symbol, interval)
        else:
            # Nothing cached — fetch everything
            fetcher = self._fetchers.get(source)
            if not fetcher:
                raise ValueError(f"Unknown source: {source}")
            logger.info(f"Fetching {symbol} {interval} full range: {start_ms} -> {end_ms}")
            df = fetcher.fetch_ohlcv(symbol, interval, start_ms, end_ms)
            if not df.empty:
                self.cache.merge_and_write(source, symbol, interval, df)
            cached = self.cache.read(source, symbol, interval)

        # Filter to requested range
        if cached.empty:
            return cached
        mask = (cached["timestamp"] >= pd.Timestamp(start_ms, unit="ms", tz="UTC")) & \
               (cached["timestamp"] < pd.Timestamp(end_ms, unit="ms", tz="UTC"))
        return cached[mask].reset_index(drop=True)

    def get_live(self, symbol: str, interval: str, lookback_bars: int = 100) -> pd.DataFrame:
        """Get recent candles from Hyperliquid (always fresh, no cache)."""
        now_ms = utc_now_ms()
        iv_ms = interval_to_ms(interval)
        start_ms = now_ms - (lookback_bars + 5) * iv_ms
        fetcher = self._fetchers["hl"]
        return fetcher.fetch_ohlcv(symbol, interval, start_ms, now_ms)

    def seed(
        self,
        symbol: str,
        interval: str,
        start_ms: int,
        end_ms: Optional[int] = None,
        source: str = "okx",
    ) -> ValidationReport:
        """Bulk download and cache. Returns validation report."""
        if end_ms is None:
            end_ms = utc_now_ms()

        logger.info(f"Seeding {source}/{symbol}/{interval} from {start_ms} to {end_ms}")
        df = self.get_historical(symbol, interval, start_ms, end_ms, source=source)
        report = validate_ohlcv(df, symbol, interval)
        logger.info(report.summary())
        return report
