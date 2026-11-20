"""Microstructure features: volume profile, VWAP, price-volume dynamics."""

from __future__ import annotations

import numpy as np
import pandas as pd

from cryptolab.features.base import FeatureBlock


class MicrostructureFeatures(FeatureBlock):
    """~15 volume and microstructure features."""

    VOL_LOOKBACKS = [6, 12, 24]

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        o = df["open"].shift(1)
        h = df["high"].shift(1)
        l = df["low"].shift(1)  # noqa: E741
        c = df["close"].shift(1)
        v = df["volume"].shift(1)

        # Volume ratio at multiple lookbacks
        for lb in self.VOL_LOOKBACKS:
            avg_v = v.rolling(lb, min_periods=lb).mean()
            df[f"vol_ratio_{lb}"] = v / avg_v.replace(0, np.nan)

        # Volume momentum (rate of change of volume)
        df["vol_roc_6"] = v / v.shift(6).replace(0, np.nan) - 1
        df["vol_roc_24"] = v / v.shift(24).replace(0, np.nan) - 1

        # VWAP distance (rolling 24-bar VWAP)
        vwap_num = (c * v).rolling(24, min_periods=24).sum()
        vwap_den = v.rolling(24, min_periods=24).sum()
        vwap = vwap_num / vwap_den.replace(0, np.nan)
        df["vwap_dist"] = (c - vwap) / vwap.replace(0, np.nan)

        # Spread proxy: (high - low) / close (intrabar volatility)
        df["spread_proxy"] = (h - l) / c.replace(0, np.nan)
        df["spread_proxy_ma"] = df["spread_proxy"].rolling(24, min_periods=24).mean()

        # Price-volume divergence: price up but volume down (bearish) or vice versa
        price_dir = np.sign(c.diff())
        vol_dir = np.sign(v.diff())
        df["pv_divergence"] = (price_dir * vol_dir)  # -1 = divergence

        # Up-volume ratio: volume on up-bars / total volume (24-bar window)
        up_vol = v.where(c.diff() > 0, 0)
        df["up_vol_ratio_24"] = (
            up_vol.rolling(24, min_periods=24).sum()
            / v.rolling(24, min_periods=24).sum().replace(0, np.nan)
        )

        # Volume concentration: max single-bar volume / total volume (24-bar)
        df["vol_concentration_24"] = (
            v.rolling(24, min_periods=24).max()
            / v.rolling(24, min_periods=24).sum().replace(0, np.nan)
        )

        return df

    def feature_names(self) -> list[str]:
        names = []
        for lb in self.VOL_LOOKBACKS:
            names.append(f"vol_ratio_{lb}")
        names.extend([
            "vol_roc_6", "vol_roc_24",
            "vwap_dist",
            "spread_proxy", "spread_proxy_ma",
            "pv_divergence",
            "up_vol_ratio_24",
            "vol_concentration_24",
        ])
        return names
