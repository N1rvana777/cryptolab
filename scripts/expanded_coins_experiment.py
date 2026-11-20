#!/usr/bin/env python3
"""Expanded coin universe experiment.

Tier 1: 25 coins with OKX data from 2021 (full walk-forward)
Tier 2: 25 coins with OKX data from 2022-2024 (partial WF)
Tier 3: 37 coins with HL data only (holdout only)

For each coin: run Donchian B0 + MR param sweep (where WF possible)
Compare: original 22 vs expanded portfolios
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
    {"name": "W1", "is_start": "2021-01-01", "is_end": "2022-07-01",
     "val_start": "2022-07-01", "val_end": "2023-07-01"},
    {"name": "W2", "is_start": "2021-01-01", "is_end": "2023-07-01",
     "val_start": "2023-07-01", "val_end": "2024-07-01"},
    {"name": "W3", "is_start": "2021-01-01", "is_end": "2024-07-01",
     "val_start": "2024-07-01", "val_end": "2025-07-01"},
]


def load_8h(cache, coin, start, end, source="okx"):
    """Load data and resample to 8H. Try OKX first, then HL."""
    if source == "okx":
        df = cache.read("okx", coin, "1h")
        if df is not None and not df.empty:
            if df["timestamp"].dt.tz is not None:
                df["timestamp"] = df["timestamp"].dt.tz_localize(None)
            df8 = resample_ohlcv(df, "8h")
            mask = (df8["timestamp"] >= pd.Timestamp(start)) & (df8["timestamp"] < pd.Timestamp(end))
            out = df8[mask].reset_index(drop=True)
            if len(out) > 50:
                return out

    # Try HL 4H -> 8H
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


def mr_sweep_coin(cache, coin, source="okx"):
    """MR param sweep for one coin using available walk-forward windows."""
    lookbacks = [24, 48, 72, 96, 168, 252, 336]
    entry_zs = [1.5, 2.0, 2.5, 3.0]
    exit_zs = [0.0, 0.25, 0.5]
    stop_zs = [3.0, 3.5, 4.0]
    param_grid = [(lb, ez, xz, sz) for lb, ez, xz, sz in
                  product(lookbacks, entry_zs, exit_zs, stop_zs) if sz > ez]

    CAPITAL = 10_000.0 / 22  # normalize

    param_results = {}
    n_windows_used = 0

    for w in WINDOWS:
        df_full = load_8h(cache, coin, w["is_start"], w["val_end"], source)
        if df_full is None or len(df_full) < 200:
            continue

        val_start = pd.Timestamp(w["val_start"])
        is_end_idx = len(df_full[df_full["timestamp"] < val_start])
        if is_end_idx < 100:
            continue

        n_windows_used += 1
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

    if not param_results:
        return None, 0

    best_param = None; best_score = -999
    for params, sharpes in param_results.items():
        valid = [s for s in sharpes if s is not None]
        if not valid: continue
        n_pos = sum(1 for s in valid if s > 0)
        avg = np.mean(valid)
        score = n_pos * 10 + avg
        if score > best_score:
            best_score = score; best_param = params

    return best_param, n_windows_used


def build_portfolio(cache, coins, mr_params, exit_z_override=None):
    """Build 50/50 Donchian+MR portfolio on holdout. Returns metrics."""
    n_coins = len(coins)
    if n_coins == 0: return None
    CAPITAL = 10_000.0 / n_coins

    don_eqs = []; mr_eqs = []
    don_trades = 0; mr_trades = 0

    for coin in coins:
        # Try OKX first, then HL for holdout
        df = load_8h(cache, coin, "2025-07-01", "2026-04-01")
        if df is None: continue

        r_don = run_donchian_b0(df, CAPITAL, n_coins, use_dynamic_slip=True)
        if r_don:
            don_eqs.append(r_don["equities"])
            don_trades += r_don["n_trades"]

        p = mr_params.get(coin)
        if p and len(p) >= 4:
            ez = exit_z_override if exit_z_override is not None else p[2]
            r_mr = run_meanrev(df, p[0], p[1], ez, p[3], CAPITAL, n_coins)
            if r_mr:
                mr_eqs.append(r_mr["equities"])
                mr_trades += r_mr["n_trades"]

    if not don_eqs and not mr_eqs:
        return None

    min_len = 999999
    for e in don_eqs + mr_eqs:
        min_len = min(min_len, len(e))

    don_total = np.zeros(min_len)
    for e in don_eqs: don_total += e[:min_len]
    mr_total = np.zeros(min_len)
    for e in mr_eqs: mr_total += e[:min_len]

    combo = (don_total + mr_total) / 2
    eq_s = pd.Series(combo)
    sr = sharpe_ratio(eq_s, PPY_8H)
    _, dd = max_drawdown(eq_s)
    ret = (combo[-1] / combo[0] - 1) * 100 if combo[0] > 0 else 0

    return {
        "sharpe": sr, "return_pct": ret, "max_dd_pct": dd,
        "n_trades": don_trades + mr_trades,
        "n_coins_don": len(don_eqs), "n_coins_mr": len(mr_eqs),
    }


def main():
    t0 = time.time()
    cache = ParquetCache()

    # Load catalog
    with open("sweep_results/coin_catalog.json") as f:
        catalog = json.load(f)

    # Load existing MR params
    with open("sweep_results/meanrev_experiment.json") as f:
        existing_mr = json.load(f).get("meanrev_best_params", {})

    # Classify coins
    usable = [c for c in catalog if c["status"] in ("HAS_OKX", "HAS_HL")]

    tier1 = [c for c in usable if c["status"] == "HAS_OKX"
             and c.get("okx_start", "9999") <= "2021-12-31"]
    tier2 = [c for c in usable if c["status"] == "HAS_OKX"
             and c.get("okx_start", "9999") > "2021-12-31"]
    tier3 = [c for c in usable if c["status"] == "HAS_HL"]

    t1_coins = [c["coin"] for c in tier1]
    t2_coins = [c.get("okx_name", c["coin"]) for c in tier2]
    t3_coins = [c["coin"] for c in tier3]

    print(f"Tier 1 (OKX 2021+, full WF): {len(t1_coins)} coins")
    print(f"Tier 2 (OKX 2022+, partial WF): {len(t2_coins)} coins")
    print(f"Tier 3 (HL only, holdout): {len(t3_coins)} coins")
    print(f"Total: {len(t1_coins) + len(t2_coins) + len(t3_coins)}")

    # ================================================================
    # Step 1: Donchian B0 holdout for ALL coins
    # ================================================================
    print(f"\n{'='*70}")
    print("Step 1: Donchian B0 Holdout (all coins)")
    print("=" * 70)

    all_coins = t1_coins + t2_coins + t3_coins
    don_sharpes = {}
    n_all = len(all_coins)
    CAPITAL = 10_000.0 / n_all

    for ci, coin in enumerate(all_coins):
        df = load_8h(cache, coin, "2025-07-01", "2026-04-01")
        if df is None:
            continue
        r = run_donchian_b0(df, CAPITAL, n_all, use_dynamic_slip=True)
        if r and not np.isnan(r["sharpe"]):
            don_sharpes[coin] = r["sharpe"]

    # Sort by Sharpe
    sorted_don = sorted(don_sharpes.items(), key=lambda x: -x[1])
    print(f"\n  {'Coin':<10} {'Tier':>5} {'Don Sharpe':>11} {'HL Vol':>10}")
    print("  " + "-" * 40)
    vol_map = {c["coin"]: c["hl_vol_24h"] for c in catalog}
    tier_map = {}
    for c in t1_coins: tier_map[c] = "T1"
    for c in t2_coins: tier_map[c] = "T2"
    for c in t3_coins: tier_map[c] = "T3"

    for coin, sr in sorted_don[:40]:
        v = vol_map.get(coin, 0)
        vs = f"{v/1e6:.1f}M" if v >= 1e6 else f"{v/1e3:.0f}K"
        t = tier_map.get(coin, "?")
        orig = " *" if coin in ORIGINAL_22 else ""
        print(f"  {coin:<10} {t:>5} {sr:>11.3f} {vs:>10}{orig}")

    n_pos = sum(1 for _, sr in don_sharpes.items() if sr > 0)
    print(f"\n  {n_pos}/{len(don_sharpes)} coins with positive Donchian Sharpe")

    # ================================================================
    # Step 2: MR param sweep for NEW coins (not in original 22)
    # ================================================================
    print(f"\n{'='*70}")
    print("Step 2: MR Param Sweep (new coins)")
    print("=" * 70)

    all_mr_params = dict(existing_mr)  # start with existing
    new_coins_to_sweep = [c for c in t1_coins + t2_coins if c not in existing_mr]

    print(f"  {len(new_coins_to_sweep)} new coins need MR sweep")
    for ci, coin in enumerate(new_coins_to_sweep):
        print(f"  [{ci+1}/{len(new_coins_to_sweep)}] {coin}...", end=" ", flush=True)
        t1_t = time.time()
        best, n_win = mr_sweep_coin(cache, coin)
        if best:
            all_mr_params[coin] = list(best)
            print(f"best=({best[0]},{best[1]},{best[2]},{best[3]}) "
                  f"windows={n_win} ({time.time()-t1_t:.0f}s)", flush=True)
        else:
            print(f"no params ({time.time()-t1_t:.0f}s)", flush=True)

    # For HL-only coins, we can't do proper WF - skip MR or use holdout-only
    # (per user requirement: don't reduce training for HL coins)
    print(f"\n  Tier 3 (HL-only): skipping MR sweep (insufficient IS data)")
    print(f"  Total coins with MR params: {len(all_mr_params)}")

    # ================================================================
    # Step 3: Portfolio comparisons on Holdout
    # ================================================================
    print(f"\n{'='*70}")
    print("Step 3: Portfolio Comparisons (Holdout)")
    print("=" * 70)

    # Find coins that have holdout data
    coins_with_holdout = []
    for coin in all_coins:
        df = load_8h(cache, coin, "2025-07-01", "2026-04-01")
        if df is not None and len(df) > 100:
            coins_with_holdout.append(coin)

    print(f"  Coins with holdout data: {len(coins_with_holdout)}")

    # Original 22
    orig_with_ho = [c for c in ORIGINAL_22 if c in coins_with_holdout]
    # New coins (not in original 22)
    new_with_ho = [c for c in coins_with_holdout if c not in ORIGINAL_22]
    # Positive Donchian new coins
    pos_don_new = [c for c in new_with_ho if don_sharpes.get(c, -1) > 0]

    portfolios = {}

    # A) Original 22 (baseline with exit_z=0.50 improvement)
    r = build_portfolio(cache, orig_with_ho, all_mr_params, exit_z_override=0.50)
    if r: portfolios["A) Original 22"] = r

    # B) Original 22 + all new coins
    all_ho = orig_with_ho + new_with_ho
    r = build_portfolio(cache, all_ho, all_mr_params, exit_z_override=0.50)
    if r: portfolios["B) All coins"] = r

    # C) Only new coins
    r = build_portfolio(cache, new_with_ho, all_mr_params, exit_z_override=0.50)
    if r: portfolios["C) New only"] = r

    # D) Original 22 + positive-Donchian new coins only
    curated = orig_with_ho + pos_don_new
    r = build_portfolio(cache, curated, all_mr_params, exit_z_override=0.50)
    if r: portfolios["D) Orig + pos-Don new"] = r

    # E) Tier 1 only (25 coins with 2021+ data)
    t1_ho = [c for c in t1_coins if c in coins_with_holdout]
    r = build_portfolio(cache, t1_ho, all_mr_params, exit_z_override=0.50)
    if r: portfolios["E) Tier 1 (25)"] = r

    # F) Top 30 by Donchian Sharpe
    top30 = [c for c, _ in sorted_don[:30] if c in coins_with_holdout]
    r = build_portfolio(cache, top30, all_mr_params, exit_z_override=0.50)
    if r: portfolios["F) Top 30 Donchian"] = r

    # Print
    print(f"\n  {'Portfolio':<25} {'Sharpe':>8} {'Ret%':>8} {'MaxDD%':>8} {'Trades':>7} {'Coins':>6}")
    print("  " + "-" * 65)
    for name, p in sorted(portfolios.items()):
        nc = p.get("n_coins_don", 0)
        print(f"  {name:<25} {p['sharpe']:>8.3f} {p['return_pct']:>8.2f} "
              f"{p['max_dd_pct']:>8.2f} {p['n_trades']:>7} {nc:>6}")

    # Cross-correlation between original and new
    if "A) Original 22" in portfolios and "C) New only" in portfolios:
        r_orig = build_portfolio(cache, orig_with_ho, all_mr_params, exit_z_override=0.50)
        r_new = build_portfolio(cache, new_with_ho, all_mr_params, exit_z_override=0.50)
        # We'd need equity curves - approximate from the portfolio build
        print(f"\n  Original vs New diversification: {len(orig_with_ho)} + {len(new_with_ho)} coins")

    # ================================================================
    # Save + RESEARCH_LOG
    # ================================================================
    save_data = {
        "don_sharpes": don_sharpes,
        "mr_params": {k: v for k, v in all_mr_params.items()},
        "portfolios": {k: v for k, v in portfolios.items()},
        "tier_counts": {"t1": len(t1_coins), "t2": len(t2_coins), "t3": len(t3_coins)},
        "coins_with_holdout": coins_with_holdout,
    }
    with open("sweep_results/expanded_coins.json", "w") as f:
        json.dump(save_data, f, indent=2, default=str)

    log_entry = f"""
