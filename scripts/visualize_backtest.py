#!/usr/bin/env python3
"""Interactive backtest visualizer with Plotly.

Overlays candlesticks, 3-TF Donchian channels, and buy/sell markers.
Hovering over trade arrows shows the full decision snapshot JSON.

Usage:
    python scripts/visualize_backtest.py --run-dir runs/20260310_portfolio_BTC
    python scripts/visualize_backtest.py --symbol BTC --start 2021-01-01 --end 2023-12-31
    python scripts/visualize_backtest.py --telemetry-file telemetry_logs/telemetry_BTC_2021-01-01_2023-12-31.jsonl
"""

import argparse
import json
import os
import sys
from typing import List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
except ImportError:
    print("ERROR: plotly is required. Install with: pip install plotly")
    sys.exit(1)

from cryptolab.indicators.donchian import compute_donchian


def load_telemetry_jsonl(filepath: str) -> pd.DataFrame:
    """Load a telemetry JSONL file into a DataFrame."""
    records = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    df = pd.DataFrame(records)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def find_telemetry_file(run_dir: str) -> Optional[str]:
    """Find the first telemetry JSONL file in a run directory."""
    telemetry_dir = os.path.join(run_dir, "telemetry_logs")
    if not os.path.isdir(telemetry_dir):
        return None
    for fname in sorted(os.listdir(telemetry_dir)):
        if fname.startswith("telemetry_") and fname.endswith(".jsonl"):
            return os.path.join(telemetry_dir, fname)
    return None


def find_actions_file(run_dir: str) -> Optional[str]:
    """Find the first actions JSONL file in a run directory."""
    telemetry_dir = os.path.join(run_dir, "telemetry_logs")
    if not os.path.isdir(telemetry_dir):
        return None
    for fname in sorted(os.listdir(telemetry_dir)):
        if fname.startswith("actions_") and fname.endswith(".jsonl"):
            return os.path.join(telemetry_dir, fname)
    return None


def compute_donchian_series(highs: pd.Series, lows: pd.Series, period: int) -> pd.DataFrame:
    """Compute rolling Donchian channel series (shifted to avoid look-ahead)."""
    upper = highs.rolling(period).max().shift(1)
    lower = lows.rolling(period).min().shift(1)
    return pd.DataFrame({"upper": upper, "lower": lower})


def format_snapshot_tooltip(row: pd.Series) -> str:
    """Format a telemetry row into a readable multi-line tooltip string."""
    # Key decision fields to show
    fields = [
        ("signal", row.get("signal")),
        ("target_pos", f"${row.get('target_position', 0):,.0f}" if row.get("target_position") else "0"),
        ("confidence", f"{row.get('confidence', 0):.2f}"),
        ("equity", f"${row.get('equity', 0):,.0f}"),
        ("close", f"{row.get('close', 0):.2f}"),
    ]

    # Donchian levels
    for key in ["dc_upper", "dc_lower"]:
        val = row.get(key)
        if val is not None and val == val:  # not NaN
            fields.append((key, f"{val:.2f}"))

    # Core scalars
    for key in ["atr", "combined", "final_combined", "vol_scalar", "dd_scalar",
                 "current_dd_pct", "ann_vol", "mom_score"]:
        val = row.get(key)
        if val is not None and val == val:
            fields.append((key, f"{val:.4f}" if abs(val) < 1 else f"{val:.2f}"))

    # TF details
    for i in range(3):
        for suffix in [f"tf{i}_lb", f"tf{i}_upper", f"tf{i}_lower"]:
            for col_key in [suffix + str(j) for j in range(10, 600)] + [suffix]:
                val = row.get(col_key)
                if val is not None and val == val:
                    fields.append((col_key, f"{val:.2f}" if isinstance(val, float) else str(val)))
                    break

    # Exit reason
    if row.get("exit_reason"):
        fields.append(("exit_reason", row["exit_reason"]))

    # Trail stop
    if row.get("trail_stop") is not None:
        fields.append(("trail_stop", f"{row['trail_stop']:.2f}"))

    lines = [f"{k}: {v}" for k, v in fields]
    return "<br>".join(lines)


