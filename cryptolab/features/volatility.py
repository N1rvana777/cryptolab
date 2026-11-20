"""Volatility features: realized vol, Parkinson, Garman-Klass, vol-of-vol, regime."""

from __future__ import annotations

import numpy as np
import pandas as pd

from cryptolab.features.base import FeatureBlock

VOL_WINDOWS = [6, 24, 72, 168]


class VolatilityFeatures(FeatureBlock):
    """~18 volatility features."""

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        c = df["close"].shift(1)
        h = df["high"].shift(1)
        l = df["low"].shift(1)  # noqa: E741

        log_ret = np.log(c / c.shift(1))

        for w in VOL_WINDOWS:
            # Realized volatility (close-to-close)
            rv = log_ret.rolling(w, min_periods=w).std()
            df[f"rvol_{w}"] = rv

            # Parkinson volatility estimator
            log_hl = np.log(h / l.replace(0, np.nan))
            park = (log_hl ** 2 / (4 * np.log(2))).rolling(w, min_periods=w).mean().pipe(np.sqrt)
            df[f"parkinson_{w}"] = park

        # Garman-Klass at 24 and 72
        for w in [24, 72]:
            log_hl = np.log(h / l.replace(0, np.nan))
            log_co = np.log(c / df["open"].shift(1).replace(0, np.nan))
            gk = (0.5 * log_hl ** 2 - (2 * np.log(2) - 1) * log_co ** 2).rolling(
                w, min_periods=w
            ).mean().pipe(np.sqrt)
            df[f"gk_vol_{w}"] = gk

        # Vol-of-vol (std of realized vol)
        rv_24 = log_ret.rolling(24, min_periods=24).std()
        df["vol_of_vol_72"] = rv_24.rolling(72, min_periods=72).std()
        df["vol_of_vol_168"] = rv_24.rolling(168, min_periods=168).std()

        # Vol regime: short-term vol / long-term vol
        rv_short = log_ret.rolling(24, min_periods=24).std()
        rv_long = log_ret.rolling(168, min_periods=168).std()
        df["vol_regime"] = rv_short / rv_long.replace(0, np.nan)

        # ATR percentile rank (rolling 168-bar window)
        from cryptolab.features.technical import _atr
        atr_14 = _atr(h, l, c, 14)
        df["atr_pctrank"] = atr_14.rolling(168, min_periods=168).apply(
            lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=False
        )

        return df

    def feature_names(self) -> list[str]:
        names = []
        for w in VOL_WINDOWS:
            names.extend([f"rvol_{w}", f"parkinson_{w}"])
        for w in [24, 72]:
            names.append(f"gk_vol_{w}")
        names.extend(["vol_of_vol_72", "vol_of_vol_168", "vol_regime", "atr_pctrank"])
        return names
