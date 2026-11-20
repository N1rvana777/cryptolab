#!/usr/bin/env python3
"""Final Holdout comparison + PM data generation.

Strategies A-G on Holdout (2025.07-2026.03), correct time alignment.
Also saves PM training (2024) and validation (2025 H1) data.
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
    compute_dynamic_slippage, compute_adx, run_donchian_b0, run_meanrev,
)
from scripts.cross_sectional_momentum import run_xsmom

PPY = 1096

# Confirmed config from user
TREND_SET = SIGNAL_SETS["8h"]["A"]
TREND_THRESH = 0.2
TREND_TVOL = 0.20
USE_1D_FILTER = True

# TSMOM-only (signal source 1): same Set A lookbacks, but only 3 TSMOM signals
TSMOM_ONLY_LBS = SIGNAL_SETS["8h"]["A"]["tsmom"]  # [90, 375, 750]


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


def run_trend_invvol(coin_dfs, signal_set, thresh, tvol, use_filter,
                     capital=10000.0, leverage=3.0, trading_start=None,
                     tsmom_only=False):
    """Multi-signal trend with inverse-volatility sizing.

    If tsmom_only=True, only use the 3 TSMOM signals (not MA/Donchian).
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

        if tsmom_only:
            # Only TSMOM signals (3 instead of 9)
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

        warmup = 0
        for i in range(n):
            if not np.isnan(composite[i]):
                warmup = i
                break

        trade_start = warmup + 1
        if trading_start is not None:
            ts_arr = df["timestamp"].values
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
            vol_sc = min(2.0, max(0.25, tvol / av))
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


