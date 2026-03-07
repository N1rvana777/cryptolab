#!/usr/bin/env python3
"""
Run a single- or multi-symbol backtest with optional lookback sweep.

Usage:
    python scripts/run_backtest.py --symbol BTC --start 2021-01-01 --end 2023-12-31
    python scripts/run_backtest.py --symbols BTC,ETH,SOL --start 2021-01-01 --end 2023-12-31
    python scripts/run_backtest.py --symbols BTC,ETH,SOL --sweep-lookback 12,20,30,48,72,96
"""

import argparse
import json
import os
import sys
from dataclasses import asdict, replace
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd

from cryptolab.config import Config
from cryptolab.data.manager import DataManager
from cryptolab.backtest import BacktestEngine, BacktestResult
from cryptolab.backtest.metrics import (
    monthly_returns, portfolio_equity_curve, bootstrap_sharpe_ci,
    deflated_sharpe, regime_split_sharpe, sharpe_ratio, max_drawdown,
    calmar_ratio, sortino_ratio, PERIODS_PER_YEAR,
)
from cryptolab.strategy import DonchianBreakout, DonchianMTF


MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _ts_ms(date_str: str) -> int:
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def print_summary(r: BacktestResult):
    print("\n" + "=" * 60)
    print(f"  Backtest: {r.strategy_name} on {r.symbol}")
    print(f"  Period: {r.start_date} to {r.end_date}")
    print(f"  Donchian lookback: {r.config.donchian_period}")
    print("=" * 60)
    print(f"  Initial equity:  ${r.initial_equity:,.2f}")
    print(f"  Final equity:    ${r.final_equity:,.2f}")
    print(f"  Return:          {r.total_return_pct:+.2f}%")
    print(f"  Max drawdown:    {r.max_drawdown_pct:.2f}% (${r.max_drawdown_usd:,.2f})")
    print(f"  Sharpe:          {r.sharpe:.2f}")
    print(f"  Sortino:         {r.sortino:.2f}")
    print(f"  Calmar:          {r.calmar:.2f}")
    print(f"  Trades:          {r.total_trades}")
    print(f"  Win rate:        {r.win_rate:.1f}%")
    print(f"  Profit factor:   {r.profit_factor:.2f}")
    print(f"  Avg win:         ${r.avg_win_pct:,.2f}")
    print(f"  Avg loss:        ${r.avg_loss_pct:,.2f}")
    print(f"  Total fees:      ${r.total_fees:,.2f}")
    print(f"  Slippage est:    ${r.total_slippage_est:,.2f}")
    print(f"  Time in market:  {r.time_in_market_pct:.1f}%")
    print(f"  Avg trade dur:   {r.avg_trade_duration_bars:.1f} bars")
    print("=" * 60)


def print_monthly_table(r: BacktestResult):
    mr = monthly_returns(r.equity_curve)
    if mr.empty:
        return

    years = sorted(mr["year"].unique())
    print(f"\n  Monthly Returns (%) — {r.symbol}")
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


def print_comparison_table(results: list[BacktestResult]):
    if len(results) < 2:
        return

    r0 = results[0]
    print("\n" + "=" * 90)
    print(f"  Comparison: {r0.strategy_name} | {r0.start_date} to {r0.end_date}")
    print("=" * 90)
    print(f"  {'Symbol':<8} {'Return':>8} {'MaxDD':>8} {'Sharpe':>7} {'Sortino':>8} {'Calmar':>7} {'Trades':>7} {'WinRate':>8} {'PF':>6}")
    print("  " + "-" * 86)
    for r in results:
        print(f"  {r.symbol:<8} {r.total_return_pct:>+7.2f}% {r.max_drawdown_pct:>7.2f}% {r.sharpe:>7.2f} {r.sortino:>8.2f} {r.calmar:>7.2f} {r.total_trades:>7d} {r.win_rate:>7.1f}% {r.profit_factor:>6.2f}")
    print("=" * 90)


def _fmt_param(val, width: int) -> str:
    if isinstance(val, (int, float)):
        return f"{val:>{width}g}"
    return f"{val:>{width}}"


