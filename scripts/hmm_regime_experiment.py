#!/usr/bin/env python3
"""HMM Regime Detection experiment: replace ADX with Hidden Markov Model.

Compares regime detection methods for PM strategy allocation:
A) Pure Donchian B0
B) Pure MeanRev
C) 50/50 Equal Weight
D-fix) ADX hysteresis
E) HMM regime switching
F) HMM + hysteresis
G) ADX+HMM vote (both must agree, else 50/50)
"""

import sys, os, time, json, warnings
from pathlib import Path
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptolab.data.cache import ParquetCache
from cryptolab.backtest.metrics import sharpe_ratio, max_drawdown
from scripts.donchian_full_sweep import resample_ohlcv
from scripts.mean_reversion_experiment import (
    compute_adx, compute_dynamic_slippage, load_8h_data,
    run_donchian_b0, run_meanrev,
    COINS, PPY_8H, FEE_BPS,
)

from hmmlearn.hmm import GaussianHMM

MEANREV_PARAMS_PATH = Path("sweep_results/meanrev_experiment.json")

WINDOWS = [
    {"name": "W1", "is_end": "2022-07-01", "val_start": "2022-07-01", "val_end": "2023-07-01"},
    {"name": "W2", "is_end": "2023-07-01", "val_start": "2023-07-01", "val_end": "2024-07-01"},
    {"name": "W3", "is_end": "2024-07-01", "val_start": "2024-07-01", "val_end": "2025-07-01"},
]
HOLDOUT = {"start": "2025-07-01", "end": "2026-04-01"}


def build_hmm_features(closes, volumes, window=20):
    """Build observation features for HMM from price/volume data.

    Features (all shifted by 1 to prevent lookahead):
    1. 1-bar return
    2. Rolling 20-bar volatility (std of returns)
    3. Rolling 20-bar volume change rate
    """
    n = len(closes)
    ret = np.zeros(n)
    ret[1:] = closes[1:] / closes[:-1] - 1

    vol = pd.Series(ret).rolling(window, min_periods=5).std().values
    vol_chg = np.zeros(n)
    vol_ma = pd.Series(volumes).rolling(window, min_periods=5).mean().values
    for i in range(1, n):
        if vol_ma[i-1] > 0:
            vol_chg[i] = (volumes[i] - vol_ma[i-1]) / vol_ma[i-1]

    # Stack features, use shift(1) equivalent by using [i-1] in loop
    features = np.column_stack([ret, vol, vol_chg])
    return features


def train_hmm(closes, volumes, n_states=2):
    """Train 2-state GaussianHMM on IS data.

    Returns trained model and state labels (which state = trending).
    """
    features = build_hmm_features(closes, volumes)

    # Remove NaN rows (warmup period)
    valid_mask = ~np.any(np.isnan(features), axis=1)
    valid_features = features[valid_mask]

    if len(valid_features) < 100:
        return None, None

    model = GaussianHMM(
        n_components=n_states,
        covariance_type="full",
        n_iter=100,
        random_state=42,
    )
    try:
        model.fit(valid_features)
    except Exception:
        return None, None

    # Decode states
    states = model.predict(valid_features)

    # Label states: higher volatility state = trending
    state_vols = []
    for s in range(n_states):
        mask = states == s
        if mask.sum() > 0:
            state_vols.append(np.mean(np.abs(valid_features[mask, 0])))
        else:
            state_vols.append(0)

    trending_state = np.argmax(state_vols)
    return model, trending_state


def hmm_predict_regime(model, trending_state, closes, volumes, bar_idx):
    """Predict regime for a single bar using HMM (no future data).

    Uses all data up to bar_idx (inclusive) for inference.
    """
    if model is None:
        return "trending"

    features = build_hmm_features(closes[:bar_idx+1], volumes[:bar_idx+1])
    valid_mask = ~np.any(np.isnan(features), axis=1)
    valid_features = features[valid_mask]

    if len(valid_features) < 10:
        return "trending"

    try:
        states = model.predict(valid_features)
        current_state = states[-1]
        return "trending" if current_state == trending_state else "ranging"
    except Exception:
        return "trending"


