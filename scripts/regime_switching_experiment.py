#!/usr/bin/env python3
"""Plan D experiment: Regime-based dynamic switching between Donchian + MeanRev.

Compares 4 portfolio approaches on Holdout (2025.07 - 2026.03):
A) Pure Donchian B0
B) Pure Mean Reversion (per-coin best params)
C) 50/50 Equal Weight (no regime awareness)
D) Regime Dynamic Switching (ADX > 25 -> Donchian, ADX < 20 -> MeanRev, 20-25 -> 50/50)
"""

import sys, os, time, json
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptolab.data.cache import ParquetCache
from cryptolab.backtest.metrics import sharpe_ratio, max_drawdown, PERIODS_PER_YEAR
from scripts.donchian_full_sweep import resample_ohlcv
from scripts.mean_reversion_experiment import (
    compute_adx, compute_dynamic_slippage, load_8h_data,
    COINS, PPY_8H, FEE_BPS, K1, K2_BPS, AUTO_THRESH,
)

# Load best MeanRev params from previous experiment
MEANREV_PARAMS_PATH = Path("sweep_results/meanrev_experiment.json")


def run_regime_switch(df, mr_lookback, mr_entry_z, mr_exit_z, mr_stop_z,
                      capital, n_coins):
    """Run regime-switching portfolio: Donchian when trending, MeanRev when ranging.

    Per-bar decision:
    - ADX > 25: only Donchian signals active
    - ADX < 20: only MeanRev signals active
    - ADX 20-25: both at 50% size

    Returns dict with metrics + equity array.
    """
    n = len(df)
    don_lbs = (36, 60, 336)  # B0 lookbacks
    max_lb = max(don_lbs)
    warmup = max(max_lb + 60, mr_lookback + 60, 100)
    if n < warmup + 20:
        return None

    highs = df["high"].values; lows = df["low"].values
    closes = df["close"].values; opens = df["open"].values
    volumes = df["volume"].values
    h_s = pd.Series(highs); l_s = pd.Series(lows)

    # Precompute Donchian channels
    channels = {}
    for lb in don_lbs:
        channels[lb] = {
            "upper": h_s.rolling(lb).max().shift(1).values,
            "lower": l_s.rolling(lb).min().shift(1).values,
        }

    # ADX
    adx = compute_adx(highs, lows, closes, 20)

    # Returns and vol
    ret = np.zeros(n); ret[1:] = closes[1:]/closes[:-1] - 1
    ret_s = pd.Series(ret)
    vol_10d = ret_s.rolling(30, min_periods=10).std().values
    vol_30d = ret_s.rolling(90, min_periods=30).std().values

    # ATR
    atr_p = 14
    tr_arr = np.maximum(highs[1:]-lows[1:],
                        np.maximum(np.abs(highs[1:]-closes[:-1]),
                                   np.abs(lows[1:]-closes[:-1])))
    tr_arr = np.insert(tr_arr, 0, highs[0]-lows[0])
    atr = np.full(n, np.nan)
    atr[atr_p] = np.mean(tr_arr[:atr_p])
    for i in range(atr_p+1, n):
        atr[i] = atr[i-1]*(atr_p-1)/atr_p + tr_arr[i]/atr_p

    # Z-score for mean reversion
    sma = pd.Series(closes).rolling(mr_lookback, min_periods=mr_lookback).mean().values
    std = pd.Series(closes).rolling(mr_lookback, min_periods=mr_lookback).std(ddof=1).values
    z_score = np.where(std > 1e-10, (closes - sma) / std, 0.0)

    # ADV
    vol_usd = volumes * closes
    adv = pd.Series(vol_usd).rolling(60, min_periods=3).sum().values / 20

    fee_rate = FEE_BPS / 10_000
    equity = capital; cash = equity; pos = 0.0; entry_px = 0.0
    peak = equity; equities = np.full(n, equity)
    n_trades = 0; wins = 0; closed = 0; prev_target = 0.0

    # Strategy states
    don_side = None   # "long", "short", None
    mr_side = None
    active_strategy = None  # "don", "mr", "both"

    start = warmup

    for i in range(start, n):
        o = opens[i]; c = closes[i]; z = z_score[i]

        # Execute previous signal
        trade_size = abs(prev_target - pos)
        if trade_size > max(5.0, abs(prev_target) * 0.03):
            fee = trade_size * fee_rate
            slip = compute_dynamic_slippage(trade_size, adv[i])
            if abs(pos) > 0.01 and entry_px > 0:
                pnl = abs(pos) * ((o-entry_px)/entry_px if pos > 0 else (entry_px-o)/entry_px)
                cash += pnl
                if pnl > 0: wins += 1
                closed += 1
            cash -= fee + slip; n_trades += 1
            pos = prev_target
            entry_px = o if abs(pos) > 0.01 else 0.0

        unrealized = 0.0
        if abs(pos) > 0.01 and entry_px > 0:
            unrealized = abs(pos) * ((c-entry_px)/entry_px if pos > 0 else (entry_px-c)/entry_px)
        equity = cash + unrealized; peak = max(peak, equity); equities[i] = equity

        # --- REGIME DETECTION ---
        adx_val = adx[i] if not np.isnan(adx[i]) else 25.0
        v10 = vol_10d[i]; v30 = vol_30d[i]
        vol_contraction = (not np.isnan(v10) and not np.isnan(v30) and v30 > 0
                           and v10 < v30 * 0.7)

        if adx_val >= 25:
            don_scale = 1.0; mr_scale = 0.0
        elif adx_val < 20:
            don_scale = 0.0; mr_scale = 1.0
        else:
            don_scale = 0.5; mr_scale = 0.5

        # Vol contraction blocks both
        if vol_contraction:
            don_scale = 0.0; mr_scale = 0.0

        # --- DONCHIAN SIGNAL ---
        don_target = 0.0
        if don_scale > 0:
            wts = [0.25, 0.50, 0.25]
            dirs = []
            for lb in don_lbs:
                u = channels[lb]["upper"][i]; l = channels[lb]["lower"][i]
                if np.isnan(u) or np.isnan(l): dirs.append(0.0)
                elif c > u: dirs.append(1.0)
                elif c < l: dirs.append(-1.0)
                else: dirs.append(0.0)
            agreement = sum(w*d for w, d in zip(wts, dirs))

            # Exit check for Donchian
            if don_side == "long" and (agreement < -0.05 or c < channels[don_lbs[1]]["lower"][i]):
                don_side = None
            elif don_side == "short" and (agreement > 0.05 or c > channels[don_lbs[1]]["upper"][i]):
                don_side = None

            if don_side is None and abs(agreement) >= 0.05:
                # Entry
                direction = 1.0 if agreement > 0 else -1.0
                if not np.isnan(atr[i]) and atr[i] > 0 and c > 0:
                    ann_vol = (atr[i]/c) * np.sqrt(PPY_8H)
                    vol_sc = max(0.5, min(2.0, 0.15/ann_vol if ann_vol > 0 else 1.0))
                else:
                    vol_sc = 1.0
                dd = max(0, 1.0 - equity/peak)
                dd_sc = 1.0 - min(dd/0.30, 1.0)*0.75 if dd > 0 else 1.0
                base = equity * 3.0 * abs(agreement) * don_scale
                don_target = direction * min(base * vol_sc * dd_sc, equity * 3.0 * don_scale)
                don_side = "long" if direction > 0 else "short"

            elif don_side == "long":
                # Hold position (rescale by don_scale)
                if not np.isnan(atr[i]) and atr[i] > 0:
                    ann_vol = (atr[i]/c) * np.sqrt(PPY_8H)
                    vol_sc = max(0.5, min(2.0, 0.15/ann_vol if ann_vol > 0 else 1.0))
                else:
                    vol_sc = 1.0
                dd = max(0, 1.0 - equity/peak)
                dd_sc = 1.0 - min(dd/0.30, 1.0)*0.75 if dd > 0 else 1.0
                don_target = min(equity * 3.0 * vol_sc * dd_sc * don_scale, equity * 3.0 * don_scale)

            elif don_side == "short":
                if not np.isnan(atr[i]) and atr[i] > 0:
                    ann_vol = (atr[i]/c) * np.sqrt(PPY_8H)
                    vol_sc = max(0.5, min(2.0, 0.15/ann_vol if ann_vol > 0 else 1.0))
                else:
                    vol_sc = 1.0
                dd = max(0, 1.0 - equity/peak)
                dd_sc = 1.0 - min(dd/0.30, 1.0)*0.75 if dd > 0 else 1.0
                don_target = -min(equity * 3.0 * vol_sc * dd_sc * don_scale, equity * 3.0 * don_scale)

        else:
            # Donchian not active in this regime -> close any open position
            if don_side is not None:
                don_side = None

        # --- MEAN REVERSION SIGNAL ---
        mr_target = 0.0
        if mr_scale > 0 and not np.isnan(z) and not np.isnan(sma[i]):
            # Exit check
            if mr_side == "long":
                if z >= -mr_exit_z or z < -mr_stop_z:
                    mr_side = None
            elif mr_side == "short":
                if z <= mr_exit_z or z > mr_stop_z:
                    mr_side = None

            if mr_side is None:
                # Entry
                stop_z_dist = mr_stop_z - mr_entry_z
                s = std[i] if not np.isnan(std[i]) and std[i] > 0 else c * 0.02
                stop_dist_pct = max(stop_z_dist * s / c, 0.001) if c > 0 else 0.01
                risk_usd = equity * 0.02
                base_pos = (risk_usd / stop_dist_pct) * 3.0 * mr_scale
                max_pos = equity * 3.0 * mr_scale

                if not np.isnan(std[i]) and std[i] > 0 and c > 0:
                    ann_vol_approx = (std[i] / c) * np.sqrt(PPY_8H)
                    vol_sc = max(0.5, min(2.0, 0.15 / ann_vol_approx)) if ann_vol_approx > 0 else 1.0
                else:
                    vol_sc = 1.0
                dd = max(0, 1.0 - equity/peak)
                dd_sc = 1.0 - min(dd/0.30, 1.0)*0.75 if dd > 0 else 1.0
                position = min(base_pos * vol_sc * dd_sc, max_pos)

                if z < -mr_entry_z and position > 0:
                    mr_target = position; mr_side = "long"
                elif z > mr_entry_z and position > 0:
                    mr_target = -position; mr_side = "short"

            elif mr_side == "long":
                stop_z_dist = mr_stop_z - mr_entry_z
                s = std[i] if not np.isnan(std[i]) and std[i] > 0 else c * 0.02
                stop_dist_pct = max(stop_z_dist * s / c, 0.001) if c > 0 else 0.01
                risk_usd = equity * 0.02
                base_pos = (risk_usd / stop_dist_pct) * 3.0 * mr_scale
                max_pos = equity * 3.0 * mr_scale
                if not np.isnan(std[i]) and std[i] > 0 and c > 0:
                    ann_vol_approx = (std[i] / c) * np.sqrt(PPY_8H)
                    vol_sc = max(0.5, min(2.0, 0.15 / ann_vol_approx)) if ann_vol_approx > 0 else 1.0
                else:
                    vol_sc = 1.0
                dd = max(0, 1.0 - equity/peak)
                dd_sc = 1.0 - min(dd/0.30, 1.0)*0.75 if dd > 0 else 1.0
                mr_target = min(base_pos * vol_sc * dd_sc, max_pos)

            elif mr_side == "short":
                stop_z_dist = mr_stop_z - mr_entry_z
                s = std[i] if not np.isnan(std[i]) and std[i] > 0 else c * 0.02
                stop_dist_pct = max(stop_z_dist * s / c, 0.001) if c > 0 else 0.01
                risk_usd = equity * 0.02
                base_pos = (risk_usd / stop_dist_pct) * 3.0 * mr_scale
                max_pos = equity * 3.0 * mr_scale
                if not np.isnan(std[i]) and std[i] > 0 and c > 0:
                    ann_vol_approx = (std[i] / c) * np.sqrt(PPY_8H)
                    vol_sc = max(0.5, min(2.0, 0.15 / ann_vol_approx)) if ann_vol_approx > 0 else 1.0
                else:
                    vol_sc = 1.0
                dd = max(0, 1.0 - equity/peak)
                dd_sc = 1.0 - min(dd/0.30, 1.0)*0.75 if dd > 0 else 1.0
                mr_target = -min(base_pos * vol_sc * dd_sc, max_pos)
        else:
            if mr_side is not None:
                mr_side = None

        # Combined target
        prev_target = don_target + mr_target

    eq = pd.Series(equities[start:])
    if len(eq) < 10:
        return None
    sr = sharpe_ratio(eq, PPY_8H); _, dd_pct = max_drawdown(eq)
    return {
        "sharpe": sr, "return_pct": (float(eq.iloc[-1]) - capital) / capital * 100,
        "max_dd_pct": dd_pct, "n_trades": n_trades,
        "win_rate": wins/closed*100 if closed > 0 else 0,
        "equities": equities[start:].copy(),
    }


