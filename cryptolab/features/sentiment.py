"""Fear & Greed Index features: market-wide sentiment signal.

Data source: alternative.me FNG API (daily, 0-100 scale).
Since FNG is daily but OHLCV is hourly, we join by date and forward-fill
within each day. All features use shift(1) to prevent look-ahead bias —
today's FNG reading is only available at end-of-day, so we use yesterday's.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from cryptolab.features.base import FeatureBlock

# Default path to cached FNG CSV
_FNG_CSV = Path(__file__).resolve().parent.parent.parent / "data" / "fng_history.csv"


class SentimentFeatures(FeatureBlock):
    """Features derived from the Crypto Fear & Greed Index.

    Expects OHLCV DataFrame with a 'timestamp' column (pd.Timestamp, UTC).
    Loads FNG CSV, joins by date, and computes rolling features.
    If FNG CSV is missing, fills all features with NaN (graceful degradation).
    """

    def __init__(self, fng_path: str | Path | None = None) -> None:
        self._fng_path = Path(fng_path) if fng_path else _FNG_CSV

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        fng = self._load_fng()
        if fng is None:
            for name in self.feature_names():
                df[name] = np.nan
            return df

        # Extract date from timestamp for joining
        df = df.copy()
        df["_date"] = pd.to_datetime(df["timestamp"]).dt.date

        # Merge FNG by date (left join — keep all OHLCV rows)
        df = df.merge(fng[["_date", "fng_value"]], on="_date", how="left")

        # Forward-fill within each day (FNG is daily, OHLCV is hourly)
        df["fng_value"] = df["fng_value"].ffill()

        # CRITICAL: shift(1) to prevent look-ahead bias
        # FNG for "today" is published at end-of-day, so we can only use
        # yesterday's value for today's features
        fng_shifted = df["fng_value"].shift(1)

        # Normalize to 0-1 range
        df["fng_raw"] = fng_shifted / 100.0

        # Rolling moving averages (on shifted data)
        df["fng_ma_7"] = fng_shifted.rolling(7 * 24, min_periods=7 * 24).mean() / 100.0
        df["fng_ma_30"] = fng_shifted.rolling(30 * 24, min_periods=30 * 24).mean() / 100.0

        # Z-score: how far is current FNG from its 30-day mean
        ma_30 = fng_shifted.rolling(30 * 24, min_periods=30 * 24).mean()
        std_30 = fng_shifted.rolling(30 * 24, min_periods=30 * 24).std()
        df["fng_zscore_30"] = (fng_shifted - ma_30) / std_30.replace(0, np.nan)

        # Cleanup temp column
        df.drop(columns=["_date", "fng_value"], inplace=True)

        return df

    def feature_names(self) -> list[str]:
        return [
            "fng_raw",
            "fng_ma_7",
            "fng_ma_30",
            "fng_zscore_30",
        ]

    def _load_fng(self) -> pd.DataFrame | None:
        """Load FNG CSV. Returns None if file not found."""
        if not self._fng_path.exists():
            import logging
            logging.getLogger(__name__).warning(
                "FNG CSV not found at %s — sentiment features will be NaN",
                self._fng_path,
            )
            return None

        fng = pd.read_csv(self._fng_path, parse_dates=["date"])
        fng["_date"] = fng["date"].dt.date
        return fng
