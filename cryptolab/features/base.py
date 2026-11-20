"""Base class for feature blocks."""

from abc import ABC, abstractmethod

import pandas as pd


class FeatureBlock(ABC):
    """Each block adds a group of related features to a DataFrame.

    Rules:
    - All features must be computed on shifted data (.shift(1)) to prevent look-ahead bias
    - The compute() method receives a DataFrame with columns:
      timestamp, open, high, low, close, volume, symbol
    - It must return the same DataFrame with new columns added
    - feature_names() must return the exact list of column names added
    """

    @abstractmethod
    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add feature columns to df. Must not leak future information."""

    @abstractmethod
    def feature_names(self) -> list[str]:
        """Return list of column names this block produces."""
