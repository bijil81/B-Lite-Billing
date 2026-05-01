"""Feature flag defaults for the context menu rollout."""

from __future__ import annotations

from typing import Mapping

from .constants import ALL_FEATURE_FLAGS


DEFAULT_FLAGS: dict[str, bool] = {flag: False for flag in ALL_FEATURE_FLAGS}

# Module overrides are intentionally empty in Phase 1. Later phases can enable
# small rollout slices without changing the global defaults.
MODULE_FLAGS: dict[str, dict[str, bool]] = {}


def get_default_flags() -> dict[str, bool]:
    return dict(DEFAULT_FLAGS)


def get_module_flags(module_name: str) -> dict[str, bool]:
    return dict(MODULE_FLAGS.get((module_name or "").strip().lower(), {}))


def is_enabled(
    flag_name: str,
    module_name: str | None = None,
    overrides: Mapping[str, bool] | None = None,
) -> bool:
    if overrides and flag_name in overrides:
        return bool(overrides[flag_name])
    if module_name:
        module_flags = MODULE_FLAGS.get(module_name.strip().lower(), {})
        if flag_name in module_flags:
            return bool(module_flags[flag_name])
    return bool(DEFAULT_FLAGS.get(flag_name, False))
