#!/usr/bin/env python3
"""A/B experiment: OOS performance WITH vs WITHOUT FNG features.

Group A: All features EXCEPT sentiment (fng_raw, fng_ma_7, fng_ma_30, fng_zscore_30)
Group B: All features INCLUDING sentiment

Same train/test split, same model hyperparams, same everything else.
"""

import sys
import os
import logging
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptolab.config import Config
from cryptolab.data.manager import DataManager
from cryptolab.features.pipeline import FeaturePipeline
from cryptolab.ml.model import QuantileGBM
from cryptolab.ml.splitter import WalkForwardSplitter
from cryptolab.ml.trainer import Trainer, pinball_loss
from cryptolab.backtest.metrics import (
    drawdown_series, max_drawdown, sharpe_ratio, sortino_ratio,
    PERIODS_PER_YEAR,
)

logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

START_MS = 1609459200000  # 2021-01-01
SYMBOLS = ["BTC", "ETH", "SOL"]
TARGET = "fwd_return_4h"
TRAIN_END = "2024-01-01"
TEST_END = "2026-03-01"

# Identical model config for both groups
MODEL_CONFIG = {
    "backend": "lightgbm",
    "n_estimators": 500,
    "learning_rate": 0.03,
    "max_depth": 5,
    "subsample": 0.8,
    "colsample_bytree": 0.6,
    "reg_alpha": 0.1,
    "reg_lambda": 1.0,
    "min_child_samples": 100,
}

GROUPS_NO_FNG = [
    "technical", "donchian", "microstructure", "cross_asset",
    "temporal", "volatility", "momentum", "funding", "orderbook",
]
GROUPS_WITH_FNG = GROUPS_NO_FNG + ["sentiment"]


def precompute_signals(model, pipeline, df):
    """Pre-compute ML predictions for every bar.

    Uses the same approach as run_ml_backtest.py: compute ALL features per-symbol
    (including filling missing ones with 0), then predict.
    """
    symbols = df["symbol"].unique() if "symbol" in df.columns else [None]
    all_signals = []

    for sym in symbols:
        sym_df = df[df["symbol"] == sym].copy().reset_index(drop=True) if sym else df.copy()

        # Compute all feature blocks (including cross_asset which fills NaN gracefully)
        for block in pipeline.registry.get_groups(pipeline.groups):
            sym_df = block.compute(sym_df)

        # Get all registered feature names
        all_feature_names = pipeline.registry.all_feature_names(pipeline.groups)
        for fn in all_feature_names:
            if fn not in sym_df.columns:
                sym_df[fn] = 0.0

        feat_names = all_feature_names

        warmup = pipeline.warmup_bars
        valid_df = sym_df.iloc[warmup:].copy()
        if valid_df.empty:
            continue

        X = valid_df[feat_names].values.astype(np.float32)
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

        preds = {q: model._models[q].predict(X) for q in sorted(model._models.keys())}
        median = preds.get(0.5, np.zeros(len(X)))
        q10 = preds.get(0.1, median)
        q90 = preds.get(0.9, median)
        spread = np.abs(q90 - q10)
        confidence = 1.0 / (1.0 + spread * 100)

        signals_df = pd.DataFrame({
            "timestamp": pd.to_datetime(valid_df["timestamp"].values, utc=True),
            "symbol": sym if sym else "",
            "direction": np.sign(median),
            "median_return": median,
            "q10": q10,
            "q90": q90,
            "confidence": confidence,
        })
        all_signals.append(signals_df)

    return pd.concat(all_signals, ignore_index=True) if all_signals else pd.DataFrame()


