"""OHLCV data validation: gap detection, duplicate check, OHLC consistency."""

import logging
from dataclasses import dataclass, field
from typing import List

import pandas as pd

from cryptolab.utils import interval_to_ms

logger = logging.getLogger(__name__)


@dataclass
class ValidationReport:
    symbol: str
    interval: str
    total_rows: int = 0
    duplicates: int = 0
    null_count: int = 0
    gaps: List[str] = field(default_factory=list)
    ohlc_violations: int = 0  # rows where high < low, etc.
    negative_volume: int = 0
    is_valid: bool = True

    def summary(self) -> str:
        status = "PASS" if self.is_valid else "FAIL"
        lines = [f"[{status}] {self.symbol} {self.interval}: {self.total_rows} rows"]
        if self.duplicates:
            lines.append(f"  - {self.duplicates} duplicate timestamps")
        if self.null_count:
            lines.append(f"  - {self.null_count} null values")
        if self.gaps:
            lines.append(f"  - {len(self.gaps)} gaps detected")
            for g in self.gaps[:5]:
                lines.append(f"    {g}")
            if len(self.gaps) > 5:
                lines.append(f"    ... and {len(self.gaps) - 5} more")
        if self.ohlc_violations:
            lines.append(f"  - {self.ohlc_violations} OHLC violations (high < low)")
        if self.negative_volume:
            lines.append(f"  - {self.negative_volume} negative volume rows")
        return "\n".join(lines)


def validate_ohlcv(df: pd.DataFrame, symbol: str, interval: str) -> ValidationReport:
    """Run all validation checks on an OHLCV DataFrame."""
    report = ValidationReport(symbol=symbol, interval=interval)

    if df.empty:
        report.total_rows = 0
        report.is_valid = False
        return report

    report.total_rows = len(df)

    # Duplicates
    report.duplicates = int(df["timestamp"].duplicated().sum())

    # Nulls
    report.null_count = int(df[["open", "high", "low", "close", "volume"]].isnull().sum().sum())

    # OHLC consistency: high >= low, high >= open, high >= close, low <= open, low <= close
    violations = (df["high"] < df["low"]) | (df["high"] < df["open"]) | (df["high"] < df["close"]) | \
                 (df["low"] > df["open"]) | (df["low"] > df["close"])
    report.ohlc_violations = int(violations.sum())

    # Negative volume
    report.negative_volume = int((df["volume"] < 0).sum())

    # Gap detection
    iv_ms = interval_to_ms(interval)
    ts_sorted = df["timestamp"].sort_values().reset_index(drop=True)
    if len(ts_sorted) > 1:
        diffs = ts_sorted.diff().dt.total_seconds() * 1000
        expected = iv_ms
        for i in range(1, len(diffs)):
            actual = diffs.iloc[i]
            if abs(actual - expected) > expected * 0.1:  # >10% deviation
                report.gaps.append(
                    f"{ts_sorted.iloc[i-1]} -> {ts_sorted.iloc[i]} (gap: {actual/1000:.0f}s, expected: {expected/1000:.0f}s)"
                )

    # Determine validity
    if report.duplicates > 0 or report.null_count > 0 or report.ohlc_violations > 0:
        report.is_valid = False
    if len(report.gaps) > report.total_rows * 0.05:  # >5% gaps
        report.is_valid = False

    return report


def cross_validate(df_a: pd.DataFrame, df_b: pd.DataFrame, max_deviation_pct: float = 0.5) -> dict:
    """
    Compare two OHLCV DataFrames (e.g., OKX vs Binance) on overlapping timestamps.
    Returns dict with match stats.
    """
    if df_a.empty or df_b.empty:
        return {"overlap": 0, "checked": False}

    merged = pd.merge(df_a, df_b, on="timestamp", suffixes=("_a", "_b"))
    if merged.empty:
        return {"overlap": 0, "checked": False}

    close_dev = ((merged["close_a"] - merged["close_b"]).abs() / merged["close_a"] * 100)
    max_dev = close_dev.max()
    mean_dev = close_dev.mean()

    return {
        "overlap": len(merged),
        "checked": True,
        "max_close_deviation_pct": round(max_dev, 4),
        "mean_close_deviation_pct": round(mean_dev, 4),
        "within_threshold": max_dev <= max_deviation_pct,
    }
