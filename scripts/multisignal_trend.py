#!/usr/bin/env python3
"""Multi-signal trend strategy: TSMOM + MA crossover + Donchian composite.

9 sub-signals (3 signal types x 3 lookbacks), equal-weight averaged.
Optional 1D trend filter. Vol-targeting position sizing.
Rolling walk-forward: W1 (IS 2021-2022, OOS 2023) + W2 (IS 2022-2023, OOS 2024).
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
from scripts.mean_reversion_experiment import compute_dynamic_slippage

ALL_28 = ["BTC","ETH","LTC","TRX","BCH","DOT","ADA","LINK","XLM","XRP",
          "ETC","ALGO","ATOM","AAVE","SOL","ICP","UNI","FIL","AVAX","NEAR",
          "CRV","DOGE","AXS","YGG","CELO","GALA","SAND","PEOPLE"]

FEE_BPS = 3.5

SIGNAL_SETS = {
    "8h": {
        "A": {
            "tsmom": [90, 375, 750],
            "ma": [(60,180), (180,540), (375,1125)],
            "donchian": [60, 180, 375],
        },
        "B": {
            "tsmom": [60, 240, 960],
            "ma": [(48,144), (144,432), (480,1440)],
            "donchian": [90, 270, 540],
        },
    },
    "1h": {
        "A": {
            "tsmom": [270, 1125, 2250],
            "ma": [(180,540), (540,1620), (1125,3375)],
            "donchian": [180, 540, 1125],
        },
        "B": {
            "tsmom": [180, 720, 2880],
            "ma": [(144,432), (432,1296), (1440,4320)],
            "donchian": [270, 810, 1620],
        },
    },
}

WINDOWS = [
    {"name": "W1", "is_start": "2021-01-01", "is_end": "2023-01-01",
     "oos_start": "2023-01-01", "oos_end": "2024-01-01"},
    {"name": "W2", "is_start": "2022-01-01", "is_end": "2024-01-01",
     "oos_start": "2024-01-01", "oos_end": "2025-01-01"},
]


def load_data(cache, coin, freq, start, end):
    df = cache.read("okx", coin, "1h")
    if df is None or df.empty:
        return None
    if df["timestamp"].dt.tz is not None:
        df["timestamp"] = df["timestamp"].dt.tz_localize(None)
    if freq != "1h":
        df = resample_ohlcv(df, freq)
    mask = (df["timestamp"] >= pd.Timestamp(start)) & (df["timestamp"] < pd.Timestamp(end))
    out = df[mask].reset_index(drop=True)
    return out if len(out) > 50 else None


def compute_signals(closes, signal_set):
    """Compute 9 sub-signals, each in [-1, +1]."""
    n = len(closes)
    signals = np.full((n, 9), np.nan)
    cs = pd.Series(closes)

    for si, lb in enumerate(signal_set["tsmom"]):
        ret = cs / cs.shift(lb) - 1
        signals[:, si] = np.tanh(ret.values * 5)

    for si, (fast, slow) in enumerate(signal_set["ma"]):
        ma_f = cs.rolling(fast, min_periods=fast).mean()
        ma_s = cs.rolling(slow, min_periods=slow).mean()
        diff = (ma_f - ma_s) / ma_s
        signals[:, 3 + si] = np.tanh(diff.values * 20)

    for si, lb in enumerate(signal_set["donchian"]):
        upper = cs.rolling(lb, min_periods=lb).max().shift(1)
        lower = cs.rolling(lb, min_periods=lb).min().shift(1)
        mid = (upper + lower) / 2
        width = upper - lower
        pos = np.where(width > 0, (cs - mid) / (width / 2), 0)
        signals[:, 6 + si] = np.clip(pos, -1, 1)

    return signals


def compute_1d_filter(closes, freq):
    """30-day trend filter. Returns array of +1/-1/0."""
    lb = 720 if freq == "1h" else 90  # 30 days in bars
    cs = pd.Series(closes)
    ret = cs / cs.shift(lb) - 1
    return np.nan_to_num(np.sign(ret.values), nan=0.0)


def run_multisignal(coin_dfs, signal_set, freq, entry_thresh, target_vol,
                    use_1d_filter=False, capital=10000.0, leverage=3.0,
                    is_start=None, trading_start=None):
    """Run multi-signal trend on all coins.

    is_start: if set, only count equity from this timestamp onward
    trading_start: if set, only generate signals from this timestamp
    """
    coins = list(coin_dfs.keys())
    n_coins = len(coins)
    if n_coins < 5:
        return None

    ppy = 1096 if freq == "8h" else 8766
    vol_window = 60 if freq == "8h" else 480
    fee_rate = FEE_BPS / 10_000
    per_coin = capital / n_coins

    all_eqs = []
    total_trades = 0
    total_wins = 0
    total_closed = 0

    for coin in coins:
        df = coin_dfs[coin]
        n = len(df)
        closes = df["close"].values
        opens = df["open"].values
        volumes = df["volume"].values

        sigs = compute_signals(closes, signal_set)
        composite = np.nanmean(sigs, axis=1)

        if use_1d_filter:
            filt = compute_1d_filter(closes, freq)
        else:
            filt = np.ones(n)

        rets = np.zeros(n)
        rets[1:] = closes[1:] / closes[:-1] - 1
        roll_vol = pd.Series(rets).rolling(vol_window, min_periods=max(20, vol_window//3)).std().values
        ann_vol = roll_vol * np.sqrt(ppy)

        vol_usd = volumes * closes
        adv = pd.Series(vol_usd).rolling(max(60, vol_window), min_periods=3).sum().values / 20

        # Find warmup end
        warmup = 0
        for i in range(n):
            if not np.isnan(composite[i]):
                warmup = i
                break

        # If trading_start specified, find that bar index
        trade_start_idx = warmup + 1
        if trading_start is not None:
            ts_arr = df["timestamp"].values
            for i in range(n):
                if ts_arr[i] >= np.datetime64(trading_start):
                    trade_start_idx = max(trade_start_idx, i)
                    break

        equity = per_coin
        cash = equity
        pos = 0.0
        entry_px = 0.0
        peak = equity
        equities = np.full(n, equity)
        n_tr = 0; wins = 0; closed_c = 0
        prev_target = 0.0

        for i in range(warmup + 1, n):
            o = opens[i]; c = closes[i]
            sig = composite[i - 1]

            # Execute
            trade_size = abs(prev_target - pos)
            if trade_size > max(5.0, abs(prev_target) * 0.03):
                fee = trade_size * fee_rate
                slip = compute_dynamic_slippage(trade_size, adv[i] if not np.isnan(adv[i]) else 1e9)
                if abs(pos) > 0.01 and entry_px > 0:
                    pnl = abs(pos) * ((o - entry_px) / entry_px if pos > 0 else (entry_px - o) / entry_px)
                    cash += pnl
                    if pnl > 0: wins += 1
                    closed_c += 1
                cash -= fee + slip
                n_tr += 1
                pos = prev_target
                entry_px = o if abs(pos) > 0.01 else 0.0

            unrealized = 0.0
            if abs(pos) > 0.01 and entry_px > 0:
                unrealized = abs(pos) * ((c - entry_px) / entry_px if pos > 0 else (entry_px - c) / entry_px)
            equity = cash + unrealized
            peak = max(peak, equity)
            equities[i] = equity

            # Only generate new signals after trade_start_idx
            if i < trade_start_idx:
                continue

            if np.isnan(sig):
                prev_target = 0.0
                continue

            d_filt = filt[i - 1]
            av = ann_vol[i - 1] if not np.isnan(ann_vol[i - 1]) and ann_vol[i - 1] > 0 else 1.0
            vol_sc = min(2.0, max(0.25, target_vol / av))
            dd = max(0, 1.0 - equity / peak)
            dd_sc = 1.0 - min(dd / 0.30, 1.0) * 0.75 if dd > 0 else 1.0
            max_pos = equity * leverage

            if sig > entry_thresh:
                if use_1d_filter and d_filt < 0:
                    prev_target = 0.0
                else:
                    prev_target = min(equity * leverage * vol_sc * dd_sc * abs(sig), max_pos)
            elif sig < -entry_thresh:
                if use_1d_filter and d_filt > 0:
                    prev_target = 0.0
                else:
                    prev_target = -min(equity * leverage * vol_sc * dd_sc * abs(sig), max_pos)
            elif abs(sig) < 0.1:
                prev_target = 0.0

        # Extract from trading_start onward
        if trading_start is not None:
            eq_slice = equities[trade_start_idx:]
        else:
            eq_slice = equities[warmup:]

        all_eqs.append(eq_slice)
        total_trades += n_tr
        total_wins += wins
        total_closed += closed_c

    if not all_eqs:
        return None

    min_len = min(len(e) for e in all_eqs)
    port_eq = sum(e[:min_len] for e in all_eqs)

    # Normalize to start at capital
    port_eq = port_eq / port_eq[0] * capital

    eq_s = pd.Series(port_eq)
    sr = sharpe_ratio(eq_s, ppy)
    _, dd_pct = max_drawdown(eq_s)
    ret = (port_eq[-1] / port_eq[0] - 1) * 100

    return {
        "sharpe": sr, "return_pct": ret, "max_dd_pct": dd_pct,
        "n_trades": total_trades,
        "win_rate": total_wins / total_closed * 100 if total_closed > 0 else 0,
        "equities": port_eq,
    }


def run_walk_forward(cache, freq, use_1d_filter, param_grid):
    """Run W1+W2 for one config. Returns per-window results."""
    results = {}

    for w in WINDOWS:
        print(f"    {w['name']}: IS {w['is_start']}~{w['is_end']}, OOS {w['oos_start']}~{w['oos_end']}")

        # Load data from earliest available through IS end / OOS end
        # Warmup is built into the data (pre-IS bars)
        is_dfs = {}
        for coin in ALL_28:
            df = load_data(cache, coin, freq, "2019-01-01", w["is_end"])
            if df is not None and len(df) > 100:
                is_dfs[coin] = df

        oos_dfs = {}
        for coin in ALL_28:
            df = load_data(cache, coin, freq, "2019-01-01", w["oos_end"])
            if df is not None and len(df) > 100:
                oos_dfs[coin] = df

        print(f"      IS coins: {len(is_dfs)}, OOS coins: {len(oos_dfs)}")

        # Sweep on IS
        is_results = []
        for pi, (sig_set_name, thresh, tvol) in enumerate(param_grid):
            sig_set = SIGNAL_SETS[freq][sig_set_name]
            r = run_multisignal(is_dfs, sig_set, freq, thresh, tvol,
                                use_1d_filter,
                                trading_start=w["is_start"])
            is_sr = r["sharpe"] if r and not np.isnan(r["sharpe"]) else -999
            is_results.append((sig_set_name, thresh, tvol, is_sr,
                               r["return_pct"] if r else 0, r["n_trades"] if r else 0))
            if (pi + 1) % 6 == 0:
                print(f"      IS: {pi+1}/{len(param_grid)}", flush=True)

        # Best from IS
        positive = [x for x in is_results if x[3] > 0]
        best = max(positive if positive else is_results, key=lambda x: x[3])
        best_set, best_thresh, best_tvol, best_is_sr, best_is_ret, best_is_tr = best
        print(f"      Best IS: Set={best_set} thresh={best_thresh} tvol={best_tvol} "
              f"SR={best_is_sr:.3f} Ret={best_is_ret:.2f}% Tr={best_is_tr}")

        # Run best on OOS
        sig_set = SIGNAL_SETS[freq][best_set]
        r_oos = run_multisignal(oos_dfs, sig_set, freq, best_thresh, best_tvol,
                                use_1d_filter,
                                trading_start=w["oos_start"])
        oos_sr = r_oos["sharpe"] if r_oos else None
        oos_ret = r_oos["return_pct"] if r_oos else None
        oos_tr = r_oos["n_trades"] if r_oos else 0
        print(f"      OOS: SR={oos_sr:.3f} Ret={oos_ret:.2f}% Tr={oos_tr}" if oos_sr else "      OOS: failed")

        results[w["name"]] = {
            "best_params": {"set": best_set, "thresh": best_thresh, "tvol": best_tvol},
            "is_sharpe": best_is_sr, "is_return": best_is_ret,
            "oos_sharpe": oos_sr, "oos_return": oos_ret, "oos_trades": oos_tr,
            "all_is": [(s, t, v, float(sr)) for s, t, v, sr, _, _ in is_results],
        }

    return results


def main():
    t0 = time.time()
    cache = ParquetCache()

    param_grid = list(product(
        ["A", "B"],
        [0.2, 0.3, 0.5],
        [0.10, 0.15, 0.20],
    ))
    print(f"Params per config: {len(param_grid)}")

    configs = [
        ("8H pure", "8h", False),
        ("8H + 1D filter", "8h", True),
        ("1H pure", "1h", False),
        ("1H + 1D filter", "1h", True),
    ]

    all_results = {}
    for cfg_name, freq, use_filter in configs:
        print(f"\n{'='*60}")
        print(f"Config: {cfg_name}")
        print(f"{'='*60}")
        wf = run_walk_forward(cache, freq, use_filter, param_grid)
        all_results[cfg_name] = wf

    # Summary
    print(f"\n{'='*70}")
    print("Part 2 Summary")
    print(f"{'='*70}")
    print(f"\n  {'Config':<18} {'W1 params':>15} {'W1 OOS SR':>10} {'W2 params':>15} {'W2 OOS SR':>10} {'Match':>6}")
    print("  " + "-" * 77)

    for cfg_name in [c[0] for c in configs]:
        r = all_results[cfg_name]
        w1 = r.get("W1", {}); w2 = r.get("W2", {})
        p1 = w1.get("best_params", {}); p2 = w2.get("best_params", {})
        s1 = w1.get("oos_sharpe"); s2 = w2.get("oos_sharpe")
        p1s = f"{p1.get('set','?')}/{p1.get('thresh','?')}/{p1.get('tvol','?')}"
        p2s = f"{p2.get('set','?')}/{p2.get('thresh','?')}/{p2.get('tvol','?')}"
        match = "YES" if p1 == p2 else "NO"
        print(f"  {cfg_name:<18} {p1s:>15} {s1:>10.3f} {p2s:>15} {s2:>10.3f} {match:>6}"
              if s1 and s2 else f"  {cfg_name:<18} --- --- ---")

    # Save
    save = {}
    for cfg, r in all_results.items():
        save[cfg] = {w: {k: v for k, v in wr.items() if k != "equities"}
                     for w, wr in r.items()}
    Path("sweep_results").mkdir(exist_ok=True)
    with open("sweep_results/multisignal_wf.json", "w") as f:
        json.dump(save, f, indent=2, default=str)

    log = f"\n## Multi-Signal Trend Walk-Forward ({pd.Timestamp.now().strftime('%Y-%m-%d')})\n\n"
    log += "### Part 2: Frequency x Filter\n"
    log += "| Config | W1 Params | W1 IS SR | W1 OOS SR | W2 Params | W2 IS SR | W2 OOS SR | Match |\n"
    log += "|--------|-----------|----------|-----------|-----------|----------|-----------|-------|\n"
    for cfg_name in [c[0] for c in configs]:
        r = all_results[cfg_name]
        w1 = r.get("W1", {}); w2 = r.get("W2", {})
        p1 = w1.get("best_params", {}); p2 = w2.get("best_params", {})
        p1s = f"{p1.get('set','?')}/{p1.get('thresh','?')}/{p1.get('tvol','?')}"
        p2s = f"{p2.get('set','?')}/{p2.get('thresh','?')}/{p2.get('tvol','?')}"
        match = "YES" if p1 == p2 else "NO"
        log += (f"| {cfg_name} | {p1s} | {w1.get('is_sharpe',0):.3f} | "
                f"{w1.get('oos_sharpe',0):.3f} | {p2s} | {w2.get('is_sharpe',0):.3f} | "
                f"{w2.get('oos_sharpe',0):.3f} | {match} |\n")
    with open("RESEARCH_LOG.md", "a", encoding="utf-8") as f:
        f.write(log)

    print(f"\n  Total: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
