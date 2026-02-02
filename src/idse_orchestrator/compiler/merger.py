from __future__ import annotations

from typing import Any, Dict


def merge_profiles(blueprint: Dict[str, Any], feature: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge of blueprint defaults with feature overrides."""
    if blueprint is None:
        blueprint = {}
    if feature is None:
        feature = {}

    merged = dict(blueprint)
    for key, value in feature.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = merge_profiles(merged[key], value)
        else:
            # Lists and scalars are replaced
            merged[key] = value
    return merged
