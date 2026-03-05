"""Parquet cache: read/write/merge OHLCV data. One file per (source, symbol, interval)."""

import os
import logging
import pandas as pd

from cryptolab.data.types import OHLCV_COLUMNS

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "cache")


class ParquetCache:
    def __init__(self, cache_dir: str = DEFAULT_CACHE_DIR):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def _path(self, source: str, symbol: str, interval: str) -> str:
        return os.path.join(self.cache_dir, f"{source}_{symbol}_{interval}.parquet")

    def read(self, source: str, symbol: str, interval: str) -> pd.DataFrame:
        path = self._path(source, symbol, interval)
        if not os.path.exists(path):
            return pd.DataFrame(columns=OHLCV_COLUMNS)
        try:
            df = pd.read_parquet(path)
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
            return df.sort_values("timestamp").reset_index(drop=True)
        except Exception as e:
            logger.warning(f"Cache read error {path}: {e}")
            return pd.DataFrame(columns=OHLCV_COLUMNS)

    def write(self, source: str, symbol: str, interval: str, df: pd.DataFrame):
        if df.empty:
            return
        path = self._path(source, symbol, interval)
        df.to_parquet(path, index=False, engine="pyarrow")
        logger.debug(f"Cache written: {path} ({len(df)} rows)")

    def merge_and_write(self, source: str, symbol: str, interval: str, new_df: pd.DataFrame):
        """Merge new data with existing cache, deduplicate, and write."""
        if new_df.empty:
            return
        existing = self.read(source, symbol, interval)
        if existing.empty:
            combined = new_df
        else:
            combined = pd.concat([existing, new_df], ignore_index=True)
        combined = combined.sort_values("timestamp").drop_duplicates(subset="timestamp").reset_index(drop=True)
        self.write(source, symbol, interval, combined)

    def get_cached_range(self, source: str, symbol: str, interval: str) -> tuple:
        """Return (min_ts_ms, max_ts_ms) of cached data, or (None, None)."""
        df = self.read(source, symbol, interval)
        if df.empty:
            return None, None
        min_ts = int(df["timestamp"].min().timestamp() * 1000)
        max_ts = int(df["timestamp"].max().timestamp() * 1000)
        return min_ts, max_ts
