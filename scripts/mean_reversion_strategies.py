#!/usr/bin/env python3
"""5 Mean Reversion Strategies: Pairs, Bollinger, OU, Cointegration, Funding Rate.

Walk-forward W1 (IS 2021-2022, OOS 2023) + W2 (IS 2022-2023, OOS 2024).
All strategies: zero positions at test window start, warmup only computes indicators.
"""

import sys, os, time, json, warnings
from pathlib import Path
from itertools import product, combinations
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptolab.data.cache import ParquetCache
from cryptolab.backtest.metrics import sharpe_ratio, max_drawdown
from scripts.donchian_full_sweep import resample_ohlcv
from scripts.mean_reversion_experiment import compute_dynamic_slippage
from statsmodels.tsa.stattools import coint

ALL_28 = ["BTC","ETH","LTC","TRX","BCH","DOT","ADA","LINK","XLM","XRP",
          "ETC","ALGO","ATOM","AAVE","SOL","ICP","UNI","FIL","AVAX","NEAR",
          "CRV","DOGE","AXS","YGG","CELO","GALA","SAND","PEOPLE"]

PPY = 1096
FEE_BPS = 3.5

WINDOWS = [
    {"name": "W1", "is_start": "2021-01-01", "is_end": "2023-01-01",
     "oos_start": "2023-01-01", "oos_end": "2024-01-01"},
    {"name": "W2", "is_start": "2022-01-01", "is_end": "2024-01-01",
     "oos_start": "2024-01-01", "oos_end": "2025-01-01"},
]


def load_8h(cache, coin, start, end):
    df = cache.read("okx", coin, "1h")
    if df is None or df.empty: return None
    if df["timestamp"].dt.tz is not None:
        df["timestamp"] = df["timestamp"].dt.tz_localize(None)
    df8 = resample_ohlcv(df, "8h")
    mask = (df8["timestamp"] >= pd.Timestamp(start)) & (df8["timestamp"] < pd.Timestamp(end))
    out = df8[mask].reset_index(drop=True)
    return out if len(out) > 50 else None


def backtest_pnl(positions_series, returns_series, fee_rate=FEE_BPS/10_000):
    """Simple PnL from position and return arrays. Returns equity curve."""
    n = len(positions_series)
    equity = 10000.0
    cash = equity
    pos_usd = 0.0
    equities = [equity]
    trades = 0

    for i in range(1, n):
        # MTM
        if abs(pos_usd) > 0.01:
            pnl = pos_usd * returns_series[i]
            cash += pnl

        # Rebalance to target
        target = positions_series[i] * equity  # position as fraction of equity
        delta = target - pos_usd
        if abs(delta) > 5.0:
            cash -= abs(delta) * fee_rate
            trades += 1
        pos_usd = target

        equity = cash
        equities.append(equity)

    return np.array(equities), trades


