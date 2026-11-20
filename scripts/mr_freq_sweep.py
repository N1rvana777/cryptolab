#!/usr/bin/env python3
"""Mean Reversion frequency sweep: find optimal frequency for MR strategy.

Tests MR at 1H, 2H, 4H, 8H with unified params (no per-coin optimization).
Walk-forward validation with holdout.
"""

import sys, os, time, json
from pathlib import Path
from itertools import product
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptolab.data.cache import ParquetCache
from cryptolab.backtest.metrics import sharpe_ratio, max_drawdown, PERIODS_PER_YEAR
from scripts.donchian_full_sweep import resample_ohlcv
from scripts.mean_reversion_experiment import compute_adx, compute_dynamic_slippage

COINS = ["BTC","ETH","LTC","TRX","BCH","DOT","ADA","LINK","XLM","XRP",
         "ETC","ALGO","ATOM","AAVE","SOL","ICP","UNI","FIL","AVAX","NEAR",
         "CRV","DOGE"]

FREQUENCIES = ["1h", "2h", "4h", "8h"]
PPY = {"1h": 8766, "2h": 4383, "4h": 2190, "8h": 1096}
BARS_PER_DAY = {"1h": 24, "2h": 12, "4h": 6, "8h": 3}

LOOKBACKS = [24, 36, 48, 72, 96, 120, 168, 252, 336, 504, 672]
ENTRY_ZS = [1.5, 2.0, 2.5, 3.0]
EXIT_ZS = [0.0, 0.25, 0.5]
# Stop Z = Entry Z + 1.0 (not independently optimized)

WINDOWS = [
    {"name": "W1", "is_start": "2021-01-01", "is_end": "2022-07-01",
     "val_start": "2022-07-01", "val_end": "2023-07-01"},
    {"name": "W2", "is_start": "2021-01-01", "is_end": "2023-07-01",
     "val_start": "2023-07-01", "val_end": "2024-07-01"},
    {"name": "W3", "is_start": "2021-01-01", "is_end": "2024-07-01",
     "val_start": "2024-07-01", "val_end": "2025-07-01"},
]
HOLDOUT = {"start": "2025-07-01", "end": "2026-04-01"}
FEE_BPS = 3.5


def run_mr_fast(df, lookback, entry_z, exit_z, stop_z, capital, n_coins, ppy,
                use_dynamic_slip=True):
    """Vectorized mean reversion backtest for any frequency."""
    n = len(df)
    warmup = max(lookback + 60, 100)
    if n < warmup + 20:
        return None

    closes = df["close"].values; opens = df["open"].values
    highs = df["high"].values; lows = df["low"].values
    volumes = df["volume"].values

    sma = pd.Series(closes).rolling(lookback, min_periods=lookback).mean().values
    std = pd.Series(closes).rolling(lookback, min_periods=lookback).std(ddof=1).values
    z_score = np.where(std > 1e-10, (closes - sma) / std, 0.0)

    adx = compute_adx(highs, lows, closes, 20)
    ret = np.zeros(n); ret[1:] = closes[1:]/closes[:-1] - 1
    ret_s = pd.Series(ret)
    vol_10d = ret_s.rolling(max(30, 10*3), min_periods=10).std().values
    vol_30d = ret_s.rolling(max(90, 30*3), min_periods=30).std().values

    vol_usd = volumes * closes
    adv_window = max(60, 20 * 3)  # at least 60 bars
    adv = pd.Series(vol_usd).rolling(adv_window, min_periods=3).sum().values / 20

    fee_rate = FEE_BPS / 10_000
    equity = capital; cash = equity; pos = 0.0; entry_px = 0.0
    peak = equity; equities = np.full(n, equity)
    n_trades = 0; wins = 0; closed = 0; prev_target = 0.0
    side = None
    start = warmup

    for i in range(start, n):
        o = opens[i]; c = closes[i]; z = z_score[i]

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

        # Inverted regime filter
        adx_val = adx[i] if not np.isnan(adx[i]) else 25.0
        if adx_val < 20: regime_scale = 1.0
        elif adx_val < 25: regime_scale = 0.5
        else: regime_scale = 0.0

        v10 = vol_10d[i]; v30 = vol_30d[i]
        if not np.isnan(v10) and not np.isnan(v30) and v30 > 0 and v10 < v30*0.7:
            regime_scale = 0.0

        if side == "long":
            if z >= -exit_z or z < -stop_z:
                prev_target = 0.0; side = None; continue
        elif side == "short":
            if z <= exit_z or z > stop_z:
                prev_target = 0.0; side = None; continue

        if side is None and regime_scale > 0:
            stop_z_dist = stop_z - entry_z
            s = std[i] if not np.isnan(std[i]) and std[i] > 0 else c * 0.02
            stop_dist_pct = max(stop_z_dist * s / c, 0.001) if c > 0 else 0.01
            risk_usd = equity * 0.02
            base_pos = (risk_usd / stop_dist_pct) * 3.0
            max_pos = equity * 3.0

            if not np.isnan(std[i]) and std[i] > 0 and c > 0:
                ann_vol = (std[i] / c) * np.sqrt(ppy)
                vol_sc = max(0.5, min(2.0, 0.15 / ann_vol)) if ann_vol > 0 else 1.0
            else:
                vol_sc = 1.0
            dd = max(0, 1.0 - equity/peak)
            dd_sc = 1.0 - min(dd/0.30, 1.0)*0.75 if dd > 0 else 1.0
            position = min(base_pos * vol_sc * dd_sc * regime_scale, max_pos)

            if z < -entry_z and position > 0:
                prev_target = position; side = "long"; continue
            if z > entry_z and position > 0:
                prev_target = -position; side = "short"; continue

    eq = pd.Series(equities[start:])
    if len(eq) < 10: return None
    sr = sharpe_ratio(eq, ppy); _, dd_pct = max_drawdown(eq)
    return {
        "sharpe": sr, "return_pct": (float(eq.iloc[-1]) - capital) / capital * 100,
        "max_dd_pct": dd_pct, "n_trades": n_trades,
        "win_rate": wins/closed*100 if closed > 0 else 0,
    }


