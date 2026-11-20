"""Momentum features: TSMOM, ROC, acceleration, mean-reversion z-score."""

from __future__ import annotations

import numpy as np
import pandas as pd

from cryptolab.features.base import FeatureBlock

TSMOM_LOOKBACKS = [6, 24, 72, 168]
ROC_HORIZONS = [1, 6, 24, 72]


class MomentumFeatures(FeatureBlock):
    """~16 momentum features."""

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        c = df["close"].shift(1)

        # TSMOM: return / vol (same logic as indicators/core.py compute_tsmom)
        log_ret = np.log(c / c.shift(1))
        for lb in TSMOM_LOOKBACKS:
            ret = c / c.shift(lb) - 1
            vol = log_ret.rolling(lb, min_periods=max(2, lb // 2)).std()
            raw = ret / (vol * np.sqrt(lb)).replace(0, np.nan)
            df[f"tsmom_{lb}"] = (raw / 2.5).clip(-1, 1)

        # Rate of change (simple returns)
        for h in ROC_HORIZONS:
            df[f"roc_{h}"] = c / c.shift(h) - 1

        # Acceleration: ROC(6) - ROC(24) (short-term momentum vs medium-term)
        df["momentum_accel"] = df.get("roc_6", c / c.shift(6) - 1) - df.get("roc_24", c / c.shift(24) - 1)

        # Mean-reversion z-score at windows 24, 72
        for w in [24, 72]:
            mean = c.rolling(w, min_periods=w).mean()
            std = c.rolling(w, min_periods=w).std()
            df[f"mr_zscore_{w}"] = (c - mean) / std.replace(0, np.nan)

        # Drawdown from rolling peak
        peak_72 = c.rolling(72, min_periods=1).max()
        df["dd_from_peak_72"] = (c - peak_72) / peak_72.replace(0, np.nan)

        # Days since new high (at 72-bar horizon)
        is_new_high = (c == peak_72).astype(float)
        df["bars_since_high_72"] = is_new_high.groupby(
            (is_new_high != is_new_high.shift()).cumsum()
        ).cumcount()
        # Normalize to 0-1 range
        df["bars_since_high_72"] = df["bars_since_high_72"] / 72.0

        return df

    def feature_names(self) -> list[str]:
        names = []
        for lb in TSMOM_LOOKBACKS:
            names.append(f"tsmom_{lb}")
        for h in ROC_HORIZONS:
            names.append(f"roc_{h}")
        names.extend([
            "momentum_accel",
            "mr_zscore_24", "mr_zscore_72",
            "dd_from_peak_72", "bars_since_high_72",
        ])
        return names
