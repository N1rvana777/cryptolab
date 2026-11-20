#!/usr/bin/env python3
"""DonchianMTF full parameter optimization: frequency x lookback x weight.

Walk-Forward validation with 3 windows + holdout.
Outputs heatmap data, per-coin analysis, and parameter sensitivity.

Usage:
    # Step 0: Screen coins (outputs list for user confirmation)
    python scripts/donchian_full_sweep.py --screen-coins

    # Step 1-3: Run full sweep (after coin confirmation)
    python scripts/donchian_full_sweep.py --run-sweep --coins BTC,ETH,SOL,...

    # Step 4: Holdout (only after sweep is finalized)
    python scripts/donchian_full_sweep.py --holdout --coins BTC,ETH,SOL,... --freq 4h --lookbacks 24,72,168 --weights equal
"""

import argparse
import itertools
import json
import logging
import os
import sys
import time
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptolab.config import Config
from cryptolab.data.manager import DataManager
from cryptolab.strategy.donchian_mtf import DonchianMTF
from cryptolab.backtest.engine import BacktestEngine
from cryptolab.backtest.metrics import sharpe_ratio, max_drawdown, PERIODS_PER_YEAR

logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")

# ── Time boundaries (ms) ──
TS = {
    "2021-01": 1609459200000,
    "2022-07": 1656633600000,
    "2023-07": 1688169600000,
    "2024-07": 1719792000000,
    "2025-07": 1751328000000,
    "2026-04": 1775088000000,
}

WINDOWS = [
    {"name": "W1", "is_start": "2021-01", "is_end": "2022-07", "val_start": "2022-07", "val_end": "2023-07"},
    {"name": "W2", "is_start": "2021-01", "is_end": "2023-07", "val_start": "2023-07", "val_end": "2024-07"},
    {"name": "W3", "is_start": "2021-01", "is_end": "2024-07", "val_start": "2024-07", "val_end": "2025-07"},
]
HOLDOUT = {"start": "2025-07", "end": "2026-04"}

# ── Frequency-adapted lookback ranges (in days) ──
FREQ_LOOKBACKS = {
    "1h":  {"short": [1, 2, 3, 4, 6],   "mid": [4, 6, 8, 12, 16],    "long": [12, 16, 20, 28, 42]},
    "2h":  {"short": [2, 3, 4, 6, 8],   "mid": [6, 8, 12, 16, 20],   "long": [16, 20, 28, 42, 56]},
    "4h":  {"short": [2, 3, 4, 6, 8],   "mid": [8, 12, 16, 20, 28],  "long": [28, 42, 56, 72, 84]},
    "8h":  {"short": [3, 4, 6, 8, 12],  "mid": [12, 16, 20, 28, 42], "long": [42, 56, 72, 84, 112]},
    "1d":  {"short": [4, 6, 8, 12, 16], "mid": [16, 20, 28, 42, 56], "long": [56, 72, 84, 112, 140]},
}

WEIGHT_SETS = {
    "equal":     [0.33, 0.34, 0.33],
    "med-heavy": [0.25, 0.50, 0.25],
}

# Fee model: taker 5bps + slippage 3bps = 8bps per side
TAKER_FEE_BPS = 5.0
SLIPPAGE_BPS = 3.0

FREQUENCIES = ["1h", "2h", "4h", "8h", "1d"]


def days_to_bars(days: int, freq: str) -> int:
    """Convert day count to bar count for a given frequency."""
    bars_per_day = {"1h": 24, "2h": 12, "4h": 6, "8h": 3, "1d": 1}
    return days * bars_per_day[freq]


def resample_ohlcv(df_1h: pd.DataFrame, target: str) -> pd.DataFrame:
    """Resample 1H OHLCV to 2H/4H/8H/1D."""
    df = df_1h.copy()
    df = df.set_index("timestamp").sort_index()

    rule_map = {"2h": "2h", "4h": "4h", "8h": "8h", "1d": "1D"}
    rule = rule_map.get(target)
    if not rule:
        return df_1h

    resampled = df.resample(rule, closed="left", label="left").agg({
        "open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"
    }).dropna(subset=["open"])

    resampled = resampled.reset_index()
    return resampled


