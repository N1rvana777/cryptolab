"""Tests for DonchianBreakout strategy."""

import unittest

import pandas as pd

from cryptolab.config import Config
from cryptolab.strategy.donchian import DonchianBreakout


def _make_df(prices, spread=0.5):
    """Build OHLCV DataFrame from a list of close prices.

    Generates high = close + spread, low = close - spread, open = close, volume = 100.
    """
    rows = []
    for i, c in enumerate(prices):
        rows.append({
            "timestamp": pd.Timestamp("2023-01-01") + pd.Timedelta(hours=4 * i),
            "open": c,
            "high": c + spread,
            "low": c - spread,
            "close": c,
            "volume": 100.0,
        })
    return pd.DataFrame(rows)


class TestDonchianFlat(unittest.TestCase):
    """Flat market — price stays within channel, no breakouts."""

    def test_flat_market_stays_flat(self):
        cfg = Config(donchian_period=5, atr_period=3)
        strat = DonchianBreakout(cfg)
        # 20 bars at the same price — no breakout possible
        df = _make_df([100.0] * 20)
        sig = strat.generate_signal("BTC", df, equity=10_000)
        self.assertEqual(sig.target_position, 0.0)


class TestDonchianLongEntry(unittest.TestCase):
    """Price breaks above channel → should go long."""

    def setUp(self):
        self.cfg = Config(donchian_period=5, atr_period=3)
        self.strat = DonchianBreakout(self.cfg)

    def test_long_breakout(self):
        # 10 bars at 100, then a bar at 105 (breaks above upper channel)
        prices = [100.0] * 10 + [105.0]
        df = _make_df(prices)
        sig = self.strat.generate_signal("BTC", df, equity=10_000)
        self.assertEqual(sig.signal, "LONG")
        self.assertGreater(sig.target_position, 0)
        self.assertIsNotNone(sig.suggested_stop_px)
        self.assertLess(sig.suggested_stop_px, 105.0)

    def test_long_hold_after_entry(self):
        # Enter long, then next bar stays high → should hold long
        prices = [100.0] * 10 + [105.0]
        df = _make_df(prices)
        self.strat.generate_signal("BTC", df, equity=10_000)

        prices2 = prices + [106.0]
        df2 = _make_df(prices2)
        sig2 = self.strat.generate_signal("BTC", df2, equity=10_000)
        self.assertEqual(sig2.signal, "HOLD")
        self.assertGreater(sig2.target_position, 0)


class TestDonchianShortEntry(unittest.TestCase):
    """Price breaks below channel → should go short."""

    def test_short_breakout(self):
        cfg = Config(donchian_period=5, atr_period=3)
        strat = DonchianBreakout(cfg)
        prices = [100.0] * 10 + [94.0]
        df = _make_df(prices)
        sig = strat.generate_signal("BTC", df, equity=10_000)
        self.assertEqual(sig.signal, "SHORT")
        self.assertLess(sig.target_position, 0)
        self.assertIsNotNone(sig.suggested_stop_px)
        self.assertGreater(sig.suggested_stop_px, 94.0)


class TestDonchianTrailingStop(unittest.TestCase):
    """Trailing stop should close position."""

    def test_long_trailing_stop_closes(self):
        cfg = Config(donchian_period=5, atr_period=3, atr_sl_mult=1.0)
        strat = DonchianBreakout(cfg)

        # Enter long at breakout
        prices = [100.0] * 10 + [105.0]
        df = _make_df(prices)
        sig = strat.generate_signal("BTC", df, equity=10_000)
        self.assertEqual(sig.signal, "LONG")

        # Price drops sharply → should trigger trailing stop
        prices2 = prices + [95.0]
        df2 = _make_df(prices2)
        sig2 = strat.generate_signal("BTC", df2, equity=10_000)
        self.assertEqual(sig2.signal, "CLOSE")
        self.assertEqual(sig2.target_position, 0.0)

    def test_short_trailing_stop_closes(self):
        cfg = Config(donchian_period=5, atr_period=3, atr_sl_mult=1.0)
        strat = DonchianBreakout(cfg)

        # Enter short at breakout
        prices = [100.0] * 10 + [94.0]
        df = _make_df(prices)
        sig = strat.generate_signal("BTC", df, equity=10_000)
        self.assertEqual(sig.signal, "SHORT")

        # Price spikes up → should trigger trailing stop
        prices2 = prices + [110.0]
        df2 = _make_df(prices2)
        sig2 = strat.generate_signal("BTC", df2, equity=10_000)
        self.assertEqual(sig2.signal, "CLOSE")
        self.assertEqual(sig2.target_position, 0.0)


