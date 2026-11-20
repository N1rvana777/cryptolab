#!/usr/bin/env python3
"""Time-Series Momentum (TSMOM) experiment.

Part A: 24 crypto coins (1D from OKX cache)
Part B: 30 traditional assets (1D from Yahoo Finance)
Part C: Cross-asset portfolio comparison

Signal: cumulative return over N days → long if positive, short if negative
Two signal types: binary (±1) and continuous (standardized, capped ±1)
"""

import sys, os, time, json, logging, itertools
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptolab.backtest.metrics import sharpe_ratio, max_drawdown

logging.basicConfig(level=logging.WARNING)

CRYPTO_COINS = ["BTC","ETH","LTC","TRX","BCH","DOT","ADA","LINK","XLM","XRP",
                "ETC","ALGO","ATOM","AAVE","SOL","ICP","UNI","FIL","AVAX","NEAR",
                "SAND","CRV","MANA","DOGE"]

TRAD_TICKERS = {
    "Indices": ["SPY","QQQ","IWM","DIA"],
    "Commodities": ["GC=F","SI=F","CL=F","BZ=F","HG=F","NG=F","PL=F","PA=F"],
    "Forex": ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","NZDUSD=X","EURGBP=X","EURJPY=X"],
    "Bonds": ["TLT","IEF"],
    "Stocks": ["AAPL","MSFT","GOOGL","AMZN","NVDA","TSLA","META"],
}
ALL_TRAD = [t for ts in TRAD_TICKERS.values() for t in ts]
TRAD_CAT = {t: c for c, ts in TRAD_TICKERS.items() for t in ts}

LOOKBACKS = [5, 10, 15, 21, 42, 63, 84, 126, 168, 252]
SIGNAL_TYPES = ["binary", "continuous"]

CRYPTO_FEE = (5+3)/10_000
TRAD_FEE = (8+3)/10_000
PPY = 252

CRYPTO_WINDOWS = [
    {"name":"W1","is_end":"2022-07-01","val_start":"2022-07-01","val_end":"2023-07-01"},
    {"name":"W2","is_end":"2023-07-01","val_start":"2023-07-01","val_end":"2024-07-01"},
    {"name":"W3","is_end":"2024-07-01","val_start":"2024-07-01","val_end":"2025-07-01"},
]
CRYPTO_HOLDOUT = {"start":"2025-07-01","end":"2026-04-01"}

TRAD_WINDOWS = [
    {"name":"W1","is_end":"2018-01-01","val_start":"2018-01-01","val_end":"2019-01-01"},
    {"name":"W2","is_end":"2019-01-01","val_start":"2019-01-01","val_end":"2020-01-01"},
    {"name":"W3","is_end":"2020-01-01","val_start":"2020-01-01","val_end":"2021-01-01"},
    {"name":"W4","is_end":"2021-01-01","val_start":"2021-01-01","val_end":"2022-01-01"},
    {"name":"W5","is_end":"2022-01-01","val_start":"2022-01-01","val_end":"2023-01-01"},
]
TRAD_HOLDOUT = {"start":"2023-01-01","end":"2026-01-01"}


