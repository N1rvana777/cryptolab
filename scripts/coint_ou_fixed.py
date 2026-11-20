#!/usr/bin/env python3
"""Fixed Cointegration + OU strategies.

Cointegration fixes:
- Hedge ratio beta clamped to [0.3, 3.0]
- Pairs with beta outside this range rejected
- Single pair position capped at 10% of capital
- Total gross position capped at capital * leverage
- Use LOG prices for cointegration (more stable)

OU fix:
- Handle W1 failure (return empty result instead of None)
"""

import sys, os, time, json, warnings
from pathlib import Path
from itertools import product, combinations
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptolab.data.cache import ParquetCache
from cryptolab.backtest.metrics import sharpe_ratio, max_drawdown
from scripts.donchian_full_sweep import resample_ohlcv
from scripts.mean_reversion_experiment import compute_dynamic_slippage
from scripts.mean_reversion_strategies import load_8h, estimate_ou, ALL_28
from scripts.cross_sectional_momentum import run_xsmom
from statsmodels.tsa.stattools import coint

PPY = 1096
FEE_BPS = 3.5
BETA_MIN, BETA_MAX = 0.3, 3.0
MAX_PAIR_PCT = 0.10  # 10% of capital per pair
MAX_PAIRS = 15

WINDOWS = [
    {"name": "W1", "is_start": "2021-01-01", "is_end": "2023-01-01",
     "oos_start": "2023-01-01", "oos_end": "2024-01-01"},
    {"name": "W2", "is_start": "2022-01-01", "is_end": "2024-01-01",
     "oos_start": "2024-01-01", "oos_end": "2025-01-01"},
]


def align_prices(coin_dfs):
    """Build aligned price matrix from coin DataFrames."""
    coins = list(coin_dfs.keys())
    n_coins = len(coins)
    all_ts = None
    for df in coin_dfs.values():
        ts = set(df["timestamp"].values)
        all_ts = ts if all_ts is None else all_ts & ts
    common_ts = sorted(all_ts)
    n_bars = len(common_ts)

    prices = np.zeros((n_bars, n_coins))
    for ci, coin in enumerate(coins):
        df = coin_dfs[coin]
        ts_map = {t: i for i, t in enumerate(df["timestamp"].values)}
        for ti, t in enumerate(common_ts):
            idx = ts_map.get(t)
            if idx is not None:
                prices[ti, ci] = df.iloc[idx]["close"]

    return coins, common_ts, prices


# ================================================================
# Fixed Cointegration
# ================================================================
def find_coint_pairs(prices, coins, end_idx):
    """Find cointegrated pairs using LOG prices, filter by beta."""
    n_coins = len(coins)
    pairs = []
    log_p = np.log(np.maximum(prices[:end_idx], 1e-10))

    for ci, cj in combinations(range(n_coins), 2):
        p_i = log_p[:, ci]; p_j = log_p[:, cj]
        valid = (prices[:end_idx, ci] > 0) & (prices[:end_idx, cj] > 0)
        if valid.sum() < 300:
            continue
        try:
            _, pval, _ = coint(p_i[valid], p_j[valid])
            if pval < 0.05:
                beta = np.polyfit(p_j[valid], p_i[valid], 1)[0]
                if BETA_MIN <= abs(beta) <= BETA_MAX:
                    pairs.append((ci, cj, pval, beta, coins[ci], coins[cj]))
        except Exception:
            continue

    pairs.sort(key=lambda x: x[2])
    return pairs


