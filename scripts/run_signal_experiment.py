#!/usr/bin/env python3
"""Three-signal controlled experiment: VW, MR, CS weight sweeps on 4-coin portfolio.

Tests each signal independently (control variable) across IS and OOS periods.
"""

import os
import sys
from dataclasses import replace
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd

from cryptolab.config import Config
from cryptolab.data.manager import DataManager
from cryptolab.backtest import BacktestEngine
from cryptolab.backtest.metrics import (
    portfolio_equity_curve, sharpe_ratio, max_drawdown,
    sortino_ratio, calmar_ratio, PERIODS_PER_YEAR,
)
from cryptolab.strategy import DonchianMTF
from cryptolab.indicators.cross_sectional import compute_cs_multipliers

# --- Constants ---
SYMBOLS = ["BTC", "SOL", "ADA", "XRP"]
SYMBOL_COMBOS = {"BTC": "G", "SOL": "G", "ADA": "G", "XRP": "F"}

MTF_COMBO_MAP = {
    "A": [18, 48, 168], "B": [24, 72, 252], "C": [36, 96, 252],
    "D": [36, 72, 336], "E": [48, 120, 336], "F": [48, 168, 504],
    "G": [24, 72, 168], "H": [36, 120, 504],
}

SIGNALS = {
    "VW": "vw_weight",
    "MR": "mr_weight",
    "CS": "cs_weight",
}

WEIGHTS = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]

PERIODS = [
    ("IS", "2021-01-01", "2023-12-31"),
    ("OOS", "2024-01-01", "2026-03-08"),
]

INTERVAL = "4h"
SOURCE = "okx"
CAPITAL = 10_000.0
LEVERAGE = 3.0


def _ts_ms(date_str: str) -> int:
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def load_all_data(dm: DataManager) -> dict:
    """Load data for all symbols and periods. Returns {(symbol, period_name): DataFrame}."""
    cache = {}
    for symbol in SYMBOLS:
        for period_name, start, end in PERIODS:
            key = (symbol, period_name)
            print(f"Loading {symbol} {INTERVAL} ({period_name}: {start} to {end})...")
            start_ms = _ts_ms(start)
            end_ms = _ts_ms(end)
            df = dm.get_historical(symbol, INTERVAL, start_ms, end_ms, source=SOURCE)
            if df.empty or len(df) < 2:
                print(f"  WARNING: Not enough data for {symbol} {period_name}")
                continue
            print(f"  Loaded {len(df)} bars")
            cache[key] = df
    return cache


def run_portfolio(data_cache: dict, period_name: str, cfg_base: Config,
                  signal_name: str = None, cs_multipliers: dict = None):
    """Run 4-coin portfolio backtest, return portfolio metrics dict."""
    ppy = PERIODS_PER_YEAR.get(INTERVAL, 2190)
    n = len(SYMBOLS)
    per_cap = cfg_base.initial_capital / n

    symbol_curves = {}
    for symbol in SYMBOLS:
        key = (symbol, period_name)
        df = data_cache.get(key)
        if df is None:
            continue

        combo = SYMBOL_COMBOS[symbol]
        lbs = MTF_COMBO_MAP[combo]
        cfg_run = replace(cfg_base,
                          initial_capital=per_cap,
                          mtf_lookbacks=lbs,
                          mtf_weights=[0.33, 0.34, 0.33])

        strategy = DonchianMTF(cfg_run)

        # Inject cross-sectional multipliers if needed
        if cs_multipliers and symbol in cs_multipliers:
            strategy._cs_lookup = cs_multipliers[symbol]

        engine = BacktestEngine(strategy, cfg_run)
        result = engine.run(symbol, df)
        symbol_curves[symbol] = result.equity_curve

    if not symbol_curves:
        return None

    port_ec = portfolio_equity_curve(symbol_curves)
    port_eq = port_ec["equity"]
    total_init = cfg_base.initial_capital

    ret = (port_eq.iloc[-1] / total_init - 1) * 100
    dd_usd, dd_pct = max_drawdown(port_eq)
    s = sharpe_ratio(port_eq, ppy)
    sort = sortino_ratio(port_eq, ppy)
    calm = calmar_ratio(port_eq, ppy)

    return {
        "return_pct": ret,
        "max_dd_pct": dd_pct,
        "sharpe": s,
        "sortino": sort,
        "calmar": calm,
    }


