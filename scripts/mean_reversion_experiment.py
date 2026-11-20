#!/usr/bin/env python3
"""Mean Reversion Z-Score experiment: parameter sweep + complementarity with Donchian.

Tasks:
1. Re-run B0 Donchian with dynamic slippage model -> compare Sharpe
2. Mean reversion parameter sweep (walk-forward)
3. Complementarity analysis (Donchian vs MeanRev correlation)
4. Portfolio combinations comparison
"""

import sys, os, time, json, logging
from pathlib import Path
from itertools import product
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptolab.data.cache import ParquetCache
from cryptolab.backtest.metrics import sharpe_ratio, max_drawdown, PERIODS_PER_YEAR
from scripts.donchian_full_sweep import resample_ohlcv

logging.basicConfig(level=logging.WARNING)

COINS = ["BTC","ETH","LTC","TRX","BCH","DOT","ADA","LINK","XLM","XRP",
         "ETC","ALGO","ATOM","AAVE","SOL","ICP","UNI","FIL","AVAX","NEAR",
         "CRV","DOGE"]

PPY_8H = 1096
FEE_BPS = 3.5   # taker fee only (slippage computed separately)
K1 = 0.01       # quadratic slippage coefficient
K2_BPS = 15.0   # linear slippage (small trader)
AUTO_THRESH = 0.001  # |trade|/ADV threshold

WINDOWS = [
    {"name": "W1", "is_start": "2021-01-01", "is_end": "2022-07-01",
     "val_start": "2022-07-01", "val_end": "2023-07-01"},
    {"name": "W2", "is_start": "2021-01-01", "is_end": "2023-07-01",
     "val_start": "2023-07-01", "val_end": "2024-07-01"},
    {"name": "W3", "is_start": "2021-01-01", "is_end": "2024-07-01",
     "val_start": "2024-07-01", "val_end": "2025-07-01"},
]
HOLDOUT = {"start": "2025-07-01", "end": "2026-04-01"}


# ---------------------------------------------------------------------------
# ADX computation (vectorized, from institutional_experiment.py)
# ---------------------------------------------------------------------------

def compute_adx(highs, lows, closes, period=20):
    n = len(highs)
    adx = np.full(n, np.nan)
    if n < period * 2:
        return adx
    tr = np.zeros(n); pdm = np.zeros(n); mdm = np.zeros(n)
    for i in range(1, n):
        h_d = highs[i] - highs[i-1]; l_d = lows[i-1] - lows[i]
        tr[i] = max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1]))
        pdm[i] = h_d if (h_d > l_d and h_d > 0) else 0
        mdm[i] = l_d if (l_d > h_d and l_d > 0) else 0
    atr_s = np.zeros(n); pdm_s = np.zeros(n); mdm_s = np.zeros(n)
    atr_s[period] = np.sum(tr[1:period+1])
    pdm_s[period] = np.sum(pdm[1:period+1])
    mdm_s[period] = np.sum(mdm[1:period+1])
    for i in range(period+1, n):
        atr_s[i] = atr_s[i-1] - atr_s[i-1]/period + tr[i]
        pdm_s[i] = pdm_s[i-1] - pdm_s[i-1]/period + pdm[i]
        mdm_s[i] = mdm_s[i-1] - mdm_s[i-1]/period + mdm[i]
    dx = np.zeros(n)
    for i in range(period, n):
        if atr_s[i] > 0:
            pdi = 100*pdm_s[i]/atr_s[i]; mdi = 100*mdm_s[i]/atr_s[i]
            if pdi+mdi > 0:
                dx[i] = 100*abs(pdi-mdi)/(pdi+mdi)
    adx[period*2] = np.mean(dx[period:period*2+1])
    for i in range(period*2+1, n):
        adx[i] = (adx[i-1]*(period-1)+dx[i])/period
    return adx


# ---------------------------------------------------------------------------
# Dynamic slippage
# ---------------------------------------------------------------------------

