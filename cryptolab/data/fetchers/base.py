"""Base fetcher ABC."""

from abc import ABC, abstractmethod
import pandas as pd


class BaseFetcher(ABC):
    """All data fetchers must implement fetch_ohlcv()."""

    source_name: str = "base"

    @abstractmethod
    def fetch_ohlcv(
        self,
        symbol: str,
        interval: str,
        start_ms: int,
        end_ms: int,
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data for a symbol in the given time range.

        Args:
            symbol: canonical symbol (e.g. "BTC")
            interval: candle interval (e.g. "4h")
            start_ms: start timestamp in milliseconds (inclusive)
            end_ms: end timestamp in milliseconds (exclusive)

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        raise NotImplementedError
