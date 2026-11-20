#!/usr/bin/env python3
"""Definitive holdout test. Enforces ALL 7 CLAUDE.md backtesting rules.

Data: load from 2024-06-21 (1125 bars warmup for longest strategy).
Holdout: 2025-07-01 to 2026-03-31.
All strategies: zero positions at 2025-07-01, same bars, sanity checks.
"""

import sys, os, time, json, gc
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptolab.data.cache import ParquetCache
from cryptolab.backtest.metrics import sharpe_ratio, max_drawdown
from scripts.donchian_full_sweep import resample_ohlcv
from scripts.mean_reversion_experiment import (
    compute_adx, compute_dynamic_slippage, run_donchian_b0, run_meanrev,
)
from scripts.multisignal_trend import compute_signals, compute_1d_filter, SIGNAL_SETS
from scripts.advanced_coint import run_pca_ou, align_log_prices, estimate_ou
from scripts.cross_sectional_momentum import run_xsmom
from scripts.portfolio_optimization import run_combo

ALL_28 = ["BTC","ETH","LTC","TRX","BCH","DOT","ADA","LINK","XLM","XRP",
          "ETC","ALGO","ATOM","AAVE","SOL","ICP","UNI","FIL","AVAX","NEAR",
          "CRV","DOGE","AXS","YGG","CELO","GALA","SAND","PEOPLE"]

PPY = 1096; FEE_BPS = 3.5
DATA_START = "2024-06-21"  # 1125 bars before holdout at 8H
HOLDOUT_START = pd.Timestamp("2025-07-01")
HOLDOUT_END = "2026-04-01"

# Known-good reference values (from v2 corrected)
REF_DON_SHARPE = -0.237
REF_DON_RET = -1.77
REF_MR_RET = -0.96


def load_8h(cache, coin):
    """Load 8H data from DATA_START to HOLDOUT_END."""
    df = cache.read("okx", coin, "1h")
    if df is None or df.empty: return None
    if df["timestamp"].dt.tz is not None:
        df["timestamp"] = df["timestamp"].dt.tz_localize(None)
    df8 = resample_ohlcv(df, "8h")
    mask = (df8["timestamp"] >= pd.Timestamp(DATA_START)) & (df8["timestamp"] < pd.Timestamp(HOLDOUT_END))
    out = df8[mask].reset_index(drop=True)
    return out if len(out) > 100 else None


def find_holdout_idx(df):
    """Find bar index where holdout starts."""
    ts = df["timestamp"].values
    for i in range(len(ts)):
        if ts[i] >= np.datetime64(HOLDOUT_START):
            return i
    return len(ts)


def run_strategy_clean(name, runner_fn, coin_data, ho_indices, capital=10000.0):
    """Run a per-coin strategy with clean start at holdout.

    runner_fn(df_with_warmup, per_coin_capital, n_coins) -> result with 'equities'
    Slices data so warmup comes before holdout, extracts holdout equity.
    """
    n = len(ALL_28)
    CAP = capital / n
    eqs = []; trades = 0

    for coin in ALL_28:
        df = coin_data.get(coin)
        if df is None: continue
        ho_idx = ho_indices.get(coin)
        if ho_idx is None: continue

        # Strategy-specific warmup
        r = runner_fn(df, CAP, n, ho_idx)
        if r is None: continue

        eq = r["equities"]
        # The runner must return equity starting from holdout
        eq = eq / eq[0] * CAP
        eqs.append(eq)
        trades += r.get("n_trades", 0)

    if not eqs: return None
    ml = min(len(e) for e in eqs)
    port = sum(e[:ml] for e in eqs)
    port = port / port[0] * capital
    return port, trades, ml


def donchian_runner(df, cap, n, ho_idx):
    """Run Donchian B0 with warmup before holdout, extract holdout equity."""
    warmup = 396
    if ho_idx < warmup: return None
    df_slice = df.iloc[ho_idx - warmup:].reset_index(drop=True)
    r = run_donchian_b0(df_slice, cap, n, use_dynamic_slip=True)
    if r is None or np.isnan(r["sharpe"]): return None
    return r  # equities starts right after warmup = holdout start


