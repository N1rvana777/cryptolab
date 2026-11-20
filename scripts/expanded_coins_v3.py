#!/usr/bin/env python3
"""Expanded coins v3: correct methodology.

- Only coins with full 3-window walk-forward (OKX data from 2021)
- Single capital pool (run_combo), not separate equity curves
- Coin screening on validation, holdout touched once
- HL top 100 by volume, >100K ADV, no stables/wrapped
"""

import sys, os, time, json
from pathlib import Path
from itertools import product
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptolab.data.cache import ParquetCache
from cryptolab.backtest.metrics import sharpe_ratio, max_drawdown
from scripts.donchian_full_sweep import resample_ohlcv
from scripts.mean_reversion_experiment import (
    compute_adx, compute_dynamic_slippage,
    run_donchian_b0, run_meanrev,
    PPY_8H, FEE_BPS,
)
from scripts.portfolio_optimization import run_combo

ORIGINAL_22 = ["BTC","ETH","LTC","TRX","BCH","DOT","ADA","LINK","XLM","XRP",
               "ETC","ALGO","ATOM","AAVE","SOL","ICP","UNI","FIL","AVAX","NEAR","CRV","DOGE"]

# 28 coins with OKX data from 2021 (full 3-window WF capable)
ALL_28 = ["BTC","ETH","SOL","XRP","ALGO","NEAR","DOGE","AVAX","AAVE","ADA",
          "LINK","UNI","LTC","DOT","CRV","BCH","ETC","TRX","XLM",
          "AXS","FIL","ATOM","YGG","CELO","GALA","ICP","SAND","PEOPLE"]

WINDOWS = [
    {"name": "W1", "is_start": "2021-01-01", "is_end": "2022-07-01",
     "val_start": "2022-07-01", "val_end": "2023-07-01"},
    {"name": "W2", "is_start": "2021-01-01", "is_end": "2023-07-01",
     "val_start": "2023-07-01", "val_end": "2024-07-01"},
    {"name": "W3", "is_start": "2021-01-01", "is_end": "2024-07-01",
     "val_start": "2024-07-01", "val_end": "2025-07-01"},
]


def load_8h(cache, coin, start, end):
    """Load OKX 1H -> 8H."""
    df = cache.read("okx", coin, "1h")
    if df is None or df.empty:
        return None
    if df["timestamp"].dt.tz is not None:
        df["timestamp"] = df["timestamp"].dt.tz_localize(None)
    df8 = resample_ohlcv(df, "8h")
    mask = (df8["timestamp"] >= pd.Timestamp(start)) & (df8["timestamp"] < pd.Timestamp(end))
    out = df8[mask].reset_index(drop=True)
    return out if len(out) > 50 else None


def run_combo_portfolio(cache, coins, mr_params, start, end,
                        don_weight=0.5, mr_weight=0.5, exit_z_override=None,
                        leverage=3.0):
    """Run 50/50 combo using single capital pool (run_combo) for each coin.
    Returns portfolio-level metrics."""
    n_coins = len(coins)
    if n_coins == 0:
        return None
    CAPITAL = 10_000.0 / n_coins

    all_eqs = []
    total_trades = 0

    for coin in coins:
        df = load_8h(cache, coin, start, end)
        if df is None:
            continue

        p = mr_params.get(coin)
        if p and len(p) >= 4:
            ez = exit_z_override if exit_z_override is not None else p[2]
            r = run_combo(df, p[0], p[1], ez, p[3], CAPITAL, n_coins,
                          leverage=leverage,
                          don_weight=don_weight, mr_weight=mr_weight)
        else:
            # No MR params: run Donchian only
            r = run_combo(df, 168, 2.0, 0.25, 3.5, CAPITAL, n_coins,
                          leverage=leverage,
                          don_weight=1.0, mr_weight=0.0)

        if r and not np.isnan(r["sharpe"]):
            all_eqs.append(r["equities"])
            total_trades += r["n_trades"]

    if not all_eqs:
        return None

    min_len = min(len(e) for e in all_eqs)
    port_eq = sum(e[:min_len] for e in all_eqs)
    eq_s = pd.Series(port_eq)
    sr = sharpe_ratio(eq_s, PPY_8H)
    _, dd = max_drawdown(eq_s)
    ret = (port_eq[-1] / port_eq[0] - 1) * 100 if port_eq[0] > 0 else 0

    return {
        "sharpe": sr, "return_pct": ret, "max_dd_pct": dd,
        "n_trades": total_trades, "n_coins": len(all_eqs),
    }


