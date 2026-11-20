"""Tests for the QuantileGBM model."""

import numpy as np
import pytest

from cryptolab.ml.model import QuantileGBM


def _make_training_data(n: int = 1000, n_features: int = 10, seed: int = 42):
    rng = np.random.RandomState(seed)
    X = rng.randn(n, n_features)
    # y = linear combination + noise
    w = rng.randn(n_features)
    y = X @ w + rng.randn(n) * 0.5
    return X, y


class TestQuantileGBM:

    def test_train_and_predict(self):
        X, y = _make_training_data()
        model = QuantileGBM(backend="lightgbm", n_estimators=50)
        model.train(X, y)

        assert model.is_trained
        assert len(model.trained_quantiles) == 5

        pred = model.predict_median(X[0])
        assert isinstance(pred, float)

    def test_quantile_ordering(self):
        """Higher quantiles should generally predict higher values."""
        X, y = _make_training_data()
        model = QuantileGBM(backend="lightgbm", n_estimators=50)
        model.train(X, y)

        preds = model.predict_quantiles(X[0])
        sorted_preds = [preds[q] for q in sorted(preds.keys())]
        # Allow some tolerance but general ordering should hold
        assert sorted_preds[-1] >= sorted_preds[0]

    def test_interpolation(self):
        """Predicting at untrained quantile should interpolate."""
        X, y = _make_training_data()
        model = QuantileGBM(backend="lightgbm", n_estimators=50)
        model.train(X, y, quantiles=(0.1, 0.5, 0.9))

        # q=0.3 is not trained, should interpolate between 0.1 and 0.5
        pred_30 = model.predict_quantile(X[0], 0.3)
        pred_10 = model.predict_quantile(X[0], 0.1)
        pred_50 = model.predict_quantile(X[0], 0.5)
        assert pred_10 <= pred_30 <= pred_50 or pred_50 <= pred_30 <= pred_10

    def test_save_load(self, tmp_path):
        X, y = _make_training_data()
        model = QuantileGBM(backend="lightgbm", n_estimators=50)
        model.train(X, y)

        save_dir = tmp_path / "model"
        model.save(save_dir)

        loaded = QuantileGBM.load(save_dir)
        assert loaded.is_trained
        assert loaded.trained_quantiles == model.trained_quantiles

        # Predictions should match
        orig = model.predict_median(X[0])
        loaded_pred = loaded.predict_median(X[0])
        assert abs(orig - loaded_pred) < 1e-6

    def test_not_trained_error(self):
        model = QuantileGBM()
        with pytest.raises(RuntimeError, match="No trained models"):
            model.predict_median(np.array([1.0, 2.0]))


class TestPortfolioOptimizer:

    def test_size_position(self):
        from cryptolab.ml.predictor import MLPrediction
        from cryptolab.portfolio.optimizer import PortfolioOptimizer

        optimizer = PortfolioOptimizer(max_leverage=3.0)
        pred = MLPrediction(
            symbol="BTC",
            median_return=0.005,
            quantile_returns={0.1: -0.02, 0.25: -0.005, 0.5: 0.005, 0.75: 0.015, 0.9: 0.025},
            confidence=0.7,
            direction=1,
        )
        target = optimizer.size_position(pred, equity=10_000.0)
        assert target.position_usd > 0  # long
        assert target.direction == 1
        assert target.position_usd <= 10_000 * 0.3 * 3.0  # max constraint

    def test_zero_signal(self):
        from cryptolab.ml.predictor import MLPrediction
        from cryptolab.portfolio.optimizer import PortfolioOptimizer

        optimizer = PortfolioOptimizer()
        pred = MLPrediction(
            symbol="BTC",
            median_return=0.0,
            quantile_returns={0.5: 0.0},
            confidence=0.5,
            direction=0,
        )
        target = optimizer.size_position(pred, equity=10_000.0)
        assert target.position_usd == 0.0