def run_signal_backtest(sym_df, signals, cfg):
    """Run backtest using pre-computed signals. Returns metrics + equity curve."""
    equity = cfg.initial_capital
    cash = equity
    position_usd = 0.0
    entry_px = None
    peak_equity = equity
    taker_fee = cfg.taker_fee_bps / 10_000
    slippage = cfg.slippage_bps / 10_000

    max_pos_pct = cfg.portfolio_opt.max_position_pct
    max_lev = cfg.portfolio_opt.max_leverage
    kelly_cap = cfg.portfolio_opt.kelly_cap
    dd_max = cfg.portfolio_opt.dd_max
    dd_floor = cfg.portfolio_opt.dd_floor

    merged = sym_df.merge(signals, on="timestamp", how="left", suffixes=("", "_sig"))
    for col in ["direction", "median_return", "confidence", "q10", "q90"]:
        merged[col] = merged[col].fillna(0)

    equities = []
    timestamps = []
    trades = []
    prev_target = 0.0

    for i in range(len(merged)):
        bar = merged.iloc[i]
        open_px = bar["open"]
        close_px = bar["close"]

        if i > 0 and abs(prev_target - position_usd) > 0.01:
            buying = prev_target > position_usd
            fill_px = open_px * (1 + slippage) if buying else open_px * (1 - slippage)
            trade_size = abs(prev_target - position_usd)
            fee = trade_size * taker_fee

            trade_pnl = 0.0
            if abs(position_usd) > 0.01 and entry_px and entry_px > 0:
                if position_usd > 0:
                    trade_pnl = abs(position_usd) * (fill_px - entry_px) / entry_px
                else:
                    trade_pnl = abs(position_usd) * (entry_px - fill_px) / entry_px
                cash += trade_pnl

            cash -= fee
            position_usd = prev_target
            entry_px = fill_px if abs(position_usd) > 0.01 else None
            trades.append({"pnl": trade_pnl, "fee": fee})

        unrealized = 0.0
        if abs(position_usd) > 0.01 and entry_px and entry_px > 0:
            if position_usd > 0:
                unrealized = position_usd * (close_px - entry_px) / entry_px
            else:
                unrealized = abs(position_usd) * (entry_px - close_px) / entry_px
        equity = cash + unrealized
        peak_equity = max(peak_equity, equity)
        equities.append(equity)
        timestamps.append(bar["timestamp"])

        direction = int(bar["direction"])
        median_ret = bar["median_return"]
        conf = bar["confidence"]
        q10_val = bar["q10"]
        q90_val = bar["q90"]

        rebalance_period = 4
        min_signal_threshold = 0.0005

        if i % rebalance_period != 0:
            pass
        elif direction == 0 or abs(median_ret) < min_signal_threshold:
            prev_target = 0.0
        else:
            spread = abs(q90_val - q10_val)
            variance = max((spread / 2.58) ** 2, 1e-8)
            kelly_f = min(abs(median_ret) / variance, kelly_cap)
            dd = max(0, 1.0 - equity / peak_equity)
            dd_scalar = 1.0
            if dd > 0:
                dd_frac = min(dd / dd_max, 1.0)
                dd_scalar = 1.0 - dd_frac * (1.0 - dd_floor)
            raw_size = equity * kelly_f * conf * dd_scalar
            max_pos = equity * max_pos_pct * max_lev
            pos_size = min(raw_size, max_pos)
            prev_target = pos_size * direction

    eq_series = pd.Series(equities)
    dd_usd, dd_pct = max_drawdown(eq_series)
    ppy = PERIODS_PER_YEAR.get(cfg.interval, 8766)
    sr = sharpe_ratio(eq_series, ppy)
    so = sortino_ratio(eq_series, ppy)

    wins = sum(1 for t in trades if t["pnl"] > 0)
    total_closed = sum(1 for t in trades if t["pnl"] != 0)
    win_rate = (wins / total_closed * 100.0) if total_closed > 0 else 0.0

    return {
        "total_return_pct": (eq_series.iloc[-1] - cfg.initial_capital) / cfg.initial_capital * 100.0,
        "max_drawdown_pct": dd_pct,
        "sharpe": sr,
        "sortino": so,
        "total_trades": len(trades),
        "win_rate": win_rate,
        "equity_curve": pd.DataFrame({"timestamp": timestamps, "equity": equities}),
    }


