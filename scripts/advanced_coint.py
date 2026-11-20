#!/usr/bin/env python3
"""Advanced Cointegration + Avellaneda-Lee PCA mean reversion.

Part 1: Triple-filtered cointegration pairs (Engle-Granger + ADF + Hurst)
Part 2: PCA residual OU (Avellaneda-Lee)
Both on 1H/4H/8H/1D timeframes.
"""

import sys, os, time, json, warnings, gc
from pathlib import Path
from itertools import product, combinations
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptolab.data.cache import ParquetCache
from cryptolab.backtest.metrics import sharpe_ratio, max_drawdown
from scripts.donchian_full_sweep import resample_ohlcv
from scripts.mean_reversion_experiment import compute_dynamic_slippage
from scripts.mean_reversion_strategies import estimate_ou, ALL_28
from scripts.cross_sectional_momentum import run_xsmom
from statsmodels.tsa.stattools import coint, adfuller

PPY_MAP = {"1h": 8766, "4h": 2190, "8h": 1096, "1d": 365}
FEE_BPS = 3.5

WINDOWS = [
    {"name": "W1", "is_start": "2021-01-01", "is_end": "2023-01-01",
     "oos_start": "2023-01-01", "oos_end": "2024-01-01"},
    {"name": "W2", "is_start": "2022-01-01", "is_end": "2024-01-01",
     "oos_start": "2024-01-01", "oos_end": "2025-01-01"},
]


def load_freq(cache, coin, freq, start, end):
    df = cache.read("okx", coin, "1h")
    if df is None or df.empty: return None
    if df["timestamp"].dt.tz is not None:
        df["timestamp"] = df["timestamp"].dt.tz_localize(None)
    if freq != "1h":
        df = resample_ohlcv(df, freq)
    mask = (df["timestamp"] >= pd.Timestamp(start)) & (df["timestamp"] < pd.Timestamp(end))
    out = df[mask].reset_index(drop=True)
    return out if len(out) > 50 else None


