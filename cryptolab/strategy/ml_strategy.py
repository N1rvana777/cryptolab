"""ML-driven strategy adapter.

Wraps MLPredictor + PortfolioOptimizer into the BaseStrategy interface,
allowing the existing BacktestEngine and PositionManager to use ML
signals with zero modifications.
"""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd

from cryptolab.config import Config
from cryptolab.strategy.base import BaseStrategy, StrategySignal
from cryptolab.ml.predictor import MLPredictor, MLPrediction
from cryptolab.portfolio.optimizer import PortfolioOptimizer

logger = logging.getLogger(__name__)


class MLStrategy(BaseStrategy):
    """ML策略适配器：把ML预测结果转换成BacktestEngine可执行的StrategySignal。

    数据流: OHLCV → MLPredictor(计算特征+预测分位数) → PortfolioOptimizer(Kelly仓位)
         → StrategySignal(目标仓位+方向+置信度)

    因为继承了BaseStrategy，BacktestEngine和PositionManager无需任何修改。
    """

    def __init__(
        self,
        cfg: Config,
        predictor: MLPredictor,
        optimizer: PortfolioOptimizer,
    ) -> None:
        super().__init__(cfg, name="MLStrategy")
        self.predictor = predictor
        self.optimizer = optimizer
        self._current_dd: float = 0.0
        self._peak_equity: float = cfg.initial_capital

    def generate_signal(
        self,
        symbol: str,
        df: pd.DataFrame,
        equity: float,
        **kwargs,
    ) -> StrategySignal:
        """Generate trading signal from ML prediction.

        Args:
            symbol: Trading symbol (e.g., "BTC")
            df: OHLCV DataFrame with history for feature computation
            equity: Current account equity
            **kwargs: Extra context

        Returns:
            StrategySignal compatible with BacktestEngine
        """
        # Update drawdown tracking
        if equity > self._peak_equity:
            self._peak_equity = equity
        self._current_dd = max(0, 1.0 - equity / self._peak_equity)

        # Need minimum bars for feature computation
        if len(df) < self.cfg.features.warmup_bars + 10:
            return StrategySignal(
                target_position=0.0,
                signal="HOLD",
                confidence=0.0,
                strategy_name=self.name,
                metadata={"reason": "insufficient_bars"},
            )

        try:
            # Get ML prediction
            prediction = self.predictor.predict(symbol, df)

            # Size position
            target = self.optimizer.size_position(
                prediction, equity, self._current_dd
            )

            # Map to signal
            if target.direction > 0:
                signal = "LONG"
            elif target.direction < 0:
                signal = "SHORT"
            else:
                signal = "HOLD"

            return StrategySignal(
                target_position=target.position_usd,
                signal=signal,
                confidence=prediction.confidence,
                strategy_name=self.name,
                metadata={
                    "median_return": prediction.median_return,
                    "quantiles": prediction.quantile_returns,
                    "kelly_f": target.kelly_fraction,
                    "dd_scalar": 1.0 - self._current_dd,
                    "direction": target.direction,
                },
            )
        except Exception as e:
            logger.warning("MLStrategy error for %s: %s", symbol, e)
            return StrategySignal(
                target_position=0.0,
                signal="HOLD",
                confidence=0.0,
                strategy_name=self.name,
                metadata={"error": str(e)},
            )

    def reset(self, symbol: str) -> None:
        """Reset is a no-op for MLStrategy (stateless predictions)."""
        pass
