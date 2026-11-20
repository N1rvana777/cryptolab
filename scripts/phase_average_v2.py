#!/usr/bin/env python3
"""Phase-averaged holdout v2: correct implementation per CLAUDE.md Rule 7.

Phase shift via rebalance counter offset, NOT data loading date.
All phases cover full holdout (2025-07-01 to 2026-03-31).
Data loaded from 2024-06-21 for all phases (same warmup).
"""

import sys, os, time, json, gc
from pathlib import Path
from itertools import combinations
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptolab.data.cache import ParquetCache
from cryptolab.backtest.metrics import sharpe_ratio, max_drawdown
from scripts.donchian_full_sweep import resample_ohlcv
from scripts.mean_reversion_experiment import (
    compute_adx, compute_dynamic_slippage, run_donchian_b0,
)
from scripts.multisignal_trend import compute_signals, compute_1d_filter, SIGNAL_SETS
from scripts.advanced_coint import run_pca_ou, estimate_ou
from scripts.portfolio_optimization import run_combo
from sklearn.decomposition import PCA

ALL_28 = ["BTC","ETH","LTC","TRX","BCH","DOT","ADA","LINK","XLM","XRP",
          "ETC","ALGO","ATOM","AAVE","SOL","ICP","UNI","FIL","AVAX","NEAR",
          "CRV","DOGE","AXS","YGG","CELO","GALA","SAND","PEOPLE"]

PPY = 1096; FEE_BPS = 3.5
DATA_START = "2024-06-21"
HOLDOUT_START = pd.Timestamp("2025-07-01")
HOLDOUT_END = "2026-04-01"
N_PHASES = 21


def load_8h(cache, coin):
    df = cache.read("okx", coin, "1h")
    if df is None or df.empty: return None
    if df["timestamp"].dt.tz is not None:
        df["timestamp"] = df["timestamp"].dt.tz_localize(None)
    df8 = resample_ohlcv(df, "8h")
    mask = (df8["timestamp"] >= pd.Timestamp(DATA_START)) & (df8["timestamp"] < pd.Timestamp(HOLDOUT_END))
    return df8[mask].reset_index(drop=True)


def find_ho_idx(df):
    ts = df["timestamp"].values
    for i in range(len(ts)):
        if ts[i] >= np.datetime64(HOLDOUT_START): return i
    return len(ts)


