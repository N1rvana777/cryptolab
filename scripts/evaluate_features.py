#!/usr/bin/env python3
"""Evaluate feature quality and importance."""

import argparse
import sys
import os
import logging
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptolab.config import Config
from cryptolab.data.manager import DataManager
from cryptolab.features.pipeline import FeaturePipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

START_MS = 1609459200000


def main():
    parser = argparse.ArgumentParser(description="Evaluate features")
    parser.add_argument("--symbols", type=str, default="BTC,ETH,SOL")
    parser.add_argument("--interval", type=str, default="1h")
    parser.add_argument("--target", type=str, default="fwd_return_4h")
    args = parser.parse_args()

    cfg = Config()
    symbols = [s.strip() for s in args.symbols.split(",")]

    dm = DataManager()
    df = dm.get_training_dataset(symbols, interval=args.interval, start_ms=START_MS)

    if df.empty:
        print("No data. Run seed_cache.py first.")
        sys.exit(1)

    pipeline = FeaturePipeline(
        groups=cfg.features.feature_groups,
        warmup_bars=cfg.features.warmup_bars,
    )

    X, y, feature_names = pipeline.build(df, target_col=args.target)

    print(f"\nFeature Matrix: {X.shape}")
    print(f"Target: {args.target}, shape={y.shape}")
    print(f"Features ({len(feature_names)}):")
    for i, name in enumerate(feature_names):
        print(f"  {i+1:3d}. {name}")

    # Basic stats
    import numpy as np
    print(f"\nTarget stats: mean={y.mean():.6f}, std={y.std():.6f}, "
          f"min={y.min():.6f}, max={y.max():.6f}")
    print(f"NaN count in X: {np.isnan(X).sum()}")
    print(f"Inf count in X: {np.isinf(X).sum()}")


if __name__ == "__main__":
    main()
