"""End-to-end ML training pipeline."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from cryptolab.features.pipeline import FeaturePipeline
from cryptolab.features.leakage_guard import LeakageGuard
from cryptolab.ml.model import QuantileGBM
from cryptolab.ml.splitter import WalkForwardSplitter, SplitInfo

logger = logging.getLogger(__name__)


@dataclass
class FoldResult:
    """Metrics for a single CV fold."""
    fold: int
    info: SplitInfo
    pinball_losses: dict[float, float] = field(default_factory=dict)
    directional_accuracy: float = 0.0
    mean_pred_return: float = 0.0


@dataclass
class TrainingReport:
    """Summary of the full training run."""
    n_samples: int
    n_features: int
    feature_names: list[str]
    fold_results: list[FoldResult]
    avg_directional_accuracy: float = 0.0
    avg_pinball_loss: float = 0.0


def pinball_loss(y_true: np.ndarray, y_pred: np.ndarray, quantile: float) -> float:
    """分位数损失函数（pinball loss）。评估分位数预测的准确性。

    当预测偏低时（实际>预测），惩罚权重=quantile；
    当预测偏高时（实际<预测），惩罚权重=1-quantile。
    所以q90的模型会更不愿意低估（因为低估的惩罚是0.9，高估只有0.1）。
    """
    diff = y_true - y_pred
    return float(np.mean(np.where(diff >= 0, quantile * diff, (quantile - 1) * diff)))


class Trainer:
    """ML训练编排器。把"原始数据→特征→交叉验证→训练→保存"串成一条流水线。

    核心方法train()的流程:
    1. 调用FeaturePipeline.build()构建特征矩阵X和目标y
    2. WalkForwardSplitter把数据划分成N折（扩展窗口+embargo）
    3. 每折: 训练QuantileGBM -> 在测试集上评估方向准确率和pinball loss
    4. 在全量数据上训练最终模型
    5. 保存模型+特征名到磁盘
    """

    def __init__(
        self,
        pipeline: FeaturePipeline,
        splitter: WalkForwardSplitter,
        model_config: Optional[dict] = None,
    ) -> None:
        self.pipeline = pipeline
        self.splitter = splitter
        self.model_config = model_config or {}
        self.guard = LeakageGuard()

    def train(
        self,
        df: pd.DataFrame,
        target_col: str = "fwd_return_4h",
        save_dir: Optional[Path] = None,
    ) -> tuple[QuantileGBM, TrainingReport]:
        """Run the full training pipeline.

        1. Build features via FeaturePipeline
        2. Walk-forward CV with LeakageGuard validation per fold
        3. Train final model on all data
        4. Save model artifacts

        Returns (trained_model, training_report).
        """
        logger.info("Building feature matrix...")
        X, y, feature_names = self.pipeline.build(df, target_col=target_col)

        # Get timestamps for splitting (after warmup/NaN removal)
        # We need to reconstruct timestamps from the processed data
        n_total = len(X)
        timestamps = pd.RangeIndex(n_total)  # ordinal index for splitting

        logger.info("Running walk-forward CV (%d folds)...", self.splitter.n_folds)
        splits = self.splitter.split(timestamps)

        fold_results = []
        for train_idx, test_idx, info in splits:
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]

            # Train fold model
            fold_model = QuantileGBM(**self.model_config)
            fold_model.train(X_train, y_train)

            # Evaluate
            result = FoldResult(fold=info.fold, info=info)

            for q in fold_model.trained_quantiles:
                preds = np.array([fold_model.predict_quantile(X_test[i], q) for i in range(len(X_test))])
                result.pinball_losses[q] = pinball_loss(y_test, preds, q)

            # Directional accuracy at median
            median_preds = np.array([fold_model.predict_median(X_test[i]) for i in range(len(X_test))])
            pred_dir = np.sign(median_preds)
            actual_dir = np.sign(y_test)
            result.directional_accuracy = float(np.mean(pred_dir == actual_dir))
            result.mean_pred_return = float(np.mean(median_preds))

            fold_results.append(result)
            logger.info(
                "Fold %d: dir_acc=%.3f, pinball_q50=%.6f",
                info.fold, result.directional_accuracy,
                result.pinball_losses.get(0.5, 0),
            )

        # Train final model on all data
        logger.info("Training final model on all %d samples...", n_total)
        final_model = QuantileGBM(**self.model_config)
        final_model.train(X, y)

        # Save
        if save_dir:
            save_dir = Path(save_dir)
            final_model.save(save_dir)
            # Save feature names
            (save_dir / "feature_names.json").write_text(
                json.dumps(feature_names, indent=2)
            )
            logger.info("Model saved to %s", save_dir)

        # Build report
        report = TrainingReport(
            n_samples=n_total,
            n_features=len(feature_names),
            feature_names=feature_names,
            fold_results=fold_results,
            avg_directional_accuracy=float(np.mean([r.directional_accuracy for r in fold_results])),
            avg_pinball_loss=float(np.mean([
                r.pinball_losses.get(0.5, 0) for r in fold_results
            ])),
        )

        logger.info(
            "Training complete: avg_dir_acc=%.3f, avg_pinball=%.6f",
            report.avg_directional_accuracy, report.avg_pinball_loss,
        )
        return final_model, report
