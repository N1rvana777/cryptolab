"""Base strategy ABC and StrategySignal dataclass."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

import pandas as pd


@dataclass
class StrategySignal:
    """策略的统一输出格式。BacktestEngine和PositionManager都只认这个接口。

    target_position: 目标仓位（USD名义值），正数=做多，负数=做空，0=空仓
    signal: 信号类型标签（用于日志和分析，不影响执行逻辑）
    """
    target_position: float = 0.0  # USD notional: positive=long, negative=short, 0=flat
    signal: str = "HOLD"  # "LONG", "SHORT", "HOLD", "FLAT", "CLOSE"
    confidence: float = 0.5
    suggested_stop_px: Optional[float] = None
    suggested_tp_px: Optional[float] = None
    strategy_name: str = ""
    order_type: str = "taker"  # "taker" or "maker"
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseStrategy(ABC):
    """策略基类。所有策略必须继承并实现generate_signal()。

    DonchianMTF(规则型)和MLStrategy(ML型)都继承自此类，
    因此BacktestEngine和PositionManager不需要区分策略类型。
    """

    def __init__(self, cfg, name: str = "BaseStrategy"):
        self.cfg = cfg
        self.name = name

    @abstractmethod
    def generate_signal(self, symbol: str, df: pd.DataFrame, equity: float, **kwargs) -> StrategySignal:
        """
        Generate a trading signal from OHLCV data.

        Args:
            symbol: trading symbol (e.g. "BTC")
            df: OHLCV DataFrame with columns: timestamp, open, high, low, close, volume
            equity: current account equity in USD
            **kwargs: extra context

        Returns:
            StrategySignal with target position and metadata
        """
        raise NotImplementedError

    def reset(self, symbol: str):
        """Reset internal state for a symbol."""
        pass
