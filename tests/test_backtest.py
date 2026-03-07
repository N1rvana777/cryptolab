"""Tests for backtest engine with synthetic data and known PnL outcomes."""

import unittest
import pandas as pd
import numpy as np

from cryptolab.config import Config
from cryptolab.strategy.base import BaseStrategy, StrategySignal
from cryptolab.backtest.engine import BacktestEngine, Trade, _PositionTracker
from cryptolab.backtest.metrics import (
    max_drawdown, win_rate_and_pnl, time_in_market,
    sharpe_ratio, sortino_ratio, calmar_ratio,
)


def make_ohlcv(prices: list[float], start: str = "2023-01-01") -> pd.DataFrame:
    """Create synthetic OHLCV DataFrame from a list of close prices.
    Open = previous close, high = max(open, close)*1.001, low = min(open, close)*0.999.
    """
    rows = []
    for i, px in enumerate(prices):
        o = prices[i - 1] if i > 0 else px
        h = max(o, px) * 1.001
        lo = min(o, px) * 0.999
        rows.append({
            "timestamp": pd.Timestamp(start, tz="UTC") + pd.Timedelta(hours=4 * i),
            "open": o,
            "high": h,
            "low": lo,
            "close": px,
            "volume": 1000.0,
        })
    return pd.DataFrame(rows)


class AlwaysLong(BaseStrategy):
    """Always wants to be long a fixed USD notional."""

    def __init__(self, cfg, size_usd=1000.0):
        super().__init__(cfg, name="AlwaysLong")
        self.size_usd = size_usd

    def generate_signal(self, symbol, df, equity, **kw):
        return StrategySignal(target_position=self.size_usd, signal="LONG", strategy_name=self.name)


class AlwaysFlat(BaseStrategy):
    """Always flat — should produce zero trades after bar 0."""

    def __init__(self, cfg):
        super().__init__(cfg, name="AlwaysFlat")

    def generate_signal(self, symbol, df, equity, **kw):
        return StrategySignal(target_position=0.0, signal="FLAT", strategy_name=self.name)


class FlipStrategy(BaseStrategy):
    """Alternates between long and short every bar."""

    def __init__(self, cfg, size_usd=500.0):
        super().__init__(cfg, name="Flip")
        self.size_usd = size_usd

    def generate_signal(self, symbol, df, equity, **kw):
        if len(df) % 2 == 1:
            return StrategySignal(target_position=self.size_usd, signal="LONG", strategy_name=self.name)
        else:
            return StrategySignal(target_position=-self.size_usd, signal="SHORT", strategy_name=self.name)


class TestPositionTracker(unittest.TestCase):
    """Test the internal position tracker gross PnL math (fees handled by engine)."""

    def test_open_and_close_long(self):
        t = _PositionTracker()
        # Open long $1000 at $100
        sz, pnl = t.execute(1000.0, 100.0)
        self.assertAlmostEqual(sz, 1000.0)
        self.assertAlmostEqual(pnl, 0.0)
        self.assertAlmostEqual(t.position_usd, 1000.0)
        self.assertAlmostEqual(t.entry_px, 100.0)

        # Close at $110 (10% gain) -> gross PnL = 1000 * 10/100 = 100
        sz, pnl = t.execute(0.0, 110.0)
        self.assertAlmostEqual(pnl, 100.0)
        self.assertAlmostEqual(t.position_usd, 0.0)

    def test_open_and_close_short(self):
        t = _PositionTracker()
        t.execute(-500.0, 200.0)
        # Close at $190 -> gross PnL = 500 * (200-190)/200 = 25
        sz, pnl = t.execute(0.0, 190.0)
        self.assertAlmostEqual(pnl, 25.0)

    def test_increase_position(self):
        t = _PositionTracker()
        t.execute(500.0, 100.0)
        t.execute(1000.0, 120.0)
        # Weighted entry: (500*100 + 500*120) / 1000 = 110
        self.assertAlmostEqual(t.entry_px, 110.0)
        self.assertAlmostEqual(t.position_usd, 1000.0)

    def test_reduce_position(self):
        t = _PositionTracker()
        t.execute(1000.0, 100.0)
        sz, pnl = t.execute(500.0, 110.0)
        # Gross realized: 500 * (110-100)/100 = 50
        self.assertAlmostEqual(pnl, 50.0)
        self.assertAlmostEqual(t.position_usd, 500.0)
        self.assertAlmostEqual(t.entry_px, 100.0)

    def test_flip(self):
        t = _PositionTracker()
        t.execute(1000.0, 100.0)
        sz, pnl = t.execute(-500.0, 110.0)
        # Close long: 1000 * 10/100 = 100 realized
        self.assertAlmostEqual(pnl, 100.0)
        self.assertAlmostEqual(t.position_usd, -500.0)
        self.assertAlmostEqual(t.entry_px, 110.0)


