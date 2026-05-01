"""Factory helpers for building normalized context menu context DTOs."""

from __future__ import annotations

from typing import Any, Mapping

from .constants import WidgetType
from .dto import ContextMenuContextDTO


def build_context(
    module_name: str,
    *,
    entity_type: str = "",
    entity_id: str | int | None = None,
    selected_row: Mapping[str, Any] | None = None,
    selected_cell: Mapping[str, Any] | None = None,
    selected_text: str = "",
    selection_count: int = 0,
    user_role: str = "",
    widget_type: str = WidgetType.UNKNOWN,
    widget_id: str = "",
    screen_x: int | None = None,
    screen_y: int | None = None,
    extra: Mapping[str, Any] | None = None,
) -> ContextMenuContextDTO:
    return ContextMenuContextDTO(
        module_name=(module_name or "").strip().lower(),
        entity_type=(entity_type or "").strip().lower(),
        entity_id=entity_id,
        selected_row=dict(selected_row or {}),
        selected_cell=dict(selected_cell or {}),
        selected_text=str(selected_text or ""),
        selection_count=max(0, int(selection_count or 0)),
        user_role=(user_role or "").strip().lower(),
        widget_type=(widget_type or WidgetType.UNKNOWN).strip().lower(),
        widget_id=str(widget_id or ""),
        screen_x=screen_x,
        screen_y=screen_y,
        extra=dict(extra or {}),
    )