def generate_combos(freq: str):
    """Generate all valid (short, mid, long) day combos for a frequency."""
    ranges = FREQ_LOOKBACKS[freq]
    combos = []
    for s, m, l in itertools.product(ranges["short"], ranges["mid"], ranges["long"]):
        if s < m < l:  # strict ordering
            combos.append((s, m, l))
    return combos


def run_single_backtest(symbol, df, lookbacks_bars, weights, cfg):
    """Fast vectorized DonchianMTF backtest — no BacktestEngine overhead.

    Pre-computes Donchian channels and ATR once, then loops through bars.
    ~100x faster than BacktestEngine for large datasets.
    """
    n = len(df)
    lb_short, lb_mid, lb_long = lookbacks_bars
    max_lb = max(lookbacks_bars)

    if n < max_lb + 20:
        return None

    # Pre-compute arrays
    highs = df["high"].values
    lows = df["low"].values
    closes = df["close"].values
    opens = df["open"].values

    # Pre-compute Donchian channels vectorized (shifted: excludes current bar)
    h_series = pd.Series(highs)
    l_series = pd.Series(lows)

    upper_s = h_series.rolling(lb_short).max().shift(1).values
    lower_s = l_series.rolling(lb_short).min().shift(1).values
    upper_m = h_series.rolling(lb_mid).max().shift(1).values
    lower_m = l_series.rolling(lb_mid).min().shift(1).values
    upper_l = h_series.rolling(lb_long).max().shift(1).values
    lower_l = l_series.rolling(lb_long).min().shift(1).values

    # Pre-compute ATR (14-period, shifted)
    atr_period = 14
    tr = np.maximum(highs[1:] - lows[1:],
                    np.maximum(np.abs(highs[1:] - closes[:-1]),
                               np.abs(lows[1:] - closes[:-1])))
    tr = np.insert(tr, 0, highs[0] - lows[0])
    atr = np.full(n, np.nan)
    atr[atr_period] = np.mean(tr[:atr_period])
    for i in range(atr_period + 1, n):
        atr[i] = atr[i - 1] * (atr_period - 1) / atr_period + tr[i] / atr_period

    # Simulation
    equity = cfg.initial_capital
    cash = equity
    position_usd = 0.0
    entry_px = 0.0
    peak_equity = equity
    fee_rate = (cfg.taker_fee_bps + cfg.slippage_bps) / 10_000  # combined per side
    vol_target = 0.15
    dd_max = 0.30
    dd_floor = 0.25
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

        # Execute previous signal at this bar's open
        if abs(prev_target - position_usd) > max(10.0, abs(prev_target) * 0.03):
            delta = abs(prev_target - position_usd)
            fee = delta * fee_rate

            # Realize PnL on existing position
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

        # MTM equity
        unrealized = 0.0
        if abs(position_usd) > 0.01 and entry_px > 0:
            if position_usd > 0:
                unrealized = position_usd * (close_px - entry_px) / entry_px
            else:
                unrealized = abs(position_usd) * (entry_px - close_px) / entry_px
        equity = cash + unrealized
        peak_equity = max(peak_equity, equity)
        equities[i] = equity

        # Compute agreement signal: current close vs channel (excluding current bar's high/low)
        cur_close = closes[i]

        # Per-TF direction: close breaks above upper → long, below lower → short
        def tf_direction(upper, lower, idx):
            if np.isnan(upper[idx]) or np.isnan(lower[idx]):
                return 0.0
            if cur_close > upper[idx]:
                return 1.0
            elif cur_close < lower[idx]:
                return -1.0
            return 0.0

        dir_s = tf_direction(upper_s, lower_s, i)
        dir_m = tf_direction(upper_m, lower_m, i)
        dir_l = tf_direction(upper_l, lower_l, i)

        agreement = dir_s * wt_s + dir_m * wt_m + dir_l * wt_l

        # Deadzone
        if abs(agreement) < 0.05:
            prev_target = 0.0
            continue

        # Vol scalar
        if not np.isnan(atr[i]) and atr[i] > 0 and close_px > 0:
            ann_vol = (atr[i] / close_px) * np.sqrt(365 * 24 / 4)  # annualize
            vol_scalar = vol_target / ann_vol if ann_vol > 0 else 1.0
            vol_scalar = max(0.5, min(2.0, vol_scalar))
        else:
            vol_scalar = 1.0

        # DD scalar
        dd = max(0, 1.0 - equity / peak_equity)
        dd_scalar = 1.0
        if dd > 0:
            dd_frac = min(dd / dd_max, 1.0)
            dd_scalar = 1.0 - dd_frac * (1.0 - dd_floor)

        direction = 1.0 if agreement > 0 else -1.0
        base_pos = equity * cfg.leverage * abs(agreement)
        target = direction * base_pos * vol_scalar * dd_scalar
        max_pos = equity * cfg.leverage
        prev_target = max(-max_pos, min(max_pos, target))

    # Metrics
    eq_series = pd.Series(equities[start_bar:])
    if len(eq_series) < 10:
        return None

    ppy = PERIODS_PER_YEAR.get(cfg.interval, 2190)
    sr = sharpe_ratio(eq_series, ppy)
    dd_usd, dd_pct = max_drawdown(eq_series)
    final = float(eq_series.iloc[-1])
    initial = cfg.initial_capital
    ret_pct = (final - initial) / initial * 100.0
    win_rate = wins / closed_trades * 100 if closed_trades > 0 else 0

    return {
        "sharpe": sr,
        "return_pct": ret_pct,
        "max_dd_pct": dd_pct,
        "n_trades": n_trades,
        "win_rate": win_rate,
        "final_equity": final,
    }