class TestBacktestEngine(unittest.TestCase):
    """Test the full engine with synthetic price data."""

    def _cfg(self, **overrides) -> Config:
        defaults = dict(
            initial_capital=10_000.0,
            taker_fee_bps=0.0,
            maker_fee_bps=0.0,
            slippage_bps=0.0,
            leverage=1.0,
            risk_per_trade=0.02,
        )
        defaults.update(overrides)
        return Config(**defaults)

    def test_flat_strategy_no_trades(self):
        cfg = self._cfg()
        strat = AlwaysFlat(cfg)
        df = make_ohlcv([100.0] * 10)
        result = BacktestEngine(strat, cfg).run("TEST", df)
        self.assertEqual(result.total_trades, 0)
        self.assertAlmostEqual(result.final_equity, 10_000.0)
        self.assertAlmostEqual(result.total_return_pct, 0.0)

    def test_always_long_rising_prices(self):
        """Long $1000 in a market going from 100 to 200 -> should profit."""
        cfg = self._cfg()
        prices = [100.0 + i * 10.0 for i in range(11)]  # 100,110,...,200
        df = make_ohlcv(prices)
        strat = AlwaysLong(cfg, size_usd=1000.0)
        result = BacktestEngine(strat, cfg).run("TEST", df)
        self.assertGreater(result.final_equity, 10_000.0)
        self.assertGreater(result.total_trades, 0)

    def test_always_long_falling_prices(self):
        """Long in a falling market -> should lose."""
        cfg = self._cfg()
        prices = [200.0 - i * 10.0 for i in range(11)]  # 200,190,...,100
        df = make_ohlcv(prices)
        strat = AlwaysLong(cfg, size_usd=1000.0)
        result = BacktestEngine(strat, cfg).run("TEST", df)
        self.assertLess(result.final_equity, 10_000.0)

    def test_fees_are_deducted(self):
        """With fees, final equity should be lower than without."""
        prices = [100.0 + np.sin(i * 0.5) * 5 for i in range(30)]
        df = make_ohlcv(prices)

        cfg_no_fee = self._cfg()
        cfg_with_fee = self._cfg(taker_fee_bps=10.0)

        # FlipStrategy opens/closes frequently so fees accumulate
        r_no_fee = BacktestEngine(FlipStrategy(cfg_no_fee, 500.0), cfg_no_fee).run("TEST", df)
        r_with_fee = BacktestEngine(FlipStrategy(cfg_with_fee, 500.0), cfg_with_fee).run("TEST", df)

        self.assertGreater(r_no_fee.final_equity, r_with_fee.final_equity)
        self.assertGreater(r_with_fee.total_fees, 0.0)

    def test_slippage_reduces_equity(self):
        """Slippage should reduce final equity."""
        prices = [100.0 + i for i in range(20)]
        df = make_ohlcv(prices)

        cfg_no_slip = self._cfg()
        cfg_slip = self._cfg(slippage_bps=50.0)

        r_no_slip = BacktestEngine(AlwaysLong(cfg_no_slip, 1000.0), cfg_no_slip).run("TEST", df)
        r_slip = BacktestEngine(AlwaysLong(cfg_slip, 1000.0), cfg_slip).run("TEST", df)

        self.assertGreater(r_no_slip.final_equity, r_slip.final_equity)

    def test_equity_curve_length(self):
        """Equity curve should have one row per bar."""
        cfg = self._cfg()
        df = make_ohlcv([100.0] * 50)
        result = BacktestEngine(AlwaysFlat(cfg), cfg).run("TEST", df)
        self.assertEqual(len(result.equity_curve), 50)

    def test_max_drawdown_computed(self):
        """Drawdown should be >0 for a strategy that loses money."""
        cfg = self._cfg()
        # Price goes up then crashes
        prices = [100.0 + i * 5 for i in range(10)] + [150.0 - i * 10 for i in range(10)]
        df = make_ohlcv(prices)
        strat = AlwaysLong(cfg, 1000.0)
        result = BacktestEngine(strat, cfg).run("TEST", df)
        self.assertGreater(result.max_drawdown_pct, 0.0)
        self.assertGreater(result.max_drawdown_usd, 0.0)

    def test_flip_strategy_generates_trades(self):
        """Flipping strategy should create many trades."""
        cfg = self._cfg()
        prices = [100.0 + np.sin(i * 0.5) * 5 for i in range(30)]
        df = make_ohlcv(prices)
        strat = FlipStrategy(cfg, 500.0)
        result = BacktestEngine(strat, cfg).run("TEST", df)
        # Should have trades on most bars (flip = close + open each time)
        self.assertGreater(result.total_trades, 10)


