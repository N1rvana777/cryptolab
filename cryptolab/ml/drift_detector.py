"""Concept drift detection for ML models.

Monitors directional accuracy and pinball loss over time.
Alerts when performance degrades significantly from baseline.
Ported from RetailLab's drift_detector.py.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

import numpy as np

logger = logging.getLogger(__name__)


class DriftSeverity(Enum):
    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class DriftAlert:
    severity: DriftSeverity
    metric: str
    z_score: float
    baseline_mean: float
    recent_mean: float
    message: str


class DriftDetector:
    """模型性能漂移检测器。监控实盘中模型是否开始退化。

    原理: 比较基线窗口（最近720bar）和近期窗口（最近168bar）的指标均值。
    如果近期均值偏离基线超过2σ → WARNING，超过3σ → CRITICAL。

    典型用法: 监控方向准确率。如果模型方向准确率从60%掉到50%以下，
    说明市场regime发生了变化，模型需要重新训练。
    """

    def __init__(
        self,
        baseline_window: int = 720,
        recent_window: int = 168,
        warning_threshold: float = 2.0,
        critical_threshold: float = 3.0,
    ) -> None:
        self.baseline_window = baseline_window
        self.recent_window = recent_window
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold

    def check(
        self,
        metric_values: np.ndarray,
        metric_name: str = "directional_accuracy",
        higher_is_better: bool = True,
    ) -> DriftAlert:
        """Check if recent metric values have drifted from baseline.

        Args:
            metric_values: Array of metric values over time.
            metric_name: Name for logging.
            higher_is_better: Whether higher values indicate better performance.

        Returns:
            DriftAlert with severity level and details.
        """
        n = len(metric_values)
        if n < self.baseline_window + self.recent_window:
            return DriftAlert(
                severity=DriftSeverity.OK,
                metric=metric_name,
                z_score=0.0,
                baseline_mean=0.0,
                recent_mean=0.0,
                message="Insufficient data for drift detection",
            )

        baseline = metric_values[-(self.baseline_window + self.recent_window):-self.recent_window]
        recent = metric_values[-self.recent_window:]

        b_mean = float(np.mean(baseline))
        b_std = float(np.std(baseline))
        r_mean = float(np.mean(recent))

        if b_std < 1e-9:
            z = 0.0
        else:
            z = (b_mean - r_mean) / b_std if higher_is_better else (r_mean - b_mean) / b_std

        if z >= self.critical_threshold:
            severity = DriftSeverity.CRITICAL
            msg = f"CRITICAL drift: {metric_name} degraded by {z:.1f}σ (baseline={b_mean:.4f}, recent={r_mean:.4f})"
        elif z >= self.warning_threshold:
            severity = DriftSeverity.WARNING
            msg = f"WARNING drift: {metric_name} degraded by {z:.1f}σ (baseline={b_mean:.4f}, recent={r_mean:.4f})"
        else:
            severity = DriftSeverity.OK
            msg = f"{metric_name} stable (z={z:.2f}σ)"

        if severity != DriftSeverity.OK:
            logger.warning(msg)
        else:
            logger.debug(msg)

        return DriftAlert(
            severity=severity,
            metric=metric_name,
            z_score=z,
            baseline_mean=b_mean,
            recent_mean=r_mean,
            message=msg,
        )