## Expanded Coin Universe ({pd.Timestamp.now().strftime('%Y-%m-%d')})

### Universe
- Tier 1 (OKX 2021+): {len(t1_coins)} coins
- Tier 2 (OKX 2022+): {len(t2_coins)} coins
- Tier 3 (HL only): {len(t3_coins)} coins
- Total usable: {len(t1_coins)+len(t2_coins)+len(t3_coins)}
- Coins with holdout data: {len(coins_with_holdout)}

### Donchian B0 Holdout ({n_pos}/{len(don_sharpes)} positive Sharpe)
Top 10 new coins by Donchian Sharpe:
"""
    new_sorted = [(c, sr) for c, sr in sorted_don if c not in ORIGINAL_22][:10]
    for coin, sr in new_sorted:
        vs = f"{vol_map.get(coin,0)/1e6:.1f}M" if vol_map.get(coin,0) >= 1e6 else f"{vol_map.get(coin,0)/1e3:.0f}K"
        log_entry += f"- {coin}: Sharpe {sr:.3f} (vol {vs})\n"

    log_entry += f"""
### Portfolio Comparison (Holdout, 50/50, exit_z=0.50)
| Portfolio | Sharpe | Return% | MaxDD% | Trades | Coins |
|-----------|--------|---------|--------|--------|-------|
"""
    for name, p in sorted(portfolios.items()):
        nc = p.get("n_coins_don", 0)
        log_entry += f"| {name} | {p['sharpe']:.3f} | {p['return_pct']:.2f} | {p['max_dd_pct']:.2f} | {p['n_trades']} | {nc} |\n"

    best = max(portfolios.items(), key=lambda x: x[1]["sharpe"])
    log_entry += f"\nBest: **{best[0]}** (Sharpe {best[1]['sharpe']:.3f})\n"

    with open("RESEARCH_LOG.md", "a", encoding="utf-8") as f:
        f.write(log_entry)

    print(f"\n  Total time: {time.time()-t0:.1f}s")
    print(f"  Results saved to sweep_results/expanded_coins.json")


if __name__ == "__main__":
    main()