# ================================================================
# Strategy 1: Pairs Trading
# ================================================================
def run_pairs(coin_dfs, spread_lb, entry_z, exit_z, trading_start,
              corr_thresh=0.80, corr_std_max=0.15, capital=10000.0):
    """Pairs trading on correlated coin pairs."""
    coins = list(coin_dfs.keys())
    n_coins = len(coins)

    # Build aligned return matrix
    all_ts = None
    for df in coin_dfs.values():
        ts = set(df["timestamp"].values)
        all_ts = ts if all_ts is None else all_ts & ts
    common_ts = sorted(all_ts)
    n_bars = len(common_ts)
    if n_bars < spread_lb + 100:
        return None, []

    prices = np.zeros((n_bars, n_coins))
    for ci, coin in enumerate(coins):
        df = coin_dfs[coin]
        ts_map = {t: i for i, t in enumerate(df["timestamp"].values)}
        for ti, t in enumerate(common_ts):
            idx = ts_map.get(t)
            if idx is not None:
                prices[ti, ci] = df.iloc[idx]["close"]

    returns = np.zeros((n_bars, n_coins))
    for i in range(1, n_bars):
        for ci in range(n_coins):
            if prices[i-1, ci] > 0:
                returns[i, ci] = prices[i, ci] / prices[i-1, ci] - 1

    # Find trading_start index
    ts_start = np.datetime64(trading_start)
    trade_idx = 0
    for i, t in enumerate(common_ts):
        if t >= ts_start:
            trade_idx = i
            break

    # Find stable pairs using IS data (before trading_start)
    corr_window = 180  # ~60 days
    stable_pairs = []

    for ci, cj in combinations(range(n_coins), 2):
        # Rolling correlation on IS data
        r_i = pd.Series(returns[:trade_idx, ci])
        r_j = pd.Series(returns[:trade_idx, cj])
        roll_corr = r_i.rolling(corr_window, min_periods=60).corr(r_j)
        valid = roll_corr.dropna()
        if len(valid) < 50:
            continue
        mean_corr = valid.mean()
        std_corr = valid.std()
        if mean_corr > corr_thresh and std_corr < corr_std_max:
            stable_pairs.append((ci, cj, mean_corr, std_corr, coins[ci], coins[cj]))

    stable_pairs.sort(key=lambda x: -x[2])
    pair_info = [(p[4], p[5], p[2], p[3]) for p in stable_pairs[:20]]

    if len(stable_pairs) == 0:
        return None, pair_info

    # Trade pairs from trading_start
    n_pairs = len(stable_pairs)
    per_pair = capital / max(n_pairs, 1)
    fee_rate = FEE_BPS / 10_000
    equity = capital
    cash = equity
    equities = np.full(n_bars, equity)
    pair_positions = {}  # (ci,cj) -> signed usd
    total_trades = 0

    for i in range(trade_idx + 1, n_bars):
        # MTM existing positions
        for (ci, cj), pos in list(pair_positions.items()):
            pnl = pos * (returns[i, ci] - returns[i, cj])
            cash += pnl

        equity = cash
        equities[i] = equity

        # Generate signals for each pair
        for ci, cj, _, _, _, _ in stable_pairs:
            # Spread = coin_i return - coin_j return (cumulative)
            spread_window = returns[max(0, i-spread_lb):i, ci] - returns[max(0, i-spread_lb):i, cj]
            if len(spread_window) < spread_lb // 2:
                continue
            spread_mean = np.mean(spread_window)
            spread_std = np.std(spread_window)
            if spread_std < 1e-10:
                continue

            current_spread = returns[i, ci] - returns[i, cj]
            z = (current_spread - spread_mean) / spread_std

            key = (ci, cj)
            current_pos = pair_positions.get(key, 0)

            if abs(current_pos) < 1 and abs(z) > entry_z:
                # Entry
                size = min(per_pair, equity * 0.15)
                if z > entry_z:
                    pair_positions[key] = -size  # short spread
                else:
                    pair_positions[key] = size  # long spread
                cash -= abs(size) * 2 * fee_rate  # entry fee for both legs
                total_trades += 1
            elif abs(current_pos) > 1 and abs(z) < exit_z:
                # Exit
                cash -= abs(current_pos) * 2 * fee_rate
                pair_positions[key] = 0
                total_trades += 1

    eq = equities[trade_idx:]
    eq = eq / eq[0] * capital
    eq_s = pd.Series(eq)
    sr = sharpe_ratio(eq_s, PPY); _, dd = max_drawdown(eq_s)
    ret = (eq[-1] / eq[0] - 1) * 100

    return {"sharpe": sr, "return_pct": ret, "max_dd_pct": dd,
            "n_trades": total_trades, "n_pairs": len(stable_pairs),
            "equities": eq}, pair_info


