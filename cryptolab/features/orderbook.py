"""Order book features: depth imbalance, spread, depth skew.

These features are computed from periodic L2 order book snapshots that have
been merged into the OHLCV DataFrame as extra columns. The snapshot columns
are:
    ob_bid_depth   — total bid-side USD depth
    ob_ask_depth   — total ask-side USD depth
    ob_spread_bps  — bid-ask spread in basis points
    ob_imbalance   — (bid - ask) / (bid + ask), range [-1, 1]

If these columns are absent, all features are filled with NaN.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from cryptolab.features.base import FeatureBlock


class OrderBookFeatures(FeatureBlock):
    """Features from L2 order book snapshots."""

    LOOKBACKS = [6, 24, 72]

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        required = ["ob_imbalance", "ob_spread_bps", "ob_bid_depth", "ob_ask_depth"]
        has_ob = all(col in df.columns for col in required)

        if not has_ob:
            for name in self.feature_names():
                df[name] = np.nan
            return df

        # Shift all OB data by 1 bar to prevent look-ahead
        imb = df["ob_imbalance"].shift(1)
        spread = df["ob_spread_bps"].shift(1)
        bid_d = df["ob_bid_depth"].shift(1)
        ask_d = df["ob_ask_depth"].shift(1)
        total_d = bid_d + ask_d

        # --- Raw features ---
        df["ob_imb"] = imb
        df["ob_spread"] = spread
        df["ob_depth_ratio"] = bid_d / ask_d.replace(0, np.nan)

        # --- Rolling statistics ---
        for lb in self.LOOKBACKS:
            # Imbalance moving average and z-score
            imb_ma = imb.rolling(lb, min_periods=lb).mean()
            imb_std = imb.rolling(lb, min_periods=lb).std()
            df[f"ob_imb_ma_{lb}"] = imb_ma
            df[f"ob_imb_zscore_{lb}"] = (imb - imb_ma) / imb_std.replace(0, np.nan)

            # Spread dynamics
            spread_ma = spread.rolling(lb, min_periods=lb).mean()
            df[f"ob_spread_ma_{lb}"] = spread_ma
            df[f"ob_spread_ratio_{lb}"] = spread / spread_ma.replace(0, np.nan)

            # Depth change (total depth momentum)
            df[f"ob_depth_chg_{lb}"] = total_d / total_d.shift(lb).replace(0, np.nan) - 1

        # --- Derived signals ---

        # Imbalance momentum: short MA vs long MA
        df["ob_imb_momentum"] = df["ob_imb_ma_6"] - df["ob_imb_ma_72"]

        # Imbalance persistence: how consistently biased is the book
        imb_sign = np.sign(imb)
        df["ob_imb_persist"] = (
            imb_sign.rolling(24, min_periods=24)
            .apply(lambda x: np.abs(x.sum()) / len(x), raw=True)
        )

        # Depth-weighted imbalance: scale imbalance by total depth (more meaningful when deep)
        depth_norm = total_d / total_d.rolling(72, min_periods=72).mean().replace(0, np.nan)
        df["ob_imb_depth_weighted"] = imb * depth_norm

        # Spread regime: current spread vs 72-bar median
        spread_median = spread.rolling(72, min_periods=72).median()
        df["ob_spread_regime"] = spread / spread_median.replace(0, np.nan)

        return df

    def feature_names(self) -> list[str]:
        names = ["ob_imb", "ob_spread", "ob_depth_ratio"]
        for lb in self.LOOKBACKS:
            names.extend([
                f"ob_imb_ma_{lb}",
                f"ob_imb_zscore_{lb}",
                f"ob_spread_ma_{lb}",
                f"ob_spread_ratio_{lb}",
                f"ob_depth_chg_{lb}",
            ])
        names.extend([
            "ob_imb_momentum",
            "ob_imb_persist",
            "ob_imb_depth_weighted",
            "ob_spread_regime",
        ])
        return names
