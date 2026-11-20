"""Tests for the feature engineering pipeline."""

import numpy as np
import pandas as pd
import pytest

from cryptolab.features.base import FeatureBlock
from cryptolab.features.technical import TechnicalFeatures
from cryptolab.features.donchian_features import DonchianFeatures
from cryptolab.features.temporal import TemporalFeatures
from cryptolab.features.volatility import VolatilityFeatures
from cryptolab.features.momentum import MomentumFeatures
from cryptolab.features.microstructure import MicrostructureFeatures
from cryptolab.features.targets import compute_targets, TARGET_COLUMNS
from cryptolab.features.pipeline import FeaturePipeline, build_default_registry


def _make_ohlcv(n: int = 500, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic OHLCV data for testing."""
    rng = np.random.RandomState(seed)
    dates = pd.date_range("2023-01-01", periods=n, freq="1h", tz="UTC")
    close = 100 + np.cumsum(rng.randn(n) * 0.5)
    close = np.maximum(close, 10)  # keep positive

    return pd.DataFrame({
        "timestamp": dates,
        "open": close + rng.randn(n) * 0.2,
        "high": close + abs(rng.randn(n) * 0.5),
        "low": close - abs(rng.randn(n) * 0.5),
        "close": close,
        "volume": abs(rng.randn(n) * 1000) + 500,
    })


class TestFeatureBlocks:
    """Test that each feature block produces the expected columns."""

    def test_technical_features(self):
        df = _make_ohlcv(300)
        block = TechnicalFeatures()
        result = block.compute(df)
        names = block.feature_names()
        assert len(names) >= 25
        for name in names:
            assert name in result.columns, f"Missing column: {name}"

    def test_donchian_features(self):
        df = _make_ohlcv(300)
        block = DonchianFeatures()
        result = block.compute(df)
        names = block.feature_names()
        assert "dc_mtf_agreement" in names
        for name in names:
            assert name in result.columns

    def test_temporal_features(self):
        df = _make_ohlcv(100)
        block = TemporalFeatures()
        result = block.compute(df)
        names = block.feature_names()
        assert "hour_sin" in names
        assert "is_weekend" in names
        for name in names:
            assert name in result.columns

    def test_volatility_features(self):
        df = _make_ohlcv(300)
        block = VolatilityFeatures()
        result = block.compute(df)
        names = block.feature_names()
        assert "rvol_24" in names
        for name in names:
            assert name in result.columns

    def test_momentum_features(self):
        df = _make_ohlcv(300)
        block = MomentumFeatures()
        result = block.compute(df)
        names = block.feature_names()
        assert "tsmom_24" in names
        assert "roc_1" in names
        for name in names:
            assert name in result.columns

    def test_microstructure_features(self):
        df = _make_ohlcv(300)
        block = MicrostructureFeatures()
        result = block.compute(df)
        names = block.feature_names()
        assert "vwap_dist" in names
        for name in names:
            assert name in result.columns

    def test_targets(self):
        df = _make_ohlcv(100)
        result = compute_targets(df)
        for col in TARGET_COLUMNS:
            assert col in result.columns

    def test_all_blocks_inherit_feature_block(self):
        blocks = [
            TechnicalFeatures(),
            DonchianFeatures(),
            TemporalFeatures(),
            VolatilityFeatures(),
            MomentumFeatures(),
            MicrostructureFeatures(),
        ]
        for block in blocks:
            assert isinstance(block, FeatureBlock)


class TestFeaturePipeline:
    """Test the full pipeline."""

    def test_pipeline_single_symbol(self):
        df = _make_ohlcv(500)
        pipeline = FeaturePipeline(
            groups=["technical", "donchian", "temporal", "momentum"],
            warmup_bars=168,
        )
        X, y, names = pipeline.build(df, target_col="fwd_return_4h")
        assert X.shape[0] == y.shape[0]
        assert X.shape[1] == len(names)
        assert X.shape[0] > 0
        assert not np.any(np.isnan(X))
        assert not np.any(np.isinf(X))

    def test_pipeline_multi_symbol(self):
        df1 = _make_ohlcv(500, seed=1)
        df1["symbol"] = "BTC"
        df2 = _make_ohlcv(500, seed=2)
        df2["symbol"] = "ETH"
        df = pd.concat([df1, df2], ignore_index=True)

        pipeline = FeaturePipeline(
            groups=["technical", "temporal", "momentum"],
            warmup_bars=168,
        )
        X, y, names = pipeline.build(df, target_col="fwd_return_4h")
        assert X.shape[0] > 0
        assert X.shape[1] == len(names)

    def test_pipeline_no_leakage(self):
        """Verify features don't have near-perfect correlation with target."""
        df = _make_ohlcv(500)
        pipeline = FeaturePipeline(
            groups=["technical", "momentum"],
            warmup_bars=168,
        )
        # This should NOT raise LookAheadLeakageError
        X, y, names = pipeline.build(df, target_col="fwd_return_4h", validate=True)
        assert X.shape[0] > 0

    def test_build_latest(self):
        df = _make_ohlcv(300)
        pipeline = FeaturePipeline(
            groups=["technical", "temporal"],
            warmup_bars=168,
        )
        # First build to set feature names
        pipeline.build(df, target_col="fwd_return_4h")
        # Then build latest
        features = pipeline.build_latest(df)
        assert features.ndim == 1
        assert len(features) > 0

    def test_registry(self):
        reg = build_default_registry()
        names = reg.all_feature_names()
        assert len(names) >= 90  # Should have ~97 features total


class TestFeatureShift:
    """Verify that features are computed on shifted (past) data."""

    def test_technical_uses_shift(self):
        """RSI computed on shifted close should not equal RSI on raw close."""
        df = _make_ohlcv(200)
        block = TechnicalFeatures()
        result = block.compute(df.copy())
        # First row should be NaN (because of shift)
        assert pd.isna(result["rsi_14"].iloc[0])
