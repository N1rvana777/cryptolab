#!/usr/bin/env python3
"""实盘复盘仪表板：从 run 目录读取日志，生成可视化报告。

用法:
  python scripts/review_live.py --run-dir runs/20260325_live_donchian

输出（HTML 文件保存到 run-dir/review/）:
  1. equity_curve.html    — 账户权益曲线 + 回撤
  2. trades.html          — 交易记录（按时间排列，hover 显示细节）
  3. per_symbol.html      — 每币种 PnL 分解
  4. worst_trades.html    — 最差交易分析
  5. slippage.html        — 实际滑点 vs 回测假设
  6. summary.txt          — 文字摘要（可直接粘贴到笔记）
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False
    print("WARNING: plotly not installed. Charts will be skipped.")


def load_equity_log(run_dir: Path) -> pd.DataFrame:
    path = run_dir / "equity_log.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path, parse_dates=["timestamp"])
    return df


def load_fills(run_dir: Path) -> pd.DataFrame:
    path = run_dir / "fills.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path, parse_dates=["ts_utc"])
    return df


def load_orders(run_dir: Path) -> pd.DataFrame:
    path = run_dir / "orders.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path, parse_dates=["ts_utc"])
    return df


def load_run_config(run_dir: Path) -> dict:
    path = run_dir / "run_config.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def compute_metrics(equity_df: pd.DataFrame) -> dict:
    """Compute key metrics from equity log."""
    if equity_df.empty or "equity" not in equity_df.columns:
        return {}

    eq = equity_df["equity"].astype(float)
    initial = eq.iloc[0]
    final = eq.iloc[-1]
    total_return = (final - initial) / initial * 100

    # Max drawdown
    peak = eq.cummax()
    dd = (eq - peak) / peak * 100
    max_dd = abs(dd.min())

    # Sharpe (assume 4H bars, 6 per day, 365 days)
    returns = eq.pct_change().dropna()
    if len(returns) > 1 and returns.std() > 0:
        sharpe = returns.mean() / returns.std() * np.sqrt(6 * 365)
    else:
        sharpe = 0.0

    # Duration
    duration_hours = 0
    if len(equity_df) > 1:
        ts = pd.to_datetime(equity_df["timestamp"])
        duration_hours = (ts.iloc[-1] - ts.iloc[0]).total_seconds() / 3600

    return {
        "initial_equity": initial,
        "final_equity": final,
        "total_return_pct": total_return,
        "max_drawdown_pct": max_dd,
        "sharpe": sharpe,
        "n_snapshots": len(equity_df),
        "duration_hours": duration_hours,
    }


def compute_trade_stats(fills_df: pd.DataFrame) -> dict:
    """Compute trade-level statistics from fills."""
    if fills_df.empty:
        return {}

    n_fills = len(fills_df)
    total_volume = 0
    total_fees = 0
    avg_slippage = 0

    if "filled_size" in fills_df.columns and "avg_fill_px" in fills_df.columns:
        fills_df["notional"] = fills_df["filled_size"].astype(float) * fills_df["avg_fill_px"].astype(float)
        total_volume = fills_df["notional"].sum()

    if "est_fees_usd" in fills_df.columns:
        total_fees = fills_df["est_fees_usd"].astype(float).sum()

    if "slippage_bps_realized" in fills_df.columns:
        avg_slippage = fills_df["slippage_bps_realized"].astype(float).mean()

    # Per-symbol breakdown
    per_symbol = {}
    if "symbol" in fills_df.columns:
        for sym, group in fills_df.groupby("symbol"):
            per_symbol[sym] = {
                "n_fills": len(group),
                "volume": group["notional"].sum() if "notional" in group.columns else 0,
                "fees": group["est_fees_usd"].astype(float).sum() if "est_fees_usd" in group.columns else 0,
                "avg_slippage_bps": group["slippage_bps_realized"].astype(float).mean() if "slippage_bps_realized" in group.columns else 0,
            }

    return {
        "n_fills": n_fills,
        "total_volume": total_volume,
        "total_fees": total_fees,
        "avg_slippage_bps": avg_slippage,
        "per_symbol": per_symbol,
    }


def worst_trades(fills_df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Find worst trades by realized slippage."""
    if fills_df.empty or "slippage_bps_realized" not in fills_df.columns:
        return pd.DataFrame()

    df = fills_df.copy()
    df["slippage_bps_realized"] = df["slippage_bps_realized"].astype(float)
    return df.nlargest(n, "slippage_bps_realized")[
        ["ts_utc", "symbol", "side", "filled_size", "avg_fill_px",
         "mid_px", "slippage_bps_realized", "est_fees_usd"]
    ]


