"""Donchian channel features: wraps existing DonchianMTF logic as ML features.

Preserves the current strategy's core signal (MTF agreement score) as one
feature input to the ML model, alongside channel-derived metrics.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from cryptolab.features.base import FeatureBlock

LOOKBACKS = [24, 72, 168]


class DonchianFeatures(FeatureBlock):
    """~13 Donchian channel features at multiple lookbacks."""

    def __init__(self, lookbacks: list[int] | None = None) -> None:
        self.lookbacks = lookbacks or LOOKBACKS

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        # Use shifted data to prevent leakage
        h = df["high"].shift(1)
        l = df["low"].shift(1)  # noqa: E741
        c = df["close"].shift(1)

        signals = []
        for lb in self.lookbacks:
            upper = h.rolling(lb, min_periods=lb).max()
            lower = l.rolling(lb, min_periods=lb).min()
            mid = (upper + lower) / 2

            # Distance from bands (normalized)
            spread = (upper - lower).replace(0, np.nan)
            df[f"dc_dist_upper_{lb}"] = (c - upper) / spread
            df[f"dc_dist_lower_{lb}"] = (c - lower) / spread

            # Channel width normalized by close
            df[f"dc_width_{lb}"] = spread / c.replace(0, np.nan)

            # Breakout signal: +1 if close at upper, -1 if at lower, 0 otherwise
            signal = pd.Series(0.0, index=df.index)
            signal = signal.where(c < upper, 1.0)
            signal = signal.where(c > lower, -1.0)
            signals.append(signal)
            df[f"dc_breakout_{lb}"] = signal

        # MTF agreement score (weighted average of signals)
        # Equal weights, matching the current DonchianMTF defaults
        n = len(self.lookbacks)
        agreement = sum(signals) / n
        df["dc_mtf_agreement"] = agreement

        return df

    def feature_names(self) -> list[str]:
        names = []
        for lb in self.lookbacks:
            names.extend([
                f"dc_dist_upper_{lb}",
                f"dc_dist_lower_{lb}",
                f"dc_width_{lb}",
                f"dc_breakout_{lb}",
            ])
        names.append("dc_mtf_agreement")
        return names
