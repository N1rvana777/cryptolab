#!/usr/bin/env python3
"""Final Holdout: PCA 8H + XSMom + Z-score MR combos.

All strategies zero positions at holdout start, same date, $10,000.
"""

import sys, os, time, json, gc
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptolab.data.cache import ParquetCache
from cryptolab.backtest.metrics import sharpe_ratio, max_drawdown
from scripts.donchian_full_sweep import resample_ohlcv
from scripts.advanced_coint import run_pca_ou, load_freq, ALL_28, PPY_MAP
from scripts.cross_sectional_momentum import run_xsmom
from scripts.portfolio_optimization import run_combo
from scripts.mean_reversion_experiment import compute_dynamic_slippage

PPY = 1096
HOLDOUT_START = "2025-07-01"
HOLDOUT_END = "2026-04-01"


def load_8h(cache, coin, start, end):
    df = cache.read("okx", coin, "1h")
    if df is None or df.empty: return None
    if df["timestamp"].dt.tz is not None:
        df["timestamp"] = df["timestamp"].dt.tz_localize(None)
    df8 = resample_ohlcv(df, "8h")
    mask = (df8["timestamp"] >= pd.Timestamp(start)) & (df8["timestamp"] < pd.Timestamp(end))
    out = df8[mask].reset_index(drop=True)
    return out if len(out) > 50 else None


def fmt(v, f=".3f"):
    if v is None: return "N/A"
    try: return f"{v:{f}}"
    except: return str(v)


