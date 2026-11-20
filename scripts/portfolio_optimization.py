#!/usr/bin/env python3
"""Portfolio optimization: leverage, dynamic allocation, threshold tuning.

Three directions to improve the 50/50 equal-weight Donchian+MeanRev combo:
1. Leverage adjustment (3x/5x/7x/10x)
2. Dynamic allocation (MR-priority, signal-weighted, 70/30)
3. MR entry threshold reduction (-0.5, -1.0)
Then combine the best from each.
"""

import sys, os, time, json
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptolab.data.cache import ParquetCache
from cryptolab.backtest.metrics import sharpe_ratio, max_drawdown, PERIODS_PER_YEAR
from scripts.donchian_full_sweep import resample_ohlcv
from scripts.mean_reversion_experiment import (
    compute_adx, compute_dynamic_slippage, load_8h_data,
    COINS, PPY_8H, FEE_BPS,
)

MEANREV_PARAMS_PATH = Path("sweep_results/meanrev_experiment.json")


# ---------------------------------------------------------------------------
# Unified backtest: runs BOTH Donchian + MeanRev with configurable params
# ---------------------------------------------------------------------------

def run_combo(df, mr_lookback, mr_entry_z, mr_exit_z, mr_stop_z,
              capital, n_coins, leverage=3.0,
              don_weight=0.5, mr_weight=0.5,
              dynamic_alloc=None):
    """Run Donchian B0 + MeanRev combo with configurable weights and leverage.

    dynamic_alloc: None (fixed weights), "mr_priority", "signal_weighted", or "fixed"
    """
    n = len(df)
    don_lbs = (36, 60, 336)
    max_lb = max(don_lbs)
    warmup = max(max_lb + 60, mr_lookback + 60, 100)
    if n < warmup + 20:
        return None

    highs = df["high"].values; lows = df["low"].values
    closes = df["close"].values; opens = df["open"].values
    volumes = df["volume"].values
    h_s = pd.Series(highs); l_s = pd.Series(lows)

    # Donchian channels
    channels = {}
    for lb in don_lbs:
        channels[lb] = {
            "upper": h_s.rolling(lb).max().shift(1).values,
            "lower": l_s.rolling(lb).min().shift(1).values,
        }

    # ADX + regime
    adx_arr = compute_adx(highs, lows, closes, 20)
    ret = np.zeros(n); ret[1:] = closes[1:]/closes[:-1] - 1
    ret_s = pd.Series(ret)
    vol_10d = ret_s.rolling(30, min_periods=10).std().values
    vol_30d = ret_s.rolling(90, min_periods=30).std().values

    # ATR
    atr_p = 14
    tr_arr = np.maximum(highs[1:]-lows[1:],
                        np.maximum(np.abs(highs[1:]-closes[:-1]),
                                   np.abs(lows[1:]-closes[:-1])))
    tr_arr = np.insert(tr_arr, 0, highs[0]-lows[0])
    atr = np.full(n, np.nan)
    atr[atr_p] = np.mean(tr_arr[:atr_p])
    for i in range(atr_p+1, n):
        atr[i] = atr[i-1]*(atr_p-1)/atr_p + tr_arr[i]/atr_p

    # Z-score
    sma = pd.Series(closes).rolling(mr_lookback, min_periods=mr_lookback).mean().values
    std = pd.Series(closes).rolling(mr_lookback, min_periods=mr_lookback).std(ddof=1).values
    z_score = np.where(std > 1e-10, (closes - sma) / std, 0.0)

    # ADV
    vol_usd = volumes * closes
    adv = pd.Series(vol_usd).rolling(60, min_periods=3).sum().values / 20

    fee_rate = FEE_BPS / 10_000
    equity = capital; cash = equity; pos = 0.0; entry_px = 0.0
    peak = equity; equities = np.full(n, equity)
    daily_returns = []
    n_trades = 0; wins = 0; closed_count = 0; prev_target = 0.0

    # MR state
    mr_side = None

    start = warmup
    prev_equity = equity

    for i in range(start, n):
        o = opens[i]; c = closes[i]; z = z_score[i]

        # Execute
        trade_size = abs(prev_target - pos)
        if trade_size > max(5.0, abs(prev_target) * 0.03):
            fee = trade_size * fee_rate
            slip = compute_dynamic_slippage(trade_size, adv[i])
            if abs(pos) > 0.01 and entry_px > 0:
                pnl = abs(pos) * ((o-entry_px)/entry_px if pos > 0 else (entry_px-o)/entry_px)
                cash += pnl
                if pnl > 0: wins += 1
                closed_count += 1
            cash -= fee + slip; n_trades += 1
            pos = prev_target
            entry_px = o if abs(pos) > 0.01 else 0.0

        unrealized = 0.0
        if abs(pos) > 0.01 and entry_px > 0:
            unrealized = abs(pos) * ((c-entry_px)/entry_px if pos > 0 else (entry_px-c)/entry_px)
        equity = cash + unrealized; peak = max(peak, equity); equities[i] = equity

        # Track daily returns (every 3 bars at 8H = 1 day)
        if (i - start) % 3 == 0 and prev_equity > 0:
            daily_returns.append(equity / prev_equity - 1)
            prev_equity = equity

        # Dynamic allocation
        dw = don_weight; mw = mr_weight
        if dynamic_alloc == "mr_priority":
            # If MR has active position, keep 50/50; else 100% Donchian
            if mr_side is not None:
                dw, mw = 0.5, 0.5
            else:
                dw, mw = 1.0, 0.0
        elif dynamic_alloc == "signal_weighted":
            # More MR positions -> more MR weight (but we only have 1 coin here)
            if mr_side is not None:
                dw = 0.5; mw = 0.5
            else:
                dw = 1.0; mw = 0.0

        # Donchian regime filter
        adx_val = adx_arr[i] if not np.isnan(adx_arr[i]) else 25.0
        don_regime = 1.0 if adx_val >= 25 else (0.5 if adx_val >= 20 else 0.0)
        v10 = vol_10d[i]; v30 = vol_30d[i]
        if not np.isnan(v10) and not np.isnan(v30) and v30 > 0 and v10 < v30*0.7:
            don_regime = 0.0

        # MR regime (inverted)
        if adx_val < 20: mr_regime = 1.0
        elif adx_val < 25: mr_regime = 0.5
        else: mr_regime = 0.0
        if not np.isnan(v10) and not np.isnan(v30) and v30 > 0 and v10 < v30*0.7:
            mr_regime = 0.0

        # --- DONCHIAN (matches run_donchian_b0 logic exactly) ---
        don_target = 0.0
        wts = [0.25, 0.50, 0.25]; dirs = []
        for lb in don_lbs:
            u = channels[lb]["upper"][i]; l = channels[lb]["lower"][i]
            if np.isnan(u) or np.isnan(l): dirs.append(0.0)
            elif c > u: dirs.append(1.0)
            elif c < l: dirs.append(-1.0)
            else: dirs.append(0.0)
        agreement = sum(w*d for w, d in zip(wts, dirs))

        if abs(agreement) < 0.05 or don_regime == 0 or dw == 0:
            # No signal or regime blocks -> flat
            don_target = 0.0
        else:
            direction = 1.0 if agreement > 0 else -1.0
            if not np.isnan(atr[i]) and atr[i] > 0 and c > 0:
                ann_vol = (atr[i]/c) * np.sqrt(PPY_8H)
                vol_sc = max(0.5, min(2.0, 0.15/ann_vol if ann_vol > 0 else 1.0))
            else:
                vol_sc = 1.0
            dd = max(0, 1.0-equity/peak)
            dd_sc = 1.0-min(dd/0.30, 1.0)*0.75 if dd > 0 else 1.0
            base = equity * leverage * abs(agreement) * dw
            don_target = direction * min(base * vol_sc * dd_sc * don_regime,
                                         equity * leverage * dw)

        # --- MEAN REVERSION ---
        mr_target = 0.0
        # Exit
        if mr_side == "long":
            if not np.isnan(z) and (z >= -mr_exit_z or z < -mr_stop_z):
                mr_side = None
        elif mr_side == "short":
            if not np.isnan(z) and (z <= mr_exit_z or z > mr_stop_z):
                mr_side = None

        # Entry or hold (recalculate position size each bar)
        if mr_side is None and mw > 0 and mr_regime > 0 and not np.isnan(z) and not np.isnan(sma[i]):
            stop_z_dist = mr_stop_z - mr_entry_z
            s = std[i] if not np.isnan(std[i]) and std[i] > 0 else c*0.02
            sdp = max(stop_z_dist*s/c, 0.001) if c > 0 else 0.01
            bp = (equity*0.02/sdp) * leverage * mw
            mp = equity * leverage * mw
            avol = (std[i]/c)*np.sqrt(PPY_8H) if not np.isnan(std[i]) and std[i] > 0 and c > 0 else 1.0
            vsc = max(0.5, min(2.0, 0.15/avol)) if avol > 0 else 1.0
            dd_ = max(0, 1.0-equity/peak)
            dsc = 1.0-min(dd_/0.30, 1.0)*0.75 if dd_ > 0 else 1.0
            position = min(bp*vsc*dsc*mr_regime, mp)
            if z < -mr_entry_z and position > 0:
                mr_target = position; mr_side = "long"
            elif z > mr_entry_z and position > 0:
                mr_target = -position; mr_side = "short"

        elif mr_side is not None and mw > 0 and not np.isnan(z) and not np.isnan(sma[i]):
            # Hold: recalculate position size (compounding)
            stop_z_dist = mr_stop_z - mr_entry_z
            s = std[i] if not np.isnan(std[i]) and std[i] > 0 else c*0.02
            sdp = max(stop_z_dist*s/c, 0.001) if c > 0 else 0.01
            bp = (equity*0.02/sdp) * leverage * mw
            mp = equity * leverage * mw
            avol = (std[i]/c)*np.sqrt(PPY_8H) if not np.isnan(std[i]) and std[i] > 0 and c > 0 else 1.0
            vsc = max(0.5, min(2.0, 0.15/avol)) if avol > 0 else 1.0
            dd_ = max(0, 1.0-equity/peak)
            dsc = 1.0-min(dd_/0.30, 1.0)*0.75 if dd_ > 0 else 1.0
            position = min(bp*vsc*dsc*mr_regime, mp)
            if mr_side == "long":
                mr_target = position
            else:
                mr_target = -position

        prev_target = don_target + mr_target

    eq = pd.Series(equities[start:])
    if len(eq) < 10: return None
    sr = sharpe_ratio(eq, PPY_8H); _, dd_pct = max_drawdown(eq)
    max_daily_loss = min(daily_returns) * 100 if daily_returns else 0
    return {
        "sharpe": sr,
        "return_pct": (float(eq.iloc[-1]) - capital) / capital * 100,
        "max_dd_pct": dd_pct,
        "max_daily_loss_pct": max_daily_loss,
        "n_trades": n_trades,
        "win_rate": wins/closed_count*100 if closed_count > 0 else 0,
        "equities": equities[start:].copy(),
    }


