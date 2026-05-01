from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Mapping, Sequence

from .app_specs import NavEntry


@dataclass(frozen=True)
class RuntimePreferenceView:
    reset_animation_colors: bool
    refresh_ai_floating_button: bool = True


@dataclass(frozen=True)
class AiFeatureUpdatePlan:
    initialize_ai_controller: bool
    reset_ai_frame: bool
    show_ai_nav_row: bool
    refresh_ai_floating_button: bool
    destroy_ai_floating_widgets: bool
    switch_to_key: str | None


def runtime_preference_view(animations_enabled: bool) -> RuntimePreferenceView:
    return RuntimePreferenceView(reset_animation_colors=not animations_enabled)


def normalize_ai_config(settings: Mapping[str, object] | None) -> dict:
    if not isinstance(settings, Mapping):
        return {}
    ai_config = settings.get("ai_config", {})
    if isinstance(ai_config, Mapping):
        return dict(ai_config)
    return {}


def sidebar_before_nav_key(
    target_key: str,
    nav_entries: Iterable[NavEntry],
    has_access: Callable[[NavEntry], bool],
    packed_keys: Sequence[str],
) -> str | None:
    packed = set(packed_keys)
    seen_target = False
    for entry in nav_entries:
        nav_key = entry[2]
        if nav_key == target_key:
            seen_target = True
            continue
        if not seen_target:
            continue
        if nav_key not in packed:
            continue
        if not has_access(entry):
            continue
        return nav_key
    return None


def ai_feature_update_plan(
    ai_enabled: bool,
    ai_available: bool,
    has_ai_controller: bool,
    current_page_key: str | None,
    fallback_key: str | None,
) -> AiFeatureUpdatePlan:
    initialize = ai_enabled and ai_available and not has_ai_controller
    switch_to_key = None
    if not ai_enabled and current_page_key == "ai_assistant":
        candidate = fallback_key or "dashboard"
        if candidate != "ai_assistant":
            switch_to_key = candidate
    return AiFeatureUpdatePlan(
        initialize_ai_controller=initialize,
        reset_ai_frame=ai_enabled,
        show_ai_nav_row=ai_enabled,
        refresh_ai_floating_button=True,
        destroy_ai_floating_widgets=not ai_enabled,
        switch_to_key=switch_to_key,
    )
