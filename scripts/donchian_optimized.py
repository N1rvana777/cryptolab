#!/usr/bin/env python3
"""Donchian Breakout + Optimization Modules A/B test.

A0: Base Donchian (8H, 12d/20d/112d, med-heavy)
A1: + Regime Detection Filter (ADX + vol contraction)
A2: + Dynamic Lookback (vol-adaptive)
A3: + Vol-Adaptive Position Sizing (risk parity)

Walk-Forward: 3 windows + Holdout, 24 crypto coins.
"""

import sys, os, time, json, logging
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptolab.data.manager import DataManager
from cryptolab.backtest.metrics import sharpe_ratio, max_drawdown
from scripts.donchian_full_sweep import resample_ohlcv

logging.basicConfig(level=logging.WARNING)

COINS = ["BTC","ETH","LTC","TRX","BCH","DOT","ADA","LINK","XLM","XRP",
         "ETC","ALGO","ATOM","AAVE","SOL","ICP","UNI","FIL","AVAX","NEAR",
         "SAND","CRV","MANA","DOGE"]

BASE_LOOKBACKS = (36, 60, 336)  # 12d/20d/112d at 8H (3 bars/day)
BASE_WEIGHTS = [0.25, 0.50, 0.25]  # med-heavy
FREQ = "8h"
PPY = 1096  # 8H bars per year
FEE_RATE = (5 + 3) / 10_000

WINDOWS = [
    {"name": "W1", "is_end": "2022-07-01", "val_start": "2022-07-01", "val_end": "2023-07-01"},
    {"name": "W2", "is_end": "2023-07-01", "val_start": "2023-07-01", "val_end": "2024-07-01"},
    {"name": "W3", "is_end": "2024-07-01", "val_start": "2024-07-01", "val_end": "2025-07-01"},
]
HOLDOUT = {"start": "2025-07-01", "end": "2026-04-01"}


def compute_adx(highs, lows, closes, period=20):
    """Compute ADX array."""
    n = len(highs)
    adx = np.full(n, np.nan)
    if n < period * 2:
        return adx

    # True Range, +DM, -DM
    tr = np.zeros(n)
    plus_dm = np.zeros(n)
    minus_dm = np.zeros(n)
    for i in range(1, n):
        h_diff = highs[i] - highs[i-1]
        l_diff = lows[i-1] - lows[i]
        tr[i] = max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1]))
        plus_dm[i] = h_diff if (h_diff > l_diff and h_diff > 0) else 0
        minus_dm[i] = l_diff if (l_diff > h_diff and l_diff > 0) else 0

    # Smoothed TR, +DM, -DM
    atr_s = np.zeros(n)
    pdm_s = np.zeros(n)
    mdm_s = np.zeros(n)
    atr_s[period] = np.sum(tr[1:period+1])
    pdm_s[period] = np.sum(plus_dm[1:period+1])
    mdm_s[period] = np.sum(minus_dm[1:period+1])
    for i in range(period+1, n):
        atr_s[i] = atr_s[i-1] - atr_s[i-1]/period + tr[i]
        pdm_s[i] = pdm_s[i-1] - pdm_s[i-1]/period + plus_dm[i]
        mdm_s[i] = mdm_s[i-1] - mdm_s[i-1]/period + minus_dm[i]

    # DI+, DI-, DX
    dx = np.zeros(n)
    for i in range(period, n):
        if atr_s[i] > 0:
            pdi = 100 * pdm_s[i] / atr_s[i]
            mdi = 100 * mdm_s[i] / atr_s[i]
            if pdi + mdi > 0:
                dx[i] = 100 * abs(pdi - mdi) / (pdi + mdi)

    # ADX = smoothed DX
    adx[period*2] = np.mean(dx[period:period*2+1])
    for i in range(period*2+1, n):
        adx[i] = (adx[i-1] * (period-1) + dx[i]) / period

    return adx