class TestDonchianPositionSizing(unittest.TestCase):
    """Verify ATR-based position sizing math."""

    def test_position_size_calculation(self):
        cfg = Config(
            donchian_period=5,
            atr_period=3,
            atr_sl_mult=2.0,
            risk_per_trade=0.02,
            leverage=3.0,
        )
        strat = DonchianBreakout(cfg)
        equity = 10_000.0

        # Build df where we know the breakout and can verify sizing
        prices = [100.0] * 10 + [105.0]
        df = _make_df(prices, spread=0.5)
        sig = strat.generate_signal("BTC", df, equity=equity)

        self.assertEqual(sig.signal, "LONG")
        # Position should be capped at equity * leverage = 30_000
        self.assertLessEqual(sig.target_position, equity * cfg.leverage)
        self.assertGreater(sig.target_position, 0)


class TestDonchianReset(unittest.TestCase):
    """Reset should clear state."""

    def test_reset_clears_state(self):
        cfg = Config(donchian_period=5, atr_period=3)
        strat = DonchianBreakout(cfg)

        # Enter a position
        prices = [100.0] * 10 + [105.0]
        df = _make_df(prices)
        strat.generate_signal("BTC", df, equity=10_000)
        self.assertIn("BTC", strat._state)
        self.assertEqual(strat._state["BTC"]["side"], "long")

        # Reset
        strat.reset("BTC")
        self.assertNotIn("BTC", strat._state)


class TestDonchianNoMicroAdjustment(unittest.TestCase):
    """Position size should be locked at entry — no rebalancing on HOLD."""

    def test_hold_preserves_position_size(self):
        cfg = Config(donchian_period=5, atr_period=3, atr_sl_mult=100.0)
        strat = DonchianBreakout(cfg)

        # Enter long
        prices = [100.0] * 10 + [105.0]
        df = _make_df(prices)
        sig1 = strat.generate_signal("BTC", df, equity=10_000)
        self.assertEqual(sig1.signal, "LONG")
        entry_pos = sig1.target_position

        # Next bar: slightly different price and equity — position must stay the same
        prices2 = prices + [107.0]
        df2 = _make_df(prices2)
        sig2 = strat.generate_signal("BTC", df2, equity=10_500)
        self.assertEqual(sig2.signal, "HOLD")
        self.assertEqual(sig2.target_position, entry_pos)

        # Another bar: position still locked
        prices3 = prices2 + [108.0]
        df3 = _make_df(prices3)
        sig3 = strat.generate_signal("BTC", df3, equity=11_000)
        self.assertEqual(sig3.signal, "HOLD")
        self.assertEqual(sig3.target_position, entry_pos)


class TestDonchianOppositeBreakout(unittest.TestCase):
    """Opposite channel breakout should close position."""

    def test_long_closed_by_short_breakout(self):
        cfg = Config(donchian_period=5, atr_period=3, atr_sl_mult=100.0)  # huge mult so trailing stop won't trigger
        strat = DonchianBreakout(cfg)

        # Enter long
        prices = [100.0] * 10 + [105.0]
        df = _make_df(prices, spread=0.5)
        sig = strat.generate_signal("BTC", df, equity=10_000)
        self.assertEqual(sig.signal, "LONG")

        # Price drops below lower channel
        prices2 = prices + [90.0]
        df2 = _make_df(prices2, spread=0.5)
        sig2 = strat.generate_signal("BTC", df2, equity=10_000)
        self.assertEqual(sig2.signal, "CLOSE")
        self.assertEqual(sig2.target_position, 0.0)


if __name__ == "__main__":
    unittest.main()
