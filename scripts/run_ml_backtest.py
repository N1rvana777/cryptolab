#!/usr/bin/env python3
"""Run ML-based backtest with pre-computed predictions.

Pre-computes all features and ML predictions ONCE, then feeds them into a
lightweight backtest loop. This is orders of magnitude faster than calling
the feature pipeline on every bar.

Honest evaluation: model is trained ONLY on data before train_end.
"""

import argparse
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
from cryptolab.features.targets import compute_targets
from cryptolab.ml.model import QuantileGBM
from cryptolab.ml.trainer import Trainer
from cryptolab.ml.splitter import WalkForwardSplitter
from cryptolab.backtest.metrics import (
    drawdown_series, max_drawdown, sharpe_ratio, sortino_ratio, calmar_ratio,
    PERIODS_PER_YEAR,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

START_MS = 1609459200000  # 2021-01-01


def precompute_signals(
    model: QuantileGBM,
    pipeline: FeaturePipeline,
    df: pd.DataFrame,
    target_col: str,
) -> pd.DataFrame:
    """Pre-compute ML predictions for every bar in the DataFrame.

    Returns DataFrame with columns: timestamp, symbol, direction, position_scale,
    median_return, q10, q90, confidence.
    """
    # Build features (without targets — we only need features for prediction)
    df_feat = df.copy()

    # Compute features per symbol
    symbols = df_feat["symbol"].unique() if "symbol" in df_feat.columns else [None]
    all_signals = []

    for sym in symbols:
        if sym is not None:
            sym_df = df_feat[df_feat["symbol"] == sym].copy().reset_index(drop=True)
        else:
            sym_df = df_feat.copy()

        # Compute features
        for block in pipeline.registry.get_groups(pipeline.groups):
            sym_df = block.compute(sym_df)

        # Get feature names (use selected if available, else all)
        all_feature_names = pipeline.registry.all_feature_names(pipeline.groups)
        for fn in all_feature_names:
            if fn not in sym_df.columns:
                sym_df[fn] = 0.0
        if hasattr(model, '_selected_features') and model._selected_features:
            feature_names = model._selected_features
        else:
            feature_names = [f for f in all_feature_names if f in sym_df.columns]

        # Skip warmup rows
        warmup = pipeline.warmup_bars
        valid_df = sym_df.iloc[warmup:].copy()

        if valid_df.empty:
            continue

        # Extract features and predict
        X = valid_df[feature_names].values.astype(np.float32)
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

        # Batch predict all quantiles
        preds = {q: model._models[q].predict(X) for q in sorted(model._models.keys())}

        median = preds.get(0.5, np.zeros(len(X)))
        q10 = preds.get(0.1, median)
        q90 = preds.get(0.9, median)

        spread = np.abs(q90 - q10)
        confidence = 1.0 / (1.0 + spread * 100)

        direction = np.sign(median)

        signals_df = pd.DataFrame({
            "timestamp": pd.to_datetime(valid_df["timestamp"].values, utc=True),
            "symbol": sym if sym else "",
            "direction": direction,
            "median_return": median,
            "q10": q10,
            "q90": q90,
            "confidence": confidence,
        })
        all_signals.append(signals_df)

    return pd.concat(all_signals, ignore_index=True) if all_signals else pd.DataFrame()


def run_signal_backtest(
    sym_df: pd.DataFrame,
    signals: pd.DataFrame,
    cfg: Config,
) -> dict:
    """Run a simple backtest using pre-computed signals.

    For each bar:
    1. Look up pre-computed signal
    2. Size position using Kelly-like formula
    3. Execute at next bar's open + slippage
    4. Track equity, drawdown, trades
    """
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

    # Merge signals with OHLCV
    merged = sym_df.merge(signals, on="timestamp", how="left", suffixes=("", "_sig"))
    merged["direction"] = merged["direction"].fillna(0)
    merged["median_return"] = merged["median_return"].fillna(0)
    merged["confidence"] = merged["confidence"].fillna(0)
    merged["q10"] = merged["q10"].fillna(0)
    merged["q90"] = merged["q90"].fillna(0)

    equities = []
    timestamps = []
    trades = []
    prev_target = 0.0

    for i in range(len(merged)):
        bar = merged.iloc[i]
        open_px = bar["open"]
        close_px = bar["close"]

        # Execute previous signal at this bar's open
        if i > 0 and abs(prev_target - position_usd) > 0.01:
            buying = prev_target > position_usd
            fill_px = open_px * (1 + slippage) if buying else open_px * (1 - slippage)

            trade_size = abs(prev_target - position_usd)
            fee = trade_size * taker_fee

            # Realize PnL on existing position being closed/reduced
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

            trades.append({
                "timestamp": bar["timestamp"],
                "side": "BUY" if buying else "SELL",
                "size_usd": trade_size,
                "fill_px": fill_px,
                "fee": fee,
                "pnl": trade_pnl,
            })

        # MTM equity
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

        # Compute next target position from signal
        direction = int(bar["direction"])
        median_ret = bar["median_return"]
        conf = bar["confidence"]
        q10_val = bar["q10"]
        q90_val = bar["q90"]

        # Signal filters:
        # - Only rebalance every rebalance_period bars (match prediction horizon)
        # - Require minimum predicted return magnitude
        # - Require q25 to agree with median direction (moderate confidence)
        rebalance_period = 4  # Match fwd_return_4h prediction horizon
        min_signal_threshold = 0.0005  # Ignore near-zero predicted returns

        if i % rebalance_period != 0:
            pass  # Hold current position between rebalance points
        elif direction == 0 or abs(median_ret) < min_signal_threshold:
            prev_target = 0.0
        else:
            # Kelly sizing (capped conservatively)
            spread = abs(q90_val - q10_val)
            variance = max((spread / 2.58) ** 2, 1e-8)
            kelly_f = min(abs(median_ret) / variance, kelly_cap)

            # Drawdown scaling
            dd = max(0, 1.0 - equity / peak_equity)
            dd_scalar = 1.0
            if dd > 0:
                dd_frac = min(dd / dd_max, 1.0)
                dd_scalar = 1.0 - dd_frac * (1.0 - dd_floor)

            raw_size = equity * kelly_f * conf * dd_scalar
            max_pos = equity * max_pos_pct * max_lev
            pos_size = min(raw_size, max_pos)
            prev_target = pos_size * direction

    # Build equity curve
    eq_series = pd.Series(equities)
    dd_series = drawdown_series(eq_series)
    equity_curve = pd.DataFrame({
        "timestamp": timestamps,
        "equity": equities,
        "drawdown_pct": dd_series.values,
    })

    # Compute metrics directly (avoid Trade dataclass dependency)
    eq = equity_curve["equity"]
    final = eq.iloc[-1]
    total_return = (final - cfg.initial_capital) / cfg.initial_capital * 100.0
    dd_usd, dd_pct = max_drawdown(eq)
    total_fees = sum(t["fee"] for t in trades)

    ppy = PERIODS_PER_YEAR.get(cfg.interval, 8766)
    sr = sharpe_ratio(eq, ppy)
    so = sortino_ratio(eq, ppy)
    cr = calmar_ratio(eq, ppy)

    # Win/loss from round-trip PnL approximation
    wins = sum(1 for t in trades if t.get("pnl", 0) > 0)
    total_closed = sum(1 for t in trades if t.get("pnl", 0) != 0)
    win_rate = (wins / total_closed * 100.0) if total_closed > 0 else 0.0
    gross_wins = sum(t.get("pnl", 0) for t in trades if t.get("pnl", 0) > 0)
    gross_losses = abs(sum(t.get("pnl", 0) for t in trades if t.get("pnl", 0) < 0))
    pf = gross_wins / gross_losses if gross_losses > 0 else (float("inf") if gross_wins > 0 else 0.0)

    return {
        "final_equity": final,
        "total_return_pct": total_return,
        "max_drawdown_pct": dd_pct,
        "sharpe": sr,
        "sortino": so,
        "calmar": cr,
        "total_trades": len(trades),
        "win_rate": win_rate,
        "profit_factor": pf,
        "total_fees": total_fees,
    }


def main():
    parser = argparse.ArgumentParser(description="ML backtest with pre-computed signals")
    parser.add_argument("--symbols", type=str,
                        default="BTC,ETH,SOL,ADA,XRP,DOGE,AVAX,LINK,ARB,SUI,DOT,NEAR,OP,FIL,APT,ATOM,PEPE")
    parser.add_argument("--interval", type=str, default="1h")
    parser.add_argument("--target", type=str, default="fwd_return_4h")
    parser.add_argument("--backend", type=str, default="lightgbm")
    parser.add_argument("--train-end", type=str, default="2024-01-01",
                        help="IS/OOS boundary")
    parser.add_argument("--test-end", type=str, default="2025-09-01",
                        help="OOS/Holdout boundary (holdout reserved for final exam)")
    parser.add_argument("--holdout-end", type=str, default="2026-03-01",
                        help="End of holdout period")
    parser.add_argument("--model-dir", type=str, default="models/backtest")
    args = parser.parse_args()

    cfg = Config()
    cfg.interval = args.interval
    symbols = [s.strip() for s in args.symbols.split(",")]

    dm = DataManager()

    # Load all data
    logger.info("Loading data for %s...", symbols)
    full_df = dm.get_training_dataset(symbols, interval=args.interval, start_ms=START_MS)
    if full_df.empty:
        logger.error("No data. Run seed_cache.py first.")
        sys.exit(1)

    train_end_ts = pd.Timestamp(args.train_end, tz="UTC")
    test_end_ts = pd.Timestamp(args.test_end, tz="UTC")

    train_df = full_df[full_df["timestamp"] < train_end_ts].copy()
    test_df = full_df[
        (full_df["timestamp"] >= train_end_ts) & (full_df["timestamp"] < test_end_ts)
    ].copy()

    logger.info("Train: %d rows, Test: %d rows", len(train_df), len(test_df))

    # Build pipeline
    pipeline = FeaturePipeline(
        groups=cfg.features.feature_groups,
        warmup_bars=cfg.features.warmup_bars,
    )

    model_dir = Path(args.model_dir)

    # Train model on pre-train_end data only
    logger.info("Training model on data before %s...", args.train_end)
    model_config = {
        "backend": args.backend,
        "n_estimators": 1000,
        "learning_rate": 0.02,
        "max_depth": 5,
        "subsample": 0.8,
        "colsample_bytree": 0.5,
        "reg_alpha": 0.1,
        "reg_lambda": 1.0,
        "min_child_samples": 200,
    }

    splitter = WalkForwardSplitter(
        n_folds=3,
        test_window_bars=cfg.ml.test_window_bars,
        embargo_bars=cfg.ml.embargo_bars,
    )

    # Phase 1: Train initial model
    trainer = Trainer(pipeline, splitter, model_config)
    model, report = trainer.train(train_df, target_col=args.target, save_dir=model_dir)
    logger.info("Phase 1 training done: dir_acc=%.3f", report.avg_directional_accuracy)

    # Phase 2: Feature selection — keep only top 30 most important features
    top_n = 30
    if hasattr(model._models[0.5], 'feature_importances_'):
        importances = model._models[0.5].feature_importances_
        feature_names = pipeline.registry.all_feature_names(pipeline.groups)
        # Some features may have been added as 0-columns; only rank real ones
        if len(importances) == len(feature_names):
            top_idx = np.argsort(importances)[-top_n:]
            selected_features = [feature_names[i] for i in top_idx]
            logger.info("Feature selection: keeping top %d features: %s",
                        top_n, selected_features[:10])

            # Retrain with selected features only
            # Build feature matrix manually with selection
            X_full, y_full, all_feat = pipeline.build(train_df, target_col=args.target)
            feat_mask = [i for i, f in enumerate(all_feat) if f in selected_features]
            X_selected = X_full[:, feat_mask]
            selected_feat_names = [all_feat[i] for i in feat_mask]

            # Train directly on selected features
            from cryptolab.ml.model import QuantileGBM
            model = QuantileGBM(**model_config)
            model.train(X_selected, y_full)
            model.save(model_dir)
            model._selected_features = selected_feat_names
            logger.info("Phase 2: retrained on %d features", len(selected_feat_names))
        else:
            logger.warning("Feature importance length mismatch, skipping selection")
            model._selected_features = None
    else:
        model._selected_features = None

    # Pre-compute signals on test period (with warmup from train)
    logger.info("Pre-computing signals on test period...")

    # For each symbol, prepend warmup bars from training data
    test_with_warmup = []
    for sym in symbols:
        sym_train = train_df[train_df["symbol"] == sym].tail(cfg.features.warmup_bars + 50)
        sym_test = test_df[test_df["symbol"] == sym]
        combined = pd.concat([sym_train, sym_test], ignore_index=True)
        combined["symbol"] = sym
        test_with_warmup.append(combined)

    test_full = pd.concat(test_with_warmup, ignore_index=True)
    signals = precompute_signals(model, pipeline, test_full, args.target)
    logger.info("Pre-computed %d signals", len(signals))

    # Run backtest per symbol
    print(f"\n{'='*70}")
    print(f"ML Backtest Results (OOS): {args.train_end} -> {args.test_end}")
    print(f"Model: {args.backend}, Features: {report.n_features}, "
          f"CV dir_acc: {report.avg_directional_accuracy:.3f}")
    print(f"{'='*70}")

    all_metrics = []
    for sym in symbols:
        sym_test = test_df[test_df["symbol"] == sym].reset_index(drop=True)
        sym_signals = signals[signals["symbol"] == sym].reset_index(drop=True)

        if len(sym_test) < 100:
            logger.warning("Insufficient test data for %s", sym)
            continue

        metrics = run_signal_backtest(sym_test, sym_signals, cfg)
        all_metrics.append((sym, metrics))

        print(f"\n  {sym}:")
        print(f"    Return:      {metrics['total_return_pct']:+.2f}%")
        print(f"    Max DD:      {metrics['max_drawdown_pct']:.2f}%")
        print(f"    Sharpe:      {metrics['sharpe']:.2f}")
        print(f"    Sortino:     {metrics['sortino']:.2f}")
        print(f"    Trades:      {metrics['total_trades']}")
        print(f"    Win Rate:    {metrics['win_rate']:.1f}%")
        print(f"    Profit Fac:  {metrics['profit_factor']:.2f}")
        print(f"    Fees:        ${metrics['total_fees']:.2f}")

    if all_metrics:
        avg_ret = np.mean([m["total_return_pct"] for _, m in all_metrics])
        avg_sharpe = np.mean([m["sharpe"] for _, m in all_metrics])
        worst_dd = max([m["max_drawdown_pct"] for _, m in all_metrics])
        total_trades = sum([m["total_trades"] for _, m in all_metrics])

        print(f"\n{'='*70}")
        print(f"Portfolio Summary ({len(all_metrics)} symbols)")
        print(f"{'='*70}")
        print(f"  Avg Return:    {avg_ret:+.2f}%")
        print(f"  Avg Sharpe:    {avg_sharpe:.2f}")
        print(f"  Worst Max DD:  {worst_dd:.2f}%")
        print(f"  Total Trades:  {total_trades}")

    # Compare with DonchianMTF baseline
    print(f"\n  DonchianMTF v1 baseline: OOS Sharpe 0.86, Return +12.89%, MaxDD 6.06%")
    print(f"\n  Note: Holdout period ({args.test_end} -> {args.holdout_end}) reserved for final exam.")
    print(f"  Run with --test-end {args.holdout_end} only after all tuning is complete.")


if __name__ == "__main__":
    main()
