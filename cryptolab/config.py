"""Simplified Config dataclass — strategy/execution/risk params only."""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class FeatureConfig:
    feature_groups: List[str] = field(default_factory=lambda: [
        "technical", "donchian", "microstructure", "cross_asset",
        "temporal", "volatility", "momentum",
        "funding", "orderbook", "sentiment",
    ])
    primary_target: str = "fwd_return_4h"
    warmup_bars: int = 168

@dataclass
class MLConfig:
    backend: str = "lightgbm"
    quantiles: List[float] = field(default_factory=lambda: [0.1, 0.25, 0.5, 0.75, 0.9])
    n_estimators: int = 500
    learning_rate: float = 0.05
    max_depth: int = 6
    subsample: float = 0.8
    colsample_bytree: float = 0.8
    reg_alpha: float = 0.1
    reg_lambda: float = 0.1
    n_folds: int = 5
    embargo_bars: int = 24
    test_window_bars: int = 720
    model_dir: str = "models"

@dataclass
class PortfolioConfig:
    method: str = "kelly"
    max_position_pct: float = 0.3
    max_leverage: float = 3.0
    vol_target: float = 0.15
    kelly_cap: float = 0.5
    dd_max: float = 0.30
    dd_floor: float = 0.25


@dataclass
class SlippageConfig:
    """Dynamic slippage model (Ludwig).

    - "fixed":     flat bps (legacy)
    - "linear":    Slippage_dollar = K2 * |trade_size|
    - "quadratic": Slippage_dollar = (K1 / ADV) * trade_size^2
    - "auto":      linear if |trade|/ADV < threshold, else quadratic
    """
    model: str = "fixed"            # "fixed", "linear", "quadratic", "auto"
    k1: float = 0.01                # quadratic coefficient
    k2_bps: float = 15.0            # linear coefficient in bps (same as fixed_bps)
    adv_window_days: int = 20       # rolling ADV lookback in calendar days
    auto_threshold: float = 0.001   # |trade|/ADV threshold for auto-select


@dataclass
class Config:
    # --- Symbols ---
    symbols: List[str] = field(default_factory=lambda: ["BTC", "ETH", "SOL"])
    interval: str = "1h"

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
    mtf_regime_filter: bool = True        # enable ADX + vol contraction regime filter
    mtf_adx_period: int = 20             # ADX lookback (8H bars)

    # --- Strategy: Momentum blending ---
    mom_lookback: int = 168               # TSMOM lookback (168 = 28 days at 4H)
    mom_weight: float = 0.0              # 0 = pure breakout, 1 = pure momentum
    mom_entry_threshold: float = 0.3     # momentum-only entry threshold (abs score)

    # --- Signal Experiment: Volume-Weighted ---
    vw_weight: float = 0.0           # 0=disabled; scales vol ratio effect on agreement
    vw_lookback: int = 20            # volume ratio lookback

    # --- Signal Experiment: Mean-Reversion Filter ---
    mr_weight: float = 0.0           # 0=no filter, 1=full block at extreme RSI
    mr_rsi_period: int = 14          # RSI period

    # --- Signal Experiment: Cross-Sectional ---
    cs_weight: float = 0.0           # 0=equal weight, higher=stronger rank adjustment
    cs_lookback: int = 168           # TSMOM lookback for ranking

    # --- Risk ---
    risk_per_trade: float = 0.02  # fraction of equity risked per trade
    max_portfolio_heat: float = 0.06  # max total risk across all positions
    leverage: float = 3.0
    max_leverage: Dict[str, float] = field(default_factory=dict)

    # --- Execution ---
    dry_run: bool = True
    slippage_bps: float = 15.0
    min_notional_usd: float = 1.0
    fail_cooldown_sec: int = 120

    # --- Data ---
    candle_lookback: int = 100
    data_source: str = "okx"  # "okx", "binance", "hl"

    # --- Strategy: Mean Reversion ---
    mr_zscore_lookback: int = 168     # Z-score SMA/std lookback (bars)
    mr_entry_z: float = 2.0          # entry Z threshold
    mr_exit_z: float = 0.25          # exit Z threshold (|z| < this -> close)
    mr_stop_z: float = 3.5           # stop Z threshold (|z| > this -> stop loss)
    mr_adx_entry_max: float = 20.0   # ADX below this = ranging, allow entries
    mr_adx_block: float = 25.0       # ADX above this = trending, block entries

    # --- Backtest ---
    initial_capital: float = 10_000.0
    maker_fee_bps: float = 1.0
    taker_fee_bps: float = 3.5
    slippage: SlippageConfig = field(default_factory=SlippageConfig)

    # --- ML Pipeline ---
    features: FeatureConfig = field(default_factory=FeatureConfig)
    ml: MLConfig = field(default_factory=MLConfig)
    portfolio_opt: PortfolioConfig = field(default_factory=PortfolioConfig)