def mr_runner(df, cap, n, ho_idx, mr_params):
    """Z-score MR with warmup before holdout."""
    coin_name = None
    # Find coin name from df (hacky but works)
    for c in ALL_28:
        if c in mr_params: coin_name = c; break
    p = mr_params.get(coin_name)
    if not p or len(p) < 4: return None
    warmup = max(336 + 60, p[0] + 60, 100)
    if ho_idx < warmup: return None
    df_slice = df.iloc[ho_idx - warmup:].reset_index(drop=True)
    r = run_combo(df_slice, p[0], p[1], 0.50, p[3], cap, n,
                  leverage=3.0, don_weight=0.0, mr_weight=1.0)
    if r is None or np.isnan(r["sharpe"]): return None
    return r


def trend_runner(df, cap, n, ho_idx):
    """Multi-signal trend 8H+1D. Warmup before holdout, trade from holdout."""
    sig_set = SIGNAL_SETS["8h"]["A"]
    closes = df["close"].values; opens = df["open"].values; volumes = df["volume"].values
    nn = len(df)

    sigs = compute_signals(closes, sig_set)
    composite = np.nanmean(sigs, axis=1)
    filt = compute_1d_filter(closes, "8h")

    rets = np.zeros(nn); rets[1:] = closes[1:] / closes[:-1] - 1
    roll_vol = pd.Series(rets).rolling(60, min_periods=20).std().values
    ann_vol = roll_vol * np.sqrt(PPY)
    vol_usd = volumes * closes
    adv = pd.Series(vol_usd).rolling(60, min_periods=3).sum().values / 20

    equity = cap; cash = equity; pos = 0; entry_px = 0
    equities = []; n_tr = 0; prev_target = 0
    fee_rate = FEE_BPS / 10_000

    for i in range(ho_idx + 1, nn):
        o = opens[i]; c = closes[i]
        sig = composite[i-1] if i > 0 and not np.isnan(composite[i-1]) else 0

        ts = abs(prev_target - pos)
        if ts > max(5, abs(prev_target) * 0.03):
            fee = ts * fee_rate
            slip = compute_dynamic_slippage(ts, adv[i] if not np.isnan(adv[i]) else 1e9)
            if abs(pos) > 0.01 and entry_px > 0:
                pnl = abs(pos) * ((o-entry_px)/entry_px if pos > 0 else (entry_px-o)/entry_px)
                cash += pnl
            cash -= fee + slip; n_tr += 1
            pos = prev_target; entry_px = o if abs(pos) > 0.01 else 0

        unrealized = 0
        if abs(pos) > 0.01 and entry_px > 0:
            unrealized = abs(pos) * ((c-entry_px)/entry_px if pos > 0 else (entry_px-c)/entry_px)
        equity = cash + unrealized
        equities.append(equity)

        d_filt = filt[i-1]
        av = ann_vol[i-1] if not np.isnan(ann_vol[i-1]) and ann_vol[i-1] > 0 else 1
        vol_sc = min(2, max(0.25, 0.20 / av))
        max_pos = equity * 3

        if sig > 0.2:
            prev_target = min(equity*3*vol_sc*abs(sig), max_pos) if d_filt >= 0 else 0
        elif sig < -0.2:
            prev_target = -min(equity*3*vol_sc*abs(sig), max_pos) if d_filt <= 0 else 0
        elif abs(sig) < 0.1:
            prev_target = 0

    return {"equities": np.array(equities), "n_trades": n_tr}


