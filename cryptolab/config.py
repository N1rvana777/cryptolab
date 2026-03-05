"""Simplified Config dataclass — strategy/execution/risk params only."""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Config:
    # --- Symbols ---
    symbols: List[str] = field(default_factory=lambda: ["BTC", "ETH", "SOL"])
    interval: str = "4h"

    # --- Strategy: Donchian ---
    donchian_period: int = 20  # lookback for channel
    atr_period: int = 14
    atr_sl_mult: float = 2.0  # stop-loss = ATR * mult

    # --- Risk ---
    risk_per_trade: float = 0.02  # fraction of equity risked per trade
    max_portfolio_heat: float = 0.06  # max total risk across all positions
    leverage: float = 3.0
    max_leverage: Dict[str, float] = field(default_factory=dict)

    # --- Execution ---
    dry_run: bool = True
    slippage_bps: float = 15.0
    min_notional_usd: float = 10.0
    fail_cooldown_sec: int = 120

    # --- Data ---
    candle_lookback: int = 100
    data_source: str = "okx"  # "okx", "binance", "hl"

    # --- Backtest ---
    initial_capital: float = 10_000.0
    maker_fee_bps: float = 1.0
    taker_fee_bps: float = 3.5
