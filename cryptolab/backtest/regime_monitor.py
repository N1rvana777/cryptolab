"""Market regime and concept drift monitor.

Detects choppy/ranging markets via rolling ADX and rolling Sharpe,
emits REGIME_WARNING entries for post-mortem analysis of dd_scalar behavior.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import List, Optional, TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from cryptolab.backtest.engine import BacktestResult

logger = logging.getLogger(__name__)


@dataclass
class RegimeWarning:
    """A single regime warning event."""
    timestamp: str
    bar_idx: int
    symbol: str
    warning_type: str  # "LOW_ADX", "NEGATIVE_SHARPE", "BOTH"
    adx_value: Optional[float] = None
    rolling_sharpe: Optional[float] = None
    message: str = ""


@dataclass
class RegimeMonitorConfig:
    """Configuration for regime detection thresholds."""
    adx_period: int = 14
    adx_rolling_window: int = 84  # 14 days at 4H
    adx_threshold: float = 20.0
    sharpe_rolling_window: int = 84  # 14 days at 4H
    sharpe_threshold: float = 0.0  # warn if below this


def compute_rolling_adx(
    ohlcv_df: pd.DataFrame,
    period: int = 14,
    rolling_window: int = 84,
) -> pd.Series:
    """Compute rolling ADX over a sliding window.

    For each bar, computes ADX using the last `rolling_window` bars of data.
    Returns a Series aligned with ohlcv_df index.
    """
    from cryptolab.indicators.core import compute_adx

    n = len(ohlcv_df)
    adx_values = pd.Series(np.nan, index=ohlcv_df.index)
    min_bars = max(rolling_window, 2 * period + 1)

    for i in range(min_bars, n):
        start = max(0, i - rolling_window)
        window = ohlcv_df.iloc[start:i + 1]
        candles = [
            {"h": row["high"], "l": row["low"], "c": row["close"]}
            for _, row in window.iterrows()
        ]
        result = compute_adx(candles, period)
        if result is not None:
            adx_values.iloc[i] = result["adx"]

    return adx_values


def compute_rolling_sharpe(
    equity_series: pd.Series,
    window: int = 84,
    periods_per_year: float = 2190,
) -> pd.Series:
    """Compute rolling annualized Sharpe ratio."""
    returns = equity_series.pct_change()
    rolling_mean = returns.rolling(window).mean()
    rolling_std = returns.rolling(window).std()

    # Avoid division by zero
    safe_std = rolling_std.replace(0, np.nan)
    rolling_sharpe = (rolling_mean / safe_std) * math.sqrt(periods_per_year)

    return rolling_sharpe


def scan_regime_warnings(
    ohlcv_df: pd.DataFrame,
    equity_curve: pd.DataFrame,
    symbol: str,
    config: Optional[RegimeMonitorConfig] = None,
) -> List[RegimeWarning]:
    """Scan for regime drift warnings across the backtest period.

    Returns list of RegimeWarning events where:
    - Rolling 14-day ADX < 20 (choppy market)
    - Rolling 14-day Sharpe < 0 (strategy underperforming)
    """
    if config is None:
        config = RegimeMonitorConfig()

    warnings: List[RegimeWarning] = []

    # Compute rolling ADX
    adx_series = compute_rolling_adx(ohlcv_df, config.adx_period, config.adx_rolling_window)

    # Compute rolling Sharpe from equity curve
    eq = equity_curve["equity"]
    sharpe_series = compute_rolling_sharpe(eq, config.sharpe_rolling_window)

    # Align timestamps
    timestamps = equity_curve["timestamp"] if "timestamp" in equity_curve.columns else ohlcv_df["timestamp"]

    # Track state to avoid spamming warnings every bar
    in_low_adx = False
    in_neg_sharpe = False

    for i in range(len(timestamps)):
        if i >= len(adx_series) or i >= len(sharpe_series):
            break

        adx_val = adx_series.iloc[i] if i < len(adx_series) else np.nan
        sharpe_val = sharpe_series.iloc[i] if i < len(sharpe_series) else np.nan
        ts = str(timestamps.iloc[i])

        low_adx = not np.isnan(adx_val) and adx_val < config.adx_threshold
        neg_sharpe = not np.isnan(sharpe_val) and sharpe_val < config.sharpe_threshold

        # Emit warning on state transitions (entering bad regime)
        if low_adx and neg_sharpe and not (in_low_adx and in_neg_sharpe):
            warnings.append(RegimeWarning(
                timestamp=ts, bar_idx=i, symbol=symbol,
                warning_type="BOTH",
                adx_value=float(adx_val), rolling_sharpe=float(sharpe_val),
                message=f"REGIME_WARNING: ADX={adx_val:.1f}<{config.adx_threshold} AND "
                        f"Sharpe={sharpe_val:.2f}<0 — choppy market with negative returns",
            ))
        elif low_adx and not in_low_adx:
            warnings.append(RegimeWarning(
                timestamp=ts, bar_idx=i, symbol=symbol,
                warning_type="LOW_ADX",
                adx_value=float(adx_val),
                message=f"REGIME_WARNING: ADX={adx_val:.1f}<{config.adx_threshold} — "
                        f"market entering ranging/choppy period",
            ))
        elif neg_sharpe and not in_neg_sharpe:
            warnings.append(RegimeWarning(
                timestamp=ts, bar_idx=i, symbol=symbol,
                warning_type="NEGATIVE_SHARPE",
                rolling_sharpe=float(sharpe_val),
                message=f"REGIME_WARNING: Rolling Sharpe={sharpe_val:.2f}<0 — "
                        f"strategy in drawdown regime",
            ))

        in_low_adx = low_adx
        in_neg_sharpe = neg_sharpe

    return warnings


def regime_summary(warnings: List[RegimeWarning]) -> dict:
    """Summarize regime warnings into counts and time spans."""
    if not warnings:
        return {
            "total_warnings": 0,
            "low_adx_events": 0,
            "neg_sharpe_events": 0,
            "both_events": 0,
        }

    low_adx = [w for w in warnings if w.warning_type in ("LOW_ADX", "BOTH")]
    neg_sharpe = [w for w in warnings if w.warning_type in ("NEGATIVE_SHARPE", "BOTH")]
    both = [w for w in warnings if w.warning_type == "BOTH"]

    return {
        "total_warnings": len(warnings),
        "low_adx_events": len(low_adx),
        "neg_sharpe_events": len(neg_sharpe),
        "both_events": len(both),
        "first_warning": warnings[0].timestamp,
        "last_warning": warnings[-1].timestamp,
    }


def print_regime_warnings(warnings: List[RegimeWarning], max_display: int = 20):
    """Print regime warnings to console."""
    if not warnings:
        print("  No regime warnings detected.")
        return

    summary = regime_summary(warnings)
    print(f"\n  Regime Monitor: {summary['total_warnings']} warnings "
          f"(ADX<20: {summary['low_adx_events']}, "
          f"Sharpe<0: {summary['neg_sharpe_events']}, "
          f"Both: {summary['both_events']})")
    print("  " + "-" * 70)

    for w in warnings[:max_display]:
        adx_str = f"ADX={w.adx_value:.1f}" if w.adx_value is not None else ""
        sharpe_str = f"Sharpe={w.rolling_sharpe:.2f}" if w.rolling_sharpe is not None else ""
        print(f"  [{w.warning_type:15s}] {w.timestamp}  {adx_str}  {sharpe_str}")

    if len(warnings) > max_display:
        print(f"  ... and {len(warnings) - max_display} more")