# ================================================================
# Strategy 2: Bollinger Band
# ================================================================
def run_bollinger(coin_dfs, lookback, k_band, trading_start, capital=10000.0):
    """Bollinger Band mean reversion per coin."""
    coins = list(coin_dfs.keys())
    n_coins = len(coins)
    per_coin = capital / n_coins
    fee_rate = FEE_BPS / 10_000
    all_eqs = []; total_trades = 0

    for coin in coins:
        df = coin_dfs[coin]
        closes = df["close"].values
        n = len(df)
        ts = df["timestamp"].values

        sma = pd.Series(closes).rolling(lookback, min_periods=lookback).mean().values
        std = pd.Series(closes).rolling(lookback, min_periods=lookback).std(ddof=1).values

        trade_start = 0
        for i in range(n):
            if ts[i] >= np.datetime64(trading_start):
                trade_start = i; break

        equity = per_coin; cash = equity; pos = 0; entry_px = 0
        equities = np.full(n, equity); n_tr = 0
        side = None

        for i in range(trade_start + 1, n):
            o = closes[i]; c = closes[i]
            if np.isnan(sma[i]) or np.isnan(std[i]) or std[i] < 1e-10:
                continue

            upper = sma[i] + k_band * std[i]
            lower = sma[i] - k_band * std[i]
            stop_upper = sma[i] + (k_band + 1) * std[i]
            stop_lower = sma[i] - (k_band + 1) * std[i]

            # Execute position change
            if side == "long":
                pnl = abs(pos) * (c - entry_px) / entry_px if entry_px > 0 else 0
                equity = cash + pnl
                if c >= sma[i] or c <= stop_lower:  # target or stop
                    cash += pnl - abs(pos) * fee_rate
                    pos = 0; side = None; entry_px = 0; n_tr += 1
            elif side == "short":
                pnl = abs(pos) * (entry_px - c) / entry_px if entry_px > 0 else 0
                equity = cash + pnl
                if c <= sma[i] or c >= stop_upper:
                    cash += pnl - abs(pos) * fee_rate
                    pos = 0; side = None; entry_px = 0; n_tr += 1
            else:
                equity = cash

            equities[i] = equity

            if side is None:
                size = min(equity * 3.0 * 0.5, equity * 0.15 * n_coins)
                if c <= lower:
                    side = "long"; pos = size; entry_px = c
                    cash -= size * fee_rate; n_tr += 1
                elif c >= upper:
                    side = "short"; pos = size; entry_px = c
                    cash -= size * fee_rate; n_tr += 1

        eq = equities[trade_start:]
        all_eqs.append(eq)
        total_trades += n_tr

    ml = min(len(e) for e in all_eqs)
    port = sum(e[:ml] for e in all_eqs)
    port = port / port[0] * capital
    eq_s = pd.Series(port)
    sr = sharpe_ratio(eq_s, PPY); _, dd = max_drawdown(eq_s)
    ret = (port[-1] / port[0] - 1) * 100
    return {"sharpe": sr, "return_pct": ret, "max_dd_pct": dd, "n_trades": total_trades}


# ================================================================
# Strategy 3: Ornstein-Uhlenbeck
# ================================================================
def estimate_ou(log_prices, dt=1.0):
    """Estimate OU parameters from log prices using OLS."""
    n = len(log_prices)
    if n < 30:
        return None, None, None
    y = log_prices[1:]
    x = log_prices[:-1]
    # OLS: y = a + b*x + noise
    x_mean = np.mean(x); y_mean = np.mean(y)
    b = np.sum((x - x_mean) * (y - y_mean)) / np.sum((x - x_mean)**2)
    a = y_mean - b * x_mean
    residuals = y - (a + b * x)
    sigma_ou = np.std(residuals)

    if b >= 1 or b <= 0:
        return None, None, None

    theta = -np.log(b) / dt
    mu = a / (1 - b)
    return theta, mu, sigma_ou


