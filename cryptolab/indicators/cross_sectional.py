"""Cross-sectional momentum: rank coins by relative TSMOM strength."""

import math
from typing import Dict

import pandas as pd


def _rolling_tsmom(closes: pd.Series, lookback: int) -> pd.Series:
    """Vectorized rolling TSMOM score (same logic as compute_tsmom)."""
    ret = closes / closes.shift(lookback) - 1
    bar_rets = closes.pct_change()
    roll_vol = bar_rets.rolling(lookback, min_periods=max(2, lookback // 2)).std()
    raw = ret / (roll_vol * math.sqrt(lookback))
    scaled = raw / 2.5
    return scaled.clip(-1.0, 1.0)


def compute_cs_multipliers(
    symbol_dfs: Dict[str, pd.DataFrame],
    lookback: int = 168,
    cs_weight: float = 0.3,
) -> Dict[str, dict]:
    """Pre-compute cross-sectional position multipliers for each symbol.

    Returns dict[symbol, dict[timestamp, multiplier]].
    Multiplier = 1 + cs_weight * z_score, clamped [0.5, 1.5],
    normalized so multipliers sum to N (capital-preserving).
    """
    if cs_weight <= 0 or len(symbol_dfs) < 2:
        return {sym: {} for sym in symbol_dfs}

    # Compute rolling TSMOM for each symbol
    tsmom_series = {}
    for sym, df in symbol_dfs.items():
        ts_col = "timestamp" if "timestamp" in df.columns else df.index.name
        if ts_col == "timestamp":
            scores = _rolling_tsmom(df["close"], lookback)
            tsmom_series[sym] = pd.DataFrame({"timestamp": df["timestamp"], "tsmom": scores})
        else:
            scores = _rolling_tsmom(df["close"], lookback)
            tsmom_series[sym] = pd.DataFrame({"timestamp": df.index, "tsmom": scores.values})

    # Merge all on timestamp (inner join)
    merged = None
    symbols = list(symbol_dfs.keys())
    for sym in symbols:
        ts_df = tsmom_series[sym].rename(columns={"tsmom": f"tsmom_{sym}"})
        if merged is None:
            merged = ts_df
        else:
            merged = merged.merge(ts_df, on="timestamp", how="inner")

    if merged is None or len(merged) == 0:
        return {sym: {} for sym in symbol_dfs}

    # Z-score across coins at each timestamp
    tsmom_cols = [f"tsmom_{sym}" for sym in symbols]
    tsmom_vals = merged[tsmom_cols]

    row_mean = tsmom_vals.mean(axis=1)
    row_std = tsmom_vals.std(axis=1, ddof=0)
    row_std = row_std.replace(0, 1.0)  # avoid division by zero

    # Compute raw multipliers
    result = {}
    for sym in symbols:
        z = (merged[f"tsmom_{sym}"] - row_mean) / row_std
        raw_mult = 1.0 + cs_weight * z
        mult = raw_mult.clip(0.5, 1.5)
        result[sym] = mult

    # Normalize so multipliers sum to N at each row
    n = len(symbols)
    mult_sum = sum(result[sym] for sym in symbols)
    for sym in symbols:
        normalized = result[sym] / mult_sum * n
        # Build timestamp -> multiplier lookup dict
        result[sym] = dict(zip(merged["timestamp"], normalized))

    return result
