"""Framework-neutral DTOs for context menu definitions and runtime context."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Tuple

from .constants import MenuKind, WidgetType


def _dict_copy(value: Mapping[str, Any] | None) -> dict[str, Any]:
    return dict(value or {})


@dataclass(frozen=True)
class ContextMenuContextDTO:
    module_name: str
    entity_type: str = ""
    entity_id: str | int | None = None
    selected_row: Mapping[str, Any] = field(default_factory=dict)
    selected_cell: Mapping[str, Any] = field(default_factory=dict)
    selected_text: str = ""
    selection_count: int = 0
    user_role: str = ""
    widget_type: str = WidgetType.UNKNOWN
    widget_id: str = ""
    screen_x: int | None = None
    screen_y: int | None = None
    extra: Mapping[str, Any] = field(default_factory=dict)

    def with_extra(self, **extra: Any) -> "ContextMenuContextDTO":
        merged = _dict_copy(self.extra)
        merged.update(extra)
        return ContextMenuContextDTO(
            module_name=self.module_name,
            entity_type=self.entity_type,
            entity_id=self.entity_id,
            selected_row=self.selected_row,
            selected_cell=self.selected_cell,
            selected_text=self.selected_text,
            selection_count=self.selection_count,
            user_role=self.user_role,
            widget_type=self.widget_type,
            widget_id=self.widget_id,
            screen_x=self.screen_x,
            screen_y=self.screen_y,
            extra=merged,
        )


@dataclass(frozen=True)
class ContextMenuActionDTO:
    id: str
    label: str
    callback_key: str
    shortcut: str = ""
    icon: str = ""
    permission_key: str = ""
    feature_flag: str = ""
    danger: bool = False
    requires_confirmation: bool = False
    visible_when: str = ""
    enabled_when: str = ""
    payload: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ContextMenuItemDTO:
    kind: str
    action: ContextMenuActionDTO | None = None
    children: Tuple["ContextMenuItemDTO", ...] = ()
    label: str = ""

    @classmethod
    def action_item(cls, action: ContextMenuActionDTO) -> "ContextMenuItemDTO":
        return cls(kind=MenuKind.ACTION, action=action)

    @classmethod
    def separator(cls) -> "ContextMenuItemDTO":
        return cls(kind=MenuKind.SEPARATOR)

    @classmethod
    def submenu(cls, label: str, children: tuple["ContextMenuItemDTO", ...]) -> "ContextMenuItemDTO":
        return cls(kind=MenuKind.SUBMENU, label=label, children=tuple(children))


@dataclass(frozen=True)
class ContextMenuSectionDTO:
    id: str
    title: str = ""
    items: Tuple[ContextMenuItemDTO, ...] = ()
    feature_flag: str = ""
    visible_when: str = ""
