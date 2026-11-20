#!/usr/bin/env python3
"""Part 3: Position management diagnostic.

Test 4 sizing methods x 3 strategy combos on W1 OOS (2023).
Uses best config from Part 2: 8H + 1D filter, Set A.
"""

import sys, os, time, json
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptolab.data.cache import ParquetCache
from cryptolab.backtest.metrics import sharpe_ratio, max_drawdown
from scripts.donchian_full_sweep import resample_ohlcv
from scripts.multisignal_trend import (
    load_data, compute_signals, compute_1d_filter, SIGNAL_SETS, ALL_28, FEE_BPS
)
from scripts.mean_reversion_experiment import compute_dynamic_slippage, compute_adx
from scripts.cross_sectional_momentum import run_xsmom

PPY = 1096


def run_trend_with_sizing(coin_dfs, signal_set, thresh, tvol, use_filter,
                          sizing_method, capital=10000.0, leverage=3.0,
                          trading_start="2023-01-01"):
    """Run multi-signal trend with different position sizing methods.

    sizing_method: "equal", "invvol", "invvol_dd", "invvol_regime"
    """
    coins = list(coin_dfs.keys())
    n_coins = len(coins)
    if n_coins < 5:
        return None

    fee_rate = FEE_BPS / 10_000
    per_coin = capital / n_coins

    all_eqs = []
    total_trades = 0

    for coin in coins:
        df = coin_dfs[coin]
        n = len(df)
        closes = df["close"].values
        opens = df["open"].values
        volumes = df["volume"].values
        highs = df["high"].values
        lows = df["low"].values

        sigs = compute_signals(closes, signal_set)
        composite = np.nanmean(sigs, axis=1)

        if use_filter:
            filt = compute_1d_filter(closes, "8h")
        else:
            filt = np.ones(n)

        rets = np.zeros(n)
        rets[1:] = closes[1:] / closes[:-1] - 1
        roll_vol = pd.Series(rets).rolling(60, min_periods=20).std().values
        ann_vol = roll_vol * np.sqrt(PPY)

        # ADX for regime method
        adx_arr = compute_adx(highs, lows, closes, 20)

        vol_usd = volumes * closes
        adv = pd.Series(vol_usd).rolling(60, min_periods=3).sum().values / 20

        warmup = 0
        for i in range(n):
            if not np.isnan(composite[i]):
                warmup = i
                break

        ts_arr = df["timestamp"].values
        trade_start = warmup + 1
        for i in range(n):
            if ts_arr[i] >= np.datetime64(trading_start):
                trade_start = max(trade_start, i)
                break

        equity = per_coin; cash = equity; pos = 0.0; entry_px = 0.0
        peak = equity; equities = np.full(n, equity)
        n_tr = 0; prev_target = 0.0

        for i in range(warmup + 1, n):
            o = opens[i]; c = closes[i]; sig = composite[i - 1]

            trade_size = abs(prev_target - pos)
            if trade_size > max(5.0, abs(prev_target) * 0.03):
                fee = trade_size * fee_rate
                slip = compute_dynamic_slippage(trade_size, adv[i] if not np.isnan(adv[i]) else 1e9)
                if abs(pos) > 0.01 and entry_px > 0:
                    pnl = abs(pos) * ((o - entry_px) / entry_px if pos > 0 else (entry_px - o) / entry_px)
                    cash += pnl
                cash -= fee + slip; n_tr += 1
                pos = prev_target
                entry_px = o if abs(pos) > 0.01 else 0.0

            unrealized = 0.0
            if abs(pos) > 0.01 and entry_px > 0:
                unrealized = abs(pos) * ((c - entry_px) / entry_px if pos > 0 else (entry_px - c) / entry_px)
            equity = cash + unrealized; peak = max(peak, equity); equities[i] = equity

            if i < trade_start or np.isnan(sig):
                prev_target = 0.0; continue

            d_filt = filt[i - 1]
            av = ann_vol[i - 1] if not np.isnan(ann_vol[i - 1]) and ann_vol[i - 1] > 0 else 1.0
            max_pos = equity * leverage

            # Position sizing by method
            if sizing_method == "equal":
                base_size = equity * leverage * abs(sig)
            elif sizing_method in ("invvol", "invvol_dd", "invvol_regime"):
                vol_sc = min(2.0, max(0.25, tvol / av))
                base_size = equity * leverage * vol_sc * abs(sig)
            else:
                base_size = equity * leverage * abs(sig)

            # DD scaling (methods C and D)
            if sizing_method in ("invvol_dd", "invvol_regime"):
                dd = max(0, 1.0 - equity / peak)
                if dd > 0.15:
                    dd_sc = 0.25
                elif dd > 0.05:
                    dd_sc = 1.0 - (dd - 0.05) / 0.10 * 0.75
                else:
                    dd_sc = 1.0
                base_size *= dd_sc

            # Regime filter (method D only)
            if sizing_method == "invvol_regime":
                adx_val = adx_arr[i - 1] if not np.isnan(adx_arr[i - 1]) else 25.0
                if adx_val < 20:
                    base_size *= 0.3  # reduce in ranging
                elif adx_val < 25:
                    base_size *= 0.7

            base_size = min(base_size, max_pos)

            if sig > thresh:
                if use_filter and d_filt < 0:
                    prev_target = 0.0
                else:
                    prev_target = base_size
            elif sig < -thresh:
                if use_filter and d_filt > 0:
                    prev_target = 0.0
                else:
                    prev_target = -base_size
            elif abs(sig) < 0.1:
                prev_target = 0.0

        eq_slice = equities[trade_start:]
        all_eqs.append(eq_slice)
        total_trades += n_tr

    min_len = min(len(e) for e in all_eqs)
    port_eq = sum(e[:min_len] for e in all_eqs)
    port_eq = port_eq / port_eq[0] * capital

    eq_s = pd.Series(port_eq)
    sr = sharpe_ratio(eq_s, PPY)
    _, dd = max_drawdown(eq_s)
    ret = (port_eq[-1] / port_eq[0] - 1) * 100

    return {
        "sharpe": sr, "return_pct": ret, "max_dd_pct": dd,
        "n_trades": total_trades, "equities": port_eq,
    }