def screen_coins():
    """Screen coins: OKX data from 2021, exclude stables, compute vol."""
    dm = DataManager()
    start_ms = TS["2021-01"]
    end_ms = int(pd.Timestamp.now("UTC").timestamp() * 1000)

    from cryptolab.data.types import OKX_SYMBOL_MAP
    all_symbols = sorted(OKX_SYMBOL_MAP.keys())

    # Exclusion lists
    stablecoins = {"USDT", "USDC", "DAI", "TUSD", "FDUSD", "PYUSD", "BUSD", "UST", "FRAX"}
    wrapped = {"WBTC", "WETH", "WBNB", "STETH", "CBETH", "RETH"}
    leverage_tokens = {s for s in all_symbols if any(x in s for x in ["UP", "DOWN", "BULL", "BEAR", "2L", "2S", "3L", "3S"])}
    exclude = stablecoins | wrapped | leverage_tokens

    results = []
    for sym in all_symbols:
        if sym in exclude:
            print(f"  {sym}: EXCLUDED (stablecoin/wrapped/leverage)")
            continue

        try:
            cached = dm.cache.read("okx", sym, "1h")
            if cached.empty:
                # Try to seed
                print(f"  {sym}: no cache, attempting seed...", end=" ", flush=True)
                dm.seed(sym, "1h", start_ms, end_ms, source="okx")
                cached = dm.cache.read("okx", sym, "1h")
                if cached.empty:
                    print("FAILED")
                    continue
                print(f"OK ({len(cached)} bars)")

            min_ts = cached["timestamp"].min()
            max_ts = cached["timestamp"].max()
            n_bars = len(cached)

            # Must have data from 2021
            if min_ts > pd.Timestamp("2021-06-01", tz="UTC"):
                print(f"  {sym}: data starts {str(min_ts)[:10]}, too late")
                continue

            # Must cover through 2026
            if max_ts < pd.Timestamp("2025-07-01", tz="UTC"):
                print(f"  {sym}: data ends {str(max_ts)[:10]}, too early")
                continue

            # Compute daily volatility
            daily = cached.set_index("timestamp")["close"].resample("1D").last().dropna()
            daily_ret = daily.pct_change().dropna()
            ann_vol = float(daily_ret.std() * np.sqrt(365) * 100)
            avg_daily_vol = float(cached["volume"].mean() * cached["close"].mean())

            if ann_vol < 1.0:
                print(f"  {sym}: vol={ann_vol:.1f}% too low")
                continue

            results.append({
                "symbol": sym,
                "start": str(min_ts)[:10],
                "end": str(max_ts)[:10],
                "bars": n_bars,
                "ann_vol_pct": round(ann_vol, 1),
                "avg_daily_notional": round(avg_daily_vol, 0),
            })
            print(f"  {sym}: OK  vol={ann_vol:.1f}%  bars={n_bars}")

        except Exception as e:
            print(f"  {sym}: ERROR - {e}")

    # Sort by volume
    results.sort(key=lambda x: -x["avg_daily_notional"])

    print(f"\n{'='*70}")
    print(f"  SCREENED COINS ({len(results)} passed)")
    print(f"{'='*70}")
    print(f"  {'#':<4s} {'Symbol':<8s} {'Start':<12s} {'End':<12s} {'Bars':>8s} {'AnnVol%':>8s}")
    print(f"  {'-'*60}")
    for i, r in enumerate(results, 1):
        print(f"  {i:<4d} {r['symbol']:<8s} {r['start']:<12s} {r['end']:<12s} {r['bars']:>8d} {r['ann_vol_pct']:>8.1f}")

    return results


