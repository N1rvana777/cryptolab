#!/usr/bin/env python3
"""Final portfolio combination test with correct time alignment.

All strategies get warmup data BEFORE holdout start (2025-07-01).
All equity curves normalized to $10,000 at holdout start.
Same trading window for all strategies.
"""

import sys, os, json
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptolab.data.cache import ParquetCache
from cryptolab.backtest.metrics import sharpe_ratio, max_drawdown
from scripts.cross_sectional_momentum import load_8h, run_xsmom, ALL_28
from scripts.mean_reversion_experiment import run_donchian_b0
from scripts.portfolio_optimization import run_combo

cache = ParquetCache()

with open("sweep_results/meanrev_experiment.json") as f:
    mr_p = json.load(f).get("meanrev_best_params", {})
if os.path.exists("sweep_results/expanded_coins_v3.json"):
    with open("sweep_results/expanded_coins_v3.json") as f:
        mr_p.update(json.load(f).get("mr_params", {}))

n = len(ALL_28)
CAP = 10000.0 / n
PPY = 1096

# Load data with warmup prepended before holdout
WARMUP_START = "2025-01-15"  # 5.5 months before holdout
HOLDOUT_START = pd.Timestamp("2025-07-01")
HOLDOUT_END = "2026-04-01"

full_dfs = {}
for coin in ALL_28:
    df = load_8h(cache, coin, WARMUP_START, HOLDOUT_END)
    if df is not None:
        full_dfs[coin] = df

btc = full_dfs["BTC"]
ho_start_idx = len(btc[btc["timestamp"] < HOLDOUT_START])
ho_bars = len(btc) - ho_start_idx
print(f"Coins: {len(full_dfs)}, warmup bars: {ho_start_idx}, holdout bars: {ho_bars}")

# ============================================================
# A) Donchian: run on full data, extract holdout portion
# ============================================================
don_coin_eqs = []
don_tr = 0
DON_WARMUP = 396  # max_lb(336) + 60

for coin in ALL_28:
    df = full_dfs.get(coin)
    if df is None:
        continue
    r = run_donchian_b0(df, CAP, n, use_dynamic_slip=True)
    if r is None or np.isnan(r["sharpe"]):
        continue
    eq = r["equities"]
    ho_offset = ho_start_idx - DON_WARMUP
    if ho_offset < 0 or ho_offset >= len(eq):
        continue
    ho_eq = eq[ho_offset:]
    ho_eq = ho_eq / ho_eq[0] * CAP  # normalize to per-coin capital
    don_coin_eqs.append(ho_eq)
    don_tr += r["n_trades"]

# ============================================================
# B) MR: run via run_combo(don=0, mr=1) on full data
# ============================================================
mr_coin_eqs = []
mr_tr = 0

for coin in ALL_28:
    df = full_dfs.get(coin)
    if df is None:
        continue
    p = mr_p.get(coin)
    if not p or len(p) < 4:
        continue
    combo_warmup = max(336 + 60, p[0] + 60, 100)
    r = run_combo(df, p[0], p[1], 0.50, p[3], CAP, n,
                  leverage=3.0, don_weight=0.0, mr_weight=1.0)
    if r is None or np.isnan(r["sharpe"]):
        continue
    eq = r["equities"]
    ho_offset = ho_start_idx - combo_warmup
    if ho_offset < 0 or ho_offset >= len(eq):
        continue
    ho_eq = eq[ho_offset:]
    ho_eq = ho_eq / ho_eq[0] * CAP
    mr_coin_eqs.append(ho_eq)
    mr_tr += r["n_trades"]

# ============================================================
# C) XSMom: run on full data, extract holdout portion
# ============================================================
XS_WARMUP = 46

r_xs = run_xsmom(full_dfs, 36, 5, 21, False, capital=10000.0)
xs_eq_full = r_xs["equities"]
xs_ho_offset = ho_start_idx - XS_WARMUP
xs_eq_ho = xs_eq_full[xs_ho_offset:]
xs_eq_ho = xs_eq_ho / xs_eq_ho[0] * 10000  # normalize to $10,000
xs_tr = r_xs["n_trades"]

# ============================================================
# Align all to common length
# ============================================================
don_ml = min(len(e) for e in don_coin_eqs)
mr_ml = min(len(e) for e in mr_coin_eqs)
common_len = min(don_ml, mr_ml, len(xs_eq_ho))

don_eq = sum(e[:common_len] for e in don_coin_eqs)
mr_eq = sum(e[:common_len] for e in mr_coin_eqs)
xs_eq = xs_eq_ho[:common_len]

print(f"Don: {len(don_coin_eqs)} coins, {don_ml} bars -> start={don_eq[0]:.2f} end={don_eq[-1]:.2f}")
print(f"MR:  {len(mr_coin_eqs)} coins, {mr_ml} bars -> start={mr_eq[0]:.2f} end={mr_eq[-1]:.2f}")
print(f"XS:  {len(xs_eq)} bars -> start={xs_eq[0]:.2f} end={xs_eq[-1]:.2f}")
print(f"Common: {common_len} bars ({common_len*8/24:.0f} days)")