def hmm_predict_all(model, trending_state, closes, volumes):
    """Predict regime for ALL bars at once (much faster than per-bar).

    Still causal: uses expanding window internally via HMM's forward algorithm.
    """
    n = len(closes)
    features = build_hmm_features(closes, volumes)
    valid_mask = ~np.any(np.isnan(features), axis=1)

    regimes = np.full(n, -1)  # -1 = unknown
    if model is None:
        return ["trending"] * n

    valid_features = features[valid_mask]
    if len(valid_features) < 10:
        return ["trending"] * n

    try:
        states = model.predict(valid_features)
        # Map back to full array
        valid_indices = np.where(valid_mask)[0]
        for idx, state in zip(valid_indices, states):
            regimes[idx] = state
    except Exception:
        return ["trending"] * n

    # Fill forward unknown values
    last_known = 0
    for i in range(n):
        if regimes[i] >= 0:
            last_known = regimes[i]
        else:
            regimes[i] = last_known

    return ["trending" if r == trending_state else "ranging" for r in regimes]


def run_hmm_regime(df, mr_lookback, mr_entry_z, mr_exit_z, mr_stop_z,
                   capital, n_coins, hmm_model, trending_state,
                   use_hysteresis=False, min_regime_bars=10):
    """Run regime switching using HMM for regime detection."""
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

    # Precompute HMM regimes for all bars at once
    hmm_regimes = hmm_predict_all(hmm_model, trending_state, closes, volumes)

    # ADX for vote method
    adx_arr = compute_adx(highs, lows, closes, 20)

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
    don_held_target = 0.0; mr_held_target = 0.0
    regime = "trending"; bars_in_regime = 999
    start = warmup

    for i in range(start, n):
        o = opens[i]; c = closes[i]; z = z_score[i]

        # Execute
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

        # HMM regime
        new_regime = hmm_regimes[i]
        bars_in_regime += 1

        if use_hysteresis:
            if new_regime != regime and bars_in_regime >= min_regime_bars:
                regime = new_regime
                bars_in_regime = 0
        else:
            regime = new_regime

        # Vol contraction blocks all
        v10 = vol_10d[i]; v30 = vol_30d[i]
        vol_contraction = (not np.isnan(v10) and not np.isnan(v30) and v30 > 0
                           and v10 < v30 * 0.7)
        don_can_enter = (regime == "trending" and not vol_contraction)
        mr_can_enter = (regime == "ranging" and not vol_contraction
                        and not np.isnan(z) and not np.isnan(sma[i]))

        # Donchian exit
        don_target = 0.0
        if don_side == "long":
            med_lower = channels[don_lbs[1]]["lower"][i]
            if not np.isnan(med_lower) and c < med_lower:
                don_side = None; don_held_target = 0.0
        elif don_side == "short":
            med_upper = channels[don_lbs[1]]["upper"][i]
            if not np.isnan(med_upper) and c > med_upper:
                don_side = None; don_held_target = 0.0

        # Donchian entry
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
                ann_vol = (atr[i]/c)*np.sqrt(PPY_8H) if not np.isnan(atr[i]) and atr[i] > 0 and c > 0 else 1.0
                vol_sc = max(0.5, min(2.0, 0.15/ann_vol)) if ann_vol > 0 else 1.0
                dd = max(0, 1.0-equity/peak)
                dd_sc = 1.0-min(dd/0.30, 1.0)*0.75 if dd > 0 else 1.0
                don_target = direction * min(equity*3.0*abs(agreement)*vol_sc*dd_sc, equity*3.0)
                don_side = "long" if direction > 0 else "short"
                don_held_target = don_target

        if don_side is not None and don_target == 0:
            don_target = don_held_target

        # MR exit
        mr_target = 0.0
        if mr_side == "long":
            if not np.isnan(z) and (z >= -mr_exit_z or z < -mr_stop_z):
                mr_side = None; mr_held_target = 0.0
        elif mr_side == "short":
            if not np.isnan(z) and (z <= mr_exit_z or z > mr_stop_z):
                mr_side = None; mr_held_target = 0.0

        # MR entry
        if mr_side is None and mr_can_enter:
            stop_z_dist = mr_stop_z - mr_entry_z
            s = std[i] if not np.isnan(std[i]) and std[i] > 0 else c*0.02
            sdp = max(stop_z_dist*s/c, 0.001) if c > 0 else 0.01
            bp = (equity*0.02/sdp)*3.0; mp = equity*3.0
            avol = (std[i]/c)*np.sqrt(PPY_8H) if not np.isnan(std[i]) and std[i] > 0 and c > 0 else 1.0
            vsc = max(0.5, min(2.0, 0.15/avol)) if avol > 0 else 1.0
            dd_ = max(0, 1.0-equity/peak)
            dsc = 1.0-min(dd_/0.30, 1.0)*0.75 if dd_ > 0 else 1.0
            position = min(bp*vsc*dsc, mp)
            if z < -mr_entry_z and position > 0:
                mr_target = position; mr_side = "long"; mr_held_target = mr_target
            elif z > mr_entry_z and position > 0:
                mr_target = -position; mr_side = "short"; mr_held_target = mr_target

        if mr_side is not None and mr_target == 0:
            mr_target = mr_held_target

        prev_target = don_target + mr_target

    eq = pd.Series(equities[start:])
    if len(eq) < 10: return None
    sr = sharpe_ratio(eq, PPY_8H); _, dd_pct = max_drawdown(eq)
    return {
        "sharpe": sr, "return_pct": (float(eq.iloc[-1])-capital)/capital*100,
        "max_dd_pct": dd_pct, "n_trades": n_trades,
        "win_rate": wins/closed*100 if closed > 0 else 0,
        "equities": equities[start:].copy(),
    }