def run_regime_switch_hysteresis(df, mr_lookback, mr_entry_z, mr_exit_z, mr_stop_z,
                                 capital, n_coins,
                                 adx_enter_trending=27.0, adx_enter_ranging=18.0,
                                 min_regime_bars=10):
    """Regime switching with hysteresis to prevent whipsaw.

    Hysteresis:
    - trending -> ranging: ADX must drop below adx_enter_ranging (18)
    - ranging -> trending: ADX must rise above adx_enter_trending (27)
    - No gray zone: only trending or ranging
    - Minimum min_regime_bars bars before re-switching
    - On switch: existing positions held until natural exit
    """
    n = len(df)
    don_lbs = (36, 60, 336)
    max_lb = max(don_lbs)
    warmup = max(max_lb + 60, mr_lookback + 60, 100)
    if n < warmup + 20:
        return None

    highs = df["high"].values; lows = df["low"].values
    closes = df["close"].values; opens = df["open"].values
    volumes = df["volume"].values
    h_s = pd.Series(highs); l_s = pd.Series(lows)

    channels = {}
    for lb in don_lbs:
        channels[lb] = {
            "upper": h_s.rolling(lb).max().shift(1).values,
            "lower": l_s.rolling(lb).min().shift(1).values,
        }

    adx = compute_adx(highs, lows, closes, 20)
    ret = np.zeros(n); ret[1:] = closes[1:]/closes[:-1] - 1
    ret_s = pd.Series(ret)
    vol_10d = ret_s.rolling(30, min_periods=10).std().values
    vol_30d = ret_s.rolling(90, min_periods=30).std().values

    atr_p = 14
    tr_arr = np.maximum(highs[1:]-lows[1:],
                        np.maximum(np.abs(highs[1:]-closes[:-1]),
                                   np.abs(lows[1:]-closes[:-1])))
    tr_arr = np.insert(tr_arr, 0, highs[0]-lows[0])
    atr = np.full(n, np.nan)
    atr[atr_p] = np.mean(tr_arr[:atr_p])
    for i in range(atr_p+1, n):
        atr[i] = atr[i-1]*(atr_p-1)/atr_p + tr_arr[i]/atr_p

    sma = pd.Series(closes).rolling(mr_lookback, min_periods=mr_lookback).mean().values
    std = pd.Series(closes).rolling(mr_lookback, min_periods=mr_lookback).std(ddof=1).values
    z_score = np.where(std > 1e-10, (closes - sma) / std, 0.0)

    vol_usd = volumes * closes
    adv = pd.Series(vol_usd).rolling(60, min_periods=3).sum().values / 20

    fee_rate = FEE_BPS / 10_000
    equity = capital; cash = equity; pos = 0.0; entry_px = 0.0
    peak = equity; equities = np.full(n, equity)
    n_trades = 0; wins = 0; closed = 0; prev_target = 0.0

    don_side = None; mr_side = None
    don_held_target = 0.0  # last donchian target when position was opened
    mr_held_target = 0.0   # last mr target when position was opened
    regime = "trending"
    bars_in_regime = 999
    n_switches = 0

    start = warmup

    for i in range(start, n):
        o = opens[i]; c = closes[i]; z = z_score[i]

        # Execute previous signal
        trade_size = abs(prev_target - pos)
        if trade_size > max(5.0, abs(prev_target) * 0.03):
            fee = trade_size * fee_rate
            slip = compute_dynamic_slippage(trade_size, adv[i])
            if abs(pos) > 0.01 and entry_px > 0:
                pnl = abs(pos) * ((o-entry_px)/entry_px if pos > 0 else (entry_px-o)/entry_px)
                cash += pnl
                if pnl > 0: wins += 1
                closed += 1
            cash -= fee + slip; n_trades += 1
            pos = prev_target
            entry_px = o if abs(pos) > 0.01 else 0.0

        unrealized = 0.0
        if abs(pos) > 0.01 and entry_px > 0:
            unrealized = abs(pos) * ((c-entry_px)/entry_px if pos > 0 else (entry_px-c)/entry_px)
        equity = cash + unrealized; peak = max(peak, equity); equities[i] = equity

        # --- REGIME DETECTION WITH HYSTERESIS ---
        adx_val = adx[i] if not np.isnan(adx[i]) else 25.0
        bars_in_regime += 1

        if regime == "trending" and adx_val < adx_enter_ranging and bars_in_regime >= min_regime_bars:
            regime = "ranging"
            bars_in_regime = 0
            n_switches += 1
        elif regime == "ranging" and adx_val > adx_enter_trending and bars_in_regime >= min_regime_bars:
            regime = "trending"
            bars_in_regime = 0
            n_switches += 1

        # Vol contraction blocks all new entries
        v10 = vol_10d[i]; v30 = vol_30d[i]
        vol_contraction = (not np.isnan(v10) and not np.isnan(v30) and v30 > 0
                           and v10 < v30 * 0.7)

        # --- DONCHIAN SIGNAL ---
        don_target = 0.0
        don_can_enter = (regime == "trending" and not vol_contraction)

        # Exit check (always runs regardless of regime)
        if don_side == "long":
            med_lower = channels[don_lbs[1]]["lower"][i]
            if not np.isnan(med_lower) and c < med_lower:
                don_side = None; don_held_target = 0.0
        elif don_side == "short":
            med_upper = channels[don_lbs[1]]["upper"][i]
            if not np.isnan(med_upper) and c > med_upper:
                don_side = None; don_held_target = 0.0

        # New entry only when regime = trending
        if don_side is None and don_can_enter:
            wts = [0.25, 0.50, 0.25]
            dirs = []
            for lb in don_lbs:
                u = channels[lb]["upper"][i]; l = channels[lb]["lower"][i]
                if np.isnan(u) or np.isnan(l): dirs.append(0.0)
                elif c > u: dirs.append(1.0)
                elif c < l: dirs.append(-1.0)
                else: dirs.append(0.0)
            agreement = sum(w*d for w, d in zip(wts, dirs))

            if abs(agreement) >= 0.05:
                direction = 1.0 if agreement > 0 else -1.0
                if not np.isnan(atr[i]) and atr[i] > 0 and c > 0:
                    ann_vol = (atr[i]/c) * np.sqrt(PPY_8H)
                    vol_sc = max(0.5, min(2.0, 0.15/ann_vol if ann_vol > 0 else 1.0))
                else:
                    vol_sc = 1.0
                dd = max(0, 1.0 - equity/peak)
                dd_sc = 1.0 - min(dd/0.30, 1.0)*0.75 if dd > 0 else 1.0
                base = equity * 3.0 * abs(agreement)
                don_target = direction * min(base * vol_sc * dd_sc, equity * 3.0)
                don_side = "long" if direction > 0 else "short"
                don_held_target = don_target

        # Hold existing position: keep last entry target (frozen)
        if don_side is not None and don_target == 0:
            don_target = don_held_target

        # --- MEAN REVERSION SIGNAL ---
        mr_target = 0.0
        mr_can_enter = (regime == "ranging" and not vol_contraction
                        and not np.isnan(z) and not np.isnan(sma[i]))

        # Exit check (always runs regardless of regime)
        if mr_side == "long":
            if not np.isnan(z):
                if z >= -mr_exit_z or z < -mr_stop_z:
                    mr_side = None; mr_held_target = 0.0
        elif mr_side == "short":
            if not np.isnan(z):
                if z <= mr_exit_z or z > mr_stop_z:
                    mr_side = None; mr_held_target = 0.0

        # New entry only when regime = ranging
        if mr_side is None and mr_can_enter:
            stop_z_dist = mr_stop_z - mr_entry_z
            s = std[i] if not np.isnan(std[i]) and std[i] > 0 else c * 0.02
            sdp = max(stop_z_dist * s / c, 0.001) if c > 0 else 0.01
            risk = equity * 0.02
            bp = (risk / sdp) * 3.0
            mp = equity * 3.0
            if not np.isnan(std[i]) and std[i] > 0 and c > 0:
                avol = (std[i] / c) * np.sqrt(PPY_8H)
                vsc = max(0.5, min(2.0, 0.15 / avol)) if avol > 0 else 1.0
            else:
                vsc = 1.0
            dd_ = max(0, 1.0 - equity/peak)
            dsc = 1.0 - min(dd_/0.30, 1.0)*0.75 if dd_ > 0 else 1.0
            position = min(bp * vsc * dsc, mp)

            if z < -mr_entry_z and position > 0:
                mr_target = position; mr_side = "long"
                mr_held_target = mr_target
            elif z > mr_entry_z and position > 0:
                mr_target = -position; mr_side = "short"
                mr_held_target = mr_target

        # Hold existing MR position: keep frozen entry target
        if mr_side is not None and mr_target == 0:
            mr_target = mr_held_target

        prev_target = don_target + mr_target

    eq = pd.Series(equities[start:])
    if len(eq) < 10:
        return None
    sr = sharpe_ratio(eq, PPY_8H); _, dd_pct = max_drawdown(eq)
    return {
        "sharpe": sr, "return_pct": (float(eq.iloc[-1]) - capital) / capital * 100,
        "max_dd_pct": dd_pct, "n_trades": n_trades,
        "win_rate": wins/closed*100 if closed > 0 else 0,
        "equities": equities[start:].copy(),
        "n_switches": n_switches,
    }