# Normalize to return multipliers
don_r = don_eq / don_eq[0]
mr_r = mr_eq / mr_eq[0]
xs_r = xs_eq / xs_eq[0]

# ============================================================
# Results
# ============================================================
def show(label, eq_arr, trades=0):
    eq_s = pd.Series(eq_arr)
    sr = sharpe_ratio(eq_s, PPY)
    _, dd = max_drawdown(eq_s)
    ret = (eq_arr[-1] / eq_arr[0] - 1) * 100
    print(f"  {label:<35} SR={sr:>7.3f} Ret={ret:>7.2f}% DD={dd:>6.2f}% Tr={trades:>5}")
    return sr, ret, dd

print(f"\n{'='*75}")
print(f"All from $10,000 on 2025-07-01, {common_len} bars ({common_len*8/24:.0f} days)")
print(f"{'='*75}")

results = []
combos = [
    ("A) Pure Donchian 28", don_eq, don_tr),
    ("B) Pure MR 28 (ez=0.50)", mr_eq, mr_tr),
    ("C) Pure XSMom 28", xs_eq, xs_tr),
    ("D) Don+MR 50/50", (0.5*don_r + 0.5*mr_r)*10000, don_tr+mr_tr),
    ("E) Don+XSMom 50/50", (0.5*don_r + 0.5*xs_r)*10000, don_tr+xs_tr),
    ("F) MR+XSMom 50/50", (0.5*mr_r + 0.5*xs_r)*10000, mr_tr+xs_tr),
    ("G) Don+MR+XSMom 33/33/33", (don_r/3 + mr_r/3 + xs_r/3)*10000, don_tr+mr_tr+xs_tr),
    ("H) Don50+MR25+XSMom25", (0.5*don_r + 0.25*mr_r + 0.25*xs_r)*10000, don_tr+mr_tr+xs_tr),
    ("I) Don25+MR25+XSMom50", (0.25*don_r + 0.25*mr_r + 0.5*xs_r)*10000, don_tr+mr_tr+xs_tr),
]

for label, eq, tr in combos:
    sr, ret, dd = show(label, eq, tr)
    results.append((label, sr, ret, dd, tr))

# Sanity checks
d_ret = results[0][2]
m_ret = results[1][2]
x_ret = results[2][2]
print(f"\nSanity checks:")
print(f"  D) expected: ({d_ret:.2f}+{m_ret:.2f})/2 = {(d_ret+m_ret)/2:.2f}%, actual: {results[3][2]:.2f}%")
print(f"  E) expected: ({d_ret:.2f}+{x_ret:.2f})/2 = {(d_ret+x_ret)/2:.2f}%, actual: {results[4][2]:.2f}%")
print(f"  G) expected: ({d_ret:.2f}+{m_ret:.2f}+{x_ret:.2f})/3 = {(d_ret+m_ret+x_ret)/3:.2f}%, actual: {results[6][2]:.2f}%")

# ============================================================
# RESEARCH_LOG
# ============================================================
log = f"\n## Portfolio Combinations - Final ({pd.Timestamp.now().strftime('%Y-%m-%d')})\n\n"
log += f"### Methodology\n"
log += f"- Warmup data prepended from 2025-01-15 (before holdout)\n"
log += f"- All strategies start trading 2025-07-01, equity = $10,000\n"
log += f"- Common window: {common_len} bars ({common_len*8/24:.0f} days)\n\n"
log += f"### Results\n"
log += f"| Portfolio | Sharpe | Return% | MaxDD% | Trades |\n"
log += f"|-----------|--------|---------|--------|--------|\n"
for label, sr, ret, dd, tr in results:
    log += f"| {label} | {sr:.3f} | {ret:.2f} | {dd:.2f} | {tr} |\n"

log += f"\n### Sanity Checks\n"
log += f"- D) ({d_ret:.2f}+{m_ret:.2f})/2 = {(d_ret+m_ret)/2:.2f}% vs actual {results[3][2]:.2f}%\n"
log += f"- E) ({d_ret:.2f}+{x_ret:.2f})/2 = {(d_ret+x_ret)/2:.2f}% vs actual {results[4][2]:.2f}%\n"
log += f"- G) ({d_ret:.2f}+{m_ret:.2f}+{x_ret:.2f})/3 = {(d_ret+m_ret+x_ret)/3:.2f}% vs actual {results[6][2]:.2f}%\n"

best = max(results, key=lambda x: x[1])
log += f"\nBest Sharpe: **{best[0]}** ({best[1]:.3f}, {best[2]:.2f}%, MaxDD {best[3]:.2f}%)\n"

with open("RESEARCH_LOG.md", "a", encoding="utf-8") as f:
    f.write(log)
print("\nWritten to RESEARCH_LOG.md")
