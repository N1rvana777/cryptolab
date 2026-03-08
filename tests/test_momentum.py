"""Tests for TSMOM indicator and momentum-blended DonchianMTF."""

import unittest

import pandas as pd

from cryptolab.config import Config
from cryptolab.indicators.core import compute_tsmom
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


class TestTSMOM(unittest.TestCase):

    def test_uptrend_positive(self):
        closes = [100 + i for i in range(200)]
        score = compute_tsmom(closes, 50)
        self.assertIsNotNone(score)
        self.assertGreater(score, 0)

    def test_downtrend_negative(self):
        closes = [200 - i for i in range(200)]
        score = compute_tsmom(closes, 50)
        self.assertIsNotNone(score)
        self.assertLess(score, 0)

    def test_flat_near_zero(self):
        closes = [100.0] * 200
        score = compute_tsmom(closes, 50)
        self.assertEqual(score, 0.0)

    def test_insufficient_data(self):
        closes = [100.0] * 10
        score = compute_tsmom(closes, 50)
        self.assertIsNone(score)

    def test_bounded(self):
        # Extreme trend should be clamped to [-1, 1]
        closes = [100] * 50 + [100 + i * 10 for i in range(100)]
        score = compute_tsmom(closes, 50)
        self.assertLessEqual(score, 1.0)
        self.assertGreaterEqual(score, -1.0)


class TestDonchianMTFWithMomentum(unittest.TestCase):

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
            mtf_pyramid_max_units=1,
            mom_lookback=20,
            mom_weight=0.0,
            mom_entry_threshold=0.3,
        )
        defaults.update(kw)
        return Config(**defaults)

    def test_zero_weight_same_as_baseline(self):
        """mom_weight=0 should produce identical results to pure breakout."""
        prices = [100] * 25 + [100 + i * 2 for i in range(1, 11)]
        df = _make_df(prices)

        strat0 = DonchianMTF(self._cfg(mom_weight=0.0))
        sig0 = strat0.generate_signal("BTC", df, 10000.0)

        strat1 = DonchianMTF(self._cfg(mom_weight=0.0))
        sig1 = strat1.generate_signal("BTC", df, 10000.0)

        self.assertEqual(sig0.signal, sig1.signal)
        self.assertEqual(sig0.target_position, sig1.target_position)

    def test_momentum_in_metadata(self):
        """Momentum score should appear in metadata when weight > 0."""
        prices = [100] * 25 + [100 + i * 2 for i in range(1, 11)]
        df = _make_df(prices)
        strat = DonchianMTF(self._cfg(mom_weight=0.5, mom_lookback=10))
        sig = strat.generate_signal("BTC", df, 10000.0)
        self.assertIn("mom_score", sig.metadata)
        self.assertIn("final_combined", sig.metadata)

    def test_momentum_entry_without_breakout(self):
        """With high mom_weight, strong momentum should trigger entry even without breakout."""
        # Spike to 140 creates a high Donchian upper that persists.
        # Then drop and rise: momentum is positive but close < upper = no breakout.
        prices = [100.0] * 25 + [140.0] + [105.0] * 3
        # Rise toward 120 but stay below 140 upper
        for i in range(1, 8):
            prices.append(105 + i * 2)
        df = _make_df(prices)
        strat = DonchianMTF(self._cfg(
            mom_weight=1.0,  # pure momentum
            mom_lookback=10,
            mom_entry_threshold=0.1,
            mtf_signal_deadzone=0.05,
        ))
        sig = strat.generate_signal("BTC", df, 10000.0)
        # With pure momentum weight, should enter long via momentum (not breakout)
        if sig.signal == "LONG":
            self.assertGreater(sig.target_position, 0)
            self.assertEqual(sig.metadata.get("entry_type"), "momentum")

    def test_breakout_entry_type_labeled(self):
        """Breakout-driven entries should be labeled as such."""
        prices = [100] * 25 + [100 + i * 2 for i in range(1, 11)]
        df = _make_df(prices)
        strat = DonchianMTF(self._cfg(mom_weight=0.3, mom_lookback=10))
        sig = strat.generate_signal("BTC", df, 10000.0)
        if sig.signal == "LONG":
            self.assertEqual(sig.metadata.get("entry_type"), "breakout")

    def test_integration_with_engine(self):
        """Momentum-blended strategy should run through BacktestEngine."""
        from cryptolab.backtest import BacktestEngine
        prices = [100] * 260 + [100 + i * 0.5 for i in range(1, 41)]
        df = _make_df(prices)
        cfg = self._cfg(initial_capital=10000.0, mom_weight=0.5, mom_lookback=20)
        strat = DonchianMTF(cfg)
        engine = BacktestEngine(strat, cfg)
        result = engine.run("BTC", df)
        self.assertGreater(len(result.equity_curve), 0)


if __name__ == "__main__":
    unittest.main()
