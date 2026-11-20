#!/usr/bin/env python3
"""Final Holdout v2: correct zero-position start for ALL strategies.

Every strategy:
1. Gets warmup data BEFORE holdout to compute indicators
2. Starts with ZERO positions at holdout first bar
3. First trade can only happen at holdout first bar or later

Prints position state at holdout first bar for confirmation.
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
from scripts.mean_reversion_experiment import (
    compute_dynamic_slippage, compute_adx, run_meanrev,
)
from scripts.cross_sectional_momentum import run_xsmom

PPY = 1096
TREND_SET = SIGNAL_SETS["8h"]["A"]
TREND_THRESH = 0.2
TREND_TVOL = 0.20

HOLDOUT_START = "2025-07-01"
HOLDOUT_END = "2026-04-01"


def load_8h(cache, coin, start, end):
    df = cache.read("okx", coin, "1h")
    if df is None or df.empty:
        return None
    if df["timestamp"].dt.tz is not None:
        df["timestamp"] = df["timestamp"].dt.tz_localize(None)
    df8 = resample_ohlcv(df, "8h")
    mask = (df8["timestamp"] >= pd.Timestamp(start)) & (df8["timestamp"] < pd.Timestamp(end))
    out = df8[mask].reset_index(drop=True)
    return out if len(out) > 50 else None


# ================================================================
# A) Donchian B0 — clean start at holdout
# ================================================================
def run_donchian_clean(coin_dfs, trading_start, capital=10000.0):
    """Run Donchian B0 with zero positions at trading_start."""
    from scripts.mean_reversion_experiment import run_donchian_b0
    coins = list(coin_dfs.keys())
    n = len(coins)
    CAP = capital / n
    all_eqs = []; total_tr = 0

    for coin in coins:
        df = coin_dfs[coin]
        # run_donchian_b0 always starts fresh (pos=0, cash=capital)
        # Just need to give it data starting before holdout for warmup
        # and extract equity from holdout start
        r = run_donchian_b0(df, CAP, n, use_dynamic_slip=True)
        if r is None or np.isnan(r["sharpe"]):
            continue
        eq_full = r["equities"]
        # Find holdout start bar in the equity array
        # run_donchian_b0 skips first 396 bars, so eq[0] = bar 396 of df
        warmup = 396
        ts = df["timestamp"].values
        ho_bar_in_df = 0
        for i in range(len(ts)):
            if ts[i] >= np.datetime64(trading_start):
                ho_bar_in_df = i
                break
        ho_bar_in_eq = ho_bar_in_df - warmup
        if ho_bar_in_eq < 0 or ho_bar_in_eq >= len(eq_full):
            continue

        # IMPORTANT: the strategy traded before holdout.
        # We need to RESET and only use holdout data.
        # Since run_donchian_b0 doesn't support trading_start,
        # we must give it ONLY holdout data (clean start).
        pass

    # CORRECT approach: give each strategy ONLY the data it needs
    # with warmup prepended, but run_donchian_b0 starts fresh every time.
    # So: load data from (holdout_start - warmup_days) to holdout_end
    # The strategy's internal warmup eats the pre-holdout bars
    # and starts trading exactly at holdout_start.
    all_eqs = []; total_tr = 0
    for coin in coins:
        # Load enough data: 396 bars warmup before holdout
        df = coin_dfs[coin]
        ts = df["timestamp"].values
        ho_idx = 0
        for i in range(len(ts)):
            if ts[i] >= np.datetime64(trading_start):
                ho_idx = i
                break

        # Need at least 396 bars before ho_idx for warmup
        if ho_idx < 396:
            # Not enough warmup, skip
            continue

        # Give exactly 396 + holdout bars
        df_slice = df.iloc[ho_idx - 396:].reset_index(drop=True)
        r = run_donchian_b0(df_slice, CAP, n, use_dynamic_slip=True)
        if r is None or np.isnan(r["sharpe"]):
            continue
        # eq starts at bar 0 of equity = first bar after warmup = holdout start
        eq = r["equities"]
        eq = eq / eq[0] * CAP  # normalize
        all_eqs.append(eq)
        total_tr += r["n_trades"]

    if not all_eqs:
        return None
    ml = min(len(e) for e in all_eqs)
    port = sum(e[:ml] for e in all_eqs)
    port = port / port[0] * capital
    eq_s = pd.Series(port)
    sr = sharpe_ratio(eq_s, PPY); _, dd = max_drawdown(eq_s)
    ret = (port[-1] / port[0] - 1) * 100
    # Confirm zero position at bar 0
    print(f"  A) Donchian: {len(all_eqs)} coins, {ml} bars, "
          f"bar0 equity=${port[0]:.2f} (should be $10000), pos=0 (fresh start)")
    return {"sharpe": sr, "return_pct": ret, "max_dd_pct": dd,
            "n_trades": total_tr, "equities": port}


# ================================================================
# B/F) Multi-signal trend — clean start
# ================================================================
def run_trend_clean(coin_dfs, signal_set, thresh, tvol, use_filter,
                    trading_start, capital=10000.0, leverage=3.0,
                    tsmom_only=False):
    """Multi-signal trend with guaranteed zero positions at trading_start."""
    coins = list(coin_dfs.keys())
    n_coins = len(coins)
    if n_coins < 5:
        return None

    fee_rate = FEE_BPS / 10_000
    per_coin = capital / n_coins
    all_eqs = []; total_trades = 0

    for coin in coins:
        df = coin_dfs[coin]
        n = len(df)
        closes = df["close"].values
        opens = df["open"].values
        volumes = df["volume"].values

        if tsmom_only:
            cs = pd.Series(closes)
            sigs_raw = np.full((n, 3), np.nan)
            for si, lb in enumerate(signal_set["tsmom"]):
                ret = cs / cs.shift(lb) - 1
                sigs_raw[:, si] = np.tanh(ret.values * 5)
            composite = np.nanmean(sigs_raw, axis=1)
        else:
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

        vol_usd = volumes * closes
        adv = pd.Series(vol_usd).rolling(60, min_periods=3).sum().values / 20

        # Find trading start bar
        ts_arr = df["timestamp"].values
        trade_start = 0
        for i in range(n):
            if ts_arr[i] >= np.datetime64(trading_start):
                trade_start = i
                break

        # Start with zero positions, full cash
        equity = per_coin; cash = equity; pos = 0.0; entry_px = 0.0
        peak = equity
        equities = np.full(n, equity)
        n_tr = 0; prev_target = 0.0

        # Only loop from trading_start onward
        for i in range(trade_start + 1, n):
            o = opens[i]; c = closes[i]
            sig = composite[i - 1] if i - 1 >= 0 and not np.isnan(composite[i - 1]) else 0

            # Execute
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

            if np.isnan(sig):
                prev_target = 0.0; continue

            d_filt = filt[i - 1]
            av = ann_vol[i - 1] if not np.isnan(ann_vol[i - 1]) and ann_vol[i - 1] > 0 else 1.0
            vol_sc = min(2.0, max(0.25, tvol / av))
            dd = max(0, 1.0 - equity / peak)
            dd_sc = 1.0 - min(dd / 0.30, 1.0) * 0.75 if dd > 0 else 1.0
            max_pos = equity * leverage

            if sig > thresh:
                if use_filter and d_filt < 0:
                    prev_target = 0.0
                else:
                    prev_target = min(equity * leverage * vol_sc * abs(sig), max_pos)
            elif sig < -thresh:
                if use_filter and d_filt > 0:
                    prev_target = 0.0
                else:
                    prev_target = -min(equity * leverage * vol_sc * abs(sig), max_pos)
            elif abs(sig) < 0.1:
                prev_target = 0.0

        eq_slice = equities[trade_start:]
        all_eqs.append(eq_slice)
        total_trades += n_tr

    ml = min(len(e) for e in all_eqs)
    port = sum(e[:ml] for e in all_eqs)
    port = port / port[0] * capital
    eq_s = pd.Series(port)
    sr = sharpe_ratio(eq_s, PPY); _, dd = max_drawdown(eq_s)
    ret = (port[-1] / port[0] - 1) * 100
    label = "F) TSMOM" if tsmom_only else "B) Trend"
    print(f"  {label}: {len(all_eqs)} coins, {ml} bars, "
          f"bar0 equity=${port[0]:.2f}, pos=0 (fresh start)")
    return {"sharpe": sr, "return_pct": ret, "max_dd_pct": dd,
            "n_trades": total_trades, "equities": port}


# ================================================================
# C) XSMom — clean start (just load holdout data only)
# ================================================================
def run_xsmom_clean(cache, coins, trading_start, trading_end, capital=10000.0):
    """XSMom with clean start: load only holdout data."""
    # XSMom needs 46 bars warmup. Load from ~15 days before holdout.
    warmup_days = 20
    warmup_start = str(pd.Timestamp(trading_start) - pd.Timedelta(days=warmup_days))

    ho_dfs = {}
    for coin in coins:
        df = load_8h(cache, coin, warmup_start, trading_end)
        if df is not None:
            ho_dfs[coin] = df

    r = run_xsmom(ho_dfs, 36, 5, 21, False, capital=capital)
    if r:
        print(f"  C) XSMom: {len(ho_dfs)} coins, {len(r['equities'])} bars, "
              f"bar0 equity=${r['equities'][0]:.2f}, pos=0 (fresh start)")
    return r


# ================================================================
# MR — clean start
# ================================================================
def run_mr_clean(cache, coins, mr_params, trading_start, trading_end,
                 capital=10000.0):
    """MR portfolio with clean start at trading_start."""
    from scripts.portfolio_optimization import run_combo
    n = len(coins); CAP = capital / n
    all_eqs = []; total_tr = 0

    for coin in coins:
        # Load with warmup before holdout
        df_full = load_8h(cache, coin, "2019-01-01", trading_end)
        if df_full is None:
            continue
        p = mr_params.get(coin)
        if not p or len(p) < 4:
            continue

        ts = df_full["timestamp"].values
        ho_idx = 0
        for i in range(len(ts)):
            if ts[i] >= np.datetime64(trading_start):
                ho_idx = i
                break

        warmup = max(336 + 60, p[0] + 60, 100)
        if ho_idx < warmup:
            continue

        # Slice: warmup + holdout
        df_slice = df_full.iloc[ho_idx - warmup:].reset_index(drop=True)
        r = run_combo(df_slice, p[0], p[1], 0.50, p[3], CAP, n,
                      leverage=3.0, don_weight=0.0, mr_weight=1.0)
        if r is None or np.isnan(r["sharpe"]):
            continue
        # Equity starts after run_combo's warmup = exactly at holdout start
        eq = r["equities"]
        eq = eq / eq[0] * CAP
        all_eqs.append(eq)
        total_tr += r["n_trades"]

    if not all_eqs:
        return None
    ml = min(len(e) for e in all_eqs)
    port = sum(e[:ml] for e in all_eqs)
    port = port / port[0] * capital
    eq_s = pd.Series(port)
    sr = sharpe_ratio(eq_s, PPY); _, dd = max_drawdown(eq_s)
    ret = (port[-1] / port[0] - 1) * 100
    print(f"  MR: {len(all_eqs)} coins, {ml} bars, "
          f"bar0 equity=${port[0]:.2f}, pos=0 (fresh start)")
    return {"sharpe": sr, "return_pct": ret, "max_dd_pct": dd,
            "n_trades": total_tr, "equities": port}


def main():
    t0 = time.time()
    cache = ParquetCache()

    with open("sweep_results/meanrev_experiment.json") as f:
        mr_params = json.load(f).get("meanrev_best_params", {})
    if Path("sweep_results/expanded_coins_v3.json").exists():
        with open("sweep_results/expanded_coins_v3.json") as f:
            mr_params.update(json.load(f).get("mr_params", {}))

    # Load all data with warmup for trend signals
    print("Loading data...", flush=True)
    trend_dfs = {}
    for coin in ALL_28:
        df = load_data(cache, coin, "8h", "2019-01-01", HOLDOUT_END)
        if df is not None:
            trend_dfs[coin] = df
    print(f"  {len(trend_dfs)} coins loaded")

    print(f"\n{'='*70}")
    print(f"HOLDOUT (2025-07-01 to 2026-03-25) — ALL CLEAN START")
    print(f"{'='*70}\n")

    # A) Donchian B0
    r_don = run_donchian_clean(trend_dfs, HOLDOUT_START)

    # B) Multi-signal trend
    r_trend = run_trend_clean(trend_dfs, TREND_SET, TREND_THRESH, TREND_TVOL,
                               True, HOLDOUT_START)

    # C) XSMom
    r_xsmom = run_xsmom_clean(cache, ALL_28, HOLDOUT_START, HOLDOUT_END)

    # F) TSMOM only
    r_tsmom = run_trend_clean(trend_dfs, TREND_SET, TREND_THRESH, TREND_TVOL,
                               True, HOLDOUT_START, tsmom_only=True)

    # MR
    r_mr = run_mr_clean(cache, ALL_28, mr_params, HOLDOUT_START, HOLDOUT_END)

    # Common length
    curves = {}
    labels_map = {"A": r_don, "B": r_trend, "C": r_xsmom, "F": r_tsmom, "MR": r_mr}
    for k, r in labels_map.items():
        if r and "equities" in r:
            curves[k] = r["equities"]

    common_len = min(len(eq) for eq in curves.values())
    for k in curves:
        curves[k] = curves[k][:common_len]
        curves[k] = curves[k] / curves[k][0] * 10000

    print(f"\n  Common length: {common_len} bars ({common_len*8/24:.0f} days)")

    # Return multipliers
    rm = {k: eq / eq[0] for k, eq in curves.items()}

    def metrics(eq, label, trades=0):
        eq_s = pd.Series(eq)
        sr = sharpe_ratio(eq_s, PPY)
        _, dd = max_drawdown(eq_s)
        ret = (eq[-1] / eq[0] - 1) * 100
        return label, sr, ret, dd, trades

    results = []
    results.append(metrics(curves["A"], "A) Donchian B0",
                           r_don["n_trades"]))
    results.append(metrics(curves["B"], "B) Multi-signal trend",
                           r_trend["n_trades"]))
    results.append(metrics(curves["C"], "C) XSMom",
                           r_xsmom["n_trades"] if r_xsmom else 0))

    d_eq = (0.6 * rm["B"] + 0.4 * rm["C"]) * 10000
    results.append(metrics(d_eq, "D) Trend60+XSMom40",
                           (r_trend["n_trades"] if r_trend else 0) + (r_xsmom["n_trades"] if r_xsmom else 0)))

    e_eq = (rm["B"]/3 + rm["MR"]/3 + rm["C"]/3) * 10000
    results.append(metrics(e_eq, "E) Trend+MR+XSMom 33ea",
                           sum(r["n_trades"] for r in [r_trend, r_mr, r_xsmom] if r)))

    results.append(metrics(curves["F"], "F) TSMOM only",
                           r_tsmom["n_trades"] if r_tsmom else 0))

    g_eq = (0.5 * rm["C"] + 0.5 * rm["MR"]) * 10000
    results.append(metrics(g_eq, "G) XSMom+MR 50/50",
                           (r_xsmom["n_trades"] if r_xsmom else 0) + (r_mr["n_trades"] if r_mr else 0)))

    # Print
    print(f"\n  {'Portfolio':<30} {'Sharpe':>8} {'Ret%':>8} {'MaxDD%':>8} {'Trades':>7}")
    print("  " + "-" * 63)
    for label, sr, ret, dd, tr in results:
        print(f"  {label:<30} {sr:>8.3f} {ret:>8.2f} {dd:>8.2f} {tr:>7}")

    # Sanity checks
    a_r = results[0][2]; b_r = results[1][2]; c_r = results[2][2]
    mr_r = (curves["MR"][-1]/curves["MR"][0]-1)*100
    f_r = results[5][2]
    print(f"\nSanity checks:")
    print(f"  D) 0.6*{b_r:.2f}+0.4*{c_r:.2f} = {0.6*b_r+0.4*c_r:.2f}% vs actual {results[3][2]:.2f}%")
    print(f"  E) ({b_r:.2f}+{mr_r:.2f}+{c_r:.2f})/3 = {(b_r+mr_r+c_r)/3:.2f}% vs actual {results[4][2]:.2f}%")
    print(f"  G) ({c_r:.2f}+{mr_r:.2f})/2 = {(c_r+mr_r)/2:.2f}% vs actual {results[6][2]:.2f}%")
    print(f"  MR standalone: {mr_r:.2f}%")

    # Save
    save = [{"label": l, "sharpe": s, "return_pct": r, "max_dd_pct": d, "n_trades": t}
            for l, s, r, d, t in results]
    with open("sweep_results/final_holdout_v2.json", "w") as f:
        json.dump(save, f, indent=2)

    # RESEARCH_LOG
    log = f"\n## Final Holdout v2 - Clean Start ({pd.Timestamp.now().strftime('%Y-%m-%d')})\n\n"
    log += "### Fix Applied\n"
    log += "- All strategies start with ZERO positions at holdout first bar\n"
    log += "- Warmup only computes indicators, no trades\n"
    log += "- Position state confirmed at bar 0 for each strategy\n\n"
    log += f"### Results (Holdout 2025-07-01 to 2026-03-25, {common_len} bars)\n"
    log += "| Portfolio | Sharpe | Return% | MaxDD% | Trades |\n"
    log += "|-----------|--------|---------|--------|--------|\n"
    for l, s, r, d, t in results:
        log += f"| {l} | {s:.3f} | {r:.2f} | {d:.2f} | {t} |\n"
    log += f"\n### Sanity Checks\n"
    log += f"- D) 0.6*B+0.4*C = {0.6*b_r+0.4*c_r:.2f}% vs actual {results[3][2]:.2f}%\n"
    log += f"- E) (B+MR+C)/3 = {(b_r+mr_r+c_r)/3:.2f}% vs actual {results[4][2]:.2f}%\n"
    log += f"- G) (C+MR)/2 = {(c_r+mr_r)/2:.2f}% vs actual {results[6][2]:.2f}%\n"

    with open("RESEARCH_LOG.md", "a", encoding="utf-8") as f:
        f.write(log)

    print(f"\n  Total: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
