"""Mean Reversion Z-Score strategy: buy dips, sell rips in ranging markets.

Complements DonchianMTF (trend-following) by profiting in low-ADX regimes.
Uses inverted regime filter: activates when ADX < 20 (choppy), blocks when ADX > 25 (trending).
"""

import math
from typing import Dict, Optional

import numpy as np
import pandas as pd

from cryptolab.config import Config
from cryptolab.strategy.base import BaseStrategy, StrategySignal
from cryptolab.strategy.donchian_mtf import _compute_adx
from cryptolab.backtest.metrics import PERIODS_PER_YEAR
from cryptolab.indicators.core import compute_atr


class MeanReversionZScore(BaseStrategy):
    """Z-score based mean reversion strategy.

    Entry: Z-score crosses beyond entry threshold (price far from mean)
    Exit:  Z-score reverts to near zero (mean reversion target hit)
    Stop:  Z-score keeps going (trend taking over, mean reversion failed)

    Regime filter (inverted from Donchian):
    - ADX < 20:  full position (ranging market, ideal for mean reversion)
    - ADX 20-25: half position (gray zone)
    - ADX > 25:  no new entries (trending, dangerous for mean reversion)
    """

    def __init__(self, cfg: Config):
        super().__init__(cfg, name="MeanReversionZScore")
        self._state: Dict[str, dict] = {}

    def _get_state(self, symbol: str) -> dict:
        if symbol not in self._state:
            self._state[symbol] = {
                "side": None,
                "entry_px": None,
                "entry_z": None,
                "peak_equity": None,
            }
        return self._state[symbol]

    def reset(self, symbol: str):
        self._state.pop(symbol, None)

    def generate_signal(self, symbol: str, df: pd.DataFrame, equity: float,
                        **kwargs) -> StrategySignal:
        cfg = self.cfg
        st = self._get_state(symbol)

        lookback = cfg.mr_zscore_lookback
        min_bars = max(lookback + 10, 60)
        if len(df) < min_bars:
            return StrategySignal(signal="HOLD", strategy_name=self.name)

        closes = df["close"].values
        highs = df["high"].values
        lows = df["low"].values
        close = float(closes[-1])

        # Z-score
        window = closes[-lookback:]
        sma = float(np.mean(window))
        std = float(np.std(window, ddof=1))
        if std < 1e-10 or sma < 1e-10:
            return StrategySignal(signal="HOLD", strategy_name=self.name)
        z = (close - sma) / std

        # ADX-based regime (inverted: low ADX = good for mean reversion)
        adx_val = _compute_adx(
            highs.tolist(), lows.tolist(), closes.tolist(), cfg.mtf_adx_period)
        if adx_val is None:
            regime_scale = 1.0
        elif adx_val < cfg.mr_adx_entry_max:
            regime_scale = 1.0  # ranging -> full
        elif adx_val < cfg.mr_adx_block:
            regime_scale = 0.5  # gray zone
        else:
            regime_scale = 0.0  # trending -> block

        # ATR for position sizing
        candles = [{"h": h, "l": l, "c": c, "v": v}
                   for h, l, c, v in zip(highs, lows, closes, df["volume"].values)]
        atr = compute_atr(candles, cfg.atr_period)
        if atr is None or atr <= 0:
            atr = close * 0.02  # fallback

        # Vol targeting + DD scaling
        ppy = PERIODS_PER_YEAR.get(cfg.interval, 2190)
        atr_pct = atr / close
        ann_vol = atr_pct * math.sqrt(ppy)
        vol_scalar = max(0.5, min(2.0, cfg.mtf_vol_target / ann_vol)) if ann_vol > 0 else 1.0

        if st["peak_equity"] is None:
            st["peak_equity"] = equity
        else:
            st["peak_equity"] = max(st["peak_equity"], equity)
        current_dd = (st["peak_equity"] - equity) / st["peak_equity"] if st["peak_equity"] > 0 else 0
        if current_dd >= cfg.mtf_dd_max:
            dd_scalar = cfg.mtf_dd_floor
        elif cfg.mtf_dd_max > 0:
            dd_scalar = 1.0 - (1.0 - cfg.mtf_dd_floor) * (current_dd / cfg.mtf_dd_max)
        else:
            dd_scalar = 1.0

        meta = {
            "z_score": z, "sma": sma, "std": std,
            "adx": adx_val, "regime_scale": regime_scale,
            "vol_scalar": vol_scalar, "dd_scalar": dd_scalar,
            "ann_vol": ann_vol,
        }

        # --- EXIT LOGIC ---
        if st["side"] == "long":
            if z >= -cfg.mr_exit_z:
                # Mean reversion target hit
                st["side"] = None
                st["entry_px"] = None
                st["entry_z"] = None
                meta["exit_reason"] = "mean_revert"
                return StrategySignal(
                    target_position=0.0, signal="CLOSE",
                    strategy_name=self.name, metadata=meta)
            if z < -cfg.mr_stop_z:
                # Stop loss: price kept falling
                st["side"] = None
                st["entry_px"] = None
                st["entry_z"] = None
                meta["exit_reason"] = "zscore_stop"
                return StrategySignal(
                    target_position=0.0, signal="CLOSE",
                    strategy_name=self.name, metadata=meta)

        elif st["side"] == "short":
            if z <= cfg.mr_exit_z:
                st["side"] = None
                st["entry_px"] = None
                st["entry_z"] = None
                meta["exit_reason"] = "mean_revert"
                return StrategySignal(
                    target_position=0.0, signal="CLOSE",
                    strategy_name=self.name, metadata=meta)
            if z > cfg.mr_stop_z:
                st["side"] = None
                st["entry_px"] = None
                st["entry_z"] = None
                meta["exit_reason"] = "zscore_stop"
                return StrategySignal(
                    target_position=0.0, signal="CLOSE",
                    strategy_name=self.name, metadata=meta)

        # --- ENTRY LOGIC ---
        if st["side"] is None and regime_scale > 0:
            # Position sizing: risk-based
            stop_z_dist = cfg.mr_stop_z - cfg.mr_entry_z
            stop_dist_pct = stop_z_dist * std / close if close > 0 else 0.1
            if stop_dist_pct <= 0:
                stop_dist_pct = 0.01

            risk_usd = equity * cfg.risk_per_trade
            base_position = (risk_usd / stop_dist_pct) * cfg.leverage
            max_position = equity * cfg.leverage
            position_usd = base_position * vol_scalar * dd_scalar * regime_scale
            position_usd = min(position_usd, max_position)

            if z < -cfg.mr_entry_z and position_usd > 0:
                st["side"] = "long"
                st["entry_px"] = close
                st["entry_z"] = z
                return StrategySignal(
                    target_position=position_usd, signal="LONG",
                    strategy_name=self.name, metadata=meta)

            if z > cfg.mr_entry_z and position_usd > 0:
                st["side"] = "short"
                st["entry_px"] = close
                st["entry_z"] = z
                return StrategySignal(
                    target_position=-position_usd, signal="SHORT",
                    strategy_name=self.name, metadata=meta)

        # --- HOLD ---
        if st["side"] == "long":
            # Re-derive position from state
            stop_z_dist = cfg.mr_stop_z - cfg.mr_entry_z
            stop_dist_pct = stop_z_dist * std / close if close > 0 else 0.1
            if stop_dist_pct <= 0:
                stop_dist_pct = 0.01
            risk_usd = equity * cfg.risk_per_trade
            base_position = (risk_usd / stop_dist_pct) * cfg.leverage
            max_position = equity * cfg.leverage
            position_usd = min(base_position * vol_scalar * dd_scalar, max_position)
            return StrategySignal(
                target_position=position_usd, signal="HOLD",
                strategy_name=self.name, metadata=meta)

        if st["side"] == "short":
            stop_z_dist = cfg.mr_stop_z - cfg.mr_entry_z
            stop_dist_pct = stop_z_dist * std / close if close > 0 else 0.1
            if stop_dist_pct <= 0:
                stop_dist_pct = 0.01
            risk_usd = equity * cfg.risk_per_trade
            base_position = (risk_usd / stop_dist_pct) * cfg.leverage
            max_position = equity * cfg.leverage
            position_usd = min(base_position * vol_scalar * dd_scalar, max_position)
            return StrategySignal(
                target_position=-position_usd, signal="HOLD",
                strategy_name=self.name, metadata=meta)

        return StrategySignal(signal="HOLD", strategy_name=self.name, metadata=meta)