def hurst_rs(ts, max_lag=100):
    """Hurst exponent via R/S method."""
    n = len(ts)
    if n < 50: return 0.5
    lags = range(10, min(max_lag, n // 2))
    rs_values = []
    for lag in lags:
        rs_list = []
        for start in range(0, n - lag, lag):
            chunk = ts[start:start + lag]
            mean_c = np.mean(chunk)
            cum_dev = np.cumsum(chunk - mean_c)
            r = np.max(cum_dev) - np.min(cum_dev)
            s = np.std(chunk)
            if s > 0:
                rs_list.append(r / s)
        if rs_list:
            rs_values.append((np.log(lag), np.log(np.mean(rs_list))))
    if len(rs_values) < 3: return 0.5
    x = np.array([v[0] for v in rs_values])
    y = np.array([v[1] for v in rs_values])
    slope = np.polyfit(x, y, 1)[0]
    return float(slope)


def align_log_prices(coin_dfs):
    """Build aligned log price matrix."""
    coins = list(coin_dfs.keys())
    n_c = len(coins)
    all_ts = None
    for df in coin_dfs.values():
        ts = set(df["timestamp"].values)
        all_ts = ts if all_ts is None else all_ts & ts
    common_ts = sorted(all_ts)
    n = len(common_ts)

    prices = np.zeros((n, n_c))
    for ci, coin in enumerate(coins):
        df = coin_dfs[coin]
        tm = {t: i for i, t in enumerate(df["timestamp"].values)}
        for ti, t in enumerate(common_ts):
            idx = tm.get(t)
            if idx is not None:
                prices[ti, ci] = df.iloc[idx]["close"]

    log_p = np.log(np.maximum(prices, 1e-10))
    returns = np.zeros_like(prices)
    returns[1:] = prices[1:] / np.maximum(prices[:-1], 1e-10) - 1

    return coins, common_ts, prices, log_p, returns


# ================================================================
# Part 1: Triple-filtered Cointegration
# ================================================================
def find_triple_pairs(log_p, prices, coins, end_idx):
    """Find pairs passing: cointegration + ADF on spread + Hurst < 0.5."""
    n_c = len(coins)
    pairs = []

    for ci, cj in combinations(range(n_c), 2):
        lp_i = log_p[:end_idx, ci]; lp_j = log_p[:end_idx, cj]
        valid = (prices[:end_idx, ci] > 0) & (prices[:end_idx, cj] > 0)
        if valid.sum() < 300: continue

        # Filter 1: Engle-Granger cointegration
        try:
            _, pval, _ = coint(lp_i[valid], lp_j[valid])
        except Exception: continue
        if pval >= 0.05: continue

        # Hedge ratio
        beta = np.polyfit(lp_j[valid], lp_i[valid], 1)[0]
        if abs(beta) < 0.3 or abs(beta) > 3.0: continue

        # Spread
        spread = lp_i[valid] - beta * lp_j[valid]

        # Filter 2: ADF on spread
        try:
            adf_stat, adf_p, _, _, _, _ = adfuller(spread, maxlag=20)
        except Exception: continue
        if adf_p >= 0.05: continue

        # Filter 3: Hurst < 0.5
        h = hurst_rs(spread)
        if h >= 0.5: continue

        # Half-life
        spread_lag = spread[:-1]; spread_diff = np.diff(spread)
        if len(spread_lag) > 10 and np.std(spread_lag) > 0:
            phi = np.polyfit(spread_lag, spread_diff, 1)[0]
            half_life = -np.log(2) / phi if phi < 0 else 999
        else:
            half_life = 999

        pairs.append({
            "ci": ci, "cj": cj, "a": coins[ci], "b": coins[cj],
            "coint_p": float(pval), "beta": float(beta),
            "adf_p": float(adf_p), "hurst": float(h),
            "half_life": float(half_life),
        })

    pairs.sort(key=lambda x: x["coint_p"])
    return pairs


def run_coint_v2(coin_dfs, z_lb, entry_z, exit_z, recalib, max_hold,
                 trading_start, freq, capital=10000.0, leverage=3.0):
    """Improved cointegration with triple filter + dynamic beta + risk controls."""
    coins, common_ts, prices, log_p, returns = align_log_prices(coin_dfs)
    n_c = len(coins); n = len(common_ts)
    ppy = PPY_MAP.get(freq, 1096)

    ts_start = np.datetime64(trading_start)
    trade_idx = 0
    for i, t in enumerate(common_ts):
        if t >= ts_start: trade_idx = i; break

    # Find pairs on IS data
    pairs = find_triple_pairs(log_p, prices, coins, trade_idx)
    if not pairs:
        return {"sharpe": 0, "return_pct": 0, "max_dd_pct": 0,
                "n_trades": 0, "n_pairs": 0}, pairs

    max_pairs = min(len(pairs), 15)
    fee_rate = FEE_BPS / 10_000

    equity = capital; cash = equity
    equities = np.full(n, equity)
    pair_pos = {}; pair_beta = {}; pair_entry_bar = {}; pair_entry_eq = {}
    last_calib = {}; total_trades = 0

    for i in range(trade_idx + 1, n):
        # MTM
        for key, pos_usd in list(pair_pos.items()):
            if abs(pos_usd) < 1: continue
            ci, cj = key
            beta = pair_beta.get(key, 1.0)
            ret_i = returns[i, ci]; ret_j = returns[i, cj]
            cash += pos_usd * (ret_i - beta * ret_j)

        equity = cash; equities[i] = equity

        for pi in range(max_pairs):
            p = pairs[pi]
            ci, cj = p["ci"], p["cj"]
            key = (ci, cj)

            # Recalibrate beta
            if key not in pair_beta or (i - last_calib.get(key, 0)) >= recalib:
                ws = max(0, i - z_lb * 2)
                lpi = log_p[ws:i, ci]; lpj = log_p[ws:i, cj]
                v = (prices[ws:i, ci] > 0) & (prices[ws:i, cj] > 0)
                if v.sum() > 50:
                    new_beta = np.polyfit(lpj[v], lpi[v], 1)[0]
                    new_beta = np.clip(new_beta, 0.3, 3.0)
                    old_beta = pair_beta.get(key, new_beta)
                    if abs(new_beta - old_beta) / abs(old_beta) > 0.30 and key in pair_pos:
                        continue  # skip unstable beta
                    pair_beta[key] = new_beta
                    last_calib[key] = i

            beta = pair_beta.get(key, p["beta"])

            # Spread Z-score
            ws = max(0, i - z_lb)
            spread = log_p[ws:i, ci] - beta * log_p[ws:i, cj]
            if len(spread) < z_lb // 2: continue
            s_mean = np.mean(spread); s_std = np.std(spread)
            if s_std < 1e-10: continue
            cur = log_p[i, ci] - beta * log_p[i, cj]
            z = (cur - s_mean) / s_std

            cur_pos = pair_pos.get(key, 0)
            max_per = equity * 0.05
            gross = sum(abs(v) for v in pair_pos.values())

            if abs(cur_pos) < 1:
                if gross >= equity * leverage: continue
                size = min(max_per, equity * leverage - gross)
                if size < 10: continue
                if z > entry_z:
                    pair_pos[key] = -size; cash -= size * 2 * fee_rate
                    pair_entry_bar[key] = i; pair_entry_eq[key] = equity
                    total_trades += 1
                elif z < -entry_z:
                    pair_pos[key] = size; cash -= size * 2 * fee_rate
                    pair_entry_bar[key] = i; pair_entry_eq[key] = equity
                    total_trades += 1
            else:
                # Exit conditions
                should_exit = False
                # Mean reversion target
                if abs(z) < exit_z: should_exit = True
                # Take profit (3%)
                entry_eq = pair_entry_eq.get(key, equity)
                if entry_eq > 0 and (equity - entry_eq) / entry_eq > 0.03: should_exit = True
                # Stop loss (2%)
                if entry_eq > 0 and (entry_eq - equity) / entry_eq > 0.02: should_exit = True
                # Time stop
                bars_held = i - pair_entry_bar.get(key, i)
                if bars_held > max_hold: should_exit = True

                if should_exit:
                    cash -= abs(cur_pos) * 2 * fee_rate
                    pair_pos[key] = 0; total_trades += 1

    eq = equities[trade_idx:]
    eq = eq / eq[0] * capital
    eq_s = pd.Series(eq)
    sr = sharpe_ratio(eq_s, ppy); _, dd = max_drawdown(eq_s)
    ret = (eq[-1] / eq[0] - 1) * 100
    return {"sharpe": sr, "return_pct": ret, "max_dd_pct": dd,
            "n_trades": total_trades, "n_pairs": len(pairs), "equities": eq}, pairs


# ================================================================
# Part 2: Avellaneda-Lee PCA
# ================================================================
def run_pca_ou(coin_dfs, n_components, entry_s, exit_s, ou_window, recalib,
              trading_start, freq, capital=10000.0, leverage=3.0):
    """PCA residual OU (Avellaneda-Lee method)."""
    coins, common_ts, prices, log_p, returns = align_log_prices(coin_dfs)
    n_c = len(coins); n = len(common_ts)
    ppy = PPY_MAP.get(freq, 1096)

    ts_start = np.datetime64(trading_start)
    trade_idx = 0
    for i, t in enumerate(common_ts):
        if t >= ts_start: trade_idx = i; break

    fee_rate = FEE_BPS / 10_000
    per_coin = capital / n_c
    equity = capital; cash = equity
    equities = np.full(n, equity)
    positions = np.zeros(n_c)  # signed USD per coin
    entry_prices = np.zeros(n_c)
    total_trades = 0
    last_pca_bar = -9999

    pca_model = None; pca_loadings = None
    cum_residuals = np.zeros((n, n_c))

    for i in range(trade_idx + 1, n):
        # MTM
        for ci in range(n_c):
            if abs(positions[ci]) > 0.01 and entry_prices[ci] > 0 and prices[i, ci] > 0:
                pass
        unrealized = 0.0
        for ci in range(n_c):
            if abs(positions[ci]) > 0.01 and entry_prices[ci] > 0:
                if positions[ci] > 0:
                    unrealized += abs(positions[ci]) * (prices[i, ci] / entry_prices[ci] - 1)
                else:
                    unrealized += abs(positions[ci]) * (1 - prices[i, ci] / entry_prices[ci])
        equity = cash + unrealized; equities[i] = equity

        # Recalibrate PCA
        if i - last_pca_bar >= recalib or pca_model is None:
            ws = max(0, i - ou_window * 2)
            ret_window = returns[ws:i]
            if ret_window.shape[0] < 100: continue

            # Remove coins with all zeros
            valid_cols = np.std(ret_window, axis=0) > 1e-10
            if valid_cols.sum() < n_components + 2: continue

            try:
                pca = PCA(n_components=min(n_components, valid_cols.sum() - 1))
                factors = pca.fit_transform(ret_window[:, valid_cols])
                pca_loadings = np.zeros((n_c, pca.n_components_))
                valid_idx = np.where(valid_cols)[0]
                pca_loadings[valid_idx] = pca.components_.T
                pca_model = pca
                last_pca_bar = i
            except Exception:
                continue

        if pca_model is None: continue

        # Compute residuals for current bar
        ret_i = returns[i].reshape(1, -1)
        factor_ret = ret_i @ pca_loadings  # [1, K]
        explained = factor_ret @ pca_loadings.T  # [1, n_c]
        residual = ret_i - explained  # [1, n_c]
        cum_residuals[i] = cum_residuals[i - 1] + residual.flatten()

        # OU on cumulative residuals
        new_positions = np.zeros(n_c)
        active_coins = 0

        for ci in range(n_c):
            ws = max(trade_idx, i - ou_window)
            cum_res = cum_residuals[ws:i + 1, ci]
            if len(cum_res) < 30: continue

            theta, mu, sigma = estimate_ou(cum_res)
            if theta is None or theta < 0.01 or sigma < 1e-10: continue

            s_score = (cum_res[-1] - mu) / sigma

            # Vol targeting
            ann_vol = sigma * np.sqrt(ppy)
            vol_sc = min(2.0, max(0.25, 0.15 / ann_vol)) if ann_vol > 0 else 1.0
            max_pos = equity * 0.10  # 10% per coin

            if s_score > entry_s:
                new_positions[ci] = -min(per_coin * leverage * vol_sc * abs(s_score) / 3, max_pos)
                active_coins += 1
            elif s_score < -entry_s:
                new_positions[ci] = min(per_coin * leverage * vol_sc * abs(s_score) / 3, max_pos)
                active_coins += 1
            elif abs(s_score) < exit_s:
                new_positions[ci] = 0

        # Enforce market neutrality (net exposure < 10%)
        long_total = sum(p for p in new_positions if p > 0)
        short_total = sum(abs(p) for p in new_positions if p < 0)
        if long_total + short_total > 0:
            net = long_total - short_total
            gross = long_total + short_total
            if abs(net) / gross > 0.10 and gross > 100:
                # Scale down the larger side
                if net > 0:
                    scale = (short_total + 0.10 * gross) / long_total if long_total > 0 else 1
                    for ci in range(n_c):
                        if new_positions[ci] > 0: new_positions[ci] *= min(scale, 1.0)
                else:
                    scale = (long_total + 0.10 * gross) / short_total if short_total > 0 else 1
                    for ci in range(n_c):
                        if new_positions[ci] < 0: new_positions[ci] *= min(scale, 1.0)

        # Execute
        for ci in range(n_c):
            delta = new_positions[ci] - positions[ci]
            if abs(delta) < 5: continue

            if abs(positions[ci]) > 0.01 and entry_prices[ci] > 0:
                if positions[ci] > 0:
                    pnl = abs(positions[ci]) * (prices[i, ci] / entry_prices[ci] - 1)
                else:
                    pnl = abs(positions[ci]) * (1 - prices[i, ci] / entry_prices[ci])
                cash += pnl

            cash -= abs(delta) * fee_rate
            total_trades += 1
            positions[ci] = new_positions[ci]
            entry_prices[ci] = prices[i, ci] if abs(new_positions[ci]) > 0.01 else 0

    eq = equities[trade_idx:]
    eq = eq / eq[0] * capital
    eq_s = pd.Series(eq)
    sr = sharpe_ratio(eq_s, ppy); _, dd = max_drawdown(eq_s)
    ret = (eq[-1] / eq[0] - 1) * 100

    # PCA variance explained
    var_explained = list(pca_model.explained_variance_ratio_) if pca_model else []

    return {"sharpe": sr, "return_pct": ret, "max_dd_pct": dd,
            "n_trades": total_trades, "var_explained": var_explained,
            "equities": eq}


def fmt(v, f=".3f"):
    """Safe format: None -> 'N/A'."""
    if v is None: return "N/A"
    try: return f"{v:{f}}"
    except: return str(v)


def main():
    t0 = time.time()
    cache = ParquetCache()

    timeframes = ["1h", "4h", "8h", "1d"]
    coint_grid = list(product([90, 180], [1.5, 2.0], [0.25, 0.50], [90, 180], [90, 180]))
    pca_grid = list(product([3, 5], [1.0, 1.5, 2.0], [0.25, 0.50], [180, 360], [90, 180]))

    print(f"Coint params: {len(coint_grid)}, PCA params: {len(pca_grid)}")
    all_results = {}
    all_pair_info = {}
    w2_equities = {}  # for correlation computation

    for freq in timeframes:
        print(f"\n{'='*60}")
        print(f"Timeframe: {freq.upper()}")
        print(f"{'='*60}")

        dfs = {}
        for coin in ALL_28:
            df = load_freq(cache, coin, freq, "2019-01-01", "2025-01-01")
            if df is not None:
                dfs[coin] = df
        print(f"  {len(dfs)} coins loaded")

        for strat_name, grid, run_fn in [
            ("Coint", coint_grid, lambda d, *p, ts: run_coint_v2(d, *p, ts, freq)),
            ("PCA", pca_grid, lambda d, *p, ts: run_pca_ou(d, *p, ts, freq)),
        ]:
            print(f"\n  --- {strat_name} ---")

            for w in WINDOWS:
                wname = w["name"]
                print(f"    {wname}: IS {w['is_start']}~{w['is_end']}, OOS {w['oos_start']}~{w['oos_end']}")

                is_results = []
                for pi, params in enumerate(grid):
                    r = run_fn(dfs, *params, ts=w["is_start"])
                    if isinstance(r, tuple): r = r[0]
                    sr = r["sharpe"] if r and not np.isnan(r.get("sharpe", float("nan"))) else -999
                    is_results.append((*params, sr))
                    if (pi + 1) % 10 == 0:
                        print(f"      IS: {pi+1}/{len(grid)}", flush=True)
                    gc.collect()

                pos = [x for x in is_results if x[-1] > 0]
                best = max(pos if pos else is_results, key=lambda x: x[-1])
                bp = best[:-1]; bsr = best[-1]
                print(f"      Best IS: {bp} SR={bsr:.3f}")

                r_oos = run_fn(dfs, *bp, ts=w["oos_start"])
                extra = None
                if isinstance(r_oos, tuple):
                    r_oos, extra = r_oos
                osr = r_oos["sharpe"] if r_oos else None
                oret = r_oos["return_pct"] if r_oos else None
                odd = r_oos["max_dd_pct"] if r_oos else None
                otr = r_oos.get("n_trades", 0) if r_oos else 0
                npairs = r_oos.get("n_pairs") if r_oos else None
                varex = r_oos.get("var_explained") if r_oos else None
                print(f"      OOS: SR={fmt(osr)} Ret={fmt(oret,'.2f')}% DD={fmt(odd,'.2f')}% Tr={otr}")

                skey = f"{strat_name}_{freq}"
                if skey not in all_results: all_results[skey] = {}
                all_results[skey][wname] = {
                    "best_params": list(bp), "is_sharpe": bsr,
                    "oos_sharpe": osr, "oos_return": oret, "oos_dd": odd,
                    "n_pairs": npairs, "n_trades": otr, "var_explained": varex,
                }

                # Save W2 equity for correlation
                if wname == "W2" and r_oos and "equities" in r_oos:
                    w2_equities[skey] = r_oos["equities"]

                # Pair info
                if extra:
                    all_pair_info[f"{skey}_{wname}"] = extra
                    if wname == "W2" and extra:
                        print(f"      Triple-filtered pairs: {len(extra)}")
                        for p in extra[:5]:
                            print(f"        {p['a']}/{p['b']}: p={p['coint_p']:.4f} "
                                  f"beta={p['beta']:.3f} H={p['hurst']:.3f} hl={p['half_life']:.0f}")

                gc.collect()

        # Free data after each timeframe
        del dfs; gc.collect()

    # ================================================================
    # Part 3: Summary Table (required format)
    # ================================================================
    print(f"\n{'='*70}")
    print("Part 3: Summary")
    print(f"{'='*70}")
    print(f"\n  {'Strategy':<15} {'W1 params':>22} {'W1 OOS SR':>10} {'W2 params':>22} {'W2 OOS SR':>10} {'Match':>6} {'Pairs/Coins':>12}")
    print("  " + "-" * 100)

    for key in sorted(all_results.keys()):
        r = all_results[key]
        w1 = r.get("W1", {}); w2 = r.get("W2", {})
        p1 = str(w1.get("best_params", []))[:22]
        p2 = str(w2.get("best_params", []))[:22]
        s1 = fmt(w1.get("oos_sharpe")); s2 = fmt(w2.get("oos_sharpe"))
        match = "YES" if w1.get("best_params") == w2.get("best_params") else "NO"
        np1 = w1.get("n_pairs") or w1.get("n_trades", 0)
        np2 = w2.get("n_pairs") or w2.get("n_trades", 0)
        pc = f"{np1}/{np2}"
        print(f"  {key:<15} {p1:>22} {s1:>10} {p2:>22} {s2:>10} {match:>6} {pc:>12}")

    # ================================================================
    # Pair stability analysis (IS vs OOS)
    # ================================================================
    print(f"\n  --- Pair Stability (Coint triple-filter) ---")
    for freq in timeframes:
        is_key = f"Coint_{freq}_W2"  # W2 IS pairs
        oos_key = f"Coint_{freq}_W2"
        is_pairs = all_pair_info.get(f"Coint_{freq}_W1", [])
        oos_pairs = all_pair_info.get(f"Coint_{freq}_W2", [])
        is_set = set((p["a"], p["b"]) for p in is_pairs) if is_pairs else set()
        oos_set = set((p["a"], p["b"]) for p in oos_pairs) if oos_pairs else set()
        overlap = is_set & oos_set
        print(f"  {freq}: W1 pairs={len(is_set)}, W2 pairs={len(oos_set)}, overlap={len(overlap)}")

    # ================================================================
    # PCA variance explained
    # ================================================================
    print(f"\n  --- PCA Variance Explained ---")
    for key in sorted(all_results.keys()):
        if not key.startswith("PCA"): continue
        for wname in ["W1", "W2"]:
            ve = all_results[key].get(wname, {}).get("var_explained")
            if ve:
                cumve = sum(ve)
                print(f"  {key} {wname}: {[f'{v:.3f}' for v in ve]} (cum={cumve:.3f})")

    # ================================================================
    # Correlation with XSMom (W2 OOS)
    # ================================================================
    print(f"\n  --- Correlation with XSMom (W2 OOS = 2024) ---")
    xsmom_dfs = {}
    for coin in ALL_28:
        df = load_freq(cache, coin, "8h", "2023-06-01", "2025-01-01")
        if df is not None: xsmom_dfs[coin] = df
    r_xs = run_xsmom(xsmom_dfs, 36, 5, 21, False, capital=10000.0)

    corr_results = {}
    if r_xs:
        xs_rets = pd.Series(r_xs["equities"]).pct_change().dropna().values
        for skey, eq in w2_equities.items():
            s_rets = pd.Series(eq).pct_change().dropna().values
            ml = min(len(xs_rets), len(s_rets))
            if ml > 20 and np.std(s_rets[:ml]) > 0 and np.std(xs_rets[:ml]) > 0:
                corr = float(np.corrcoef(xs_rets[:ml], s_rets[:ml])[0, 1])
                corr_results[skey] = corr
                print(f"  {skey} vs XSMom: {corr:.3f}")
            else:
                print(f"  {skey} vs XSMom: N/A (insufficient data)")

    # ================================================================
    # Part 4: Combo tests (W2 OOS, strategies with positive Sharpe)
    # ================================================================
    print(f"\n{'='*70}")
    print("Part 4: Combo with XSMom (W2 OOS)")
    print(f"{'='*70}")

    if r_xs:
        xs_eq = r_xs["equities"]
        xs_r = xs_eq / xs_eq[0]

        print(f"\n  {'Combo':<40} {'Sharpe':>8} {'Ret%':>8} {'MaxDD%':>8}")
        print("  " + "-" * 66)

        for skey, eq in w2_equities.items():
            w2sr = all_results[skey].get("W2", {}).get("oos_sharpe")
            if w2sr is None or w2sr <= 0: continue

            s_r = eq / eq[0]
            ml = min(len(xs_r), len(s_r))

            # 50/50
            combo50 = (0.5 * s_r[:ml] + 0.5 * xs_r[:ml]) * 10000
            eq_s = pd.Series(combo50)
            sr50 = sharpe_ratio(eq_s, PPY_MAP.get(skey.split("_")[-1], 1096))
            _, dd50 = max_drawdown(eq_s)
            ret50 = (combo50[-1] / combo50[0] - 1) * 100

            print(f"  {skey}+XSMom 50/50{'':<20} {sr50:>8.3f} {ret50:>8.2f} {dd50:>8.2f}")

            # 33/33/33 with Z-score MR (use MR equity from w2_equities if available)
            # Skip if no MR equity available

    # ================================================================
    # Save
    # ================================================================
    save = {}
    for k, v in all_results.items():
        save[k] = {}
        for w, wr in v.items():
            save[k][w] = {kk: vv for kk, vv in wr.items() if kk != "equities"}
    save["correlations"] = corr_results
    save["pair_info"] = {k: [dict(p) for p in v[:10]] for k, v in all_pair_info.items() if v}

    Path("sweep_results").mkdir(exist_ok=True)
    with open("sweep_results/advanced_coint.json", "w") as f:
        json.dump(save, f, indent=2, default=str)

    # RESEARCH_LOG
    log = f"\n## Advanced Cointegration + Avellaneda-Lee PCA ({pd.Timestamp.now().strftime('%Y-%m-%d')})\n\n"
    log += "### Part 3: Full Comparison\n"
    log += "| Strategy | Timeframe | W1 Params | W1 OOS SR | W2 Params | W2 OOS SR | Match | Pairs |\n"
    log += "|----------|-----------|-----------|-----------|-----------|-----------|-------|-------|\n"
    for key in sorted(all_results.keys()):
        r = all_results[key]
        parts = key.split("_"); strat = parts[0]; tf = parts[1]
        w1 = r.get("W1", {}); w2 = r.get("W2", {})
        p1 = str(w1.get("best_params", []))[:18]
        p2 = str(w2.get("best_params", []))[:18]
        match = "YES" if w1.get("best_params") == w2.get("best_params") else "NO"
        np_ = w2.get("n_pairs", w2.get("n_trades", ""))
        log += (f"| {strat} | {tf} | {p1} | {fmt(w1.get('oos_sharpe'))} | "
                f"{p2} | {fmt(w2.get('oos_sharpe'))} | {match} | {np_} |\n")

    # Pair stability
    log += "\n### Pair Stability (triple-filter)\n"
    for freq in timeframes:
        is_p = all_pair_info.get(f"Coint_{freq}_W1", [])
        oos_p = all_pair_info.get(f"Coint_{freq}_W2", [])
        is_s = set((p["a"], p["b"]) for p in is_p) if is_p else set()
        oos_s = set((p["a"], p["b"]) for p in oos_p) if oos_p else set()
        log += f"- {freq}: W1={len(is_s)} pairs, W2={len(oos_s)} pairs, overlap={len(is_s & oos_s)}\n"

    # PCA variance
    log += "\n### PCA Variance Explained\n"
    for key in sorted(all_results.keys()):
        if not key.startswith("PCA"): continue
        ve = all_results[key].get("W2", {}).get("var_explained")
        if ve:
            log += f"- {key}: {[f'{v:.3f}' for v in ve]} (cum={sum(ve):.3f})\n"

    # Correlations
    log += "\n### Correlation with XSMom\n"
    for skey, corr in corr_results.items():
        log += f"- {skey}: {corr:.3f}\n"

    with open("RESEARCH_LOG.md", "a", encoding="utf-8") as f:
        f.write(log)

    print(f"\n  Total: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
