#!/usr/bin/env python3
"""Train ML model for crypto signal prediction."""

import argparse
import sys
import os
import logging
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptolab.config import Config
from cryptolab.data.manager import DataManager
from cryptolab.features.pipeline import FeaturePipeline
from cryptolab.ml.splitter import WalkForwardSplitter
from cryptolab.ml.trainer import Trainer
from cryptolab.ml.feature_importance import get_feature_importance, print_importance_report

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# 2021-01-01 UTC
START_MS = 1609459200000


def main():
    parser = argparse.ArgumentParser(description="Train ML model")
    parser.add_argument("--symbols", type=str, default="BTC,ETH,SOL,ADA,XRP",
                        help="Comma-separated symbols")
    parser.add_argument("--interval", type=str, default="1h")
    parser.add_argument("--target", type=str, default="fwd_return_4h")
    parser.add_argument("--backend", type=str, default="lightgbm",
                        choices=["lightgbm", "xgboost"])
    parser.add_argument("--n-folds", type=int, default=5)
    parser.add_argument("--save-dir", type=str, default="models/latest")
    args = parser.parse_args()

    cfg = Config()
    symbols = [s.strip() for s in args.symbols.split(",")]

    # Load data
    logger.info("Loading training data for %s...", symbols)
    dm = DataManager()
    df = dm.get_training_dataset(symbols, interval=args.interval, start_ms=START_MS)

    if df.empty:
        logger.error("No data loaded. Run seed_cache.py first.")
        sys.exit(1)

    logger.info("Loaded %d rows across %d symbols", len(df), df["symbol"].nunique())

    # Build pipeline
    pipeline = FeaturePipeline(
        groups=cfg.features.feature_groups,
        warmup_bars=cfg.features.warmup_bars,
    )

    splitter = WalkForwardSplitter(
        n_folds=args.n_folds,
        test_window_bars=cfg.ml.test_window_bars,
        embargo_bars=cfg.ml.embargo_bars,
    )

    model_config = {
        "backend": args.backend,
        "n_estimators": cfg.ml.n_estimators,
        "learning_rate": cfg.ml.learning_rate,
        "max_depth": cfg.ml.max_depth,
        "subsample": cfg.ml.subsample,
        "colsample_bytree": cfg.ml.colsample_bytree,
        "reg_alpha": cfg.ml.reg_alpha,
        "reg_lambda": cfg.ml.reg_lambda,
    }

    trainer = Trainer(pipeline, splitter, model_config)

    # Train
    save_dir = Path(args.save_dir)
    model, report = trainer.train(df, target_col=args.target, save_dir=save_dir)

    # Print results
    print(f"\n{'='*60}")
    print(f"Training Report")
    print(f"{'='*60}")
    print(f"Samples: {report.n_samples:,}")
    print(f"Features: {report.n_features}")
    print(f"Avg Directional Accuracy: {report.avg_directional_accuracy:.3f}")
    print(f"Avg Pinball Loss (q50): {report.avg_pinball_loss:.6f}")
    print()

    for fr in report.fold_results:
        print(f"  Fold {fr.fold}: dir_acc={fr.directional_accuracy:.3f}, "
              f"train={fr.info.train_size:,} bars, test={fr.info.test_size:,} bars")

    # Feature importance
    print()
    importance = get_feature_importance(model, report.feature_names, top_n=30)
    print(print_importance_report(importance, top_n=30))

    print(f"\nModel saved to: {save_dir.resolve()}")


if __name__ == "__main__":
    main()
