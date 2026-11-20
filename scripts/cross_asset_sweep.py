#!/usr/bin/env python3
"""Cross-asset Donchian Breakout walk-forward experiment.

Uses Yahoo Finance daily data for traditional assets (indices, commodities, forex, bonds, stocks).
Validates whether cross-asset diversification improves Sharpe vs pure crypto.

Usage:
    python scripts/cross_asset_sweep.py
"""

import itertools
import json
import logging
import sys
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptolab.backtest.metrics import sharpe_ratio, max_drawdown

logging.basicConfig(level=logging.WARNING)

# ── Assets ──
ASSETS = {
    "Indices": ["SPY", "QQQ", "IWM", "DIA"],
    "Commodities": ["GC=F", "SI=F", "CL=F", "BZ=F", "HG=F", "NG=F", "PL=F", "PA=F"],
    "Forex": ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X",
              "USDCHF=X", "NZDUSD=X", "EURGBP=X", "EURJPY=X"],
    "Bonds": ["TLT", "IEF"],
    "Stocks": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META"],
}
ALL_TICKERS = [t for tickers in ASSETS.values() for t in tickers]
TICKER_CAT = {t: cat for cat, tickers in ASSETS.items() for t in tickers}

# ── Walk-Forward Windows ──
WINDOWS = [
    {"name": "W1", "is_end": "2018-01-01", "val_start": "2018-01-01", "val_end": "2019-01-01"},
    {"name": "W2", "is_end": "2019-01-01", "val_start": "2019-01-01", "val_end": "2020-01-01"},
    {"name": "W3", "is_end": "2020-01-01", "val_start": "2020-01-01", "val_end": "2021-01-01"},
    {"name": "W4", "is_end": "2021-01-01", "val_start": "2021-01-01", "val_end": "2022-01-01"},
    {"name": "W5", "is_end": "2022-01-01", "val_start": "2022-01-01", "val_end": "2023-01-01"},
]
IS_START = "2015-01-01"
HOLDOUT = {"start": "2023-01-01", "end": "2026-01-01"}

# ── Parameters ──
SHORT_LBS = [12, 18, 24, 36, 48]
MID_LBS = [48, 72, 96, 120, 168]
LONG_LBS = [168, 252, 336, 504, 672]
WEIGHT_SETS = {
    "equal": [0.33, 0.34, 0.33],
    "med-heavy": [0.25, 0.50, 0.25],
}
FEE_RATE = (8 + 3) / 10_000  # 0.08% fee + 0.03% slippage per side
PPY = 252  # trading days per year


def generate_combos():
    combos = []
    for s, m, l in itertools.product(SHORT_LBS, MID_LBS, LONG_LBS):
        if s < m < l:
            combos.append((s, m, l))
    return combos


def download_data():
    """Download all daily data from Yahoo Finance."""
    import yfinance as yf
    data = {}
    for ticker in ALL_TICKERS:
        try:
            df = yf.download(ticker, start="2014-06-01", end="2026-01-01", progress=False)
            if len(df) > 100:
                df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
                df.columns = ["open", "high", "low", "close", "volume"]
                df.index.name = "date"
                data[ticker] = df
        except Exception as e:
            print(f"  WARNING: {ticker} failed: {e}")
    return data


