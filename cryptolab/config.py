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

    # --- Strategy: Donchian MTF ---
    mtf_lookbacks: List[int] = field(default_factory=lambda: [24, 72, 168])
    mtf_weights: List[float] = field(default_factory=lambda: [0.33, 0.34, 0.33])
    mtf_signal_deadzone: float = 0.05
    mtf_vol_target: float = 0.15
    mtf_vol_scalar_bounds: List[float] = field(default_factory=lambda: [0.5, 2.0])
    mtf_dd_max: float = 0.30
    mtf_dd_floor: float = 0.25
    mtf_rebalance_pct: float = 0.05
    mtf_use_trailing_stop: bool = False
    mtf_pyramid_max_units: int = 1        # max units including initial entry (1 = disabled)
    mtf_pyramid_spacing_atr: float = 0.5  # ATR multiple between pyramid adds

    # --- Strategy: Momentum blending ---
    mom_lookback: int = 168               # TSMOM lookback (168 = 28 days at 4H)
    mom_weight: float = 0.0              # 0 = pure breakout, 1 = pure momentum
    mom_entry_threshold: float = 0.3     # momentum-only entry threshold (abs score)

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
