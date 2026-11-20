"""Temporal / calendar features with cyclical encoding.

Ported from RetailLab's temporal_features.py, adapted for crypto (24/7 market).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from cryptolab.features.base import FeatureBlock


class TemporalFeatures(FeatureBlock):
    """~12 calendar and session features."""

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        ts = df["timestamp"]

        # Hour of day (cyclical)
        hour = ts.dt.hour
        df["hour_sin"] = np.sin(2 * np.pi * hour / 24)
        df["hour_cos"] = np.cos(2 * np.pi * hour / 24)

        # Day of week (cyclical)
        dow = ts.dt.dayofweek
        df["dow_sin"] = np.sin(2 * np.pi * dow / 7)
        df["dow_cos"] = np.cos(2 * np.pi * dow / 7)

        # Month (cyclical)
        month = ts.dt.month
        df["month_sin"] = np.sin(2 * np.pi * month / 12)
        df["month_cos"] = np.cos(2 * np.pi * month / 12)

        # Trading session flags (approximate)
        df["is_asia"] = ((hour >= 0) & (hour < 8)).astype(np.float64)
        df["is_europe"] = ((hour >= 8) & (hour < 16)).astype(np.float64)
        df["is_us"] = ((hour >= 13) & (hour < 22)).astype(np.float64)

        # Weekend flag
        df["is_weekend"] = (dow >= 5).astype(np.float64)

        # Quarter
        df["quarter"] = ts.dt.quarter.astype(np.float64)

        # Day of month (for end-of-month effects)
        df["dom"] = ts.dt.day.astype(np.float64)

        return df

    def feature_names(self) -> list[str]:
        return [
            "hour_sin", "hour_cos",
            "dow_sin", "dow_cos",
            "month_sin", "month_cos",
            "is_asia", "is_europe", "is_us",
            "is_weekend", "quarter", "dom",
        ]
