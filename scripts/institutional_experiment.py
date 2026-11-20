#!/usr/bin/env python3
"""Institutional prior-knowledge experiment: no parameter optimization.

Donchian variants (B0-B3) on 24 crypto coins.
TSMOM variants (C1-C2) on crypto + 30 traditional assets.
Mixed portfolios.
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

CRYPTO_COINS = ["BTC","ETH","LTC","TRX","BCH","DOT","ADA","LINK","XLM","XRP",
                "ETC","ALGO","ATOM","AAVE","SOL","ICP","UNI","FIL","AVAX","NEAR",
                "SAND","CRV","MANA","DOGE"]

TRAD_TICKERS = ["SPY","QQQ","IWM","DIA",
                "GC=F","SI=F","CL=F","BZ=F","HG=F","NG=F","PL=F","PA=F",
                "EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","NZDUSD=X","EURGBP=X","EURJPY=X",
                "TLT","IEF",
                "AAPL","MSFT","GOOGL","AMZN","NVDA","TSLA","META"]

PPY_8H = 1096
PPY_1D = 252
FEE_CRYPTO = (5+3)/10_000
FEE_TRAD = (8+3)/10_000

CRYPTO_WINDOWS = [
    {"name":"W1","val_start":"2022-07-01","val_end":"2023-07-01"},
    {"name":"W2","val_start":"2023-07-01","val_end":"2024-07-01"},
    {"name":"W3","val_start":"2024-07-01","val_end":"2025-07-01"},
]
CRYPTO_HOLDOUT = {"start":"2025-07-01","end":"2026-04-01"}

TRAD_WINDOWS = [
    {"name":"W1","val_start":"2018-01-01","val_end":"2019-01-01"},
    {"name":"W2","val_start":"2019-01-01","val_end":"2020-01-01"},
    {"name":"W3","val_start":"2020-01-01","val_end":"2021-01-01"},
    {"name":"W4","val_start":"2021-01-01","val_end":"2022-01-01"},
    {"name":"W5","val_start":"2022-01-01","val_end":"2023-01-01"},
]
TRAD_HOLDOUT = {"start":"2023-01-01","end":"2026-01-01"}


def compute_adx(highs, lows, closes, period=20):
    n = len(highs)
    adx = np.full(n, np.nan)
    if n < period*2: return adx
    tr = np.zeros(n); pdm = np.zeros(n); mdm = np.zeros(n)
    for i in range(1, n):
        h_d = highs[i]-highs[i-1]; l_d = lows[i-1]-lows[i]
        tr[i] = max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1]))
        pdm[i] = h_d if (h_d > l_d and h_d > 0) else 0
        mdm[i] = l_d if (l_d > h_d and l_d > 0) else 0
    atr_s = np.zeros(n); pdm_s = np.zeros(n); mdm_s = np.zeros(n)
    atr_s[period] = np.sum(tr[1:period+1]); pdm_s[period] = np.sum(pdm[1:period+1]); mdm_s[period] = np.sum(mdm[1:period+1])
    for i in range(period+1, n):
        atr_s[i] = atr_s[i-1]-atr_s[i-1]/period+tr[i]
        pdm_s[i] = pdm_s[i-1]-pdm_s[i-1]/period+pdm[i]
        mdm_s[i] = mdm_s[i-1]-mdm_s[i-1]/period+mdm[i]
    dx = np.zeros(n)
    for i in range(period, n):
        if atr_s[i] > 0:
            pdi = 100*pdm_s[i]/atr_s[i]; mdi = 100*mdm_s[i]/atr_s[i]
            if pdi+mdi > 0: dx[i] = 100*abs(pdi-mdi)/(pdi+mdi)
    adx[period*2] = np.mean(dx[period:period*2+1])
    for i in range(period*2+1, n):
        adx[i] = (adx[i-1]*(period-1)+dx[i])/period
    return adx


def run_donchian(df, version, ppy, fee_rate, capital, n_coins):
    """Run Donchian B0-B3 on 8H data."""
    n = len(df)
    lbs = (36, 60, 336)  # 12d/20d/112d at 8H
    max_lb = max(lbs)
    if n < max_lb + 60: return None

    highs = df["high"].values; lows = df["low"].values
    closes = df["close"].values; opens = df["open"].values
    h_s = pd.Series(highs); l_s = pd.Series(lows)

    # Channels for all 3 lookbacks
    channels = {}
    for lb in lbs:
        channels[lb] = {
            "upper": h_s.rolling(lb).max().shift(1).values,
            "lower": l_s.rolling(lb).min().shift(1).values,
        }

    # ADX for regime filter
    adx = compute_adx(highs, lows, closes, 20)

    # Rolling vol for B2/B3 position sizing
    ret = np.zeros(n); ret[1:] = closes[1:]/closes[:-1]-1
    vol_20 = pd.Series(ret).rolling(60).std().values  # 20 days at 8H = 60 bars
    TARGET_VOL = 0.30

    # ATR
    atr_p = 14
    tr = np.maximum(highs[1:]-lows[1:], np.maximum(np.abs(highs[1:]-closes[:-1]), np.abs(lows[1:]-closes[:-1])))
    tr = np.insert(tr, 0, highs[0]-lows[0])
    atr = np.full(n, np.nan)
    atr[atr_p] = np.mean(tr[:atr_p])
    for i in range(atr_p+1, n): atr[i] = atr[i-1]*(atr_p-1)/atr_p+tr[i]/atr_p

    equity = capital; cash = equity; pos = 0.0; entry_px = 0.0
    peak = equity; equities = np.full(n, equity)
    n_trades = 0; wins = 0; closed = 0; prev_target = 0.0
    start = max_lb + 60
    rebal_counter = 0

    for i in range(start, n):
        o = opens[i]; c = closes[i]

        # Execute
        if abs(prev_target-pos) > max(5.0, abs(prev_target)*0.03):
            fee = abs(prev_target-pos)*fee_rate
            if abs(pos) > 0.01 and entry_px > 0:
                pnl = abs(pos)*((o-entry_px)/entry_px if pos > 0 else (entry_px-o)/entry_px)
                cash += pnl
                if pnl > 0: wins += 1
                closed += 1
            cash -= fee; n_trades += 1
            pos = prev_target
            entry_px = o if abs(pos) > 0.01 else 0.0

        unrealized = 0.0
        if abs(pos) > 0.01 and entry_px > 0:
            unrealized = abs(pos)*((c-entry_px)/entry_px if pos > 0 else (entry_px-c)/entry_px)
        equity = cash+unrealized; peak = max(peak, equity); equities[i] = equity

        # Regime filter (all versions)
        adx_val = adx[i] if not np.isnan(adx[i]) else 25.0
        regime_scale = 1.0 if adx_val >= 25 else (0.5 if adx_val >= 20 else 0.0)
        vol10 = pd.Series(ret[max(0,i-30):i]).std() if i >= 30 else np.nan
        vol30 = pd.Series(ret[max(0,i-90):i]).std() if i >= 90 else np.nan
        if not np.isnan(vol10) and not np.isnan(vol30) and vol30 > 0 and vol10 < vol30*0.7:
            regime_scale = 0.0

        # Signal generation
        if version in ("B0", "B2"):
            # Original med-heavy weighted agreement
            wts = [0.25, 0.50, 0.25]
            dirs = []
            for j, lb in enumerate(lbs):
                u = channels[lb]["upper"][i]; l = channels[lb]["lower"][i]
                if np.isnan(u) or np.isnan(l): dirs.append(0.0)
                elif c > u: dirs.append(1.0)
                elif c < l: dirs.append(-1.0)
                else: dirs.append(0.0)
            agreement = sum(w*d for w, d in zip(wts, dirs))
            if abs(agreement) < 0.05 or regime_scale == 0:
                prev_target = 0.0; continue
            direction = 1.0 if agreement > 0 else -1.0

        elif version in ("B1", "B3"):
            # Multi-lookback signal mixing: equal weight, threshold 0.33
            dirs = []
            for lb in lbs:
                u = channels[lb]["upper"][i]; l = channels[lb]["lower"][i]
                if np.isnan(u) or np.isnan(l): dirs.append(0.0)
                elif c > u: dirs.append(1.0)
                elif c < l: dirs.append(-1.0)
                else: dirs.append(0.0)
            avg_signal = np.mean(dirs)
            if abs(avg_signal) < 0.33 or regime_scale == 0:
                prev_target = 0.0; continue
            direction = 1.0 if avg_signal > 0 else -1.0
            agreement = abs(avg_signal)

        # Position sizing
        if version in ("B0", "B1"):
            # Original sizing
            if not np.isnan(atr[i]) and atr[i] > 0 and c > 0:
                ann_vol = (atr[i]/c)*np.sqrt(ppy)
                vol_scalar = max(0.5, min(2.0, 0.15/ann_vol if ann_vol > 0 else 1.0))
            else: vol_scalar = 1.0
            dd = max(0, 1.0-equity/peak)
            dd_scalar = 1.0-min(dd/0.30, 1.0)*0.75 if dd > 0 else 1.0
            base = equity*3.0*abs(agreement if version == "B0" else avg_signal)
            prev_target = direction*min(base*vol_scalar*dd_scalar*regime_scale, equity*3.0)

        elif version in ("B2", "B3"):
            # Target volatility sizing (30% annual, no optimization)
            rebal_counter += 1
            ann_vol_coin = vol_20[i]*np.sqrt(ppy) if not np.isnan(vol_20[i]) and vol_20[i] > 0 else 1.0
            target_risk = (TARGET_VOL/n_coins)/ann_vol_coin * equity if ann_vol_coin > 0 else 0
            target_risk = max(equity*0.01, min(equity*0.15, target_risk))  # 1%-15% bounds
            dd = max(0, 1.0-equity/peak)
            dd_scalar = 1.0-min(dd/0.30, 1.0)*0.75 if dd > 0 else 1.0
            prev_target = direction*target_risk*dd_scalar*regime_scale

    eq = pd.Series(equities[start:]);
    if len(eq) < 10: return None
    sr = sharpe_ratio(eq, ppy); _, dd_pct = max_drawdown(eq)
    return {"sharpe": sr, "return_pct": (float(eq.iloc[-1])-capital)/capital*100,
            "max_dd_pct": dd_pct, "n_trades": n_trades,
            "win_rate": wins/closed*100 if closed > 0 else 0}


def run_tsmom(df, ppy, fee_rate, capital, n_coins, version="C1"):
    """Run multi-lookback TSMOM C1/C2."""
    n = len(df)
    tsmom_lbs = [5, 21, 63, 126, 252]
    if n < max(tsmom_lbs)+20: return None

    closes = df["close"].values; opens = df["open"].values
    ret = np.zeros(n); ret[1:] = closes[1:]/closes[:-1]-1
    vol_20 = pd.Series(ret).rolling(20, min_periods=10).std().values
    TARGET_VOL = 0.30

    # Pre-compute cumulative returns for all lookbacks
    cum_rets = {}
    for lb in tsmom_lbs:
        cr = np.full(n, 0.0)
        for i in range(lb, n):
            cr[i] = closes[i]/closes[i-lb]-1
        cum_rets[lb] = cr

    equity = capital; cash = equity; pos = 0.0; entry_px = 0.0
    peak = equity; equities = np.full(n, equity)
    n_trades = 0; wins = 0; closed = 0; prev_target = 0.0
    start = max(tsmom_lbs)+5

    for i in range(start, n):
        o = opens[i]; c = closes[i]

        if abs(prev_target-pos) > max(5.0, abs(prev_target)*0.03):
            fee = abs(prev_target-pos)*fee_rate
            if abs(pos) > 0.01 and entry_px > 0:
                pnl = abs(pos)*((o-entry_px)/entry_px if pos > 0 else (entry_px-o)/entry_px)
                cash += pnl
                if pnl > 0: wins += 1
                closed += 1
            cash -= fee; n_trades += 1
            pos = prev_target
            entry_px = o if abs(pos) > 0.01 else 0.0

        unrealized = 0.0
        if abs(pos) > 0.01 and entry_px > 0:
            unrealized = abs(pos)*((c-entry_px)/entry_px if pos > 0 else (entry_px-c)/entry_px)
        equity = cash+unrealized; peak = max(peak, equity); equities[i] = equity

        # Multi-lookback signal: average of 5 binary signals
        signals = []
        for lb in tsmom_lbs:
            cr = cum_rets[lb][i]
            signals.append(1.0 if cr > 0 else (-1.0 if cr < 0 else 0.0))
        avg_signal = np.mean(signals)

        if abs(avg_signal) < 0.2:
            prev_target = 0.0; continue

        direction = 1.0 if avg_signal > 0 else -1.0

        if version == "C1":
            prev_target = direction*equity*abs(avg_signal)
        elif version == "C2":
            ann_vol = vol_20[i]*np.sqrt(ppy) if not np.isnan(vol_20[i]) and vol_20[i] > 0 else 1.0
            target_risk = (TARGET_VOL/n_coins)/ann_vol*equity if ann_vol > 0 else 0
            target_risk = max(equity*0.01, min(equity*0.15, target_risk))
            dd = max(0, 1.0-equity/peak)
            dd_scalar = 1.0-min(dd/0.30, 1.0)*0.75 if dd > 0 else 1.0
            prev_target = direction*target_risk*dd_scalar

    eq = pd.Series(equities[start:])
    if len(eq) < 10: return None
    sr = sharpe_ratio(eq, ppy); _, dd_pct = max_drawdown(eq)
    return {"sharpe": sr, "return_pct": (float(eq.iloc[-1])-capital)/capital*100,
            "max_dd_pct": dd_pct, "n_trades": n_trades,
            "win_rate": wins/closed*100 if closed > 0 else 0}


def run_portfolio(data, windows, holdout, run_fn, versions, ppy, fee_rate, label):
    """Run all versions on all assets across all windows."""
    results = {v: [] for v in versions}
    n_coins = len(data)
    capital = 10000.0/n_coins

    periods = [{"name": w["name"], "val_start": w["val_start"], "val_end": w["val_end"]} for w in windows]
    periods.append({"name": "HOLDOUT", "val_start": holdout["start"], "val_end": holdout["end"]})

    for window in periods:
        wname = window["name"]
        vs = pd.Timestamp(window["val_start"])
        ve = pd.Timestamp(window["val_end"])

        for ver in versions:
            sharpes = []; rets = []; dds = []; trades = []
            for sym, df in data.items():
                mask = (df.index >= vs) & (df.index < ve)
                period_df = df[mask].reset_index(drop=True) if isinstance(df.index[0], pd.Timestamp) else df.loc[mask].reset_index(drop=True)
                # Handle timestamp index vs regular index
                if hasattr(df, 'index') and hasattr(df.index, 'tz') and df.index.tz:
                    period_df = df[(df.index >= vs) & (df.index < ve)].copy()
                    period_df = period_df.reset_index(drop=True)
                else:
                    period_df = df[(df.index >= vs) & (df.index < ve)].copy()
                    period_df = period_df.reset_index(drop=True)

                if len(period_df) < 100: continue
                m = run_fn(period_df, ppy, fee_rate, capital, n_coins, ver) if "C" in ver else run_fn(period_df, ver, ppy, fee_rate, capital, n_coins)
                if m:
                    sharpes.append(m["sharpe"]); rets.append(m["return_pct"])
                    dds.append(m["max_dd_pct"]); trades.append(m["n_trades"])

            if sharpes:
                results[ver].append({
                    "window": wname, "sharpe": np.mean(sharpes), "return": np.mean(rets),
                    "max_dd": max(dds), "trades": sum(trades), "n_assets": len(sharpes)
                })

    return results


def main():
    dm = DataManager()

    # Load crypto 8H data
    print("Loading crypto 8H data...")
    crypto_8h = {}
    for sym in CRYPTO_COINS:
        df = dm.cache.read("okx", sym, "1h")
        if not df.empty:
            df8 = resample_ohlcv(df, "8h")
            df8["timestamp"] = pd.to_datetime(df8["timestamp"]).dt.tz_localize(None)
            df8 = df8.set_index("timestamp")
            crypto_8h[sym] = df8
    print(f"  Loaded {len(crypto_8h)} crypto coins")

    # Load crypto daily for TSMOM
    print("Loading crypto daily data...")
    crypto_1d = {}
    for sym in CRYPTO_COINS:
        df = dm.cache.read("okx", sym, "1h")
        if not df.empty:
            df = df.copy()
            df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
            daily = df.set_index("timestamp").resample("1D").agg(
                {"open":"first","high":"max","low":"min","close":"last","volume":"sum"}).dropna()
            crypto_1d[sym] = daily
    print(f"  Loaded {len(crypto_1d)} crypto daily")

    # Load traditional daily
    print("Loading traditional daily data...")
    import yfinance as yf
    trad_1d = {}
    for ticker in TRAD_TICKERS:
        try:
            df = yf.download(ticker, start="2014-06-01", end="2026-01-01", progress=False)
            if len(df) > 100:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [c[0].lower() for c in df.columns]
                else:
                    df.columns = [c.lower() for c in df.columns]
                trad_1d[ticker] = df
        except: pass
    print(f"  Loaded {len(trad_1d)} traditional assets")

    # ── Donchian B0-B3 on crypto ──
    print(f"\n{'='*70}")
    print(f"  DONCHIAN B0-B3 (Crypto, 8H)")
    print(f"{'='*70}")

    donchian_versions = ["B0", "B1", "B2", "B3"]
    donchian_results = run_portfolio(crypto_8h, CRYPTO_WINDOWS, CRYPTO_HOLDOUT,
                                      run_donchian, donchian_versions, PPY_8H, FEE_CRYPTO, "Donchian")

    for ver in donchian_versions:
        for r in donchian_results[ver]:
            print(f"  {ver} {r['window']}: Sharpe={r['sharpe']:.3f}  Ret={r['return']:+.2f}%  MaxDD={r['max_dd']:.2f}%  Trades={r['trades']}")

    # ── TSMOM C1-C2 on crypto ──
    print(f"\n{'='*70}")
    print(f"  TSMOM C1-C2 (Crypto, 1D)")
    print(f"{'='*70}")

    tsmom_c_versions = ["C1", "C2"]
    tsmom_crypto = run_portfolio(crypto_1d, CRYPTO_WINDOWS, CRYPTO_HOLDOUT,
                                 run_tsmom, tsmom_c_versions, PPY_1D, FEE_CRYPTO, "TSMOM-crypto")

    for ver in tsmom_c_versions:
        for r in tsmom_crypto[ver]:
            print(f"  {ver} {r['window']}: Sharpe={r['sharpe']:.3f}  Ret={r['return']:+.2f}%  MaxDD={r['max_dd']:.2f}%  Trades={r['trades']}")

    # ── TSMOM C1-C2 on traditional ──
    print(f"\n{'='*70}")
    print(f"  TSMOM C1-C2 (Traditional, 1D)")
    print(f"{'='*70}")

    tsmom_trad = run_portfolio(trad_1d, TRAD_WINDOWS, TRAD_HOLDOUT,
                                run_tsmom, tsmom_c_versions, PPY_1D, FEE_TRAD, "TSMOM-trad")

    for ver in tsmom_c_versions:
        for r in tsmom_trad[ver]:
            print(f"  {ver} {r['window']}: Sharpe={r['sharpe']:.3f}  Ret={r['return']:+.2f}%  MaxDD={r['max_dd']:.2f}%  Trades={r['trades']}")

    # ── Summary Table ──
    print(f"\n{'='*80}")
    print(f"  FINAL COMPARISON TABLE")
    print(f"{'='*80}")

    def print_row(label, results, n_windows):
        vals = [r["sharpe"] for r in results if r["window"] != "HOLDOUT"]
        ho = [r for r in results if r["window"] == "HOLDOUT"]
        avg_val = np.mean(vals) if vals else 0
        ho_s = ho[0]["sharpe"] if ho else 0
        ho_dd = ho[0]["max_dd"] if ho else 0
        ho_t = ho[0]["trades"] if ho else 0
        win_str = " ".join(f"{s:>7.3f}" for s in vals)
        print(f"  {label:<30s} {win_str}  avg={avg_val:>7.3f}  HO={ho_s:>7.3f}  DD={ho_dd:>6.1f}%  T={ho_t}")

    header_crypto = "  " + " "*30 + "  ".join(f"{'W'+str(i+1):>7s}" for i in range(len(CRYPTO_WINDOWS)))
    header_trad = "  " + " "*30 + "  ".join(f"{'W'+str(i+1):>7s}" for i in range(len(TRAD_WINDOWS)))

    print(f"\n  --- Crypto ---")
    print(header_crypto + "     avg      HO     DD%    T")
    for ver in donchian_versions:
        print_row(f"Donchian {ver}", donchian_results[ver], len(CRYPTO_WINDOWS))
    for ver in tsmom_c_versions:
        print_row(f"TSMOM {ver} (crypto)", tsmom_crypto[ver], len(CRYPTO_WINDOWS))

    print(f"\n  --- Traditional ---")
    print(header_trad + "     avg      HO     DD%    T")
    for ver in tsmom_c_versions:
        print_row(f"TSMOM {ver} (trad)", tsmom_trad[ver], len(TRAD_WINDOWS))

    # Mixed portfolio: average crypto + trad sharpes
    print(f"\n  --- Mixed Portfolios ---")
    for ver in tsmom_c_versions:
        c_vals = [r["sharpe"] for r in tsmom_crypto[ver] if r["window"] != "HOLDOUT"]
        t_vals = [r["sharpe"] for r in tsmom_trad[ver] if r["window"] != "HOLDOUT"]
        c_ho = [r["sharpe"] for r in tsmom_crypto[ver] if r["window"] == "HOLDOUT"]
        t_ho = [r["sharpe"] for r in tsmom_trad[ver] if r["window"] == "HOLDOUT"]
        if c_vals and t_vals:
            # Simple average of crypto avg and trad avg
            mix_val = (np.mean(c_vals) + np.mean(t_vals)) / 2
            mix_ho = (c_ho[0] + t_ho[0]) / 2 if c_ho and t_ho else 0
            print(f"  {ver} Mixed (crypto+trad): Val avg={mix_val:.3f}, Holdout={mix_ho:.3f}")

    # Save
    Path("sweep_results").mkdir(exist_ok=True)
    save = {"donchian": donchian_results, "tsmom_crypto": tsmom_crypto, "tsmom_trad": tsmom_trad}
    Path("sweep_results/institutional_results.json").write_text(json.dumps(save, indent=2, default=str))
    print(f"\n  Results saved to sweep_results/institutional_results.json")


if __name__ == "__main__":
    main()
