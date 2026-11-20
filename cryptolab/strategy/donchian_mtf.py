"""Multi-Timeframe Donchian strategy: breakout + trailing stop + MTF-sized positions.

Uses the medium lookback as the primary entry/exit signal (like DonchianBreakout),
but sizes positions by how many timeframes agree, with vol-targeting and drawdown scaling.
"""

import math
from typing import Dict

import numpy as np
import pandas as pd

from cryptolab.config import Config
from cryptolab.strategy.base import BaseStrategy, StrategySignal
from cryptolab.indicators.donchian import compute_donchian
from cryptolab.indicators.core import compute_atr, compute_tsmom, compute_volume_ratio, compute_rsi
from cryptolab.backtest.metrics import PERIODS_PER_YEAR


def _compute_adx(highs, lows, closes, period=20):
    """Compute ADX for regime detection. Returns (adx_value, dx_series)."""
    n = len(highs)
    if n < period * 2 + 1:
        return None

    tr = [0.0] * n
    plus_dm = [0.0] * n
    minus_dm = [0.0] * n
    for i in range(1, n):
        h_diff = highs[i] - highs[i - 1]
        l_diff = lows[i - 1] - lows[i]
        tr[i] = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        plus_dm[i] = h_diff if (h_diff > l_diff and h_diff > 0) else 0
        minus_dm[i] = l_diff if (l_diff > h_diff and l_diff > 0) else 0

    # Wilder smoothing
    atr_s = sum(tr[1:period + 1])
    pdm_s = sum(plus_dm[1:period + 1])
    mdm_s = sum(minus_dm[1:period + 1])
    for i in range(period + 1, n):
        atr_s = atr_s - atr_s / period + tr[i]
        pdm_s = pdm_s - pdm_s / period + plus_dm[i]
        mdm_s = mdm_s - mdm_s / period + minus_dm[i]

    # Final DX and ADX
    dx_vals = []
    cur_atr = sum(tr[1:period + 1])
    cur_pdm = sum(plus_dm[1:period + 1])
    cur_mdm = sum(minus_dm[1:period + 1])
    for i in range(period + 1, n):
        cur_atr = cur_atr - cur_atr / period + tr[i]
        cur_pdm = cur_pdm - cur_pdm / period + plus_dm[i]
        cur_mdm = cur_mdm - cur_mdm / period + minus_dm[i]
        if cur_atr > 0:
            pdi = 100 * cur_pdm / cur_atr
            mdi = 100 * cur_mdm / cur_atr
            if pdi + mdi > 0:
                dx_vals.append(100 * abs(pdi - mdi) / (pdi + mdi))
            else:
                dx_vals.append(0)
        else:
            dx_vals.append(0)

    if len(dx_vals) < period:
        return None

    adx = sum(dx_vals[:period]) / period
    for dx in dx_vals[period:]:
        adx = (adx * (period - 1) + dx) / period

    return adx


def _compute_regime_scale(highs, lows, closes, adx_period=20):
    """Compute regime_scale for the latest bar.

    Returns (regime_scale, adx_value, vol_10d, vol_30d).
    regime_scale: 1.0 (trending), 0.5 (gray zone), 0.0 (choppy)
    """
    # ADX
    adx_val = _compute_adx(highs, lows, closes, adx_period)
    if adx_val is None:
        return 1.0, None, None, None

    # ADX thresholds
    if adx_val >= 25:
        regime_scale = 1.0
    elif adx_val >= 20:
        regime_scale = 0.5
    else:
        regime_scale = 0.0

    # Vol contraction (OR with ADX — can only lower regime_scale)
    n = len(closes)
    if n >= 90:
        rets = [closes[i] / closes[i - 1] - 1 for i in range(max(1, n - 90), n)]
        vol_30d = float(np.std(rets)) if len(rets) >= 90 else None
        vol_10d = float(np.std(rets[-30:])) if len(rets) >= 30 else None

        if vol_10d is not None and vol_30d is not None and vol_30d > 0:
            if vol_10d < vol_30d * 0.7:
                regime_scale = 0.0
    else:
        vol_10d = None
        vol_30d = None

    return regime_scale, adx_val, vol_10d, vol_30d


