"""Small in-memory state holder for the context menu system."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .dto import ContextMenuContextDTO


@dataclass
class ContextMenuState:
    current_context: ContextMenuContextDTO | None = None
    current_module: str = ""
    focused_widget_id: str = ""
    focused_widget_type: str = ""
    menu_open: bool = False


class ContextMenuStateService:
    def __init__(self) -> None:
        self._state = ContextMenuState()

    def open_menu(self, context: ContextMenuContextDTO) -> None:
        self._state.current_context = context
        self._state.current_module = context.module_name
        self._state.focused_widget_id = context.widget_id
        self._state.focused_widget_type = context.widget_type
        self._state.menu_open = True

    def close_menu(self) -> None:
        self._state.menu_open = False

    def clear(self) -> None:
        self._state = ContextMenuState()

    def snapshot(self) -> ContextMenuState:
        return ContextMenuState(
            current_context=self._state.current_context,
            current_module=self._state.current_module,
            focused_widget_id=self._state.focused_widget_id,
            focused_widget_type=self._state.focused_widget_type,
            menu_open=self._state.menu_open,
        )

    def set_focus(self, widget_id: str, widget_type: str, extra: dict[str, Any] | None = None) -> None:
        self._state.focused_widget_id = widget_id or ""
        self._state.focused_widget_type = widget_type or ""


state_service = ContextMenuStateService()
