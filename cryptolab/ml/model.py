"""Quantile gradient boosted model for return distribution prediction.

Ported from RetailLab's GradientBoostedQuantileForecaster, adapted for
crypto return prediction. Trains one model per quantile level.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Literal

import numpy as np

logger = logging.getLogger(__name__)

STANDARD_QUANTILES: tuple[float, ...] = (0.1, 0.25, 0.5, 0.75, 0.9)


class QuantileGBM:
    """分位数梯度提升回归模型，预测收益率的分布而非单一点估计。

    为什么用分位数回归而不是普通回归？
    - 普通回归只给一个预测值（均值），无法衡量不确定性
    - 分位数回归同时预测q10/q25/q50/q75/q90，给出收益率的完整分布
    - q50就是中位数预测（方向信号），q10-q90的宽度衡量置信度
    - 宽度越窄 = 模型越确定 = 可以加大仓位（Kelly公式的关键输入）

    实现: 对每个分位数水平训练一个独立的LightGBM/XGBoost模型。
    对未训练的分位数，在最近两个已训练模型之间线性插值。
    """

    def __init__(
        self,
        backend: Literal["xgboost", "lightgbm"] = "lightgbm",
        n_estimators: int = 500,
        learning_rate: float = 0.05,
        max_depth: int = 6,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        reg_alpha: float = 0.1,
        reg_lambda: float = 0.1,
        min_child_samples: int = 20,
    ) -> None:
        self._backend = backend
        self._n_estimators = n_estimators
        self._learning_rate = learning_rate
        self._max_depth = max_depth
        self._subsample = subsample
        self._colsample_bytree = colsample_bytree
        self._reg_alpha = reg_alpha
        self._reg_lambda = reg_lambda
        self._min_child_samples = min_child_samples
        self._models: dict[float, Any] = {}

    @property
    def is_trained(self) -> bool:
        return len(self._models) > 0

    @property
    def trained_quantiles(self) -> tuple[float, ...]:
        return tuple(sorted(self._models.keys()))

    def train(
        self,
        x_train: np.ndarray,
        y_train: np.ndarray,
        quantiles: tuple[float, ...] | None = None,
    ) -> None:
        """Train one model per quantile level."""
        quantiles = quantiles or STANDARD_QUANTILES

        for q in quantiles:
            logger.info("Training %s model at quantile %.3f", self._backend, q)
            model = self._build_model(q)
            model.fit(x_train, y_train)
            self._models[q] = model

        logger.info(
            "Training complete: %d quantile models (%s)",
            len(self._models),
            ", ".join(f"{q:.2f}" for q in sorted(self._models)),
        )

    def predict_quantiles(self, features: np.ndarray) -> dict[float, float]:
        """Predict at all trained quantiles. Returns {quantile: prediction}."""
        if not self._models:
            raise RuntimeError("No trained models. Call train() first.")
        feat_2d = features.reshape(1, -1) if features.ndim == 1 else features
        return {q: float(m.predict(feat_2d)[0]) for q, m in sorted(self._models.items())}

    def predict_quantile(self, features: np.ndarray, quantile: float) -> float:
        """预测指定分位数。如果该分位数没有对应模型，在相邻模型间线性插值。"""
        if not self._models:
            raise RuntimeError("No trained models. Call train() first.")

        feat_2d = features.reshape(1, -1) if features.ndim == 1 else features

        # Exact match
        if quantile in self._models:
            return float(self._models[quantile].predict(feat_2d)[0])

        # Interpolation
        sorted_qs = sorted(self._models.keys())

        if quantile <= sorted_qs[0]:
            return float(self._models[sorted_qs[0]].predict(feat_2d)[0])
        if quantile >= sorted_qs[-1]:
            return float(self._models[sorted_qs[-1]].predict(feat_2d)[0])

        lower_q = max(q for q in sorted_qs if q <= quantile)
        upper_q = min(q for q in sorted_qs if q >= quantile)

        if lower_q == upper_q:
            return float(self._models[lower_q].predict(feat_2d)[0])

        lower_pred = float(self._models[lower_q].predict(feat_2d)[0])
        upper_pred = float(self._models[upper_q].predict(feat_2d)[0])

        weight = (quantile - lower_q) / (upper_q - lower_q)
        return lower_pred + weight * (upper_pred - lower_pred)

    def predict_median(self, features: np.ndarray) -> float:
        return self.predict_quantile(features, quantile=0.5)

    def save(self, path: Path) -> None:
        """Save all quantile models and metadata."""
        import joblib

        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)

        for q, model in self._models.items():
            joblib.dump(model, path / f"model_q{q:.2f}.joblib")

        meta = {
            "backend": self._backend,
            "quantiles": list(sorted(self._models.keys())),
            "n_estimators": self._n_estimators,
            "learning_rate": self._learning_rate,
            "max_depth": self._max_depth,
        }
        (path / "metadata.json").write_text(json.dumps(meta, indent=2))
        logger.info("Saved %d models to %s", len(self._models), path)

    @classmethod
    def load(cls, path: Path) -> QuantileGBM:
        """Load a saved QuantileGBM from disk."""
        import joblib

        path = Path(path)
        meta = json.loads((path / "metadata.json").read_text())

        instance = cls(
            backend=meta["backend"],
            n_estimators=meta["n_estimators"],
            learning_rate=meta["learning_rate"],
            max_depth=meta["max_depth"],
        )

        for q in meta["quantiles"]:
            model_path = path / f"model_q{q:.2f}.joblib"
            instance._models[q] = joblib.load(model_path)

        logger.info("Loaded %d models from %s", len(instance._models), path)
        return instance

    def _build_model(self, quantile: float) -> Any:
        if self._backend == "lightgbm":
            import lightgbm as lgb
            return lgb.LGBMRegressor(
                objective="quantile",
                alpha=quantile,
                n_estimators=self._n_estimators,
                learning_rate=self._learning_rate,
                num_leaves=2**self._max_depth - 1,
                min_child_samples=self._min_child_samples,
                subsample=self._subsample,
                colsample_bytree=self._colsample_bytree,
                reg_alpha=self._reg_alpha,
                reg_lambda=self._reg_lambda,
                verbose=-1,
            )
        else:
            import xgboost as xgb
            return xgb.XGBRegressor(
                objective="reg:quantileerror",
                quantile_alpha=quantile,
                n_estimators=self._n_estimators,
                learning_rate=self._learning_rate,
                max_depth=self._max_depth,
                subsample=self._subsample,
                colsample_bytree=self._colsample_bytree,
                reg_alpha=self._reg_alpha,
                reg_lambda=self._reg_lambda,
                verbosity=0,
            )