def run_experiment(label, groups, train_df, test_df, full_df, cfg):
    """Train model and backtest for one group."""
    print(f"\n{'='*65}")
    print(f"  {label}")
    print(f"{'='*65}")

    pipeline = FeaturePipeline(groups=groups, warmup_bars=168)
    splitter = WalkForwardSplitter(n_folds=3, test_window_bars=720, embargo_bars=24)
    trainer = Trainer(pipeline, splitter, MODEL_CONFIG)

    print(f"  Training on {len(train_df)} rows...")
    model, report = trainer.train(train_df, target_col=TARGET)
    model._selected_features = None
    print(f"  CV dir_acc: {report.avg_directional_accuracy:.4f}, "
          f"pinball: {report.avg_pinball_loss:.6f}, "
          f"features: {report.n_features}")

    # Per-fold details
    for fr in report.fold_results:
        print(f"    Fold {fr.fold}: dir_acc={fr.directional_accuracy:.4f}, "
              f"pinball_q50={fr.pinball_losses.get(0.5, 0):.6f}")

    # Precompute signals on test with warmup
    test_with_warmup = []
    for sym in SYMBOLS:
        sym_train = train_df[train_df["symbol"] == sym].tail(200)
        sym_test = test_df[test_df["symbol"] == sym]
        combined = pd.concat([sym_train, sym_test], ignore_index=True)
        combined["symbol"] = sym
        test_with_warmup.append(combined)
    test_full = pd.concat(test_with_warmup, ignore_index=True)

    print(f"  Pre-computing OOS signals...")
    signals = precompute_signals(model, pipeline, test_full)

    # Per-symbol backtest
    all_metrics = {}
    all_eq_curves = {}
    for sym in SYMBOLS:
        sym_test = test_df[test_df["symbol"] == sym].reset_index(drop=True)
        sym_signals = signals[signals["symbol"] == sym].reset_index(drop=True)
        if len(sym_test) < 100:
            continue
        metrics = run_signal_backtest(sym_test, sym_signals, cfg)
        all_metrics[sym] = metrics
        all_eq_curves[sym] = metrics.pop("equity_curve")

        print(f"  {sym}: Return={metrics['total_return_pct']:+.2f}%, "
              f"Sharpe={metrics['sharpe']:.3f}, "
              f"MaxDD={metrics['max_drawdown_pct']:.2f}%, "
              f"WinRate={metrics['win_rate']:.1f}%")

    # Portfolio summary
    avg_ret = np.mean([m["total_return_pct"] for m in all_metrics.values()])
    avg_sharpe = np.mean([m["sharpe"] for m in all_metrics.values()])
    avg_sortino = np.mean([m["sortino"] for m in all_metrics.values()])
    worst_dd = max(m["max_drawdown_pct"] for m in all_metrics.values())
    avg_wr = np.mean([m["win_rate"] for m in all_metrics.values()])

    summary = {
        "avg_return_pct": avg_ret,
        "avg_sharpe": avg_sharpe,
        "avg_sortino": avg_sortino,
        "worst_max_dd_pct": worst_dd,
        "avg_win_rate": avg_wr,
        "cv_dir_acc": report.avg_directional_accuracy,
        "cv_pinball": report.avg_pinball_loss,
        "n_features": report.n_features,
        "per_symbol": all_metrics,
    }
    print(f"\n  Portfolio avg: Return={avg_ret:+.2f}%, Sharpe={avg_sharpe:.3f}, "
          f"MaxDD={worst_dd:.2f}%, WinRate={avg_wr:.1f}%")

    # Per-quarter analysis
    print(f"\n  Per-Quarter OOS Breakdown:")
    quarters = {}
    for sym, eq_df in all_eq_curves.items():
        eq_df = eq_df.copy()
        eq_df["timestamp"] = pd.to_datetime(eq_df["timestamp"])
        eq_df["quarter"] = eq_df["timestamp"].dt.to_period("Q").astype(str)
        for q_label, q_group in eq_df.groupby("quarter"):
            if len(q_group) < 50:
                continue
            eq_s = q_group["equity"].reset_index(drop=True)
            q_ret = (eq_s.iloc[-1] - eq_s.iloc[0]) / eq_s.iloc[0] * 100.0
            if q_label not in quarters:
                quarters[q_label] = []
            quarters[q_label].append(q_ret)

    for q_label in sorted(quarters.keys()):
        rets = quarters[q_label]
        avg_q_ret = np.mean(rets)
        print(f"    {q_label}: avg_return={avg_q_ret:+.2f}% ({len(rets)} symbols)")

    summary["quarters"] = {q: float(np.mean(r)) for q, r in sorted(quarters.items())}
    return summary


