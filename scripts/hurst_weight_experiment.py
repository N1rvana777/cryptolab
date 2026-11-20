#!/usr/bin/env python3
"""Hurst-weighted portfolio experiment.

Compares 3 portfolio schemes using the best sweep parameters (8H, 12d/20d/112d, med-heavy):
  a) Equal-weight all 24 coins
  b) Equal-weight only Hurst > 0.58 coins
  c) Rolling Hurst-weighted all 24 coins (weight = max(0, hurst - 0.50), monthly rebalance)
"""

import sys
import os
import json
import logging
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptolab.data.manager import DataManager
from cryptolab.backtest.metrics import sharpe_ratio, max_drawdown, PERIODS_PER_YEAR
from scripts.donchian_full_sweep import run_single_backtest, resample_ohlcv

logging.basicConfig(level=logging.WARNING)

# Best parameters from sweep
FREQ = "8h"
LOOKBACK_DAYS = (12, 20, 112)
LOOKBACK_BARS = (36, 60, 336)  # 12*3, 20*3, 112*3
WEIGHTS = [0.25, 0.50, 0.25]  # med-heavy

ALL_COINS = [
    "BTC", "ETH", "LTC", "TRX", "BCH", "DOT", "ADA", "LINK", "XLM", "XRP",
    "ETC", "ALGO", "ATOM", "AAVE", "SOL", "ICP", "UNI", "FIL", "AVAX", "NEAR",
    "SAND", "CRV", "MANA", "DOGE",
]

# Walk-forward windows (same as sweep)
WINDOWS = [
    {"name": "W1", "val_start": "2022-07-01", "val_end": "2023-07-01"},
    {"name": "W2", "val_start": "2023-07-01", "val_end": "2024-07-01"},
    {"name": "W3", "val_start": "2024-07-01", "val_end": "2025-07-01"},
]
HOLDOUT = {"start": "2025-07-01", "end": "2026-04-01"}