def run_coint_fixed(coin_dfs, z_lookback, entry_z, exit_z, recalib_period,
                    trading_start, capital=10000.0, leverage=3.0):
    """Fixed cointegration strategy."""
    coins, common_ts, prices = align_prices(coin_dfs)
    n_coins = len(coins)
    n_bars = len(common_ts)

    ts_start = np.datetime64(trading_start)
    trade_idx = 0
    for i, t in enumerate(common_ts):
        if t >= ts_start:
            trade_idx = i; break

    # Find pairs on IS data
    coint_pairs = find_coint_pairs(prices, coins, trade_idx)
    pair_info = [(p[4], p[5], float(p[2]), float(p[3])) for p in coint_pairs[:20]]

    if not coint_pairs:
        return {"sharpe": 0, "return_pct": 0, "max_dd_pct": 0,
                "n_trades": 0, "n_pairs": 0, "equities": np.full(100, capital)}, pair_info

    n_pairs = min(len(coint_pairs), MAX_PAIRS)
    fee_rate = FEE_BPS / 10_000

    equity = capital; cash = equity
    equities = np.full(n_bars, equity)
    pair_pos = {}  # (ci,cj) -> signed USD
    pair_beta = {}
    last_calib = {}
    total_trades = 0

    for i in range(trade_idx + 1, n_bars):
        # MTM
        for (ci, cj), pos_usd in list(pair_pos.items()):
            if abs(pos_usd) < 1:
                continue
            beta = pair_beta.get((ci, cj), 1.0)
            # PnL from spread movement
            ret_i = (prices[i, ci] / prices[i-1, ci] - 1) if prices[i-1, ci] > 0 else 0
            ret_j = (prices[i, cj] / prices[i-1, cj] - 1) if prices[i-1, cj] > 0 else 0
            # Long spread: long A, short beta*B
            # pos_usd > 0 means long spread
            pnl = pos_usd * (ret_i - beta * ret_j)
            cash += pnl

        equity = cash
        equities[i] = equity

        # Trade each pair
        for pi in range(n_pairs):
            ci, cj, _, _, _, _ = coint_pairs[pi]
            key = (ci, cj)

            # Recalibrate beta
            if key not in pair_beta or (i - last_calib.get(key, 0)) >= recalib_period:
                window_start = max(0, i - z_lookback * 2)
                log_i = np.log(np.maximum(prices[window_start:i, ci], 1e-10))
                log_j = np.log(np.maximum(prices[window_start:i, cj], 1e-10))
                valid = (prices[window_start:i, ci] > 0) & (prices[window_start:i, cj] > 0)
                if valid.sum() > 50:
                    beta = np.polyfit(log_j[valid], log_i[valid], 1)[0]
                    beta = np.clip(beta, BETA_MIN, BETA_MAX)
                    pair_beta[key] = beta
                    last_calib[key] = i

            beta = pair_beta.get(key, 1.0)

            # Compute spread Z-score (log prices)
            window_start = max(0, i - z_lookback)
            log_spread = (np.log(np.maximum(prices[window_start:i, ci], 1e-10)) -
                         beta * np.log(np.maximum(prices[window_start:i, cj], 1e-10)))
            if len(log_spread) < z_lookback // 2:
                continue
            s_mean = np.mean(log_spread)
            s_std = np.std(log_spread)
            if s_std < 1e-10:
                continue
            current = (np.log(max(prices[i, ci], 1e-10)) -
                      beta * np.log(max(prices[i, cj], 1e-10)))
            z = (current - s_mean) / s_std

            cur_pos = pair_pos.get(key, 0)
            max_per_pair = equity * MAX_PAIR_PCT
            max_total = equity * leverage

            if abs(cur_pos) < 1:
                # Check total gross position
                gross = sum(abs(p) for p in pair_pos.values())
                if gross >= max_total:
                    continue
                size = min(max_per_pair, max_total - gross)
                if size < 10:
                    continue

                if z > entry_z:
                    pair_pos[key] = -size  # short spread
                    cash -= size * 2 * fee_rate
                    total_trades += 1
                elif z < -entry_z:
                    pair_pos[key] = size   # long spread
                    cash -= size * 2 * fee_rate
                    total_trades += 1
            elif abs(z) < exit_z:
                cash -= abs(cur_pos) * 2 * fee_rate
                pair_pos[key] = 0
                total_trades += 1

    eq = equities[trade_idx:]
    eq = eq / eq[0] * capital
    eq_s = pd.Series(eq)
    sr = sharpe_ratio(eq_s, PPY); _, dd = max_drawdown(eq_s)
    ret = (eq[-1] / eq[0] - 1) * 100

    return {"sharpe": sr, "return_pct": ret, "max_dd_pct": dd,
            "n_trades": total_trades, "n_pairs": len(coint_pairs),
            "equities": eq}, pair_info


