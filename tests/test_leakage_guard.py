"""Tests for the leakage guard."""

import pandas as pd
import pytest

from cryptolab.features.leakage_guard import LeakageGuard, LookAheadLeakageError


class TestLeakageGuard:

    def setup_method(self):
        self.guard = LeakageGuard()

    def test_lag_features_pass(self):
        """Properly shifted features should pass validation."""
        import numpy as np
        rng = np.random.RandomState(42)
        target = rng.randn(100)
        # A truly independent feature should have low correlation
        feature = rng.randn(100)
        df = pd.DataFrame({
            "date": pd.date_range("2023-01-01", periods=100, freq="1h"),
            "target": target,
            "lag_1": feature,
        })
        # Should not raise (correlation << 0.95)
        self.guard.validate_lag_features(df, ["lag_1"], target_col="target")

    def test_lag_features_detect_leakage(self):
        """Feature with near-perfect correlation to target should fail."""
        df = pd.DataFrame({
            "date": pd.date_range("2023-01-01", periods=100, freq="1h"),
            "target": range(100),
            "leaked_feature": range(100),  # identical to target = leakage
        })
        with pytest.raises(LookAheadLeakageError, match="LEAKAGE DETECTED"):
            self.guard.validate_lag_features(df, ["leaked_feature"], target_col="target")

    def test_train_test_split_pass(self):
        """Non-overlapping splits should pass."""
        train_dates = pd.Series(pd.date_range("2023-01-01", periods=100, freq="1h"))
        test_dates = pd.Series(pd.date_range("2023-01-10", periods=50, freq="1h"))
        self.guard.validate_train_test_split(train_dates, test_dates)

    def test_train_test_split_fail(self):
        """Overlapping splits should fail."""
        train_dates = pd.Series(pd.date_range("2023-01-01", periods=100, freq="1h"))
        test_dates = pd.Series(pd.date_range("2023-01-01", periods=50, freq="1h"))
        with pytest.raises(LookAheadLeakageError):
            self.guard.validate_train_test_split(train_dates, test_dates)

    def test_embargo_pass(self):
        """Sufficient embargo gap should pass."""
        train_end = pd.Timestamp("2023-01-01 00:00:00", tz="UTC")
        test_start = pd.Timestamp("2023-01-02 12:00:00", tz="UTC")
        self.guard.validate_embargo(train_end, test_start, min_embargo_bars=24)

    def test_embargo_fail(self):
        """Insufficient embargo should fail."""
        train_end = pd.Timestamp("2023-01-01 00:00:00", tz="UTC")
        test_start = pd.Timestamp("2023-01-01 12:00:00", tz="UTC")
        with pytest.raises(LookAheadLeakageError):
            self.guard.validate_embargo(train_end, test_start, min_embargo_bars=24)

    def test_no_target_in_features_pass(self):
        self.guard.validate_no_target_in_features(
            ["rsi_14", "atr_14"], ["fwd_return_4h"]
        )

    def test_no_target_in_features_fail(self):
        with pytest.raises(LookAheadLeakageError):
            self.guard.validate_no_target_in_features(
                ["rsi_14", "fwd_return_4h"], ["fwd_return_4h"]
            )
