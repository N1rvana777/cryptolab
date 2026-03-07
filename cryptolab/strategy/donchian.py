"""Donchian Breakout strategy — trend-following with ATR trailing stops."""

from typing import Dict, Optional

import pandas as pd

from cryptolab.config import Config
from cryptolab.strategy.base import BaseStrategy, StrategySignal
from cryptolab.indicators.donchian import compute_donchian
from cryptolab.indicators.core import compute_atr


class DonchianBreakout(BaseStrategy):
    """Enter on Donchian channel breakouts, exit on ATR trailing stop or opposite breakout."""

    def __init__(self, cfg: Config):
        super().__init__(cfg, name="DonchianBreakout")
        self._state: Dict[str, dict] = {}

    def _get_state(self, symbol: str) -> dict:
        if symbol not in self._state:
            self._state[symbol] = {"side": None, "entry_px": None, "trail_stop": None, "target_pos": None}
        return self._state[symbol]

    def reset(self, symbol: str):
        self._state.pop(symbol, None)

    def generate_signal(self, symbol: str, df: pd.DataFrame, equity: float, **kwargs) -> StrategySignal:
        cfg = self.cfg
        st = self._get_state(symbol)

        # Need enough bars for both donchian and ATR
        min_bars = max(cfg.donchian_period, cfg.atr_period + 1)
        if len(df) < min_bars:
            return StrategySignal(signal="HOLD", strategy_name=self.name)

        # Convert DataFrame to indicator inputs
        # Donchian on prior bars only (exclude current) to avoid look-ahead
        highs = df["high"].tolist()
        lows = df["low"].tolist()
        candles = [
            {"h": row["high"], "l": row["low"], "c": row["close"], "v": row["volume"]}
            for _, row in df.iterrows()
        ]

        dc = compute_donchian(highs[:-1], lows[:-1], cfg.donchian_period)
        atr = compute_atr(candles, cfg.atr_period)

        if dc is None or atr is None or atr <= 0:
            return StrategySignal(signal="HOLD", strategy_name=self.name)

        close = df.iloc[-1]["close"]
        upper = dc["upper"]
        lower = dc["lower"]
        stop_dist = atr * cfg.atr_sl_mult

        meta = {
            "dc_upper": upper,
            "dc_lower": lower,
            "atr": atr,
            "trail_stop": st["trail_stop"],
        }

        # --- Check exits if in position ---
        if st["side"] == "long":
            # Ratchet trailing stop up
            new_stop = close - stop_dist
            if st["trail_stop"] is not None:
                st["trail_stop"] = max(st["trail_stop"], new_stop)
            else:
                st["trail_stop"] = new_stop

            # Exit: trailing stop hit or opposite breakout
            trail = st["trail_stop"]
            if close <= trail or close < lower:
                exit_reason = "trail_stop" if close <= trail else "opposite_breakout"
                st["side"] = None
                st["entry_px"] = None
                st["trail_stop"] = None
                st["target_pos"] = None
                meta["exit_reason"] = exit_reason
                return StrategySignal(
                    target_position=0.0,
                    signal="CLOSE",
                    strategy_name=self.name,
                    metadata=meta,
                )

        elif st["side"] == "short":
            # Ratchet trailing stop down
            new_stop = close + stop_dist
            if st["trail_stop"] is not None:
                st["trail_stop"] = min(st["trail_stop"], new_stop)
            else:
                st["trail_stop"] = new_stop

            # Exit: trailing stop hit or opposite breakout
            trail = st["trail_stop"]
            if close >= trail or close > upper:
                exit_reason = "trail_stop" if close >= trail else "opposite_breakout"
                st["side"] = None
                st["entry_px"] = None
                st["trail_stop"] = None
                st["target_pos"] = None
                meta["exit_reason"] = exit_reason
                return StrategySignal(
                    target_position=0.0,
                    signal="CLOSE",
                    strategy_name=self.name,
                    metadata=meta,
                )

        # --- Check entries if flat ---
        if st["side"] is None:
            risk_usd = equity * cfg.risk_per_trade
            stop_dist_pct = stop_dist / close
            if stop_dist_pct <= 0:
                return StrategySignal(signal="HOLD", strategy_name=self.name, metadata=meta)

            position_usd = (risk_usd / stop_dist_pct) * cfg.leverage
            max_position = equity * cfg.leverage
            position_usd = min(position_usd, max_position)

            if close > upper:
                # Long breakout
                st["side"] = "long"
                st["entry_px"] = close
                st["trail_stop"] = close - stop_dist
                st["target_pos"] = position_usd
                meta["trail_stop"] = st["trail_stop"]
                return StrategySignal(
                    target_position=position_usd,
                    signal="LONG",
                    suggested_stop_px=st["trail_stop"],
                    strategy_name=self.name,
                    metadata=meta,
                )

            if close < lower:
                # Short breakout
                st["side"] = "short"
                st["entry_px"] = close
                st["trail_stop"] = close + stop_dist
                st["target_pos"] = -position_usd
                meta["trail_stop"] = st["trail_stop"]
                return StrategySignal(
                    target_position=-position_usd,
                    signal="SHORT",
                    suggested_stop_px=st["trail_stop"],
                    strategy_name=self.name,
                    metadata=meta,
                )

        # --- Hold current position (locked size from entry) ---
        if st["side"] in ("long", "short"):
            meta["trail_stop"] = st["trail_stop"]
            return StrategySignal(
                target_position=st["target_pos"],
                signal="HOLD",
                suggested_stop_px=st["trail_stop"],
                strategy_name=self.name,
                metadata=meta,
            )

        # Flat, no breakout
        return StrategySignal(signal="HOLD", strategy_name=self.name, metadata=meta)
