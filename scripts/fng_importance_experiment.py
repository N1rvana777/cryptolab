#!/usr/bin/env python3
"""Compare feature importance with and without FNG sentiment features.

Trains two LightGBM models (without/with FNG) and compares top-20 importance.
"""

import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import lightgbm as lgb
from cryptolab.data.manager import DataManager
from cryptolab.features.pipeline import FeaturePipeline, build_default_registry
from cryptolab.features.sentiment import SentimentFeatures

logging.basicConfig(level=logging.WARNING)

START_MS = 1609459200000  # 2021-01-01
TARGET = "fwd_return_4h"
SYMBOLS = ["BTC", "ETH", "SOL"]

LGB_PARAMS = dict(
    n_estimators=300,
    learning_rate=0.05,
    max_depth=6,
    subsample=0.8,
    colsample_bytree=0.8,
    verbosity=-1,
    random_state=42,
)


def train_and_rank(X, y, feature_names, label):
    """Train LGB and return sorted feature importance."""
    model = lgb.LGBMRegressor(**LGB_PARAMS)
    model.fit(X, y)
    imp = model.feature_importances_
    ranked = sorted(zip(feature_names, imp), key=lambda x: -x[1])
    print(f"\n{'='*60}")
    print(f"  {label}: Top 20 Feature Importance")
    print(f"{'='*60}")
    for i, (name, score) in enumerate(ranked[:20], 1):
        print(f"  {i:2d}. {name:<30s} {score:6.0f}")
    print(f"  ... ({len(feature_names)} features total)")
    return ranked


def main():
    print("Loading data...")
    dm = DataManager()
    df = dm.get_training_dataset(SYMBOLS, interval="1h", start_ms=START_MS)
    if df.empty:
        print("No data. Run seed_cache.py first.")
        sys.exit(1)

    # --- Without FNG ---
    groups_no_fng = [
        "technical", "donchian", "microstructure", "cross_asset",
        "temporal", "volatility", "momentum", "funding", "orderbook",
    ]
    pipeline_no_fng = FeaturePipeline(groups=groups_no_fng, warmup_bars=168)
    X1, y1, names1 = pipeline_no_fng.build(df.copy(), target_col=TARGET, validate=False)
    ranked1 = train_and_rank(X1, y1, names1, "WITHOUT FNG")

    # --- With FNG ---
    groups_with_fng = groups_no_fng + ["sentiment"]
    pipeline_with_fng = FeaturePipeline(groups=groups_with_fng, warmup_bars=168)
    X2, y2, names2 = pipeline_with_fng.build(df.copy(), target_col=TARGET, validate=False)
    ranked2 = train_and_rank(X2, y2, names2, "WITH FNG")

    # --- Compare ---
    print(f"\n{'='*60}")
    print(f"  Comparison")
    print(f"{'='*60}")
    print(f"  Features without FNG: {len(names1)}")
    print(f"  Features with FNG:    {len(names2)}")

    # Where do FNG features rank?
    fng_names = SentimentFeatures().feature_names()
    print(f"\n  FNG feature ranks (out of {len(names2)}):")
    for fname in fng_names:
        for i, (name, score) in enumerate(ranked2, 1):
            if name == fname:
                print(f"    {fname:<30s} rank #{i:3d}  (importance={score:.0f})")
                break
        else:
            print(f"    {fname:<30s} NOT FOUND")

    # Top-20 stability
    top20_before = set(n for n, _ in ranked1[:20])
    top20_after = set(n for n, _ in ranked2[:20])
    stable = top20_before & top20_after
    dropped = top20_before - top20_after
    entered = top20_after - top20_before
    print(f"\n  Top-20 stability:")
    print(f"    Stable features:  {len(stable)}")
    if dropped:
        print(f"    Dropped from top-20: {dropped}")
    if entered:
        print(f"    Entered top-20:      {entered}")


if __name__ == "__main__":
    main()