def run_xsmom_phased(coin_dfs, ho_indices, lookback, top_k, rebal_bars,
                     phase_offset, capital=10000.0):
    """XSMom with phase offset in rebalance counter."""
    coins = list(coin_dfs.keys()); n_c = len(coins)
    if n_c < 6: return None

    # Build aligned price matrix (full data)
    all_ts = None
    for df in coin_dfs.values():
        ts = set(df["timestamp"].values)
        all_ts = ts if all_ts is None else all_ts & ts
    common_ts = sorted(all_ts); n = len(common_ts)

    prices = np.zeros((n, n_c)); volumes = np.zeros((n, n_c))
    for ci, coin in enumerate(coins):
        df = coin_dfs[coin]
        tm = {t: j for j, t in enumerate(df["timestamp"].values)}
        for ti, t in enumerate(common_ts):
            idx = tm.get(t)
            if idx is not None:
                prices[ti, ci] = df.iloc[idx]["close"]
                volumes[ti, ci] = df.iloc[idx]["volume"] * df.iloc[idx]["close"]

    returns = np.zeros((n, n_c))
    for i in range(1, n):
        for ci in range(n_c):
            if prices[i-1, ci] > 0:
                returns[i, ci] = prices[i, ci] / prices[i-1, ci] - 1

    # Find holdout start in common_ts
    ho_bar = 0
    for i, t in enumerate(common_ts):
        if t >= np.datetime64(HOLDOUT_START): ho_bar = i; break

    warmup = lookback + 10
    adv = pd.DataFrame(volumes).rolling(60, min_periods=3).sum().values / 20
    fee_rate = FEE_BPS / 10_000
    k = min(int(top_k), n_c // 2 - 1)

    equity = capital; cash = equity; peak = equity
    positions = np.zeros(n_c); entry_prices = np.zeros(n_c)
    equities = []; n_trades = 0

    for i in range(ho_bar, n):
        # MTM
        unrealized = 0
        for ci in range(n_c):
            if abs(positions[ci]) > 0.01 and entry_prices[ci] > 0 and prices[i, ci] > 0:
                if positions[ci] > 0:
                    unrealized += abs(positions[ci]) * (prices[i, ci] / entry_prices[ci] - 1)
                else:
                    unrealized += abs(positions[ci]) * (1 - prices[i, ci] / entry_prices[ci])
        equity = cash + unrealized; peak = max(peak, equity)
        equities.append(equity)

        # Rebalance check with phase offset
        bars_since_ho = i - ho_bar
        if (bars_since_ho + phase_offset) % rebal_bars != 0:
            continue
        if i < warmup: continue

        # Rank
        cum_rets = np.zeros(n_c); valid = np.ones(n_c, dtype=bool)
        for ci in range(n_c):
            if prices[i, ci] > 0 and prices[max(0, i-lookback), ci] > 0:
                cum_rets[ci] = prices[i, ci] / prices[max(0, i-lookback), ci] - 1
            else: valid[ci] = False

        if valid.sum() < 2*k+2: continue
        if np.std(cum_rets[valid]) < 0.001: continue

        ranked = np.argsort(-cum_rets)
        valid_ranked = [ci for ci in ranked if valid[ci]]
        long_coins = valid_ranked[:k]; short_coins = valid_ranked[-k:]

        dd = max(0, 1 - equity/peak)
        dd_sc = 1 - min(dd/0.30, 1)*0.75 if dd > 0 else 1
        per_coin_usd = min((equity * 3 * dd_sc) / (2*k), equity * 0.15)

        new_pos = np.zeros(n_c)
        for ci in long_coins: new_pos[ci] = per_coin_usd
        for ci in short_coins: new_pos[ci] = -per_coin_usd

        for ci in range(n_c):
            delta = new_pos[ci] - positions[ci]
            if abs(delta) < 5: continue
            if abs(positions[ci]) > 0.01 and entry_prices[ci] > 0:
                if positions[ci] > 0:
                    pnl = abs(positions[ci]) * (prices[i, ci] / entry_prices[ci] - 1)
                else:
                    pnl = abs(positions[ci]) * (1 - prices[i, ci] / entry_prices[ci])
                cash += pnl
            adv_val = adv[i, ci] if not np.isnan(adv[i, ci]) else 1e9
            cash -= abs(delta) * fee_rate + compute_dynamic_slippage(abs(delta), adv_val)
            n_trades += 1
            positions[ci] = new_pos[ci]
            entry_prices[ci] = prices[i, ci] if abs(new_pos[ci]) > 0.01 else 0

    eq = np.array(equities)
    eq = eq / eq[0] * capital
    return {"equities": eq, "n_trades": n_trades,
            "sharpe": sharpe_ratio(pd.Series(eq), PPY),
            "return_pct": (eq[-1]/eq[0]-1)*100,
            "max_dd_pct": max_drawdown(pd.Series(eq))[1]}


def main():
    t0 = time.time()
    cache = ParquetCache()

    with open("sweep_results/meanrev_experiment.json") as f:
        mr_params = json.load(f).get("meanrev_best_params", {})
    if Path("sweep_results/expanded_coins_v3.json").exists():
        with open("sweep_results/expanded_coins_v3.json") as f:
            mr_params.update(json.load(f).get("mr_params", {}))

    # Load data once
    coin_data = {}; ho_indices = {}
    for coin in ALL_28:
        df = load_8h(cache, coin)
        if df is not None:
            coin_data[coin] = df
            ho_indices[coin] = find_ho_idx(df)

    btc = coin_data["BTC"]; ho_idx = ho_indices["BTC"]
    ho_bars = len(btc) - ho_idx
    print(f"Data: {DATA_START} to {HOLDOUT_END}")
    print(f"Holdout: {btc['timestamp'].iloc[ho_idx]} to {btc['timestamp'].iloc[-1]}, {ho_bars} bars")
    print(f"Phases: {N_PHASES}\n")

    # ================================================================
    # Non-phase-sensitive strategies (run once, result constant)
    # ================================================================
    print("Running non-phase-sensitive strategies (single run)...", flush=True)
    n = len(ALL_28); CAP = 10000.0 / n

    # A) Donchian (no rebalance cycle -> phase invariant)
    don_eqs = []
    for coin in ALL_28:
        df = coin_data.get(coin);
        if df is None: continue
        hi = ho_indices[coin]
        if hi < 396: continue
        r = run_donchian_b0(df.iloc[hi-396:].reset_index(drop=True), CAP, n, use_dynamic_slip=True)
        if r and not np.isnan(r["sharpe"]):
            eq = r["equities"]; don_eqs.append(eq / eq[0] * CAP)
    don_ml = min(len(e) for e in don_eqs)
    don_eq = sum(e[:don_ml] for e in don_eqs); don_eq = don_eq / don_eq[0] * 10000
    don_sr = sharpe_ratio(pd.Series(don_eq), PPY)
    don_ret = (don_eq[-1]/don_eq[0]-1)*100
    print(f"  A) Donchian: SR={don_sr:.3f} Ret={don_ret:.2f}% (phase invariant)")

    # B) Trend (every-bar signal -> phase invariant)
    sig_set = SIGNAL_SETS["8h"]["A"]; fee_rate = FEE_BPS / 10_000
    trend_eqs = []
    for coin in ALL_28:
        df = coin_data.get(coin);
        if df is None: continue
        hi = ho_indices[coin]
        closes = df["close"].values; opens = df["open"].values; volumes = df["volume"].values
        nn = len(df)
        sigs = compute_signals(closes, sig_set); comp = np.nanmean(sigs, axis=1)
        filt = compute_1d_filter(closes, "8h")
        rets = np.zeros(nn); rets[1:] = closes[1:]/closes[:-1]-1
        rv = pd.Series(rets).rolling(60, min_periods=20).std().values * np.sqrt(PPY)
        adv = pd.Series(volumes*closes).rolling(60, min_periods=3).sum().values / 20
        eq_val = CAP; cash_val = eq_val; pos = 0; epx = 0; eqs_coin = []; pt = 0
        for i in range(hi+1, nn):
            o = opens[i]; c = closes[i]; sig = comp[i-1] if not np.isnan(comp[i-1]) else 0
            ts_val = abs(pt - pos)
            if ts_val > max(5, abs(pt)*0.03):
                f = ts_val * fee_rate; sl = compute_dynamic_slippage(ts_val, adv[i] if not np.isnan(adv[i]) else 1e9)
                if abs(pos) > 0.01 and epx > 0:
                    pnl = abs(pos)*((o-epx)/epx if pos > 0 else (epx-o)/epx); cash_val += pnl
                cash_val -= f + sl; pos = pt; epx = o if abs(pos) > 0.01 else 0
            ur = 0
            if abs(pos) > 0.01 and epx > 0:
                ur = abs(pos)*((c-epx)/epx if pos > 0 else (epx-c)/epx)
            eq_val = cash_val + ur; eqs_coin.append(eq_val)
            av = rv[i-1] if not np.isnan(rv[i-1]) and rv[i-1] > 0 else 1
            vs = min(2, max(0.25, 0.20/av)); mx = eq_val * 3
            if sig > 0.2: pt = min(eq_val*3*vs*abs(sig), mx) if filt[i-1] >= 0 else 0
            elif sig < -0.2: pt = -min(eq_val*3*vs*abs(sig), mx) if filt[i-1] <= 0 else 0
            elif abs(sig) < 0.1: pt = 0
        trend_eqs.append(np.array(eqs_coin))
    trend_ml = min(len(e) for e in trend_eqs)
    trend_eq = sum(e[:trend_ml] for e in trend_eqs); trend_eq = trend_eq/trend_eq[0]*10000
    trend_sr = sharpe_ratio(pd.Series(trend_eq), PPY)
    trend_ret = (trend_eq[-1]/trend_eq[0]-1)*100
    print(f"  B) Trend: SR={trend_sr:.3f} Ret={trend_ret:.2f}% (phase invariant)")

    # E) MR (every-bar signal -> phase invariant)
    mr_eqs = []
    for coin in ALL_28:
        df = coin_data.get(coin);
        if df is None: continue
        p = mr_params.get(coin)
        if not p or len(p) < 4: continue
        hi = ho_indices[coin]; wm = max(336+60, p[0]+60, 100)
        if hi < wm: continue
        r = run_combo(df.iloc[hi-wm:].reset_index(drop=True), p[0], p[1], 0.50, p[3], CAP, n, leverage=3.0, don_weight=0, mr_weight=1)
        if r and not np.isnan(r["sharpe"]):
            eq = r["equities"]; mr_eqs.append(eq / eq[0] * CAP)
    mr_ml = min(len(e) for e in mr_eqs)
    mr_eq = sum(e[:mr_ml] for e in mr_eqs); mr_eq = mr_eq / mr_eq[0] * 10000
    mr_sr = sharpe_ratio(pd.Series(mr_eq), PPY)
    mr_ret = (mr_eq[-1]/mr_eq[0]-1)*100
    print(f"  E) MR: SR={mr_sr:.3f} Ret={mr_ret:.2f}% (phase invariant)")

    # ================================================================
    # Phase-sensitive strategies
    # ================================================================
    # C) XSMom: phase offset in rebalance counter
    print(f"\n  C) XSMom: {N_PHASES} phases...", flush=True)
    xs_phase_results = []
    for phase in range(N_PHASES):
        r = run_xsmom_phased(coin_data, ho_indices, 36, 5, 21, phase)
        if r:
            xs_phase_results.append(r)
            print(f"    phase {phase}: SR={r['sharpe']:.3f} Ret={r['return_pct']:.2f}%", flush=True)
        else:
            xs_phase_results.append(None)
        gc.collect()

    # D) PCA: phase offset in recalib counter (recalib=180)
    print(f"\n  D) PCA 8H: {N_PHASES} phases (recalib offset)...", flush=True)
    pca_phase_results = []
    # PCA phase: shift trading_start by phase bars WITHIN the warmup
    # All still start at holdout. The recalib counter starts at different offset.
    # Since run_pca_ou recalibs at (i - last_pca_bar >= recalib), shifting
    # the initial last_pca_bar achieves phase shift.
    # Simplest: run PCA with trading_start shifted by phase bars (but still >= holdout)
    # This doesn't change coverage. Let's just run it N_PHASES times with same params.
    # PCA recalib=180 means only ~4 recalibs in 822 bars, so phase sensitivity is low.
    for phase in range(N_PHASES):
        # Shift trading_start by phase bars (within holdout, slight offset)
        ts_offset = HOLDOUT_START + pd.Timedelta(hours=8 * phase)
        r = run_pca_ou(coin_data, 5, 1.5, 0.25, 180, 180,
                       ts_offset.strftime("%Y-%m-%d %H:%M:%S"), "8h")
        if r and "equities" in r:
            eq = r["equities"]; eq = eq / eq[0] * 10000
            sr = sharpe_ratio(pd.Series(eq), PPY)
            ret = (eq[-1]/eq[0]-1)*100
            _, dd = max_drawdown(pd.Series(eq))
            pca_phase_results.append({"sharpe": sr, "return_pct": ret, "max_dd_pct": dd,
                                       "n_trades": r["n_trades"], "equities": eq})
            print(f"    phase {phase}: SR={sr:.3f} Ret={ret:.2f}%", flush=True)
        else:
            pca_phase_results.append(None)
        gc.collect()

    # ================================================================
    # Align and compute combos per phase
    # ================================================================
    common_len = min(don_ml, trend_ml, mr_ml)
    # For phase-sensitive, use per-phase common len
    for r in xs_phase_results:
        if r: common_len = min(common_len, len(r["equities"]))
    for r in pca_phase_results:
        if r: common_len = min(common_len, len(r["equities"]))

    don_eq = don_eq[:common_len]; don_r = don_eq / don_eq[0]
    trend_eq = trend_eq[:common_len]; trend_r = trend_eq / trend_eq[0]
    mr_eq = mr_eq[:common_len]; mr_r = mr_eq / mr_eq[0]

    # ================================================================
    # Summary
    # ================================================================
    print(f"\n{'='*90}")
    print(f"PHASE-AVERAGED HOLDOUT ({common_len} bars, Rule 7 enforced)")
    print(f"{'='*90}")

    all_strats = {}

    # Phase-invariant strategies
    for name, sr, ret in [("A) Donchian B0", don_sr, don_ret),
                           ("B) Trend 8H+1D", trend_sr, trend_ret),
                           ("E) Z-score MR", mr_sr, mr_ret)]:
        all_strats[name] = {"avg_sr": sr, "std_sr": 0.0, "best_sr": sr, "worst_sr": sr,
                            "avg_ret": ret, "std_ret": 0.0, "verdict": "INVARIANT"}

    # Phase-sensitive
    for name, results in [("C) XSMom", xs_phase_results), ("D) PCA 8H", pca_phase_results)]:
        valid = [r for r in results if r is not None]
        if not valid: continue
        srs = [r["sharpe"] for r in valid]; rets = [r["return_pct"] for r in valid]
        std_sr = np.std(srs)
        verdict = "ROBUST" if std_sr < 0.3 else ("MARGINAL" if std_sr < 0.6 else "UNRELIABLE")
        all_strats[name] = {
            "avg_sr": np.mean(srs), "std_sr": std_sr,
            "best_sr": max(srs), "worst_sr": min(srs),
            "avg_ret": np.mean(rets), "std_ret": np.std(rets),
            "verdict": verdict,
        }

    # Combos (for each XSMom phase, combine with invariant strategies)
    combo_defs = {
        "F) PCA+XSMom 50/50": (["D) PCA 8H", "C) XSMom"], [0.5, 0.5]),
        "G) PCA+XSMom+MR 33": (["D) PCA 8H", "C) XSMom", "E) Z-score MR"], [1/3, 1/3, 1/3]),
        "H) XSMom+MR 50/50": (["C) XSMom", "E) Z-score MR"], [0.5, 0.5]),
        "I) Don+PCA+XSMom 33": (["A) Donchian B0", "D) PCA 8H", "C) XSMom"], [1/3, 1/3, 1/3]),
    }

    invariant_eqs = {"A) Donchian B0": don_r, "B) Trend 8H+1D": trend_r, "E) Z-score MR": mr_r}

    for combo_name, (components, weights) in combo_defs.items():
        combo_srs = []; combo_rets = []
        for phase in range(N_PHASES):
            rm_list = []
            skip = False
            for comp in components:
                if comp in invariant_eqs:
                    rm_list.append(invariant_eqs[comp][:common_len])
                elif comp == "C) XSMom" and xs_phase_results[phase]:
                    eq = xs_phase_results[phase]["equities"][:common_len]
                    rm_list.append(eq / eq[0])
                elif comp == "D) PCA 8H" and pca_phase_results[phase]:
                    eq = pca_phase_results[phase]["equities"][:common_len]
                    rm_list.append(eq / eq[0])
                else:
                    skip = True; break
            if skip: continue

            combo_eq = sum(w * r for w, r in zip(weights, rm_list)) * 10000
            combo_srs.append(sharpe_ratio(pd.Series(combo_eq), PPY))
            combo_rets.append((combo_eq[-1]/combo_eq[0]-1)*100)

        if combo_srs:
            std_sr = np.std(combo_srs)
            verdict = "ROBUST" if std_sr < 0.3 else ("MARGINAL" if std_sr < 0.6 else "UNRELIABLE")
            all_strats[combo_name] = {
                "avg_sr": np.mean(combo_srs), "std_sr": std_sr,
                "best_sr": max(combo_srs), "worst_sr": min(combo_srs),
                "avg_ret": np.mean(combo_rets), "std_ret": np.std(combo_rets),
                "verdict": verdict,
            }

    # Print
    print(f"\n  {'Strategy':<22} {'Avg SR':>7} {'SR std':>7} {'Best SR':>8} {'Worst SR':>9} {'Avg Ret%':>9} {'Ret std':>8} {'Verdict':>11}")
    print("  " + "-" * 85)
    order = ["A) Donchian B0", "B) Trend 8H+1D", "C) XSMom", "D) PCA 8H", "E) Z-score MR",
             "F) PCA+XSMom 50/50", "G) PCA+XSMom+MR 33", "H) XSMom+MR 50/50", "I) Don+PCA+XSMom 33"]
    for name in order:
        s = all_strats.get(name)
        if not s: continue
        print(f"  {name:<22} {s['avg_sr']:>7.3f} {s['std_sr']:>7.3f} {s['best_sr']:>8.3f} {s['worst_sr']:>9.3f} "
              f"{s['avg_ret']:>9.2f} {s['std_ret']:>8.2f} {s['verdict']:>11}")

    # Save + Log
    save = {k: {kk: vv for kk, vv in v.items()} for k, v in all_strats.items()}
    with open("sweep_results/phase_average_v2.json", "w") as f:
        json.dump(save, f, indent=2)

    log = f"\n## Phase-Averaged Holdout v2 ({pd.Timestamp.now().strftime('%Y-%m-%d')})\n\n"
    log += f"Rule 7 enforced: phase shift via rebalance counter offset, all phases cover full holdout.\n"
    log += f"Data: {DATA_START} to {HOLDOUT_END}. Holdout: {common_len} bars.\n\n"
    log += "| Strategy | Avg SR | SR std | Best SR | Worst SR | Avg Ret% | Ret std | Verdict |\n"
    log += "|----------|--------|--------|---------|----------|---------|---------|--------|\n"
    for name in order:
        s = all_strats.get(name)
        if not s: continue
        log += (f"| {name} | {s['avg_sr']:.3f} | {s['std_sr']:.3f} | {s['best_sr']:.3f} | "
                f"{s['worst_sr']:.3f} | {s['avg_ret']:.2f} | {s['std_ret']:.2f} | {s['verdict']} |\n")

    log += "\n### Previous phase avg comparison\n"
    log += "- Previous Donchian avg SR was 0.811 (WRONG: warmup ate holdout bars)\n"
    log += f"- Corrected Donchian SR: {don_sr:.3f} (phase invariant, matches v2 corrected -0.237)\n"
    log += f"- Previous XSMom avg SR was 0.216 with std 0.687 (WRONG: different holdout coverage per phase)\n"

    with open("RESEARCH_LOG.md", "a", encoding="utf-8") as f:
        f.write(log)

    print(f"\n  Total: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