def run_sweep(coins, output_dir="sweep_results"):
    """Run the full frequency x lookback x weight sweep with walk-forward validation."""
    dm = DataManager()
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    cfg_base = Config()
    cfg_base.slippage_bps = SLIPPAGE_BPS
    cfg_base.taker_fee_bps = TAKER_FEE_BPS
    cfg_base.leverage = 3.0
    per_coin_capital = 10000.0 / len(coins)

    # Pre-load all 1H data
    print("Loading 1H data for all coins...")
    raw_1h = {}
    for sym in coins:
        df = dm.cache.read("okx", sym, "1h")
        if df.empty:
            print(f"  WARNING: no data for {sym}")
            continue
        raw_1h[sym] = df
    print(f"  Loaded {len(raw_1h)} coins")

    # Generate all parameter combinations
    all_params = []
    for freq in FREQUENCIES:
        combos = generate_combos(freq)
        for days_combo in combos:
            for wt_name, wts in WEIGHT_SETS.items():
                bars = tuple(days_to_bars(d, freq) for d in days_combo)
                all_params.append({
                    "freq": freq,
                    "days": days_combo,
                    "bars": bars,
                    "weight_name": wt_name,
                    "weights": wts,
                    "label": f"{freq}_{days_combo[0]}d_{days_combo[1]}d_{days_combo[2]}d_{wt_name}",
                })

    print(f"\nTotal parameter combinations: {len(all_params)}")
    print(f"Coins: {len(raw_1h)}")
    print(f"Walk-forward windows: {len(WINDOWS)}")
    est_backtests = len(all_params) * len(raw_1h) * len(WINDOWS) * 2  # IS + Val
    print(f"Estimated total backtests (upper bound): {est_backtests:,}")

    # ── Run sweep per window ──
    results_by_param = {}  # param_label -> {w1_is_sharpe, w1_val_sharpe, ...}

    for wi, window in enumerate(WINDOWS):
        wname = window["name"]
        is_start = pd.Timestamp(window["is_start"].replace("-", "-01-") if len(window["is_start"]) == 7 else window["is_start"], tz="UTC")
        is_end = pd.Timestamp(window["is_end"].replace("-", "-01-") if len(window["is_end"]) == 7 else window["is_end"], tz="UTC")
        val_start = pd.Timestamp(window["val_start"].replace("-", "-01-") if len(window["val_start"]) == 7 else window["val_start"], tz="UTC")
        val_end = pd.Timestamp(window["val_end"].replace("-", "-01-") if len(window["val_end"]) == 7 else window["val_end"], tz="UTC")

        is_start_ms = int(is_start.timestamp() * 1000)
        is_end_ms = int(is_end.timestamp() * 1000)
        val_start_ms = int(val_start.timestamp() * 1000)
        val_end_ms = int(val_end.timestamp() * 1000)

        print(f"\n{'='*70}")
        print(f"  Window {wname}: IS={window['is_start']}~{window['is_end']}, "
              f"Val={window['val_start']}~{window['val_end']}")
        print(f"{'='*70}")

        # Pre-resample data for each frequency
        freq_data = {}
        for freq in FREQUENCIES:
            freq_data[freq] = {}
            for sym, df_1h in raw_1h.items():
                if freq == "1h":
                    freq_data[freq][sym] = df_1h
                else:
                    freq_data[freq][sym] = resample_ohlcv(df_1h, freq)

        # IS phase
        t0 = time.time()
        is_survivors = []
        n_total = len(all_params)

        for pi, param in enumerate(all_params):
            freq = param["freq"]
            bars = param["bars"]
            label = param["label"]

            if pi % 10 == 0:
                elapsed = time.time() - t0
                print(f"  {wname} IS: {pi}/{n_total} ({elapsed:.0f}s)...", flush=True)

            # Run on all coins, compute equal-weight portfolio Sharpe
            coin_sharpes = []
            coin_metrics = {}
            cfg_run = replace(cfg_base, interval=freq, initial_capital=per_coin_capital)

            for sym in raw_1h:
                full_df = freq_data[freq].get(sym)
                if full_df is None or full_df.empty:
                    continue

                # Filter to IS period
                mask = (full_df["timestamp"] >= is_start) & (full_df["timestamp"] < is_end)
                is_df = full_df[mask].reset_index(drop=True)

                if len(is_df) < max(bars) + 50:
                    continue

                m = run_single_backtest(sym, is_df, bars, param["weights"], cfg_run)
                if m is not None:
                    coin_sharpes.append(m["sharpe"])
                    coin_metrics[sym] = m

            if not coin_sharpes:
                continue

            avg_is_sharpe = np.mean(coin_sharpes)

            if label not in results_by_param:
                results_by_param[label] = {"param": param, "windows": {}}
            results_by_param[label]["windows"][f"{wname}_is_sharpe"] = avg_is_sharpe
            results_by_param[label]["windows"][f"{wname}_is_per_coin"] = coin_metrics

            # IS filter: avg Sharpe must be positive
            if avg_is_sharpe > 0:
                is_survivors.append(param)

        print(f"  {wname} IS done: {len(is_survivors)}/{n_total} survived (Sharpe>0), {time.time()-t0:.0f}s")

        # Validation phase
        t0 = time.time()
        for pi, param in enumerate(is_survivors):
            freq = param["freq"]
            bars = param["bars"]
            label = param["label"]

            coin_sharpes = []
            coin_metrics = {}
            cfg_run = replace(cfg_base, interval=freq, initial_capital=per_coin_capital)

            for sym in raw_1h:
                full_df = freq_data[freq].get(sym)
                if full_df is None or full_df.empty:
                    continue

                mask = (full_df["timestamp"] >= val_start) & (full_df["timestamp"] < val_end)
                val_df = full_df[mask].reset_index(drop=True)

                if len(val_df) < max(bars) + 50:
                    continue

                m = run_single_backtest(sym, val_df, bars, param["weights"], cfg_run)
                if m is not None:
                    coin_sharpes.append(m["sharpe"])
                    coin_metrics[sym] = m

            if coin_sharpes:
                avg_val_sharpe = np.mean(coin_sharpes)
                results_by_param[label]["windows"][f"{wname}_val_sharpe"] = avg_val_sharpe
                results_by_param[label]["windows"][f"{wname}_val_per_coin"] = coin_metrics

        print(f"  {wname} Val done: {len(is_survivors)} params, {time.time()-t0:.0f}s")

    # ── Aggregate across windows ──
    print(f"\n{'='*70}")
    print(f"  AGGREGATING RESULTS")
    print(f"{'='*70}")

    final_results = []
    for label, data in results_by_param.items():
        w = data["windows"]
        val_sharpes = []
        for wn in ["W1", "W2", "W3"]:
            vs = w.get(f"{wn}_val_sharpe")
            if vs is not None:
                val_sharpes.append(vs)

        if len(val_sharpes) < 3:
            continue

        all_positive = all(s > 0 for s in val_sharpes)
        avg_val = np.mean(val_sharpes)
        std_val = np.std(val_sharpes)

        # Per-coin analysis: how many coins positive across windows?
        coin_avg_sharpes = {}
        for sym in raw_1h:
            sym_sharpes = []
            for wn in ["W1", "W2", "W3"]:
                per_coin = w.get(f"{wn}_val_per_coin", {})
                if sym in per_coin:
                    sym_sharpes.append(per_coin[sym]["sharpe"])
            if sym_sharpes:
                coin_avg_sharpes[sym] = np.mean(sym_sharpes)

        final_results.append({
            "label": label,
            "param": data["param"],
            "val_sharpes": val_sharpes,
            "avg_val_sharpe": avg_val,
            "std_val_sharpe": std_val,
            "all_positive": all_positive,
            "coin_avg_sharpes": coin_avg_sharpes,
            "windows": w,
        })

    # Sort: all-positive first, then by stability (low std), then by avg sharpe
    final_results.sort(key=lambda x: (-x["all_positive"], x["std_val_sharpe"], -x["avg_val_sharpe"]))

    # ── Output results ──
    print(f"\n  Total params with 3-window validation: {len(final_results)}")
    all_pos = [r for r in final_results if r["all_positive"]]
    print(f"  All 3 windows positive: {len(all_pos)}")

    # Top 30 by selection criteria
    print(f"\n  {'='*90}")
    print(f"  TOP 30 PARAMETERS (sorted by stability then avg Sharpe)")
    print(f"  {'='*90}")
    print(f"  {'#':>3s} {'Freq':>4s} {'Short':>5s} {'Mid':>5s} {'Long':>5s} {'Wt':>9s} "
          f"{'W1 Val':>7s} {'W2 Val':>7s} {'W3 Val':>7s} {'Avg':>7s} {'Std':>6s} {'All+':>5s}")
    print(f"  {'-'*88}")

    for i, r in enumerate(final_results[:30], 1):
        p = r["param"]
        vs = r["val_sharpes"]
        print(f"  {i:>3d} {p['freq']:>4s} {p['days'][0]:>5d} {p['days'][1]:>5d} {p['days'][2]:>5d} "
              f"{p['weight_name']:>9s} {vs[0]:>7.3f} {vs[1]:>7.3f} {vs[2]:>7.3f} "
              f"{r['avg_val_sharpe']:>7.3f} {r['std_val_sharpe']:>6.3f} "
              f"{'YES' if r['all_positive'] else 'no':>5s}")

    # Best parameter detail
    if final_results:
        best = final_results[0]
        print(f"\n  {'='*70}")
        print(f"  BEST PARAMETER: {best['label']}")
        print(f"  {'='*70}")
        print(f"  Freq: {best['param']['freq']}")
        print(f"  Lookback (days): {best['param']['days']}")
        print(f"  Lookback (bars): {best['param']['bars']}")
        print(f"  Weights: {best['param']['weight_name']} {best['param']['weights']}")
        print(f"  Val Sharpes: W1={best['val_sharpes'][0]:.3f}, W2={best['val_sharpes'][1]:.3f}, W3={best['val_sharpes'][2]:.3f}")
        print(f"  Avg Val Sharpe: {best['avg_val_sharpe']:.3f}")
        print(f"  Std Val Sharpe: {best['std_val_sharpe']:.3f}")

        # Per-coin breakdown (sorted by vol)
        print(f"\n  Per-coin avg Validation Sharpe (sorted by Sharpe):")
        coin_list = sorted(best["coin_avg_sharpes"].items(), key=lambda x: -x[1])
        extreme_neg = []
        for sym, sr in coin_list:
            flag = " ** EXCLUDE (< -2)" if sr < -2 else ""
            print(f"    {sym:<8s} {sr:>7.3f}{flag}")
            if sr < -2:
                extreme_neg.append(sym)

        if extreme_neg:
            print(f"\n  Coins to exclude (Sharpe < -2): {extreme_neg}")
        else:
            print(f"\n  No coins excluded (all Sharpe > -2)")

        # Parameter sensitivity
        print(f"\n  Parameter Sensitivity (best param +/- 1 step):")
        bp = best["param"]
        freq = bp["freq"]
        ranges = FREQ_LOOKBACKS[freq]
        for dim, dim_vals, dim_idx in [("short", ranges["short"], 0), ("mid", ranges["mid"], 1), ("long", ranges["long"], 2)]:
            current = bp["days"][dim_idx]
            idx = dim_vals.index(current) if current in dim_vals else -1
            neighbors = []
            for di in [-1, 0, 1]:
                ni = idx + di
                if 0 <= ni < len(dim_vals):
                    neighbor_days = list(bp["days"])
                    neighbor_days[dim_idx] = dim_vals[ni]
                    if neighbor_days[0] < neighbor_days[1] < neighbor_days[2]:  # valid combo
                        nlabel = f"{freq}_{neighbor_days[0]}d_{neighbor_days[1]}d_{neighbor_days[2]}d_{bp['weight_name']}"
                        for r in final_results:
                            if r["label"] == nlabel:
                                neighbors.append((dim_vals[ni], r["avg_val_sharpe"]))
                                break
            if neighbors:
                vals_str = ", ".join(f"{d}d={s:.3f}" for d, s in neighbors)
                print(f"    {dim}: {vals_str}")

    # Save results to JSON
    save_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "coins": list(raw_1h.keys()),
        "n_params_tested": len(all_params),
        "n_3window_valid": len(final_results),
        "n_all_positive": len(all_pos),
        "top_30": [{
            "label": r["label"],
            "freq": r["param"]["freq"],
            "days": r["param"]["days"],
            "bars": r["param"]["bars"],
            "weight_name": r["param"]["weight_name"],
            "val_sharpes": r["val_sharpes"],
            "avg_val_sharpe": r["avg_val_sharpe"],
            "std_val_sharpe": r["std_val_sharpe"],
            "all_positive": r["all_positive"],
            "coin_avg_sharpes": r["coin_avg_sharpes"],
        } for r in final_results[:30]],
    }
    json_path = out_dir / "sweep_results.json"
    json_path.write_text(json.dumps(save_data, indent=2, default=str))
    print(f"\n  Results saved to {json_path}")

    return final_results