def main():
    t0 = time.time()
    cache = ParquetCache()

    # Load MR params
    with open("sweep_results/meanrev_experiment.json") as f:
        mr_params = json.load(f).get("meanrev_best_params", {})
    if Path("sweep_results/expanded_coins_v3.json").exists():
        with open("sweep_results/expanded_coins_v3.json") as f:
            mr_params.update(json.load(f).get("mr_params", {}))

    print("Loading data...", flush=True)

    # ================================================================
    # A) PCA 8H - zero position start at holdout
    # ================================================================
    print("\nA) PCA 8H...", flush=True)
    # Load with warmup (PCA needs OU_window=180 + recalib=180 bars before holdout)
    pca_dfs = {}
    for coin in ALL_28:
        df = load_freq(cache, coin, "8h", "2019-01-01", HOLDOUT_END)
        if df is not None:
            pca_dfs[coin] = df

    r_pca = run_pca_ou(pca_dfs, 5, 1.5, 0.25, 180, 180,
                       HOLDOUT_START, "8h", capital=10000.0)
    pca_eq = r_pca["equities"]
    pca_eq = pca_eq / pca_eq[0] * 10000
    print(f"  PCA: {len(pca_eq)} bars, start=${pca_eq[0]:.2f}, end=${pca_eq[-1]:.2f}, "
          f"ret={(pca_eq[-1]/pca_eq[0]-1)*100:.2f}%")

    gc.collect()

    # ================================================================
    # B) XSMom - clean start (load only near holdout)
    # ================================================================
    print("B) XSMom...", flush=True)
    xs_dfs = {}
    for coin in ALL_28:
        df = load_8h(cache, coin, "2025-06-01", HOLDOUT_END)  # 1 month warmup
        if df is not None:
            xs_dfs[coin] = df

    r_xs = run_xsmom(xs_dfs, 36, 5, 21, False, capital=10000.0)
    xs_eq = r_xs["equities"]
    xs_eq = xs_eq / xs_eq[0] * 10000
    print(f"  XSMom: {len(xs_eq)} bars, start=${xs_eq[0]:.2f}, end=${xs_eq[-1]:.2f}, "
          f"ret={(xs_eq[-1]/xs_eq[0]-1)*100:.2f}%")

    gc.collect()

    # ================================================================
    # MR - clean start
    # ================================================================
    print("MR...", flush=True)
    n_coins = len(ALL_28)
    CAP_PC = 10000.0 / n_coins
    mr_coin_eqs = []
    mr_tr = 0
    for coin in ALL_28:
        df_full = load_8h(cache, coin, "2019-01-01", HOLDOUT_END)
        if df_full is None: continue
        p = mr_params.get(coin)
        if not p or len(p) < 4: continue

        ts = df_full["timestamp"].values
        ho_idx = 0
        for i in range(len(ts)):
            if ts[i] >= np.datetime64(HOLDOUT_START):
                ho_idx = i; break

        warmup = max(336 + 60, p[0] + 60, 100)
        if ho_idx < warmup: continue

        df_slice = df_full.iloc[ho_idx - warmup:].reset_index(drop=True)
        r = run_combo(df_slice, p[0], p[1], 0.50, p[3], CAP_PC, n_coins,
                      leverage=3.0, don_weight=0.0, mr_weight=1.0)
        if r and not np.isnan(r["sharpe"]):
            eq = r["equities"]
            eq = eq / eq[0] * CAP_PC
            mr_coin_eqs.append(eq)
            mr_tr += r["n_trades"]

    mr_ml = min(len(e) for e in mr_coin_eqs)
    mr_eq = sum(e[:mr_ml] for e in mr_coin_eqs)
    mr_eq = mr_eq / mr_eq[0] * 10000
    print(f"  MR: {len(mr_coin_eqs)} coins, {mr_ml} bars, start=${mr_eq[0]:.2f}, end=${mr_eq[-1]:.2f}, "
          f"ret={(mr_eq[-1]/mr_eq[0]-1)*100:.2f}%")

    gc.collect()

    # ================================================================
    # Align all to common length
    # ================================================================
    common_len = min(len(pca_eq), len(xs_eq), len(mr_eq))
    pca_eq = pca_eq[:common_len]
    xs_eq = xs_eq[:common_len]
    mr_eq = mr_eq[:common_len]

    # Normalize return multipliers
    pca_r = pca_eq / pca_eq[0]
    xs_r = xs_eq / xs_eq[0]
    mr_r = mr_eq / mr_eq[0]

    print(f"\nCommon length: {common_len} bars ({common_len*8/24:.0f} days)")

    # ================================================================
    # Build all portfolios
    # ================================================================
    def metrics(eq, label, trades=0):
        eq_s = pd.Series(eq)
        sr = sharpe_ratio(eq_s, PPY)
        _, dd = max_drawdown(eq_s)
        ret = (eq[-1] / eq[0] - 1) * 100
        return label, sr, ret, dd, trades

    pca_ret = (pca_eq[-1] / pca_eq[0] - 1) * 100
    xs_ret = (xs_eq[-1] / xs_eq[0] - 1) * 100
    mr_ret = (mr_eq[-1] / mr_eq[0] - 1) * 100

    results = []
    results.append(metrics(pca_eq, "A) PCA 8H", r_pca["n_trades"]))
    results.append(metrics(xs_eq, "B) XSMom", r_xs["n_trades"]))
    results.append(metrics((0.5*pca_r + 0.5*xs_r)*10000, "C) PCA+XSMom 50/50",
                           r_pca["n_trades"] + r_xs["n_trades"]))
    results.append(metrics((pca_r/3 + xs_r/3 + mr_r/3)*10000, "D) PCA+XSMom+MR 33ea",
                           r_pca["n_trades"] + r_xs["n_trades"] + mr_tr))
    results.append(metrics((0.6*pca_r + 0.4*xs_r)*10000, "E) PCA60+XSMom40",
                           r_pca["n_trades"] + r_xs["n_trades"]))
    results.append(metrics((0.4*pca_r + 0.6*xs_r)*10000, "F) PCA40+XSMom60",
                           r_pca["n_trades"] + r_xs["n_trades"]))

    # ================================================================
    # Print
    # ================================================================
    print(f"\n{'='*70}")
    print(f"HOLDOUT ({common_len} bars, all from $10,000)")
    print(f"{'='*70}")
    print(f"\n  {'Portfolio':<25} {'Sharpe':>8} {'Ret%':>8} {'MaxDD%':>8} {'Trades':>7}")
    print("  " + "-" * 58)
    for label, sr, ret, dd, tr in results:
        print(f"  {label:<25} {sr:>8.3f} {ret:>8.2f} {dd:>8.2f} {tr:>7}")

    # Sanity checks
    print(f"\nSanity checks:")
    print(f"  C) ({pca_ret:.2f}+{xs_ret:.2f})/2 = {(pca_ret+xs_ret)/2:.2f}% vs actual {results[2][2]:.2f}%")
    print(f"  D) ({pca_ret:.2f}+{xs_ret:.2f}+{mr_ret:.2f})/3 = {(pca_ret+xs_ret+mr_ret)/3:.2f}% vs actual {results[3][2]:.2f}%")
    print(f"  E) 0.6*{pca_ret:.2f}+0.4*{xs_ret:.2f} = {0.6*pca_ret+0.4*xs_ret:.2f}% vs actual {results[4][2]:.2f}%")
    print(f"  F) 0.4*{pca_ret:.2f}+0.6*{xs_ret:.2f} = {0.4*pca_ret+0.6*xs_ret:.2f}% vs actual {results[5][2]:.2f}%")

    # Correlation
    pca_rets = pd.Series(pca_eq).pct_change().dropna().values
    xs_rets = pd.Series(xs_eq).pct_change().dropna().values
    mr_rets = pd.Series(mr_eq).pct_change().dropna().values
    ml = min(len(pca_rets), len(xs_rets), len(mr_rets))

    print(f"\nDaily return correlations (holdout):")
    if ml > 10:
        corr_px = float(np.corrcoef(pca_rets[:ml], xs_rets[:ml])[0, 1])
        corr_pm = float(np.corrcoef(pca_rets[:ml], mr_rets[:ml])[0, 1])
        corr_xm = float(np.corrcoef(xs_rets[:ml], mr_rets[:ml])[0, 1])
        print(f"  PCA vs XSMom: {corr_px:.3f}")
        print(f"  PCA vs MR:    {corr_pm:.3f}")
        print(f"  XSMom vs MR:  {corr_xm:.3f}")

    # ================================================================
    # Save + Log
    # ================================================================
    save = [{"label": l, "sharpe": s, "return_pct": r, "max_dd_pct": d, "n_trades": t}
            for l, s, r, d, t in results]
    with open("sweep_results/final_holdout_v2b.json", "w") as f:
        json.dump(save, f, indent=2)

    log = f"\n## PCA + XSMom Holdout ({pd.Timestamp.now().strftime('%Y-%m-%d')})\n\n"
    log += f"Config: PCA 8H K=5, entry=1.5, exit=0.25, OU=180, recalib=180\n\n"
    log += "| Portfolio | Sharpe | Return% | MaxDD% | Trades |\n"
    log += "|-----------|--------|---------|--------|--------|\n"
    for l, s, r, d, t in results:
        log += f"| {l} | {s:.3f} | {r:.2f} | {d:.2f} | {t} |\n"
    log += f"\nSanity: C) ({pca_ret:.2f}+{xs_ret:.2f})/2={results[2][2]:.2f}% OK\n"
    if ml > 10:
        log += f"\nCorrelations: PCA-XSMom={corr_px:.3f}, PCA-MR={corr_pm:.3f}, XSMom-MR={corr_xm:.3f}\n"

    with open("RESEARCH_LOG.md", "a", encoding="utf-8") as f:
        f.write(log)

    print(f"\n  Total: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
