"""Tests for drift detection."""

import numpy as np

from cryptolab.ml.drift_detector import DriftDetector, DriftSeverity


class TestDriftDetector:

    def test_no_drift(self):
        detector = DriftDetector(baseline_window=100, recent_window=20)
        values = np.random.RandomState(42).normal(0.55, 0.05, 120)
        alert = detector.check(values, "accuracy")
        assert alert.severity == DriftSeverity.OK

    def test_warning_drift(self):
        detector = DriftDetector(baseline_window=100, recent_window=20)
        baseline = np.random.RandomState(42).normal(0.55, 0.02, 100)
        recent = np.random.RandomState(43).normal(0.50, 0.02, 20)
        values = np.concatenate([baseline, recent])
        alert = detector.check(values, "accuracy")
        assert alert.severity in (DriftSeverity.WARNING, DriftSeverity.CRITICAL)

    def test_insufficient_data(self):
        detector = DriftDetector(baseline_window=100, recent_window=20)
        values = np.array([0.5, 0.6])
        alert = detector.check(values, "accuracy")
        assert alert.severity == DriftSeverity.OK
        assert "Insufficient" in alert.message