def run_holdout(coins, freq, lookbacks_days, weight_name, output_dir="sweep_results"):
    """Run holdout validation — ONE TIME ONLY."""
    dm = DataManager()
    cfg = Config()
    cfg.interval = freq
    cfg.slippage_bps = SLIPPAGE_BPS
    cfg.taker_fee_bps = TAKER_FEE_BPS
    cfg.leverage = 3.0

    per_coin_capital = 10000.0 / len(coins)
    cfg.initial_capital = per_coin_capital

    bars = tuple(days_to_bars(d, freq) for d in lookbacks_days)
    weights = WEIGHT_SETS[weight_name]

    ho_start = pd.Timestamp("2025-07-01", tz="UTC")
    ho_end = pd.Timestamp("2026-04-01", tz="UTC")

    print(f"\n{'='*70}")
    print(f"  HOLDOUT VALIDATION (2025-07 ~ 2026-03)")
    print(f"  Freq={freq}, Lookback={lookbacks_days}, Weights={weight_name}")
    print(f"  Coins: {coins}")
    print(f"{'='*70}")

    raw_1h = {}
    for sym in coins:
        df = dm.cache.read("okx", sym, "1h")
        if not df.empty:
            raw_1h[sym] = df

    coin_metrics = {}
    for sym, df_1h in raw_1h.items():
        if freq == "1h":
            full_df = df_1h
        else:
            full_df = resample_ohlcv(df_1h, freq)

        mask = (full_df["timestamp"] >= ho_start) & (full_df["timestamp"] < ho_end)
        ho_df = full_df[mask].reset_index(drop=True)

        if len(ho_df) < max(bars) + 50:
            print(f"  {sym}: insufficient holdout data ({len(ho_df)} bars)")
            continue

        m = run_single_backtest(sym, ho_df, bars, weights, cfg)
        if m:
            coin_metrics[sym] = m
            print(f"  {sym}: Sharpe={m['sharpe']:.3f}, Return={m['return_pct']:+.2f}%, "
                  f"MaxDD={m['max_dd_pct']:.2f}%, Trades={m['n_trades']}, WinRate={m['win_rate']:.1f}%")

    if coin_metrics:
        avg_sharpe = np.mean([m["sharpe"] for m in coin_metrics.values()])
        avg_ret = np.mean([m["return_pct"] for m in coin_metrics.values()])
        worst_dd = max(m["max_dd_pct"] for m in coin_metrics.values())
        total_trades = sum(m["n_trades"] for m in coin_metrics.values())

        print(f"\n  Portfolio Summary ({len(coin_metrics)} coins):")
        print(f"    Avg Sharpe:    {avg_sharpe:.3f}")
        print(f"    Avg Return:    {avg_ret:+.2f}%")
        print(f"    Worst MaxDD:   {worst_dd:.2f}%")
        print(f"    Total Trades:  {total_trades}")

    return coin_metrics


