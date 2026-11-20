"""Tests for walk-forward splitter."""

import numpy as np
import pandas as pd
import pytest

from cryptolab.ml.splitter import WalkForwardSplitter, ForbiddenKFoldError, assert_no_kfold


class TestWalkForwardSplitter:

    def test_basic_split(self):
        n = 10000
        timestamps = pd.date_range("2021-01-01", periods=n, freq="1h")
        splitter = WalkForwardSplitter(
            n_folds=3,
            test_window_bars=500,
            embargo_bars=24,
            min_train_bars=1000,
        )
        splits = splitter.split(timestamps)
        assert len(splits) == 3

    def test_temporal_ordering(self):
        """All train indices must be before all test indices."""
        n = 10000
        timestamps = pd.date_range("2021-01-01", periods=n, freq="1h")
        splitter = WalkForwardSplitter(n_folds=3, test_window_bars=500, embargo_bars=24)
        splits = splitter.split(timestamps)

        for train_idx, test_idx, info in splits:
            assert train_idx.max() < test_idx.min(), "Train must precede test"
            # Check embargo gap
            gap = test_idx.min() - train_idx.max()
            assert gap >= 24, f"Embargo gap too small: {gap}"

    def test_expanding_window(self):
        """Each fold should have more training data than the previous."""
        n = 10000
        timestamps = pd.date_range("2021-01-01", periods=n, freq="1h")
        splitter = WalkForwardSplitter(n_folds=3, test_window_bars=500, embargo_bars=24)
        splits = splitter.split(timestamps)

        train_sizes = [len(train_idx) for train_idx, _, _ in splits]
        for i in range(1, len(train_sizes)):
            assert train_sizes[i] > train_sizes[i - 1]

    def test_insufficient_data(self):
        """Should raise if not enough data for the requested folds."""
        timestamps = pd.date_range("2021-01-01", periods=100, freq="1h")
        splitter = WalkForwardSplitter(n_folds=5, test_window_bars=500)
        with pytest.raises(ValueError, match="Not enough data"):
            splitter.split(timestamps)

    def test_no_overlap(self):
        """Train and test indices should not overlap."""
        n = 10000
        timestamps = pd.date_range("2021-01-01", periods=n, freq="1h")
        splitter = WalkForwardSplitter(n_folds=3, test_window_bars=500, embargo_bars=24)
        splits = splitter.split(timestamps)

        for train_idx, test_idx, _ in splits:
            overlap = set(train_idx) & set(test_idx)
            assert len(overlap) == 0

    def test_forbid_kfold(self):
        try:
            from sklearn.model_selection import KFold
            with pytest.raises(ForbiddenKFoldError):
                assert_no_kfold(KFold(n_splits=5))
        except ImportError:
            pytest.skip("sklearn not installed")