def run_backtest(df, lookbacks, weights, capital=10000.0):
    """Fast vectorized Donchian MTF backtest on daily data."""
    n = len(df)
    lb_s, lb_m, lb_l = lookbacks
    max_lb = max(lookbacks)

    if n < max_lb + 20:
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
    tr = np.maximum(highs[1:] - lows[1:],
                    np.maximum(np.abs(highs[1:] - closes[:-1]),
                               np.abs(lows[1:] - closes[:-1])))
    tr = np.insert(tr, 0, highs[0] - lows[0])
    atr = np.full(n, np.nan)
    atr[atr_period] = np.mean(tr[:atr_period])
    for i in range(atr_period + 1, n):
        atr[i] = atr[i - 1] * (atr_period - 1) / atr_period + tr[i] / atr_period

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
    start_bar = max_lb + atr_period + 1

    for i in range(start_bar, n):
        open_px = opens[i]
        close_px = closes[i]

        if abs(prev_target - position_usd) > max(10.0, abs(prev_target) * 0.03):
            delta = abs(prev_target - position_usd)
            fee = delta * FEE_RATE
            if abs(position_usd) > 0.01 and entry_px > 0:
                if position_usd > 0:
                    pnl = abs(position_usd) * (open_px - entry_px) / entry_px
                else:
                    pnl = abs(position_usd) * (entry_px - open_px) / entry_px
                cash += pnl
                if pnl > 0:
                    wins += 1
                closed_trades += 1
            cash -= fee
            n_trades += 1
            position_usd = prev_target
            entry_px = open_px if abs(position_usd) > 0.01 else 0.0

        unrealized = 0.0
        if abs(position_usd) > 0.01 and entry_px > 0:
            if position_usd > 0:
                unrealized = position_usd * (close_px - entry_px) / entry_px
            else:
                unrealized = abs(position_usd) * (entry_px - close_px) / entry_px
        equity = cash + unrealized
        peak_equity = max(peak_equity, equity)
        equities[i] = equity

        cur_close = closes[i]

        def tf_dir(upper, lower, idx):
            if np.isnan(upper[idx]) or np.isnan(lower[idx]):
                return 0.0
            if cur_close > upper[idx]:
                return 1.0
            elif cur_close < lower[idx]:
                return -1.0
            return 0.0

        dir_s = tf_dir(upper_s, lower_s, i)
        dir_m = tf_dir(upper_m, lower_m, i)
        dir_l = tf_dir(upper_l, lower_l, i)
        agreement = dir_s * wt_s + dir_m * wt_m + dir_l * wt_l

        if abs(agreement) < 0.05:
            prev_target = 0.0
            continue

        if not np.isnan(atr[i]) and atr[i] > 0 and close_px > 0:
            ann_vol = (atr[i] / close_px) * np.sqrt(PPY)
            vol_scalar = 0.15 / ann_vol if ann_vol > 0 else 1.0
            vol_scalar = max(0.5, min(2.0, vol_scalar))
        else:
            vol_scalar = 1.0

        dd = max(0, 1.0 - equity / peak_equity)
        dd_scalar = 1.0
        if dd > 0:
            dd_frac = min(dd / 0.30, 1.0)
            dd_scalar = 1.0 - dd_frac * 0.75

        direction = 1.0 if agreement > 0 else -1.0
        base_pos = equity * 3.0 * abs(agreement)
        target = direction * base_pos * vol_scalar * dd_scalar
        max_pos = equity * 3.0
        prev_target = max(-max_pos, min(max_pos, target))

    eq_series = pd.Series(equities[start_bar:])
    if len(eq_series) < 10:
        return None

    sr = sharpe_ratio(eq_series, PPY)
    dd_usd, dd_pct = max_drawdown(eq_series)
    final = float(eq_series.iloc[-1])
    ret_pct = (final - capital) / capital * 100.0
    win_rate = wins / closed_trades * 100 if closed_trades > 0 else 0

    return {
        "sharpe": sr, "return_pct": ret_pct, "max_dd_pct": dd_pct,
        "n_trades": n_trades, "win_rate": win_rate, "final_equity": final,
    }


