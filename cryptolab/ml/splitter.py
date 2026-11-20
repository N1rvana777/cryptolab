"""Walk-forward cross-validation with embargo periods.

Ensures strict temporal ordering: all training data precedes test data,
with an embargo gap to prevent label leakage through forward-return targets.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class SplitInfo:
    """Metadata for a single train/test split."""
    fold: int
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    train_size: int
    test_size: int


class WalkForwardSplitter:
    """时序交叉验证（walk-forward CV），禁止使用KFold。

    为什么不能用KFold？
    KFold会随机打乱数据，导致未来数据出现在训练集中——这在时序预测中是致命错误。
    Walk-forward保证训练集永远在测试集之前：

        Fold 0: |-------- Train --------|--Embargo--|--- Test ---|
        Fold 1: |----------- Train ----------|--Embargo--|--- Test ---|
        Fold 2: |-------------- Train --------------|--Embargo--|--- Test ---|

    训练窗口逐折扩大（expanding window），测试窗口固定大小。
    Embargo（隔离期）: 训练集和测试集之间留出间隔，防止forward-return标签
    在边界处泄漏（因为fwd_return_4h需要看未来4根K线）。
    """

    def __init__(
        self,
        n_folds: int = 5,
        test_window_bars: int = 720,
        embargo_bars: int = 24,
        min_train_bars: int = 2000,
    ) -> None:
        self.n_folds = n_folds
        self.test_window_bars = test_window_bars
        self.embargo_bars = embargo_bars
        self.min_train_bars = min_train_bars

    def split(
        self,
        timestamps: pd.Series | np.ndarray,
    ) -> list[tuple[np.ndarray, np.ndarray, SplitInfo]]:
        """Generate (train_indices, test_indices, info) for each fold.

        Args:
            timestamps: Sorted timestamps array (one per sample).

        Returns:
            List of (train_idx, test_idx, SplitInfo) tuples.
        """
        n = len(timestamps)
        ts = pd.Series(timestamps).reset_index(drop=True)

        # Calculate split points: reserve space for test + embargo at end
        total_test = self.n_folds * self.test_window_bars
        total_embargo = self.n_folds * self.embargo_bars
        available = n - total_test - total_embargo

        if available < self.min_train_bars:
            raise ValueError(
                f"Not enough data: {n} bars, need at least "
                f"{self.min_train_bars + total_test + total_embargo} "
                f"({self.min_train_bars} min train + {self.n_folds} folds × "
                f"{self.test_window_bars} test + {self.embargo_bars} embargo)"
            )

        splits = []
        for fold in range(self.n_folds):
            # Expanding training window
            test_end_idx = n - (self.n_folds - fold - 1) * (self.test_window_bars + self.embargo_bars)
            test_start_idx = test_end_idx - self.test_window_bars
            train_end_idx = test_start_idx - self.embargo_bars
            train_start_idx = 0  # expanding window

            if train_end_idx < self.min_train_bars:
                logger.warning("Fold %d: train too small (%d), skipping", fold, train_end_idx)
                continue

            train_idx = np.arange(train_start_idx, train_end_idx)
            test_idx = np.arange(test_start_idx, test_end_idx)

            info = SplitInfo(
                fold=fold,
                train_start=ts.iloc[train_start_idx],
                train_end=ts.iloc[train_end_idx - 1],
                test_start=ts.iloc[test_start_idx],
                test_end=ts.iloc[test_end_idx - 1],
                train_size=len(train_idx),
                test_size=len(test_idx),
            )

            logger.info(
                "Fold %d: train[%s..%s] (%d bars) → embargo(%d) → test[%s..%s] (%d bars)",
                fold, info.train_start, info.train_end, info.train_size,
                self.embargo_bars, info.test_start, info.test_end, info.test_size,
            )

            splits.append((train_idx, test_idx, info))

        if not splits:
            raise ValueError("No valid folds could be generated")

        return splits


class ForbiddenKFoldError(Exception):
    """Raised when someone tries to use KFold on time-series data."""


def assert_no_kfold(cv: Any) -> None:
    """Raise ForbiddenKFoldError if cv is a KFold instance."""
    try:
        from sklearn.model_selection import KFold, StratifiedKFold
        if isinstance(cv, (KFold, StratifiedKFold)):
            raise ForbiddenKFoldError(
                "KFold is FORBIDDEN for time-series data. "
                "Use WalkForwardSplitter instead."
            )
    except ImportError:
        pass