def run_backtest(df, lookbacks, weights, version="A0", capital=10000.0/24):
    """Run Donchian backtest with optional optimization modules."""
    n = len(df)
    lb_s, lb_m, lb_l = [int(x) for x in lookbacks]
    max_lb = max(lb_s, lb_m, lb_l)

    if n < max_lb + 50:
        return None

    highs = df["high"].values
    lows = df["low"].values
    closes = df["close"].values
    opens = df["open"].values

    h_s = pd.Series(highs)
    l_s = pd.Series(lows)

    upper_s = h_s.rolling(lb_s).max().shift(1).values
    lower_s = l_s.rolling(lb_s).min().shift(1).values
    upper_m = h_s.rolling(lb_m).max().shift(1).values
    lower_m = l_s.rolling(lb_m).min().shift(1).values
    upper_l = h_s.rolling(lb_l).max().shift(1).values
    lower_l = l_s.rolling(lb_l).min().shift(1).values

    # ATR
    atr_period = 14
    tr = np.maximum(highs[1:]-lows[1:], np.maximum(np.abs(highs[1:]-closes[:-1]), np.abs(lows[1:]-closes[:-1])))
    tr = np.insert(tr, 0, highs[0]-lows[0])
    atr = np.full(n, np.nan)
    atr[atr_period] = np.mean(tr[:atr_period])
    for i in range(atr_period+1, n):
        atr[i] = atr[i-1]*(atr_period-1)/atr_period + tr[i]/atr_period

    # Module A: ADX + vol contraction
    adx = compute_adx(highs, lows, closes, 20) if version in ("A1","A2","A3") else None

    # Rolling vol for regime and dynamic lookback
    ret = np.zeros(n)
    ret[1:] = closes[1:]/closes[:-1] - 1
    vol_10 = pd.Series(ret).rolling(10*3).std().values  # 10 days at 8H = 30 bars
    vol_30 = pd.Series(ret).rolling(30*3).std().values  # 30 days

    # Module B: Dynamic lookback - need rolling vol quantiles
    if version in ("A2", "A3"):
        vol_20 = pd.Series(ret).rolling(20*3).std().values
        # Expanding quantiles (no look-ahead)
        vol_q25 = pd.Series(vol_20).expanding(min_periods=60*3).quantile(0.25).values
        vol_q75 = pd.Series(vol_20).expanding(min_periods=60*3).quantile(0.75).values

    equity = capital
    cash = equity
    position_usd = 0.0
    entry_px = 0.0
    peak_equity = equity
    wt_s, wt_m, wt_l = weights
    equities = np.full(n, equity)
    n_trades = 0
    wins = 0
    closed_trades = 0
    prev_target = 0.0
    start_bar = max_lb + 50

    for i in range(start_bar, n):
        open_px = opens[i]
        close_px = closes[i]

        if abs(prev_target - position_usd) > max(5.0, abs(prev_target)*0.03):
            delta = abs(prev_target - position_usd)
            fee = delta * FEE_RATE
            if abs(position_usd) > 0.01 and entry_px > 0:
                pnl = abs(position_usd) * ((open_px-entry_px)/entry_px if position_usd > 0 else (entry_px-open_px)/entry_px)
                cash += pnl
                if pnl > 0: wins += 1
                closed_trades += 1
            cash -= fee
            n_trades += 1
            position_usd = prev_target
            entry_px = open_px if abs(position_usd) > 0.01 else 0.0

        unrealized = 0.0
        if abs(position_usd) > 0.01 and entry_px > 0:
            unrealized = abs(position_usd) * ((close_px-entry_px)/entry_px if position_usd > 0 else (entry_px-close_px)/entry_px)
        equity = cash + unrealized
        peak_equity = max(peak_equity, equity)
        equities[i] = equity

        # Dynamic lookback (Module B)
        if version in ("A2", "A3") and not np.isnan(vol_20[i]) and not np.isnan(vol_q25[i]) and not np.isnan(vol_q75[i]):
            if vol_20[i] > vol_q75[i]:
                lb_mult = 0.7
            elif vol_20[i] < vol_q25[i]:
                lb_mult = 1.5
            else:
                lb_mult = 1.0
            cur_lb_s = max(6, int(lb_s * lb_mult))
            cur_lb_m = max(12, int(lb_m * lb_mult))
            cur_lb_l = max(24, int(lb_l * lb_mult))
            # Recompute channels for current bar with dynamic lookback
            u_s = np.max(highs[max(0,i-cur_lb_s):i]) if i >= cur_lb_s else np.nan
            l_s_v = np.min(lows[max(0,i-cur_lb_s):i]) if i >= cur_lb_s else np.nan
            u_m = np.max(highs[max(0,i-cur_lb_m):i]) if i >= cur_lb_m else np.nan
            l_m_v = np.min(lows[max(0,i-cur_lb_m):i]) if i >= cur_lb_m else np.nan
            u_l = np.max(highs[max(0,i-cur_lb_l):i]) if i >= cur_lb_l else np.nan
            l_l_v = np.min(lows[max(0,i-cur_lb_l):i]) if i >= cur_lb_l else np.nan
        else:
            u_s, l_s_v = upper_s[i], lower_s[i]
            u_m, l_m_v = upper_m[i], lower_m[i]
            u_l, l_l_v = upper_l[i], lower_l[i]

        cur_close = closes[i]
        def tf_dir(u, l):
            if np.isnan(u) or np.isnan(l): return 0.0
            if cur_close > u: return 1.0
            elif cur_close < l: return -1.0
            return 0.0

        agreement = tf_dir(u_s, l_s_v)*wt_s + tf_dir(u_m, l_m_v)*wt_m + tf_dir(u_l, l_l_v)*wt_l

        # Regime filter (Module A)
        regime_scale = 1.0
        if version in ("A1","A2","A3") and adx is not None:
            adx_val = adx[i] if not np.isnan(adx[i]) else 25.0
            if adx_val < 20:
                regime_scale = 0.0  # no new positions
            elif adx_val < 25:
                regime_scale = 0.5
            # Vol contraction check
            if not np.isnan(vol_10[i]) and not np.isnan(vol_30[i]) and vol_30[i] > 0:
                if vol_10[i] < vol_30[i] * 0.7:
                    regime_scale = min(regime_scale, 0.0)

        if abs(agreement) < 0.05 or regime_scale == 0:
            if regime_scale == 0 and abs(position_usd) < 0.01:
                prev_target = 0.0
                continue
            elif abs(agreement) < 0.05:
                prev_target = 0.0
                continue

        # Vol scalar
        if not np.isnan(atr[i]) and atr[i] > 0 and close_px > 0:
            ann_vol = (atr[i]/close_px) * np.sqrt(PPY)
            vol_scalar = 0.15 / ann_vol if ann_vol > 0 else 1.0
            vol_scalar = max(0.5, min(2.0, vol_scalar))
        else:
            vol_scalar = 1.0

        dd = max(0, 1.0-equity/peak_equity)
        dd_scalar = 1.0 - min(dd/0.30, 1.0) * 0.75 if dd > 0 else 1.0

        # Module C: Vol-adaptive position sizing
        if version == "A3" and not np.isnan(vol_20[i]) and vol_20[i] > 0:
            # Target: equal risk contribution per coin
            target_risk = equity / len(COINS)
            ann_vol_coin = vol_20[i] * np.sqrt(PPY)
            if ann_vol_coin > 0:
                vol_pos = target_risk / ann_vol_coin
                vol_pos = min(vol_pos, equity * 0.20)  # cap at 20% of equity per coin
                direction = 1.0 if agreement > 0 else -1.0
                prev_target = direction * vol_pos * regime_scale * dd_scalar
            else:
                prev_target = 0.0
        else:
            direction = 1.0 if agreement > 0 else -1.0
            base_pos = equity * 3.0 * abs(agreement)
            target = direction * base_pos * vol_scalar * dd_scalar * regime_scale
            max_pos = equity * 3.0
            prev_target = max(-max_pos, min(max_pos, target))

    eq = pd.Series(equities[start_bar:])
    if len(eq) < 10: return None
    sr = sharpe_ratio(eq, PPY)
    _, dd_pct = max_drawdown(eq)
    final = float(eq.iloc[-1])
    ret_pct = (final-capital)/capital*100
    wr = wins/closed_trades*100 if closed_trades > 0 else 0
    return {"sharpe": sr, "return_pct": ret_pct, "max_dd_pct": dd_pct,
            "n_trades": n_trades, "win_rate": wr, "final_equity": final}