def main():
    t0 = time.time()
    cache = ParquetCache()

    # Load W1 OOS data (2023) with warmup
    print("Loading data...")
    trend_dfs = {}
    xsmom_dfs = {}
    for coin in ALL_28:
        df = load_data(cache, coin, "8h", "2019-01-01", "2024-01-01")
        if df is not None:
            trend_dfs[coin] = df
        df_oos = load_data(cache, coin, "8h", "2022-01-01", "2024-01-01")
        if df_oos is not None:
            xsmom_dfs[coin] = df_oos

    print(f"  Trend coins: {len(trend_dfs)}, XSMom coins: {len(xsmom_dfs)}")

    sig_set = SIGNAL_SETS["8h"]["A"]
    thresh = 0.3
    tvol = 0.15
    use_filter = True  # 1D filter (best from Part 2)

    sizing_methods = ["equal", "invvol", "invvol_dd", "invvol_regime"]
    sizing_labels = {
        "equal": "A) Equal weight",
        "invvol": "B) Inv volatility",
        "invvol_dd": "C) InvVol + DD scaling",
        "invvol_regime": "D) InvVol + DD + Regime",
    }

    # ================================================================
    # Run diagnostics
    # ================================================================
    print(f"\n{'='*70}")
    print("Part 3: Position Management Diagnostic (W1 OOS = 2023)")
    print(f"{'='*70}")

    results = {}

    for method in sizing_methods:
        label_base = sizing_labels[method]

        # 1) Pure trend
        r_trend = run_trend_with_sizing(
            trend_dfs, sig_set, thresh, tvol, use_filter,
            method, trading_start="2023-01-01")

        # 2) Pure XSMom
        r_xsmom = run_xsmom(xsmom_dfs, 36, 5, 21, False, capital=10000.0)
        # Extract 2023 portion
        xs_eq = r_xsmom["equities"] if r_xsmom else None

        # 3) Trend 60% + XSMom 40%
        combo_eq = None
        if r_trend and xs_eq is not None:
            t_eq = r_trend["equities"]
            x_eq = xs_eq
            ml = min(len(t_eq), len(x_eq))
            t_r = t_eq[:ml] / t_eq[0]
            x_r = x_eq[:ml] / x_eq[0]
            combo = (0.6 * t_r + 0.4 * x_r) * 10000
            combo_s = pd.Series(combo)
            combo_sr = sharpe_ratio(combo_s, PPY)
            _, combo_dd = max_drawdown(combo_s)
            combo_ret = (combo[-1] / combo[0] - 1) * 100
            combo_tr = (r_trend["n_trades"] if r_trend else 0) + (r_xsmom["n_trades"] if r_xsmom else 0)

        for strat_label, r in [
            ("Trend only", r_trend),
            ("XSMom only", r_xsmom),
        ]:
            key = f"{label_base} | {strat_label}"
            if r:
                results[key] = {
                    "sharpe": r["sharpe"], "return_pct": r["return_pct"],
                    "max_dd_pct": r["max_dd_pct"], "n_trades": r["n_trades"],
                }

        if combo_eq is not None or (r_trend and xs_eq is not None):
            key = f"{label_base} | Trend60+XS40"
            results[key] = {
                "sharpe": combo_sr, "return_pct": combo_ret,
                "max_dd_pct": combo_dd, "n_trades": combo_tr,
            }

    # Print
    print(f"\n  {'Sizing | Strategy':<40} {'Sharpe':>8} {'Ret%':>8} {'MaxDD%':>8} {'Trades':>7}")
    print("  " + "-" * 73)
    for key in sorted(results.keys()):
        r = results[key]
        print(f"  {key:<40} {r['sharpe']:>8.3f} {r['return_pct']:>8.2f} {r['max_dd_pct']:>8.2f} {r['n_trades']:>7}")

    # Save
    with open("sweep_results/position_diagnostic.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    log = f"\n### Part 3: Position Management Diagnostic (W1 OOS = 2023)\n\n"
    log += "| Sizing | Strategy | Sharpe | Return% | MaxDD% | Trades |\n"
    log += "|--------|----------|--------|---------|--------|--------|\n"
    for key, r in sorted(results.items()):
        parts = key.split(" | ")
        log += f"| {parts[0]} | {parts[1]} | {r['sharpe']:.3f} | {r['return_pct']:.2f} | {r['max_dd_pct']:.2f} | {r['n_trades']} |\n"

    with open("RESEARCH_LOG.md", "a", encoding="utf-8") as f:
        f.write(log)

    print(f"\n  Total: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
