"""Portfolio-level risk budgeting and volatility targeting."""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def inverse_vol_weights(
    returns_dict: dict[str, pd.Series],
    lookback: int = 72,
) -> dict[str, float]:
    """Compute inverse-volatility weights for portfolio allocation.

    Symbols with lower volatility get higher weight (risk parity lite).
    """
    vols = {}
    for sym, rets in returns_dict.items():
        if len(rets) < lookback:
            vols[sym] = 1.0
        else:
            vols[sym] = max(rets.tail(lookback).std(), 1e-8)

    inv_vols = {sym: 1.0 / v for sym, v in vols.items()}
    total = sum(inv_vols.values())

    return {sym: iv / total for sym, iv in inv_vols.items()}


def correlation_matrix(
    returns_dict: dict[str, pd.Series],
    lookback: int = 168,
) -> pd.DataFrame:
    """Compute rolling correlation matrix across symbols."""
    df = pd.DataFrame(returns_dict)
    return df.tail(lookback).corr()


def portfolio_vol(
    weights: dict[str, float],
    returns_dict: dict[str, pd.Series],
    lookback: int = 168,
) -> float:
    """Estimate annualized portfolio volatility."""
    symbols = list(weights.keys())
    w = np.array([weights[s] for s in symbols])

    df = pd.DataFrame({s: returns_dict[s] for s in symbols}).tail(lookback).dropna()
    if len(df) < 10:
        return 0.0

    cov = df.cov().values
    port_var = w @ cov @ w
    # Annualize (assuming 1H bars, 8760 bars/year)
    return float(np.sqrt(port_var * 8760))
