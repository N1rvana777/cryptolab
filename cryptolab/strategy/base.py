"""Base strategy ABC and StrategySignal dataclass."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

import pandas as pd


@dataclass
class StrategySignal:
    """Unified output from any strategy."""
    target_position: float = 0.0  # USD notional: positive=long, negative=short, 0=flat
    signal: str = "HOLD"  # "LONG", "SHORT", "HOLD", "FLAT", "CLOSE"
    confidence: float = 0.5
    suggested_stop_px: Optional[float] = None
    suggested_tp_px: Optional[float] = None
    strategy_name: str = ""
    order_type: str = "taker"  # "taker" or "maker"
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseStrategy(ABC):
    """All strategies must inherit this and implement generate_signal()."""

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
