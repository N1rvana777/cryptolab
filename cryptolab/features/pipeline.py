"""Feature pipeline: orchestrates all feature blocks and validates output."""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd

from cryptolab.features.registry import FeatureRegistry
from cryptolab.features.base import FeatureBlock
from cryptolab.features.technical import TechnicalFeatures
from cryptolab.features.donchian_features import DonchianFeatures
from cryptolab.features.microstructure import MicrostructureFeatures
from cryptolab.features.cross_asset import CrossAssetFeatures
from cryptolab.features.temporal import TemporalFeatures
from cryptolab.features.volatility import VolatilityFeatures
from cryptolab.features.momentum import MomentumFeatures
from cryptolab.features.funding import FundingFeatures
from cryptolab.features.orderbook import OrderBookFeatures
from cryptolab.features.sentiment import SentimentFeatures
from cryptolab.features.targets import compute_targets, TARGET_COLUMNS
from cryptolab.features.leakage_guard import LeakageGuard

logger = logging.getLogger(__name__)


def build_default_registry() -> FeatureRegistry:
    """Create registry with all standard feature blocks."""
    reg = FeatureRegistry()
    reg.register("technical", TechnicalFeatures())
    reg.register("donchian", DonchianFeatures())
    reg.register("microstructure", MicrostructureFeatures())
    reg.register("cross_asset", CrossAssetFeatures())
    reg.register("temporal", TemporalFeatures())
    reg.register("volatility", VolatilityFeatures())
    reg.register("momentum", MomentumFeatures())
    reg.register("funding", FundingFeatures())
    reg.register("orderbook", OrderBookFeatures())
    reg.register("sentiment", SentimentFeatures())
    return reg


class FeaturePipeline:
    """特征工程总编排器。把原始OHLCV变成ML可用的 (X, y) 矩阵。

    完整流程:
    1. 对每个币种分别调用9个FeatureBlock计算特征（全部shift(1)防泄漏）
    2. 跨币种计算CrossAsset特征（需要所有币种数据）
    3. 计算目标变量（fwd_return_1h/4h/24h，用未来数据，不作为特征）
    4. LeakageGuard验证：特征和目标不能有>0.95的相关性
    5. 丢弃前warmup_bars行（滚动窗口预热期，全是NaN）
    6. 输出: X(n_samples, n_features), y(n_samples,), feature_names

    用法:
        pipeline = FeaturePipeline()
        X, y, feature_names = pipeline.build(df, target_col="fwd_return_4h")
    """

    def __init__(
        self,
        groups: list[str] | None = None,
        warmup_bars: int = 168,
        registry: FeatureRegistry | None = None,
    ) -> None:
        self.registry = registry or build_default_registry()
        self.groups = groups
        self.warmup_bars = warmup_bars
        self.guard = LeakageGuard()
        self._feature_names: list[str] = []

    def build(
        self,
        df: pd.DataFrame,
        target_col: str = "fwd_return_4h",
        validate: bool = True,
    ) -> tuple[np.ndarray, np.ndarray, list[str]]:
        """从原始OHLCV构建特征矩阵X和目标向量y。

        这是训练时调用的核心方法。处理多币种数据时会自动按symbol分组计算。
        NaN和Inf会被替换为0（GBM可以处理，但不能有NaN输入）。

        输入: OHLCV DataFrame（可含symbol列表示多币种）
        输出: X(n_samples, n_features) float32, y(n_samples,) float32, 特征名列表
        """
        df = df.copy()

        # Compute features per symbol group if multi-symbol
        if "symbol" in df.columns:
            symbols = df["symbol"].unique()
            frames = []
            for sym in symbols:
                sym_df = df[df["symbol"] == sym].copy().reset_index(drop=True)
                sym_df = self._compute_features(sym_df)
                frames.append(sym_df)
            df = pd.concat(frames, ignore_index=True)
            # Cross-asset features need full DataFrame
            cross_block = self.registry.get("cross_asset") if "cross_asset" in (self.groups or self.registry._blocks) else None
            if cross_block:
                df = cross_block.compute(df)
        else:
            df = self._compute_features(df)

        # Compute targets
        if "symbol" in df.columns:
            frames = []
            for sym in df["symbol"].unique():
                sym_df = df[df["symbol"] == sym].copy()
                sym_df = compute_targets(sym_df)
                frames.append(sym_df)
            df = pd.concat(frames, ignore_index=True)
        else:
            df = compute_targets(df)

        # Get feature column names
        feature_names = self.registry.all_feature_names(self.groups)
        # Only include columns that actually exist
        feature_names = [f for f in feature_names if f in df.columns]
        self._feature_names = feature_names

        # Validate
        if validate:
            self.guard.validate_no_target_in_features(feature_names, TARGET_COLUMNS)
            self.guard.validate_lag_features(
                df.dropna(subset=[target_col]),
                feature_names,
                target_col=target_col,
            )

        # Drop warm-up rows (NaN from rolling windows)
        if "symbol" in df.columns:
            # Drop first warmup_bars per symbol
            df = df.groupby("symbol").apply(
                lambda g: g.iloc[self.warmup_bars:], include_groups=False
            ).reset_index(drop=True)
        else:
            df = df.iloc[self.warmup_bars:]

        # Drop rows where target is NaN (last few bars for forward returns)
        df = df.dropna(subset=[target_col])

        # Extract X, y
        X = df[feature_names].values.astype(np.float32)
        y = df[target_col].values.astype(np.float32)

        # Replace remaining NaN/inf with 0 in X
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

        logger.info(
            "Feature pipeline: X=%s, y=%s, features=%d",
            X.shape, y.shape, len(feature_names),
        )
        return X, y, feature_names

    def build_latest(self, df: pd.DataFrame) -> np.ndarray:
        """只计算最新一根K线的特征向量（实盘推理用）。

        和build()不同，这个方法不计算目标变量，只返回最后一行的特征。
        需要传入足够多的历史K线（至少warmup_bars根）作为滚动窗口的输入。

        输出: 特征向量 shape=(n_features,) float32
        """
        df = df.copy()
        df = self._compute_features(df)

        if not self._feature_names:
            self._feature_names = self.registry.all_feature_names(self.groups)
            self._feature_names = [f for f in self._feature_names if f in df.columns]

        row = df.iloc[-1]
        features = row[self._feature_names].values.astype(np.float32)
        return np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)

    def _compute_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Run all feature blocks except cross_asset (needs full DataFrame)."""
        for block in self.registry.get_groups(self.groups):
            if isinstance(block, CrossAssetFeatures):
                continue  # handled separately in build()
            df = block.compute(df)
        return df