def run_tsmom_backtest(df, lookback, signal_type="binary", fee_rate=CRYPTO_FEE, capital=10000.0):
    """Run TSMOM backtest on daily OHLCV data."""
    n = len(df)
    if n < lookback + 20:
        return None

    closes = df["close"].values
    opens = df["open"].values

    # Cumulative return over lookback
    cum_ret = np.full(n, 0.0)
    for i in range(lookback, n):
        cum_ret[i] = closes[i] / closes[i-lookback] - 1

    # Rolling vol for continuous signal normalization
    ret = np.zeros(n)
    ret[1:] = closes[1:]/closes[:-1] - 1
    roll_vol = pd.Series(ret).rolling(lookback, min_periods=min(lookback, max(5, lookback//2))).std().values

    equity = capital
    cash = equity
    position_usd = 0.0
    entry_px = 0.0
    peak_equity = equity
    equities = np.full(n, equity)
    n_trades = 0
    wins = 0
    closed_trades = 0
    prev_target = 0.0
    start = lookback + 5

    for i in range(start, n):
        open_px = opens[i]
        close_px = closes[i]

        # Execute previous signal
        if abs(prev_target - position_usd) > max(5.0, abs(prev_target)*0.03):
            delta = abs(prev_target - position_usd)
            fee = delta * fee_rate
            if abs(position_usd) > 0.01 and entry_px > 0:
                pnl = abs(position_usd) * ((open_px-entry_px)/entry_px if position_usd > 0 else (entry_px-open_px)/entry_px)
                cash += pnl
                if pnl > 0: wins += 1
                closed_trades += 1
            cash -= fee
            n_trades += 1
            position_usd = prev_target
            entry_px = open_px if abs(position_usd) > 0.01 else 0.0

        # MTM
        unrealized = 0.0
        if abs(position_usd) > 0.01 and entry_px > 0:
            unrealized = abs(position_usd) * ((close_px-entry_px)/entry_px if position_usd > 0 else (entry_px-close_px)/entry_px)
        equity = cash + unrealized
        peak_equity = max(peak_equity, equity)
        equities[i] = equity

        # Generate signal
        cr = cum_ret[i]
        if signal_type == "binary":
            if cr > 0:
                signal = 1.0
            elif cr < 0:
                signal = -1.0
            else:
                signal = 0.0
        else:  # continuous
            vol = roll_vol[i] if not np.isnan(roll_vol[i]) and roll_vol[i] > 0 else 0.01
            raw_signal = cr / (vol * np.sqrt(lookback))
            signal = max(-1.0, min(1.0, raw_signal))

        # Position sizing: simple equal weight
        target_size = equity * abs(signal)
        direction = 1.0 if signal > 0 else (-1.0 if signal < 0 else 0.0)

        # DD scaling
        dd = max(0, 1.0-equity/peak_equity)
        dd_scalar = 1.0 - min(dd/0.30, 1.0) * 0.75 if dd > 0 else 1.0

        prev_target = direction * target_size * dd_scalar

    eq = pd.Series(equities[start:])
    if len(eq) < 10: return None
    sr = sharpe_ratio(eq, PPY)
    _, dd_pct = max_drawdown(eq)
    final = float(eq.iloc[-1])
    ret_pct = (final-capital)/capital*100
    wr = wins/closed_trades*100 if closed_trades > 0 else 0
    return {"sharpe": sr, "return_pct": ret_pct, "max_dd_pct": dd_pct,
            "n_trades": n_trades, "win_rate": wr}


def run_sweep(data, windows, holdout, fee_rate, label=""):
    """Run full TSMOM sweep for a set of assets."""
    all_params = [(lb, st) for lb in LOOKBACKS for st in SIGNAL_TYPES]
    asset_results = {}

    for ti, (ticker, df) in enumerate(data.items()):
        t0 = time.time()
        param_results = {}

        for wi, window in enumerate(windows):
            val_start = pd.Timestamp(window["val_start"])
            val_end = pd.Timestamp(window["val_end"])
            is_end = pd.Timestamp(window["is_end"])

            is_df = df[df.index < is_end].copy()
            val_df = df[(df.index >= val_start) & (df.index < val_end)].copy()

            # IS phase
            for lb, st in all_params:
                plabel = f"{lb}_{st}"
                m_is = run_tsmom_backtest(is_df, lb, st, fee_rate)
                if m_is and m_is["sharpe"] > 0:
                    if plabel not in param_results:
                        param_results[plabel] = {"lb": lb, "st": st, "windows": {}}
                    param_results[plabel]["windows"][f"{window['name']}_is"] = m_is["sharpe"]
                    # Val
                    m_val = run_tsmom_backtest(val_df, lb, st, fee_rate)
                    if m_val:
                        param_results[plabel]["windows"][f"{window['name']}_val"] = m_val["sharpe"]

        # Select best param
        best_label = None
        best_score = (-999, 999, -999)
        for plabel, entry in param_results.items():
            val_sharpes = [entry["windows"].get(f"{w['name']}_val", -99) for w in windows]
            valid = [s for s in val_sharpes if s != -99]
            if len(valid) < len(windows) // 2:
                continue
            n_pos = sum(1 for s in valid if s > 0)
            avg = np.mean(valid)
            std = np.std(valid)
            score = (n_pos, -std, avg)
            if score > best_score:
                best_score = score
                best_label = plabel

        if best_label:
            entry = param_results[best_label]
            val_sharpes = [entry["windows"].get(f"{w['name']}_val", 0) for w in windows]
            asset_results[ticker] = {
                "lb": entry["lb"], "st": entry["st"],
                "val_sharpes": val_sharpes,
                "avg_val_sharpe": np.mean(val_sharpes),
                "std_val_sharpe": np.std(val_sharpes),
                "n_positive": sum(1 for s in val_sharpes if s > 0),
            }

        elapsed = time.time() - t0
        status = f"Sharpe={asset_results[ticker]['avg_val_sharpe']:.3f} ({asset_results[ticker]['lb']}d {asset_results[ticker]['st'][:3]})" if ticker in asset_results else "NO PARAM"
        print(f"  [{ti+1}/{len(data)}] {ticker:<12s} {elapsed:.1f}s  {status}")

    # Holdout
    ho_start = pd.Timestamp(holdout["start"])
    ho_end = pd.Timestamp(holdout["end"])
    holdout_results = {}
    for ticker, r in asset_results.items():
        if r["avg_val_sharpe"] < -0.5:
            continue
        ho_df = data[ticker]
        ho_df = ho_df[(ho_df.index >= ho_start) & (ho_df.index < ho_end)].copy()
        if len(ho_df) < 50:
            continue
        m = run_tsmom_backtest(ho_df, r["lb"], r["st"], fee_rate)
        if m:
            holdout_results[ticker] = {**m, "lb": r["lb"], "st": r["st"],
                                        "val_avg": r["avg_val_sharpe"]}

    return asset_results, holdout_results


def main():
    # ── Part A: Crypto ──
    print(f"\n{'='*70}")
    print(f"  PART A: TSMOM on Crypto (24 coins)")
    print(f"{'='*70}")

    from cryptolab.data.manager import DataManager
    dm = DataManager()
    crypto_data = {}
    for sym in CRYPTO_COINS:
        df = dm.cache.read("okx", sym, "1h")
        if not df.empty:
            df = df.copy()
            df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
            daily = df.set_index("timestamp").resample("1D").agg(
                {"open":"first","high":"max","low":"min","close":"last","volume":"sum"}).dropna()
            crypto_data[sym] = daily
    print(f"  Loaded {len(crypto_data)} crypto coins")

    crypto_results, crypto_holdout = run_sweep(crypto_data, CRYPTO_WINDOWS, CRYPTO_HOLDOUT, CRYPTO_FEE, "crypto")

    # ── Part B: Traditional ──
    print(f"\n{'='*70}")
    print(f"  PART B: TSMOM on Traditional Assets (30)")
    print(f"{'='*70}")

    import yfinance as yf
    trad_data = {}
    for ticker in ALL_TRAD:
        try:
            df = yf.download(ticker, start="2014-06-01", end="2026-01-01", progress=False)
            if len(df) > 100:
                # Handle MultiIndex columns from newer yfinance
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [c[0].lower() for c in df.columns]
                else:
                    df.columns = [c.lower() for c in df.columns]
                trad_data[ticker] = df
        except:
            pass
    print(f"  Loaded {len(trad_data)} traditional assets")

    trad_results, trad_holdout = run_sweep(trad_data, TRAD_WINDOWS, TRAD_HOLDOUT, TRAD_FEE, "trad")

    # ── Summary ──
    print(f"\n{'='*70}")
    print(f"  TSMOM RESULTS SUMMARY")
    print(f"{'='*70}")

    print(f"\n  Crypto ({len(crypto_results)} assets with params):")
    print(f"  {'Coin':<10s} {'Lookback':>8s} {'Signal':>8s} {'AvgVal':>8s} {'Pos':>5s}")
    for t in sorted(crypto_results, key=lambda x: -crypto_results[x]["avg_val_sharpe"]):
        r = crypto_results[t]
        print(f"  {t:<10s} {r['lb']:>8d} {r['st'][:3]:>8s} {r['avg_val_sharpe']:>8.3f} {r['n_positive']:>3d}/{len(CRYPTO_WINDOWS)}")

    print(f"\n  Traditional ({len(trad_results)} assets with params):")
    print(f"  {'Ticker':<12s} {'Cat':<10s} {'Lookback':>8s} {'Signal':>8s} {'AvgVal':>8s} {'Pos':>5s}")
    for t in sorted(trad_results, key=lambda x: -trad_results[x]["avg_val_sharpe"]):
        r = trad_results[t]
        cat = TRAD_CAT.get(t, "?")
        print(f"  {t:<12s} {cat:<10s} {r['lb']:>8d} {r['st'][:3]:>8s} {r['avg_val_sharpe']:>8.3f} {r['n_positive']:>3d}/{len(TRAD_WINDOWS)}")

    # Holdout
    print(f"\n  Holdout Results:")
    if crypto_holdout:
        avg_cs = np.mean([m["sharpe"] for m in crypto_holdout.values()])
        print(f"    Crypto TSMOM ({len(crypto_holdout)} coins): avg Sharpe={avg_cs:.3f}")
        for t in sorted(crypto_holdout, key=lambda x: -crypto_holdout[x]["sharpe"]):
            m = crypto_holdout[t]
            print(f"      {t:<10s} Sharpe={m['sharpe']:>7.3f}  Ret={m['return_pct']:>+8.2f}%  (lb={m['lb']}, {m['st'][:3]})")

    if trad_holdout:
        avg_ts = np.mean([m["sharpe"] for m in trad_holdout.values()])
        print(f"    Trad TSMOM ({len(trad_holdout)} assets): avg Sharpe={avg_ts:.3f}")
        for t in sorted(trad_holdout, key=lambda x: -trad_holdout[x]["sharpe"]):
            m = trad_holdout[t]
            print(f"      {t:<12s} Sharpe={m['sharpe']:>7.3f}  Ret={m['return_pct']:>+8.2f}%  (lb={m['lb']}, {m['st'][:3]})")

    # Correlation matrix for mixed portfolio
    if crypto_holdout and trad_holdout:
        print(f"\n  Cross-Asset Correlation (Holdout daily returns):")
        ho_s = pd.Timestamp(TRAD_HOLDOUT["start"])
        ho_e = pd.Timestamp(TRAD_HOLDOUT["end"])
        returns = {}
        for t in crypto_holdout:
            if t in crypto_data:
                r = crypto_data[t]["close"].pct_change().dropna()
                r = r[(r.index >= ho_s) & (r.index < ho_e)]
                if len(r) > 50: returns[f"C:{t}"] = r
        for t in trad_holdout:
            if t in trad_data:
                r = trad_data[t]["close"].pct_change().dropna()
                r = r[(r.index >= ho_s) & (r.index < ho_e)]
                if len(r) > 50: returns[f"T:{t}"] = r

        if len(returns) > 2:
            rdf = pd.DataFrame(returns)
            corr = rdf.corr()
            # Avg crypto-crypto, trad-trad, crypto-trad
            cc = [corr.loc[a,b] for a in corr.columns if a.startswith("C:") for b in corr.columns if b.startswith("C:") and a!=b]
            tt = [corr.loc[a,b] for a in corr.columns if a.startswith("T:") for b in corr.columns if b.startswith("T:") and a!=b]
            ct = [corr.loc[a,b] for a in corr.columns if a.startswith("C:") for b in corr.columns if b.startswith("T:")]
            if cc: print(f"    Avg crypto-crypto correlation: {np.mean(cc):+.3f}")
            if tt: print(f"    Avg trad-trad correlation:     {np.mean(tt):+.3f}")
            if ct: print(f"    Avg crypto-trad correlation:   {np.mean(ct):+.3f}")

    # Save
    Path("sweep_results").mkdir(exist_ok=True)
    save = {
        "crypto_results": {t: {**r, "val_sharpes": [float(x) for x in r["val_sharpes"]]} for t,r in crypto_results.items()},
        "trad_results": {t: {**r, "val_sharpes": [float(x) for x in r["val_sharpes"]]} for t,r in trad_results.items()},
        "crypto_holdout": crypto_holdout,
        "trad_holdout": trad_holdout,
    }
    Path("sweep_results/tsmom_results.json").write_text(json.dumps(save, indent=2, default=str))
    print(f"\n  Results saved to sweep_results/tsmom_results.json")


if __name__ == "__main__":
    main()
