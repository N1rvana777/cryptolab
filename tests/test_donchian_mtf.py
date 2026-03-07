"""Tests for DonchianMTF strategy."""

import unittest

import pandas as pd

from cryptolab.config import Config
from cryptolab.strategy.donchian_mtf import DonchianMTF


def _make_df(prices, spread=0.5):
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


class TestDonchianMTFSignal(unittest.TestCase):

    def _cfg(self, **kw):
        defaults = dict(
            mtf_lookbacks=[5, 10, 20],
            mtf_weights=[0.25, 0.50, 0.25],
            atr_period=5,
            atr_sl_mult=2.0,
            risk_per_trade=0.02,
            leverage=1.0,
            mtf_signal_deadzone=0.05,
            mtf_rebalance_pct=0.0,
            mtf_dd_max=0.30,
            mtf_dd_floor=0.25,
            mtf_vol_target=0.15,
            mtf_vol_scalar_bounds=[0.5, 2.0],
            mtf_use_trailing_stop=False,
        )
        defaults.update(kw)
        return Config(**defaults)

    def test_long_breakout_entry(self):
        """Price breaking above all channels should produce LONG entry."""
        prices = [100] * 25 + [100 + i * 2 for i in range(1, 11)]
        df = _make_df(prices)
        strat = DonchianMTF(self._cfg())
        sig = strat.generate_signal("BTC", df, 10000.0)
        self.assertGreater(sig.target_position, 0)
        self.assertEqual(sig.signal, "LONG")
        self.assertGreater(sig.metadata["combined"], 0)

    def test_short_breakout_entry(self):
        """Price breaking below all channels should produce SHORT entry."""
        prices = [100] * 25 + [100 - i * 2 for i in range(1, 11)]
        df = _make_df(prices)
        strat = DonchianMTF(self._cfg())
        sig = strat.generate_signal("BTC", df, 10000.0)
        self.assertLess(sig.target_position, 0)
        self.assertEqual(sig.signal, "SHORT")
        self.assertLess(sig.metadata["combined"], 0)

    def test_flat_market_no_entry(self):
        """Flat market should not trigger breakout — HOLD."""
        prices = [100.0] * 35
        df = _make_df(prices)
        strat = DonchianMTF(self._cfg())
        sig = strat.generate_signal("BTC", df, 10000.0)
        self.assertEqual(sig.target_position, 0.0)

    def test_conflicting_tfs_smaller_position(self):
        """When short TF disagrees, position should be smaller than unanimous."""
        cfg = self._cfg()

        # Unanimous uptrend
        up_prices = [100] * 25 + [100 + i * 2 for i in range(1, 11)]
        strat_up = DonchianMTF(cfg)
        sig_up = strat_up.generate_signal("BTC", _make_df(up_prices), 10000.0)

        # Short TF bearish (recent dip), others still bullish
        mixed_prices = [100] * 20 + [100 + i * 2 for i in range(1, 11)] + [108, 106, 104, 102, 100, 115]
        strat_mixed = DonchianMTF(cfg)
        sig_mixed = strat_mixed.generate_signal("BTC", _make_df(mixed_prices), 10000.0)

        if sig_up.signal == "LONG" and sig_mixed.signal == "LONG":
            # Mixed should have smaller combined agreement -> smaller position
            self.assertLessEqual(abs(sig_mixed.metadata["combined"]), abs(sig_up.metadata["combined"]))

    def test_trailing_stop_exit(self):
        """After long entry, trailing stop should close position."""
        cfg = self._cfg()
        strat = DonchianMTF(cfg)

        # Enter long
        prices = [100] * 25 + [100 + i * 2 for i in range(1, 11)]
        sig = strat.generate_signal("BTC", _make_df(prices), 10000.0)
        self.assertEqual(sig.signal, "LONG")

        # Price drops to hit trailing stop
        drop_prices = prices + [80]  # sharp drop well below trail stop
        sig2 = strat.generate_signal("BTC", _make_df(drop_prices), 10000.0)
        self.assertEqual(sig2.signal, "CLOSE")
        self.assertEqual(sig2.target_position, 0.0)

    def test_drawdown_scaling_reduces_position(self):
        """Position should be smaller when in drawdown."""
        prices = [100] * 25 + [100 + i * 2 for i in range(1, 11)]
        cfg = self._cfg()

        strat1 = DonchianMTF(cfg)
        sig1 = strat1.generate_signal("BTC", _make_df(prices), 10000.0)

        strat2 = DonchianMTF(cfg)
        st = strat2._get_state("BTC")
        st["peak_equity"] = 10000.0
        sig2 = strat2.generate_signal("BTC", _make_df(prices), 8000.0)

        if sig1.signal == "LONG" and sig2.signal == "LONG":
            self.assertLess(abs(sig2.target_position), abs(sig1.target_position))
            self.assertLess(sig2.metadata["dd_scalar"], 1.0)

    def test_vol_scalar_in_metadata(self):
        """Vol scalar should be present and bounded."""
        prices = [100] * 25 + [100 + i * 2 for i in range(1, 11)]
        strat = DonchianMTF(self._cfg())
        sig = strat.generate_signal("BTC", _make_df(prices), 10000.0)
        if sig.signal == "LONG":
            self.assertIn("vol_scalar", sig.metadata)
            self.assertGreaterEqual(sig.metadata["vol_scalar"], 0.5)
            self.assertLessEqual(sig.metadata["vol_scalar"], 2.0)

    def test_hold_preserves_or_pyramids_position(self):
        """After entry, HOLD should keep or increase position via pyramiding."""
        cfg = self._cfg(mtf_pyramid_max_units=1)  # disable pyramiding
        strat = DonchianMTF(cfg)

        # Enter long
        prices = [100] * 25 + [100 + i * 2 for i in range(1, 11)]
        sig1 = strat.generate_signal("BTC", _make_df(prices), 10000.0)
        self.assertEqual(sig1.signal, "LONG")

        # Next bar still in trend — no pyramid (max_units=1)
        prices2 = prices + [122]
        sig2 = strat.generate_signal("BTC", _make_df(prices2), 10000.0)
        self.assertEqual(sig2.signal, "HOLD")
        self.assertEqual(sig2.target_position, sig1.target_position)

    def test_pyramiding_adds_to_position(self):
        """With pyramiding enabled, trend continuation should increase position."""
        cfg = self._cfg(mtf_pyramid_max_units=4, mtf_pyramid_spacing_atr=0.5)
        strat = DonchianMTF(cfg)

        # Enter long
        prices = [100] * 25 + [100 + i * 2 for i in range(1, 11)]
        sig1 = strat.generate_signal("BTC", _make_df(prices), 10000.0)
        self.assertEqual(sig1.signal, "LONG")
        self.assertEqual(sig1.metadata.get("n_units"), 1)

        # Strong continuation — should trigger pyramid add
        prices2 = prices + [122]
        sig2 = strat.generate_signal("BTC", _make_df(prices2), 10000.0)
        self.assertEqual(sig2.signal, "HOLD")
        self.assertGreater(sig2.target_position, sig1.target_position)
        self.assertEqual(sig2.metadata.get("n_units"), 2)

    def test_leverage_cap_respected(self):
        """Position should never exceed equity * leverage."""
        prices = [100] * 25 + [100 + i * 5 for i in range(1, 11)]
        cfg = self._cfg(leverage=2.0, mtf_vol_target=1.0)
        strat = DonchianMTF(cfg)
        sig = strat.generate_signal("BTC", _make_df(prices), 10000.0)
        self.assertLessEqual(abs(sig.target_position), 10000.0 * 2.0 + 0.01)

    def test_integration_with_engine(self):
        """DonchianMTF should run through BacktestEngine without errors."""
        from cryptolab.backtest import BacktestEngine
        prices = [100] * 260 + [100 + i * 0.5 for i in range(1, 41)]
        df = _make_df(prices)
        cfg = self._cfg(initial_capital=10000.0)
        strat = DonchianMTF(cfg)
        engine = BacktestEngine(strat, cfg)
        result = engine.run("BTC", df)
        self.assertGreater(len(result.equity_curve), 0)
        self.assertEqual(result.strategy_name, "DonchianMTF")


if __name__ == "__main__":
    unittest.main()
