"""Cross-asset features: BTC-relative returns, correlation, beta."""

from __future__ import annotations

import numpy as np
import pandas as pd

from cryptolab.features.base import FeatureBlock


class CrossAssetFeatures(FeatureBlock):
    """~10 cross-asset features. Requires 'symbol' column and BTC data in DataFrame."""

    CORR_WINDOWS = [24, 72, 168]

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        if "symbol" not in df.columns:
            # Single-symbol mode: skip cross-asset features (fill with NaN)
            for name in self.feature_names():
                df[name] = np.nan
            return df

        c = df["close"].shift(1)
        log_ret = np.log(c / c.shift(1))

        # Get BTC returns as reference
        btc_mask = df["symbol"] == "BTC"
        if not btc_mask.any():
            for name in self.feature_names():
                df[name] = np.nan
            return df

        btc_ret = log_ret.where(btc_mask).reindex(df.index)

        # For cross-asset features, we need to align by timestamp
        # Build a BTC return lookup by timestamp
        btc_df = df.loc[btc_mask, ["timestamp"]].copy()
        btc_df["btc_ret"] = log_ret.loc[btc_mask].values

        df = df.merge(btc_df, on="timestamp", how="left", suffixes=("", "_btc"))

        # Return relative to BTC
        df["ret_vs_btc"] = log_ret - df["btc_ret"]

        # Rolling correlation with BTC
        for w in self.CORR_WINDOWS:
            df[f"corr_btc_{w}"] = log_ret.rolling(w, min_periods=w).corr(df["btc_ret"])

        # Rolling beta to BTC
        cov_72 = log_ret.rolling(72, min_periods=72).cov(df["btc_ret"])
        var_72 = df["btc_ret"].rolling(72, min_periods=72).var()
        df["beta_btc_72"] = cov_72 / var_72.replace(0, np.nan)

        # Cross-sectional rank (within symbols at each timestamp)
        # ROC_24 rank across all symbols
        roc_24 = c / c.shift(24) - 1
        df["cs_rank"] = roc_24.groupby(df["timestamp"]).rank(pct=True)

        # Clean up temp column
        df.drop(columns=["btc_ret"], inplace=True, errors="ignore")

        return df

    def feature_names(self) -> list[str]:
        names = ["ret_vs_btc"]
        for w in self.CORR_WINDOWS:
            names.append(f"corr_btc_{w}")
        names.extend(["beta_btc_72", "cs_rank"])
        return names