def run_ou(coin_dfs, ou_window, entry_thresh, theta_min, trading_start, capital=10000.0):
    """OU-based mean reversion."""
    coins = list(coin_dfs.keys())
    n_coins = len(coins)
    per_coin = capital / n_coins
    fee_rate = FEE_BPS / 10_000
    all_eqs = []; total_trades = 0; theta_stats = {}

    for coin in coins:
        df = coin_dfs[coin]
        closes = df["close"].values
        n = len(df)
        ts = df["timestamp"].values
        log_prices = np.log(closes)

        trade_start = 0
        for i in range(n):
            if ts[i] >= np.datetime64(trading_start):
                trade_start = i; break

        equity = per_coin; cash = equity; pos = 0; entry_px = 0
        equities = np.full(n, equity); n_tr = 0; side = None
        thetas = []

        for i in range(trade_start + 1, n):
            c = closes[i]

            # Estimate OU on rolling window
            window = log_prices[max(0, i-ou_window):i]
            theta, mu, sigma = estimate_ou(window)

            if theta is not None:
                thetas.append(theta)

            # MTM
            if side == "long":
                pnl = abs(pos) * (c - entry_px) / entry_px if entry_px > 0 else 0
                equity = cash + pnl
            elif side == "short":
                pnl = abs(pos) * (entry_px - c) / entry_px if entry_px > 0 else 0
                equity = cash + pnl
            else:
                equity = cash
            equities[i] = equity

            if theta is None or sigma is None or sigma < 1e-10:
                continue
            if theta < theta_min:
                continue

            signal = theta * (mu - log_prices[i]) / sigma

            if side == "long" and signal < 0.1:
                cash += pnl - abs(pos) * fee_rate
                pos = 0; side = None; n_tr += 1
            elif side == "short" and signal > -0.1:
                cash += pnl - abs(pos) * fee_rate
                pos = 0; side = None; n_tr += 1
            elif side is None:
                size = min(equity * 3.0 * 0.5, equity * 0.15 * n_coins)
                if signal > entry_thresh:
                    side = "long"; pos = size; entry_px = c
                    cash -= size * fee_rate; n_tr += 1
                elif signal < -entry_thresh:
                    side = "short"; pos = size; entry_px = c
                    cash -= size * fee_rate; n_tr += 1

        eq = equities[trade_start:]
        all_eqs.append(eq)
        total_trades += n_tr
        if thetas:
            theta_stats[coin] = {"mean": np.mean(thetas), "std": np.std(thetas)}

    ml = min(len(e) for e in all_eqs)
    port = sum(e[:ml] for e in all_eqs)
    port = port / port[0] * capital
    eq_s = pd.Series(port)
    sr = sharpe_ratio(eq_s, PPY); _, dd = max_drawdown(eq_s)
    ret = (port[-1] / port[0] - 1) * 100
    return {"sharpe": sr, "return_pct": ret, "max_dd_pct": dd,
            "n_trades": total_trades, "theta_stats": theta_stats}


