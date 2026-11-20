"""Data leakage (look-ahead bias) prevention for time-series features.

Ported from RetailLab's leakage_guard.py, adapted for crypto OHLCV data.
This is the most critical defensive module: if features accidentally include
future information, the ML model will appear brilliant in backtesting but
fail catastrophically in production.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class LookAheadLeakageError(Exception):
    """Raised when future information leakage is detected.

    Intentionally NOT caught by upstream handlers. Leakage is fatal —
    any model trained on leaked data is fundamentally untrustworthy.
    """


class LeakageGuard:
    """未来函数(look-ahead bias)防线。这是整个系统最关键的安全模块。

    如果特征不小心包含了未来信息，模型在回测中会表现极好但实盘必然失败。
    本类的所有检查都是"发现即致命"——抛出LookAheadLeakageError，不可捕获。

    四层防护:
    1. validate_lag_features: 检查特征-目标相关性（>0.95说明有泄漏）
    2. validate_train_test_split: 训练集的最晚时间必须早于测试集最早时间
    3. validate_embargo: 训练集和测试集之间必须有足够的间隔（防标签穿透）
    4. validate_no_target_in_features: fwd_return_*列绝对不能出现在特征矩阵中
    """

    def validate_lag_features(
        self,
        df: pd.DataFrame,
        feature_cols: list[str],
        target_col: str | None = None,
    ) -> None:
        """Verify that lag/rolling features do not contain future information.

        Checks correlation between each feature and the target at the same bar.
        A properly shifted feature should not have near-perfect correlation with
        the current-bar target.
        """
        if df.empty or not feature_cols:
            return

        if target_col and target_col in df.columns:
            for col in feature_cols:
                if col not in df.columns:
                    continue
                corr = df[col].corr(df[target_col])
                if abs(corr) > 0.95:
                    msg = (
                        f"LEAKAGE DETECTED: Feature '{col}' has {corr:.3f} correlation "
                        f"with target '{target_col}'. This suggests the feature includes "
                        f"current-bar information. Ensure .shift(1) is applied."
                    )
                    logger.error(msg)
                    raise LookAheadLeakageError(msg)

        logger.info("Lag feature validation passed for %d columns", len(feature_cols))

    def validate_train_test_split(
        self,
        train_dates: pd.Series,
        test_dates: pd.Series,
    ) -> None:
        """Verify that ALL training dates are before ALL test dates."""
        train_max = pd.to_datetime(train_dates).max()
        test_min = pd.to_datetime(test_dates).min()

        if train_max >= test_min:
            msg = (
                f"LEAKAGE DETECTED: Training data extends to {train_max} "
                f"but test data starts at {test_min}. "
                f"Training data must strictly precede test data. "
                f"Use TimeSeriesSplit, not KFold."
            )
            logger.error(msg)
            raise LookAheadLeakageError(msg)

        logger.info(
            "Train/test split validation passed (train_max=%s, test_min=%s)",
            train_max, test_min,
        )

    def validate_embargo(
        self,
        train_end: pd.Timestamp,
        test_start: pd.Timestamp,
        min_embargo_bars: int,
        interval_hours: int = 1,
    ) -> None:
        """Verify sufficient gap between train and test periods.

        The embargo prevents label leakage: features near the train/test
        boundary may contain information that bleeds through forward-return targets.
        """
        gap_hours = (test_start - train_end).total_seconds() / 3600
        required_hours = min_embargo_bars * interval_hours

        if gap_hours < required_hours:
            msg = (
                f"LEAKAGE DETECTED: Embargo too short. "
                f"Gap is {gap_hours:.0f}h but need {required_hours}h "
                f"({min_embargo_bars} bars × {interval_hours}h). "
                f"Train ends {train_end}, test starts {test_start}."
            )
            logger.error(msg)
            raise LookAheadLeakageError(msg)

        logger.info(
            "Embargo validation passed (gap=%.0fh, required=%dh)",
            gap_hours, required_hours,
        )

    def validate_no_target_in_features(
        self,
        feature_cols: list[str],
        target_cols: list[str],
    ) -> None:
        """Verify target columns are not included in the feature set."""
        overlap = set(feature_cols) & set(target_cols)
        if overlap:
            msg = (
                f"LEAKAGE DETECTED: Target columns found in feature set: {overlap}. "
                f"Target columns must NEVER be used as features."
            )
            logger.error(msg)
            raise LookAheadLeakageError(msg)

        logger.info("Target/feature separation validated")