def main():
    parser = argparse.ArgumentParser(description="DonchianMTF full parameter optimization")
    parser.add_argument("--screen-coins", action="store_true", help="Step 0: screen coins")
    parser.add_argument("--run-sweep", action="store_true", help="Steps 1-3: run full sweep")
    parser.add_argument("--holdout", action="store_true", help="Step 4: holdout validation")
    parser.add_argument("--coins", type=str, default=None, help="Comma-separated coin list")
    parser.add_argument("--freq", type=str, default="4h", help="Frequency for holdout")
    parser.add_argument("--lookbacks", type=str, default="4,12,28", help="Lookback days for holdout (comma-sep)")
    parser.add_argument("--weights", type=str, default="equal", help="Weight set for holdout")
    parser.add_argument("--output-dir", type=str, default="sweep_results")
    args = parser.parse_args()

    if args.screen_coins:
        screen_coins()
    elif args.run_sweep:
        if not args.coins:
            print("ERROR: --coins required for sweep")
            sys.exit(1)
        coins = [c.strip() for c in args.coins.split(",")]
        run_sweep(coins, args.output_dir)
    elif args.holdout:
        if not args.coins:
            print("ERROR: --coins required for holdout")
            sys.exit(1)
        coins = [c.strip() for c in args.coins.split(",")]
        lookbacks = tuple(int(d) for d in args.lookbacks.split(","))
        run_holdout(coins, args.freq, lookbacks, args.weights, args.output_dir)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
