#!/usr/bin/env python3
"""Phase-averaged holdout: test strategy robustness across 21 starting phases.

Each strategy run 21 times with data loaded from 2025-06-01 to 2025-06-21.
All start with zero positions at the first bar after warmup.
"""

import sys, os, time, json, gc
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptolab.data.cache import ParquetCache
from cryptolab.backtest.metrics import sharpe_ratio, max_drawdown
from scripts.donchian_full_sweep import resample_ohlcv
from scripts.advanced_coint import run_pca_ou, load_freq, ALL_28
from scripts.cross_sectional_momentum import run_xsmom
from scripts.mean_reversion_experiment import run_donchian_b0, run_meanrev
from scripts.portfolio_optimization import run_combo
from scripts.multisignal_trend import (
    compute_signals, compute_1d_filter, SIGNAL_SETS,
)
from scripts.mean_reversion_experiment import compute_dynamic_slippage

PPY = 1096
FEE_BPS = 3.5
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


# ================================================================
# Strategy runners (each returns equity array starting at 10000)
# ================================================================

def run_don_phase(cache, phase_start):
    """Donchian B0 with clean start."""
    n = len(ALL_28); CAP = 10000.0 / n
    eqs = []
    for coin in ALL_28:
        df = load_8h(cache, coin, phase_start, HOLDOUT_END)
        if df is None: continue
        if len(df) < 400: continue
        r = run_donchian_b0(df, CAP, n, use_dynamic_slip=True)
        if r and not np.isnan(r["sharpe"]):
            eq = r["equities"]
            eq = eq / eq[0] * CAP
            eqs.append(eq)
    if not eqs: return None, 0
    ml = min(len(e) for e in eqs)
    port = sum(e[:ml] for e in eqs)
    port = port / port[0] * 10000
    trades = sum(1 for _ in range(0))  # approximate
    return port, 0


def run_xsmom_phase(cache, phase_start):
    """XSMom with clean start."""
    dfs = {}
    for coin in ALL_28:
        df = load_8h(cache, coin, phase_start, HOLDOUT_END)
        if df is not None: dfs[coin] = df
    r = run_xsmom(dfs, 36, 5, 21, False, capital=10000.0)
    if r: return r["equities"] / r["equities"][0] * 10000, r["n_trades"]
    return None, 0


def run_pca_phase(cache, phase_start):
    """PCA 8H with clean start."""
    dfs = {}
    for coin in ALL_28:
        df = load_freq(cache, coin, "8h", "2019-01-01", HOLDOUT_END)
        if df is not None: dfs[coin] = df
    # trading_start = first bar >= phase_start + enough warmup
    # PCA uses all data for indicator computation, only trades from trading_start
    ts_start = str(pd.Timestamp(phase_start) + pd.Timedelta(days=15))[:10]
    r = run_pca_ou(dfs, 5, 1.5, 0.25, 180, 180, ts_start, "8h")
    if r and "equities" in r:
        eq = r["equities"]
        eq = eq / eq[0] * 10000
        return eq, r["n_trades"]
    return None, 0


def run_trend_phase(cache, phase_start):
    """Multi-signal trend 8H+1D filter with clean start."""
    sig_set = SIGNAL_SETS["8h"]["A"]
    n = len(ALL_28); CAP = 10000.0 / n
    all_eqs = []; total_tr = 0
    fee_rate = FEE_BPS / 10_000

    ts_start = str(pd.Timestamp(phase_start) + pd.Timedelta(days=15))[:10]

    for coin in ALL_28:
        df = load_freq(cache, coin, "8h", "2019-01-01", HOLDOUT_END)
        if df is None: continue
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

        ts_arr = df["timestamp"].values
        trade_start = 0
        for i in range(nn):
            if ts_arr[i] >= np.datetime64(ts_start):
                trade_start = i; break

        equity = CAP; cash = equity; pos = 0; entry_px = 0
        equities = np.full(nn, equity); n_tr = 0; prev_target = 0

        for i in range(trade_start + 1, nn):
            o = opens[i]; c = closes[i]; sig = composite[i-1] if not np.isnan(composite[i-1]) else 0

            trade_size = abs(prev_target - pos)
            if trade_size > max(5, abs(prev_target) * 0.03):
                fee = trade_size * fee_rate
                slip = compute_dynamic_slippage(trade_size, adv[i] if not np.isnan(adv[i]) else 1e9)
                if abs(pos) > 0.01 and entry_px > 0:
                    pnl = abs(pos) * ((o-entry_px)/entry_px if pos > 0 else (entry_px-o)/entry_px)
                    cash += pnl
                cash -= fee + slip; n_tr += 1
                pos = prev_target; entry_px = o if abs(pos) > 0.01 else 0

            unrealized = 0
            if abs(pos) > 0.01 and entry_px > 0:
                unrealized = abs(pos) * ((c-entry_px)/entry_px if pos > 0 else (entry_px-c)/entry_px)
            equity = cash + unrealized; equities[i] = equity

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

        eq = equities[trade_start:]
        all_eqs.append(eq); total_tr += n_tr

    if not all_eqs: return None, 0
    ml = min(len(e) for e in all_eqs)
    port = sum(e[:ml] for e in all_eqs)
    port = port / port[0] * 10000
    return port, total_tr