def run_vote_regime(df, mr_lookback, mr_entry_z, mr_exit_z, mr_stop_z,
                    capital, n_coins, hmm_model, trending_state,
                    min_regime_bars=10):
    """ADX + HMM vote: both agree -> that regime, disagree -> 50/50.

    50/50 is implemented as: run both strategies at half equity.
    For simplicity, we just run the full regime-switch logic where
    regime is determined by vote.
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

    hmm_regimes = hmm_predict_all(hmm_model, trending_state, closes, volumes)
    adx_arr = compute_adx(highs, lows, closes, 20)

    ret = np.zeros(n); ret[1:] = closes[1:]/closes[:-1] - 1
    ret_s = pd.Series(ret)
    vol_10d = ret_s.rolling(30, min_periods=10).std().values
    vol_30d = ret_s.rolling(90, min_periods=30).std().values

    atr_p = 14
    tr_arr = np.maximum(highs[1:]-lows[1:], np.maximum(np.abs(highs[1:]-closes[:-1]), np.abs(lows[1:]-closes[:-1])))
    tr_arr = np.insert(tr_arr, 0, highs[0]-lows[0])
    atr = np.full(n, np.nan)
    atr[atr_p] = np.mean(tr_arr[:atr_p])
    for i in range(atr_p+1, n): atr[i] = atr[i-1]*(atr_p-1)/atr_p + tr_arr[i]/atr_p

    sma = pd.Series(closes).rolling(mr_lookback, min_periods=mr_lookback).mean().values
    std = pd.Series(closes).rolling(mr_lookback, min_periods=mr_lookback).std(ddof=1).values
    z_score = np.where(std > 1e-10, (closes-sma)/std, 0.0)

    vol_usd = volumes * closes
    adv = pd.Series(vol_usd).rolling(60, min_periods=3).sum().values / 20

    fee_rate = FEE_BPS / 10_000
    equity = capital; cash = equity; pos = 0.0; entry_px = 0.0
    peak = equity; equities = np.full(n, equity)
    n_trades = 0; wins = 0; closed = 0; prev_target = 0.0
    don_side = None; mr_side = None
    don_held_target = 0.0; mr_held_target = 0.0
    start = warmup

    for i in range(start, n):
        o = opens[i]; c = closes[i]; z = z_score[i]

        trade_size = abs(prev_target - pos)
        if trade_size > max(5.0, abs(prev_target)*0.03):
            fee = trade_size * fee_rate
            slip = compute_dynamic_slippage(trade_size, adv[i])
            if abs(pos) > 0.01 and entry_px > 0:
                pnl = abs(pos)*((o-entry_px)/entry_px if pos > 0 else (entry_px-o)/entry_px)
                cash += pnl
                if pnl > 0: wins += 1
                closed += 1
            cash -= fee + slip; n_trades += 1
            pos = prev_target
            entry_px = o if abs(pos) > 0.01 else 0.0

        unrealized = 0.0
        if abs(pos) > 0.01 and entry_px > 0:
            unrealized = abs(pos)*((c-entry_px)/entry_px if pos > 0 else (entry_px-c)/entry_px)
        equity = cash + unrealized; peak = max(peak, equity); equities[i] = equity

        # Vote: ADX + HMM
        hmm_reg = hmm_regimes[i]
        adx_val = adx_arr[i] if not np.isnan(adx_arr[i]) else 25.0
        adx_reg = "trending" if adx_val >= 25 else ("ranging" if adx_val < 20 else "gray")

        # Vote logic
        if hmm_reg == "trending" and adx_reg == "trending":
            don_scale = 1.0; mr_scale = 0.0
        elif hmm_reg == "ranging" and adx_reg == "ranging":
            don_scale = 0.0; mr_scale = 1.0
        else:
            don_scale = 0.5; mr_scale = 0.5  # disagree -> 50/50

        v10 = vol_10d[i]; v30 = vol_30d[i]
        if not np.isnan(v10) and not np.isnan(v30) and v30 > 0 and v10 < v30*0.7:
            don_scale = 0.0; mr_scale = 0.0

        don_target = 0.0
        if don_side == "long":
            med_lower = channels[don_lbs[1]]["lower"][i]
            if not np.isnan(med_lower) and c < med_lower:
                don_side = None; don_held_target = 0.0
        elif don_side == "short":
            med_upper = channels[don_lbs[1]]["upper"][i]
            if not np.isnan(med_upper) and c > med_upper:
                don_side = None; don_held_target = 0.0

        if don_side is None and don_scale > 0:
            wts = [0.25, 0.50, 0.25]; dirs = []
            for lb in don_lbs:
                u = channels[lb]["upper"][i]; l = channels[lb]["lower"][i]
                if np.isnan(u) or np.isnan(l): dirs.append(0.0)
                elif c > u: dirs.append(1.0)
                elif c < l: dirs.append(-1.0)
                else: dirs.append(0.0)
            agreement = sum(w*d for w, d in zip(wts, dirs))
            if abs(agreement) >= 0.05:
                direction = 1.0 if agreement > 0 else -1.0
                ann_vol = (atr[i]/c)*np.sqrt(PPY_8H) if not np.isnan(atr[i]) and atr[i] > 0 and c > 0 else 1.0
                vol_sc = max(0.5, min(2.0, 0.15/ann_vol)) if ann_vol > 0 else 1.0
                dd = max(0, 1.0-equity/peak)
                dd_sc = 1.0-min(dd/0.30, 1.0)*0.75 if dd > 0 else 1.0
                don_target = direction*min(equity*3.0*abs(agreement)*vol_sc*dd_sc*don_scale, equity*3.0*don_scale)
                don_side = "long" if direction > 0 else "short"
                don_held_target = don_target
        if don_side is not None and don_target == 0:
            don_target = don_held_target

        mr_target = 0.0
        if mr_side == "long":
            if not np.isnan(z) and (z >= -mr_exit_z or z < -mr_stop_z):
                mr_side = None; mr_held_target = 0.0
        elif mr_side == "short":
            if not np.isnan(z) and (z <= mr_exit_z or z > mr_stop_z):
                mr_side = None; mr_held_target = 0.0

        if mr_side is None and mr_scale > 0 and not np.isnan(z) and not np.isnan(sma[i]):
            stop_z_dist = mr_stop_z - mr_entry_z
            s = std[i] if not np.isnan(std[i]) and std[i] > 0 else c*0.02
            sdp = max(stop_z_dist*s/c, 0.001) if c > 0 else 0.01
            bp = (equity*0.02/sdp)*3.0*mr_scale; mp = equity*3.0*mr_scale
            avol = (std[i]/c)*np.sqrt(PPY_8H) if not np.isnan(std[i]) and std[i] > 0 and c > 0 else 1.0
            vsc = max(0.5, min(2.0, 0.15/avol)) if avol > 0 else 1.0
            dd_ = max(0, 1.0-equity/peak)
            dsc = 1.0-min(dd_/0.30, 1.0)*0.75 if dd_ > 0 else 1.0
            position = min(bp*vsc*dsc, mp)
            if z < -mr_entry_z and position > 0:
                mr_target = position; mr_side = "long"; mr_held_target = mr_target
            elif z > mr_entry_z and position > 0:
                mr_target = -position; mr_side = "short"; mr_held_target = mr_target
        if mr_side is not None and mr_target == 0:
            mr_target = mr_held_target

        prev_target = don_target + mr_target

    eq = pd.Series(equities[start:])
    if len(eq) < 10: return None
    sr = sharpe_ratio(eq, PPY_8H); _, dd_pct = max_drawdown(eq)
    return {
        "sharpe": sr, "return_pct": (float(eq.iloc[-1])-capital)/capital*100,
        "max_dd_pct": dd_pct, "n_trades": n_trades,
        "win_rate": wins/closed*100 if closed > 0 else 0,
        "equities": equities[start:].copy(),
    }


def main():
    t0 = time.time()
    cache = ParquetCache()
    n_coins = len(COINS)
    CAPITAL = 10_000.0 / n_coins

    with open(MEANREV_PARAMS_PATH) as f:
        mr_params = json.load(f).get("meanrev_best_params", {})

    from scripts.regime_switching_experiment import run_regime_switch_hysteresis

    print("=" * 70)
    print("HMM Regime Detection Experiment (Holdout 2025.07-2026.03)")
    print("=" * 70)

    # Step 1: Train HMM on IS data (use W3's IS: 2021-01 to 2024-07)
    print("\n  Training HMM models per coin on IS data (2021-01 to 2024-07)...")
    hmm_models = {}
    for coin in COINS:
        df_is = load_8h_data(cache, coin, "2021-01-01", "2024-07-01")
        if df_is is None or len(df_is) < 500:
            print(f"    {coin}: insufficient IS data, skip")
            continue
        model, trend_state = train_hmm(df_is["close"].values, df_is["volume"].values)
        if model is not None:
            hmm_models[coin] = (model, trend_state)
            # Quick check: what fraction is trending?
            regimes = hmm_predict_all(model, trend_state, df_is["close"].values, df_is["volume"].values)
            pct_trend = sum(1 for r in regimes if r == "trending") / len(regimes) * 100
            print(f"    {coin}: trained OK ({pct_trend:.0f}% trending in IS)")
        else:
            print(f"    {coin}: HMM training failed")

    # Step 2: Run all strategies on holdout
    print(f"\n  Running strategies on holdout ({len(hmm_models)} coins with HMM)...")
    keys = ["A_don", "B_mr", "Df_adx", "E_hmm", "F_hmm_hyst", "G_vote"]
    results = {k: {} for k in keys}

    for coin in COINS:
        df = load_8h_data(cache, coin, "2025-07-01", "2026-04-01")
        if df is None: continue

        p = mr_params.get(coin)
        if not p or len(p) != 4: continue

        # A) Donchian
        r = run_donchian_b0(df, CAPITAL, n_coins, use_dynamic_slip=True)
        if r: results["A_don"][coin] = r

        # B) MeanRev
        r = run_meanrev(df, p[0], p[1], p[2], p[3], CAPITAL, n_coins)
        if r: results["B_mr"][coin] = r

        # D-fix) ADX hysteresis
        r = run_regime_switch_hysteresis(df, p[0], p[1], p[2], p[3], CAPITAL, n_coins)
        if r: results["Df_adx"][coin] = r

        if coin not in hmm_models: continue
        model, trend_state = hmm_models[coin]

        # E) HMM (no hysteresis)
        r = run_hmm_regime(df, p[0], p[1], p[2], p[3], CAPITAL, n_coins,
                           model, trend_state, use_hysteresis=False)
        if r: results["E_hmm"][coin] = r

        # F) HMM + hysteresis
        r = run_hmm_regime(df, p[0], p[1], p[2], p[3], CAPITAL, n_coins,
                           model, trend_state, use_hysteresis=True)
        if r: results["F_hmm_hyst"][coin] = r

        # G) ADX + HMM vote
        r = run_vote_regime(df, p[0], p[1], p[2], p[3], CAPITAL, n_coins,
                            model, trend_state)
        if r: results["G_vote"][coin] = r

    # Build portfolio metrics
    portfolio = {}
    labels = [
        ("A) Donchian B0", "A_don"), ("B) MeanRev", "B_mr"),
        ("D-fix) ADX hyst", "Df_adx"),
        ("E) HMM", "E_hmm"), ("F) HMM+hyst", "F_hmm_hyst"),
        ("G) ADX+HMM vote", "G_vote"),
    ]
    for name, key in labels:
        cr = results[key]
        if not cr: continue
        min_len = min(len(r["equities"]) for r in cr.values())
        port_eq = np.zeros(min_len)
        for r in cr.values():
            port_eq += r["equities"][:min_len]
        eq_s = pd.Series(port_eq)
        sr = sharpe_ratio(eq_s, PPY_8H); _, dd = max_drawdown(eq_s)
        ret = (port_eq[-1]/port_eq[0]-1)*100 if port_eq[0] > 0 else 0
        total_trades = sum(r["n_trades"] for r in cr.values())
        portfolio[name] = {"sharpe": sr, "max_dd": dd, "return_pct": ret, "n_trades": total_trades}

    # C) 50/50
    if "A) Donchian B0" in portfolio and "B) MeanRev" in portfolio:
        a_eq = np.zeros(1); b_eq = np.zeros(1)
        a_cr = results["A_don"]; b_cr = results["B_mr"]
        min_len = min(min(len(r["equities"]) for r in a_cr.values()),
                      min(len(r["equities"]) for r in b_cr.values()))
        a_eq = sum(r["equities"][:min_len] for r in a_cr.values())
        b_eq = sum(r["equities"][:min_len] for r in b_cr.values())
        combo = (a_eq + b_eq) / 2
        eq_s = pd.Series(combo)
        sr = sharpe_ratio(eq_s, PPY_8H); _, dd = max_drawdown(eq_s)
        ret = (combo[-1]/combo[0]-1)*100 if combo[0] > 0 else 0
        portfolio["C) 50/50 Equal"] = {
            "sharpe": sr, "max_dd": dd, "return_pct": ret,
            "n_trades": portfolio["A) Donchian B0"]["n_trades"] + portfolio["B) MeanRev"]["n_trades"],
        }

    # Print
    print(f"\n  {'Portfolio':<20} {'Sharpe':>8} {'MaxDD%':>8} {'Return%':>9} {'Trades':>7}")
    print("  " + "-" * 55)
    ALL_NAMES = ["A) Donchian B0", "B) MeanRev", "C) 50/50 Equal",
                 "D-fix) ADX hyst", "E) HMM", "F) HMM+hyst", "G) ADX+HMM vote"]
    for name in ALL_NAMES:
        if name in portfolio:
            p = portfolio[name]
            print(f"  {name:<20} {p['sharpe']:>8.3f} {p['max_dd']:>8.2f} {p['return_pct']:>9.2f} {p['n_trades']:>7}")

    # Save + log
    save_data = {name: p for name, p in portfolio.items()}
    Path("sweep_results").mkdir(exist_ok=True)
    with open("sweep_results/hmm_regime_experiment.json", "w") as f:
        json.dump(save_data, f, indent=2, default=str)

    log_entry = f"""
## HMM Regime Detection Experiment ({pd.Timestamp.now().strftime('%Y-%m-%d')})

### Portfolio Comparison (Holdout 2025.07-2026.03)
| Portfolio | Sharpe | MaxDD% | Return% | Trades |
|-----------|--------|--------|---------|--------|
"""
    for name in ALL_NAMES:
        if name in portfolio:
            p = portfolio[name]
            log_entry += f"| {name} | {p['sharpe']:.3f} | {p['max_dd']:.2f} | {p['return_pct']:.2f} | {p['n_trades']} |\n"

    best = max(portfolio.items(), key=lambda x: x[1]["sharpe"])
    log_entry += f"\nBest: {best[0]} (Sharpe {best[1]['sharpe']:.3f})\n"

    with open("RESEARCH_LOG.md", "a", encoding="utf-8") as f:
        f.write(log_entry)

    print(f"\n  Results saved. Total time: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