def main():
    t0 = time.time()
    cache = ParquetCache()
    n_coins = len(COINS)
    CAPITAL = 10_000.0 / n_coins

    # Load MeanRev best params
    if MEANREV_PARAMS_PATH.exists():
        with open(MEANREV_PARAMS_PATH) as f:
            prev = json.load(f)
        mr_params = prev.get("meanrev_best_params", {})
    else:
        print("ERROR: Run mean_reversion_experiment.py first")
        return

    # Import B0 and MR functions
    from scripts.mean_reversion_experiment import run_donchian_b0, run_meanrev

    print("=" * 70)
    print("Regime Dynamic Switching Experiment (Holdout 2025.07-2026.03)")
    print("=" * 70)

    # Run all 5 strategies on holdout
    results = {k: {} for k in ["A_don", "B_mr", "D_switch", "Df_switch"]}

    for coin in COINS:
        df = load_8h_data(cache, coin, "2025-07-01", "2026-04-01")
        if df is None:
            print(f"  {coin}: no holdout data", flush=True)
            continue

        # A) Pure Donchian
        r_don = run_donchian_b0(df, CAPITAL, n_coins, use_dynamic_slip=True)
        if r_don:
            results["A_don"][coin] = r_don

        # B) Pure MeanRev
        p = mr_params.get(coin)
        if p and len(p) == 4:
            r_mr = run_meanrev(df, p[0], p[1], p[2], p[3], CAPITAL, n_coins)
            if r_mr:
                results["B_mr"][coin] = r_mr

        # D) Regime switching (original, no hysteresis)
        if p and len(p) == 4:
            r_sw = run_regime_switch(df, p[0], p[1], p[2], p[3], CAPITAL, n_coins)
            if r_sw:
                results["D_switch"][coin] = r_sw

        # D-fixed) Regime switching with hysteresis
        if p and len(p) == 4:
            r_swf = run_regime_switch_hysteresis(
                df, p[0], p[1], p[2], p[3], CAPITAL, n_coins)
            if r_swf:
                results["Df_switch"][coin] = r_swf

    # C) 50/50 equal weight (combine A and B equity curves)
    # We need to build it from per-coin results
    common = [c for c in COINS if c in results["A_don"] and c in results["B_mr"]]

    # Portfolio-level metrics
    portfolio = {}
    for name, key in [("A) Donchian B0 only", "A_don"),
                       ("B) MeanRev only", "B_mr"),
                       ("D) Regime Switch", "D_switch"),
                       ("D-fix) Hysteresis", "Df_switch")]:
        coin_results = results[key]
        if not coin_results:
            continue
        min_len = min(len(r["equities"]) for r in coin_results.values())
        port_eq = np.zeros(min_len)
        for r in coin_results.values():
            port_eq += r["equities"][:min_len]
        eq_s = pd.Series(port_eq)
        sr = sharpe_ratio(eq_s, PPY_8H)
        _, dd = max_drawdown(eq_s)
        ret = (port_eq[-1] / port_eq[0] - 1) * 100 if port_eq[0] > 0 else 0
        total_trades = sum(r["n_trades"] for r in coin_results.values())
        portfolio[name] = {
            "sharpe": sr, "max_dd": dd, "return_pct": ret,
            "n_trades": total_trades, "equities": port_eq,
        }

    # C) 50/50: average of A and B equity curves
    if "A) Donchian B0 only" in portfolio and "B) MeanRev only" in portfolio:
        a_eq = portfolio["A) Donchian B0 only"]["equities"]
        b_eq = portfolio["B) MeanRev only"]["equities"]
        min_len = min(len(a_eq), len(b_eq))
        combo_eq = (a_eq[:min_len] + b_eq[:min_len]) / 2
        eq_s = pd.Series(combo_eq)
        sr = sharpe_ratio(eq_s, PPY_8H)
        _, dd = max_drawdown(eq_s)
        ret = (combo_eq[-1] / combo_eq[0] - 1) * 100 if combo_eq[0] > 0 else 0
        portfolio["C) 50/50 Equal Weight"] = {
            "sharpe": sr, "max_dd": dd, "return_pct": ret,
            "n_trades": portfolio["A) Donchian B0 only"]["n_trades"] +
                        portfolio["B) MeanRev only"]["n_trades"],
            "equities": combo_eq,
        }

    # Print results
    print(f"\n  {'Portfolio':<25} {'Sharpe':>8} {'MaxDD%':>8} {'Return%':>9} {'Trades':>7}")
    print("  " + "-" * 60)
    ALL_NAMES = ["A) Donchian B0 only", "B) MeanRev only",
                  "C) 50/50 Equal Weight", "D) Regime Switch",
                  "D-fix) Hysteresis"]
    for name in ALL_NAMES:
        if name in portfolio:
            p = portfolio[name]
            print(f"  {name:<25} {p['sharpe']:>8.3f} {p['max_dd']:>8.2f} "
                  f"{p['return_pct']:>9.2f} {p['n_trades']:>7}")

    # Regime switch stats
    if results["Df_switch"]:
        total_sw = sum(r.get("n_switches", 0) for r in results["Df_switch"].values())
        total_sw_old = sum(1 for _ in range(0))  # D doesn't track switches
        print(f"\n  D-fixed total regime switches: {total_sw} (across all coins)")

    # Per-coin comparison
    print(f"\n  Per-coin holdout:")
    print(f"  {'Coin':<6} {'Don SR':>8} {'MR SR':>8} {'D SR':>8} {'D-fix SR':>9} {'D-fix Ret%':>11}")
    print("  " + "-" * 55)
    for coin in COINS:
        ds = results["A_don"].get(coin, {}).get("sharpe")
        ms = results["B_mr"].get(coin, {}).get("sharpe")
        ss = results["D_switch"].get(coin, {}).get("sharpe")
        sf = results["Df_switch"].get(coin, {}).get("sharpe")
        rf = results["Df_switch"].get(coin, {}).get("return_pct")
        ds_s = f"{ds:>8.3f}" if ds is not None else f"{'---':>8}"
        ms_s = f"{ms:>8.3f}" if ms is not None else f"{'---':>8}"
        ss_s = f"{ss:>8.3f}" if ss is not None else f"{'---':>8}"
        sf_s = f"{sf:>9.3f}" if sf is not None else f"{'---':>9}"
        rf_s = f"{rf:>11.2f}" if rf is not None else f"{'---':>11}"
        print(f"  {coin:<6} {ds_s} {ms_s} {ss_s} {sf_s} {rf_s}")

    # Save results
    save_data = {
        "portfolio_comparison": {
            name: {k: v for k, v in p.items() if k != "equities"}
            for name, p in portfolio.items()
        },
        "per_coin_d_fixed": {
            c: {k: v for k, v in r.items() if k != "equities"}
            for c, r in results["Df_switch"].items()
        },
    }
    out_path = Path("sweep_results/regime_switch_experiment.json")
    with open(out_path, "w") as f:
        json.dump(save_data, f, indent=2, default=str)

    # Append to RESEARCH_LOG.md
    log_entry = f"""
## Regime Switching with Hysteresis ({pd.Timestamp.now().strftime('%Y-%m-%d')})

### Hysteresis Parameters
- Trending -> Ranging: ADX must drop below 18 (was 20)
- Ranging -> Trending: ADX must rise above 27 (was 25)
- No gray zone (binary: trending or ranging)
- Minimum 10 bars (80h) hold before re-switching
- On switch: existing positions held until natural exit

### Portfolio Comparison (Holdout 2025.07-2026.03)
| Portfolio | Sharpe | MaxDD% | Return% | Trades |
|-----------|--------|--------|---------|--------|
"""
    for name in ALL_NAMES:
        if name in portfolio:
            p = portfolio[name]
            log_entry += f"| {name} | {p['sharpe']:.3f} | {p['max_dd']:.2f} | {p['return_pct']:.2f} | {p['n_trades']} |\n"

    log_entry += "\n### Key Finding\n"
    best = max(portfolio.items(), key=lambda x: x[1].get("sharpe", 0))
    log_entry += f"- Best approach: {best[0]} (Sharpe {best[1]['sharpe']:.3f})\n"
    if "D-fix) Hysteresis" in portfolio and "D) Regime Switch" in portfolio:
        df_sr = portfolio["D-fix) Hysteresis"]["sharpe"]
        d_sr = portfolio["D) Regime Switch"]["sharpe"]
        df_tr = portfolio["D-fix) Hysteresis"]["n_trades"]
        d_tr = portfolio["D) Regime Switch"]["n_trades"]
        log_entry += f"- Hysteresis reduced trades: {d_tr} -> {df_tr}\n"
        log_entry += f"- Hysteresis Sharpe: {df_sr:.3f} vs original: {d_sr:.3f}\n"

    with open("RESEARCH_LOG.md", "a", encoding="utf-8") as f:
        f.write(log_entry)

    print(f"\n  Results saved and appended to RESEARCH_LOG.md")
    print(f"  Total time: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