# ================================================================
# Strategy 4: Cointegration
# ================================================================
def run_coint(coin_dfs, z_lookback, entry_z, exit_z, recalib_period,
              trading_start, capital=10000.0):
    """Cointegration-based pairs trading."""
    coins = list(coin_dfs.keys())
    n_coins = len(coins)

    # Align prices
    all_ts = None
    for df in coin_dfs.values():
        ts = set(df["timestamp"].values)
        all_ts = ts if all_ts is None else all_ts & ts
    common_ts = sorted(all_ts)
    n_bars = len(common_ts)

    prices = np.zeros((n_bars, n_coins))
    for ci, coin in enumerate(coins):
        df = coin_dfs[coin]
        ts_map = {t: i for i, t in enumerate(df["timestamp"].values)}
        for ti, t in enumerate(common_ts):
            idx = ts_map.get(t)
            if idx is not None:
                prices[ti, ci] = df.iloc[idx]["close"]

    ts_start = np.datetime64(trading_start)
    trade_idx = 0
    for i, t in enumerate(common_ts):
        if t >= ts_start:
            trade_idx = i; break

    # Find cointegrated pairs on IS data
    coint_pairs = []
    for ci, cj in combinations(range(n_coins), 2):
        p_i = prices[:trade_idx, ci]
        p_j = prices[:trade_idx, cj]
        valid = (p_i > 0) & (p_j > 0)
        if valid.sum() < 200:
            continue
        try:
            _, pval, _ = coint(p_i[valid], p_j[valid])
            if pval < 0.05:
                coint_pairs.append((ci, cj, pval, coins[ci], coins[cj]))
        except Exception:
            continue

    coint_pairs.sort(key=lambda x: x[2])
    pair_info = [(p[3], p[4], p[2]) for p in coint_pairs[:20]]

    if not coint_pairs:
        return None, pair_info

    # Trade
    n_pairs = min(len(coint_pairs), 20)  # cap at 20 pairs
    per_pair = capital / max(n_pairs, 1)
    fee_rate = FEE_BPS / 10_000
    equity = capital; cash = equity
    equities = np.full(n_bars, equity)
    pair_pos = {}; pair_beta = {}
    total_trades = 0
    last_calib = {}

    for i in range(trade_idx + 1, n_bars):
        # MTM
        for (ci, cj), pos in list(pair_pos.items()):
            beta = pair_beta.get((ci, cj), 1.0)
            ret_spread = (prices[i, ci] / prices[i-1, ci] - 1) - beta * (prices[i, cj] / prices[i-1, cj] - 1)
            cash += pos * ret_spread

        equity = cash; equities[i] = equity

        for pi_idx in range(min(n_pairs, len(coint_pairs))):
            ci, cj, _, _, _ = coint_pairs[pi_idx]
            key = (ci, cj)

            # Recalibrate beta
            if key not in pair_beta or (i - last_calib.get(key, 0)) >= recalib_period:
                window = max(0, i - z_lookback * 2)
                p_i = prices[window:i, ci]; p_j = prices[window:i, cj]
                valid = (p_i > 0) & (p_j > 0)
                if valid.sum() > 50:
                    beta = np.polyfit(p_j[valid], p_i[valid], 1)[0]
                    pair_beta[key] = beta
                    last_calib[key] = i

            beta = pair_beta.get(key, 1.0)
            spread = prices[max(0,i-z_lookback):i, ci] - beta * prices[max(0,i-z_lookback):i, cj]
            if len(spread) < z_lookback // 2:
                continue
            s_mean = np.mean(spread); s_std = np.std(spread)
            if s_std < 1e-10:
                continue
            current = prices[i, ci] - beta * prices[i, cj]
            z = (current - s_mean) / s_std

            cur_pos = pair_pos.get(key, 0)
            if abs(cur_pos) < 1:
                size = min(per_pair, equity * 0.15)
                if z > entry_z:
                    pair_pos[key] = -size; cash -= size * 2 * fee_rate; total_trades += 1
                elif z < -entry_z:
                    pair_pos[key] = size; cash -= size * 2 * fee_rate; total_trades += 1
            elif abs(z) < exit_z:
                cash -= abs(cur_pos) * 2 * fee_rate
                pair_pos[key] = 0; total_trades += 1

    eq = equities[trade_idx:]
    eq = eq / eq[0] * capital
    eq_s = pd.Series(eq)
    sr = sharpe_ratio(eq_s, PPY); _, dd = max_drawdown(eq_s)
    ret = (eq[-1] / eq[0] - 1) * 100
    return {"sharpe": sr, "return_pct": ret, "max_dd_pct": dd,
            "n_trades": total_trades, "n_pairs": len(coint_pairs)}, pair_info