def build_equity_chart(equity_df: pd.DataFrame, output_path: str):
    """Build equity curve + drawdown chart."""
    if not HAS_PLOTLY or equity_df.empty:
        return

    eq = equity_df["equity"].astype(float)
    ts = pd.to_datetime(equity_df["timestamp"])
    peak = eq.cummax()
    dd_pct = (eq - peak) / peak * 100

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.7, 0.3],
        subplot_titles=["Equity Curve", "Drawdown %"],
    )

    fig.add_trace(go.Scatter(
        x=ts, y=eq, name="Equity",
        line=dict(color="#2196F3", width=2),
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=ts, y=peak, name="Peak",
        line=dict(color="gray", width=1, dash="dot"),
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=ts, y=dd_pct, name="Drawdown",
        fill="tozeroy", fillcolor="rgba(255,0,0,0.2)",
        line=dict(color="red", width=1),
    ), row=2, col=1)

    fig.update_layout(
        title="Live Trading Equity Curve",
        height=600, template="plotly_dark",
    )
    fig.write_html(output_path)


def build_fills_chart(fills_df: pd.DataFrame, output_path: str):
    """Build fills timeline with slippage coloring."""
    if not HAS_PLOTLY or fills_df.empty:
        return

    df = fills_df.copy()
    df["ts"] = pd.to_datetime(df["ts_utc"])
    df["notional"] = df["filled_size"].astype(float) * df["avg_fill_px"].astype(float)
    df["slip"] = df["slippage_bps_realized"].astype(float)

    buys = df[df["side"] == "BUY"]
    sells = df[df["side"] == "SELL"]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=buys["ts"], y=buys["notional"],
        mode="markers", name="BUY",
        marker=dict(
            size=8, color=buys["slip"],
            colorscale="RdYlGn_r", colorbar=dict(title="Slippage bps"),
            symbol="triangle-up",
        ),
        text=buys.apply(lambda r: f"{r['symbol']}<br>Size: {r['filled_size']}<br>"
                                   f"Fill: {r['avg_fill_px']}<br>Slip: {r['slip']:.1f}bps", axis=1),
        hoverinfo="text",
    ))

    fig.add_trace(go.Scatter(
        x=sells["ts"], y=sells["notional"],
        mode="markers", name="SELL",
        marker=dict(
            size=8, color=sells["slip"],
            colorscale="RdYlGn_r",
            symbol="triangle-down",
        ),
        text=sells.apply(lambda r: f"{r['symbol']}<br>Size: {r['filled_size']}<br>"
                                    f"Fill: {r['avg_fill_px']}<br>Slip: {r['slip']:.1f}bps", axis=1),
        hoverinfo="text",
    ))

    fig.update_layout(
        title="Trade Fills (colored by slippage)",
        xaxis_title="Time", yaxis_title="Notional USD",
        height=500, template="plotly_dark",
    )
    fig.write_html(output_path)


def build_slippage_chart(fills_df: pd.DataFrame, output_path: str):
    """Build slippage distribution histogram."""
    if not HAS_PLOTLY or fills_df.empty or "slippage_bps_realized" not in fills_df.columns:
        return

    slip = fills_df["slippage_bps_realized"].astype(float)

    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=slip, nbinsx=50, name="Realized Slippage",
        marker_color="#2196F3",
    ))

    # Backtest assumption line
    fig.add_vline(x=15.0, line_dash="dash", line_color="red",
                  annotation_text="Backtest assumption (15 bps)")

    fig.add_vline(x=slip.mean(), line_dash="dash", line_color="green",
                  annotation_text=f"Actual mean ({slip.mean():.1f} bps)")

    fig.update_layout(
        title="Slippage Distribution: Actual vs Backtest Assumption",
        xaxis_title="Slippage (bps)", yaxis_title="Count",
        height=400, template="plotly_dark",
    )
    fig.write_html(output_path)


def build_per_symbol_chart(fills_df: pd.DataFrame, equity_df: pd.DataFrame, output_path: str):
    """Build per-symbol PnL breakdown."""
    if not HAS_PLOTLY or equity_df.empty:
        return

    # Parse positions from equity log
    if "positions" not in equity_df.columns:
        return

    fig = go.Figure()
    ts = pd.to_datetime(equity_df["timestamp"])

    # Try to extract per-symbol position sizes over time
    symbols = set()
    for _, row in equity_df.iterrows():
        try:
            pos = json.loads(row["positions"]) if isinstance(row["positions"], str) else {}
            symbols.update(pos.keys())
        except (json.JSONDecodeError, TypeError):
            pass

    colors = ["#2196F3", "#FF9800", "#4CAF50", "#E91E63", "#9C27B0"]
    for i, sym in enumerate(sorted(symbols)):
        values = []
        for _, row in equity_df.iterrows():
            try:
                pos = json.loads(row["positions"]) if isinstance(row["positions"], str) else {}
                values.append(pos.get(sym, 0))
            except (json.JSONDecodeError, TypeError):
                values.append(0)

        fig.add_trace(go.Scatter(
            x=ts, y=values, name=sym,
            stackgroup="one",
            line=dict(color=colors[i % len(colors)]),
        ))

    fig.update_layout(
        title="Position Exposure by Symbol (USD)",
        xaxis_title="Time", yaxis_title="Position USD",
        height=500, template="plotly_dark",
    )
    fig.write_html(output_path)


