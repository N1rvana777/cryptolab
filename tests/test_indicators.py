#!/usr/bin/env python3
"""Sanity tests for ported indicators."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptolab.indicators.core import (
    compute_atr, compute_ema, compute_sma, compute_rsi,
    compute_adx, compute_bollinger, compute_slope_z, compute_volume_ratio,
)
from cryptolab.indicators.donchian import compute_donchian


def make_candles(prices):
    """Create candle dicts from a list of close prices with synthetic OHLCV."""
    candles = []
    for i, p in enumerate(prices):
        candles.append({
            "o": str(p * 0.999),
            "h": str(p * 1.01),
            "l": str(p * 0.99),
            "c": str(p),
            "v": str(100 + i),
        })
    return candles


def test_sma():
    assert compute_sma([1, 2, 3, 4, 5], 3) == 4.0
    assert compute_sma([10, 20], 5) is None
    print("  SMA: OK")


def test_ema():
    vals = list(range(1, 21))
    result = compute_ema(vals, 10)
    assert result is not None
    assert 14 < result < 20
    assert compute_ema([1], 5) is None
    print("  EMA: OK")


def test_rsi():
    # Monotonically increasing -> RSI should be 100
    closes = list(range(100, 120))
    rsi = compute_rsi(closes, 14)
    assert rsi is not None
    assert rsi == 100.0

    # Monotonically decreasing -> RSI should be 0
    closes_down = list(range(120, 100, -1))
    rsi_down = compute_rsi(closes_down, 14)
    assert rsi_down is not None
    assert rsi_down == 0.0
    print("  RSI: OK")


def test_atr():
    prices = [100 + i * 0.5 for i in range(30)]
    candles = make_candles(prices)
    atr = compute_atr(candles, 14)
    assert atr is not None
    assert atr > 0
    assert compute_atr(candles[:5], 14) is None
    print("  ATR: OK")


def test_adx():
    prices = [100 + i * 0.5 for i in range(50)]
    candles = make_candles(prices)
    result = compute_adx(candles, 14)
    assert result is not None
    assert "adx" in result
    assert result["adx"] > 0
    print("  ADX: OK")


def test_bollinger():
    closes = [100 + i * 0.1 for i in range(30)]
    bb = compute_bollinger(closes, 20)
    assert bb is not None
    assert bb["upper"] > bb["middle"] > bb["lower"]
    assert bb["width"] > 0
    print("  Bollinger: OK")


def test_slope_z():
    # Strong uptrend
    closes_up = list(range(100, 130))
    sz = compute_slope_z(closes_up, 20)
    assert sz is not None
    assert sz > 0

    # Strong downtrend
    closes_down = list(range(130, 100, -1))
    sz_down = compute_slope_z(closes_down, 20)
    assert sz_down is not None
    assert sz_down < 0
    print("  Slope-Z: OK")


def test_volume_ratio():
    candles = make_candles([100 + i for i in range(25)])
    vr = compute_volume_ratio(candles, 20)
    assert vr > 0
    print("  Volume Ratio: OK")


def test_donchian():
    highs = [100 + i for i in range(25)]
    lows = [90 + i for i in range(25)]
    dc = compute_donchian(highs, lows, 20)
    assert dc is not None
    assert dc["upper"] == max(highs[-20:])
    assert dc["lower"] == min(lows[-20:])
    assert dc["middle"] == (dc["upper"] + dc["lower"]) / 2
    assert compute_donchian(highs[:5], lows[:5], 20) is None
    print("  Donchian: OK")


if __name__ == "__main__":
    print("Running indicator tests...")
    test_sma()
    test_ema()
    test_rsi()
    test_atr()
    test_adx()
    test_bollinger()
    test_slope_z()
    test_volume_ratio()
    test_donchian()
    print("\nAll tests passed!")