def main():
    print("=" * 65)
    print("  FNG A/B OOS Experiment")
    print(f"  Symbols: {SYMBOLS}")
    print(f"  Train: 2021-01-01 ~ {TRAIN_END}")
    print(f"  OOS:   {TRAIN_END} ~ {TEST_END}")
    print(f"  Target: {TARGET}")
    print("=" * 65)

    cfg = Config()
    cfg.interval = "1h"

    dm = DataManager()
    print("Loading data...")
    full_df = dm.get_training_dataset(SYMBOLS, interval="1h", start_ms=START_MS)
    if full_df.empty:
        print("No data. Run seed_cache.py first.")
        sys.exit(1)

    train_end_ts = pd.Timestamp(TRAIN_END, tz="UTC")
    test_end_ts = pd.Timestamp(TEST_END, tz="UTC")

    train_df = full_df[full_df["timestamp"] < train_end_ts].copy()
    test_df = full_df[
        (full_df["timestamp"] >= train_end_ts) & (full_df["timestamp"] < test_end_ts)
    ].copy()

    print(f"Train: {len(train_df)} rows, OOS: {len(test_df)} rows")

    # Run both experiments
    result_a = run_experiment(
        "Group A: WITHOUT FNG", GROUPS_NO_FNG,
        train_df, test_df, full_df, cfg
    )
    result_b = run_experiment(
        "Group B: WITH FNG", GROUPS_WITH_FNG,
        train_df, test_df, full_df, cfg
    )

    # Final comparison
    print(f"\n{'='*65}")
    print(f"  FINAL COMPARISON")
    print(f"{'='*65}")
    print(f"{'Metric':<25s} {'No FNG':>12s} {'With FNG':>12s} {'Delta':>12s}")
    print(f"{'-'*65}")

    comparisons = [
        ("OOS Avg Return %", result_a["avg_return_pct"], result_b["avg_return_pct"]),
        ("OOS Avg Sharpe", result_a["avg_sharpe"], result_b["avg_sharpe"]),
        ("OOS Avg Sortino", result_a["avg_sortino"], result_b["avg_sortino"]),
        ("OOS Worst MaxDD %", result_a["worst_max_dd_pct"], result_b["worst_max_dd_pct"]),
        ("OOS Avg Win Rate %", result_a["avg_win_rate"], result_b["avg_win_rate"]),
        ("CV Dir Accuracy", result_a["cv_dir_acc"], result_b["cv_dir_acc"]),
        ("CV Pinball Loss", result_a["cv_pinball"], result_b["cv_pinball"]),
        ("N Features", result_a["n_features"], result_b["n_features"]),
    ]

    for label, va, vb in comparisons:
        delta = vb - va
        sign = "+" if delta > 0 else ""
        print(f"  {label:<23s} {va:>12.4f} {vb:>12.4f} {sign}{delta:>11.4f}")

    # Per-symbol comparison
    print(f"\n  Per-Symbol Sharpe Comparison:")
    for sym in SYMBOLS:
        sa = result_a["per_symbol"].get(sym, {}).get("sharpe", 0)
        sb = result_b["per_symbol"].get(sym, {}).get("sharpe", 0)
        delta = sb - sa
        winner = "FNG+" if delta > 0.05 else ("FNG-" if delta < -0.05 else "~")
        print(f"    {sym}: {sa:.3f} ->{sb:.3f} (delta={delta:+.3f}) [{winner}]")

    # Per-quarter comparison
    print(f"\n  Per-Quarter Avg Return Comparison:")
    all_qs = sorted(set(list(result_a.get("quarters", {}).keys()) +
                        list(result_b.get("quarters", {}).keys())))
    for q in all_qs:
        ra = result_a.get("quarters", {}).get(q, 0)
        rb = result_b.get("quarters", {}).get(q, 0)
        delta = rb - ra
        winner = "FNG+" if delta > 0.5 else ("FNG-" if delta < -0.5 else "~")
        print(f"    {q}: {ra:+.2f}% ->{rb:+.2f}% (delta={delta:+.2f}%) [{winner}]")

    # Verdict
    sharpe_delta = result_b["avg_sharpe"] - result_a["avg_sharpe"]
    print(f"\n{'='*65}")
    if sharpe_delta > 0.05:
        print(f"  VERDICT: FNG IMPROVES OOS (Sharpe delta = {sharpe_delta:+.3f})")
        print(f"  ->Keep sentiment features in production pipeline")
    elif sharpe_delta < -0.05:
        print(f"  VERDICT: FNG HURTS OOS (Sharpe delta = {sharpe_delta:+.3f})")
        print(f"  ->FNG overfits IS, remove from production pipeline")
    else:
        print(f"  VERDICT: FNG has NO SIGNIFICANT EFFECT (Sharpe delta = {sharpe_delta:+.3f})")
        print(f"  ->FNG adds complexity without benefit, consider removing")
    print(f"{'='*65}")


if __name__ == "__main__":
    main()
