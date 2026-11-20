"""Tests for alternative data features (funding, order book)."""

import numpy as np
import pandas as pd
import pytest

from cryptolab.features.funding import FundingFeatures
from cryptolab.features.orderbook import OrderBookFeatures
from cryptolab.data.alt_cache import AltDataCache


def _make_ohlcv(n: int = 200) -> pd.DataFrame:
    """Create synthetic OHLCV data."""
    rng = np.random.default_rng(42)
    prices = 100.0 + np.cumsum(rng.standard_normal(n) * 0.5)
    return pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC"),
        "open": prices,
        "high": prices + rng.uniform(0, 2, n),
        "low": prices - rng.uniform(0, 2, n),
        "close": prices + rng.standard_normal(n) * 0.3,
        "volume": rng.uniform(1e6, 5e6, n),
    })


class TestFundingFeatures:
    def test_compute_with_funding_data(self):
        df = _make_ohlcv(200)
        # Add synthetic funding rate (every 8 bars, forward-filled)
        rng = np.random.default_rng(123)
        fr = np.zeros(200)
        for i in range(0, 200, 8):
            val = rng.normal(0.0001, 0.0005)
            fr[i:i+8] = val
        df["funding_rate"] = fr
        df["premium"] = fr * 0.5

        block = FundingFeatures()
        result = block.compute(df)

        # Check all feature columns exist
        for name in block.feature_names():
            assert name in result.columns, f"Missing column: {name}"

        # First row should be NaN (shift)
        assert pd.isna(result["fr_raw"].iloc[0])

        # After warmup, should have valid values
        valid = result.iloc[100:]
        assert valid["fr_ma_8"].notna().any()
        assert valid["fr_zscore_72"].notna().any()

    def test_compute_without_funding_data(self):
        """Graceful degradation when funding_rate column is missing."""
        df = _make_ohlcv(200)
        block = FundingFeatures()
        result = block.compute(df)

        for name in block.feature_names():
            assert name in result.columns
            assert result[name].isna().all()

    def test_no_leakage(self):
        """Funding features must be shifted — no correlation with current bar."""
        df = _make_ohlcv(200)
        rng = np.random.default_rng(99)
        # Make funding rate correlated with price movement
        df["funding_rate"] = df["close"].pct_change() * 10
        df["premium"] = df["funding_rate"] * 0.5

        block = FundingFeatures()
        result = block.compute(df)

        # fr_raw should be shifted — it should NOT equal the current funding_rate
        # (it should equal the previous one)
        shifted = df["funding_rate"].shift(1)
        pd.testing.assert_series_equal(
            result["fr_raw"], shifted, check_names=False
        )

    def test_feature_count(self):
        block = FundingFeatures()
        names = block.feature_names()
        # 1 raw + 3*3 lookbacks + 5 derived = 15
        assert len(names) == 15


class TestOrderBookFeatures:
    def test_compute_with_ob_data(self):
        df = _make_ohlcv(200)
        rng = np.random.default_rng(42)
        df["ob_bid_depth"] = rng.uniform(1e6, 5e6, 200)
        df["ob_ask_depth"] = rng.uniform(1e6, 5e6, 200)
        df["ob_spread_bps"] = rng.uniform(1, 10, 200)
        df["ob_imbalance"] = (df["ob_bid_depth"] - df["ob_ask_depth"]) / (
            df["ob_bid_depth"] + df["ob_ask_depth"]
        )

        block = OrderBookFeatures()
        result = block.compute(df)

        for name in block.feature_names():
            assert name in result.columns, f"Missing: {name}"

        # After warmup, should have valid values
        valid = result.iloc[100:]
        assert valid["ob_imb"].notna().any()
        assert valid["ob_imb_zscore_24"].notna().any()

    def test_compute_without_ob_data(self):
        df = _make_ohlcv(200)
        block = OrderBookFeatures()
        result = block.compute(df)

        for name in block.feature_names():
            assert name in result.columns
            assert result[name].isna().all()

    def test_no_leakage(self):
        df = _make_ohlcv(200)
        rng = np.random.default_rng(42)
        df["ob_bid_depth"] = rng.uniform(1e6, 5e6, 200)
        df["ob_ask_depth"] = rng.uniform(1e6, 5e6, 200)
        df["ob_spread_bps"] = rng.uniform(1, 10, 200)
        df["ob_imbalance"] = rng.uniform(-0.5, 0.5, 200)

        block = OrderBookFeatures()
        result = block.compute(df)

        # ob_imb should equal shifted ob_imbalance
        shifted = df["ob_imbalance"].shift(1)
        pd.testing.assert_series_equal(
            result["ob_imb"], shifted, check_names=False
        )

    def test_feature_count(self):
        block = OrderBookFeatures()
        names = block.feature_names()
        # 3 raw + 5*3 lookbacks + 4 derived = 22
        assert len(names) == 22


class TestAltDataCache:
    def test_round_trip(self, tmp_path):
        cache = AltDataCache(str(tmp_path))
        df = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=10, freq="8h", tz="UTC"),
            "funding_rate": np.random.randn(10) * 0.001,
            "premium": np.random.randn(10) * 0.0005,
        })
        cache.write("funding", "BTC", df)
        loaded = cache.read("funding", "BTC")
        assert len(loaded) == 10
        assert "timestamp" in loaded.columns

    def test_merge(self, tmp_path):
        cache = AltDataCache(str(tmp_path))
        df1 = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=5, freq="8h", tz="UTC"),
            "funding_rate": [0.001] * 5,
        })
        df2 = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01 16:00", periods=5, freq="8h", tz="UTC"),
            "funding_rate": [0.002] * 5,
        })
        cache.write("funding", "BTC", df1)
        cache.merge_and_write("funding", "BTC", df2)
        loaded = cache.read("funding", "BTC")
        # Should deduplicate overlapping timestamps
        assert len(loaded) == 7  # 5 + 5 - 3 overlap

    def test_cached_range(self, tmp_path):
        cache = AltDataCache(str(tmp_path))
        df = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=10, freq="8h", tz="UTC"),
            "funding_rate": np.random.randn(10) * 0.001,
        })
        cache.write("funding", "BTC", df)
        min_ts, max_ts = cache.get_cached_range("funding", "BTC")
        assert min_ts is not None
        assert max_ts is not None
        assert max_ts > min_ts

    def test_empty_read(self, tmp_path):
        cache = AltDataCache(str(tmp_path))
        df = cache.read("funding", "NONEXISTENT")
        assert df.empty