def generate_summary(run_config: dict, metrics: dict, trade_stats: dict,
                     worst_df: pd.DataFrame) -> str:
    """Generate text summary for quick review."""
    lines = []
    lines.append("=" * 60)
    lines.append("  LIVE TRADING REVIEW")
    lines.append("=" * 60)

    if run_config:
        lines.append(f"\n  Start:     {run_config.get('start_time', 'N/A')}")
        lines.append(f"  Mode:      {'LIVE' if not run_config.get('dry_run', True) else 'DRY-RUN'}")
        lines.append(f"  Leverage:  {run_config.get('leverage', 'N/A')}x")
        syms = run_config.get("symbols", {})
        lines.append(f"  Symbols:   {', '.join(f'{s}({v.get('combo','?')})' for s, v in syms.items())}")

    if metrics:
        lines.append(f"\n  --- Performance ---")
        lines.append(f"  Initial:   ${metrics.get('initial_equity', 0):.2f}")
        lines.append(f"  Final:     ${metrics.get('final_equity', 0):.2f}")
        lines.append(f"  Return:    {metrics.get('total_return_pct', 0):+.2f}%")
        lines.append(f"  Max DD:    {metrics.get('max_drawdown_pct', 0):.2f}%")
        lines.append(f"  Sharpe:    {metrics.get('sharpe', 0):.2f}")
        lines.append(f"  Duration:  {metrics.get('duration_hours', 0):.0f} hours")

    if trade_stats:
        lines.append(f"\n  --- Execution ---")
        lines.append(f"  Fills:     {trade_stats.get('n_fills', 0)}")
        lines.append(f"  Volume:    ${trade_stats.get('total_volume', 0):,.0f}")
        lines.append(f"  Fees:      ${trade_stats.get('total_fees', 0):.2f}")
        lines.append(f"  Avg Slip:  {trade_stats.get('avg_slippage_bps', 0):.1f} bps (backtest: 15 bps)")

        per_sym = trade_stats.get("per_symbol", {})
        if per_sym:
            lines.append(f"\n  --- Per Symbol ---")
            for sym, stats in sorted(per_sym.items()):
                lines.append(
                    f"  {sym}: {stats['n_fills']} fills, "
                    f"vol=${stats['volume']:,.0f}, "
                    f"fees=${stats['fees']:.2f}, "
                    f"slip={stats['avg_slippage_bps']:.1f}bps"
                )

    if not worst_df.empty:
        lines.append(f"\n  --- Worst Fills (by slippage) ---")
        for _, row in worst_df.head(5).iterrows():
            lines.append(
                f"  {row.get('ts_utc', '')}: {row.get('side', '')} {row.get('symbol', '')} "
                f"slip={row.get('slippage_bps_realized', 0):.1f}bps "
                f"(fill={row.get('avg_fill_px', 0):.4f}, mid={row.get('mid_px', 0):.4f})"
            )

    lines.append("\n" + "=" * 60)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Review live trading results")
    parser.add_argument("--run-dir", type=str, required=True, help="Path to run directory")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    if not run_dir.exists():
        print(f"Run directory not found: {run_dir}")
        sys.exit(1)

    review_dir = run_dir / "review"
    review_dir.mkdir(exist_ok=True)

    # Load data
    run_config = load_run_config(run_dir)
    equity_df = load_equity_log(run_dir)
    fills_df = load_fills(run_dir)
    orders_df = load_orders(run_dir)

    # Compute metrics
    metrics = compute_metrics(equity_df)
    trade_stats = compute_trade_stats(fills_df)
    worst_df = worst_trades(fills_df)

    # Generate summary
    summary = generate_summary(run_config, metrics, trade_stats, worst_df)
    print(summary)
    (review_dir / "summary.txt").write_text(summary)

    # Generate charts
    if HAS_PLOTLY:
        if not equity_df.empty:
            build_equity_chart(equity_df, str(review_dir / "equity_curve.html"))
            print(f"  Chart: {review_dir / 'equity_curve.html'}")

        if not fills_df.empty:
            build_fills_chart(fills_df, str(review_dir / "trades.html"))
            build_slippage_chart(fills_df, str(review_dir / "slippage.html"))
            print(f"  Chart: {review_dir / 'trades.html'}")
            print(f"  Chart: {review_dir / 'slippage.html'}")

        if not equity_df.empty:
            build_per_symbol_chart(fills_df, equity_df, str(review_dir / "per_symbol.html"))
            print(f"  Chart: {review_dir / 'per_symbol.html'}")
    else:
        print("  (Install plotly for charts: pip install plotly)")

    print(f"\n  All outputs saved to: {review_dir}")


if __name__ == "__main__":
    main()
