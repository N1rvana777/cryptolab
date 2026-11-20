#!/usr/bin/env python3
"""Generate a professional CryptoLab pipeline architecture diagram for social media."""

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch


def draw_rounded_box(ax, x, y, w, h, title, items, color, title_color="white",
                     fontsize=9.5, title_fontsize=13):
    """Draw a rounded box with title bar and item list."""
    # Main box body
    body = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.12",
                          facecolor=color, edgecolor="none", alpha=0.12, zorder=1)
    ax.add_patch(body)

    # Border
    border = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.12",
                            facecolor="none", edgecolor=color, linewidth=2.0,
                            alpha=0.7, zorder=2)
    ax.add_patch(border)

    # Title bar
    title_h = 0.45
    title_box = FancyBboxPatch((x + 0.05, y + h - title_h - 0.05), w - 0.10, title_h,
                               boxstyle="round,pad=0.08", facecolor=color,
                               edgecolor="none", alpha=0.9, zorder=3)
    ax.add_patch(title_box)

    # Title text
    ax.text(x + w / 2, y + h - title_h / 2 - 0.02, title, fontsize=title_fontsize,
            fontweight="bold", color=title_color, ha="center", va="center",
            zorder=4, fontfamily="monospace")

    # Items
    line_spacing = 0.32
    item_y = y + h - title_h - 0.35
    for item in items:
        if item.startswith("---"):
            # Section divider
            ax.plot([x + 0.2, x + w - 0.2], [item_y + 0.12, item_y + 0.12],
                    color=color, alpha=0.35, linewidth=0.8, zorder=3)
            item_y -= 0.15
        else:
            # Color code: filenames in bright, descriptions dimmer
            ax.text(x + 0.25, item_y, item, fontsize=fontsize, color="#c9d1d9",
                    ha="left", va="center", zorder=4, fontfamily="monospace")
            item_y -= line_spacing


def draw_arrow(ax, start, end, color="#555555", style="-|>", lw=2.0,
               connectionstyle="arc3,rad=0"):
    """Draw a curved arrow between two points."""
    arrow = FancyArrowPatch(start, end, arrowstyle=style, color=color,
                            linewidth=lw, connectionstyle=connectionstyle,
                            mutation_scale=15, zorder=5, alpha=0.6)
    ax.add_patch(arrow)