def print_sweep_table(sweep_results: list[tuple[dict, BacktestResult]]):
    """Print a parameter sweep sensitivity matrix.

    Each entry is (params_dict, BacktestResult) where params_dict has keys like
    'lookback' and/or 'leverage'.
    """
    if not sweep_results:
        return

    r0 = sweep_results[0][1]
    param_keys = list(sweep_results[0][0].keys())

    print("\n" + "=" * 110)
    print(f"  Parameter Sweep: {r0.strategy_name} | {r0.start_date} to {r0.end_date}")
    print("=" * 110)

    param_headers = "  ".join(f"{k:>10}" for k in param_keys)
    print(f"  {param_headers}  {'Symbol':<6} {'Return':>8} {'MaxDD':>8} {'Sharpe':>7} {'Sortino':>8} {'Calmar':>7} {'Trades':>7} {'WinRate':>8} {'PF':>6}")
    print("  " + "-" * (10 * len(param_keys) + 2 * len(param_keys) + 80))
    for params, r in sweep_results:
        param_vals = "  ".join(_fmt_param(params[k], 10) for k in param_keys)
        print(f"  {param_vals}  {r.symbol:<6} {r.total_return_pct:>+7.2f}% {r.max_drawdown_pct:>7.2f}% {r.sharpe:>7.2f} {r.sortino:>8.2f} {r.calmar:>7.2f} {r.total_trades:>7d} {r.win_rate:>7.1f}% {r.profit_factor:>6.2f}")
    print("=" * 110)


