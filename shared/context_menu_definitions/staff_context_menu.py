"""Staff context menu definitions."""

from __future__ import annotations

from shared.context_menu.constants import PermissionKey
from shared.context_menu.dto import ContextMenuActionDTO, ContextMenuItemDTO, ContextMenuSectionDTO


class StaffContextAction:
    EDIT = "staff.row.edit"
    COPY_NAME = "staff.row.copy_name"
    COPY_PHONE = "staff.row.copy_phone"
    COPY_ROLE = "staff.row.copy_role"
    TOGGLE_ACTIVE = "staff.row.toggle_active"
    DELETE = "staff.row.delete"


def _action(
    action_id: str,
    label: str,
    shortcut: str = "",
    permission_key: str = "",
    danger: bool = False,
) -> ContextMenuItemDTO:
    return ContextMenuItemDTO.action_item(
        ContextMenuActionDTO(
            id=action_id,
            label=label,
            callback_key=action_id,
            shortcut=shortcut,
            permission_key=permission_key,
            danger=danger,
        )
    )


def get_sections() -> tuple[ContextMenuSectionDTO, ...]:
    return (
        ContextMenuSectionDTO(
            id="staff_row_primary",
            title="Staff",
            items=(
                _action(StaffContextAction.EDIT, "Open staff profile", "F2"),
                _action(StaffContextAction.TOGGLE_ACTIVE, "Activate/deactivate"),
            ),
        ),
        ContextMenuSectionDTO(
            id="staff_row_copy",
            title="Copy",
            items=(
                _action(StaffContextAction.COPY_PHONE, "Copy phone number"),
                _action(StaffContextAction.COPY_NAME, "Copy staff name"),
                _action(StaffContextAction.COPY_ROLE, "Copy role"),
            ),
        ),
        ContextMenuSectionDTO(
            id="staff_row_danger",
            title="Danger",
            items=(
                _action(
                    StaffContextAction.DELETE,
                    "Delete staff",
                    permission_key=PermissionKey.ADMIN_USER_DISABLE,
                    danger=True,
                ),
            ),
        ),
    )