class TestMetrics(unittest.TestCase):
    """Test metric computation functions directly."""

    def test_max_drawdown_simple(self):
        eq = pd.Series([100, 110, 105, 120, 90, 115])
        dd_usd, dd_pct = max_drawdown(eq)
        # Peak was 120, trough was 90 -> dd = 30 USD, 25%
        self.assertAlmostEqual(dd_usd, 30.0)
        self.assertAlmostEqual(dd_pct, 25.0)

    def test_max_drawdown_monotonic_up(self):
        eq = pd.Series([100, 110, 120, 130])
        dd_usd, dd_pct = max_drawdown(eq)
        self.assertAlmostEqual(dd_usd, 0.0)
        self.assertAlmostEqual(dd_pct, 0.0)

    def test_win_rate(self):
        trades = [
            Trade(0, pd.Timestamp("2023-01-01"), "X", "SELL", 100, 110, 0, 100, 0, 10.0, "CLOSE"),
            Trade(1, pd.Timestamp("2023-01-02"), "X", "SELL", 100, 90, 0, 100, 0, -5.0, "CLOSE"),
            Trade(2, pd.Timestamp("2023-01-03"), "X", "SELL", 100, 105, 0, 100, 0, 3.0, "CLOSE"),
        ]
        result = win_rate_and_pnl(trades)
        self.assertAlmostEqual(result["win_rate"], 2 / 3 * 100)
        self.assertGreater(result["profit_factor"], 1.0)

    def test_sharpe_ratio_positive(self):
        """Monotonically rising equity -> positive Sharpe."""
        eq = pd.Series([100.0 + i for i in range(100)])
        sr = sharpe_ratio(eq, 2190)
        self.assertGreater(sr, 0.0)

    def test_sharpe_ratio_flat(self):
        """Flat equity (zero std) -> Sharpe = 0."""
        eq = pd.Series([100.0] * 50)
        sr = sharpe_ratio(eq, 2190)
        self.assertAlmostEqual(sr, 0.0)

    def test_sortino_ratio_positive(self):
        """Rising equity with noise -> positive Sortino, and Sortino >= Sharpe."""
        np.random.seed(42)
        eq = pd.Series(100.0 + np.cumsum(np.random.normal(0.1, 0.5, 200)))
        sr = sharpe_ratio(eq, 2190)
        so = sortino_ratio(eq, 2190)
        self.assertGreater(so, 0.0)
        self.assertGreaterEqual(so, sr)

    def test_calmar_ratio_positive(self):
        """Rising equity with drawdown -> positive Calmar."""
        prices = [100.0 + i for i in range(50)]
        prices += [prices[-1] - i * 0.5 for i in range(1, 11)]
        prices += [prices[-1] + i for i in range(1, 20)]
        eq = pd.Series(prices)
        cr = calmar_ratio(eq, 2190)
        self.assertGreater(cr, 0.0)

    def test_calmar_ratio_no_drawdown(self):
        """Monotonically rising equity -> no drawdown -> Calmar = 0."""
        eq = pd.Series([100.0 + i for i in range(50)])
        cr = calmar_ratio(eq, 2190)
        self.assertAlmostEqual(cr, 0.0)


if __name__ == "__main__":
    unittest.main()
