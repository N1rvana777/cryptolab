#!/usr/bin/env python3
"""
Portfolio-level backtest: run Donchian Breakout on multiple symbols with equal-weight capital allocation.

Usage:
    python scripts/run_portfolio.py --symbols BTC,SOL --start 2021-01-01 --end 2023-12-31 --lookback 72 --leverage 1.5
"""

import argparse
import json
import os
import sys
from dataclasses import asdict, replace
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd

from cryptolab.config import Config
from cryptolab.data.manager import DataManager
from cryptolab.backtest import BacktestEngine, BacktestResult
from cryptolab.backtest.metrics import (
    max_drawdown, sharpe_ratio, sortino_ratio, calmar_ratio,
    monthly_returns, PERIODS_PER_YEAR,
)
from cryptolab.strategy import DonchianBreakout, DonchianMTF

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _ts_ms(date_str: str) -> int:
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def load_data(symbol, interval, source, start, end, dm):
    print(f"\nLoading {symbol} {interval} data from {source} ({start} to {end})...")
    df = dm.get_historical(symbol, interval, _ts_ms(start), _ts_ms(end), source=source)
    if df.empty or len(df) < 2:
        print(f"ERROR: Not enough data for {symbol}.")
        sys.exit(1)
    print(f"Loaded {len(df)} bars ({df.iloc[0]['timestamp']} to {df.iloc[-1]['timestamp']})")
    return df


def merge_equity_curves(results: list[BacktestResult]) -> pd.DataFrame:
    """Merge per-symbol equity curves into a portfolio-level equity curve.

    Each symbol's equity starts at capital/N. Portfolio equity = sum of all sub-equities.
    Forward-fills to handle different start dates.
    """
    dfs = []
    for r in results:
        ec = r.equity_curve[["timestamp", "equity"]].copy()
        ec = ec.rename(columns={"equity": f"equity_{r.symbol}"})
        ec = ec.set_index("timestamp")
        dfs.append(ec)

    merged = pd.concat(dfs, axis=1)
    merged = merged.sort_index()

    # Forward-fill: before a symbol's data starts, its equity = its initial allocation
    for r in results:
        col = f"equity_{r.symbol}"
        merged[col] = merged[col].ffill()
        merged[col] = merged[col].bfill()

    merged["equity"] = merged.sum(axis=1)
    merged = merged.reset_index()
    return merged


def print_portfolio_summary(results: list[BacktestResult], portfolio_eq: pd.DataFrame,
                            total_capital: float, interval: str):
    ppy = PERIODS_PER_YEAR.get(interval, 2190)
    eq_series = portfolio_eq["equity"]
    final = eq_series.iloc[-1]
    ret = (final / total_capital - 1) * 100.0
    dd_usd, dd_pct = max_drawdown(eq_series)
    sr = sharpe_ratio(eq_series, ppy)
    so = sortino_ratio(eq_series, ppy)
    cr = calmar_ratio(eq_series, ppy)

    symbols_str = ", ".join(r.symbol for r in results)
    n = len(results)
    start_date = portfolio_eq["timestamp"].iloc[0].strftime("%Y-%m-%d")
    end_date = portfolio_eq["timestamp"].iloc[-1].strftime("%Y-%m-%d")

    print("\n" + "=" * 70)
    print(f"  Portfolio: {results[0].strategy_name} ({symbols_str})")
    print(f"  Period: {start_date} to {end_date}")
    print(f"  Weight: equal ({100/n:.0f}% each, ${total_capital/n:,.0f} per symbol)")
    print("=" * 70)
    print(f"  Initial equity:  ${total_capital:,.2f}")
    print(f"  Final equity:    ${final:,.2f}")
    print(f"  Return:          {ret:+.2f}%")
    print(f"  Max drawdown:    {dd_pct:.2f}% (${dd_usd:,.2f})")
    print(f"  Sharpe:          {sr:.2f}")
    print(f"  Sortino:         {so:.2f}")
    print(f"  Calmar:          {cr:.2f}")
    print()

    # Per-symbol breakdown
    print(f"  {'Symbol':<8} {'Capital':>8} {'Return':>8} {'MaxDD':>8} {'Sharpe':>7} {'Sortino':>8} {'PF':>6}")
    print("  " + "-" * 62)
    for r in results:
        cap = total_capital / n
        print(f"  {r.symbol:<8} ${cap:>7,.0f} {r.total_return_pct:>+7.2f}% {r.max_drawdown_pct:>7.2f}% {r.sharpe:>7.2f} {r.sortino:>8.2f} {r.profit_factor:>6.2f}")
    print("=" * 70)

    return {
        "initial_equity": total_capital,
        "final_equity": final,
        "return_pct": ret,
        "max_drawdown_pct": dd_pct,
        "max_drawdown_usd": dd_usd,
        "sharpe": sr,
        "sortino": so,
        "calmar": cr,
    }


