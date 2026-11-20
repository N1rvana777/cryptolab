#!/usr/bin/env python3
"""Expanded coin experiment v2: fix data snooping bias.

Key fix: coin selection based on VALIDATION Sharpe, not holdout.
- Step 1: Run Donchian B0 on all coins across 3 validation windows
- Step 2: Select coins with avg validation Sharpe > 0
- Step 3: MR param sweep on selected coins (validation)
- Step 4: Holdout test (touched ONCE)
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

ORIGINAL_22 = ["BTC","ETH","LTC","TRX","BCH","DOT","ADA","LINK","XLM","XRP",
               "ETC","ALGO","ATOM","AAVE","SOL","ICP","UNI","FIL","AVAX","NEAR","CRV","DOGE"]

WINDOWS = [
    {"name": "W1", "val_start": "2022-07-01", "val_end": "2023-07-01"},
    {"name": "W2", "val_start": "2023-07-01", "val_end": "2024-07-01"},
    {"name": "W3", "val_start": "2024-07-01", "val_end": "2025-07-01"},
]


def load_8h(cache, coin, start, end):
    """Load OKX 1H -> 8H. Falls back to HL 4H -> 8H."""
    # OKX first
    okx_map = {'kPEPE':'PEPE','kBONK':'BONK','kSHIB':'SHIB','kFLOKI':'FLOKI','kLUNC':'LUNC'}
    okx_name = okx_map.get(coin, coin)
    df = cache.read("okx", okx_name, "1h")
    if df is not None and not df.empty:
        if df["timestamp"].dt.tz is not None:
            df["timestamp"] = df["timestamp"].dt.tz_localize(None)
        df8 = resample_ohlcv(df, "8h")
        mask = (df8["timestamp"] >= pd.Timestamp(start)) & (df8["timestamp"] < pd.Timestamp(end))
        out = df8[mask].reset_index(drop=True)
        if len(out) > 50:
            return out

    # HL 4H -> 8H
    df4 = cache.read("hl", coin, "4h")
    if df4 is not None and not df4.empty:
        if df4["timestamp"].dt.tz is not None:
            df4["timestamp"] = df4["timestamp"].dt.tz_localize(None)
        df8 = resample_ohlcv(df4, "8h")
        mask = (df8["timestamp"] >= pd.Timestamp(start)) & (df8["timestamp"] < pd.Timestamp(end))
        out = df8[mask].reset_index(drop=True)
        if len(out) > 50:
            return out
    return None


def build_portfolio(cache, coins, mr_params, start, end, exit_z_override=0.50):
    """Build 50/50 portfolio for a date range."""
    n_coins = len(coins)
    if n_coins == 0: return None
    CAPITAL = 10_000.0 / n_coins
    don_eqs = []; mr_eqs = []; don_tr = 0; mr_tr = 0

    for coin in coins:
        df = load_8h(cache, coin, start, end)
        if df is None: continue

        r = run_donchian_b0(df, CAPITAL, n_coins, use_dynamic_slip=True)
        if r and not np.isnan(r["sharpe"]):
            don_eqs.append(r["equities"])
            don_tr += r["n_trades"]

        p = mr_params.get(coin)
        if p and len(p) >= 4:
            r = run_meanrev(df, p[0], p[1], exit_z_override, p[3], CAPITAL, n_coins)
            if r and not np.isnan(r["sharpe"]):
                mr_eqs.append(r["equities"])
                mr_tr += r["n_trades"]

    if not don_eqs and not mr_eqs:
        return None

    min_len = min(len(e) for e in don_eqs + mr_eqs)
    don_total = sum(e[:min_len] for e in don_eqs) if don_eqs else np.zeros(min_len)
    mr_total = sum(e[:min_len] for e in mr_eqs) if mr_eqs else np.zeros(min_len)
    combo = (don_total + mr_total) / 2

    eq_s = pd.Series(combo)
    sr = sharpe_ratio(eq_s, PPY_8H)
    _, dd = max_drawdown(eq_s)
    ret = (combo[-1] / combo[0] - 1) * 100 if combo[0] > 0 else 0
    return {"sharpe": sr, "return_pct": ret, "max_dd_pct": dd,
            "n_trades": don_tr + mr_tr, "n_coins": max(len(don_eqs), len(mr_eqs))}


def main():
    t0 = time.time()
    cache = ParquetCache()

    with open("sweep_results/coin_catalog.json") as f:
        catalog = json.load(f)
    with open("sweep_results/meanrev_experiment.json") as f:
        existing_mr = json.load(f).get("meanrev_best_params", {})

    usable = [c for c in catalog if c["status"] in ("HAS_OKX", "HAS_HL")]
    all_coins = [c["coin"] for c in usable]
    print(f"Total usable coins: {len(all_coins)}")

    # ==================================================================
    # Step 1: Donchian B0 on VALIDATION windows (NOT holdout)
    # ==================================================================
    print(f"\n{'='*70}")
    print("Step 1: Donchian B0 Validation (coin screening)")
    print("=" * 70)

    coin_val_sharpes = {}  # {coin: [w1_sr, w2_sr, w3_sr]}
    CAPITAL = 10_000.0 / 22  # normalize

    for ci, coin in enumerate(all_coins):
        sharpes = []
        for w in WINDOWS:
            df = load_8h(cache, coin, w["val_start"], w["val_end"])
            if df is None or len(df) < 100:
                sharpes.append(None)
                continue
            r = run_donchian_b0(df, CAPITAL, 22, use_dynamic_slip=True)
            sharpes.append(r["sharpe"] if r and not np.isnan(r["sharpe"]) else None)
        coin_val_sharpes[coin] = sharpes
        if (ci + 1) % 20 == 0:
            print(f"  {ci+1}/{len(all_coins)} done...", flush=True)

    # Select coins with avg validation Sharpe > 0
    selected = []
    for coin, sharpes in coin_val_sharpes.items():
        valid = [s for s in sharpes if s is not None]
        if not valid:
            continue
        avg = np.mean(valid)
        if avg > 0:
            selected.append((coin, avg, len(valid)))

    selected.sort(key=lambda x: -x[1])
    print(f"\n  Coins with avg validation Donchian Sharpe > 0: {len(selected)}/{len(all_coins)}")
    print(f"  {'Coin':<10} {'Avg Val SR':>10} {'Windows':>8} {'Original':>9}")
    print("  " + "-" * 42)
    for coin, avg, nw in selected:
        orig = "yes" if coin in ORIGINAL_22 else ""
        print(f"  {coin:<10} {avg:>10.3f} {nw:>8} {orig:>9}")

    selected_coins = [c for c, _, _ in selected]

    # ==================================================================
    # Step 2: MR sweep for new selected coins
    # ==================================================================
    print(f"\n{'='*70}")
    print("Step 2: MR Param Sweep (new selected coins)")
    print("=" * 70)

    all_mr_params = dict(existing_mr)
    new_to_sweep = [c for c in selected_coins if c not in existing_mr]
    print(f"  {len(new_to_sweep)} new coins need MR sweep")

    lookbacks = [24, 48, 72, 96, 168, 252, 336]
    entry_zs = [1.5, 2.0, 2.5, 3.0]
    exit_zs = [0.0, 0.25, 0.5]
    stop_zs = [3.0, 3.5, 4.0]
    param_grid = [(lb, ez, xz, sz) for lb, ez, xz, sz in
                  product(lookbacks, entry_zs, exit_zs, stop_zs) if sz > ez]

    for ci, coin in enumerate(new_to_sweep):
        print(f"  [{ci+1}/{len(new_to_sweep)}] {coin}...", end=" ", flush=True)
        t1 = time.time()

        param_results = {}
        for w in WINDOWS:
            is_end = w["val_start"]
            df_full = load_8h(cache, coin, "2021-01-01", w["val_end"])
            if df_full is None or len(df_full) < 200:
                continue
            val_start = pd.Timestamp(w["val_start"])
            is_end_idx = len(df_full[df_full["timestamp"] < val_start])
            if is_end_idx < 100:
                continue

            for params in param_grid:
                lb, ez, xz, sz = params
                df_is = df_full.iloc[:is_end_idx].reset_index(drop=True)
                r_is = run_meanrev(df_is, lb, ez, xz, sz, CAPITAL, 22)
                if r_is is None or r_is["sharpe"] <= 0:
                    param_results.setdefault(params, []).append(None)
                    continue
                df_val = df_full[df_full["timestamp"] >= val_start].reset_index(drop=True)
                if len(df_val) < 50:
                    param_results.setdefault(params, []).append(None)
                    continue
                r_val = run_meanrev(df_val, lb, ez, xz, sz, CAPITAL, 22)
                param_results.setdefault(params, []).append(r_val["sharpe"] if r_val else None)

        best = None; best_score = -999
        for params, sharpes in param_results.items():
            valid = [s for s in sharpes if s is not None]
            if not valid: continue
            score = sum(1 for s in valid if s > 0) * 10 + np.mean(valid)
            if score > best_score:
                best_score = score; best = params

        if best:
            all_mr_params[coin] = list(best)
            valid = [s for s in param_results[best] if s is not None]
            print(f"({best[0]},{best[1]},{best[2]},{best[3]}) avg={np.mean(valid):.3f} ({time.time()-t1:.0f}s)")
        else:
            print(f"no params ({time.time()-t1:.0f}s)")

    # ==================================================================
    # Step 3: Holdout comparison (TOUCHED ONCE)
    # ==================================================================
    print(f"\n{'='*70}")
    print("Step 3: Holdout Comparison")
    print("=" * 70)

    ho_start = "2025-07-01"; ho_end = "2026-04-01"

    # A) Original 22
    r_a = build_portfolio(cache, ORIGINAL_22, all_mr_params, ho_start, ho_end)

    # B) All validation-selected coins
    r_b = build_portfolio(cache, selected_coins, all_mr_params, ho_start, ho_end)

    # C) Only new coins (selected - original)
    new_selected = [c for c in selected_coins if c not in ORIGINAL_22]
    r_c = build_portfolio(cache, new_selected, all_mr_params, ho_start, ho_end) if new_selected else None

    # D) Original + new selected
    combined = ORIGINAL_22 + new_selected
    r_d = build_portfolio(cache, combined, all_mr_params, ho_start, ho_end)

    # E) Top N by validation Sharpe (where N = 30)
    top30 = selected_coins[:30]
    r_e = build_portfolio(cache, top30, all_mr_params, ho_start, ho_end)

    portfolios = {}
    if r_a: portfolios["A) Original 22"] = r_a
    if r_b: portfolios["B) Val-selected all"] = r_b
    if r_c: portfolios["C) New selected only"] = r_c
    if r_d: portfolios["D) Orig + new selected"] = r_d
    if r_e: portfolios["E) Top 30 by val SR"] = r_e

    print(f"\n  {'Portfolio':<25} {'Sharpe':>8} {'Ret%':>8} {'MaxDD%':>8} {'Trades':>7} {'Coins':>6}")
    print("  " + "-" * 65)
    for name in ["A) Original 22", "B) Val-selected all", "C) New selected only",
                  "D) Orig + new selected", "E) Top 30 by val SR"]:
        p = portfolios.get(name)
        if p:
            print(f"  {name:<25} {p['sharpe']:>8.3f} {p['return_pct']:>8.2f} "
                  f"{p['max_dd_pct']:>8.2f} {p['n_trades']:>7} {p['n_coins']:>6}")

    # ==================================================================
    # Save + RESEARCH_LOG
    # ==================================================================
    save_data = {
        "coin_screening": {c: {"avg_val_sr": avg, "n_windows": nw}
                           for c, avg, nw in selected},
        "selected_coins": selected_coins,
        "new_selected": new_selected,
        "mr_params": {k: v for k, v in all_mr_params.items()},
        "portfolios": portfolios,
    }
    with open("sweep_results/expanded_coins_v2.json", "w") as f:
        json.dump(save_data, f, indent=2, default=str)

    log_entry = f"""
## Expanded Coins v2 - No Data Snooping ({pd.Timestamp.now().strftime('%Y-%m-%d')})

### Methodology Fix
- Coin selection: avg **validation** Donchian Sharpe > 0 (NOT holdout)
- Holdout touched ONCE after all selection/tuning complete

### Coin Screening (Validation)
- Total usable: {len(all_coins)}
- Passed screening (avg val SR > 0): {len(selected_coins)}
- Original 22 that passed: {sum(1 for c in selected_coins if c in ORIGINAL_22)}/22
- New coins selected: {len(new_selected)}

New selected coins: {', '.join(new_selected)}

### Holdout (50/50 Donchian+MR, exit_z=0.50)
| Portfolio | Sharpe | Return% | MaxDD% | Trades | Coins |
|-----------|--------|---------|--------|--------|-------|
"""
    for name in ["A) Original 22", "B) Val-selected all", "C) New selected only",
                  "D) Orig + new selected", "E) Top 30 by val SR"]:
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