def compute_dynamic_slippage(trade_usd, adv_usd):
    """Auto-select slippage model. Returns slippage in USD."""
    if trade_usd <= 0:
        return 0.0
    if adv_usd <= 0 or np.isnan(adv_usd):
        return trade_usd * K2_BPS / 10_000
    if trade_usd / adv_usd < AUTO_THRESH:
        return trade_usd * K2_BPS / 10_000  # linear
    else:
        return (K1 / adv_usd) * trade_usd ** 2  # quadratic


# ---------------------------------------------------------------------------
# Vectorized Donchian B0 backtest (with dynamic slippage)
# ---------------------------------------------------------------------------

def run_donchian_b0(df, capital, n_coins, use_dynamic_slip=True):
    """Run Donchian B0 on 8H data. Returns dict with metrics + equity array."""
    n = len(df)
    lbs = (36, 60, 336)
    max_lb = max(lbs)
    if n < max_lb + 60:
        return None

    highs = df["high"].values; lows = df["low"].values
    closes = df["close"].values; opens = df["open"].values
    volumes = df["volume"].values
    h_s = pd.Series(highs); l_s = pd.Series(lows)

    channels = {}
    for lb in lbs:
        channels[lb] = {
            "upper": h_s.rolling(lb).max().shift(1).values,
            "lower": l_s.rolling(lb).min().shift(1).values,
        }

    adx = compute_adx(highs, lows, closes, 20)
    ret = np.zeros(n); ret[1:] = closes[1:]/closes[:-1] - 1
    ret_s = pd.Series(ret)
    vol_10d_arr = ret_s.rolling(30, min_periods=10).std().values
    vol_30d_arr = ret_s.rolling(90, min_periods=30).std().values

    # ATR
    atr_p = 14
    tr_arr = np.maximum(highs[1:]-lows[1:],
                        np.maximum(np.abs(highs[1:]-closes[:-1]), np.abs(lows[1:]-closes[:-1])))
    tr_arr = np.insert(tr_arr, 0, highs[0]-lows[0])
    atr = np.full(n, np.nan)
    atr[atr_p] = np.mean(tr_arr[:atr_p])
    for i in range(atr_p+1, n):
        atr[i] = atr[i-1]*(atr_p-1)/atr_p + tr_arr[i]/atr_p

    # ADV (rolling 20-day = 60 bars at 8H)
    vol_usd = volumes * closes
    adv = pd.Series(vol_usd).rolling(60, min_periods=3).sum().values / 20

    fee_rate = FEE_BPS / 10_000
    equity = capital; cash = equity; pos = 0.0; entry_px = 0.0
    peak = equity; equities = np.full(n, equity)
    n_trades = 0; wins = 0; closed = 0; prev_target = 0.0
    start = max_lb + 60

    for i in range(start, n):
        o = opens[i]; c = closes[i]

        # Execute previous signal
        trade_size = abs(prev_target - pos)
        if trade_size > max(5.0, abs(prev_target) * 0.03):
            fee = trade_size * fee_rate
            if use_dynamic_slip:
                slip = compute_dynamic_slippage(trade_size, adv[i])
            else:
                slip = trade_size * 15.0 / 10_000
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

        # Regime filter
        adx_val = adx[i] if not np.isnan(adx[i]) else 25.0
        regime_scale = 1.0 if adx_val >= 25 else (0.5 if adx_val >= 20 else 0.0)
        v10 = vol_10d_arr[i]; v30 = vol_30d_arr[i]
        if not np.isnan(v10) and not np.isnan(v30) and v30 > 0 and v10 < v30*0.7:
            regime_scale = 0.0

        # Signal: med-heavy weighted agreement
        wts = [0.25, 0.50, 0.25]
        dirs = []
        for lb in lbs:
            u = channels[lb]["upper"][i]; l = channels[lb]["lower"][i]
            if np.isnan(u) or np.isnan(l): dirs.append(0.0)
            elif c > u: dirs.append(1.0)
            elif c < l: dirs.append(-1.0)
            else: dirs.append(0.0)
        agreement = sum(w*d for w, d in zip(wts, dirs))
        if abs(agreement) < 0.05 or regime_scale == 0:
            prev_target = 0.0; continue
        direction = 1.0 if agreement > 0 else -1.0

        # Position sizing
        if not np.isnan(atr[i]) and atr[i] > 0 and c > 0:
            ann_vol = (atr[i]/c) * np.sqrt(PPY_8H)
            vol_scalar = max(0.5, min(2.0, 0.15/ann_vol if ann_vol > 0 else 1.0))
        else:
            vol_scalar = 1.0
        dd = max(0, 1.0 - equity/peak)
        dd_scalar = 1.0 - min(dd/0.30, 1.0)*0.75 if dd > 0 else 1.0
        base = equity * 3.0 * abs(agreement)
        prev_target = direction * min(base * vol_scalar * dd_scalar * regime_scale, equity * 3.0)

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