def main():
    out_dir = Path("sweep_results")
    out_dir.mkdir(exist_ok=True)

    # Download data
    print("Downloading Yahoo Finance data...")
    data = download_data()
    print(f"  Downloaded {len(data)}/{len(ALL_TICKERS)} tickers")

    combos = generate_combos()
    all_params = []
    for combo in combos:
        for wt_name, wts in WEIGHT_SETS.items():
            all_params.append({"combo": combo, "weight_name": wt_name, "weights": wts})
    print(f"  Parameter combinations: {len(all_params)}")
    print(f"  Walk-forward windows: {len(WINDOWS)}")
    est = len(all_params) * len(data) * len(WINDOWS) * 2
    print(f"  Estimated backtests (upper bound): {est:,}")

    # Per-asset sweep
    asset_results = {}  # ticker -> best param + per-window results

    for ti, ticker in enumerate(data.keys()):
        t0 = time.time()
        full_df = data[ticker]

        # Run all windows
        param_window_results = {}  # param_label -> {w1_is, w1_val, ...}

        for wi, window in enumerate(WINDOWS):
            is_end = pd.Timestamp(window["is_end"])
            val_start = pd.Timestamp(window["val_start"])
            val_end = pd.Timestamp(window["val_end"])

            is_df = full_df[full_df.index < is_end].copy()
            val_df = full_df[(full_df.index >= val_start) & (full_df.index < val_end)].copy()

            # IS phase
            is_survivors = []
            for param in all_params:
                label = f"{param['combo']}_{param['weight_name']}"
                m = run_backtest(is_df, param["combo"], param["weights"])
                if m and m["sharpe"] > 0:
                    is_survivors.append((param, label))
                    if label not in param_window_results:
                        param_window_results[label] = {"param": param, "windows": {}}
                    param_window_results[label]["windows"][f"{window['name']}_is"] = m["sharpe"]

            # Val phase
            for param, label in is_survivors:
                m = run_backtest(val_df, param["combo"], param["weights"])
                if m and label in param_window_results:
                    param_window_results[label]["windows"][f"{window['name']}_val"] = m["sharpe"]
                    param_window_results[label]["windows"][f"{window['name']}_val_ret"] = m["return_pct"]
                    param_window_results[label]["windows"][f"{window['name']}_val_dd"] = m["max_dd_pct"]
                    param_window_results[label]["windows"][f"{window['name']}_val_trades"] = m["n_trades"]

        # Select best parameter for this ticker
        best_label = None
        best_score = (-999, 999, -999)  # (n_positive_windows, -std, avg_sharpe)

        for label, data_entry in param_window_results.items():
            val_sharpes = []
            for w in WINDOWS:
                vs = data_entry["windows"].get(f"{w['name']}_val")
                if vs is not None:
                    val_sharpes.append(vs)

            if len(val_sharpes) < 3:
                continue

            n_pos = sum(1 for s in val_sharpes if s > 0)
            avg = np.mean(val_sharpes)
            std = np.std(val_sharpes)
            score = (n_pos, -std, avg)

            if score > best_score:
                best_score = score
                best_label = label

        if best_label:
            entry = param_window_results[best_label]
            val_sharpes = [entry["windows"].get(f"{w['name']}_val", 0) for w in WINDOWS]
            val_rets = [entry["windows"].get(f"{w['name']}_val_ret", 0) for w in WINDOWS]

            asset_results[ticker] = {
                "category": TICKER_CAT.get(ticker, "?"),
                "param": entry["param"],
                "val_sharpes": val_sharpes,
                "avg_val_sharpe": np.mean(val_sharpes),
                "std_val_sharpe": np.std(val_sharpes),
                "n_positive": sum(1 for s in val_sharpes if s > 0),
                "avg_val_return": np.mean(val_rets),
            }

        elapsed = time.time() - t0
        status = f"Sharpe={asset_results[ticker]['avg_val_sharpe']:.3f}" if ticker in asset_results else "NO PARAM"
        print(f"  [{ti+1}/{len(data)}] {ticker:<12s} {TICKER_CAT.get(ticker,''):<12s} {elapsed:.1f}s  {status}")

    # ── Results Summary ──
    print(f"\n{'='*80}")
    print(f"  CROSS-ASSET DONCHIAN SWEEP RESULTS")
    print(f"{'='*80}")
    print(f"  {'Ticker':<12s} {'Category':<12s} {'Param':<20s} {'AvgSharpe':>10s} {'StdSharpe':>10s} {'Pos/5':>6s}")
    print(f"  {'-'*75}")

    for ticker in sorted(asset_results.keys(), key=lambda t: -asset_results[t]["avg_val_sharpe"]):
        r = asset_results[ticker]
        combo = r["param"]["combo"]
        wt = r["param"]["weight_name"]
        param_str = f"{combo[0]}/{combo[1]}/{combo[2]} {wt[:3]}"
        print(f"  {ticker:<12s} {r['category']:<12s} {param_str:<20s} {r['avg_val_sharpe']:>10.3f} {r['std_val_sharpe']:>10.3f} {r['n_positive']:>4d}/5")

    # ── Holdout ──
    print(f"\n{'='*80}")
    print(f"  HOLDOUT VALIDATION (2023-01 ~ 2025-12)")
    print(f"{'='*80}")

    ho_start = pd.Timestamp(HOLDOUT["start"])
    ho_end = pd.Timestamp(HOLDOUT["end"])

    holdout_results = {}
    for ticker, r in asset_results.items():
        if r["avg_val_sharpe"] < -0.5:
            continue
        full_df = data[ticker]
        ho_df = full_df[(full_df.index >= ho_start) & (full_df.index < ho_end)].copy()
        if len(ho_df) < 100:
            continue
        m = run_backtest(ho_df, r["param"]["combo"], r["param"]["weights"])
        if m:
            holdout_results[ticker] = m
            holdout_results[ticker]["category"] = r["category"]
            holdout_results[ticker]["val_avg_sharpe"] = r["avg_val_sharpe"]
            print(f"  {ticker:<12s} {r['category']:<12s} Sharpe={m['sharpe']:>7.3f}  Ret={m['return_pct']:>+8.2f}%  DD={m['max_dd_pct']:>6.2f}%  Trades={m['n_trades']}")

    # Portfolio comparison
    if holdout_results:
        all_sharpes = [m["sharpe"] for m in holdout_results.values()]
        all_rets = [m["return_pct"] for m in holdout_results.values()]
        avg_sharpe = np.mean(all_sharpes)
        avg_ret = np.mean(all_rets)
        worst_dd = max(m["max_dd_pct"] for m in holdout_results.values())

        print(f"\n  Portfolio ({len(holdout_results)} assets):")
        print(f"    Avg Sharpe: {avg_sharpe:.3f}")
        print(f"    Avg Return: {avg_ret:+.2f}%")
        print(f"    Worst MaxDD: {worst_dd:.2f}%")

    # Correlation matrix
    print(f"\n{'='*80}")
    print(f"  CORRELATION MATRIX (Holdout daily returns)")
    print(f"{'='*80}")

    ho_returns = {}
    for ticker in holdout_results:
        full_df = data[ticker]
        ho_df = full_df[(full_df.index >= ho_start) & (full_df.index < ho_end)].copy()
        ho_returns[ticker] = ho_df["close"].pct_change().dropna()

    if len(ho_returns) > 1:
        ret_df = pd.DataFrame(ho_returns)
        corr = ret_df.corr()

        # Print average correlation by category pair
        cats = list(ASSETS.keys())
        print(f"\n  Average pairwise correlation by category:")
        for c1 in cats:
            for c2 in cats:
                t1 = [t for t in holdout_results if TICKER_CAT.get(t) == c1]
                t2 = [t for t in holdout_results if TICKER_CAT.get(t) == c2]
                if t1 and t2:
                    pairs = [(a, b) for a in t1 for b in t2 if a != b and a in corr.columns and b in corr.columns]
                    if pairs:
                        avg_corr = np.mean([corr.loc[a, b] for a, b in pairs])
                        print(f"    {c1:<12s} vs {c2:<12s}: {avg_corr:+.3f}")

        # Crypto vs Traditional (reference)
        print(f"\n  Note: Crypto correlation data from separate experiment")
        print(f"  Key question: Is cross-asset correlation significantly lower than intra-crypto?")

    # Save results
    save_data = {
        "asset_results": {t: {**r, "param": {"combo": r["param"]["combo"], "weight_name": r["param"]["weight_name"]}} for t, r in asset_results.items()},
        "holdout_results": holdout_results,
        "n_params": len(all_params),
        "n_windows": len(WINDOWS),
    }
    json_path = out_dir / "cross_asset_sweep.json"
    json_path.write_text(json.dumps(save_data, indent=2, default=str))
    print(f"\n  Results saved to {json_path}")


if __name__ == "__main__":
    main()