def run_portfolio(cache, mr_params, leverage=3.0, don_weight=0.5, mr_weight=0.5,
                  dynamic_alloc=None, z_offset=0.0):
    """Run full portfolio across all coins on holdout. Returns portfolio metrics."""
    n_coins = len(COINS)
    CAPITAL = 10_000.0 / n_coins
    coin_results = {}

    for coin in COINS:
        df = load_8h_data(cache, coin, "2025-07-01", "2026-04-01")
        if df is None: continue

        p = mr_params.get(coin)
        if not p or len(p) != 4: continue

        entry_z = max(1.0, p[1] + z_offset)
        exit_z = p[2]
        stop_z = entry_z + (p[3] - p[1])  # keep stop distance constant

        r = run_combo(df, p[0], entry_z, exit_z, stop_z, CAPITAL, n_coins,
                      leverage=leverage, don_weight=don_weight, mr_weight=mr_weight,
                      dynamic_alloc=dynamic_alloc)
        if r:
            coin_results[coin] = r

    if not coin_results:
        return None

    min_len = min(len(r["equities"]) for r in coin_results.values())
    port_eq = np.zeros(min_len)
    for r in coin_results.values():
        port_eq += r["equities"][:min_len]

    eq_s = pd.Series(port_eq)
    sr = sharpe_ratio(eq_s, PPY_8H)
    _, dd = max_drawdown(eq_s)
    ret = (port_eq[-1] / port_eq[0] - 1) * 100 if port_eq[0] > 0 else 0
    total_trades = sum(r["n_trades"] for r in coin_results.values())

    # Max daily loss
    daily_rets = eq_s.pct_change().dropna()
    max_daily_loss = float(daily_rets.min()) * 100 if len(daily_rets) > 0 else 0

    return {
        "sharpe": sr, "return_pct": ret, "max_dd_pct": dd,
        "max_daily_loss_pct": max_daily_loss, "n_trades": total_trades,
        "n_coins": len(coin_results),
    }


