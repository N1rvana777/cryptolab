"""Multi-Timeframe Donchian strategy: breakout + trailing stop + MTF-sized positions.

Uses the medium lookback as the primary entry/exit signal (like DonchianBreakout),
but sizes positions by how many timeframes agree, with vol-targeting and drawdown scaling.
"""

import math
from typing import Dict

import pandas as pd

from cryptolab.config import Config
from cryptolab.strategy.base import BaseStrategy, StrategySignal
from cryptolab.indicators.donchian import compute_donchian
from cryptolab.indicators.core import compute_atr, compute_tsmom
from cryptolab.backtest.metrics import PERIODS_PER_YEAR


class DonchianMTF(BaseStrategy):
    """Donchian breakout with multi-timeframe agreement sizing and dynamic risk scaling.

    Entry: medium-TF Donchian breakout (same as DonchianBreakout).
    Sizing: position scaled by how many TFs agree (0-100%), vol target, and drawdown.
    Exit: ATR trailing stop or opposite breakout on medium TF.
    """

    def __init__(self, cfg: Config):
        super().__init__(cfg, name="DonchianMTF")
        self._state: Dict[str, dict] = {}

    def _get_state(self, symbol: str) -> dict:
        if symbol not in self._state:
            self._state[symbol] = {
                "side": None,
                "entry_px": None,
                "trail_stop": None,
                "base_pos": None,  # total position USD (accumulates with pyramiding)
                "peak_equity": None,
                "tf_trends": [0.0] * len(self.cfg.mtf_lookbacks),
                "n_units": 0,         # number of pyramid units (0 when flat)
                "last_add_px": None,   # price of last entry/add
                "unit_size": None,     # size of one unit at entry
            }
        return self._state[symbol]

    def reset(self, symbol: str):
        self._state.pop(symbol, None)

    @staticmethod
    def _clear_position(st: dict):
        st["side"] = None
        st["entry_px"] = None
        st["trail_stop"] = None
        st["base_pos"] = None
        st["n_units"] = 0
        st["last_add_px"] = None
        st["unit_size"] = None

    def _compute_tf_agreement(self, highs, lows, close, st):
        """Compute per-TF breakout states and combined agreement score."""
        cfg = self.cfg
        tf_signals = list(st["tf_trends"])
        tf_meta = {}

        for i, lb in enumerate(cfg.mtf_lookbacks):
            dc = compute_donchian(highs[:-1], lows[:-1], lb)
            if dc is None:
                continue
            if close > dc["upper"]:
                tf_signals[i] = 1.0
            elif close < dc["lower"]:
                tf_signals[i] = -1.0
            tf_meta[f"tf{i}_lb{lb}"] = tf_signals[i]
            tf_meta[f"tf{i}_upper"] = dc["upper"]
            tf_meta[f"tf{i}_lower"] = dc["lower"]

        st["tf_trends"] = tf_signals
        combined = sum(w * s for w, s in zip(cfg.mtf_weights, tf_signals))
        return combined, tf_meta

    def _compute_scalars(self, close, atr, equity, st):
        """Compute vol_scalar and dd_scalar for position sizing."""
        cfg = self.cfg

        # Vol targeting
        ppy = PERIODS_PER_YEAR.get(cfg.interval, 2190)
        atr_pct = atr / close
        ann_vol = atr_pct * math.sqrt(ppy)
        lo, hi = cfg.mtf_vol_scalar_bounds
        vol_scalar = max(lo, min(hi, cfg.mtf_vol_target / ann_vol)) if ann_vol > 0 else 1.0

        # Drawdown scaling
        if st["peak_equity"] is None:
            st["peak_equity"] = equity
        else:
            st["peak_equity"] = max(st["peak_equity"], equity)

        current_dd = (st["peak_equity"] - equity) / st["peak_equity"] if st["peak_equity"] > 0 else 0.0
        if current_dd >= cfg.mtf_dd_max:
            dd_scalar = cfg.mtf_dd_floor
        elif cfg.mtf_dd_max > 0:
            dd_scalar = 1.0 - (1.0 - cfg.mtf_dd_floor) * (current_dd / cfg.mtf_dd_max)
        else:
            dd_scalar = 1.0

        return vol_scalar, dd_scalar, ann_vol, current_dd

    def generate_signal(self, symbol: str, df: pd.DataFrame, equity: float, **kwargs) -> StrategySignal:
        cfg = self.cfg
        st = self._get_state(symbol)

        min_bars = max(max(cfg.mtf_lookbacks), cfg.atr_period + 1)
        if len(df) < min_bars:
            return StrategySignal(signal="HOLD", strategy_name=self.name)

        highs = df["high"].tolist()
        lows = df["low"].tolist()
        closes = df["close"].tolist()
        close = closes[-1]
        candles = [
            {"h": row["high"], "l": row["low"], "c": row["close"], "v": row["volume"]}
            for _, row in df.iterrows()
        ]

        # Medium TF Donchian (primary signal, same as DonchianBreakout)
        med_lb = cfg.mtf_lookbacks[1] if len(cfg.mtf_lookbacks) > 1 else cfg.mtf_lookbacks[0]
        dc_med = compute_donchian(highs[:-1], lows[:-1], med_lb)
        atr = compute_atr(candles, cfg.atr_period)

        if dc_med is None or atr is None or atr <= 0 or close <= 0:
            return StrategySignal(signal="HOLD", strategy_name=self.name)

        upper = dc_med["upper"]
        lower = dc_med["lower"]
        stop_dist = atr * cfg.atr_sl_mult

        # MTF agreement score
        combined, tf_meta = self._compute_tf_agreement(highs, lows, close, st)

        # Dynamic scalars
        vol_scalar, dd_scalar, ann_vol, current_dd = self._compute_scalars(close, atr, equity, st)

        # Momentum score
        mom_score = compute_tsmom(closes, cfg.mom_lookback) if cfg.mom_weight > 0 else 0.0
        if mom_score is None:
            mom_score = 0.0

        # Blend breakout + momentum
        final_combined = (1 - cfg.mom_weight) * combined + cfg.mom_weight * mom_score

        meta = {
            "dc_upper": upper, "dc_lower": lower, "atr": atr,
            "trail_stop": st["trail_stop"],
            "combined": combined,
            "mom_score": mom_score, "final_combined": final_combined,
            "vol_scalar": vol_scalar, "dd_scalar": dd_scalar,
            "current_dd_pct": current_dd * 100, "ann_vol": ann_vol,
            **tf_meta,
        }

        # --- EXIT LOGIC (if in position) ---
        if st["side"] == "long":
            new_stop = close - stop_dist
            if st["trail_stop"] is not None:
                st["trail_stop"] = max(st["trail_stop"], new_stop)
            else:
                st["trail_stop"] = new_stop

            trail = st["trail_stop"]
            if close <= trail or close < lower:
                exit_reason = "trail_stop" if close <= trail else "opposite_breakout"
                self._clear_position(st)
                meta["exit_reason"] = exit_reason
                meta["trail_stop"] = trail
                return StrategySignal(
                    target_position=0.0, signal="CLOSE",
                    strategy_name=self.name, metadata=meta,
                )

        elif st["side"] == "short":
            new_stop = close + stop_dist
            if st["trail_stop"] is not None:
                st["trail_stop"] = min(st["trail_stop"], new_stop)
            else:
                st["trail_stop"] = new_stop

            trail = st["trail_stop"]
            if close >= trail or close > upper:
                exit_reason = "trail_stop" if close >= trail else "opposite_breakout"
                self._clear_position(st)
                meta["exit_reason"] = exit_reason
                meta["trail_stop"] = trail
                return StrategySignal(
                    target_position=0.0, signal="CLOSE",
                    strategy_name=self.name, metadata=meta,
                )

        # --- ENTRY LOGIC (if flat) ---
        if st["side"] is None:
            risk_usd = equity * cfg.risk_per_trade
            stop_dist_pct = stop_dist / close
            if stop_dist_pct <= 0:
                return StrategySignal(signal="HOLD", strategy_name=self.name, metadata=meta)

            base_position = (risk_usd / stop_dist_pct) * cfg.leverage
            max_position = equity * cfg.leverage

            # Use blended score for agreement/sizing
            agreement = abs(final_combined)
            if agreement < cfg.mtf_signal_deadzone:
                agreement = 0.0

            position_usd = base_position * agreement * vol_scalar * dd_scalar
            position_usd = min(position_usd, max_position)

            # Entry triggers: breakout OR strong momentum
            breakout_long = close > upper
            breakout_short = close < lower
            mom_long = cfg.mom_weight > 0 and mom_score > cfg.mom_entry_threshold
            mom_short = cfg.mom_weight > 0 and mom_score < -cfg.mom_entry_threshold

            if (breakout_long or mom_long) and final_combined > 0 and position_usd > 0:
                st["side"] = "long"
                st["entry_px"] = close
                st["trail_stop"] = close - stop_dist
                st["base_pos"] = position_usd
                st["n_units"] = 1
                st["last_add_px"] = close
                st["unit_size"] = position_usd
                meta["trail_stop"] = st["trail_stop"]
                meta["n_units"] = 1
                meta["entry_type"] = "momentum" if mom_long and not breakout_long else "breakout"
                return StrategySignal(
                    target_position=position_usd, signal="LONG",
                    confidence=agreement,
                    suggested_stop_px=st["trail_stop"],
                    strategy_name=self.name, metadata=meta,
                )

            if (breakout_short or mom_short) and final_combined < 0 and position_usd > 0:
                st["side"] = "short"
                st["entry_px"] = close
                st["trail_stop"] = close + stop_dist
                st["base_pos"] = -position_usd
                st["n_units"] = 1
                st["last_add_px"] = close
                st["unit_size"] = position_usd
                meta["trail_stop"] = st["trail_stop"]
                meta["n_units"] = 1
                meta["entry_type"] = "momentum" if mom_short and not breakout_short else "breakout"
                return StrategySignal(
                    target_position=-position_usd, signal="SHORT",
                    confidence=agreement,
                    suggested_stop_px=st["trail_stop"],
                    strategy_name=self.name, metadata=meta,
                )

        # --- HOLD with pyramiding ---
        if st["side"] in ("long", "short"):
            meta["trail_stop"] = st["trail_stop"]
            meta["n_units"] = st["n_units"]

            # Check for pyramid add
            max_units = cfg.mtf_pyramid_max_units
            spacing = cfg.mtf_pyramid_spacing_atr
            if st["n_units"] < max_units and st["last_add_px"] is not None and atr > 0:
                max_position = equity * cfg.leverage

                if st["side"] == "long":
                    add_threshold = st["last_add_px"] + atr * spacing
                    if close > add_threshold:
                        # Compute add unit using current scalars
                        add_unit = self._compute_add_unit(
                            equity, close, atr, stop_dist, final_combined, vol_scalar, dd_scalar)
                        new_pos = st["base_pos"] + add_unit
                        if new_pos <= max_position:
                            st["n_units"] += 1
                            st["last_add_px"] = close
                            st["base_pos"] = new_pos
                            # Tighten stop for all units
                            st["trail_stop"] = close - stop_dist
                            meta["trail_stop"] = st["trail_stop"]
                            meta["n_units"] = st["n_units"]
                            meta["pyramid_add"] = True
                            return StrategySignal(
                                target_position=st["base_pos"], signal="HOLD",
                                suggested_stop_px=st["trail_stop"],
                                strategy_name=self.name, metadata=meta,
                            )

                elif st["side"] == "short":
                    add_threshold = st["last_add_px"] - atr * spacing
                    if close < add_threshold:
                        add_unit = self._compute_add_unit(
                            equity, close, atr, stop_dist, final_combined, vol_scalar, dd_scalar)
                        new_pos = st["base_pos"] - add_unit
                        if abs(new_pos) <= max_position:
                            st["n_units"] += 1
                            st["last_add_px"] = close
                            st["base_pos"] = new_pos
                            st["trail_stop"] = close + stop_dist
                            meta["trail_stop"] = st["trail_stop"]
                            meta["n_units"] = st["n_units"]
                            meta["pyramid_add"] = True
                            return StrategySignal(
                                target_position=st["base_pos"], signal="HOLD",
                                suggested_stop_px=st["trail_stop"],
                                strategy_name=self.name, metadata=meta,
                            )

            return StrategySignal(
                target_position=st["base_pos"], signal="HOLD",
                suggested_stop_px=st["trail_stop"],
                strategy_name=self.name, metadata=meta,
            )

        return StrategySignal(signal="HOLD", strategy_name=self.name, metadata=meta)

    def _compute_add_unit(self, equity, close, atr, stop_dist, combined, vol_scalar, dd_scalar):
        """Compute USD size of one pyramid add unit."""
        cfg = self.cfg
        risk_usd = equity * cfg.risk_per_trade
        stop_dist_pct = stop_dist / close
        if stop_dist_pct <= 0:
            return 0.0
        base = (risk_usd / stop_dist_pct) * cfg.leverage
        agreement = abs(combined)
        if agreement < cfg.mtf_signal_deadzone:
            agreement = 0.0
        return base * agreement * vol_scalar * dd_scalar
