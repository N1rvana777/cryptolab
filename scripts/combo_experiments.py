#!/usr/bin/env python3
"""Three experiments: multi-lookback MR, exit Z sweep, expanded coins.

Experiment 1: Dual-lookback MR (short 72 + long 336) vs single lookback
Experiment 2: Exit Z threshold sweep (0.0 to 1.0)
Experiment 3: Expanded coin universe (add coins from OKX cache)
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
from scripts.mean_reversion_experiment import (
    compute_adx, compute_dynamic_slippage, load_8h_data,
    run_donchian_b0, run_meanrev,
    COINS, PPY_8H, FEE_BPS,
)

MEANREV_PARAMS_PATH = Path("sweep_results/meanrev_experiment.json")

EXTRA_COINS = ["APT", "ARB", "AXS", "BNB", "HBAR", "MANA", "OP", "PEPE", "SAND", "SUI"]

WINDOWS = [
    {"name": "W1", "is_start": "2021-01-01", "is_end": "2022-07-01",
     "val_start": "2022-07-01", "val_end": "2023-07-01"},
    {"name": "W2", "is_start": "2021-01-01", "is_end": "2023-07-01",
     "val_start": "2023-07-01", "val_end": "2024-07-01"},
    {"name": "W3", "is_start": "2021-01-01", "is_end": "2024-07-01",
     "val_start": "2024-07-01", "val_end": "2025-07-01"},
]


def run_dual_mr(df, capital, n_coins):
    """Run two MR strategies (short + long lookback) sharing 50% of capital (25% each)."""
    n = len(df)
    warmup = 400  # enough for 336 lookback + 60
    if n < warmup + 20:
        return None

    closes = df["close"].values; opens = df["open"].values
    highs = df["high"].values; lows = df["low"].values
    volumes = df["volume"].values

    # Short MR: lookback=72, entry=2.0, exit=0.5, stop=3.0
    sma_s = pd.Series(closes).rolling(72, min_periods=72).mean().values
    std_s = pd.Series(closes).rolling(72, min_periods=72).std(ddof=1).values
    z_s = np.where(std_s > 1e-10, (closes - sma_s) / std_s, 0.0)

    # Long MR: lookback=336, entry=2.5, exit=0.0, stop=3.5
    sma_l = pd.Series(closes).rolling(336, min_periods=336).mean().values
    std_l = pd.Series(closes).rolling(336, min_periods=336).std(ddof=1).values
    z_l = np.where(std_l > 1e-10, (closes - sma_l) / std_l, 0.0)

    adx = compute_adx(highs, lows, closes, 20)
    ret = np.zeros(n); ret[1:] = closes[1:]/closes[:-1] - 1
    ret_s = pd.Series(ret)
    vol_10d = ret_s.rolling(30, min_periods=10).std().values
    vol_30d = ret_s.rolling(90, min_periods=30).std().values
    vol_usd = volumes * closes
    adv = pd.Series(vol_usd).rolling(60, min_periods=3).sum().values / 20

    fee_rate = FEE_BPS / 10_000
    equity = capital; cash = equity; pos = 0.0; entry_px = 0.0
    peak = equity; equities = np.full(n, equity)
    n_trades = 0; wins = 0; closed_c = 0; prev_target = 0.0

    # Two independent MR states
    mr_s_side = None; mr_s_held = 0.0
    mr_l_side = None; mr_l_held = 0.0
    start = warmup

    for i in range(start, n):
        o = opens[i]; c = closes[i]

        trade_size = abs(prev_target - pos)
        if trade_size > max(5.0, abs(prev_target) * 0.03):
            fee = trade_size * fee_rate
            slip = compute_dynamic_slippage(trade_size, adv[i])
            if abs(pos) > 0.01 and entry_px > 0:
                pnl = abs(pos) * ((o-entry_px)/entry_px if pos > 0 else (entry_px-o)/entry_px)
                cash += pnl
                if pnl > 0: wins += 1
                closed_c += 1
            cash -= fee + slip; n_trades += 1
            pos = prev_target
            entry_px = o if abs(pos) > 0.01 else 0.0

        unrealized = 0.0
        if abs(pos) > 0.01 and entry_px > 0:
            unrealized = abs(pos) * ((c-entry_px)/entry_px if pos > 0 else (entry_px-c)/entry_px)
        equity = cash + unrealized; peak = max(peak, equity); equities[i] = equity

        # Regime (inverted)
        adx_val = adx[i] if not np.isnan(adx[i]) else 25.0
        if adx_val < 20: mr_regime = 1.0
        elif adx_val < 25: mr_regime = 0.5
        else: mr_regime = 0.0
        v10 = vol_10d[i]; v30 = vol_30d[i]
        if not np.isnan(v10) and not np.isnan(v30) and v30 > 0 and v10 < v30*0.7:
            mr_regime = 0.0

        mr_eq = equity * 0.25  # 25% each MR sub-strategy

        def _mr_signal(z_val, std_val, entry_z, exit_z, stop_z, side, held, eq_alloc):
            target = 0.0
            # Exit
            if side == "long":
                if not np.isnan(z_val) and (z_val >= -exit_z or z_val < -stop_z):
                    return 0.0, None, 0.0
            elif side == "short":
                if not np.isnan(z_val) and (z_val <= exit_z or z_val > stop_z):
                    return 0.0, None, 0.0

            # Entry
            if side is None and mr_regime > 0 and not np.isnan(z_val) and not np.isnan(std_val):
                sz_dist = stop_z - entry_z
                s = std_val if std_val > 0 else c * 0.02
                sdp = max(sz_dist * s / c, 0.001) if c > 0 else 0.01
                bp = (eq_alloc * 0.02 / sdp) * 3.0
                mp = eq_alloc * 3.0
                avol = (s / c) * np.sqrt(PPY_8H) if c > 0 else 1.0
                vsc = max(0.5, min(2.0, 0.15 / avol)) if avol > 0 else 1.0
                dd_ = max(0, 1.0 - equity / peak)
                dsc = 1.0 - min(dd_ / 0.30, 1.0) * 0.75 if dd_ > 0 else 1.0
                position = min(bp * vsc * dsc * mr_regime, mp)
                if z_val < -entry_z and position > 0:
                    return position, "long", position
                elif z_val > entry_z and position > 0:
                    return -position, "short", -position

            # Hold
            if side is not None:
                return held, side, held
            return 0.0, None, 0.0

        # Short MR
        mr_s_target, mr_s_side, mr_s_held = _mr_signal(
            z_s[i], std_s[i], 2.0, 0.5, 3.0, mr_s_side, mr_s_held, mr_eq)

        # Long MR
        mr_l_target, mr_l_side, mr_l_held = _mr_signal(
            z_l[i], std_l[i], 2.5, 0.0, 3.5, mr_l_side, mr_l_held, mr_eq)

        prev_target = mr_s_target + mr_l_target

    eq = pd.Series(equities[start:])
    if len(eq) < 10: return None
    sr = sharpe_ratio(eq, PPY_8H); _, dd_pct = max_drawdown(eq)
    return {
        "sharpe": sr, "return_pct": (float(eq.iloc[-1]) - capital) / capital * 100,
        "max_dd_pct": dd_pct, "n_trades": n_trades,
        "equities": equities[start:].copy(),
    }


def run_portfolio_combo(cache, coins, mr_params, exit_z_override=None,
                        use_dual_mr=False):
    """Run Donchian + MR combo on holdout for a set of coins.

    If use_dual_mr: replace single MR with dual-lookback MR.
    If exit_z_override: override all coins' exit Z with this value.
    """
    n_coins = len(coins)
    CAPITAL = 10_000.0 / n_coins
    don_results = {}; mr_results = {}

    for coin in coins:
        df = load_8h_data(cache, coin, "2025-07-01", "2026-04-01")
        if df is None: continue

        # Donchian B0
        r_don = run_donchian_b0(df, CAPITAL, n_coins, use_dynamic_slip=True)
        if r_don: don_results[coin] = r_don

        # MR
        p = mr_params.get(coin)
        if use_dual_mr:
            r_mr = run_dual_mr(df, CAPITAL, n_coins)
            if r_mr: mr_results[coin] = r_mr
        elif p and len(p) == 4:
            exit_z = exit_z_override if exit_z_override is not None else p[2]
            r_mr = run_meanrev(df, p[0], p[1], exit_z, p[3], CAPITAL, n_coins)
            if r_mr: mr_results[coin] = r_mr

    # Combine 50/50
    common = set(don_results.keys()) | set(mr_results.keys())
    if not common: return None

    all_coins_with_data = set(don_results.keys()) | set(mr_results.keys())
    min_len = 999999
    for c in all_coins_with_data:
        if c in don_results: min_len = min(min_len, len(don_results[c]["equities"]))
        if c in mr_results: min_len = min(min_len, len(mr_results[c]["equities"]))

    don_eq = np.zeros(min_len)
    mr_eq = np.zeros(min_len)
    for c in don_results:
        don_eq += don_results[c]["equities"][:min_len]
    for c in mr_results:
        mr_eq += mr_results[c]["equities"][:min_len]

    combo_eq = (don_eq + mr_eq) / 2
    eq_s = pd.Series(combo_eq)
    sr = sharpe_ratio(eq_s, PPY_8H); _, dd = max_drawdown(eq_s)
    ret = (combo_eq[-1] / combo_eq[0] - 1) * 100 if combo_eq[0] > 0 else 0

    don_trades = sum(r["n_trades"] for r in don_results.values())
    mr_trades = sum(r["n_trades"] for r in mr_results.values())

    return {
        "sharpe": sr, "return_pct": ret, "max_dd_pct": dd,
        "n_trades": don_trades + mr_trades,
        "n_coins": len(all_coins_with_data),
        "don_eq": don_eq, "mr_eq": mr_eq,
    }


def mr_sweep_for_coins(cache, coins):
    """Run MR parameter sweep for new coins. Returns {coin: best_params}."""
    lookbacks = [24, 48, 72, 96, 168, 252, 336]
    entry_zs = [1.5, 2.0, 2.5, 3.0]
    exit_zs = [0.0, 0.25, 0.5]
    stop_zs = [3.0, 3.5, 4.0]
    param_grid = [(lb, ez, xz, sz) for lb, ez, xz, sz in
                  product(lookbacks, entry_zs, exit_zs, stop_zs) if sz > ez]

    n_coins = len(coins)
    CAPITAL = 10_000.0 / max(n_coins, 22)
    best_params = {}

    for ci, coin in enumerate(coins):
        print(f"    [{ci+1}/{len(coins)}] {coin}...", end=" ", flush=True)
        t1 = time.time()

        param_results = {}
        for w in WINDOWS:
            df_full = load_8h_data(cache, coin, w["is_start"], w["val_end"])
            if df_full is None: continue
            val_start = pd.Timestamp(w["val_start"])
            is_end_idx = len(df_full[df_full["timestamp"] < val_start])

            for params in param_grid:
                lb, ez, xz, sz = params
                df_is = df_full.iloc[:is_end_idx].reset_index(drop=True)
                r_is = run_meanrev(df_is, lb, ez, xz, sz, CAPITAL, n_coins)
                if r_is is None or r_is["sharpe"] <= 0:
                    param_results.setdefault(params, []).append(None)
                    continue
                df_val = df_full[df_full["timestamp"] >= val_start].reset_index(drop=True)
                if len(df_val) < 50:
                    param_results.setdefault(params, []).append(None)
                    continue
                r_val = run_meanrev(df_val, lb, ez, xz, sz, CAPITAL, n_coins)
                param_results.setdefault(params, []).append(r_val["sharpe"] if r_val else None)

        best_param = None; best_score = -999
        for params, sharpes in param_results.items():
            valid = [s for s in sharpes if s is not None]
            if len(valid) < 1: continue
            n_pos = sum(1 for s in valid if s > 0)
            avg = np.mean(valid)
            score = n_pos * 10 + avg
            if score > best_score:
                best_score = score; best_param = params

        if best_param:
            valid = [s for s in param_results[best_param] if s is not None]
            avg = np.mean(valid)
            best_params[coin] = list(best_param)
            print(f"best=({best_param[0]},{best_param[1]},{best_param[2]},{best_param[3]}) "
                  f"avg_val={avg:.3f} ({time.time()-t1:.0f}s)", flush=True)
        else:
            print(f"no params ({time.time()-t1:.0f}s)", flush=True)

    return best_params


def main():
    t0 = time.time()
    cache = ParquetCache()

    with open(MEANREV_PARAMS_PATH) as f:
        mr_params = json.load(f).get("meanrev_best_params", {})

    all_results = {}

    # ================================================================
    # Baseline
    # ================================================================
    print("=" * 70)
    print("Baseline: Original 50/50 (22 coins)")
    print("=" * 70)
    r_base = run_portfolio_combo(cache, COINS, mr_params)
    all_results["Baseline 50/50"] = r_base
    print(f"  Sharpe={r_base['sharpe']:.3f}  Ret={r_base['return_pct']:.2f}%  "
          f"MaxDD={r_base['max_dd_pct']:.2f}%  Trades={r_base['n_trades']}")

    # ================================================================
    # Experiment 1: Dual-lookback MR
    # ================================================================
    print(f"\n{'=' * 70}")
    print("Experiment 1: Dual-Lookback MR (short=72 + long=336)")
    print("=" * 70)
    r_dual = run_portfolio_combo(cache, COINS, mr_params, use_dual_mr=True)
    all_results["Dual-LB MR"] = r_dual
    print(f"  Sharpe={r_dual['sharpe']:.3f}  Ret={r_dual['return_pct']:.2f}%  "
          f"MaxDD={r_dual['max_dd_pct']:.2f}%  Trades={r_dual['n_trades']}")

    # ================================================================
    # Experiment 2: Exit Z sweep
    # ================================================================
    print(f"\n{'=' * 70}")
    print("Experiment 2: Exit Z Threshold Sweep")
    print("=" * 70)

    for exit_z in [0.0, 0.25, 0.5, 0.75, 1.0]:
        label = f"Exit Z={exit_z:.2f}"
        r = run_portfolio_combo(cache, COINS, mr_params, exit_z_override=exit_z)
        all_results[label] = r
        print(f"  {label:<15} Sharpe={r['sharpe']:.3f}  Ret={r['return_pct']:.2f}%  "
              f"MaxDD={r['max_dd_pct']:.2f}%  Trades={r['n_trades']}")

    # ================================================================
    # Experiment 3: Expanded Coins
    # ================================================================
    print(f"\n{'=' * 70}")
    print("Experiment 3: Expanded Coin Universe")
    print("=" * 70)

    # Check which extra coins have enough data and HL volume
    valid_extra = []
    for coin in EXTRA_COINS:
        df = load_8h_data(cache, coin, "2021-01-01", "2026-04-01")
        if df is not None and len(df) > 500:
            valid_extra.append(coin)
            print(f"  {coin}: {len(df)} bars (8H), OK", flush=True)
        else:
            # Try with available data
            df2 = load_8h_data(cache, coin, "2022-01-01", "2026-04-01")
            if df2 is not None and len(df2) > 300:
                valid_extra.append(coin)
                print(f"  {coin}: {len(df2)} bars (8H, partial), OK", flush=True)
            else:
                print(f"  {coin}: insufficient data, skip", flush=True)

    print(f"\n  Valid extra coins: {valid_extra}")

    # Run Donchian B0 on extra coins (holdout)
    print("\n  Running Donchian B0 on extra coins (holdout)...")
    n_all = len(COINS) + len(valid_extra)
    CAP_NEW = 10_000.0 / max(len(valid_extra), 1)
    extra_don_sharpes = {}
    for coin in valid_extra:
        df = load_8h_data(cache, coin, "2025-07-01", "2026-04-01")
        if df is None: continue
        r = run_donchian_b0(df, CAP_NEW, len(valid_extra), use_dynamic_slip=True)
        if r:
            extra_don_sharpes[coin] = r["sharpe"]
            print(f"    {coin}: Donchian Sharpe={r['sharpe']:.3f}", flush=True)

    # MR parameter sweep for extra coins
    print(f"\n  Running MR param sweep for {len(valid_extra)} extra coins...")
    extra_mr_params = mr_sweep_for_coins(cache, valid_extra)

    # Combine all params
    all_mr_params = {**mr_params, **{c: p for c, p in extra_mr_params.items()}}

    # Portfolio comparisons
    all_coins = COINS + [c for c in valid_extra if c in extra_mr_params or c in extra_don_sharpes]
    print(f"\n  Total coins for expanded portfolio: {len(all_coins)}")

    # Original 22 only
    r_orig = run_portfolio_combo(cache, COINS, all_mr_params)
    all_results["22 coins"] = r_orig

    # Extra only
    extra_with_data = [c for c in valid_extra if c in extra_mr_params or c in extra_don_sharpes]
    if extra_with_data:
        r_extra = run_portfolio_combo(cache, extra_with_data, all_mr_params)
        all_results["Extra coins only"] = r_extra
        if r_extra:
            print(f"  Extra only:  Sharpe={r_extra['sharpe']:.3f}  Ret={r_extra['return_pct']:.2f}%  "
                  f"MaxDD={r_extra['max_dd_pct']:.2f}%")

    # Combined
    r_all = run_portfolio_combo(cache, all_coins, all_mr_params)
    all_results["All coins combined"] = r_all
    if r_all:
        print(f"  All combined: Sharpe={r_all['sharpe']:.3f}  Ret={r_all['return_pct']:.2f}%  "
              f"MaxDD={r_all['max_dd_pct']:.2f}%")

    # Cross-correlation between original and extra
    if r_orig and r_extra and "don_eq" in r_orig and "don_eq" in r_extra:
        ml = min(len(r_orig["don_eq"]), len(r_extra["don_eq"]))
        if ml > 10:
            orig_rets = pd.Series(r_orig["don_eq"][:ml]).pct_change().dropna().values
            extra_rets = pd.Series(r_extra["don_eq"][:ml]).pct_change().dropna().values
            ml2 = min(len(orig_rets), len(extra_rets))
            if ml2 > 10 and np.std(orig_rets[:ml2]) > 0 and np.std(extra_rets[:ml2]) > 0:
                corr = float(np.corrcoef(orig_rets[:ml2], extra_rets[:ml2])[0, 1])
                print(f"\n  Original vs Extra daily return correlation: {corr:.3f}")

    # ================================================================
    # Summary
    # ================================================================
    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print("=" * 70)
    print(f"  {'Method':<25} {'Sharpe':>8} {'Return%':>9} {'MaxDD%':>8} {'Trades':>7}")
    print("  " + "-" * 60)

    display_order = [
        "Baseline 50/50", "Dual-LB MR",
        "Exit Z=0.00", "Exit Z=0.25", "Exit Z=0.50", "Exit Z=0.75", "Exit Z=1.00",
        "22 coins", "Extra coins only", "All coins combined",
    ]
    for key in display_order:
        r = all_results.get(key)
        if r:
            print(f"  {key:<25} {r['sharpe']:>8.3f} {r['return_pct']:>9.2f} "
                  f"{r['max_dd_pct']:>8.2f} {r['n_trades']:>7}")

    # Save + log
    save_data = {k: {kk: vv for kk, vv in v.items()
                      if kk not in ("equities", "don_eq", "mr_eq")}
                 for k, v in all_results.items() if v}
    save_data["extra_mr_params"] = extra_mr_params
    save_data["extra_don_sharpes"] = extra_don_sharpes
    with open("sweep_results/combo_experiments.json", "w") as f:
        json.dump(save_data, f, indent=2, default=str)

    log_entry = f"""