def print_portfolio_monthly(portfolio_eq: pd.DataFrame):
    mr = monthly_returns(portfolio_eq)
    if mr.empty:
        return

    years = sorted(mr["year"].unique())
    print(f"\n  Portfolio Monthly Returns (%)")
    header = "  Year  " + "  ".join(f"{m:>6s}" for m in MONTH_NAMES) + "  Annual"
    print(header)
    print("  " + "-" * (len(header) - 2))

    for year in years:
        yr_data = mr[mr["year"] == year]
        cols = []
        annual = 1.0
        for m in range(1, 13):
            row = yr_data[yr_data["month"] == m]
            if not row.empty:
                val = row["return_pct"].iloc[0]
                annual *= (1 + val / 100.0)
                cols.append(f"{val:+6.1f}")
            else:
                cols.append("     -")
        annual_pct = (annual - 1) * 100.0
        print(f"  {year}  " + "  ".join(cols) + f"  {annual_pct:+6.1f}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Portfolio-level backtest")
    parser.add_argument("--symbols", type=str, required=True, help="Comma-separated symbols (e.g. BTC,SOL)")
    parser.add_argument("--start", type=str, default="2021-01-01")
    parser.add_argument("--end", type=str, default="2023-12-31")
    parser.add_argument("--interval", type=str, default="4h")
    parser.add_argument("--source", type=str, default="okx")
    parser.add_argument("--capital", type=float, default=10000.0)
    parser.add_argument("--leverage", type=float, default=None)
    parser.add_argument("--lookback", type=int, default=None)
    parser.add_argument("--strategy", type=str, default="donchian",
                        choices=["donchian", "donchian_mtf"])
    args = parser.parse_args()

    symbol_list = [s.strip().upper() for s in args.symbols.split(",")]
    n = len(symbol_list)
    capital_per_symbol = args.capital / n

    cfg = Config(interval=args.interval, data_source=args.source,
                 initial_capital=capital_per_symbol)
    if args.leverage is not None:
        cfg.leverage = args.leverage
    if args.lookback is not None:
        cfg.donchian_period = args.lookback

    dm = DataManager()

    # Load data
    data_cache = {}
    for symbol in symbol_list:
        data_cache[symbol] = load_data(symbol, args.interval, args.source, args.start, args.end, dm)

    # Run individual backtests
    results = []
    for symbol in symbol_list:
        if args.strategy == "donchian_mtf":
            strategy = DonchianMTF(cfg)
        else:
            strategy = DonchianBreakout(cfg)
        engine = BacktestEngine(strategy, cfg)
        result = engine.run(symbol, data_cache[symbol])
        results.append(result)

    # Merge equity curves
    portfolio_eq = merge_equity_curves(results)

    # Print results
    portfolio_stats = print_portfolio_summary(results, portfolio_eq, args.capital, args.interval)
    print_portfolio_monthly(portfolio_eq)

    # Save
    project_root = os.path.join(os.path.dirname(__file__), "..")
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    symbols_tag = "_".join(symbol_list)
    run_dir = os.path.join(project_root, "runs", f"{ts}_portfolio_{symbols_tag}")
    os.makedirs(run_dir, exist_ok=True)

    portfolio_eq.to_csv(os.path.join(run_dir, "portfolio_equity.csv"), index=False)

    for r in results:
        r.equity_curve.to_csv(os.path.join(run_dir, f"equity_{r.symbol}.csv"), index=False)

    summary = {
        "symbols": symbol_list,
        "weight": "equal",
        "capital_per_symbol": capital_per_symbol,
        **portfolio_stats,
        "per_symbol": [
            {"symbol": r.symbol, "return_pct": r.total_return_pct,
             "max_drawdown_pct": r.max_drawdown_pct, "sharpe": r.sharpe,
             "sortino": r.sortino, "profit_factor": r.profit_factor}
            for r in results
        ],
        "config": asdict(cfg),
    }
    with open(os.path.join(run_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)

    print(f"  Results saved to {run_dir}/")

    # Append to research log
    log_path = os.path.join(project_root, "RESEARCH_LOG.md")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    entry = f"""
## {now} -- Portfolio: {symbols_tag} (equal weight)

- Period: {portfolio_eq['timestamp'].iloc[0].strftime('%Y-%m-%d')} to {portfolio_eq['timestamp'].iloc[-1].strftime('%Y-%m-%d')}
- Config: lookback={cfg.donchian_period}, leverage={cfg.leverage}, capital=${args.capital:,.0f} (${capital_per_symbol:,.0f}/symbol)
- **Portfolio**: Return {portfolio_stats['return_pct']:+.2f}% | MaxDD {portfolio_stats['max_drawdown_pct']:.2f}% | Sharpe {portfolio_stats['sharpe']:.2f} | Sortino {portfolio_stats['sortino']:.2f} | Calmar {portfolio_stats['calmar']:.2f}

| Symbol | Return | MaxDD | Sharpe | PF |
|--------|--------|-------|--------|----|
"""
    for r in results:
        entry += f"| {r.symbol} | {r.total_return_pct:+.2f}% | {r.max_drawdown_pct:.2f}% | {r.sharpe:.2f} | {r.profit_factor:.2f} |\n"

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(entry)
    print(f"  Appended to {log_path}")


if __name__ == "__main__":
    main()