def main():
    t0 = time.time()
    cache = ParquetCache()

    with open(MEANREV_PARAMS_PATH) as f:
        mr_params = json.load(f).get("meanrev_best_params", {})

    results = {}

    # ================================================================
    # Direction 1: Leverage
    # ================================================================
    print("=" * 70)
    print("Direction 1: Leverage Adjustment")
    print("=" * 70)

    for lev in [3, 5, 7, 10]:
        r = run_portfolio(cache, mr_params, leverage=float(lev))
        label = f"50/50 {lev}x"
        results[label] = r
        ok = "OK" if r and r["max_dd_pct"] <= 20 else "REJECT"
        acceptable = r["max_dd_pct"] <= 10 if r else False
        print(f"  {label:<15} Sharpe={r['sharpe']:>7.3f}  Ret={r['return_pct']:>7.2f}%  "
              f"MaxDD={r['max_dd_pct']:>6.2f}%  MaxDayLoss={r['max_daily_loss_pct']:>6.2f}%  "
              f"Trades={r['n_trades']:>4}  {'<= 10% DD' if acceptable else ok}")

    # Find best leverage with MaxDD <= 10%
    best_lev = None; best_lev_sr = -999
    for lev in [3, 5, 7, 10]:
        r = results[f"50/50 {lev}x"]
        if r and r["max_dd_pct"] <= 10 and r["sharpe"] > best_lev_sr:
            best_lev = lev; best_lev_sr = r["sharpe"]
    if best_lev is None:
        best_lev = 3  # fallback
    print(f"\n  Best leverage (MaxDD<=10%): {best_lev}x (Sharpe {best_lev_sr:.3f})")

    # ================================================================
    # Direction 2: Dynamic Allocation
    # ================================================================
    print(f"\n{'=' * 70}")
    print("Direction 2: Dynamic Allocation")
    print("=" * 70)

    alloc_configs = [
        ("50/50 Fixed", 0.5, 0.5, None),
        ("MR Priority", 0.5, 0.5, "mr_priority"),
        ("Signal Weighted", 0.5, 0.5, "signal_weighted"),
        ("70/30 Don/MR", 0.7, 0.3, None),
    ]

    for label, dw, mw, dyn in alloc_configs:
        r = run_portfolio(cache, mr_params, leverage=3.0,
                          don_weight=dw, mr_weight=mw, dynamic_alloc=dyn)
        results[label] = r
        print(f"  {label:<20} Sharpe={r['sharpe']:>7.3f}  Ret={r['return_pct']:>7.2f}%  "
              f"MaxDD={r['max_dd_pct']:>6.2f}%  Trades={r['n_trades']:>4}")

    best_alloc = max(alloc_configs, key=lambda x: results[x[0]]["sharpe"] if results.get(x[0]) else -999)
    print(f"\n  Best allocation: {best_alloc[0]} (Sharpe {results[best_alloc[0]]['sharpe']:.3f})")

    # ================================================================
    # Direction 3: Entry Threshold Adjustment
    # ================================================================
    print(f"\n{'=' * 70}")
    print("Direction 3: MR Entry Threshold Adjustment")
    print("=" * 70)

    for offset, label in [(0.0, "Original Z"), (-0.5, "Z - 0.5"), (-1.0, "Z - 1.0")]:
        r = run_portfolio(cache, mr_params, leverage=3.0, z_offset=offset)
        results[label] = r
        print(f"  {label:<15} Sharpe={r['sharpe']:>7.3f}  Ret={r['return_pct']:>7.2f}%  "
              f"MaxDD={r['max_dd_pct']:>6.2f}%  Trades={r['n_trades']:>4}")

    best_z = max(
        [(0.0, "Original Z"), (-0.5, "Z - 0.5"), (-1.0, "Z - 1.0")],
        key=lambda x: results[x[1]]["sharpe"] if results.get(x[1]) else -999
    )
    print(f"\n  Best threshold: {best_z[1]} (Sharpe {results[best_z[1]]['sharpe']:.3f})")

    # ================================================================
    # Combined Optimal
    # ================================================================
    print(f"\n{'=' * 70}")
    print("Combined Optimal")
    print("=" * 70)

    best_dw, best_mw, best_dyn = best_alloc[1], best_alloc[2], best_alloc[3]
    best_z_off = best_z[0]

    combo_label = f"{best_lev}x + {best_alloc[0]} + {best_z[1]}"
    r_combo = run_portfolio(cache, mr_params, leverage=float(best_lev),
                            don_weight=best_dw, mr_weight=best_mw,
                            dynamic_alloc=best_dyn, z_offset=best_z_off)
    results[combo_label] = r_combo

    # Also test a few other promising combos
    extra_combos = [
        (5, best_alloc[1], best_alloc[2], best_alloc[3], best_z_off,
         f"5x + {best_alloc[0]} + {best_z[1]}"),
        (best_lev, 0.7, 0.3, None, best_z_off,
         f"{best_lev}x + 70/30 + {best_z[1]}"),
    ]
    for lev, dw, mw, dyn, zoff, label in extra_combos:
        if label not in results:
            r = run_portfolio(cache, mr_params, leverage=float(lev),
                              don_weight=dw, mr_weight=mw,
                              dynamic_alloc=dyn, z_offset=zoff)
            results[label] = r

    # Final comparison table
    print(f"\n  {'Method':<35} {'Sharpe':>8} {'Return%':>9} {'MaxDD%':>8} {'Trades':>7}")
    print("  " + "-" * 70)

    comparison_keys = [
        "50/50 Fixed",  # baseline
        f"50/50 {best_lev}x",
        best_alloc[0],
        best_z[1],
        combo_label,
    ]
    # Add extras
    for _, _, _, _, _, label in extra_combos:
        if label not in comparison_keys:
            comparison_keys.append(label)

    for key in comparison_keys:
        r = results.get(key)
        if r:
            dd_flag = " !" if r["max_dd_pct"] > 10 else ""
            print(f"  {key:<35} {r['sharpe']:>8.3f} {r['return_pct']:>9.2f} "
                  f"{r['max_dd_pct']:>8.2f}{dd_flag} {r['n_trades']:>7}")

    # ================================================================
    # Save + RESEARCH_LOG
    # ================================================================
    save_data = {k: {kk: vv for kk, vv in v.items() if kk != "equities"}
                 for k, v in results.items() if v}
    Path("sweep_results").mkdir(exist_ok=True)
    with open("sweep_results/portfolio_optimization.json", "w") as f:
        json.dump(save_data, f, indent=2, default=str)

    log_entry = f"""
## Portfolio Optimization ({pd.Timestamp.now().strftime('%Y-%m-%d')})

### Direction 1: Leverage (50/50 Equal Weight)
| Leverage | Sharpe | Return% | MaxDD% | Max Day Loss% | Trades |
|----------|--------|---------|--------|---------------|--------|
"""
    for lev in [3, 5, 7, 10]:
        r = results[f"50/50 {lev}x"]
        log_entry += f"| {lev}x | {r['sharpe']:.3f} | {r['return_pct']:.2f} | {r['max_dd_pct']:.2f} | {r['max_daily_loss_pct']:.2f} | {r['n_trades']} |\n"
    log_entry += f"\nBest leverage (MaxDD<=10%): **{best_lev}x**\n"

    log_entry += f"""
### Direction 2: Dynamic Allocation (3x leverage)
| Method | Sharpe | Return% | MaxDD% | Trades |
|--------|--------|---------|--------|--------|
"""
    for label, _, _, _ in alloc_configs:
        r = results[label]
        log_entry += f"| {label} | {r['sharpe']:.3f} | {r['return_pct']:.2f} | {r['max_dd_pct']:.2f} | {r['n_trades']} |\n"
    log_entry += f"\nBest allocation: **{best_alloc[0]}**\n"

    log_entry += f"""
### Direction 3: MR Entry Threshold
| Threshold | Sharpe | Return% | MaxDD% | Trades |
|-----------|--------|---------|--------|--------|
"""
    for offset, label in [(0.0, "Original Z"), (-0.5, "Z - 0.5"), (-1.0, "Z - 1.0")]:
        r = results[label]
        log_entry += f"| {label} | {r['sharpe']:.3f} | {r['return_pct']:.2f} | {r['max_dd_pct']:.2f} | {r['n_trades']} |\n"
    log_entry += f"\nBest threshold: **{best_z[1]}**\n"

    log_entry += f"""
### Combined Optimal
| Method | Sharpe | Return% | MaxDD% | Trades |
|--------|--------|---------|--------|--------|
"""
    for key in comparison_keys:
        r = results.get(key)
        if r:
            log_entry += f"| {key} | {r['sharpe']:.3f} | {r['return_pct']:.2f} | {r['max_dd_pct']:.2f} | {r['n_trades']} |\n"

    best_overall = max(
        [(k, r) for k, r in results.items() if r and r.get("max_dd_pct", 99) <= 15],
        key=lambda x: x[1]["sharpe"],
        default=("50/50 Fixed", results.get("50/50 Fixed", {}))
    )
    log_entry += f"\n**Best overall: {best_overall[0]}** (Sharpe {best_overall[1].get('sharpe', 0):.3f}, Return {best_overall[1].get('return_pct', 0):.2f}%, MaxDD {best_overall[1].get('max_dd_pct', 0):.2f}%)\n"

    with open("RESEARCH_LOG.md", "a", encoding="utf-8") as f:
        f.write(log_entry)

    print(f"\n  Results saved. Total time: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