def save_results(r: BacktestResult, run_dir: str):
    os.makedirs(run_dir, exist_ok=True)

    # Equity curve
    r.equity_curve.to_csv(os.path.join(run_dir, "equity_curve.csv"), index=False)

    # Trade log
    if r.trades:
        trade_rows = []
        for t in r.trades:
            trade_rows.append({
                "bar_idx": t.bar_idx,
                "timestamp": t.timestamp,
                "symbol": t.symbol,
                "side": t.side,
                "size_usd": t.size_usd,
                "fill_px": t.fill_px,
                "fee": t.fee,
                "old_position": t.old_position,
                "new_position": t.new_position,
                "realized_pnl": t.realized_pnl,
                "signal": t.signal,
            })
        pd.DataFrame(trade_rows).to_csv(os.path.join(run_dir, "trades.csv"), index=False)

    # Monthly returns
    mr = monthly_returns(r.equity_curve)
    if not mr.empty:
        mr.to_csv(os.path.join(run_dir, "monthly_returns.csv"), index=False)

    # config.json
    cfg_dict = asdict(r.config)
    with open(os.path.join(run_dir, "config.json"), "w", encoding="utf-8") as f:
        json.dump(cfg_dict, f, indent=2)

    # summary.json
    summary = {
        "symbol": r.symbol,
        "strategy_name": r.strategy_name,
        "start_date": r.start_date,
        "end_date": r.end_date,
        "initial_equity": r.initial_equity,
        "final_equity": r.final_equity,
        "total_return_pct": r.total_return_pct,
        "max_drawdown_pct": r.max_drawdown_pct,
        "max_drawdown_usd": r.max_drawdown_usd,
        "sharpe": r.sharpe,
        "sortino": r.sortino,
        "calmar": r.calmar,
        "total_trades": r.total_trades,
        "win_rate": r.win_rate,
        "avg_win_pct": r.avg_win_pct,
        "avg_loss_pct": r.avg_loss_pct,
        "profit_factor": r.profit_factor,
        "total_fees": r.total_fees,
        "total_slippage_est": r.total_slippage_est,
        "time_in_market_pct": r.time_in_market_pct,
        "avg_trade_duration_bars": r.avg_trade_duration_bars,
    }
    with open(os.path.join(run_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\n  Results saved to {run_dir}/")


def append_research_log(r: BacktestResult, project_root: str):
    log_path = os.path.join(project_root, "RESEARCH_LOG.md")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    c = r.config
    entry = f"""
## {now} — Backtest: {r.strategy_name} on {r.symbol}

- Period: {r.start_date} to {r.end_date}
- Config: donchian_period={c.donchian_period}, atr_period={c.atr_period}, atr_sl_mult={c.atr_sl_mult}, risk_per_trade={c.risk_per_trade}, leverage={c.leverage}
- Return: {r.total_return_pct:+.2f}% | Max DD: {r.max_drawdown_pct:.2f}% | Sharpe: {r.sharpe:.2f} | Sortino: {r.sortino:.2f} | Calmar: {r.calmar:.2f}
- Trades: {r.total_trades} | Win rate: {r.win_rate:.1f}% | Profit factor: {r.profit_factor:.2f}
- Fees: ${r.total_fees:.2f} | Slippage: ${r.total_slippage_est:.2f} | Time in market: {r.time_in_market_pct:.1f}%
- Initial: ${r.initial_equity:,.0f} | Final: ${r.final_equity:,.2f}
"""
    if not os.path.exists(log_path):
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("# Research Log\n")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(entry)
    print(f"  Appended to {log_path}")


def append_comparison_log(results: list[BacktestResult], project_root: str):
    if len(results) < 2:
        return
    log_path = os.path.join(project_root, "RESEARCH_LOG.md")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    r0 = results[0]
    symbols = ", ".join(r.symbol for r in results)

    lines = [f"\n## {now} — Comparison: {r0.strategy_name} ({symbols})\n"]
    lines.append("| Symbol | Return | MaxDD | Sharpe | Sortino | Calmar | Trades | WinRate | PF |")
    lines.append("|--------|--------|-------|--------|---------|--------|--------|---------|-----|")
    for r in results:
        lines.append(f"| {r.symbol} | {r.total_return_pct:+.2f}% | {r.max_drawdown_pct:.2f}% | {r.sharpe:.2f} | {r.sortino:.2f} | {r.calmar:.2f} | {r.total_trades} | {r.win_rate:.1f}% | {r.profit_factor:.2f} |")
    lines.append("")

    with open(log_path, "a", encoding="utf-8") as f:
        f.write("\n".join(lines))


def append_sweep_log(sweep_results: list[tuple[dict, BacktestResult]], project_root: str):
    """Append sweep sensitivity table to RESEARCH_LOG."""
    if not sweep_results:
        return
    log_path = os.path.join(project_root, "RESEARCH_LOG.md")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    r0 = sweep_results[0][1]
    param_keys = list(sweep_results[0][0].keys())
    symbols = sorted(set(r.symbol for _, r in sweep_results))

    param_desc = ", ".join(f"{k}={sorted(set(str(p[k]) for p, _ in sweep_results))}" for k in param_keys)
    lines = [f"\n## {now} — Parameter Sweep: {r0.strategy_name} ({', '.join(symbols)})\n"]
    lines.append(f"Params: {param_desc}\n")

    header_cols = " | ".join(k.capitalize() for k in param_keys)
    lines.append(f"| {header_cols} | Symbol | Return | MaxDD | Sharpe | Sortino | Calmar | Trades | WinRate | PF |")
    sep_cols = " | ".join("---" for _ in param_keys)
    lines.append(f"| {sep_cols} | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for params, r in sweep_results:
        param_vals = " | ".join(f"{params[k]:g}" if isinstance(params[k], (int, float)) else str(params[k]) for k in param_keys)
        lines.append(f"| {param_vals} | {r.symbol} | {r.total_return_pct:+.2f}% | {r.max_drawdown_pct:.2f}% | {r.sharpe:.2f} | {r.sortino:.2f} | {r.calmar:.2f} | {r.total_trades} | {r.win_rate:.1f}% | {r.profit_factor:.2f} |")
    lines.append("")

    with open(log_path, "a", encoding="utf-8") as f:
        f.write("\n".join(lines))


def load_data(symbol: str, interval: str, source: str, start: str, end: str, dm: DataManager) -> pd.DataFrame:
    """Load OHLCV data for a symbol. Returns DataFrame or exits on failure."""
    print(f"\nLoading {symbol} {interval} data from {source} ({start} to {end})...")
    start_ms = _ts_ms(start)
    end_ms = _ts_ms(end)
    df = dm.get_historical(symbol, interval, start_ms, end_ms, source=source)

    if df.empty or len(df) < 2:
        print(f"ERROR: Not enough data for {symbol}. Try seeding first: python scripts/seed_cache.py")
        sys.exit(1)

    print(f"Loaded {len(df)} bars ({df.iloc[0]['timestamp']} to {df.iloc[-1]['timestamp']})")
    return df


def run_backtest(symbol: str, df: pd.DataFrame, cfg: Config, strategy_name: str = "donchian") -> BacktestResult:
    """Run backtest on pre-loaded data with given config."""
    if strategy_name == "donchian_mtf":
        strategy = DonchianMTF(cfg)
    else:
        strategy = DonchianBreakout(cfg)
    engine = BacktestEngine(strategy, cfg)
    return engine.run(symbol, df)


def main():
    parser = argparse.ArgumentParser(description="Run a single- or multi-symbol backtest")
    parser.add_argument("--symbol", type=str, default="BTC", help="Single symbol (e.g. BTC)")
    parser.add_argument("--symbols", type=str, default=None, help="Comma-separated symbols (e.g. BTC,ETH,SOL)")
    parser.add_argument("--start", type=str, default="2021-01-01", help="Start date YYYY-MM-DD")
    parser.add_argument("--end", type=str, default="2023-12-31", help="End date YYYY-MM-DD")
    parser.add_argument("--interval", type=str, default="4h", help="Candle interval")
    parser.add_argument("--source", type=str, default="okx", help="Data source")
    parser.add_argument("--capital", type=float, default=None, help="Override initial capital")
    parser.add_argument("--leverage", type=float, default=None, help="Override leverage")
    parser.add_argument("--lookback", type=int, default=None, help="Override donchian_period (single value)")
    parser.add_argument("--sweep-lookback", type=str, default=None,
                        help="Comma-separated Donchian lookback values (e.g. 12,20,30,48,72,96)")
    parser.add_argument("--sweep-leverage", type=str, default=None,
                        help="Comma-separated leverage values (e.g. 1.0,1.5,2.0,2.5,3.0)")
    parser.add_argument("--strategy", type=str, default="donchian",
                        choices=["donchian", "donchian_mtf"],
                        help="Strategy to use (default: donchian)")
    parser.add_argument("--mtf-lookbacks", type=str, default=None,
                        help="Comma-separated short,medium,long lookback (e.g. 24,72,252)")
    parser.add_argument("--mtf-weights", type=str, default=None,
                        help="Comma-separated weights (e.g. 0.25,0.50,0.25)")
    parser.add_argument("--sweep-mtf", action="store_true",
                        help="Sweep predefined MTF lookback combos x weight sets")
    parser.add_argument("--portfolio", action="store_true",
                        help="Run multi-symbol portfolio backtest with equal capital split")
    parser.add_argument("--symbol-combos", type=str, default=None,
                        help="Per-symbol combo overrides: SYM:combo,... (e.g. XRP:F,BTC:G)")
    parser.add_argument("--overfit-check", action="store_true",
                        help="Run overfitting diagnostics (bootstrap CI, regime split)")
    parser.add_argument("--pyramid-units", type=int, default=None,
                        help="Max pyramid units (1=no pyramiding, 4=full turtle)")
    args = parser.parse_args()

    cfg = Config(interval=args.interval, data_source=args.source)
    if args.capital is not None:
        cfg.initial_capital = args.capital
    if args.leverage is not None:
        cfg.leverage = args.leverage
    if args.lookback is not None:
        cfg.donchian_period = args.lookback
    if args.mtf_lookbacks:
        cfg.mtf_lookbacks = [int(x) for x in args.mtf_lookbacks.split(",")]
    if args.mtf_weights:
        cfg.mtf_weights = [float(x) for x in args.mtf_weights.split(",")]
    if args.pyramid_units is not None:
        cfg.mtf_pyramid_max_units = args.pyramid_units

    # Determine symbols to run
    if args.symbols:
        symbol_list = [s.strip().upper() for s in args.symbols.split(",")]
    else:
        symbol_list = [args.symbol.upper()]

    # Portfolio mode
    if args.portfolio:
        _run_portfolio(args, cfg, symbol_list)
        return

    # MTF combo sweep mode
    if args.sweep_mtf:
        MTF_COMBOS = [
            ("A", [18, 48, 168]),
            ("B", [24, 72, 252]),
            ("C", [36, 96, 252]),
            ("D", [36, 72, 336]),
            ("E", [48, 120, 336]),
            ("F", [48, 168, 504]),
            ("G", [24, 72, 168]),
            ("H", [36, 120, 504]),
        ]
        MTF_WEIGHT_SETS = [
            ("med-heavy", [0.25, 0.50, 0.25]),
            ("equal", [0.33, 0.34, 0.33]),
        ]
        _run_mtf_sweep(args, cfg, symbol_list, MTF_COMBOS, MTF_WEIGHT_SETS)
        return

    # Determine sweep axes
    lookbacks = ([int(x.strip()) for x in args.sweep_lookback.split(",")]
                 if args.sweep_lookback else [cfg.donchian_period])
    leverages = ([float(x.strip()) for x in args.sweep_leverage.split(",")]
                 if args.sweep_leverage else [cfg.leverage])

    is_sweep = len(lookbacks) > 1 or len(leverages) > 1

    dm = DataManager()
    project_root = os.path.join(os.path.dirname(__file__), "..")
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # Pre-load data once per symbol
    data_cache: dict[str, pd.DataFrame] = {}
    for symbol in symbol_list:
        data_cache[symbol] = load_data(symbol, args.interval, args.source, args.start, args.end, dm)

    # Run all combinations (lookback × leverage × symbol)
    all_results: list[tuple[dict, BacktestResult]] = []

    for lb in lookbacks:
        for lev in leverages:
            cfg_run = replace(cfg, donchian_period=lb, leverage=lev)

            for symbol in symbol_list:
                if is_sweep:
                    print(f"\n--- Lookback={lb}, Leverage={lev}, Symbol={symbol} ---")

                result = run_backtest(symbol, data_cache[symbol], cfg_run, args.strategy)
                params = {"lookback": lb, "leverage": lev}
                all_results.append((params, result))

                print_summary(result)

                if not is_sweep:
                    print_monthly_table(result)

                run_dir = os.path.join(project_root, "runs",
                                       f"{ts}_lb{lb}_lev{lev}_{symbol}_{result.strategy_name}")
                save_results(result, run_dir)
                append_research_log(result, project_root)

    # Summary tables
    if is_sweep:
        # Remove constant params from sweep display
        display_results = _strip_constant_params(all_results)
        print_sweep_table(display_results)
        append_sweep_log(display_results, project_root)
    elif len(symbol_list) > 1:
        results = [r for _, r in all_results]
        print_comparison_table(results)
        append_comparison_log(results, project_root)


MTF_COMBO_MAP = {
    "A": [18, 48, 168],
    "B": [24, 72, 252],
    "C": [36, 96, 252],
    "D": [36, 72, 336],
    "E": [48, 120, 336],
    "F": [48, 168, 504],
    "G": [24, 72, 168],
    "H": [36, 120, 504],
}


def _parse_symbol_combos(s: str) -> dict[str, str]:
    """Parse 'XRP:F,BTC:G' into {'XRP': 'F', 'BTC': 'G'}."""
    result = {}
    for pair in s.split(","):
        parts = pair.strip().split(":")
        if len(parts) == 2:
            result[parts[0].upper()] = parts[1].upper()
    return result


def _run_portfolio(args, cfg, symbol_list):
    """Run multi-symbol portfolio backtest with equal capital split."""
    dm = DataManager()
    project_root = os.path.join(os.path.dirname(__file__), "..")
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    ppy = PERIODS_PER_YEAR.get(args.interval, 2190)

    n_symbols = len(symbol_list)
    per_symbol_capital = cfg.initial_capital / n_symbols

    # Parse per-symbol combo overrides
    combo_overrides = _parse_symbol_combos(args.symbol_combos) if args.symbol_combos else {}

    # Load data
    data_cache: dict[str, pd.DataFrame] = {}
    for symbol in symbol_list:
        data_cache[symbol] = load_data(symbol, args.interval, args.source, args.start, args.end, dm)

    # Run per-symbol backtests
    symbol_results: dict[str, BacktestResult] = {}
    symbol_curves: dict[str, pd.DataFrame] = {}

    for symbol in symbol_list:
        combo_letter = combo_overrides.get(symbol, "G")
        lbs = MTF_COMBO_MAP.get(combo_letter, MTF_COMBO_MAP["G"])
        cfg_run = replace(cfg,
                          initial_capital=per_symbol_capital,
                          mtf_lookbacks=lbs,
                          mtf_weights=[0.33, 0.34, 0.33])

        combo_str = f"{lbs[0]}/{lbs[1]}/{lbs[2]}"
        print(f"\n--- {symbol} (Combo {combo_letter}: {combo_str}, capital=${per_symbol_capital:,.0f}) ---")

        result = run_backtest(symbol, data_cache[symbol], cfg_run, args.strategy)
        symbol_results[symbol] = result
        symbol_curves[symbol] = result.equity_curve

        print_summary(result)

        run_dir = os.path.join(project_root, "runs", f"{ts}_portfolio_{symbol}")
        save_results(result, run_dir)

        # Overfit check per symbol
        if args.overfit_check:
            _print_overfit_diagnostics(symbol, result, data_cache[symbol], ppy)

    # Combine into portfolio
    port_ec = portfolio_equity_curve(symbol_curves)
    port_eq = port_ec["equity"]
    total_initial = cfg.initial_capital

    port_return = (port_eq.iloc[-1] / total_initial - 1) * 100
    dd_usd, dd_pct = max_drawdown(port_eq)
    port_sharpe = sharpe_ratio(port_eq, ppy)
    port_sortino = sortino_ratio(port_eq, ppy)
    port_calmar = calmar_ratio(port_eq, ppy)

    # Print portfolio summary
    print("\n" + "=" * 70)
    print(f"  PORTFOLIO SUMMARY ({n_symbols} coins, equal weight)")
    print("=" * 70)
    print(f"  Initial capital:  ${total_initial:,.2f}")
    print(f"  Final equity:     ${port_eq.iloc[-1]:,.2f}")
    print(f"  Return:           {port_return:+.2f}%")
    print(f"  Max drawdown:     {dd_pct:.2f}% (${dd_usd:,.2f})")
    print(f"  Sharpe:           {port_sharpe:.2f}")
    print(f"  Sortino:          {port_sortino:.2f}")
    print(f"  Calmar:           {port_calmar:.2f}")
    print()

    # Per-symbol contribution
    print(f"  {'Symbol':<8} {'Combo':<8} {'Return':>8} {'MaxDD':>8} {'Sharpe':>7} {'Contrib$':>10}")
    print("  " + "-" * 55)
    for symbol in symbol_list:
        r = symbol_results[symbol]
        combo_letter = combo_overrides.get(symbol, "G")
        pnl = r.final_equity - per_symbol_capital
        print(f"  {symbol:<8} {combo_letter:<8} {r.total_return_pct:>+7.2f}% {r.max_drawdown_pct:>7.2f}% {r.sharpe:>7.2f} {pnl:>+10.2f}")
    print("=" * 70)

    # Save portfolio equity curve
    port_dir = os.path.join(project_root, "runs", f"{ts}_portfolio_combined")
    os.makedirs(port_dir, exist_ok=True)
    port_ec.to_csv(os.path.join(port_dir, "portfolio_equity_curve.csv"), index=False)

    # Portfolio overfit check (bootstrap on portfolio curve)
    if args.overfit_check:
        print("\n  --- Portfolio Bootstrap ---")
        bs = bootstrap_sharpe_ci(port_eq, ppy)
        print(f"  Portfolio Sharpe 95% CI: [{bs['lower']:.2f}, {bs['upper']:.2f}]")
        print(f"  Bootstrap median: {bs['median']:.2f}, std: {bs['std']:.2f}")


def _print_overfit_diagnostics(symbol: str, result: BacktestResult, ohlcv_df: pd.DataFrame, ppy: float):
    """Print overfitting diagnostics for a single backtest result."""
    eq = result.equity_curve["equity"]

    print(f"\n  --- Overfit Diagnostics: {symbol} ---")

    # 1. Bootstrap CI
    bs = bootstrap_sharpe_ci(eq, ppy)
    print(f"  Bootstrap Sharpe 95% CI: [{bs['lower']:.2f}, {bs['upper']:.2f}]")
    print(f"  Bootstrap median: {bs['median']:.2f}, std: {bs['std']:.2f}")
    if bs["lower"] <= 0:
        print(f"  WARNING: CI includes 0 — Sharpe not statistically significant")
    else:
        print(f"  OK: CI above 0 — Sharpe is statistically significant")

    # 2. Regime split
    regime = regime_split_sharpe(ohlcv_df, result.equity_curve, sma_period=200, periods_per_year=ppy)
    for r_name in ["bull", "bear"]:
        r_data = regime.get(r_name, {})
        print(f"  Regime {r_name}: Sharpe={r_data.get('sharpe', 0):.2f}, "
              f"bars={r_data.get('bars', 0)}, {r_data.get('pct_of_total', 0):.1f}% of period")

    bull_sharpe = regime.get("bull", {}).get("sharpe", 0)
    bear_sharpe = regime.get("bear", {}).get("sharpe", 0)
    if bull_sharpe > 0.5 and bear_sharpe < -0.3:
        print(f"  WARNING: Regime-dependent: works in bull, fails in bear")
    elif bear_sharpe > 0.5 and bull_sharpe < -0.3:
        print(f"  WARNING: Regime-dependent: works in bear, fails in bull")
    else:
        print(f"  OK: Not obviously regime-dependent")


def _run_mtf_sweep(args, cfg, symbol_list, combos, weight_sets):
    """Run MTF lookback combo × weight set sweep."""
    dm = DataManager()
    project_root = os.path.join(os.path.dirname(__file__), "..")
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    data_cache: dict[str, pd.DataFrame] = {}
    for symbol in symbol_list:
        data_cache[symbol] = load_data(symbol, args.interval, args.source, args.start, args.end, dm)

    all_results: list[tuple[dict, BacktestResult]] = []

    for combo_name, lbs in combos:
        for wt_name, wts in weight_sets:
            cfg_run = replace(cfg, mtf_lookbacks=lbs, mtf_weights=wts)

            for symbol in symbol_list:
                label = f"{combo_name}/{wt_name}"
                print(f"\n--- Combo {combo_name} {lbs}, Weights {wt_name} {wts}, Symbol={symbol} ---")

                result = run_backtest(symbol, data_cache[symbol], cfg_run, "donchian_mtf")
                params = {
                    "combo": combo_name,
                    "lookbacks": f"{lbs[0]}/{lbs[1]}/{lbs[2]}",
                    "weights": wt_name,
                }
                all_results.append((params, result))

                print_summary(result)

                run_dir = os.path.join(project_root, "runs",
                                       f"{ts}_mtf_{combo_name}_{wt_name}_{symbol}")
                save_results(result, run_dir)
                append_research_log(result, project_root)

    # Sort by Sharpe descending
    all_results.sort(key=lambda x: x[1].sharpe, reverse=True)
    print_sweep_table(all_results)
    append_sweep_log(all_results, project_root)


def _strip_constant_params(
    sweep_results: list[tuple[dict, BacktestResult]],
) -> list[tuple[dict, BacktestResult]]:
    """Remove param keys that have only one unique value (not interesting to show)."""
    if not sweep_results:
        return sweep_results
    all_keys = list(sweep_results[0][0].keys())
    varying_keys = [k for k in all_keys if len(set(p[k] for p, _ in sweep_results)) > 1]
    if not varying_keys:
        varying_keys = all_keys  # show all if nothing varies
    return [({k: p[k] for k in varying_keys}, r) for p, r in sweep_results]


if __name__ == "__main__":
    main()
