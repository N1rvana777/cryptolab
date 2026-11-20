"""Feature registry: manages feature blocks by group."""

from __future__ import annotations

from typing import Dict, List

from cryptolab.features.base import FeatureBlock


class FeatureRegistry:
    """Central registry mapping group names to FeatureBlock instances."""

    def __init__(self) -> None:
        self._blocks: Dict[str, FeatureBlock] = {}

    def register(self, group: str, block: FeatureBlock) -> None:
        self._blocks[group] = block

    def get(self, group: str) -> FeatureBlock:
        if group not in self._blocks:
            raise KeyError(f"Unknown feature group: {group}")
        return self._blocks[group]

    def get_groups(self, names: list[str] | None = None) -> List[FeatureBlock]:
        """Return blocks for given group names, or all if None."""
        if names is None:
            return list(self._blocks.values())
        return [self._blocks[n] for n in names if n in self._blocks]

    def all_feature_names(self, groups: list[str] | None = None) -> List[str]:
        """Return all feature column names across selected groups."""
        names = []
        for block in self.get_groups(groups):
            names.extend(block.feature_names())
        return names