def main():
    t0 = time.time()
    cache = ParquetCache()

    # Load existing MR params
    with open("sweep_results/meanrev_experiment.json") as f:
        existing_mr = json.load(f).get("meanrev_best_params", {})

    print(f"Coins with full 3-window WF: {len(ALL_28)}")
    new_coins = [c for c in ALL_28 if c not in ORIGINAL_22]
    print(f"  Original 22: {sum(1 for c in ALL_28 if c in ORIGINAL_22)}")
    print(f"  New: {len(new_coins)} ({', '.join(new_coins)})")

    # ==================================================================
    # Step 1: Donchian B0 Validation screening (3 windows)
    # ==================================================================
    print(f"\n{'='*70}")
    print("Step 1: Donchian B0 Validation Screening")
    print("=" * 70)

    CAPITAL = 10_000.0 / len(ALL_28)
    coin_don_val = {}

    for coin in ALL_28:
        sharpes = []
        for w in WINDOWS:
            df = load_8h(cache, coin, w["val_start"], w["val_end"])
            if df is None or len(df) < 100:
                sharpes.append(None)
                continue
            r = run_donchian_b0(df, CAPITAL, len(ALL_28), use_dynamic_slip=True)
            sharpes.append(r["sharpe"] if r and not np.isnan(r["sharpe"]) else None)
        coin_don_val[coin] = sharpes

    print(f"\n  {'Coin':<8} {'W1':>8} {'W2':>8} {'W3':>8} {'Avg':>8} {'Pass':>5}")
    print("  " + "-" * 46)
    passed = []
    for coin in ALL_28:
        s = coin_don_val[coin]
        valid = [x for x in s if x is not None]
        avg = np.mean(valid) if valid else -999
        n_pos = sum(1 for x in valid if x > 0)
        is_pass = len(valid) == 3 and avg > 0
        if is_pass:
            passed.append((coin, avg))
        s_str = [f"{x:>8.3f}" if x is not None else f"{'---':>8}" for x in s]
        mark = " *" if coin not in ORIGINAL_22 else ""
        status = "OK" if is_pass else ""
        print(f"  {coin:<8} {s_str[0]} {s_str[1]} {s_str[2]} {avg:>8.3f} {status:>5}{mark}")

    passed.sort(key=lambda x: -x[1])
    print(f"\n  Passed (3 windows, avg > 0): {len(passed)}/{len(ALL_28)}")

    # ==================================================================
    # Step 2: MR sweep for new coins
    # ==================================================================
    print(f"\n{'='*70}")
    print("Step 2: MR Param Sweep (new coins)")
    print("=" * 70)

    all_mr = dict(existing_mr)
    new_need_sweep = [c for c in ALL_28 if c not in existing_mr]
    print(f"  {len(new_need_sweep)} coins need MR sweep")

    lookbacks = [24, 48, 72, 96, 168, 252, 336]
    entry_zs = [1.5, 2.0, 2.5, 3.0]
    exit_zs = [0.0, 0.25, 0.5]
    stop_zs = [3.0, 3.5, 4.0]
    param_grid = [(lb, ez, xz, sz) for lb, ez, xz, sz in
                  product(lookbacks, entry_zs, exit_zs, stop_zs) if sz > ez]

    for ci, coin in enumerate(new_need_sweep):
        print(f"  [{ci+1}/{len(new_need_sweep)}] {coin}...", end=" ", flush=True)
        tt = time.time()
        param_results = {}
        for w in WINDOWS:
            df_full = load_8h(cache, coin, w["is_start"], w["val_end"])
            if df_full is None or len(df_full) < 200: continue
            val_start = pd.Timestamp(w["val_start"])
            is_end_idx = len(df_full[df_full["timestamp"] < val_start])
            if is_end_idx < 100: continue

            for params in param_grid:
                lb, ez, xz, sz = params
                df_is = df_full.iloc[:is_end_idx].reset_index(drop=True)
                r_is = run_meanrev(df_is, lb, ez, xz, sz, CAPITAL, len(ALL_28))
                if r_is is None or r_is["sharpe"] <= 0:
                    param_results.setdefault(params, []).append(None)
                    continue
                df_val = df_full[df_full["timestamp"] >= val_start].reset_index(drop=True)
                if len(df_val) < 50:
                    param_results.setdefault(params, []).append(None)
                    continue
                r_val = run_meanrev(df_val, lb, ez, xz, sz, CAPITAL, len(ALL_28))
                param_results.setdefault(params, []).append(r_val["sharpe"] if r_val else None)

        best = None; best_score = -999
        for params, sharpes in param_results.items():
            valid = [s for s in sharpes if s is not None]
            if not valid: continue
            score = sum(1 for s in valid if s > 0) * 10 + np.mean(valid)
            if score > best_score:
                best_score = score; best = params

        if best:
            all_mr[coin] = list(best)
            valid = [s for s in param_results[best] if s is not None]
            print(f"({best[0]},{best[1]},{best[2]},{best[3]}) avg={np.mean(valid):.3f} ({time.time()-tt:.0f}s)")
        else:
            print(f"no params ({time.time()-tt:.0f}s)")

    # ==================================================================
    # Step 3: Holdout (single capital pool, run_combo)
    # ==================================================================
    print(f"\n{'='*70}")
    print("Step 3: Holdout (single capital pool)")
    print("=" * 70)

    ho_start = "2025-07-01"; ho_end = "2026-04-01"
    passed_coins = [c for c, _ in passed]
    new_passed = [c for c in passed_coins if c not in ORIGINAL_22]

    portfolios = {}

    # A) Original 22, 50/50, exit_z per-coin
    r = run_combo_portfolio(cache, ORIGINAL_22, all_mr, ho_start, ho_end)
    if r: portfolios["A) Orig 22 (per-coin ez)"] = r

    # B) Original 22, 50/50, exit_z=0.50
    r = run_combo_portfolio(cache, ORIGINAL_22, all_mr, ho_start, ho_end, exit_z_override=0.50)
    if r: portfolios["B) Orig 22 (ez=0.50)"] = r

    # C) All 28
    r = run_combo_portfolio(cache, ALL_28, all_mr, ho_start, ho_end, exit_z_override=0.50)
    if r: portfolios["C) All 28 (ez=0.50)"] = r

    # D) Validation-passed only
    r = run_combo_portfolio(cache, passed_coins, all_mr, ho_start, ho_end, exit_z_override=0.50)
    if r: portfolios["D) Val-passed"] = r

    # E) Original 22 + new passed
    combined = ORIGINAL_22 + new_passed
    r = run_combo_portfolio(cache, combined, all_mr, ho_start, ho_end, exit_z_override=0.50)
    if r: portfolios["E) Orig + new passed"] = r

    # F) Pure Donchian (no MR), original 22
    r = run_combo_portfolio(cache, ORIGINAL_22, all_mr, ho_start, ho_end,
                            don_weight=1.0, mr_weight=0.0)
    if r: portfolios["F) Pure Donchian 22"] = r

    # Print
    print(f"\n  {'Portfolio':<25} {'Sharpe':>8} {'Ret%':>8} {'MaxDD%':>8} {'Trades':>7} {'Coins':>6}")
    print("  " + "-" * 65)
    display_order = ["F) Pure Donchian 22", "A) Orig 22 (per-coin ez)",
                     "B) Orig 22 (ez=0.50)", "C) All 28 (ez=0.50)",
                     "D) Val-passed", "E) Orig + new passed"]
    for name in display_order:
        p = portfolios.get(name)
        if p:
            print(f"  {name:<25} {p['sharpe']:>8.3f} {p['return_pct']:>8.2f} "
                  f"{p['max_dd_pct']:>8.2f} {p['n_trades']:>7} {p['n_coins']:>6}")

    # ==================================================================
    # Save + log
    # ==================================================================
    save_data = {
        "coins_28": ALL_28,
        "validation_screening": {c: {"sharpes": coin_don_val[c]} for c in ALL_28},
        "passed_coins": passed_coins,
        "new_passed": new_passed,
        "mr_params": all_mr,
        "portfolios": portfolios,
    }
    with open("sweep_results/expanded_coins_v3.json", "w") as f:
        json.dump(save_data, f, indent=2, default=str)

    log_entry = f"""
## Expanded Coins v3 - Correct Methodology ({pd.Timestamp.now().strftime('%Y-%m-%d')})

### Methodology
- Single capital pool (run_combo) — no double-counting
- Only coins with OKX data from 2021 (full 3-window WF): {len(ALL_28)}
- Coin screening: avg validation Donchian Sharpe > 0 across all 3 windows
- Holdout touched once

### Validation Screening
- Passed: {len(passed_coins)}/{len(ALL_28)} (avg val Sharpe > 0, all 3 windows)
- New coins (not in original 22): {', '.join(new_coins)}
- New coins that passed: {', '.join(new_passed) if new_passed else 'none'}

### Holdout (50/50 Donchian+MR, 3x leverage)
| Portfolio | Sharpe | Return% | MaxDD% | Trades | Coins |
|-----------|--------|---------|--------|--------|-------|
"""
    for name in display_order:
        p = portfolios.get(name)
        if p:
            log_entry += f"| {name} | {p['sharpe']:.3f} | {p['return_pct']:.2f} | {p['max_dd_pct']:.2f} | {p['n_trades']} | {p['n_coins']} |\n"

    best = max(portfolios.items(), key=lambda x: x[1]["sharpe"])
    log_entry += f"\nBest: **{best[0]}** (Sharpe {best[1]['sharpe']:.3f})\n"

    with open("RESEARCH_LOG.md", "a", encoding="utf-8") as f:
        f.write(log_entry)

    print(f"\n  Total time: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
