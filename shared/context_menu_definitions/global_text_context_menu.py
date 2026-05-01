"""Global text widget context menu definition."""

from __future__ import annotations

from shared.context_menu.constants import CommonActionId
from shared.context_menu.dto import (
    ContextMenuActionDTO,
    ContextMenuItemDTO,
    ContextMenuSectionDTO,
)


TEXT_EDIT_SECTION = ContextMenuSectionDTO(
    id="global_text_edit",
    items=(
        ContextMenuItemDTO.action_item(
            ContextMenuActionDTO(CommonActionId.COPY, "Copy", CommonActionId.COPY, shortcut="Ctrl+C")
        ),
        ContextMenuItemDTO.action_item(
            ContextMenuActionDTO(CommonActionId.PASTE, "Paste", CommonActionId.PASTE, shortcut="Ctrl+V")
        ),
        ContextMenuItemDTO.action_item(
            ContextMenuActionDTO(CommonActionId.CUT, "Cut", CommonActionId.CUT, shortcut="Ctrl+X")
        ),
        ContextMenuItemDTO.separator(),
        ContextMenuItemDTO.action_item(
            ContextMenuActionDTO(CommonActionId.SELECT_ALL, "Select all", CommonActionId.SELECT_ALL, shortcut="Ctrl+A")
        ),
        ContextMenuItemDTO.action_item(
            ContextMenuActionDTO(CommonActionId.COPY_ALL, "Copy all", CommonActionId.COPY_ALL)
        ),
    ),
)


def get_sections() -> tuple[ContextMenuSectionDTO, ...]:
    return (TEXT_EDIT_SECTION,)