# ================================================================
# Fixed OU
# ================================================================
def run_ou_fixed(coin_dfs, ou_window, entry_thresh, theta_min,
                 trading_start, capital=10000.0, leverage=3.0):
    """OU with fixed W1 handling."""
    coins = list(coin_dfs.keys())
    n_coins = len(coins)
    per_coin = capital / n_coins
    fee_rate = FEE_BPS / 10_000
    all_eqs = []; total_trades = 0; theta_stats = {}

    for coin in coins:
        df = coin_dfs[coin]
        closes = df["close"].values
        n = len(df)
        ts = df["timestamp"].values

        if n < ou_window + 50:
            continue

        log_prices = np.log(np.maximum(closes, 1e-10))

        trade_start = 0
        for i in range(n):
            if ts[i] >= np.datetime64(trading_start):
                trade_start = i; break

        if trade_start < ou_window:
            # Not enough warmup, skip this coin but don't fail
            all_eqs.append(np.full(n - trade_start, per_coin))
            continue

        equity = per_coin; cash = equity; pos = 0; entry_px = 0
        equities = np.full(n, equity); n_tr = 0; side = None
        thetas = []

        for i in range(trade_start + 1, n):
            c = closes[i]

            window = log_prices[max(0, i - ou_window):i]
            theta, mu, sigma = estimate_ou(window)

            if theta is not None and theta > 0:
                thetas.append(theta)

            # MTM
            if side == "long":
                pnl = abs(pos) * (c - entry_px) / entry_px if entry_px > 0 else 0
                equity = cash + pnl
            elif side == "short":
                pnl = abs(pos) * (entry_px - c) / entry_px if entry_px > 0 else 0
                equity = cash + pnl
            else:
                equity = cash
                pnl = 0
            equities[i] = equity

            if theta is None or sigma is None or sigma < 1e-10 or theta < theta_min:
                if side is not None:
                    # Close if theta becomes invalid
                    cash += pnl - abs(pos) * fee_rate
                    pos = 0; side = None; n_tr += 1
                continue

            signal = theta * (mu - log_prices[i]) / sigma

            # Vol targeting
            ann_vol = sigma * np.sqrt(PPY)
            vol_sc = min(2.0, max(0.25, 0.15 / ann_vol)) if ann_vol > 0 else 1.0
            max_pos = equity * leverage / n_coins

            if side == "long" and (signal < 0.1 or signal < -entry_thresh):
                cash += pnl - abs(pos) * fee_rate; pos = 0; side = None; n_tr += 1
            elif side == "short" and (signal > -0.1 or signal > entry_thresh):
                cash += pnl - abs(pos) * fee_rate; pos = 0; side = None; n_tr += 1
            elif side is None:
                size = min(equity * leverage * vol_sc * abs(signal) / n_coins, max_pos)
                size = max(0, min(size, equity * 0.15 * n_coins))
                if signal > entry_thresh and size > 5:
                    side = "long"; pos = size; entry_px = c
                    cash -= size * fee_rate; n_tr += 1
                elif signal < -entry_thresh and size > 5:
                    side = "short"; pos = size; entry_px = c
                    cash -= size * fee_rate; n_tr += 1

        eq = equities[trade_start:]
        all_eqs.append(eq)
        total_trades += n_tr
        if thetas:
            theta_stats[coin] = {"mean": float(np.mean(thetas)), "std": float(np.std(thetas))}

    if not all_eqs:
        return {"sharpe": 0, "return_pct": 0, "max_dd_pct": 0,
                "n_trades": 0, "theta_stats": {}, "equities": np.full(100, capital)}

    ml = min(len(e) for e in all_eqs)
    port = sum(e[:ml] for e in all_eqs)
    port = port / port[0] * capital
    eq_s = pd.Series(port)
    sr = sharpe_ratio(eq_s, PPY); _, dd = max_drawdown(eq_s)
    ret = (port[-1] / port[0] - 1) * 100
    return {"sharpe": sr, "return_pct": ret, "max_dd_pct": dd,
            "n_trades": total_trades, "theta_stats": theta_stats, "equities": port}