def main():
    fig, ax = plt.subplots(1, 1, figsize=(28, 18))
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#0d1117")

    ax.set_xlim(-0.5, 20)
    ax.set_ylim(-1.5, 14.5)
    ax.set_aspect("equal")
    ax.axis("off")

    # ============ TITLE ============
    ax.text(10, 13.8, "CryptoLab", fontsize=44, fontweight="bold",
            color="#58a6ff", ha="center", va="center", fontfamily="monospace")
    ax.text(10, 13.1, "Quantitative Cryptocurrency Trading System",
            fontsize=17, color="#8b949e", ha="center", va="center", fontfamily="monospace")
    ax.text(10, 12.65, "57 modules  |  12 test suites  |  17 experiment scripts  |  22 coins  |  Live on Hyperliquid",
            fontsize=12, color="#6e7681", ha="center", va="center", fontfamily="monospace")

    # Color palette
    C_DATA = "#3fb950"
    C_FEAT = "#d29922"
    C_ML = "#bc8cff"
    C_STRAT = "#58a6ff"
    C_BT = "#f0883e"
    C_EXEC = "#f85149"
    C_RISK = "#ff7b72"
    C_SCRIPT = "#79c0ff"

    # ============ ROW 1: DATA LAYER ============
    bw1 = 3.6  # box width
    bh1 = 3.2  # box height
    row1_y = 8.8

    draw_rounded_box(ax, 0, row1_y, bw1, bh1, "DATA SOURCES", [
        "OKX Perpetuals API",
        "Binance Perpetuals API",
        "Hyperliquid API",
        "---",
        "Yahoo Finance (trad)",
        "alternative.me (FNG)",
        "Reddit API",
    ], C_DATA, fontsize=9.5)

    draw_rounded_box(ax, 4.2, row1_y, 3.8, bh1, "DATA LAYER", [
        "manager.py     DataManager",
        "cache.py       ParquetCache",
        "validate.py    Data quality",
        "types.py       Symbol maps",
        "---",
        "fetchers/okx.py",
        "fetchers/binance.py",
        "fetchers/hyperliquid.py",
    ], C_DATA, fontsize=9)

    draw_rounded_box(ax, 8.6, row1_y, 3.6, bh1, "DATA STORAGE", [
        "data/cache/",
        "  okx_{SYM}_{1h,4h}.parquet",
        "  hl_{SYM}_4h.parquet",
        "  funding_{SYM}.parquet",
        "---",
        "data/collection/",
        "  crypto_data.db (SQLite)",
        "  fng_history.csv",
    ], C_DATA, fontsize=9)

    draw_rounded_box(ax, 12.8, row1_y, 3.4, bh1, "INDICATORS", [
        "core.py",
        "  ATR, RSI, Bollinger",
        "  EMA, VWAP, ADX",
        "---",
        "donchian.py",
        "  Channel computation",
        "---",
        "cross_sectional.py",
    ], C_DATA, fontsize=9)

    draw_rounded_box(ax, 16.8, row1_y, 2.8, bh1, "CONFIG", [
        "config.py",
        "  FeatureConfig",
        "  MLConfig",
        "  PortfolioConfig",
        "  Config (main)",
        "---",
        "utils.py",
        "  interval_to_ms",
    ], C_DATA, fontsize=9)

    # ============ ROW 2: FEATURES + ML + STRATEGY ============
    row2_y = 4.8

    draw_rounded_box(ax, 0, row2_y, 5.5, 3.4, "FEATURE ENGINEERING  (138 features)", [
        "pipeline.py      Orchestrator",
        "leakage_guard.py  4-layer bias check",
        "targets.py        fwd_return labels",
        "---",
        "technical.py   40   momentum.py   16",
        "volatility.py  18   funding.py    18",
        "orderbook.py   18   donchian.py   13",
        "microstructure 15   temporal.py   12",
        "cross_asset.py 10   sentiment.py   4",
    ], C_FEAT, fontsize=9.5)

    draw_rounded_box(ax, 6.1, row2_y, 4.2, 3.4, "ML PIPELINE", [
        "model.py",
        "  QuantileGBM (LightGBM)",
        "  5 quantiles: 10/25/50/75/90",
        "splitter.py",
        "  WalkForwardSplitter",
        "  KFold FORBIDDEN",
        "trainer.py       Training loop",
        "predictor.py     Inference",
        "drift_detector.py  2s/3s alerts",
        "feature_importance.py SHAP",
    ], C_ML, fontsize=9)

    draw_rounded_box(ax, 10.9, row2_y, 4.2, 3.4, "STRATEGIES", [
        "base.py",
        "  BaseStrategy ABC",
        "  StrategySignal interface",
        "---",
        "donchian_mtf.py  [PROD]",
        "  3-TF Donchian Breakout",
        "  ADX Regime Filter",
        "  Vol target + DD scaling",
        "---",
        "donchian.py     Single-TF",
        "ml_strategy.py  ML adapter",
    ], C_STRAT, fontsize=9)

    draw_rounded_box(ax, 15.7, row2_y, 3.9, 3.4, "PORTFOLIO", [
        "optimizer.py",
        "  Kelly criterion",
        "  Position sizing",
        "---",
        "risk_budget.py",
        "  Risk budgeting",
        "  Cross-asset allocation",
        "---",
        "Vol target: 15% annual",
        "DD floor: 25-30%",
    ], C_ML, fontsize=9)

    # ============ ROW 3: BACKTEST + EXECUTION ============
    row3_y = 0.5

    draw_rounded_box(ax, 0, row3_y, 4.8, 3.6, "BACKTESTING", [
        "engine.py",
        "  T+1 execution model",
        "  Taker fee: 3.5 bps",
        "  Slippage: 15 bps",
        "  Gap stop simulation",
        "---",
        "metrics.py     Sharpe/Sortino/Calmar",
        "               MaxDD, bootstrap CI",
        "bias_audit.py  Fill timing check",
        "telemetry.py   JSONL snapshots",
        "regime_monitor.py",
    ], C_BT, fontsize=9)

    draw_rounded_box(ax, 5.4, row3_y, 4.8, 3.6, "LIVE EXECUTION", [
        "orchestrator.py",
        "  8H candle polling (30s)",
        "  Crash recovery",
        "  22 coins x B0 combo",
        "---",
        "position_manager.py",
        "  Order execution",
        "  CSV trade logging",
        "---",
        "hl_client.py    HL SDK wrapper",
        "kill_switch.py  3-state safety",
    ], C_EXEC, fontsize=9)

    draw_rounded_box(ax, 10.8, row3_y, 3.8, 3.6, "SAFETY & RISK", [
        "KillSwitch States:",
        "  NORMAL",
        "  -> REDUCE_ONLY",
        "  -> HALTED",
        "---",
        "Regime Filter:",
        "  ADX >= 25: full size",
        "  ADX 20-25: half size",
        "  ADX < 20:  no entry",
        "  Vol contraction: block",
    ], C_RISK, fontsize=9)

    draw_rounded_box(ax, 15.2, row3_y, 4.4, 3.6, "SCRIPTS & TESTS", [
        "seed_cache.py      Data download",
        "live_donchian.py   Live entry",
        "review_live.py     Dashboard",
        "data_collector.py  Daemon",
        "---",
        "donchian_full_sweep.py",
        "institutional_experiment.py",
        "tsmom_experiment.py",
        "cross_asset_sweep.py",
        "+ 9 more experiments",
        "---",
        "12 test suites (pytest)",
    ], C_SCRIPT, fontsize=8.5)

    # ============ ARROWS ============
    # Row 1 horizontal
    draw_arrow(ax, (3.6, 10.4), (4.2, 10.4), C_DATA, lw=2.5)
    draw_arrow(ax, (8.0, 10.4), (8.6, 10.4), C_DATA, lw=2.5)
    draw_arrow(ax, (12.2, 10.4), (12.8, 10.4), C_DATA, lw=2.5)

    # Row 1 -> Row 2 (vertical)
    draw_arrow(ax, (5.5, 8.8), (3.5, 8.2), C_FEAT, lw=2.5,
               connectionstyle="arc3,rad=0.15")
    draw_arrow(ax, (7.5, 8.8), (12.5, 8.2), C_STRAT, lw=2.5,
               connectionstyle="arc3,rad=-0.2")

    # Row 2 horizontal
    draw_arrow(ax, (5.5, 6.5), (6.1, 6.5), C_FEAT, lw=2.5)
    draw_arrow(ax, (10.3, 6.5), (10.9, 6.5), C_ML, lw=2.5)
    draw_arrow(ax, (15.1, 6.5), (15.7, 6.5), C_STRAT, lw=2.5)

    # Row 2 -> Row 3 (vertical)
    draw_arrow(ax, (12.0, 4.8), (3.5, 4.1), C_BT, lw=2.5,
               connectionstyle="arc3,rad=0.15")
    draw_arrow(ax, (13.5, 4.8), (8.5, 4.1), C_EXEC, lw=2.5,
               connectionstyle="arc3,rad=0.15")

    # Execution -> Safety
    draw_arrow(ax, (10.2, 2.3), (10.8, 2.3), C_EXEC, lw=2.5)

    # ============ BOTTOM BANNER ============
    ax.text(10, -0.5,
            "LIVE  |  $357 equity  |  22 coins  |  3x leverage  |  Hyperliquid Perpetuals  |  B0 Regime Filter",
            fontsize=13, color=C_EXEC, ha="center", va="center", fontfamily="monospace",
            fontweight="bold", alpha=0.8)

    ax.text(10, -1.1, "github.com/n1rva/cryptolab",
            fontsize=10, color="#30363d", ha="center", va="center", fontfamily="monospace")

    plt.tight_layout(pad=0.3)
    plt.savefig("demo_output/cryptolab_pipeline.png", dpi=180, bbox_inches="tight",
                facecolor="#0d1117", edgecolor="none")
    print("Saved to demo_output/cryptolab_pipeline.png")


if __name__ == "__main__":
    main()