def run_mr_phase(cache, phase_start, mr_params):
    """Z-score MR with clean start."""
    n = len(ALL_28); CAP = 10000.0 / n
    eqs = []; total_tr = 0

    for coin in ALL_28:
        df = load_8h(cache, coin, "2019-01-01", HOLDOUT_END)
        if df is None: continue
        p = mr_params.get(coin)
        if not p or len(p) < 4: continue

        ts = df["timestamp"].values
        ho_idx = 0
        for i in range(len(ts)):
            if ts[i] >= np.datetime64(phase_start):
                ho_idx = i; break

        warmup = max(336+60, p[0]+60, 100)
        if ho_idx < warmup: continue

        df_slice = df.iloc[ho_idx - warmup:].reset_index(drop=True)
        r = run_combo(df_slice, p[0], p[1], 0.50, p[3], CAP, n,
                      leverage=3.0, don_weight=0.0, mr_weight=1.0)
        if r and not np.isnan(r["sharpe"]):
            eq = r["equities"]
            eq = eq / eq[0] * CAP
            eqs.append(eq); total_tr += r["n_trades"]

    if not eqs: return None, 0
    ml = min(len(e) for e in eqs)
    port = sum(e[:ml] for e in eqs)
    port = port / port[0] * 10000
    return port, total_tr