def run_mr_portfolio(cache, coins, mr_params, start, end, trading_start,
                     capital=10000.0):
    """Pure MR portfolio with correct alignment."""
    from scripts.portfolio_optimization import run_combo
    n = len(coins); CAP = capital / n
    all_eqs = []; total_tr = 0

    for coin in coins:
        df = load_8h(cache, coin, start, end)
        if df is None: continue
        p = mr_params.get(coin)
        if not p or len(p) < 4: continue
        r = run_combo(df, p[0], p[1], 0.50, p[3], CAP, n,
                      leverage=3.0, don_weight=0.0, mr_weight=1.0)
        if r and not np.isnan(r["sharpe"]):
            # Find trading_start offset
            ts = df["timestamp"].values
            ts_start = np.datetime64(trading_start)
            warmup = max(336 + 60, p[0] + 60, 100)
            ho_offset = 0
            for i in range(len(ts)):
                if ts[i] >= ts_start:
                    ho_offset = max(0, i - warmup)
                    break
            eq = r["equities"]
            if ho_offset < len(eq):
                eq_slice = eq[ho_offset:]
                eq_slice = eq_slice / eq_slice[0] * CAP
                all_eqs.append(eq_slice)
                total_tr += r["n_trades"]

    if not all_eqs: return None
    ml = min(len(e) for e in all_eqs)
    port = sum(e[:ml] for e in all_eqs)
    port = port / port[0] * capital
    eq_s = pd.Series(port)
    sr = sharpe_ratio(eq_s, PPY); _, dd = max_drawdown(eq_s)
    ret = (port[-1] / port[0] - 1) * 100
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

    # ================================================================
    # Determine common trading start
    # ================================================================
    # Longest warmup: trend Set A MA slow = 1125 8H bars = 375 days
    # Load from 2019, so warmup is pre-holdout
    HOLDOUT_START = "2025-07-01"
    DATA_START = "2019-01-01"
    DATA_END = "2026-04-01"

    # Load all data
    print("Loading data...", flush=True)
    trend_dfs = {}  # full data for trend (warmup + holdout)
    xsmom_dfs = {}  # for XSMom (less warmup needed)
    for coin in ALL_28:
        df = load_data(cache, coin, "8h", DATA_START, DATA_END)
        if df is not None:
            trend_dfs[coin] = df
        df2 = load_data(cache, coin, "8h", "2024-01-01", DATA_END)
        if df2 is not None:
            xsmom_dfs[coin] = df2

    print(f"  Trend: {len(trend_dfs)} coins, XSMom: {len(xsmom_dfs)} coins")

    # ================================================================
    # A) Donchian B0
    # ================================================================
    print("\nA) Donchian B0...", flush=True)
    n_coins = len(ALL_28)
    CAP_PC = 10000.0 / n_coins
    don_eqs = []; don_tr = 0
    for coin in ALL_28:
        df = trend_dfs.get(coin)
        if df is None: continue
        r = run_donchian_b0(df, CAP_PC, n_coins, use_dynamic_slip=True)
        if r and not np.isnan(r["sharpe"]):
            # Extract holdout portion
            ts = trend_dfs[coin]["timestamp"].values
            warmup = 396
            ho_idx = 0
            for i in range(len(ts)):
                if ts[i] >= np.datetime64(HOLDOUT_START):
                    ho_idx = max(0, i - warmup)
                    break
            eq = r["equities"]
            if ho_idx < len(eq):
                eq_s = eq[ho_idx:]
                eq_s = eq_s / eq_s[0] * CAP_PC
                don_eqs.append(eq_s)
                don_tr += r["n_trades"]

    # ================================================================
    # B) Multi-signal trend (InvVol)
    # ================================================================
    print("B) Multi-signal trend...", flush=True)
    r_trend = run_trend_invvol(trend_dfs, TREND_SET, TREND_THRESH, TREND_TVOL,
                                USE_1D_FILTER, trading_start=HOLDOUT_START)

    # ================================================================
    # C) XSMom
    # ================================================================
    print("C) XSMom...", flush=True)
    r_xsmom = run_xsmom(xsmom_dfs, 36, 5, 21, False, capital=10000.0)
    # Extract holdout portion
    if r_xsmom:
        xs_full = r_xsmom["equities"]
        # Find holdout start in XSMom equity
        # XSMom warmup = 46 bars, data starts 2024-01
        df_ref = list(xsmom_dfs.values())[0]
        ts_ref = df_ref["timestamp"].values
        xs_warmup = 46
        xs_ho_idx = 0
        for i in range(len(ts_ref)):
            if ts_ref[i] >= np.datetime64(HOLDOUT_START):
                xs_ho_idx = max(0, i - xs_warmup)
                break
        xs_eq = xs_full[xs_ho_idx:]
        xs_eq = xs_eq / xs_eq[0] * 10000

    # ================================================================
    # F) TSMOM only (3 signals)
    # ================================================================
    print("F) TSMOM only...", flush=True)
    r_tsmom = run_trend_invvol(trend_dfs, TREND_SET, TREND_THRESH, TREND_TVOL,
                                USE_1D_FILTER, trading_start=HOLDOUT_START,
                                tsmom_only=True)

    # ================================================================
    # MR for combos E and G
    # ================================================================
    print("MR portfolio...", flush=True)
    r_mr = run_mr_portfolio(cache, ALL_28, mr_params,
                            DATA_START, DATA_END, HOLDOUT_START)

    # ================================================================
    # Align all equity curves
    # ================================================================
    curves = {}
    if don_eqs:
        ml = min(len(e) for e in don_eqs)
        don_port = sum(e[:ml] for e in don_eqs)
        don_port = don_port / don_port[0] * 10000
        curves["A"] = don_port
    if r_trend:
        curves["B"] = r_trend["equities"]
    if r_xsmom:
        curves["C"] = xs_eq
    if r_tsmom:
        curves["F"] = r_tsmom["equities"]
    if r_mr:
        curves["MR"] = r_mr["equities"]

    # Common length
    common_len = min(len(eq) for eq in curves.values())
    for k in curves:
        curves[k] = curves[k][:common_len]
        # Normalize all to start at $10,000
        curves[k] = curves[k] / curves[k][0] * 10000

    print(f"\nCommon length: {common_len} bars ({common_len*8/24:.0f} days)")
    for k, eq in curves.items():
        print(f"  {k}: start=${eq[0]:.2f} end=${eq[-1]:.2f} ret={(eq[-1]/eq[0]-1)*100:.2f}%")

    # Return multipliers
    rm = {k: eq / eq[0] for k, eq in curves.items()}

    # ================================================================
    # Build all portfolios
    # ================================================================
    def metrics(eq, label, trades=0):
        eq_s = pd.Series(eq)
        sr = sharpe_ratio(eq_s, PPY)
        _, dd = max_drawdown(eq_s)
        ret = (eq[-1] / eq[0] - 1) * 100
        return label, sr, ret, dd, trades

    results = []

    # A) Donchian
    results.append(metrics(curves["A"], "A) Donchian B0", don_tr))

    # B) Multi-signal trend
    results.append(metrics(curves["B"], "B) Multi-signal trend", r_trend["n_trades"] if r_trend else 0))

    # C) XSMom
    results.append(metrics(curves["C"], "C) XSMom", r_xsmom["n_trades"] if r_xsmom else 0))

    # D) Trend 60% + XSMom 40%
    d_eq = (0.6 * rm["B"] + 0.4 * rm["C"]) * 10000
    d_tr = (r_trend["n_trades"] if r_trend else 0) + (r_xsmom["n_trades"] if r_xsmom else 0)
    results.append(metrics(d_eq, "D) Trend60+XSMom40", d_tr))

    # E) Trend + MR + XSMom 33/33/33
    e_eq = (rm["B"] / 3 + rm["MR"] / 3 + rm["C"] / 3) * 10000
    e_tr = (r_trend["n_trades"] if r_trend else 0) + (r_mr["n_trades"] if r_mr else 0) + (r_xsmom["n_trades"] if r_xsmom else 0)
    results.append(metrics(e_eq, "E) Trend+MR+XSMom 33ea", e_tr))

    # F) TSMOM only
    results.append(metrics(curves["F"], "F) TSMOM only", r_tsmom["n_trades"] if r_tsmom else 0))

    # G) XSMom + MR 50/50
    g_eq = (0.5 * rm["C"] + 0.5 * rm["MR"]) * 10000
    g_tr = (r_xsmom["n_trades"] if r_xsmom else 0) + (r_mr["n_trades"] if r_mr else 0)
    results.append(metrics(g_eq, "G) XSMom+MR 50/50", g_tr))

    # ================================================================
    # Print
    # ================================================================
    print(f"\n{'='*70}")
    print(f"HOLDOUT RESULTS (all from $10,000, {common_len} bars)")
    print(f"{'='*70}")
    print(f"  {'Portfolio':<30} {'Sharpe':>8} {'Ret%':>8} {'MaxDD%':>8} {'Trades':>7}")
    print("  " + "-" * 63)
    for label, sr, ret, dd, tr in results:
        print(f"  {label:<30} {sr:>8.3f} {ret:>8.2f} {dd:>8.2f} {tr:>7}")

    # Sanity checks
    a_ret = results[0][2]; b_ret = results[1][2]; c_ret = results[2][2]
    mr_ret = (curves["MR"][-1] / curves["MR"][0] - 1) * 100
    f_ret = results[5][2]
    print(f"\nSanity checks:")
    print(f"  D) expected: 0.6*{b_ret:.2f}+0.4*{c_ret:.2f} = {0.6*b_ret+0.4*c_ret:.2f}%, actual: {results[3][2]:.2f}%")
    print(f"  E) expected: ({b_ret:.2f}+{mr_ret:.2f}+{c_ret:.2f})/3 = {(b_ret+mr_ret+c_ret)/3:.2f}%, actual: {results[4][2]:.2f}%")
    print(f"  G) expected: ({c_ret:.2f}+{mr_ret:.2f})/2 = {(c_ret+mr_ret)/2:.2f}%, actual: {results[6][2]:.2f}%")
    print(f"  MR standalone ret: {mr_ret:.2f}%")
    print(f"  TSMOM vs full trend: F={f_ret:.2f}% vs B={b_ret:.2f}%")

    # ================================================================
    # Save results
    # ================================================================
    save = {"holdout": [{"label": l, "sharpe": s, "return_pct": r, "max_dd_pct": d, "n_trades": t}
                        for l, s, r, d, t in results]}
    Path("sweep_results").mkdir(exist_ok=True)
    with open("sweep_results/final_holdout.json", "w") as f:
        json.dump(save, f, indent=2)

    # ================================================================
    # PM Training Data
    # ================================================================
    print(f"\n{'='*70}")
    print("Saving PM Training Data...")
    print(f"{'='*70}")

    for period_name, period_start, period_end in [
        ("pm_training_2024", "2024-01-01", "2025-01-01"),
        ("pm_validation_2025h1", "2025-01-01", "2025-07-01"),
    ]:
        rows = []
        for coin in ALL_28:
            df = load_data(cache, coin, "8h", "2019-01-01", period_end)
            if df is None:
                continue

            closes = df["close"].values
            highs = df["high"].values
            lows = df["low"].values
            volumes = df["volume"].values
            timestamps = df["timestamp"].values
            n = len(df)

            # Signals
            sigs = compute_signals(closes, TREND_SET)
            composite = np.nanmean(sigs, axis=1)
            filt_1d = compute_1d_filter(closes, "8h")

            # TSMOM only
            cs = pd.Series(closes)
            tsmom_sigs = np.full((n, 3), np.nan)
            for si, lb in enumerate(TREND_SET["tsmom"]):
                ret = cs / cs.shift(lb) - 1
                tsmom_sigs[:, si] = np.tanh(ret.values * 5)
            tsmom_composite = np.nanmean(tsmom_sigs, axis=1)

            # ADX
            adx_arr = compute_adx(highs, lows, closes, 20)

            # Rolling vol
            rets = np.zeros(n)
            rets[1:] = closes[1:] / closes[:-1] - 1
            roll_vol = pd.Series(rets).rolling(60, min_periods=20).std().values

            # Volume change rate
            vol_ma = pd.Series(volumes * closes).rolling(60, min_periods=3).mean().values
            vol_chg = np.zeros(n)
            for i in range(1, n):
                if vol_ma[i - 1] > 0:
                    vol_chg[i] = (volumes[i] * closes[i] - vol_ma[i - 1]) / vol_ma[i - 1]

            # Future returns
            fwd_3 = np.full(n, np.nan)
            fwd_9 = np.full(n, np.nan)
            fwd_21 = np.full(n, np.nan)
            for i in range(n):
                if i + 3 < n:
                    fwd_3[i] = closes[i + 3] / closes[i] - 1
                if i + 9 < n:
                    fwd_9[i] = closes[i + 9] / closes[i] - 1
                if i + 21 < n:
                    fwd_21[i] = closes[i + 21] / closes[i] - 1

            # Filter to period
            for i in range(n):
                if timestamps[i] < np.datetime64(period_start):
                    continue
                if timestamps[i] >= np.datetime64(period_end):
                    break

                row = {
                    "timestamp": str(timestamps[i]),
                    "coin": coin,
                    "close": closes[i],
                    # Individual signals
                    "tsmom_fast": sigs[i, 0] if not np.isnan(sigs[i, 0]) else None,
                    "tsmom_med": sigs[i, 1] if not np.isnan(sigs[i, 1]) else None,
                    "tsmom_slow": sigs[i, 2] if not np.isnan(sigs[i, 2]) else None,
                    "ma_fast": sigs[i, 3] if not np.isnan(sigs[i, 3]) else None,
                    "ma_med": sigs[i, 4] if not np.isnan(sigs[i, 4]) else None,
                    "ma_slow": sigs[i, 5] if not np.isnan(sigs[i, 5]) else None,
                    "don_fast": sigs[i, 6] if not np.isnan(sigs[i, 6]) else None,
                    "don_med": sigs[i, 7] if not np.isnan(sigs[i, 7]) else None,
                    "don_slow": sigs[i, 8] if not np.isnan(sigs[i, 8]) else None,
                    "composite_9sig": composite[i] if not np.isnan(composite[i]) else None,
                    "tsmom_composite": tsmom_composite[i] if not np.isnan(tsmom_composite[i]) else None,
                    "filter_1d": filt_1d[i],
                    # Market state
                    "adx": adx_arr[i] if not np.isnan(adx_arr[i]) else None,
                    "roll_vol_60": roll_vol[i] if not np.isnan(roll_vol[i]) else None,
                    "vol_chg_rate": vol_chg[i],
                    # Forward returns
                    "fwd_ret_3": fwd_3[i] if not np.isnan(fwd_3[i]) else None,
                    "fwd_ret_9": fwd_9[i] if not np.isnan(fwd_9[i]) else None,
                    "fwd_ret_21": fwd_21[i] if not np.isnan(fwd_21[i]) else None,
                }
                rows.append(row)

        pm_df = pd.DataFrame(rows)
        out_path = f"data/{period_name}.parquet"
        pm_df.to_parquet(out_path, index=False)
        print(f"  {period_name}: {len(pm_df)} rows -> {out_path}")

    # ================================================================
    # RESEARCH_LOG
    # ================================================================
    log = f"\n## Final Holdout ({pd.Timestamp.now().strftime('%Y-%m-%d')})\n\n"
    log += "### Config\n"
    log += "- Multi-signal trend: 8H + 1D filter, Set A, thresh=0.2, tvol=0.20 (W2 params)\n"
    log += "- Sizing: Inverse Volatility\n"
    log += "- 28 coins, unified params\n\n"
    log += f"### Results (Holdout 2025.07-2026.03, {common_len} bars)\n"
    log += "| Portfolio | Sharpe | Return% | MaxDD% | Trades |\n"
    log += "|-----------|--------|---------|--------|--------|\n"
    for label, sr, ret, dd, tr in results:
        log += f"| {label} | {sr:.3f} | {ret:.2f} | {dd:.2f} | {tr} |\n"
    log += f"\n### Sanity Checks\n"
    log += f"- D) 0.6*B+0.4*C = {0.6*b_ret+0.4*c_ret:.2f}% vs actual {results[3][2]:.2f}%\n"
    log += f"- E) (B+MR+C)/3 = {(b_ret+mr_ret+c_ret)/3:.2f}% vs actual {results[4][2]:.2f}%\n"
    log += f"- F) TSMOM-only = {f_ret:.2f}% vs full 9-signal = {b_ret:.2f}%\n"
    log += f"\n### PM Data Saved\n"
    log += "- pm_training_2024.parquet\n"
    log += "- pm_validation_2025h1.parquet\n"

    with open("RESEARCH_LOG.md", "a", encoding="utf-8") as f:
        f.write(log)

    print(f"\n  Total: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
