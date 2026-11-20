"""Feature importance analysis for trained models."""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


def get_feature_importance(
    model,
    feature_names: list[str],
    importance_type: str = "gain",
    top_n: Optional[int] = None,
) -> list[tuple[str, float]]:
    """Extract feature importance from a trained model.

    Args:
        model: A trained QuantileGBM (uses the median model).
        feature_names: List of feature names matching the training matrix.
        importance_type: "gain", "split", or "weight".
        top_n: Return only top N features. None for all.

    Returns:
        List of (feature_name, importance) sorted descending.
    """
    if not model.is_trained:
        raise RuntimeError("Model not trained")

    # Use the median (q=0.5) model for importance
    q50_model = model._models.get(0.5)
    if q50_model is None:
        # Use first available
        q50_model = next(iter(model._models.values()))

    try:
        importances = q50_model.feature_importances_
    except AttributeError:
        logger.warning("Model does not support feature_importances_")
        return []

    pairs = list(zip(feature_names, importances))
    pairs.sort(key=lambda x: x[1], reverse=True)

    if top_n:
        pairs = pairs[:top_n]

    return pairs


def print_importance_report(
    pairs: list[tuple[str, float]],
    top_n: int = 30,
) -> str:
    """Format feature importance as a readable report."""
    lines = [f"Top {min(top_n, len(pairs))} features by importance:", ""]
    total = sum(v for _, v in pairs) or 1.0

    for i, (name, imp) in enumerate(pairs[:top_n]):
        pct = imp / total * 100
        bar = "#" * int(pct)
        lines.append(f"  {i+1:3d}. {name:30s} {imp:10.1f} ({pct:5.1f}%) {bar}")

    return "\n".join(lines)