def build_figure(
    telemetry_df: pd.DataFrame,
    actions_df: Optional[pd.DataFrame] = None,
    mtf_lookbacks: Optional[List[int]] = None,
    title: str = "Backtest Visualization",
) -> go.Figure:
    """Build the interactive Plotly figure.

    Args:
        telemetry_df: Full telemetry DataFrame (all bars).
        actions_df: Actions-only DataFrame (entries/exits). If None, extracted from telemetry.
        mtf_lookbacks: List of 3 Donchian lookback periods. Auto-detected from telemetry if None.
        title: Figure title.
    """
    df = telemetry_df.copy()
    df = df.sort_values("timestamp").reset_index(drop=True)

    # Auto-detect MTF lookbacks from telemetry column names
    if mtf_lookbacks is None:
        mtf_lookbacks = []
        for col in df.columns:
            if col.startswith("tf") and "_lb" in col:
                # e.g. tf0_lb24 -> 24
                parts = col.split("_lb")
                if len(parts) == 2:
                    try:
                        lb = int(parts[1])
                        if lb not in mtf_lookbacks:
                            mtf_lookbacks.append(lb)
                    except ValueError:
                        pass
        mtf_lookbacks.sort()

    # Create subplots: price + equity
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.75, 0.25],
        subplot_titles=["Price & Donchian Channels", "Equity Curve"],
    )

    # --- Row 1: Candlestick ---
    fig.add_trace(
        go.Candlestick(
            x=df["timestamp"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="OHLC",
            increasing_line_color="#26a69a",
            decreasing_line_color="#ef5350",
        ),
        row=1, col=1,
    )

    # --- Donchian channels for each TF ---
    colors = ["rgba(66,133,244,0.5)", "rgba(219,68,55,0.5)", "rgba(244,180,0,0.5)"]
    tf_labels = ["Short TF", "Medium TF", "Long TF"]

    for i, lb in enumerate(mtf_lookbacks[:3]):
        dc = compute_donchian_series(df["high"], df["low"], lb)
        color = colors[i] if i < len(colors) else "rgba(128,128,128,0.4)"
        label = tf_labels[i] if i < len(tf_labels) else f"TF {lb}"

        fig.add_trace(
            go.Scatter(
                x=df["timestamp"], y=dc["upper"],
                mode="lines", name=f"{label} Upper ({lb})",
                line=dict(color=color, width=1, dash="dot"),
                showlegend=True,
            ),
            row=1, col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=df["timestamp"], y=dc["lower"],
                mode="lines", name=f"{label} Lower ({lb})",
                line=dict(color=color, width=1, dash="dot"),
                showlegend=False,
                fill="tonexty",
                fillcolor=color.replace("0.5)", "0.08)"),
            ),
            row=1, col=1,
        )

    # --- Trade markers with decision snapshot tooltips ---
    if actions_df is None:
        # Extract actions from telemetry
        actions_df = df[df["signal"].isin(["LONG", "SHORT", "CLOSE"])].copy()
        # Also include pyramid adds
        pyramid_mask = (df["signal"] == "HOLD") & (df.get("pyramid_add", pd.Series(False, index=df.index)).astype(bool))
        if pyramid_mask.any():
            actions_df = pd.concat([actions_df, df[pyramid_mask]])
        actions_df = actions_df.sort_values("timestamp").reset_index(drop=True)

    if not actions_df.empty:
        # Build tooltips
        tooltips = [format_snapshot_tooltip(row) for _, row in actions_df.iterrows()]

        # Long entries
        longs = actions_df[actions_df["signal"] == "LONG"]
        if not longs.empty:
            long_tips = [tooltips[i] for i in longs.index if i < len(tooltips)]
            fig.add_trace(
                go.Scatter(
                    x=longs["timestamp"], y=longs["close"],
                    mode="markers",
                    name="LONG Entry",
                    marker=dict(symbol="triangle-up", size=14, color="#26a69a",
                                line=dict(color="white", width=1)),
                    hovertext=long_tips,
                    hoverinfo="text",
                ),
                row=1, col=1,
            )

        # Short entries
        shorts = actions_df[actions_df["signal"] == "SHORT"]
        if not shorts.empty:
            short_tips = [tooltips[i] for i in shorts.index if i < len(tooltips)]
            fig.add_trace(
                go.Scatter(
                    x=shorts["timestamp"], y=shorts["close"],
                    mode="markers",
                    name="SHORT Entry",
                    marker=dict(symbol="triangle-down", size=14, color="#ef5350",
                                line=dict(color="white", width=1)),
                    hovertext=short_tips,
                    hoverinfo="text",
                ),
                row=1, col=1,
            )

        # Close signals
        closes = actions_df[actions_df["signal"] == "CLOSE"]
        if not closes.empty:
            close_tips = [tooltips[i] for i in closes.index if i < len(tooltips)]
            fig.add_trace(
                go.Scatter(
                    x=closes["timestamp"], y=closes["close"],
                    mode="markers",
                    name="CLOSE",
                    marker=dict(symbol="x", size=12, color="#ffa726",
                                line=dict(color="white", width=1)),
                    hovertext=close_tips,
                    hoverinfo="text",
                ),
                row=1, col=1,
            )

        # Pyramid adds
        pyramids = actions_df[actions_df.get("pyramid_add", pd.Series(False, index=actions_df.index)).astype(bool)]
        if not pyramids.empty:
            pyr_tips = [tooltips[i] for i in pyramids.index if i < len(tooltips)]
            fig.add_trace(
                go.Scatter(
                    x=pyramids["timestamp"], y=pyramids["close"],
                    mode="markers",
                    name="Pyramid Add",
                    marker=dict(symbol="diamond", size=10, color="#7e57c2",
                                line=dict(color="white", width=1)),
                    hovertext=pyr_tips,
                    hoverinfo="text",
                ),
                row=1, col=1,
            )

    # --- Row 2: Equity curve ---
    if "equity" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["timestamp"], y=df["equity"],
                mode="lines",
                name="Equity",
                line=dict(color="#42a5f5", width=2),
            ),
            row=2, col=1,
        )

    # Layout
    symbol = df["symbol"].iloc[0] if "symbol" in df.columns else ""
    fig.update_layout(
        title=f"{title} — {symbol}",
        template="plotly_dark",
        height=900,
        xaxis_rangeslider_visible=False,
        hovermode="closest",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Equity ($)", row=2, col=1)

    return fig


def main():
    parser = argparse.ArgumentParser(description="Interactive backtest visualizer")
    parser.add_argument("--run-dir", type=str, default=None,
                        help="Path to a backtest run directory (contains telemetry_logs/)")
    parser.add_argument("--telemetry-file", type=str, default=None,
                        help="Direct path to a telemetry JSONL file")
    parser.add_argument("--actions-file", type=str, default=None,
                        help="Direct path to an actions JSONL file")
    parser.add_argument("--mtf-lookbacks", type=str, default=None,
                        help="Comma-separated lookback periods (e.g. 24,72,168)")
    parser.add_argument("--output", type=str, default=None,
                        help="Save as HTML file instead of opening in browser")
    args = parser.parse_args()

    # Resolve telemetry file
    telemetry_path = args.telemetry_file
    actions_path = args.actions_file

    if telemetry_path is None and args.run_dir:
        telemetry_path = find_telemetry_file(args.run_dir)
        if telemetry_path is None:
            print(f"ERROR: No telemetry file found in {args.run_dir}/telemetry_logs/")
            print("Re-run your backtest to generate telemetry data.")
            sys.exit(1)
        if actions_path is None:
            actions_path = find_actions_file(args.run_dir)

    if telemetry_path is None:
        print("ERROR: Provide --run-dir or --telemetry-file")
        parser.print_help()
        sys.exit(1)

    print(f"Loading telemetry from: {telemetry_path}")
    telemetry_df = load_telemetry_jsonl(telemetry_path)
    print(f"Loaded {len(telemetry_df)} snapshots")

    actions_df = None
    if actions_path:
        print(f"Loading actions from: {actions_path}")
        actions_df = load_telemetry_jsonl(actions_path)
        print(f"Loaded {len(actions_df)} action snapshots")

    # Parse lookbacks
    mtf_lookbacks = None
    if args.mtf_lookbacks:
        mtf_lookbacks = [int(x.strip()) for x in args.mtf_lookbacks.split(",")]

    # Build and show figure
    fig = build_figure(
        telemetry_df=telemetry_df,
        actions_df=actions_df,
        mtf_lookbacks=mtf_lookbacks,
    )

    if args.output:
        fig.write_html(args.output)
        print(f"Saved to {args.output}")
    else:
        fig.show()


if __name__ == "__main__":
    main()