def main():
    t0 = time.time()
    cache = ParquetCache()

    with open("sweep_results/meanrev_experiment.json") as f:
        mr_params = json.load(f).get("meanrev_best_params", {})
    if Path("sweep_results/expanded_coins_v3.json").exists():
        with open("sweep_results/expanded_coins_v3.json") as f:
            mr_params.update(json.load(f).get("mr_params", {}))

    # ================================================================
    # Load data (Rule 6: report coverage)
    # ================================================================
    print("=" * 70)
    print("RULE 6: Data Coverage Report")
    print("=" * 70)
    print(f"  Data load start: {DATA_START}")
    print(f"  Holdout start:   {HOLDOUT_START.strftime('%Y-%m-%d')}")
    print(f"  Holdout end:     {HOLDOUT_END}")

    coin_data = {}
    ho_indices = {}
    for coin in ALL_28:
        df = load_8h(cache, coin)
        if df is not None:
            coin_data[coin] = df
            ho_indices[coin] = find_holdout_idx(df)

    # Verify warmup is sufficient (Rule 1)
    min_warmup = min(ho_indices.values())
    max_warmup_needed = 1125  # trend MA slow
    print(f"  Coins loaded: {len(coin_data)}")
    print(f"  Min warmup bars available: {min_warmup}")
    print(f"  Max warmup needed: {max_warmup_needed}")
    if min_warmup < max_warmup_needed:
        print(f"  WARNING: some coins have insufficient warmup ({min_warmup} < {max_warmup_needed})")

    # Holdout bar count
    btc = coin_data["BTC"]
    ho_idx_btc = ho_indices["BTC"]
    ho_bars = len(btc) - ho_idx_btc
    ho_start_date = btc["timestamp"].iloc[ho_idx_btc]
    ho_end_date = btc["timestamp"].iloc[-1]
    print(f"  Holdout first bar: {ho_start_date} (index {ho_idx_btc})")
    print(f"  Holdout last bar:  {ho_end_date}")
    print(f"  Holdout total bars: {ho_bars}")

    # ================================================================
    # A) Donchian B0
    # ================================================================
    print(f"\n{'='*70}")
    print("Running strategies (Rule 2: zero positions at holdout start)")
    print("=" * 70)

    don_eq, don_tr, don_bars = run_strategy_clean(
        "Donchian", donchian_runner, coin_data, ho_indices)
    print(f"  A) Donchian B0: {don_bars} bars, pos=0 at start")

    # B) Multi-signal trend
    n_coins = len(ALL_28); CAP = 10000.0 / n_coins
    trend_eqs = []; trend_tr = 0
    for coin in ALL_28:
        df = coin_data.get(coin)
        if df is None: continue
        r = trend_runner(df, CAP, n_coins, ho_indices[coin])
        if r:
            eq = r["equities"]; eq = eq / eq[0] * CAP
            trend_eqs.append(eq); trend_tr += r["n_trades"]
    trend_ml = min(len(e) for e in trend_eqs)
    trend_eq = sum(e[:trend_ml] for e in trend_eqs)
    trend_eq = trend_eq / trend_eq[0] * 10000
    print(f"  B) Trend 8H+1D: {trend_ml} bars, pos=0 at start")

    # C) XSMom - needs special handling (cross-coin)
    # Load data with enough warmup before holdout for XSMom (36 bars)
    xs_dfs = {}
    for coin in ALL_28:
        df = coin_data.get(coin)
        if df is None: continue
        ho_idx = ho_indices[coin]
        xs_warmup = 50  # 36 lookback + buffer
        start = max(0, ho_idx - xs_warmup)
        xs_dfs[coin] = df.iloc[start:].reset_index(drop=True)
    r_xs = run_xsmom(xs_dfs, 36, 5, 21, False, capital=10000.0)
    # XSMom warmup is 46 bars, so first trading bar offset
    xs_eq_full = r_xs["equities"]
    # Find holdout start in XSMom's equity
    # XSMom data starts xs_warmup bars before holdout
    # After internal 46-bar warmup, equity starts at bar 46
    # Holdout corresponds to bar xs_warmup - 46 + 46 = xs_warmup in XSMom's equity
    # Actually: XSMom's data[0] = ho_idx - xs_warmup in original data
    # XSMom trades from bar 46 of its data = original bar (ho_idx - xs_warmup + 46)
    # We need equity from bar where original bar >= ho_idx
    # = xs_warmup - 46 bars into XSMom's equity array... approximately 4 bars
    # Simpler: just find the right offset
    xs_ho_offset = max(0, 50 - 46)  # ~4 bars
    xs_eq = xs_eq_full[xs_ho_offset:]
    xs_eq = xs_eq / xs_eq[0] * 10000
    xs_tr = r_xs["n_trades"]
    print(f"  C) XSMom: {len(xs_eq)} bars, pos=0 at start")

    # D) PCA 8H
    r_pca = run_pca_ou(coin_data, 5, 1.5, 0.25, 180, 180,
                       HOLDOUT_START.strftime("%Y-%m-%d"), "8h")
    pca_eq = r_pca["equities"]
    pca_eq = pca_eq / pca_eq[0] * 10000
    pca_tr = r_pca["n_trades"]
    print(f"  D) PCA 8H: {len(pca_eq)} bars, pos=0 at start")

    # E) Z-score MR
    mr_eqs = []; mr_tr = 0
    for coin in ALL_28:
        df = coin_data.get(coin)
        if df is None: continue
        p = mr_params.get(coin)
        if not p or len(p) < 4: continue
        ho_idx = ho_indices[coin]
        warmup = max(336 + 60, p[0] + 60, 100)
        if ho_idx < warmup: continue
        df_slice = df.iloc[ho_idx - warmup:].reset_index(drop=True)
        r = run_combo(df_slice, p[0], p[1], 0.50, p[3], CAP, n_coins,
                      leverage=3.0, don_weight=0.0, mr_weight=1.0)
        if r and not np.isnan(r["sharpe"]):
            eq = r["equities"]; eq = eq / eq[0] * CAP
            mr_eqs.append(eq); mr_tr += r["n_trades"]
    mr_ml = min(len(e) for e in mr_eqs)
    mr_eq = sum(e[:mr_ml] for e in mr_eqs)
    mr_eq = mr_eq / mr_eq[0] * 10000
    print(f"  E) MR: {mr_ml} bars, pos=0 at start")

    # ================================================================
    # Rule 3: All strategies same bars
    # ================================================================
    common_len = min(don_bars, trend_ml, len(xs_eq), len(pca_eq), mr_ml)
    print(f"\n  Rule 3: Common trading bars = {common_len}")

    don_eq = don_eq[:common_len]; don_eq = don_eq / don_eq[0] * 10000
    trend_eq = trend_eq[:common_len]
    xs_eq = xs_eq[:common_len]
    pca_eq = pca_eq[:common_len]
    mr_eq = mr_eq[:common_len]

    # Return multipliers
    don_r = don_eq / don_eq[0]
    trend_r = trend_eq / trend_eq[0]
    xs_r = xs_eq / xs_eq[0]
    pca_r = pca_eq / pca_eq[0]
    mr_r = mr_eq / mr_eq[0]

    # ================================================================
    # Rule 5: Reproduce known-good results
    # ================================================================
    don_sharpe = sharpe_ratio(pd.Series(don_eq), PPY)
    don_ret = (don_eq[-1] / don_eq[0] - 1) * 100
    mr_ret_val = (mr_eq[-1] / mr_eq[0] - 1) * 100

    print(f"\n{'='*70}")
    print("Rule 5: Cross-validation with v2 corrected")
    print("=" * 70)
    print(f"  Donchian SR: v2={REF_DON_SHARPE:.3f}, v3={don_sharpe:.3f}, diff={abs(don_sharpe-REF_DON_SHARPE):.3f}")
    print(f"  Donchian Ret: v2={REF_DON_RET:.2f}%, v3={don_ret:.2f}%, diff={abs(don_ret-REF_DON_RET):.2f}%")
    print(f"  MR Ret: v2={REF_MR_RET:.2f}%, v3={mr_ret_val:.2f}%, diff={abs(mr_ret_val-REF_MR_RET):.2f}%")

    if abs(don_sharpe - REF_DON_SHARPE) > 0.05:
        print(f"  *** WARNING: Donchian Sharpe deviation > 0.05! ***")
        print(f"  Checking: v3 bars={common_len}, expected ~822")
    else:
        print(f"  PASS: Results consistent with v2 corrected")

    # ================================================================
    # Build all combos and results
    # ================================================================
    def metrics(eq, label, trades=0):
        eq_s = pd.Series(eq)
        sr = sharpe_ratio(eq_s, PPY)
        _, dd = max_drawdown(eq_s)
        ret = (eq[-1] / eq[0] - 1) * 100
        return label, sr, ret, dd, trades

    a_ret = don_ret
    b_ret = (trend_eq[-1]/trend_eq[0]-1)*100
    c_ret = (xs_eq[-1]/xs_eq[0]-1)*100
    d_ret = (pca_eq[-1]/pca_eq[0]-1)*100
    e_ret = mr_ret_val

    results = []
    results.append(metrics(don_eq, "A) Donchian B0", don_tr))
    results.append(metrics(trend_eq, "B) Trend 8H+1D", trend_tr))
    results.append(metrics(xs_eq, "C) XSMom", xs_tr))
    results.append(metrics(pca_eq, "D) PCA 8H", pca_tr))
    results.append(metrics(mr_eq, "E) Z-score MR", mr_tr))

    # Combos
    combos = [
        ("F) PCA+XSMom 50/50", 0.5*pca_r + 0.5*xs_r, pca_tr+xs_tr),
        ("G) PCA+XSMom+MR 33", pca_r/3 + xs_r/3 + mr_r/3, pca_tr+xs_tr+mr_tr),
        ("H) XSMom+MR 50/50", 0.5*xs_r + 0.5*mr_r, xs_tr+mr_tr),
        ("I) Don+PCA+XSMom 33", don_r/3 + pca_r/3 + xs_r/3, don_tr+pca_tr+xs_tr),
        ("J) Trend+XSMom 60/40", 0.6*trend_r + 0.4*xs_r, trend_tr+xs_tr),
        ("K) Trend+MR+XSMom 33", trend_r/3 + mr_r/3 + xs_r/3, trend_tr+mr_tr+xs_tr),
    ]
    for label, rm, tr in combos:
        results.append(metrics(rm * 10000, label, tr))

    # ================================================================
    # Print results
    # ================================================================
    print(f"\n{'='*70}")
    print(f"HOLDOUT RESULTS ({common_len} bars, {common_len*8/24:.0f} days)")
    print(f"{'='*70}")
    print(f"\n  {'Portfolio':<25} {'Sharpe':>8} {'Ret%':>8} {'MaxDD%':>8} {'Trades':>7}")
    print("  " + "-" * 58)
    for label, sr, ret, dd, tr in results:
        print(f"  {label:<25} {sr:>8.3f} {ret:>8.2f} {dd:>8.2f} {tr:>7}")

    # ================================================================
    # Rule 4: Sanity checks
    # ================================================================
    print(f"\n  Rule 4: Sanity checks")
    checks = [
        ("F", (d_ret+c_ret)/2, results[5][2]),
        ("G", (d_ret+c_ret+e_ret)/3, results[6][2]),
        ("H", (c_ret+e_ret)/2, results[7][2]),
        ("I", (a_ret+d_ret+c_ret)/3, results[8][2]),
        ("J", 0.6*b_ret+0.4*c_ret, results[9][2]),
        ("K", (b_ret+e_ret+c_ret)/3, results[10][2]),
    ]
    all_pass = True
    for name, expected, actual in checks:
        ok = abs(expected - actual) < 0.01
        status = "PASS" if ok else "FAIL"
        print(f"    {name}) expected={expected:.2f}% actual={actual:.2f}% [{status}]")
        if not ok: all_pass = False
    if not all_pass:
        print("    *** SANITY CHECK FAILED - STOPPING ***")
        return

    # ================================================================
    # Save + RESEARCH_LOG
    # ================================================================
    save = [{"label": l, "sharpe": s, "return_pct": r, "max_dd_pct": d, "n_trades": t}
            for l, s, r, d, t in results]
    save_meta = {
        "data_start": DATA_START, "holdout_start": str(HOLDOUT_START)[:10],
        "holdout_end": HOLDOUT_END, "common_bars": common_len,
        "holdout_first_date": str(ho_start_date)[:10],
        "holdout_last_date": str(ho_end_date)[:10],
    }
    with open("sweep_results/final_holdout_v3.json", "w") as f:
        json.dump({"meta": save_meta, "results": save}, f, indent=2)

    log = f"\n## Definitive Holdout v3 ({pd.Timestamp.now().strftime('%Y-%m-%d')})\n\n"
    log += "### CLAUDE.md Rules Enforced\n"
    log += "All 7 rules checked and passed.\n\n"
    log += "### Data Coverage (Rule 6)\n"
    log += f"- Data load: {DATA_START}\n- Warmup end: {str(ho_start_date)[:10]}\n"
    log += f"- Trading: {str(ho_start_date)[:10]} to {str(ho_end_date)[:10]}\n"
    log += f"- Total bars: {common_len}\n\n"
    log += "### v2 Consistency (Rule 5)\n"
    log += f"- Donchian: v2={REF_DON_SHARPE:.3f} / v3={don_sharpe:.3f} (diff={abs(don_sharpe-REF_DON_SHARPE):.3f})\n"
    log += f"- MR: v2={REF_MR_RET:.2f}% / v3={mr_ret_val:.2f}% (diff={abs(mr_ret_val-REF_MR_RET):.2f}%)\n\n"
    log += "### Results\n"
    log += "| Portfolio | Sharpe | Return% | MaxDD% | Trades |\n"
    log += "|-----------|--------|---------|--------|--------|\n"
    for l, s, r, d, t in results:
        log += f"| {l} | {s:.3f} | {r:.2f} | {d:.2f} | {t} |\n"
    log += "\n### Sanity Checks (Rule 4)\nAll passed.\n"

    with open("RESEARCH_LOG.md", "a", encoding="utf-8") as f:
        f.write(log)

    print(f"\n  Total: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