def run_experiment(data_cache: dict):
    """Run full experiment: 3 signals × 6 weights × 2 periods."""
    results = []  # list of dicts

    for signal_name, config_key in SIGNALS.items():
        print(f"\n{'='*60}")
        print(f"  SIGNAL: {signal_name} ({config_key})")
        print(f"{'='*60}")

        for weight in WEIGHTS:
            # Create config with ONLY this signal's weight set
            cfg = Config(
                interval=INTERVAL,
                data_source=SOURCE,
                initial_capital=CAPITAL,
                leverage=LEVERAGE,
            )
            setattr(cfg, config_key, weight)

            for period_name, start, end in PERIODS:
                # Pre-compute cross-sectional multipliers if needed
                cs_mults = None
                if signal_name == "CS" and weight > 0:
                    period_dfs = {}
                    for sym in SYMBOLS:
                        key = (sym, period_name)
                        if key in data_cache:
                            period_dfs[sym] = data_cache[key]
                    cs_mults = compute_cs_multipliers(period_dfs, cfg.cs_lookback, weight)

                metrics = run_portfolio(data_cache, period_name, cfg,
                                        signal_name=signal_name,
                                        cs_multipliers=cs_mults)

                if metrics is None:
                    continue

                row = {
                    "signal": signal_name,
                    "weight": weight,
                    "period": period_name,
                    **metrics,
                }
                results.append(row)

                print(f"  {signal_name} w={weight:.1f} {period_name}: "
                      f"Sharpe={metrics['sharpe']:.2f}  Ret={metrics['return_pct']:+.1f}%  "
                      f"MaxDD={metrics['max_dd_pct']:.1f}%")

    return results


def print_summary_table(results: list):
    """Print the final summary table."""
    print("\n" + "=" * 90)
    print("  THREE-SIGNAL EXPERIMENT RESULTS")
    print("=" * 90)
    print(f"  {'Signal':<8} {'Weight':>6} {'IS_Sharpe':>10} {'OOS_Sharpe':>11} "
          f"{'OOS_Ret':>8} {'OOS_MaxDD':>10} {'IS-OOS':>7}")
    print("  " + "-" * 85)

    # Group by signal and weight
    for signal_name in SIGNALS:
        for weight in WEIGHTS:
            is_row = next((r for r in results
                           if r["signal"] == signal_name and r["weight"] == weight
                           and r["period"] == "IS"), None)
            oos_row = next((r for r in results
                            if r["signal"] == signal_name and r["weight"] == weight
                            and r["period"] == "OOS"), None)

            is_sharpe = is_row["sharpe"] if is_row else float("nan")
            oos_sharpe = oos_row["sharpe"] if oos_row else float("nan")
            oos_ret = oos_row["return_pct"] if oos_row else float("nan")
            oos_dd = oos_row["max_dd_pct"] if oos_row else float("nan")
            delta = is_sharpe - oos_sharpe

            marker = ""
            if weight == 0.0:
                marker = " (baseline)"
            elif oos_sharpe > 0.86:
                marker = " ***"

            print(f"  {signal_name:<8} {weight:>6.1f} {is_sharpe:>10.2f} {oos_sharpe:>11.2f} "
                  f"{oos_ret:>+7.1f}% {oos_dd:>9.1f}% {delta:>+7.2f}{marker}")

        print("  " + "-" * 85)

    print("=" * 90)
    print("  *** = OOS Sharpe > 0.86 baseline")
    print("  IS-OOS = gap between in-sample and out-of-sample (smaller = less overfit)")


def append_to_research_log(results: list, project_root: str):
    """Append experiment results to RESEARCH_LOG.md."""
    log_path = os.path.join(project_root, "RESEARCH_LOG.md")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        f"\n## {now} — Signal Experiment: VW / MR / CS Weight Sweep\n",
        f"Portfolio: {', '.join(f'{s}({SYMBOL_COMBOS[s]})' for s in SYMBOLS)}",
        f"IS: 2021-2023, OOS: 2024-2026, Capital: ${CAPITAL:,.0f}, Leverage: {LEVERAGE}x\n",
        "| Signal | Weight | IS Sharpe | OOS Sharpe | OOS Return | OOS MaxDD |",
        "| --- | --- | --- | --- | --- | --- |",
    ]

    for signal_name in SIGNALS:
        for weight in WEIGHTS:
            is_row = next((r for r in results
                           if r["signal"] == signal_name and r["weight"] == weight
                           and r["period"] == "IS"), None)
            oos_row = next((r for r in results
                            if r["signal"] == signal_name and r["weight"] == weight
                            and r["period"] == "OOS"), None)

            is_s = f"{is_row['sharpe']:.2f}" if is_row else "N/A"
            oos_s = f"{oos_row['sharpe']:.2f}" if oos_row else "N/A"
            oos_r = f"{oos_row['return_pct']:+.2f}%" if oos_row else "N/A"
            oos_d = f"{oos_row['max_dd_pct']:.2f}%" if oos_row else "N/A"

            lines.append(f"| {signal_name} | {weight:.1f} | {is_s} | {oos_s} | {oos_r} | {oos_d} |")

    lines.append("")

    with open(log_path, "a", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\n  Results appended to {log_path}")


def main():
    print("=" * 60)
    print("  THREE-SIGNAL CONTROLLED EXPERIMENT")
    print(f"  Symbols: {', '.join(f'{s}({SYMBOL_COMBOS[s]})' for s in SYMBOLS)}")
    print(f"  Signals: {', '.join(SIGNALS.keys())}")
    print(f"  Weights: {WEIGHTS}")
    print(f"  Periods: IS (2021-2023), OOS (2024-2026)")
    print("=" * 60)

    dm = DataManager()
    data_cache = load_all_data(dm)

    results = run_experiment(data_cache)

    print_summary_table(results)

    project_root = os.path.join(os.path.dirname(__file__), "..")
    append_to_research_log(results, project_root)


if __name__ == "__main__":
    main()
