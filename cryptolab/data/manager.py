"""DataManager: unified entry point for historical and live data."""

import logging
from typing import Optional

import pandas as pd

from cryptolab.utils import interval_to_ms, utc_now_ms
from cryptolab.data.cache import ParquetCache
from cryptolab.data.alt_cache import AltDataCache
from cryptolab.data.fetchers.okx import OKXFetcher
from cryptolab.data.fetchers.binance import BinanceFetcher
from cryptolab.data.fetchers.hyperliquid import HyperliquidFetcher
from cryptolab.data.validate import validate_ohlcv, ValidationReport
from cryptolab.data.alt_fetcher import fetch_funding_history, fetch_l2_snapshot, fetch_meta_snapshot

logger = logging.getLogger(__name__)


class DataManager:
    """统一数据入口。所有数据获取都经过这个类，不直接调用fetcher。

    核心方法:
    - get_historical(): 先查缓存，缺失部分从交易所补全（缓存穿透）
    - get_live(): 从Hyperliquid获取最新K线（不缓存，每次实时拉取）
    - seed(): 批量下载历史数据到本地缓存
    - get_training_dataset(): 多币种OHLCV堆叠，用于ML训练
    - get_training_dataset_with_alt(): 同上，但额外合并funding rate等替代数据
    """

    def __init__(self, cache_dir: Optional[str] = None):
        self.cache = ParquetCache(cache_dir) if cache_dir else ParquetCache()
        self.alt_cache = AltDataCache(cache_dir) if cache_dir else AltDataCache()
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
        """获取历史K线数据（缓存穿透模式）。

        流程: 读缓存 -> 检测时间范围缺口 -> 从交易所补全缺失部分 -> 合并写回缓存
        输入: 币种、K线间隔、起止时间戳(毫秒)、数据源
        输出: OHLCV DataFrame [timestamp, open, high, low, close, volume]
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
        """从Hyperliquid获取最新K线（实盘用，不走缓存）。"""
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

    def get_training_dataset(
        self,
        symbols: list[str],
        interval: str = "1h",
        start_ms: int = 1609459200000,  # 2021-01-01
        end_ms: int | None = None,
        source: str = "okx",
    ) -> pd.DataFrame:
        """Load and stack OHLCV data for multiple symbols into a single DataFrame.

        Returns DataFrame with columns: timestamp, open, high, low, close, volume, symbol
        Sorted by (symbol, timestamp).
        """
        if end_ms is None:
            end_ms = utc_now_ms()

        frames = []
        for sym in symbols:
            df = self.get_historical(sym, interval, start_ms, end_ms, source=source)
            if df.empty:
                logger.warning("No data for %s, skipping", sym)
                continue
            df = df.copy()
            df["symbol"] = sym
            frames.append(df)

        if not frames:
            return pd.DataFrame()

        combined = pd.concat(frames, ignore_index=True)
        combined.sort_values(["symbol", "timestamp"], inplace=True)
        combined.reset_index(drop=True, inplace=True)
        logger.info(
            "Training dataset: %d rows, %d symbols, %s to %s",
            len(combined), len(frames),
            combined["timestamp"].min(), combined["timestamp"].max(),
        )
        return combined

    # ------------------------------------------------------------------
    # Alternative data: funding rates, order book, open interest
    # ------------------------------------------------------------------

    def seed_funding(
        self,
        symbol: str,
        start_ms: int,
        end_ms: Optional[int] = None,
    ) -> pd.DataFrame:
        """Download and cache funding rate history from Hyperliquid."""
        if end_ms is None:
            end_ms = utc_now_ms()

        # Check cache for existing data
        cached_min, cached_max = self.alt_cache.get_cached_range("funding", symbol)
        if cached_max is not None:
            # Only fetch what's new
            fetch_start = cached_max + 1
            if fetch_start >= end_ms:
                logger.info("Funding %s already up to date", symbol)
                return self.alt_cache.read("funding", symbol)
        else:
            fetch_start = start_ms

        logger.info("Fetching funding %s: %d -> %d", symbol, fetch_start, end_ms)
        df = fetch_funding_history(symbol, fetch_start, end_ms)
        if not df.empty:
            self.alt_cache.merge_and_write("funding", symbol, df)
            logger.info("Cached %d funding records for %s", len(df), symbol)
        return self.alt_cache.read("funding", symbol)

    def get_funding(self, symbol: str) -> pd.DataFrame:
        """Read cached funding rate data."""
        return self.alt_cache.read("funding", symbol)

    def get_l2_snapshot(self, symbol: str) -> dict:
        """Fetch live L2 order book snapshot."""
        return fetch_l2_snapshot(symbol)

    def get_meta_snapshot(self) -> pd.DataFrame:
        """Fetch live meta info (OI, funding, mark price) for all perps."""
        return fetch_meta_snapshot()

    def merge_funding_with_ohlcv(
        self,
        ohlcv_df: pd.DataFrame,
        symbol: str,
    ) -> pd.DataFrame:
        """Merge funding rate data into OHLCV DataFrame using forward-fill.

        Funding settles every 8 hours, so we forward-fill to match the OHLCV
        interval (typically 1H). This is safe because funding settlements are
        known at their timestamp and don't change retroactively.
        """
        funding = self.get_funding(symbol)
        if funding.empty:
            ohlcv_df["funding_rate"] = float("nan")
            ohlcv_df["premium"] = float("nan")
            return ohlcv_df

        # Merge on nearest timestamp (funding is sparse — every 8h)
        ohlcv_df = ohlcv_df.copy()
        ohlcv_df = pd.merge_asof(
            ohlcv_df.sort_values("timestamp"),
            funding[["timestamp", "funding_rate", "premium"]].sort_values("timestamp"),
            on="timestamp",
            direction="backward",
        )
        return ohlcv_df

    def get_training_dataset_with_alt(
        self,
        symbols: list[str],
        interval: str = "1h",
        start_ms: int = 1609459200000,
        end_ms: int | None = None,
        source: str = "okx",
    ) -> pd.DataFrame:
        """Load OHLCV + alternative data for multiple symbols.

        Same as get_training_dataset but merges in funding rate data.
        """
        if end_ms is None:
            end_ms = utc_now_ms()

        frames = []
        for sym in symbols:
            df = self.get_historical(sym, interval, start_ms, end_ms, source=source)
            if df.empty:
                logger.warning("No data for %s, skipping", sym)
                continue
            df = df.copy()
            df["symbol"] = sym

            # Merge funding data
            df = self.merge_funding_with_ohlcv(df, sym)
            frames.append(df)

        if not frames:
            return pd.DataFrame()

        combined = pd.concat(frames, ignore_index=True)
        combined.sort_values(["symbol", "timestamp"], inplace=True)
        combined.reset_index(drop=True, inplace=True)
        logger.info(
            "Training dataset (with alt): %d rows, %d symbols",
            len(combined), len(frames),
        )
        return combined