# ================================================================
# Strategy 5: Funding Rate (W2 only)
# ================================================================
def run_funding(coin_funding, coin_prices, fr_lookback, entry_z, exit_z,
                trading_start, capital=10000.0):
    """Funding rate mean reversion. Only coins with funding data."""
    coins = list(coin_funding.keys())
    if len(coins) < 3:
        return None

    n_coins = len(coins)
    per_coin = capital / n_coins
    fee_rate = FEE_BPS / 10_000
    all_eqs = []; total_trades = 0

    for coin in coins:
        fr_df = coin_funding[coin]
        price_df = coin_prices.get(coin)
        if price_df is None:
            continue

        # Align FR to 8H bars
        fr_ts = fr_df["timestamp"].values
        fr_vals = fr_df["funding_rate"].values
        p_ts = price_df["timestamp"].values
        closes = price_df["close"].values
        n = len(p_ts)

        # Map FR to price bars (take last known FR)
        aligned_fr = np.full(n, np.nan)
        fr_idx = 0
        for i in range(n):
            while fr_idx < len(fr_ts) - 1 and fr_ts[fr_idx + 1] <= p_ts[i]:
                fr_idx += 1
            if fr_idx < len(fr_vals):
                aligned_fr[i] = fr_vals[fr_idx]

        fr_series = pd.Series(aligned_fr)
        fr_mean = fr_series.rolling(fr_lookback, min_periods=30).mean().values
        fr_std = fr_series.rolling(fr_lookback, min_periods=30).std().values

        trade_start = 0
        for i in range(n):
            if p_ts[i] >= np.datetime64(trading_start):
                trade_start = i; break

        equity = per_coin; cash = equity; pos = 0; entry_px = 0
        equities = np.full(n, equity); n_tr = 0; side = None

        for i in range(trade_start + 1, n):
            c = closes[i]

            if side == "long":
                pnl = abs(pos) * (c - entry_px) / entry_px if entry_px > 0 else 0
                equity = cash + pnl
            elif side == "short":
                pnl = abs(pos) * (entry_px - c) / entry_px if entry_px > 0 else 0
                equity = cash + pnl
            else:
                equity = cash
            equities[i] = equity

            if np.isnan(fr_mean[i]) or np.isnan(fr_std[i]) or fr_std[i] < 1e-10:
                continue
            z = (aligned_fr[i] - fr_mean[i]) / fr_std[i] if not np.isnan(aligned_fr[i]) else 0

            if side == "long" and z > -exit_z:
                cash += pnl - abs(pos) * fee_rate; pos = 0; side = None; n_tr += 1
            elif side == "short" and z < exit_z:
                cash += pnl - abs(pos) * fee_rate; pos = 0; side = None; n_tr += 1
            elif side is None:
                size = min(equity * 3.0 * 0.5, equity * 0.15 * n_coins)
                if z > entry_z:  # extreme positive FR -> short
                    side = "short"; pos = size; entry_px = c
                    cash -= size * fee_rate; n_tr += 1
                elif z < -entry_z:  # extreme negative FR -> long
                    side = "long"; pos = size; entry_px = c
                    cash -= size * fee_rate; n_tr += 1

        eq = equities[trade_start:]
        all_eqs.append(eq)
        total_trades += n_tr

    if not all_eqs:
        return None
    ml = min(len(e) for e in all_eqs)
    port = sum(e[:ml] for e in all_eqs)
    port = port / port[0] * capital
    eq_s = pd.Series(port)
    sr = sharpe_ratio(eq_s, PPY); _, dd = max_drawdown(eq_s)
    ret = (port[-1] / port[0] - 1) * 100
    return {"sharpe": sr, "return_pct": ret, "max_dd_pct": dd, "n_trades": total_trades}


# ================================================================
# Walk-forward runner
# ================================================================
def sweep_strategy(name, run_fn, param_grid, coin_dfs, windows):
    """Generic walk-forward sweep for any strategy."""
    results = {}
    for w in windows:
        print(f"    {w['name']}: IS {w['is_start']}~{w['is_end']}, OOS {w['oos_start']}~{w['oos_end']}")

        # IS sweep
        is_results = []
        for params in param_grid:
            r = run_fn(coin_dfs, *params, trading_start=w["is_start"])
            if isinstance(r, tuple):
                r = r[0]  # some return (result, info)
            sr = r["sharpe"] if r and not np.isnan(r.get("sharpe", float("nan"))) else -999
            is_results.append((*params, sr))

        # Best
        positive = [x for x in is_results if x[-1] > 0]
        best = max(positive if positive else is_results, key=lambda x: x[-1])
        best_params = best[:-1]
        best_is_sr = best[-1]
        print(f"      Best IS: params={best_params} SR={best_is_sr:.3f}")

        # OOS
        r_oos = run_fn(coin_dfs, *best_params, trading_start=w["oos_start"])
        extra_info = None
        if isinstance(r_oos, tuple):
            r_oos, extra_info = r_oos
        oos_sr = r_oos["sharpe"] if r_oos else None
        oos_ret = r_oos["return_pct"] if r_oos else None
        print(f"      OOS: SR={oos_sr:.3f} Ret={oos_ret:.2f}%" if oos_sr else "      OOS: failed")

        results[w["name"]] = {
            "best_params": list(best_params),
            "is_sharpe": best_is_sr,
            "oos_sharpe": oos_sr,
            "oos_return": oos_ret,
            "extra_info": extra_info,
            "oos_result": {k: v for k, v in r_oos.items() if k != "equities"} if r_oos else None,
        }

    return results