## Combo Experiments ({pd.Timestamp.now().strftime('%Y-%m-%d')})

### Experiment 1: Dual-Lookback MR
- Short MR: lookback=72, entry_z=2.0, exit_z=0.5, stop_z=3.0
- Long MR: lookback=336, entry_z=2.5, exit_z=0.0, stop_z=3.5
- Each gets 25% of capital (total MR = 50%)

### Experiment 2: Exit Z Sweep

### Experiment 3: Expanded Coins
- Extra coins tested: {valid_extra}
- Extra coins with MR params: {list(extra_mr_params.keys())}

### Results
| Method | Sharpe | Return% | MaxDD% | Trades |
|--------|--------|---------|--------|--------|
"""
    for key in display_order:
        r = all_results.get(key)
        if r:
            log_entry += f"| {key} | {r['sharpe']:.3f} | {r['return_pct']:.2f} | {r['max_dd_pct']:.2f} | {r['n_trades']} |\n"

    best = max([(k, r) for k, r in all_results.items() if r],
               key=lambda x: x[1]["sharpe"])
    log_entry += f"\nBest: **{best[0]}** (Sharpe {best[1]['sharpe']:.3f})\n"

    if extra_don_sharpes:
        log_entry += f"\n### Extra Coin Donchian Sharpes\n"
        for coin, sr in sorted(extra_don_sharpes.items(), key=lambda x: -x[1]):
            log_entry += f"- {coin}: {sr:.3f}\n"

    with open("RESEARCH_LOG.md", "a", encoding="utf-8") as f:
        f.write(log_entry)

    print(f"\n  Total time: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
