"""ML-driven position sizing using quantile predictions.

Analogous to RetailLab's Newsvendor model: the quantile spread from ML
predictions determines position size, just as the critical ratio determines
optimal order quantity.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

from cryptolab.ml.predictor import MLPrediction

logger = logging.getLogger(__name__)


@dataclass
class PositionTarget:
    """Target position for a single symbol."""
    symbol: str
    position_usd: float  # signed: positive=long, negative=short
    direction: int  # +1, -1, 0
    confidence: float
    kelly_fraction: float
    raw_size_usd: float  # before constraints


class PortfolioOptimizer:
    """把ML预测结果转换成具体仓位大小（Kelly公式）。

    仓位计算流程:
    1. 方向: median_return的正负号（正=做多，负=做空）
    2. Kelly比例: f* = |预期收益| / 方差。方差从q10-q90区间估算
       方差 = (spread / 2.58)²，其中2.58是80%置信区间对应的z值
    3. 缩放: Kelly比例 × 置信度 × 回撤缩放
    4. 约束: 不超过 equity × max_position_pct × max_leverage

    为什么用Kelly？
    Kelly公式给出最优杠杆率——在已知预期收益和方差时，最大化长期复利增长。
    但full Kelly波动太大，所以用kelly_cap(默认0.5)截断。
    """

    def __init__(
        self,
        equity: float = 10_000.0,
        max_position_pct: float = 0.3,
        max_leverage: float = 3.0,
        vol_target: float = 0.15,
        kelly_cap: float = 0.5,
        dd_max: float = 0.30,
        dd_floor: float = 0.25,
    ) -> None:
        self.equity = equity
        self.max_position_pct = max_position_pct
        self.max_leverage = max_leverage
        self.vol_target = vol_target
        self.kelly_cap = kelly_cap
        self.dd_max = dd_max
        self.dd_floor = dd_floor

    def size_position(
        self,
        prediction: MLPrediction,
        equity: float,
        current_dd: float = 0.0,
    ) -> PositionTarget:
        """Compute optimal position size from ML prediction.

        Args:
            prediction: MLPrediction with quantile returns.
            equity: Current account equity.
            current_dd: Current drawdown fraction (0 to 1, positive means in drawdown).

        Returns:
            PositionTarget with constrained position size.
        """
        median = prediction.median_return
        direction = prediction.direction

        if direction == 0:
            return PositionTarget(
                symbol=prediction.symbol,
                position_usd=0.0,
                direction=0,
                confidence=prediction.confidence,
                kelly_fraction=0.0,
                raw_size_usd=0.0,
            )

        # Kelly fraction: f* = expected_return / variance
        q10 = prediction.quantile_returns.get(0.1, median)
        q90 = prediction.quantile_returns.get(0.9, median)
        spread = abs(q90 - q10)
        variance = (spread / 2.58) ** 2  # approximate: 80% CI ≈ 2.58 sigma
        variance = max(variance, 1e-8)

        kelly_f = abs(median) / variance
        kelly_f = min(kelly_f, self.kelly_cap)  # cap Kelly

        # Scale by confidence
        raw_size = equity * kelly_f * prediction.confidence

        # Drawdown scaling (same logic as DonchianMTF)
        dd_scalar = 1.0
        if current_dd > 0:
            dd_frac = min(current_dd / self.dd_max, 1.0)
            dd_scalar = 1.0 - dd_frac * (1.0 - self.dd_floor)
        raw_size *= dd_scalar

        # Apply constraints
        max_pos = equity * self.max_position_pct * self.max_leverage
        position_usd = min(raw_size, max_pos)
        position_usd *= direction  # sign

        return PositionTarget(
            symbol=prediction.symbol,
            position_usd=position_usd,
            direction=direction,
            confidence=prediction.confidence,
            kelly_fraction=kelly_f,
            raw_size_usd=raw_size * direction,
        )

    def size_portfolio(
        self,
        predictions: list[MLPrediction],
        equity: float,
        current_dd: float = 0.0,
    ) -> list[PositionTarget]:
        """Size positions for all symbols with portfolio-level constraints."""
        targets = []
        for pred in predictions:
            target = self.size_position(pred, equity, current_dd)
            targets.append(target)

        # Portfolio leverage constraint
        total_abs = sum(abs(t.position_usd) for t in targets)
        max_total = equity * self.max_leverage
        if total_abs > max_total and total_abs > 0:
            scale = max_total / total_abs
            for t in targets:
                t.position_usd *= scale
            logger.info("Portfolio leverage scaled by %.2f", scale)

        return targets