def main():
    t0 = time.time()
    cache = ParquetCache()

    # Load all 8H data with warmup
    print("Loading data...", flush=True)
    full_dfs = {}
    for coin in ALL_28:
        df = load_8h(cache, coin, "2019-01-01", "2025-01-01")
        if df is not None:
            full_dfs[coin] = df
    print(f"  {len(full_dfs)} coins loaded")

    all_results = {}

    # ================================================================
    # Strategy 1: Pairs Trading
    # ================================================================
    print(f"\n{'='*60}")
    print("Strategy 1: Pairs Trading")
    print(f"{'='*60}")
    pairs_grid = list(product([90, 180, 360], [1.5, 2.0, 2.5], [0.25, 0.50]))
    r1 = sweep_strategy("Pairs", lambda dfs, lb, ez, xz, trading_start:
                         run_pairs(dfs, lb, ez, xz, trading_start),
                         pairs_grid, full_dfs, WINDOWS)
    all_results["1_Pairs"] = r1

    # ================================================================
    # Strategy 2: Bollinger Band
    # ================================================================
    print(f"\n{'='*60}")
    print("Strategy 2: Bollinger Band")
    print(f"{'='*60}")
    bb_grid = list(product([90, 180, 360], [1.5, 2.0, 2.5]))
    r2 = sweep_strategy("Bollinger", lambda dfs, lb, k, trading_start:
                         run_bollinger(dfs, lb, k, trading_start),
                         bb_grid, full_dfs, WINDOWS)
    all_results["2_Bollinger"] = r2

    # ================================================================
    # Strategy 3: OU
    # ================================================================
    print(f"\n{'='*60}")
    print("Strategy 3: Ornstein-Uhlenbeck")
    print(f"{'='*60}")
    ou_grid = list(product([180, 360, 720], [1.0, 1.5, 2.0], [0.01, 0.05]))
    r3 = sweep_strategy("OU", lambda dfs, w, t, tm, trading_start:
                         run_ou(dfs, w, t, tm, trading_start),
                         ou_grid, full_dfs, WINDOWS)
    all_results["3_OU"] = r3

    # Print theta stats from W2
    if "W2" in r3 and r3["W2"].get("oos_result"):
        ts = r3["W2"]["oos_result"].get("theta_stats", {})
        if ts:
            print("\n  OU theta stats (W2):")
            for coin in sorted(ts.keys(), key=lambda c: -ts[c]["mean"]):
                print(f"    {coin}: theta_mean={ts[coin]['mean']:.4f}")

    # ================================================================
    # Strategy 4: Cointegration
    # ================================================================
    print(f"\n{'='*60}")
    print("Strategy 4: Cointegration")
    print(f"{'='*60}")
    coint_grid = list(product([90, 180], [1.5, 2.0, 2.5], [0.25, 0.50], [90, 180]))
    r4 = sweep_strategy("Coint", lambda dfs, zl, ez, xz, rp, trading_start:
                         run_coint(dfs, zl, ez, xz, rp, trading_start),
                         coint_grid, full_dfs, WINDOWS)
    all_results["4_Coint"] = r4

    # ================================================================
    # Strategy 5: Funding Rate (W2 only)
    # ================================================================
    print(f"\n{'='*60}")
    print("Strategy 5: Funding Rate")
    print(f"{'='*60}")

    # Load funding data
    funding_data = {}
    for f in os.listdir("data/cache"):
        if f.startswith("funding_"):
            coin = f.replace("funding_", "").replace(".parquet", "")
            df = pd.read_parquet(f"data/cache/{f}")
            if df["timestamp"].dt.tz is not None:
                df["timestamp"] = df["timestamp"].dt.tz_localize(None)
            funding_data[coin] = df

    fr_coins = list(funding_data.keys())
    print(f"  Funding data: {fr_coins}")
    print(f"  Range: {funding_data['BTC']['timestamp'].min()} to {funding_data['BTC']['timestamp'].max()}")
    print(f"  W1 not possible (data from 2023). Running W2 only.")

    # W2 only for funding
    fr_grid = list(product([90, 180, 360], [1.5, 2.0, 2.5], [0.25, 0.50]))
    fr_price_dfs = {c: full_dfs[c] for c in fr_coins if c in full_dfs}

    w2 = WINDOWS[1]
    print(f"    W2: IS {w2['is_start']}~{w2['is_end']}, OOS {w2['oos_start']}~{w2['oos_end']}")
    fr_is_results = []
    for params in fr_grid:
        r = run_funding(funding_data, fr_price_dfs, *params, trading_start=w2["is_start"])
        sr = r["sharpe"] if r and not np.isnan(r.get("sharpe", float("nan"))) else -999
        fr_is_results.append((*params, sr))

    positive = [x for x in fr_is_results if x[-1] > 0]
    best = max(positive if positive else fr_is_results, key=lambda x: x[-1])
    best_params = best[:-1]; best_is_sr = best[-1]
    print(f"      Best IS: params={best_params} SR={best_is_sr:.3f}")

    r_fr_oos = run_funding(funding_data, fr_price_dfs, *best_params, trading_start=w2["oos_start"])
    fr_oos_sr = r_fr_oos["sharpe"] if r_fr_oos else None
    print(f"      OOS: SR={fr_oos_sr:.3f}" if fr_oos_sr else "      OOS: failed")

    all_results["5_Funding"] = {
        "W2": {"best_params": list(best_params), "is_sharpe": best_is_sr,
               "oos_sharpe": fr_oos_sr,
               "oos_return": r_fr_oos["return_pct"] if r_fr_oos else None},
        "note": "W1 not possible (funding data from 2023 only)"
    }

    # ================================================================
    # Summary
    # ================================================================
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"\n  {'Strategy':<20} {'W1 params':>15} {'W1 OOS SR':>10} {'W2 params':>15} {'W2 OOS SR':>10} {'Match':>6}")
    print("  " + "-" * 80)

    for name, r in all_results.items():
        w1 = r.get("W1", {})
        w2 = r.get("W2", {})
        p1 = str(w1.get("best_params", "N/A"))[:15]
        p2 = str(w2.get("best_params", "N/A"))[:15]
        s1 = w1.get("oos_sharpe")
        s2 = w2.get("oos_sharpe")
        match = "YES" if w1.get("best_params") == w2.get("best_params") else "NO"
        s1s = f"{s1:.3f}" if s1 is not None else "N/A"
        s2s = f"{s2:.3f}" if s2 is not None else "N/A"
        print(f"  {name:<20} {p1:>15} {s1s:>10} {p2:>15} {s2s:>10} {match:>6}")

    # Save
    save = {}
    for name, r in all_results.items():
        save[name] = {}
        for wname, wr in r.items():
            if isinstance(wr, dict):
                save[name][wname] = {k: v for k, v in wr.items()
                                      if k not in ("equities", "theta_stats", "extra_info")}
            else:
                save[name][wname] = wr

    Path("sweep_results").mkdir(exist_ok=True)
    with open("sweep_results/mr_strategies_5.json", "w") as f:
        json.dump(save, f, indent=2, default=str)

    # RESEARCH_LOG
    log = f"\n## 5 Mean Reversion Strategies ({pd.Timestamp.now().strftime('%Y-%m-%d')})\n\n"
    log += "| Strategy | W1 Params | W1 OOS SR | W2 Params | W2 OOS SR | Match | MktNeutral |\n"
    log += "|----------|-----------|-----------|-----------|-----------|-------|------------|\n"
    neutral = {"1_Pairs": "YES", "2_Bollinger": "NO", "3_OU": "NO", "4_Coint": "YES", "5_Funding": "NO"}
    for name, r in all_results.items():
        w1 = r.get("W1", {}); w2 = r.get("W2", {})
        p1 = str(w1.get("best_params", "N/A"))[:20]
        p2 = str(w2.get("best_params", "N/A"))[:20]
        s1 = w1.get("oos_sharpe"); s2 = w2.get("oos_sharpe")
        s1s = f"{s1:.3f}" if s1 is not None else "N/A"
        s2s = f"{s2:.3f}" if s2 is not None else "N/A"
        match = "YES" if w1.get("best_params") == w2.get("best_params") else "NO"
        mn = neutral.get(name, "?")
        log += f"| {name} | {p1} | {s1s} | {p2} | {s2s} | {match} | {mn} |\n"

    with open("RESEARCH_LOG.md", "a", encoding="utf-8") as f:
        f.write(log)

    print(f"\n  Total: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