def main():
    dm = DataManager()
    print("Loading crypto data...")
    raw_1h = {}
    for sym in COINS:
        df = dm.cache.read("okx", sym, "1h")
        if not df.empty:
            raw_1h[sym] = resample_ohlcv(df, "8h")
    print(f"  Loaded {len(raw_1h)} coins")

    versions = ["A0", "A1", "A2", "A3"]
    all_results = {v: [] for v in versions}

    periods = WINDOWS + [{"name": "HOLDOUT", "val_start": HOLDOUT["start"], "val_end": HOLDOUT["end"]}]

    for window in periods:
        wname = window["name"]
        val_start = pd.Timestamp(window["val_start"], tz="UTC")
        val_end = pd.Timestamp(window["val_end"], tz="UTC")

        print(f"\n{'='*70}")
        print(f"  {wname}: {window['val_start']} ~ {window['val_end']}")
        print(f"{'='*70}")

        for ver in versions:
            coin_sharpes = []
            coin_rets = []
            coin_dds = []
            coin_trades = []
            for sym in raw_1h:
                full_df = raw_1h[sym]
                mask = (full_df["timestamp"] >= val_start) & (full_df["timestamp"] < val_end)
                period_df = full_df[mask].reset_index(drop=True)
                if len(period_df) < max(BASE_LOOKBACKS) + 60:
                    continue
                m = run_backtest(period_df, BASE_LOOKBACKS, BASE_WEIGHTS, version=ver)
                if m:
                    coin_sharpes.append(m["sharpe"])
                    coin_rets.append(m["return_pct"])
                    coin_dds.append(m["max_dd_pct"])
                    coin_trades.append(m["n_trades"])

            if coin_sharpes:
                avg_s = np.mean(coin_sharpes)
                avg_r = np.mean(coin_rets)
                worst_dd = max(coin_dds)
                total_t = sum(coin_trades)
                all_results[ver].append({
                    "window": wname, "sharpe": avg_s, "return": avg_r,
                    "max_dd": worst_dd, "trades": total_t, "n_coins": len(coin_sharpes)
                })
                print(f"  {ver}: Sharpe={avg_s:.3f}  Ret={avg_r:+.2f}%  MaxDD={worst_dd:.2f}%  Trades={total_t}")

    # Summary
    print(f"\n{'='*70}")
    print(f"  COMPARISON TABLE")
    print(f"{'='*70}")
    print(f"  {'Version':<8s} {'W1 Sharpe':>10s} {'W2 Sharpe':>10s} {'W3 Sharpe':>10s} {'Avg Val':>10s} {'Holdout':>10s}")
    print(f"  {'-'*55}")
    for ver in versions:
        results = all_results[ver]
        vals = [r["sharpe"] for r in results if r["window"] != "HOLDOUT"]
        ho = [r["sharpe"] for r in results if r["window"] == "HOLDOUT"]
        avg_val = np.mean(vals) if vals else 0
        ho_s = ho[0] if ho else 0
        row = f"  {ver:<8s}"
        for r in results[:3]:
            row += f" {r['sharpe']:>10.3f}"
        row += f" {avg_val:>10.3f} {ho_s:>10.3f}"
        print(row)

    # Incremental contribution
    print(f"\n  Incremental Contribution:")
    for i in range(1, len(versions)):
        prev = versions[i-1]
        curr = versions[i]
        prev_vals = [r["sharpe"] for r in all_results[prev] if r["window"] != "HOLDOUT"]
        curr_vals = [r["sharpe"] for r in all_results[curr] if r["window"] != "HOLDOUT"]
        if prev_vals and curr_vals:
            delta = np.mean(curr_vals) - np.mean(prev_vals)
            label = {1: "Regime Filter", 2: "Dynamic Lookback", 3: "Vol-Adaptive Sizing"}[i]
            status = "POSITIVE" if delta > 0.02 else ("NEGATIVE" if delta < -0.02 else "NEGLIGIBLE")
            print(f"    {prev}->{curr} ({label}): Sharpe delta = {delta:+.3f} [{status}]")

    Path("sweep_results").mkdir(exist_ok=True)
    Path("sweep_results/donchian_optimized.json").write_text(
        json.dumps(all_results, indent=2, default=str))
    print(f"\n  Results saved to sweep_results/donchian_optimized.json")


if __name__ == "__main__":
    main()