def main():
    t0 = time.time()
    cache = ParquetCache()

    print("Loading data...", flush=True)
    full_dfs = {}
    for coin in ALL_28:
        df = load_8h(cache, coin, "2019-01-01", "2025-01-01")
        if df is not None:
            full_dfs[coin] = df
    print(f"  {len(full_dfs)} coins")

    # ================================================================
    # Cointegration (fixed)
    # ================================================================
    print(f"\n{'='*60}")
    print("Cointegration (fixed: beta clamped, position capped)")
    print(f"{'='*60}")

    coint_grid = list(product([90, 180], [1.5, 2.0, 2.5], [0.25, 0.50], [90, 180]))
    coint_results = {}
    all_pair_info = {}

    for w in WINDOWS:
        print(f"\n  {w['name']}: IS {w['is_start']}~{w['is_end']}, OOS {w['oos_start']}~{w['oos_end']}")

        is_results = []
        for params in coint_grid:
            r, info = run_coint_fixed(full_dfs, *params, trading_start=w["is_start"])
            sr = r["sharpe"] if not np.isnan(r["sharpe"]) else -999
            is_results.append((*params, sr, r["n_pairs"]))

        positive = [x for x in is_results if x[-2] > 0]
        best = max(positive if positive else is_results, key=lambda x: x[-2])
        best_params = best[:4]; best_sr = best[-2]; best_npairs = best[-1]
        print(f"    Best IS: {best_params} SR={best_sr:.3f} pairs={best_npairs}")

        r_oos, pair_info = run_coint_fixed(full_dfs, *best_params, trading_start=w["oos_start"])
        print(f"    OOS: SR={r_oos['sharpe']:.3f} Ret={r_oos['return_pct']:.2f}% "
              f"DD={r_oos['max_dd_pct']:.2f}% Pairs={r_oos['n_pairs']} Trades={r_oos['n_trades']}")

        coint_results[w["name"]] = {
            "best_params": list(best_params), "is_sharpe": best_sr,
            "oos_sharpe": r_oos["sharpe"], "oos_return": r_oos["return_pct"],
            "oos_dd": r_oos["max_dd_pct"], "n_pairs": r_oos["n_pairs"],
            "n_trades": r_oos["n_trades"],
        }
        all_pair_info[w["name"]] = pair_info

    # Print pairs
    for wname, info in all_pair_info.items():
        if info:
            print(f"\n  {wname} top cointegrated pairs (beta clamped {BETA_MIN}-{BETA_MAX}):")
            for a, b, p, beta in info[:10]:
                print(f"    {a}/{b}: p={p:.4f} beta={beta:.3f}")

    # ================================================================
    # OU (fixed)
    # ================================================================
    print(f"\n{'='*60}")
    print("OU (fixed: W1 handling)")
    print(f"{'='*60}")

    ou_grid = list(product([180, 360, 720], [1.0, 1.5, 2.0], [0.01, 0.05]))
    ou_results = {}
    ou_theta = {}

    for w in WINDOWS:
        print(f"\n  {w['name']}: IS {w['is_start']}~{w['is_end']}, OOS {w['oos_start']}~{w['oos_end']}")

        is_results = []
        for params in ou_grid:
            r = run_ou_fixed(full_dfs, *params, trading_start=w["is_start"])
            sr = r["sharpe"] if not np.isnan(r["sharpe"]) else -999
            is_results.append((*params, sr))

        positive = [x for x in is_results if x[-1] > 0]
        best = max(positive if positive else is_results, key=lambda x: x[-1])
        best_params = best[:3]; best_sr = best[-1]
        print(f"    Best IS: {best_params} SR={best_sr:.3f}")

        r_oos = run_ou_fixed(full_dfs, *best_params, trading_start=w["oos_start"])
        print(f"    OOS: SR={r_oos['sharpe']:.3f} Ret={r_oos['return_pct']:.2f}% "
              f"DD={r_oos['max_dd_pct']:.2f}% Trades={r_oos['n_trades']}")

        ou_results[w["name"]] = {
            "best_params": list(best_params), "is_sharpe": best_sr,
            "oos_sharpe": r_oos["sharpe"], "oos_return": r_oos["return_pct"],
            "oos_dd": r_oos["max_dd_pct"], "n_trades": r_oos["n_trades"],
        }
        if r_oos.get("theta_stats"):
            ou_theta[w["name"]] = r_oos["theta_stats"]

    # Print theta
    for wname, ts in ou_theta.items():
        print(f"\n  {wname} OU theta (mean reversion speed):")
        for coin in sorted(ts.keys(), key=lambda c: -ts[c]["mean"])[:10]:
            print(f"    {coin}: theta={ts[coin]['mean']:.4f} +/- {ts[coin]['std']:.4f}")

    # ================================================================
    # Correlation with XSMom (W2 OOS)
    # ================================================================
    print(f"\n{'='*60}")
    print("Correlation with XSMom (W2 OOS = 2024)")
    print(f"{'='*60}")

    # Run XSMom on W2 OOS
    xsmom_dfs = {}
    for coin in ALL_28:
        df = load_8h(cache, coin, "2023-06-01", "2025-01-01")
        if df is not None:
            xsmom_dfs[coin] = df
    r_xs = run_xsmom(xsmom_dfs, 36, 5, 21, False, capital=10000.0)

    if r_xs:
        xs_eq = r_xs["equities"]
        xs_rets = pd.Series(xs_eq).pct_change().dropna().values

        # Cointegration W2 OOS equity
        best_coint_params = coint_results["W2"]["best_params"]
        r_c, _ = run_coint_fixed(full_dfs, *best_coint_params, trading_start="2024-01-01")
        if r_c and "equities" in r_c:
            c_rets = pd.Series(r_c["equities"]).pct_change().dropna().values
            ml = min(len(xs_rets), len(c_rets))
            if ml > 10 and np.std(c_rets[:ml]) > 0 and np.std(xs_rets[:ml]) > 0:
                corr = float(np.corrcoef(xs_rets[:ml], c_rets[:ml])[0, 1])
                print(f"  Cointegration vs XSMom: {corr:.3f}")

        # OU W2 OOS equity
        best_ou_params = ou_results["W2"]["best_params"]
        r_o = run_ou_fixed(full_dfs, *best_ou_params, trading_start="2024-01-01")
        if r_o and "equities" in r_o:
            o_rets = pd.Series(r_o["equities"]).pct_change().dropna().values
            ml = min(len(xs_rets), len(o_rets))
            if ml > 10 and np.std(o_rets[:ml]) > 0 and np.std(xs_rets[:ml]) > 0:
                corr = float(np.corrcoef(xs_rets[:ml], o_rets[:ml])[0, 1])
                print(f"  OU vs XSMom: {corr:.3f}")

        # OU vs Coint
        if r_c and r_o and "equities" in r_c and "equities" in r_o:
            ml = min(len(c_rets), len(o_rets))
            if ml > 10 and np.std(c_rets[:ml]) > 0 and np.std(o_rets[:ml]) > 0:
                corr = float(np.corrcoef(c_rets[:ml], o_rets[:ml])[0, 1])
                print(f"  Cointegration vs OU: {corr:.3f}")

    # ================================================================
    # Summary
    # ================================================================
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"\n  {'Strategy':<15} {'W1 OOS SR':>10} {'W1 Ret%':>10} {'W2 OOS SR':>10} {'W2 Ret%':>10} {'Match':>6}")
    print("  " + "-" * 63)

    for name, r in [("Coint (fixed)", coint_results), ("OU (fixed)", ou_results)]:
        w1 = r.get("W1", {}); w2 = r.get("W2", {})
        s1 = w1.get("oos_sharpe", "N/A"); s2 = w2.get("oos_sharpe", "N/A")
        r1 = w1.get("oos_return", "N/A"); r2 = w2.get("oos_return", "N/A")
        match = "YES" if w1.get("best_params") == w2.get("best_params") else "NO"
        s1s = f"{s1:.3f}" if isinstance(s1, (int, float)) else s1
        s2s = f"{s2:.3f}" if isinstance(s2, (int, float)) else s2
        r1s = f"{r1:.2f}" if isinstance(r1, (int, float)) else r1
        r2s = f"{r2:.2f}" if isinstance(r2, (int, float)) else r2
        print(f"  {name:<15} {s1s:>10} {r1s:>10} {s2s:>10} {r2s:>10} {match:>6}")

    # Save + Log
    save = {"coint": coint_results, "ou": ou_results,
            "coint_pairs": {k: v for k, v in all_pair_info.items()},
            "ou_theta": ou_theta}
    with open("sweep_results/coint_ou_fixed.json", "w") as f:
        json.dump(save, f, indent=2, default=str)

    log = f"\n## Cointegration + OU Fixed ({pd.Timestamp.now().strftime('%Y-%m-%d')})\n\n"
    log += "### Fixes Applied\n"
    log += f"- Cointegration: LOG prices, beta clamped [{BETA_MIN},{BETA_MAX}], "
    log += f"max {MAX_PAIR_PCT*100:.0f}% per pair, max {MAX_PAIRS} pairs\n"
    log += "- OU: handle insufficient warmup gracefully\n\n"
    log += "### Results\n"
    log += "| Strategy | W1 OOS SR | W1 Ret% | W2 OOS SR | W2 Ret% | Match |\n"
    log += "|----------|-----------|---------|-----------|---------|-------|\n"
    for name, r in [("Coint", coint_results), ("OU", ou_results)]:
        w1 = r.get("W1", {}); w2 = r.get("W2", {})
        s1 = w1.get("oos_sharpe"); s2 = w2.get("oos_sharpe")
        r1 = w1.get("oos_return"); r2 = w2.get("oos_return")
        match = "YES" if w1.get("best_params") == w2.get("best_params") else "NO"
        log += f"| {name} | {s1:.3f if s1 else 'N/A'} | {r1:.2f if r1 else 'N/A'} | "
        log += f"{s2:.3f if s2 else 'N/A'} | {r2:.2f if r2 else 'N/A'} | {match} |\n"

    if all_pair_info.get("W2"):
        log += "\n### Top Cointegrated Pairs (W2)\n"
        for a, b, p, beta in all_pair_info["W2"][:10]:
            log += f"- {a}/{b}: p={p:.4f} beta={beta:.3f}\n"

    if ou_theta.get("W2"):
        log += "\n### OU Theta (W2, top 10 by reversion speed)\n"
        ts = ou_theta["W2"]
        for coin in sorted(ts.keys(), key=lambda c: -ts[c]["mean"])[:10]:
            log += f"- {coin}: theta={ts[coin]['mean']:.4f}\n"

    with open("RESEARCH_LOG.md", "a", encoding="utf-8") as f:
        f.write(log)

    print(f"\n  Total: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