# ---------------------------------------------------------------------------
# Vectorized Mean Reversion backtest
# ---------------------------------------------------------------------------

def run_meanrev(df, lookback, entry_z, exit_z, stop_z, capital, n_coins,
                use_dynamic_slip=True):
    """Run mean reversion Z-score strategy on 8H data.

    Returns dict with metrics + equity array, or None if insufficient data.
    """
    n = len(df)
    warmup = max(lookback + 60, 100)
    if n < warmup + 20:
        return None

    highs = df["high"].values; lows = df["low"].values
    closes = df["close"].values; opens = df["open"].values
    volumes = df["volume"].values

    # Precompute Z-score series
    sma = pd.Series(closes).rolling(lookback, min_periods=lookback).mean().values
    std = pd.Series(closes).rolling(lookback, min_periods=lookback).std(ddof=1).values
    z_score = np.where(std > 1e-10, (closes - sma) / std, 0.0)

    # ADX for inverted regime filter
    adx = compute_adx(highs, lows, closes, 20)

    # Vol contraction (precompute rolling std)
    ret = np.zeros(n); ret[1:] = closes[1:]/closes[:-1] - 1
    ret_s = pd.Series(ret)
    vol_10d = ret_s.rolling(30, min_periods=10).std().values  # 10 days = 30 bars at 8H
    vol_30d = ret_s.rolling(90, min_periods=30).std().values  # 30 days = 90 bars at 8H

    # ADV for dynamic slippage
    vol_usd = volumes * closes
    adv = pd.Series(vol_usd).rolling(60, min_periods=3).sum().values / 20

    fee_rate = FEE_BPS / 10_000
    equity = capital; cash = equity; pos = 0.0; entry_px = 0.0
    peak = equity; equities = np.full(n, equity)
    n_trades = 0; wins = 0; closed = 0; prev_target = 0.0
    side = None  # "long", "short", None
    start = warmup

    for i in range(start, n):
        o = opens[i]; c = closes[i]; z = z_score[i]

        # Execute previous signal
        trade_size = abs(prev_target - pos)
        if trade_size > max(5.0, abs(prev_target) * 0.03):
            fee = trade_size * fee_rate
            if use_dynamic_slip:
                slip = compute_dynamic_slippage(trade_size, adv[i])
            else:
                slip = trade_size * 15.0 / 10_000
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

        if np.isnan(z) or np.isnan(sma[i]):
            prev_target = 0.0; continue

        # Regime filter (INVERTED: low ADX = good for mean reversion)
        adx_val = adx[i] if not np.isnan(adx[i]) else 25.0
        if adx_val < 20:
            regime_scale = 1.0   # ranging -> activate
        elif adx_val < 25:
            regime_scale = 0.5   # gray zone
        else:
            regime_scale = 0.0   # trending -> block

        # Vol contraction -> block
        v10 = vol_10d[i]; v30 = vol_30d[i]
        if not np.isnan(v10) and not np.isnan(v30) and v30 > 0 and v10 < v30*0.7:
            regime_scale = 0.0

        # Exit logic
        if side == "long":
            if z >= -exit_z:  # mean reverted
                prev_target = 0.0; side = None; continue
            if z < -stop_z:   # stop loss
                prev_target = 0.0; side = None; continue

        elif side == "short":
            if z <= exit_z:   # mean reverted
                prev_target = 0.0; side = None; continue
            if z > stop_z:    # stop loss
                prev_target = 0.0; side = None; continue

        # Entry logic (only when flat and regime allows)
        if side is None and regime_scale > 0:
            # Position sizing
            stop_z_dist = stop_z - entry_z
            s = std[i] if not np.isnan(std[i]) and std[i] > 0 else c * 0.02
            stop_dist_pct = stop_z_dist * s / c if c > 0 else 0.01
            stop_dist_pct = max(stop_dist_pct, 0.001)

            risk_usd = equity * 0.02  # 2% risk per trade
            base_pos = (risk_usd / stop_dist_pct) * 3.0  # 3x leverage
            max_pos = equity * 3.0

            # Vol targeting
            if not np.isnan(std[i]) and std[i] > 0 and c > 0:
                ann_vol_approx = (std[i] / c) * np.sqrt(PPY_8H)
                vol_scalar = max(0.5, min(2.0, 0.15 / ann_vol_approx)) if ann_vol_approx > 0 else 1.0
            else:
                vol_scalar = 1.0

            dd = max(0, 1.0 - equity/peak)
            dd_scalar = 1.0 - min(dd/0.30, 1.0)*0.75 if dd > 0 else 1.0

            position = min(base_pos * vol_scalar * dd_scalar * regime_scale, max_pos)

            if z < -entry_z and position > 0:
                prev_target = position; side = "long"; continue
            if z > entry_z and position > 0:
                prev_target = -position; side = "short"; continue

        # Hold existing position (no change to prev_target)

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


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_8h_data(cache, symbol, start, end):
    """Load 1H data from cache and resample to 8H."""
    df = cache.read("okx", symbol, "1h")
    if df is None or df.empty or len(df) < 100:
        return None
    # Strip timezone for comparison
    if df["timestamp"].dt.tz is not None:
        df["timestamp"] = df["timestamp"].dt.tz_localize(None)
    df8 = resample_ohlcv(df, "8h")
    mask = (df8["timestamp"] >= pd.Timestamp(start)) & (df8["timestamp"] < pd.Timestamp(end))
    out = df8[mask].reset_index(drop=True)
    return out if len(out) > 100 else None