class DonchianMTF(BaseStrategy):
    """多时间框架Donchian突破策略（v1规则型策略，也是v2 ML模型的对比基准）。

    入场: 中等TF（默认72bar）的Donchian通道突破——收盘价突破N bar最高/最低价
    仓位大小 = 基础仓位 × MTF共识 × 波动率定标 × 回撤缩放
      - MTF共识: 3个TF(24/72/168)中有多少个同方向（0~100%）
      - 波动率定标: 目标年化波动率(15%) / 实际年化波动率，限制在0.5~2.0x
      - 回撤缩放: 回撤越大仓位越小，最多缩到floor(25%)
    出场: ATR追踪止损 或 反方向Donchian突破
    可选: 金字塔加仓（默认关闭）、动量混合（默认关闭）
    """

    def __init__(self, cfg: Config):
        super().__init__(cfg, name="DonchianMTF")
        self._state: Dict[str, dict] = {}
        self._cs_lookup: dict = {}  # {timestamp: multiplier} for cross-sectional signal

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
        """计算各TF的突破状态，返回加权共识分数。

        对每个lookback(24/72/168)检查收盘价是否突破通道上/下沿。
        突破上沿=+1(看多)，突破下沿=-1(看空)，通道内=保持上次状态。
        返回: (combined_score, metadata_dict)
        combined_score范围[-1,1]，绝对值越大=越多TF同方向。
        """
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
        """计算波动率定标和回撤缩放系数。

        vol_scalar: 目标年化波动率 / 实际年化波动率（限制在0.5~2.0x）
        dd_scalar: 当前回撤越深，仓位越小。回撤=0时为1.0，回撤=dd_max时为dd_floor
        """
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
        """生成交易信号（核心策略逻辑）。

        输入: 币种、截至当前bar的OHLCV历史、当前权益
        输出: StrategySignal（目标仓位、信号类型、止损价、元数据）

        逻辑顺序: 检查出场条件(持仓时) -> 检查入场条件(空仓时) -> 检查加仓条件(持仓时)
        """
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
            {"h": h, "l": l, "c": c, "v": v}
            for h, l, c, v in zip(
                df["high"].values, df["low"].values,
                df["close"].values, df["volume"].values,
            )
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

        # Volume-weighted momentum: amplify/dampen agreement by volume ratio
        if cfg.vw_weight > 0:
            vol_ratio = compute_volume_ratio(candles, cfg.vw_lookback)
            vol_factor = max(0.5, min(2.0, 1.0 + cfg.vw_weight * (vol_ratio - 1.0)))
            combined = combined * vol_factor
        else:
            vol_ratio = None
            vol_factor = None

        # Dynamic scalars
        vol_scalar, dd_scalar, ann_vol, current_dd = self._compute_scalars(close, atr, equity, st)

        # Regime filter (B0: ADX + vol contraction)
        regime_scale = 1.0
        adx_val = None
        vol_10d = None
        vol_30d = None
        if cfg.mtf_regime_filter:
            regime_scale, adx_val, vol_10d, vol_30d = _compute_regime_scale(
                highs, lows, closes, cfg.mtf_adx_period
            )

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
            "regime_scale": regime_scale, "adx": adx_val,
            "vol_10d": vol_10d, "vol_30d": vol_30d,
            **tf_meta,
        }
        if vol_ratio is not None:
            meta["vol_ratio"] = vol_ratio
            meta["vol_factor"] = vol_factor

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

            position_usd = base_position * agreement * vol_scalar * dd_scalar * regime_scale
            position_usd = min(position_usd, max_position)

            # Mean-reversion RSI filter: penalize entries at extreme RSI
            if cfg.mr_weight > 0:
                rsi = compute_rsi(closes, cfg.mr_rsi_period)
                if rsi is not None:
                    if final_combined > 0:  # long — penalize overbought
                        penalty = 1.0 - cfg.mr_weight * max(0.0, (rsi - 60.0) / 40.0)
                    elif final_combined < 0:  # short — penalize oversold
                        penalty = 1.0 - cfg.mr_weight * max(0.0, (30.0 - rsi) / 30.0)
                    else:
                        penalty = 1.0
                    penalty = max(0.0, penalty)
                    position_usd *= penalty
                    meta["rsi"] = rsi
                    meta["mr_penalty"] = penalty

            # Cross-sectional momentum: scale by relative strength rank
            if cfg.cs_weight > 0 and self._cs_lookup:
                ts = df.iloc[-1].get("timestamp") if "timestamp" in df.columns else df.index[-1]
                cs_mult = self._cs_lookup.get(ts, 1.0)
                position_usd *= cs_mult
                meta["cs_multiplier"] = cs_mult

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
