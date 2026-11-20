#!/usr/bin/env python3
"""Cross-Sectional Momentum strategy experiment.

Long top-K performers, short bottom-K performers, rebalance periodically.
Market-neutral by construction (long = short notional).
"""

import sys, os, time, json
from pathlib import Path
from itertools import product
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptolab.data.cache import ParquetCache
from cryptolab.backtest.metrics import sharpe_ratio, max_drawdown
from scripts.donchian_full_sweep import resample_ohlcv
from scripts.mean_reversion_experiment import compute_dynamic_slippage, PPY_8H, FEE_BPS

ALL_28 = ["BTC","ETH","LTC","TRX","BCH","DOT","ADA","LINK","XLM","XRP",
          "ETC","ALGO","ATOM","AAVE","SOL","ICP","UNI","FIL","AVAX","NEAR",
          "CRV","DOGE","AXS","YGG","CELO","GALA","SAND","PEOPLE"]

WINDOWS = [
    {"name": "W1", "is_start": "2021-01-01", "is_end": "2022-07-01",
     "val_start": "2022-07-01", "val_end": "2023-07-01"},
    {"name": "W2", "is_start": "2021-01-01", "is_end": "2023-07-01",
     "val_start": "2023-07-01", "val_end": "2024-07-01"},
    {"name": "W3", "is_start": "2021-01-01", "is_end": "2024-07-01",
     "val_start": "2024-07-01", "val_end": "2025-07-01"},
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


def run_xsmom(coin_dfs, lookback, top_k, rebal_bars, weighted=False,
              capital=10000.0):
    """Run cross-sectional momentum on multiple coins.

    Args:
        coin_dfs: dict {coin: DataFrame} with aligned timestamps
        lookback: bars to compute return ranking
        top_k: number of coins to long/short (int or float for pct)
        rebal_bars: rebalance every N bars
        weighted: if True, weight by return magnitude
        capital: total capital

    Returns dict with metrics.
    """
    coins = list(coin_dfs.keys())
    n_coins = len(coins)
    if n_coins < 6:
        return None

    # Build aligned price matrix
    # Find common timestamps
    all_ts = None
    for coin, df in coin_dfs.items():
        ts = set(df["timestamp"].values)
        all_ts = ts if all_ts is None else all_ts & ts
    if not all_ts or len(all_ts) < lookback + 50:
        return None

    common_ts = sorted(all_ts)
    n_bars = len(common_ts)

    # Price matrix: [n_bars, n_coins]
    prices = np.zeros((n_bars, n_coins))
    volumes = np.zeros((n_bars, n_coins))
    for ci, coin in enumerate(coins):
        df = coin_dfs[coin]
        ts_map = {t: i for i, t in enumerate(df["timestamp"].values)}
        for ti, t in enumerate(common_ts):
            idx = ts_map.get(t)
            if idx is not None:
                prices[ti, ci] = df.iloc[idx]["close"]
                volumes[ti, ci] = df.iloc[idx]["volume"] * df.iloc[idx]["close"]

    # Compute returns
    returns = np.zeros((n_bars, n_coins))
    for i in range(1, n_bars):
        for ci in range(n_coins):
            if prices[i-1, ci] > 0:
                returns[i, ci] = prices[i, ci] / prices[i-1, ci] - 1

    # ADV for slippage
    adv = pd.DataFrame(volumes).rolling(60, min_periods=3).sum().values / 20

    # Determine K
    if isinstance(top_k, float) and top_k < 1:
        k = max(1, int(n_coins * top_k))
    else:
        k = int(top_k)
    k = min(k, n_coins // 2 - 1)  # can't long/short more than half
    if k < 1:
        return None

    fee_rate = FEE_BPS / 10_000
    equity = capital; cash = equity
    peak = equity
    equities = np.full(n_bars, equity)
    positions = np.zeros(n_coins)  # signed USD per coin
    entry_prices = np.zeros(n_coins)
    n_trades = 0; wins = 0; closed_c = 0

    warmup = lookback + 10
    per_side_capital = capital * 1.5  # 3x leverage, split long/short

    for i in range(warmup, n_bars):
        # Mark-to-market
        for ci in range(n_coins):
            if abs(positions[ci]) > 0.01 and entry_prices[ci] > 0 and prices[i, ci] > 0:
                pass  # unrealized computed below

        unrealized = 0.0
        for ci in range(n_coins):
            if abs(positions[ci]) > 0.01 and entry_prices[ci] > 0 and prices[i, ci] > 0:
                if positions[ci] > 0:
                    unrealized += abs(positions[ci]) * (prices[i, ci] - entry_prices[ci]) / entry_prices[ci]
                else:
                    unrealized += abs(positions[ci]) * (entry_prices[ci] - prices[i, ci]) / entry_prices[ci]
        equity = cash + unrealized
        peak = max(peak, equity)
        equities[i] = equity

        # Rebalance check
        if (i - warmup) % rebal_bars != 0:
            continue

        # Compute lookback returns for ranking
        cum_rets = np.zeros(n_coins)
        valid_mask = np.ones(n_coins, dtype=bool)
        for ci in range(n_coins):
            if prices[i, ci] > 0 and prices[max(0, i - lookback), ci] > 0:
                cum_rets[ci] = prices[i, ci] / prices[max(0, i - lookback), ci] - 1
            else:
                valid_mask[ci] = False

        n_valid = valid_mask.sum()
        if n_valid < 2 * k + 2:
            continue

        # Check dispersion (skip if returns too similar)
        valid_rets = cum_rets[valid_mask]
        if np.std(valid_rets) < 0.001:
            continue

        # Rank: highest return = rank 0 (long), lowest = rank n-1 (short)
        ranked_indices = np.argsort(-cum_rets)  # descending
        valid_ranked = [ci for ci in ranked_indices if valid_mask[ci]]

        long_coins = valid_ranked[:k]
        short_coins = valid_ranked[-k:]

        # DD scaling
        dd = max(0, 1.0 - equity / peak)
        dd_sc = 1.0 - min(dd / 0.30, 1.0) * 0.75 if dd > 0 else 1.0

        # Compute target positions
        new_positions = np.zeros(n_coins)
        per_coin_usd = (equity * 3.0 * dd_sc) / (2 * k)  # split across long+short
        max_per_coin = equity * 0.15  # 15% cap
        per_coin_usd = min(per_coin_usd, max_per_coin)

        if weighted:
            # Weight by distance from median return
            median_ret = np.median(valid_rets)
            for ci in long_coins:
                w = max(0.1, abs(cum_rets[ci] - median_ret))
                new_positions[ci] = per_coin_usd * w / max(0.01, sum(
                    max(0.1, abs(cum_rets[c] - median_ret)) for c in long_coins)) * k
            for ci in short_coins:
                w = max(0.1, abs(cum_rets[ci] - median_ret))
                new_positions[ci] = -per_coin_usd * w / max(0.01, sum(
                    max(0.1, abs(cum_rets[c] - median_ret)) for c in short_coins)) * k
        else:
            for ci in long_coins:
                new_positions[ci] = per_coin_usd
            for ci in short_coins:
                new_positions[ci] = -per_coin_usd

        # Execute trades
        for ci in range(n_coins):
            delta = new_positions[ci] - positions[ci]
            if abs(delta) < max(5.0, abs(new_positions[ci]) * 0.03):
                continue

            trade_usd = abs(delta)
            fee = trade_usd * fee_rate
            adv_val = adv[i, ci] if i < len(adv) and not np.isnan(adv[i, ci]) else 1e9
            slip = compute_dynamic_slippage(trade_usd, adv_val)

            # Close old position PnL
            if abs(positions[ci]) > 0.01 and entry_prices[ci] > 0 and prices[i, ci] > 0:
                if positions[ci] > 0:
                    pnl = abs(positions[ci]) * (prices[i, ci] - entry_prices[ci]) / entry_prices[ci]
                else:
                    pnl = abs(positions[ci]) * (entry_prices[ci] - prices[i, ci]) / entry_prices[ci]
                cash += pnl
                if pnl > 0: wins += 1
                closed_c += 1

            cash -= fee + slip
            n_trades += 1
            positions[ci] = new_positions[ci]
            entry_prices[ci] = prices[i, ci] if abs(new_positions[ci]) > 0.01 else 0

    # Final equity
    unrealized = 0.0
    for ci in range(n_coins):
        if abs(positions[ci]) > 0.01 and entry_prices[ci] > 0 and prices[-1, ci] > 0:
            if positions[ci] > 0:
                unrealized += abs(positions[ci]) * (prices[-1, ci] - entry_prices[ci]) / entry_prices[ci]
            else:
                unrealized += abs(positions[ci]) * (entry_prices[ci] - prices[-1, ci]) / entry_prices[ci]
    equity = cash + unrealized
    equities[-1] = equity

    eq = pd.Series(equities[warmup:])
    if len(eq) < 10: return None
    sr = sharpe_ratio(eq, PPY_8H); _, dd_pct = max_drawdown(eq)

    # Net exposure check
    net_exp = sum(positions)
    gross_exp = sum(abs(p) for p in positions)

    # Beta to BTC
    btc_idx = coins.index("BTC") if "BTC" in coins else 0
    strat_rets = eq.pct_change().dropna().values
    btc_rets = pd.Series(prices[warmup:, btc_idx]).pct_change().dropna().values
    ml = min(len(strat_rets), len(btc_rets))
    if ml > 10 and np.std(btc_rets[:ml]) > 0:
        beta = np.cov(strat_rets[:ml], btc_rets[:ml])[0, 1] / np.var(btc_rets[:ml])
    else:
        beta = None

    return {
        "sharpe": sr,
        "return_pct": (float(eq.iloc[-1]) - capital) / capital * 100,
        "max_dd_pct": dd_pct,
        "n_trades": n_trades,
        "win_rate": wins / closed_c * 100 if closed_c > 0 else 0,
        "net_exposure": net_exp,
        "beta_btc": beta,
        "equities": equities[warmup:].copy(),
    }


def main():
    t0 = time.time()
    cache = ParquetCache()

    # Load existing MR params
    with open("sweep_results/meanrev_experiment.json") as f:
        mr_params_all = json.load(f).get("meanrev_best_params", {})
    # Add new coins MR params
    if Path("sweep_results/expanded_coins_v3.json").exists():
        with open("sweep_results/expanded_coins_v3.json") as f:
            v3 = json.load(f)
        mr_params_all.update(v3.get("mr_params", {}))

    # Parameter grid
    lookbacks = [12, 24, 36, 48, 72, 96, 120, 168, 252]
    top_ks = [3, 5, 7]
    rebal_bars_list = [3, 9, 21, 42]
    weightings = [False, True]

    param_grid = list(product(lookbacks, top_ks, rebal_bars_list, weightings))
    print(f"Parameter combinations: {len(param_grid)}")

    # ==================================================================
    # Walk-Forward Sweep
    # ==================================================================
    print(f"\n{'='*70}")
    print("Cross-Sectional Momentum Walk-Forward Sweep")
    print("=" * 70)

    param_val_sharpes = {}

    for wi, w in enumerate(WINDOWS):
        print(f"\n  --- {w['name']}: val {w['val_start']} to {w['val_end']} ---")

        # Load IS data
        is_dfs = {}
        for coin in ALL_28:
            df = load_8h(cache, coin, w["is_start"], w["is_end"])
            if df is not None:
                is_dfs[coin] = df

        # Load val data
        val_dfs = {}
        for coin in ALL_28:
            df = load_8h(cache, coin, w["val_start"], w["val_end"])
            if df is not None:
                val_dfs[coin] = df

        print(f"  IS coins: {len(is_dfs)}, Val coins: {len(val_dfs)}")

        for pi, params in enumerate(param_grid):
            lb, k, rb, wt = params

            # IS
            r_is = run_xsmom(is_dfs, lb, k, rb, wt)
            if r_is is None or r_is["sharpe"] <= 0:
                param_val_sharpes.setdefault(params, []).append(None)
                continue

            # Validation
            r_val = run_xsmom(val_dfs, lb, k, rb, wt)
            val_sr = r_val["sharpe"] if r_val else None
            param_val_sharpes.setdefault(params, []).append(val_sr)

            if (pi + 1) % 20 == 0:
                print(f"    {pi+1}/{len(param_grid)} done...", flush=True)

    # Select best params
    best_param = None; best_score = -999
    for params, sharpes in param_val_sharpes.items():
        valid = [s for s in sharpes if s is not None]
        if len(valid) < 2: continue
        n_pos = sum(1 for s in valid if s > 0)
        avg = np.mean(valid)
        score = n_pos * 10 + avg
        if score > best_score:
            best_score = score; best_param = params

    if best_param:
        valid = [s for s in param_val_sharpes[best_param] if s is not None]
        lb, k, rb, wt = best_param
        print(f"\n  Best: lookback={lb}, K={k}, rebal={rb}bars, weighted={wt}")
        print(f"  Avg validation Sharpe: {np.mean(valid):.3f}")
        print(f"  Per-window: {[f'{s:.3f}' if s else 'N/A' for s in param_val_sharpes[best_param]]}")
    else:
        print("\n  No valid params found!")
        return

    # ==================================================================
    # Holdout
    # ==================================================================
    print(f"\n{'='*70}")
    print("Holdout (2025.07 - 2026.03)")
    print("=" * 70)

    ho_dfs = {}
    for coin in ALL_28:
        df = load_8h(cache, coin, "2025-07-01", "2026-04-01")
        if df is not None:
            ho_dfs[coin] = df
    print(f"  Holdout coins: {len(ho_dfs)}")

    # A) XS Momentum
    lb, k, rb, wt = best_param
    r_xsmom = run_xsmom(ho_dfs, lb, k, rb, wt)

    # B) Pure Donchian 28
    from scripts.mean_reversion_experiment import run_donchian_b0
    from scripts.portfolio_optimization import run_combo

    n_coins = len(ALL_28)
    CAPITAL = 10_000.0 / n_coins
    don_eqs = []
    don_trades = 0
    for coin in ALL_28:
        df = load_8h(cache, coin, "2025-07-01", "2026-04-01")
        if df is None: continue
        r = run_donchian_b0(df, CAPITAL, n_coins, use_dynamic_slip=True)
        if r and not np.isnan(r["sharpe"]):
            don_eqs.append(r["equities"])
            don_trades += r["n_trades"]

    min_len = min(len(e) for e in don_eqs) if don_eqs else 0

    # C-E) Combo portfolios using run_combo
    combo_results = {}
    for label, dw, mw, xw in [
        ("C) Don+XSMom 50/50", 0.5, 0.0, 0.5),
        ("D) Don+MR+XSMom 33%", 0.34, 0.33, 0.33),
        ("E) Don50+MR25+XSMom25", 0.50, 0.25, 0.25),
    ]:
        # For combos, we run Donchian+MR via run_combo, then add XSMom separately
        combo_eqs = []
        combo_trades = 0
        for coin in ALL_28:
            df = load_8h(cache, coin, "2025-07-01", "2026-04-01")
            if df is None: continue
            p = mr_params_all.get(coin)
            if p and len(p) >= 4:
                r = run_combo(df, p[0], p[1], 0.50, p[3], CAPITAL, n_coins,
                              leverage=3.0, don_weight=dw, mr_weight=mw)
            else:
                r = run_combo(df, 168, 2.0, 0.50, 3.5, CAPITAL, n_coins,
                              leverage=3.0, don_weight=dw + mw, mr_weight=0.0)
            if r and not np.isnan(r["sharpe"]):
                combo_eqs.append(r["equities"])
                combo_trades += r["n_trades"]

        if combo_eqs and r_xsmom:
            ml = min(min(len(e) for e in combo_eqs), len(r_xsmom["equities"]))
            dm_port = sum(e[:ml] for e in combo_eqs)
            xs_port = np.full(ml, 10000.0)  # XSMom baseline
            xs_port[:len(r_xsmom["equities"][:ml])] = r_xsmom["equities"][:ml]

            # Weighted combination: (1-xw) * DonchianMR + xw * XSMom
            combined = dm_port * (1 - xw) + xs_port * xw
            eq_s = pd.Series(combined)
            sr = sharpe_ratio(eq_s, PPY_8H)
            _, dd = max_drawdown(eq_s)
            ret = (combined[-1] / combined[0] - 1) * 100 if combined[0] > 0 else 0
            combo_results[label] = {
                "sharpe": sr, "return_pct": ret, "max_dd_pct": dd,
                "n_trades": combo_trades + (r_xsmom["n_trades"] if r_xsmom else 0),
            }

    # Build results table
    portfolios = {}

    # A) Pure Donchian
    if don_eqs:
        port_don = sum(e[:min_len] for e in don_eqs)
        eq_s = pd.Series(port_don)
        sr = sharpe_ratio(eq_s, PPY_8H); _, dd = max_drawdown(eq_s)
        ret = (port_don[-1] / port_don[0] - 1) * 100 if port_don[0] > 0 else 0
        portfolios["A) Donchian 28"] = {"sharpe": sr, "return_pct": ret,
                                         "max_dd_pct": dd, "n_trades": don_trades}

    # B) Pure XS Momentum
    if r_xsmom:
        portfolios["B) XS Momentum"] = {k: v for k, v in r_xsmom.items() if k != "equities"}

    portfolios.update(combo_results)

    # Print
    print(f"\n  {'Portfolio':<25} {'Sharpe':>8} {'Ret%':>8} {'MaxDD%':>8} {'Trades':>7}")
    print("  " + "-" * 58)
    for name in ["A) Donchian 28", "B) XS Momentum",
                  "C) Don+XSMom 50/50", "D) Don+MR+XSMom 33%", "E) Don50+MR25+XSMom25"]:
        p = portfolios.get(name)
        if p:
            print(f"  {name:<25} {p['sharpe']:>8.3f} {p['return_pct']:>8.2f} "
                  f"{p['max_dd_pct']:>8.2f} {p['n_trades']:>7}")

    # Market neutrality check
    if r_xsmom:
        print(f"\n  XS Momentum Analysis:")
        print(f"    Beta to BTC: {r_xsmom.get('beta_btc', 'N/A')}")
        print(f"    Final net exposure: ${r_xsmom.get('net_exposure', 0):.2f}")

    # Correlation matrix
    if r_xsmom and don_eqs:
        xs_rets = pd.Series(r_xsmom["equities"]).pct_change().dropna().values
        don_rets = pd.Series(port_don).pct_change().dropna().values
        ml = min(len(xs_rets), len(don_rets))
        if ml > 10 and np.std(xs_rets[:ml]) > 0 and np.std(don_rets[:ml]) > 0:
            corr = float(np.corrcoef(xs_rets[:ml], don_rets[:ml])[0, 1])
            print(f"    Correlation with Donchian: {corr:.3f}")

    # ==================================================================
    # Save + Log
    # ==================================================================
    save_data = {
        "best_params": {"lookback": best_param[0], "top_k": best_param[1],
                        "rebal_bars": best_param[2], "weighted": best_param[3]},
        "validation_sharpes": [s if s is not None else "null"
                               for s in param_val_sharpes.get(best_param, [])],
        "portfolios": portfolios,
        "xsmom_details": {k: v for k, v in r_xsmom.items() if k != "equities"} if r_xsmom else None,
    }
    with open("sweep_results/xsmom_experiment.json", "w") as f:
        json.dump(save_data, f, indent=2, default=str)

    log_entry = f"""
## Cross-Sectional Momentum Experiment ({pd.Timestamp.now().strftime('%Y-%m-%d')})

### Best Parameters
- Lookback: {best_param[0]} bars
- Top/Bottom K: {best_param[1]}
- Rebalance: every {best_param[2]} bars ({best_param[2]*8}h)
- Weighting: {'return-weighted' if best_param[3] else 'equal-weight'}
- Avg validation Sharpe: {np.mean([s for s in param_val_sharpes[best_param] if s is not None]):.3f}

### Holdout (28 coins, 50/50 Donchian+MR, exit_z=0.50)
| Portfolio | Sharpe | Return% | MaxDD% | Trades |
|-----------|--------|---------|--------|--------|
"""
    for name in ["A) Donchian 28", "B) XS Momentum",
                  "C) Don+XSMom 50/50", "D) Don+MR+XSMom 33%", "E) Don50+MR25+XSMom25"]:
        p = portfolios.get(name)
        if p:
            log_entry += f"| {name} | {p['sharpe']:.3f} | {p['return_pct']:.2f} | {p['max_dd_pct']:.2f} | {p['n_trades']} |\n"

    if r_xsmom:
        log_entry += f"""
### Market Neutrality
- Beta to BTC: {r_xsmom.get('beta_btc', 'N/A')}
- Net exposure: ${r_xsmom.get('net_exposure', 0):.2f}
"""

    with open("RESEARCH_LOG.md", "a", encoding="utf-8") as f:
        f.write(log_entry)

    print(f"\n  Total time: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
