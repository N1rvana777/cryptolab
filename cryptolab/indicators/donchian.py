"""Donchian Channel indicator."""

from typing import Optional, Dict


def compute_donchian(highs: list, lows: list, period: int = 20) -> Optional[Dict[str, float]]:
    """
    Compute Donchian Channel: highest high and lowest low over `period` bars.

    Args:
        highs: list of high prices (at least `period` elements)
        lows: list of low prices (at least `period` elements)
        period: lookback period

    Returns:
        {"upper": float, "lower": float, "middle": float} or None if insufficient data
    """
    if len(highs) < period or len(lows) < period:
        return None
    upper = max(highs[-period:])
    lower = min(lows[-period:])
    middle = (upper + lower) / 2.0
    return {"upper": upper, "lower": lower, "middle": middle}
