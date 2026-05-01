from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Mapping

from .app_specs import ModuleSpec, NavEntry

AI_ASSISTANT_KEY = "ai_assistant"
BILLING_KEY = "billing"


@dataclass(frozen=True)
class SwitchAccessResult:
    allowed: bool
    entry: NavEntry | None
    message: str | None = None


def find_nav_entry(nav_entries: Iterable[NavEntry], key: str) -> NavEntry | None:
    return next((entry for entry in nav_entries if entry[2] == key), None)


def switch_access_result(
    nav_entries: Iterable[NavEntry],
    key: str,
    has_access: Callable[[NavEntry], bool],
) -> SwitchAccessResult:
    entry = find_nav_entry(nav_entries, key)
    if entry and not has_access(entry):
        return SwitchAccessResult(
            allowed=False,
            entry=entry,
            message=f"{entry[1]} access is restricted for your role.",
        )
    return SwitchAccessResult(allowed=True, entry=entry)


def restore_visible_page_key(current_page_key: str | None, frame_keys: Iterable[str]) -> str | None:
    if not current_page_key:
        return None
    return current_page_key if current_page_key in set(frame_keys) else None


def cached_frame_key(frames: Mapping[str, object], key: str) -> str | None:
    return key if key in frames else None


def standard_module_spec(module_specs: Mapping[str, ModuleSpec], key: str) -> ModuleSpec | None:
    if key == AI_ASSISTANT_KEY:
        return None
    return module_specs.get(key)


def should_initialize_ai_tab(
    key: str,
    ai_enabled: bool,
    ai_available: bool,
    has_ai_controller: bool,
) -> bool:
    return key == AI_ASSISTANT_KEY and ai_enabled and ai_available and not has_ai_controller


def ai_tab_runtime_ready(
    key: str,
    ai_enabled: bool,
    ai_available: bool,
    has_ai_controller: bool,
) -> bool:
    return key == AI_ASSISTANT_KEY and ai_enabled and ai_available and has_ai_controller


def should_show_ai_runtime_placeholder(
    key: str,
    ai_enabled: bool,
    ai_available: bool,
    has_ai_controller: bool,
) -> bool:
    return key == AI_ASSISTANT_KEY and ai_enabled and not (ai_available and has_ai_controller)


def should_attach_billing_frame(key: str) -> bool:
    return key == BILLING_KEY


def frame_visibility_plan(frame_keys: Iterable[str], active_key: str) -> list[tuple[str, bool]]:
    return [(frame_key, frame_key == active_key) for frame_key in frame_keys]


def nav_button_active_plan(nav_keys: Iterable[str], active_key: str) -> list[tuple[str, bool]]:
    return [(nav_key, nav_key == active_key) for nav_key in nav_keys]