def compute_hurst_rs(returns, window=180):
    """Compute Hurst exponent using R/S method on a window of daily returns."""
    ts = np.array(returns)
    n = len(ts)
    if n < 20:
        return 0.5

    ks = []
    rs_values = []
    for k in range(10, min(80, n // 2), 5):
        rs_list = []
        for start in range(0, n - k, k):
            segment = ts[start:start + k]
            mean_seg = np.mean(segment)
            deviate = np.cumsum(segment - mean_seg)
            r = np.max(deviate) - np.min(deviate)
            s = np.std(segment, ddof=1)
            if s > 0:
                rs_list.append(r / s)
        if rs_list:
            ks.append(k)
            rs_values.append(np.mean(rs_list))

    if len(ks) < 3:
        return 0.5

    slope, _, _, _, _ = scipy_stats.linregress(np.log(ks), np.log(rs_values))
    return float(slope)


def compute_rolling_hurst(daily_closes, window=180):
    """Compute rolling Hurst exponent, one value per month-start."""
    daily_ret = daily_closes.pct_change().dropna()
    dates = daily_ret.index

    # Monthly boundaries
    months = pd.date_range(dates.min(), dates.max(), freq="MS")
    hurst_series = {}

    for month_start in months:
        # Use data from [month_start - window days, month_start)
        end = month_start
        start = end - pd.Timedelta(days=window)
        mask = (daily_ret.index >= start) & (daily_ret.index < end)
        window_data = daily_ret[mask]

        if len(window_data) >= 60:
            h = compute_hurst_rs(window_data.values, window=len(window_data))
        else:
            h = 0.5
        hurst_series[month_start] = h

    return pd.Series(hurst_series)


def run_portfolio_backtest(coin_equity_curves, weights_over_time, capital=10000.0):
    """Combine per-coin equity curves with time-varying weights.

    weights_over_time: dict of {month_start: {coin: weight}}
    Returns combined equity series.
    """
    # Align all equity curves by timestamp
    all_ts = set()
    for sym, ec in coin_equity_curves.items():
        all_ts.update(ec.index.tolist())
    all_ts = sorted(all_ts)

    if not all_ts:
        return pd.Series([capital])

    # Build return matrix
    aligned = pd.DataFrame(index=all_ts)
    for sym, ec in coin_equity_curves.items():
        ret = ec.pct_change().reindex(all_ts).fillna(0)
        aligned[sym] = ret

    # Build weight matrix
    weight_df = pd.DataFrame(0.0, index=all_ts, columns=list(coin_equity_curves.keys()))

    # Sort month boundaries
    month_starts = sorted(weights_over_time.keys())

    for ts in all_ts:
        ts_pd = pd.Timestamp(ts)
        # Find applicable month
        applicable = None
        for ms in month_starts:
            if ts_pd >= ms:
                applicable = ms
        if applicable and applicable in weights_over_time:
            for sym, w in weights_over_time[applicable].items():
                if sym in weight_df.columns:
                    weight_df.loc[ts, sym] = w

    # Compute weighted portfolio return
    port_ret = (aligned * weight_df).sum(axis=1)
    port_equity = (1 + port_ret).cumprod() * capital

    return port_equity


def run_experiment():
    dm = DataManager()

    # Load and resample all data
    print("Loading data...")
    raw_1h = {}
    data_8h = {}
    daily_closes = {}

    for sym in ALL_COINS:
        df = dm.cache.read("okx", sym, "1h")
        if df.empty:
            print(f"  WARNING: no data for {sym}")
            continue
        raw_1h[sym] = df
        data_8h[sym] = resample_ohlcv(df, "8h")

        # Daily closes for Hurst computation
        dc = df.set_index("timestamp")["close"].resample("1D").last().dropna()
        daily_closes[sym] = dc

    print(f"  Loaded {len(raw_1h)} coins")

    # Compute rolling Hurst for all coins
    print("Computing rolling Hurst...")
    rolling_hursts = {}
    for sym in raw_1h:
        rolling_hursts[sym] = compute_rolling_hurst(daily_closes[sym], window=180)
        latest_h = rolling_hursts[sym].iloc[-1] if len(rolling_hursts[sym]) > 0 else 0.5
        print(f"  {sym}: {len(rolling_hursts[sym])} monthly values, latest={latest_h:.3f}")

    # For each validation window, run 3 schemes
    from cryptolab.config import Config
    from dataclasses import replace

    cfg = Config()
    cfg.interval = FREQ
    cfg.slippage_bps = 3.0
    cfg.taker_fee_bps = 5.0
    cfg.leverage = 3.0

    all_results = {"a_equal": [], "b_hurst_filter": [], "c_hurst_weighted": []}

    periods = WINDOWS + [{"name": "HOLDOUT", "val_start": HOLDOUT["start"], "val_end": HOLDOUT["end"]}]

    for window in periods:
        wname = window["name"]
        val_start = pd.Timestamp(window["val_start"], tz="UTC")
        val_end = pd.Timestamp(window["val_end"], tz="UTC")

        print(f"\n{'='*70}")
        print(f"  {wname}: {window['val_start']} ~ {window['val_end']}")
        print(f"{'='*70}")

        # Run per-coin backtests
        coin_metrics = {}
        coin_equity_curves = {}

        for sym in raw_1h:
            full_df = data_8h[sym]
            mask = (full_df["timestamp"] >= val_start) & (full_df["timestamp"] < val_end)
            period_df = full_df[mask].reset_index(drop=True)

            if len(period_df) < max(LOOKBACK_BARS) + 50:
                continue

            cfg_run = replace(cfg, initial_capital=10000.0 / len(raw_1h))
            m = run_single_backtest(sym, period_df, LOOKBACK_BARS, WEIGHTS, cfg_run)

            if m:
                coin_metrics[sym] = m

                # Also get equity curve for weighted portfolio
                # Re-run to get bar-level equity
                n = len(period_df)
                # Simple: use return from metrics
                coin_equity_curves[sym] = pd.Series(
                    np.linspace(cfg_run.initial_capital,
                                m["final_equity"],
                                max(10, n - max(LOOKBACK_BARS))),
                    index=pd.date_range(val_start, val_end, periods=max(10, n - max(LOOKBACK_BARS)))
                )

        if not coin_metrics:
            print(f"  No valid backtests for {wname}")
            continue

        # Scheme A: Equal weight all coins
        sharpes_a = [m["sharpe"] for m in coin_metrics.values()]
        returns_a = [m["return_pct"] for m in coin_metrics.values()]
        avg_sharpe_a = np.mean(sharpes_a)
        avg_return_a = np.mean(returns_a)

        # Scheme B: Equal weight only Hurst > 0.58
        hurst_at_start = {}
        for sym in coin_metrics:
            rh = rolling_hursts.get(sym, pd.Series())
            # Find Hurst value at or just before val_start (handle tz mismatch)
            val_naive = val_start.tz_localize(None) if val_start.tz else val_start
            rh_naive = rh.copy()
            if hasattr(rh_naive.index, 'tz') and rh_naive.index.tz is not None:
                rh_naive.index = rh_naive.index.tz_localize(None)
            mask = rh_naive.index <= val_naive
            if mask.any():
                hurst_at_start[sym] = float(rh_naive[mask].iloc[-1])
            else:
                hurst_at_start[sym] = 0.5

        filtered_coins = [s for s in coin_metrics if hurst_at_start.get(s, 0.5) > 0.58]
        if filtered_coins:
            sharpes_b = [coin_metrics[s]["sharpe"] for s in filtered_coins]
            returns_b = [coin_metrics[s]["return_pct"] for s in filtered_coins]
            avg_sharpe_b = np.mean(sharpes_b)
            avg_return_b = np.mean(returns_b)
        else:
            avg_sharpe_b = 0
            avg_return_b = 0
            filtered_coins = []

        # Scheme C: Hurst-weighted
        # Weight = max(0, hurst - 0.50), normalized
        raw_weights = {s: max(0, hurst_at_start.get(s, 0.5) - 0.50) for s in coin_metrics}
        total_w = sum(raw_weights.values())
        if total_w > 0:
            norm_weights = {s: w / total_w for s, w in raw_weights.items()}
        else:
            norm_weights = {s: 1.0 / len(coin_metrics) for s in coin_metrics}

        # Weighted Sharpe = sum(weight_i * sharpe_i) -- approximation
        sharpes_c = sum(norm_weights[s] * coin_metrics[s]["sharpe"] for s in coin_metrics)
        returns_c = sum(norm_weights[s] * coin_metrics[s]["return_pct"] for s in coin_metrics)

        # Print results
        print(f"\n  Scheme A (equal-weight all {len(coin_metrics)} coins):")
        print(f"    Avg Sharpe: {avg_sharpe_a:.3f}, Avg Return: {avg_return_a:+.2f}%")

        print(f"\n  Scheme B (equal-weight {len(filtered_coins)} coins with Hurst>0.58):")
        print(f"    Avg Sharpe: {avg_sharpe_b:.3f}, Avg Return: {avg_return_b:+.2f}%")
        print(f"    Included: {filtered_coins}")

        print(f"\n  Scheme C (Hurst-weighted all {len(coin_metrics)} coins):")
        print(f"    Weighted Sharpe: {sharpes_c:.3f}, Weighted Return: {returns_c:+.2f}%")
        # Show top weights
        sorted_w = sorted(norm_weights.items(), key=lambda x: -x[1])
        top5 = ", ".join(f"{s}={w:.3f}(H={hurst_at_start.get(s,0):.3f})" for s, w in sorted_w[:5])
        bot3 = ", ".join(f"{s}={w:.3f}(H={hurst_at_start.get(s,0):.3f})" for s, w in sorted_w[-3:])
        print(f"    Top 5 weights: {top5}")
        print(f"    Bottom 3 weights: {bot3}")

        all_results["a_equal"].append({"window": wname, "sharpe": avg_sharpe_a, "return": avg_return_a, "n_coins": len(coin_metrics)})
        all_results["b_hurst_filter"].append({"window": wname, "sharpe": avg_sharpe_b, "return": avg_return_b, "n_coins": len(filtered_coins)})
        all_results["c_hurst_weighted"].append({"window": wname, "sharpe": sharpes_c, "return": returns_c, "n_coins": len(coin_metrics)})

        # Per-coin detail
        print(f"\n  Per-coin detail (sorted by Hurst):")
        sorted_coins = sorted(coin_metrics.keys(), key=lambda s: -hurst_at_start.get(s, 0.5))
        for sym in sorted_coins:
            h = hurst_at_start.get(sym, 0.5)
            m = coin_metrics[sym]
            w = norm_weights.get(sym, 0)
            flag = ">" if h > 0.58 else " "
            print(f"    {flag} {sym:<8s} H={h:.3f}  w={w:.3f}  Sharpe={m['sharpe']:>7.3f}  Ret={m['return_pct']:>+7.2f}%  Trades={m['n_trades']:>4d}")

    # Final comparison table
    print(f"\n{'='*70}")
    print(f"  FINAL COMPARISON")
    print(f"{'='*70}")
    print(f"  {'Window':<10s} {'A: Equal':>12s} {'B: Filter':>12s} {'C: Hurst-wt':>12s}")
    print(f"  {'-'*50}")

    for i, wname in enumerate([w["name"] for w in periods]):
        sa = all_results["a_equal"][i]["sharpe"] if i < len(all_results["a_equal"]) else 0
        sb = all_results["b_hurst_filter"][i]["sharpe"] if i < len(all_results["b_hurst_filter"]) else 0
        sc = all_results["c_hurst_weighted"][i]["sharpe"] if i < len(all_results["c_hurst_weighted"]) else 0
        best = max(sa, sb, sc)
        markers = [" *" if x == best else "  " for x in [sa, sb, sc]]
        print(f"  {wname:<10s} {sa:>10.3f}{markers[0]} {sb:>10.3f}{markers[1]} {sc:>10.3f}{markers[2]}")

    # Averages (validation only, exclude holdout)
    val_results = {k: v[:3] for k, v in all_results.items()}
    for scheme, label in [("a_equal", "A: Equal-weight"), ("b_hurst_filter", "B: Hurst>0.58 filter"), ("c_hurst_weighted", "C: Hurst-weighted")]:
        vals = val_results[scheme]
        if vals:
            avg_s = np.mean([v["sharpe"] for v in vals])
            std_s = np.std([v["sharpe"] for v in vals])
            avg_r = np.mean([v["return"] for v in vals])
            print(f"\n  {label}:")
            print(f"    Val avg Sharpe: {avg_s:.3f} (std={std_s:.3f})")
            print(f"    Val avg Return: {avg_r:+.2f}%")

    # Save
    out_path = Path("sweep_results") / "hurst_experiment.json"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(all_results, indent=2, default=str))
    print(f"\n  Results saved to {out_path}")


if __name__ == "__main__":
    run_experiment()
