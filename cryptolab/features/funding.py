"""Funding rate features: carry signal, crowding indicator, mean-reversion."""

from __future__ import annotations

import numpy as np
import pandas as pd

from cryptolab.features.base import FeatureBlock


class FundingFeatures(FeatureBlock):
    """Features derived from perpetual funding rates.

    Expects column 'funding_rate' in the input DataFrame (merged from alt data).
    If absent, fills all features with NaN (graceful degradation).

    Key signals:
    - Funding rate level: positive = longs pay shorts (crowded long)
    - Funding rate z-score: extreme values predict reversals
    - Cumulative funding: carry cost for holding positions
    - Funding momentum: acceleration of crowding
    """

    LOOKBACKS = [8, 24, 72]  # 8h intervals → 1 day, 3 days, 9 days at 8h

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        if "funding_rate" not in df.columns:
            for name in self.feature_names():
                df[name] = np.nan
            return df

        # Shift to avoid look-ahead: use previous funding settlement
        fr = df["funding_rate"].shift(1)

        # Raw funding rate (already shifted)
        df["fr_raw"] = fr

        # Rolling statistics at multiple lookbacks
        for lb in self.LOOKBACKS:
            ma = fr.rolling(lb, min_periods=lb).mean()
            std = fr.rolling(lb, min_periods=lb).std()

            df[f"fr_ma_{lb}"] = ma
            df[f"fr_zscore_{lb}"] = (fr - ma) / std.replace(0, np.nan)

            # Cumulative funding (carry cost over window)
            df[f"fr_cumsum_{lb}"] = fr.rolling(lb, min_periods=lb).sum()

        # Funding momentum: change in moving average
        fr_ma_short = df["fr_ma_8"]
        fr_ma_long = df["fr_ma_72"]
        df["fr_momentum"] = fr_ma_short - fr_ma_long

        # Funding extreme indicator: >2 std from 72-period mean
        df["fr_extreme"] = df["fr_zscore_72"].abs()

        # Sign persistence: fraction of last 24 periods with same sign
        fr_sign = np.sign(fr)
        df["fr_sign_persist"] = (
            fr_sign.rolling(24, min_periods=24)
            .apply(lambda x: np.abs(x.sum()) / len(x), raw=True)
        )

        # Premium (if available)
        if "premium" in df.columns:
            prem = df["premium"].shift(1)
            df["prem_raw"] = prem
            df["prem_ma_24"] = prem.rolling(24, min_periods=24).mean()
        else:
            df["prem_raw"] = np.nan
            df["prem_ma_24"] = np.nan

        return df

    def feature_names(self) -> list[str]:
        names = ["fr_raw"]
        for lb in self.LOOKBACKS:
            names.extend([
                f"fr_ma_{lb}",
                f"fr_zscore_{lb}",
                f"fr_cumsum_{lb}",
            ])
        names.extend([
            "fr_momentum",
            "fr_extreme",
            "fr_sign_persist",
            "prem_raw",
            "prem_ma_24",
        ])
        return names