def main():
    t0 = time.time()
    cache = ParquetCache()

    with open("sweep_results/meanrev_experiment.json") as f:
        mr_params = json.load(f).get("meanrev_best_params", {})
    if Path("sweep_results/expanded_coins_v3.json").exists():
        with open("sweep_results/expanded_coins_v3.json") as f:
            mr_params.update(json.load(f).get("mr_params", {}))

    # 21 phases: 2025-06-01 to 2025-06-21
    phases = [f"2025-06-{d:02d}" for d in range(1, 22)]
    print(f"Phases: {len(phases)} ({phases[0]} to {phases[-1]})")

    strategies = {
        "A) PCA 8H": lambda ps: run_pca_phase(cache, ps),
        "B) XSMom": lambda ps: run_xsmom_phase(cache, ps),
        "C) Donchian B0": lambda ps: run_don_phase(cache, ps),
        "D) Trend 8H+1D": lambda ps: run_trend_phase(cache, ps),
        "E) Z-score MR": lambda ps: run_mr_phase(cache, ps, mr_params),
    }

    # Run all phases for all strategies
    phase_results = {}  # {strategy: [(sharpe, ret, dd, eq), ...]}

    for sname, runner in strategies.items():
        print(f"\n{'='*50}")
        print(f"{sname}: running {len(phases)} phases...")
        print(f"{'='*50}")

        results = []
        for pi, ps in enumerate(phases):
            eq, tr = runner(ps)
            if eq is not None and len(eq) > 10:
                eq_s = pd.Series(eq)
                sr = sharpe_ratio(eq_s, PPY)
                _, dd = max_drawdown(eq_s)
                ret = (eq[-1] / eq[0] - 1) * 100
                results.append({"sharpe": sr, "ret": ret, "dd": dd, "eq": eq, "trades": tr})
                print(f"  phase {pi}: SR={sr:.3f} Ret={ret:.2f}%", flush=True)
            else:
                results.append(None)
                print(f"  phase {pi}: FAILED", flush=True)
            gc.collect()

        phase_results[sname] = results

    # ================================================================
    # Compute combos for each phase
    # ================================================================
    combo_names = {
        "F) PCA+XSMom 50/50": ("A) PCA 8H", "B) XSMom", 0.5, 0.5, None, None),
        "G) PCA+XSMom+MR 33": ("A) PCA 8H", "B) XSMom", 1/3, 1/3, "E) Z-score MR", 1/3),
        "H) XSMom+MR 50/50": ("B) XSMom", "E) Z-score MR", 0.5, 0.5, None, None),
    }

    for combo_name, (s1, s2, w1, w2, s3, w3) in combo_names.items():
        results = []
        for pi in range(len(phases)):
            r1 = phase_results[s1][pi]
            r2 = phase_results[s2][pi]
            r3 = phase_results.get(s3, [None]*len(phases))[pi] if s3 else None

            if r1 is None or r2 is None: results.append(None); continue
            eq1 = r1["eq"]; eq2 = r2["eq"]

            if s3 and r3 is None: results.append(None); continue
            eq3 = r3["eq"] if r3 else None

            ml = min(len(eq1), len(eq2))
            if eq3 is not None: ml = min(ml, len(eq3))

            rm1 = eq1[:ml] / eq1[0]
            rm2 = eq2[:ml] / eq2[0]
            if eq3 is not None:
                rm3 = eq3[:ml] / eq3[0]
                combo = (w1 * rm1 + w2 * rm2 + w3 * rm3) * 10000
            else:
                combo = (w1 * rm1 + w2 * rm2) * 10000

            eq_s = pd.Series(combo)
            sr = sharpe_ratio(eq_s, PPY)
            _, dd = max_drawdown(eq_s)
            ret = (combo[-1] / combo[0] - 1) * 100
            tr = (r1.get("trades", 0) or 0) + (r2.get("trades", 0) or 0)
            if r3: tr += r3.get("trades", 0) or 0
            results.append({"sharpe": sr, "ret": ret, "dd": dd, "eq": combo, "trades": tr})

        phase_results[combo_name] = results

    # ================================================================
    # Summary table
    # ================================================================
    print(f"\n{'='*90}")
    print("PHASE-AVERAGED HOLDOUT RESULTS")
    print(f"{'='*90}")

    all_names = ["A) PCA 8H", "B) XSMom", "C) Donchian B0", "D) Trend 8H+1D", "E) Z-score MR",
                 "F) PCA+XSMom 50/50", "G) PCA+XSMom+MR 33", "H) XSMom+MR 50/50"]

    print(f"\n  {'Strategy':<22} {'Avg SR':>7} {'SR std':>7} {'Best SR':>8} {'Worst SR':>9} {'Avg Ret%':>9} {'Ret std':>8} {'Verdict':>10}")
    print("  " + "-" * 85)

    summary = {}
    for sname in all_names:
        results = phase_results.get(sname, [])
        valid = [r for r in results if r is not None]
        if not valid:
            print(f"  {sname:<22} {'N/A':>7}"); continue

        sharpes = [r["sharpe"] for r in valid]
        rets = [r["ret"] for r in valid]

        avg_sr = np.mean(sharpes); std_sr = np.std(sharpes)
        best_sr = max(sharpes); worst_sr = min(sharpes)
        avg_ret = np.mean(rets); std_ret = np.std(rets)

        if std_sr < 0.3: verdict = "ROBUST"
        elif std_sr < 0.6: verdict = "MODERATE"
        else: verdict = "UNRELIABLE"

        print(f"  {sname:<22} {avg_sr:>7.3f} {std_sr:>7.3f} {best_sr:>8.3f} {worst_sr:>9.3f} "
              f"{avg_ret:>9.2f} {std_ret:>8.2f} {verdict:>10}")

        summary[sname] = {
            "avg_sharpe": avg_sr, "std_sharpe": std_sr,
            "best_sharpe": best_sr, "worst_sharpe": worst_sr,
            "avg_return": avg_ret, "std_return": std_ret,
            "verdict": verdict, "n_valid": len(valid),
        }

    # ================================================================
    # Phase consistency (correlation between phase 0 and phase 10)
    # ================================================================
    print(f"\n  --- Phase Consistency (corr between phase 0 and phase 10 daily returns) ---")
    for sname in all_names:
        results = phase_results.get(sname, [])
        if len(results) < 11 or results[0] is None or results[10] is None: continue
        eq0 = results[0]["eq"]; eq10 = results[10]["eq"]
        ml = min(len(eq0), len(eq10))
        if ml < 20: continue
        r0 = pd.Series(eq0[:ml]).pct_change().dropna().values
        r10 = pd.Series(eq10[:ml]).pct_change().dropna().values
        ml2 = min(len(r0), len(r10))
        if ml2 > 10 and np.std(r0[:ml2]) > 0 and np.std(r10[:ml2]) > 0:
            corr = float(np.corrcoef(r0[:ml2], r10[:ml2])[0, 1])
            print(f"  {sname:<22} phase0-phase10 corr: {corr:.3f}")

    # ================================================================
    # Save + Log
    # ================================================================
    save = {k: {kk: vv for kk, vv in v.items() if kk != "eq"}
            for k, v in summary.items()}
    with open("sweep_results/phase_average.json", "w") as f:
        json.dump(save, f, indent=2)

    log = f"\n## Phase-Averaged Holdout ({pd.Timestamp.now().strftime('%Y-%m-%d')})\n\n"
    log += "21 phases (data start 2025-06-01 to 2025-06-21), all zero-position clean start.\n\n"
    log += "| Strategy | Avg SR | SR std | Best SR | Worst SR | Avg Ret% | Ret std | Verdict |\n"
    log += "|----------|--------|--------|---------|----------|---------|---------|--------|\n"
    for sname in all_names:
        s = summary.get(sname)
        if s:
            log += (f"| {sname} | {s['avg_sharpe']:.3f} | {s['std_sharpe']:.3f} | "
                    f"{s['best_sharpe']:.3f} | {s['worst_sharpe']:.3f} | "
                    f"{s['avg_return']:.2f} | {s['std_return']:.2f} | {s['verdict']} |\n")

    log += "\n### Interpretation\n"
    log += "- SR std < 0.3 = ROBUST (result trustworthy)\n"
    log += "- SR std 0.3-0.6 = MODERATE (some phase dependency)\n"
    log += "- SR std > 0.6 = UNRELIABLE (result is luck)\n"

    with open("RESEARCH_LOG.md", "a", encoding="utf-8") as f:
        f.write(log)

    print(f"\n  Total: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