# ---------------------------------------------------------------------------
# Main experiment
# ---------------------------------------------------------------------------

def main():
    t0 = time.time()
    cache = ParquetCache()
    results_dir = Path("sweep_results")
    results_dir.mkdir(exist_ok=True)

    n_coins = len(COINS)
    CAPITAL = 10_000.0 / n_coins  # per-coin capital

    # ==================================================================
    # PART 1: B0 Donchian with dynamic vs fixed slippage
    # ==================================================================
    print("=" * 70)
    print("PART 1: Dynamic slippage impact on Donchian B0")
    print("=" * 70)

    b0_fixed = {}; b0_dynamic = {}
    for coin in COINS:
        df = load_8h_data(cache, coin, "2025-07-01", "2026-04-01")
        if df is None:
            print(f"  {coin}: no holdout data, skip")
            continue
        r_fixed = run_donchian_b0(df, CAPITAL, n_coins, use_dynamic_slip=False)
        r_dynamic = run_donchian_b0(df, CAPITAL, n_coins, use_dynamic_slip=True)
        if r_fixed and r_dynamic:
            b0_fixed[coin] = r_fixed
            b0_dynamic[coin] = r_dynamic

    if b0_fixed:
        avg_fixed = np.mean([r["sharpe"] for r in b0_fixed.values()])
        avg_dynamic = np.mean([r["sharpe"] for r in b0_dynamic.values()])
        print(f"\n  B0 Holdout Sharpe (fixed slippage 15bps):  {avg_fixed:.3f}")
        print(f"  B0 Holdout Sharpe (dynamic slippage auto): {avg_dynamic:.3f}")
        print(f"  Delta: {avg_dynamic - avg_fixed:+.3f}")

        print(f"\n  {'Coin':<6} {'Fixed':>8} {'Dynamic':>8} {'Delta':>8}")
        print("  " + "-" * 34)
        for coin in COINS:
            if coin in b0_fixed:
                f = b0_fixed[coin]["sharpe"]; d = b0_dynamic[coin]["sharpe"]
                print(f"  {coin:<6} {f:>8.3f} {d:>8.3f} {d-f:>+8.3f}")

    # ==================================================================
    # PART 2: Mean Reversion parameter sweep
    # ==================================================================
    print("\n" + "=" * 70)
    print("PART 2: Mean Reversion Z-Score parameter sweep")
    print("=" * 70)

    # Parameter grid
    lookbacks = [12, 24, 48, 72, 96, 168, 252, 336]
    entry_zs = [1.5, 2.0, 2.5, 3.0]
    exit_zs = [0.0, 0.25, 0.5]
    stop_zs = [3.0, 3.5, 4.0]
    param_grid = list(product(lookbacks, entry_zs, exit_zs, stop_zs))
    # Filter: stop_z must be > entry_z
    param_grid = [(lb, ez, xz, sz) for lb, ez, xz, sz in param_grid if sz > ez]
    print(f"  Parameter combinations: {len(param_grid)}")

    # Load all data for all windows
    all_data = {}  # {coin: {window_name: df_8h}}
    for coin in COINS:
        all_data[coin] = {}
        for w in WINDOWS:
            df = load_8h_data(cache, coin, w["is_start"], w["val_end"])
            if df is not None:
                all_data[coin][w["name"]] = df
        # Holdout
        df = load_8h_data(cache, coin, "2021-01-01", "2026-04-01")
        if df is not None:
            all_data[coin]["full"] = df

    # Walk-forward sweep
    coin_best_params = {}  # {coin: (lb, ez, xz, sz)}
    coin_val_sharpes = {}  # {coin: {param: [w1_sharpe, w2_sharpe, w3_sharpe]}}

    for ci, coin in enumerate(COINS):
        if not all_data[coin]:
            print(f"  {coin}: no data, skip")
            continue

        print(f"\n  [{ci+1}/{n_coins}] {coin}: sweeping {len(param_grid)} params...", end=" ")
        t1 = time.time()

        param_results = {}  # {param_tuple: [val_sharpe_w1, w2, w3]}
        for w in WINDOWS:
            wname = w["name"]
            df_full = all_data[coin].get(wname)
            if df_full is None:
                continue

            val_start = pd.Timestamp(w["val_start"])
            val_end = pd.Timestamp(w["val_end"])
            is_end_idx = len(df_full[df_full["timestamp"] < val_start])

            for params in param_grid:
                lb, ez, xz, sz = params
                # IS phase
                df_is = df_full.iloc[:is_end_idx].reset_index(drop=True)
                r_is = run_meanrev(df_is, lb, ez, xz, sz, CAPITAL, n_coins)
                if r_is is None or r_is["sharpe"] <= 0:
                    if params not in param_results:
                        param_results[params] = []
                    param_results[params].append(None)
                    continue

                # Validation phase
                df_val = df_full[(df_full["timestamp"] >= val_start) &
                                 (df_full["timestamp"] < val_end)].reset_index(drop=True)
                if len(df_val) < 50:
                    if params not in param_results:
                        param_results[params] = []
                    param_results[params].append(None)
                    continue

                r_val = run_meanrev(df_val, lb, ez, xz, sz, CAPITAL, n_coins)
                val_sr = r_val["sharpe"] if r_val else None

                if params not in param_results:
                    param_results[params] = []
                param_results[params].append(val_sr)

        # Select best params: prefer all 3 windows positive, then lowest std
        best_param = None; best_score = -999
        for params, sharpes in param_results.items():
            valid = [s for s in sharpes if s is not None]
            if len(valid) < 2:
                continue
            n_pos = sum(1 for s in valid if s > 0)
            avg_sr = np.mean(valid)
            std_sr = np.std(valid)
            # Score: prioritize positive windows, then avg sharpe, penalize std
            score = n_pos * 10 + avg_sr - std_sr * 0.5
            if score > best_score:
                best_score = score
                best_param = params

        coin_best_params[coin] = best_param
        coin_val_sharpes[coin] = param_results

        if best_param:
            valid_sharpes = [s for s in param_results[best_param] if s is not None]
            print(f"best=({best_param[0]},{best_param[1]},{best_param[2]},{best_param[3]}) "
                  f"avg_val={np.mean(valid_sharpes):.3f} ({time.time()-t1:.1f}s)")
        else:
            print(f"no positive params ({time.time()-t1:.1f}s)")

    # Summary table
    print(f"\n  {'Coin':<6} {'Lookback':>8} {'Entry_Z':>8} {'Exit_Z':>7} {'Stop_Z':>7} {'Avg Val SR':>10}")
    print("  " + "-" * 52)
    for coin in COINS:
        p = coin_best_params.get(coin)
        if p and p in coin_val_sharpes.get(coin, {}):
            valid = [s for s in coin_val_sharpes[coin][p] if s is not None]
            avg = np.mean(valid) if valid else 0
            print(f"  {coin:<6} {p[0]:>8} {p[1]:>8.1f} {p[2]:>7.2f} {p[3]:>7.1f} {avg:>10.3f}")
        else:
            print(f"  {coin:<6} {'---':>8} {'---':>8} {'---':>7} {'---':>7} {'---':>10}")

    # ==================================================================
    # PART 3: Holdout + Complementarity analysis
    # ==================================================================
    print("\n" + "=" * 70)
    print("PART 3: Holdout & Complementarity analysis")
    print("=" * 70)

    mr_holdout = {}; don_holdout = {}
    mr_daily_rets = {}; don_daily_rets = {}

    for coin in COINS:
        # Donchian B0 on holdout
        df_ho = load_8h_data(cache, coin, "2025-07-01", "2026-04-01")
        if df_ho is None:
            continue
        r_don = run_donchian_b0(df_ho, CAPITAL, n_coins, use_dynamic_slip=True)
        if r_don:
            don_holdout[coin] = r_don
            eq = pd.Series(r_don["equities"])
            don_daily_rets[coin] = eq.pct_change().dropna().values

        # Mean reversion on holdout
        p = coin_best_params.get(coin)
        if p is None:
            continue
        r_mr = run_meanrev(df_ho, p[0], p[1], p[2], p[3], CAPITAL, n_coins,
                           use_dynamic_slip=True)
        if r_mr:
            mr_holdout[coin] = r_mr
            eq = pd.Series(r_mr["equities"])
            mr_daily_rets[coin] = eq.pct_change().dropna().values

    # Per-coin holdout comparison
    print(f"\n  {'Coin':<6} {'Don SR':>8} {'MR SR':>8} {'Don Ret%':>9} {'MR Ret%':>9} {'Corr':>6}")
    print("  " + "-" * 48)
    corrs = []
    for coin in COINS:
        don_sr = don_holdout[coin]["sharpe"] if coin in don_holdout else None
        mr_sr = mr_holdout[coin]["sharpe"] if coin in mr_holdout else None
        don_ret = don_holdout[coin]["return_pct"] if coin in don_holdout else None
        mr_ret = mr_holdout[coin]["return_pct"] if coin in mr_holdout else None

        # Correlation
        corr = None
        if coin in don_daily_rets and coin in mr_daily_rets:
            d = don_daily_rets[coin]; m = mr_daily_rets[coin]
            min_len = min(len(d), len(m))
            if min_len > 10 and np.std(d[:min_len]) > 0 and np.std(m[:min_len]) > 0:
                corr = float(np.corrcoef(d[:min_len], m[:min_len])[0, 1])
                if not np.isnan(corr):
                    corrs.append(corr)

        print(f"  {coin:<6} "
              f"{don_sr:>8.3f} " if don_sr is not None else f"  {coin:<6} {'---':>8} ",
              end="")
        print(f"{mr_sr:>8.3f} " if mr_sr is not None else f"{'---':>8} ", end="")
        print(f"{don_ret:>9.2f} " if don_ret is not None else f"{'---':>9} ", end="")
        print(f"{mr_ret:>9.2f} " if mr_ret is not None else f"{'---':>9} ", end="")
        print(f"{corr:>6.2f}" if corr is not None else f"{'---':>6}")

    if corrs:
        print(f"\n  Average Don-MR return correlation: {np.mean(corrs):.3f}")

    # ==================================================================
    # PART 4: Portfolio combinations
    # ==================================================================
    print("\n" + "=" * 70)
    print("PART 4: Portfolio combinations (Holdout)")
    print("=" * 70)

    # Build portfolio equity curves
    common_coins = [c for c in COINS if c in don_holdout and c in mr_holdout]
    if not common_coins:
        print("  No coins with both strategies, cannot build portfolios")
        return

    # Get aligned equity arrays
    port_don = np.zeros(0); port_mr = np.zeros(0)
    port_combo_eq = np.zeros(0); port_switch = np.zeros(0)

    # Simple approach: sum per-coin equities
    min_len = min(
        min(len(don_holdout[c]["equities"]) for c in common_coins),
        min(len(mr_holdout[c]["equities"]) for c in common_coins)
    )

    port_don_eq = np.zeros(min_len)
    port_mr_eq = np.zeros(min_len)
    for c in common_coins:
        port_don_eq += don_holdout[c]["equities"][:min_len]
        port_mr_eq += mr_holdout[c]["equities"][:min_len]

    # C: Equal weight combo (50/50)
    port_combo_eq = (port_don_eq + port_mr_eq) / 2

    # D: Regime switching (would need per-bar ADX, approximate with equal weight for now)
    # For proper regime switching, we'd need bar-level ADX. Use equal-weight as proxy.
    port_switch_eq = port_combo_eq  # placeholder

    # Compute portfolio metrics
    results_table = []
    for name, eq_arr in [("A) Donchian B0 only", port_don_eq),
                          ("B) MeanRev only", port_mr_eq),
                          ("C) 50/50 Equal Weight", port_combo_eq)]:
        eq_s = pd.Series(eq_arr)
        sr = sharpe_ratio(eq_s, PPY_8H)
        _, dd = max_drawdown(eq_s)
        ret = (eq_arr[-1] / eq_arr[0] - 1) * 100 if eq_arr[0] > 0 else 0
        results_table.append({"name": name, "sharpe": sr, "max_dd": dd, "return_pct": ret})

    print(f"\n  {'Portfolio':<25} {'Sharpe':>8} {'MaxDD%':>8} {'Return%':>9}")
    print("  " + "-" * 52)
    for r in results_table:
        print(f"  {r['name']:<25} {r['sharpe']:>8.3f} {r['max_dd']:>8.2f} {r['return_pct']:>9.2f}")

    # Daily return correlation of the two portfolio equity curves
    don_port_rets = pd.Series(port_don_eq).pct_change().dropna().values
    mr_port_rets = pd.Series(port_mr_eq).pct_change().dropna().values
    ml = min(len(don_port_rets), len(mr_port_rets))
    if ml > 10:
        port_corr = float(np.corrcoef(don_port_rets[:ml], mr_port_rets[:ml])[0, 1])
        print(f"\n  Portfolio-level daily return correlation: {port_corr:.3f}")

    # ==================================================================
    # Save results
    # ==================================================================
    save_data = {
        "b0_slippage_comparison": {
            "fixed": {c: {k: v for k, v in r.items() if k != "equities"}
                      for c, r in b0_fixed.items()},
            "dynamic": {c: {k: v for k, v in r.items() if k != "equities"}
                        for c, r in b0_dynamic.items()},
        },
        "meanrev_best_params": {c: list(p) if p else None
                                for c, p in coin_best_params.items()},
        "holdout_donchian": {c: {k: v for k, v in r.items() if k != "equities"}
                             for c, r in don_holdout.items()},
        "holdout_meanrev": {c: {k: v for k, v in r.items() if k != "equities"}
                            for c, r in mr_holdout.items()},
        "portfolio_results": results_table,
        "avg_correlation": float(np.mean(corrs)) if corrs else None,
    }
    out_path = results_dir / "meanrev_experiment.json"
    with open(out_path, "w") as f:
        json.dump(save_data, f, indent=2, default=str)
    print(f"\n  Results saved to {out_path}")

    # ==================================================================
    # PART 5: Record to RESEARCH_LOG.md
    # ==================================================================
    log_entry = f"""
## Mean Reversion Experiment ({pd.Timestamp.now().strftime('%Y-%m-%d')})

### Dynamic Slippage Model Impact on B0
- Fixed slippage (15bps): avg Holdout Sharpe = {np.mean([r['sharpe'] for r in b0_fixed.values()]):.3f}
- Dynamic slippage (auto): avg Holdout Sharpe = {np.mean([r['sharpe'] for r in b0_dynamic.values()]):.3f}
- Delta: {np.mean([r['sharpe'] for r in b0_dynamic.values()]) - np.mean([r['sharpe'] for r in b0_fixed.values()]):+.3f}

### Mean Reversion Best Parameters (per coin)
| Coin | Lookback | Entry Z | Exit Z | Stop Z | Avg Val Sharpe |
|------|----------|---------|--------|--------|----------------|
"""
    for coin in COINS:
        p = coin_best_params.get(coin)
        if p and p in coin_val_sharpes.get(coin, {}):
            valid = [s for s in coin_val_sharpes[coin][p] if s is not None]
            avg = np.mean(valid) if valid else 0
            log_entry += f"| {coin} | {p[0]} | {p[1]:.1f} | {p[2]:.2f} | {p[3]:.1f} | {avg:.3f} |\n"
        else:
            log_entry += f"| {coin} | --- | --- | --- | --- | --- |\n"

    log_entry += f"""
### Holdout Results
| Coin | Donchian SR | MeanRev SR | Don Ret% | MR Ret% | Correlation |
|------|-------------|------------|----------|---------|-------------|
"""
    for coin in COINS:
        ds = don_holdout.get(coin, {}).get("sharpe", None)
        ms = mr_holdout.get(coin, {}).get("sharpe", None)
        dr = don_holdout.get(coin, {}).get("return_pct", None)
        mr_ret = mr_holdout.get(coin, {}).get("return_pct", None)
        c_val = None
        if coin in don_daily_rets and coin in mr_daily_rets:
            d = don_daily_rets[coin]; m = mr_daily_rets[coin]
            ml2 = min(len(d), len(m))
            if ml2 > 10:
                c_val = float(np.corrcoef(d[:ml2], m[:ml2])[0, 1])
        ds_s = f"{ds:.3f}" if ds is not None else "---"
        ms_s = f"{ms:.3f}" if ms is not None else "---"
        dr_s = f"{dr:.2f}" if dr is not None else "---"
        mr_s = f"{mr_ret:.2f}" if mr_ret is not None else "---"
        cv_s = f"{c_val:.2f}" if c_val is not None else "---"
        log_entry += f"| {coin} | {ds_s} | {ms_s} | {dr_s} | {mr_s} | {cv_s} |\n"

    log_entry += f"""
### Portfolio Comparison (Holdout)
| Portfolio | Sharpe | MaxDD% | Return% |
|-----------|--------|--------|---------|
"""
    for r in results_table:
        log_entry += f"| {r['name']} | {r['sharpe']:.3f} | {r['max_dd']:.2f} | {r['return_pct']:.2f} |\n"

    if corrs:
        log_entry += f"\nAverage Donchian-MeanRev daily return correlation: {np.mean(corrs):.3f}\n"

    with open("RESEARCH_LOG.md", "a", encoding="utf-8") as f:
        f.write(log_entry)

    print(f"\n  Total time: {time.time()-t0:.1f}s")
    print("  Results appended to RESEARCH_LOG.md")


if __name__ == "__main__":
    main()