def load_freq_data(cache, symbol, freq, start, end):
    """Load OHLCV data at specified frequency."""
    df = cache.read("okx", symbol, "1h")
    if df is None or df.empty: return None
    if df["timestamp"].dt.tz is not None:
        df["timestamp"] = df["timestamp"].dt.tz_localize(None)

    if freq == "1h":
        out = df
    else:
        out = resample_ohlcv(df, freq)

    mask = (out["timestamp"] >= pd.Timestamp(start)) & (out["timestamp"] < pd.Timestamp(end))
    result = out[mask].reset_index(drop=True)
    return result if len(result) > 100 else None


def main():
    t0 = time.time()
    cache = ParquetCache()
    n_coins = len(COINS)
    CAPITAL = 10_000.0 / n_coins

    print("=" * 70)
    print("Mean Reversion Frequency Sweep")
    print("=" * 70)

    # Build param grid
    param_grid = []
    for lb, ez, xz in product(LOOKBACKS, ENTRY_ZS, EXIT_ZS):
        sz = ez + 1.0  # stop_z = entry_z + 1.0
        param_grid.append((lb, ez, xz, sz))
    print(f"  Params per frequency: {len(param_grid)}")

    freq_results = {}

    for freq in FREQUENCIES:
        ppy = PPY[freq]
        print(f"\n  === {freq.upper()} (PPY={ppy}) ===")

        # Load all data for all windows
        all_data = {}  # {window_name: {coin: df}}
        for w in WINDOWS:
            all_data[w["name"]] = {}
            for coin in COINS:
                df = load_freq_data(cache, coin, freq, w["is_start"], w["val_end"])
                if df is not None:
                    all_data[w["name"]][coin] = df

        # For holdout
        ho_data = {}
        for coin in COINS:
            df = load_freq_data(cache, coin, freq, HOLDOUT["start"], HOLDOUT["end"])
            if df is not None:
                ho_data[coin] = df

        # Walk-forward sweep with UNIFIED params (all coins same params)
        param_val_sharpes = {}  # {param: [w1_avg_sharpe, w2, w3]}

        t1 = time.time()
        for pi, params in enumerate(param_grid):
            lb, ez, xz, sz = params
            val_sharpes = []

            for w in WINDOWS:
                wname = w["name"]
                val_start = pd.Timestamp(w["val_start"])

                coin_sharpes = []
                for coin in COINS:
                    df_full = all_data.get(wname, {}).get(coin)
                    if df_full is None: continue

                    # IS phase
                    is_end_idx = len(df_full[df_full["timestamp"] < val_start])
                    df_is = df_full.iloc[:is_end_idx].reset_index(drop=True)
                    r_is = run_mr_fast(df_is, lb, ez, xz, sz, CAPITAL, n_coins, ppy)
                    if r_is is None or r_is["sharpe"] <= 0:
                        coin_sharpes.append(None)
                        continue

                    # Validation
                    df_val = df_full[df_full["timestamp"] >= val_start].reset_index(drop=True)
                    if len(df_val) < 50:
                        coin_sharpes.append(None)
                        continue

                    r_val = run_mr_fast(df_val, lb, ez, xz, sz, CAPITAL, n_coins, ppy)
                    coin_sharpes.append(r_val["sharpe"] if r_val else None)

                # Equal-weight portfolio Sharpe across coins
                valid = [s for s in coin_sharpes if s is not None]
                if len(valid) >= 5:
                    val_sharpes.append(np.mean(valid))
                else:
                    val_sharpes.append(None)

            param_val_sharpes[params] = val_sharpes

            if (pi + 1) % 50 == 0:
                print(f"    {pi+1}/{len(param_grid)} params done ({time.time()-t1:.0f}s)")

        # Select best unified params: all 3 windows positive, highest avg
        best_param = None; best_score = -999
        for params, sharpes in param_val_sharpes.items():
            valid = [s for s in sharpes if s is not None]
            if len(valid) < 2: continue
            n_pos = sum(1 for s in valid if s > 0)
            avg_sr = np.mean(valid)
            score = n_pos * 10 + avg_sr
            if score > best_score:
                best_score = score
                best_param = params

        if best_param:
            valid_sharpes = [s for s in param_val_sharpes[best_param] if s is not None]
            avg_val = np.mean(valid_sharpes)
            print(f"    Best: lookback={best_param[0]}, entry_z={best_param[1]}, "
                  f"exit_z={best_param[2]}, stop_z={best_param[3]:.1f}")
            print(f"    Avg validation Sharpe: {avg_val:.3f}")

            # Holdout
            ho_sharpes = []
            ho_trades = 0
            ho_equities = []
            for coin in COINS:
                df_ho = ho_data.get(coin)
                if df_ho is None: continue
                r = run_mr_fast(df_ho, best_param[0], best_param[1], best_param[2],
                                best_param[3], CAPITAL, n_coins, ppy)
                if r:
                    ho_sharpes.append(r["sharpe"])
                    ho_trades += r["n_trades"]

            if ho_sharpes:
                ho_avg = np.mean(ho_sharpes)
                print(f"    Holdout avg Sharpe: {ho_avg:.3f}, trades: {ho_trades}")
            else:
                ho_avg = None

            freq_results[freq] = {
                "best_param": best_param,
                "avg_val_sharpe": avg_val,
                "holdout_sharpe": ho_avg,
                "holdout_trades": ho_trades,
                "n_valid_windows": len([s for s in param_val_sharpes[best_param] if s is not None]),
            }
        else:
            print(f"    No valid params found")
            freq_results[freq] = None

    # Summary table
    print(f"\n" + "=" * 70)
    print(f"  Summary")
    print(f"  {'Freq':<5} {'Lookback':>8} {'Entry Z':>8} {'Exit Z':>7} {'Avg Val SR':>10} {'HO SR':>8} {'HO Trades':>10}")
    print("  " + "-" * 62)
    for freq in FREQUENCIES:
        r = freq_results.get(freq)
        if r and r.get("best_param"):
            p = r["best_param"]
            print(f"  {freq:<5} {p[0]:>8} {p[1]:>8.1f} {p[2]:>7.2f} "
                  f"{r['avg_val_sharpe']:>10.3f} "
                  f"{r['holdout_sharpe']:>8.3f} " if r['holdout_sharpe'] is not None else f"  {freq:<5} {'---':>8}",
                  end="")
            print(f"{r['holdout_trades']:>10}" if r.get('holdout_trades') else "")
        else:
            print(f"  {freq:<5} {'--- no valid params ---'}")

    # Save + log
    save_data = {}
    for freq, r in freq_results.items():
        if r:
            save_data[freq] = {k: (list(v) if isinstance(v, tuple) else v) for k, v in r.items()}
    with open("sweep_results/mr_freq_sweep.json", "w") as f:
        json.dump(save_data, f, indent=2, default=str)

    log_entry = f"""
## Mean Reversion Frequency Sweep ({pd.Timestamp.now().strftime('%Y-%m-%d')})

### Unified params (all coins same), stop_z = entry_z + 1.0

| Freq | Lookback | Entry Z | Exit Z | Avg Val Sharpe | Holdout Sharpe | Trades |
|------|----------|---------|--------|----------------|----------------|--------|
"""
    for freq in FREQUENCIES:
        r = freq_results.get(freq)
        if r and r.get("best_param"):
            p = r["best_param"]
            ho = f"{r['holdout_sharpe']:.3f}" if r.get('holdout_sharpe') is not None else "---"
            log_entry += f"| {freq} | {p[0]} | {p[1]:.1f} | {p[2]:.2f} | {r['avg_val_sharpe']:.3f} | {ho} | {r.get('holdout_trades', '---')} |\n"
        else:
            log_entry += f"| {freq} | --- | --- | --- | --- | --- | --- |\n"

    # Analysis
    best_freq = max(
        [(f, r) for f, r in freq_results.items() if r and r.get("holdout_sharpe") is not None],
        key=lambda x: x[1]["holdout_sharpe"],
        default=(None, None)
    )
    if best_freq[0]:
        log_entry += f"\nBest frequency: {best_freq[0]} (Holdout Sharpe {best_freq[1]['holdout_sharpe']:.3f})\n"

    with open("RESEARCH_LOG.md", "a", encoding="utf-8") as f:
        f.write(log_entry)

    print(f"\n  Total time: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
