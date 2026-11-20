"""Live inference: loads a trained model and produces predictions."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from cryptolab.features.pipeline import FeaturePipeline
from cryptolab.ml.model import QuantileGBM

logger = logging.getLogger(__name__)


@dataclass
class MLPrediction:
    """Output of a single prediction."""
    symbol: str
    median_return: float
    quantile_returns: dict[float, float]
    confidence: float  # 0-1, based on quantile spread
    direction: int  # +1 long, -1 short, 0 neutral
    metadata: dict = field(default_factory=dict)


class MLPredictor:
    """加载已训练模型，对最新K线做推理。回测和实盘都用这个类。

    用法:
        predictor = MLPredictor(model_dir="models/latest", pipeline=pipeline)
        prediction = predictor.predict("BTC", df)  # df需要足够长的历史用于特征计算
        print(prediction.direction, prediction.confidence)
    """

    def __init__(self, model_dir: Path, pipeline: FeaturePipeline) -> None:
        self.model = QuantileGBM.load(Path(model_dir))
        self.pipeline = pipeline

        # Load feature names
        fn_path = Path(model_dir) / "feature_names.json"
        self.feature_names = json.loads(fn_path.read_text())
        self.pipeline._feature_names = self.feature_names

    def predict(self, symbol: str, df: pd.DataFrame) -> MLPrediction:
        """Generate prediction for a symbol given its recent OHLCV data.

        Args:
            symbol: Trading symbol (e.g., "BTC")
            df: OHLCV DataFrame with enough history for feature computation.

        Returns:
            MLPrediction with return distribution and direction.
        """
        features = self.pipeline.build_latest(df)
        quantile_returns = self.model.predict_quantiles(features)

        median = quantile_returns.get(0.5, 0.0)
        q10 = quantile_returns.get(0.1, median)
        q90 = quantile_returns.get(0.9, median)

        # Confidence: inverse of quantile spread (tighter = more confident)
        spread = abs(q90 - q10)
        confidence = 1.0 / (1.0 + spread * 100)  # scale to 0-1

        # Direction
        direction = 1 if median > 0 else (-1 if median < 0 else 0)

        return MLPrediction(
            symbol=symbol,
            median_return=median,
            quantile_returns=quantile_returns,
            confidence=confidence,
            direction=direction,
        )
