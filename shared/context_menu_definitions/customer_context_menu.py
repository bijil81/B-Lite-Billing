"""Customer directory context menu definitions."""

from __future__ import annotations

from shared.context_menu.constants import PermissionKey
from shared.context_menu.dto import ContextMenuActionDTO, ContextMenuItemDTO, ContextMenuSectionDTO


class CustomerContextAction:
    VIEW_HISTORY = "customer.row.view_history"
    EDIT = "customer.row.edit"
    LOYALTY_POINTS = "customer.row.loyalty_points"
    CREATE_BILL = "customer.row.create_bill"
    COPY_NAME = "customer.row.copy_name"
    COPY_PHONE = "customer.row.copy_phone"
    TOGGLE_VIP = "customer.row.toggle_vip"
    DELETE = "customer.row.delete"


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
            id="customer_row_primary",
            title="Customer",
            items=(
                _action(CustomerContextAction.VIEW_HISTORY, "View previous bills"),
                _action(CustomerContextAction.EDIT, "Open customer profile", "F2"),
                _action(CustomerContextAction.LOYALTY_POINTS, "View payment/points history"),
                _action(CustomerContextAction.CREATE_BILL, "Create bill"),
            ),
        ),
        ContextMenuSectionDTO(
            id="customer_row_copy",
            title="Copy",
            items=(
                _action(CustomerContextAction.COPY_PHONE, "Copy phone number"),
                _action(CustomerContextAction.COPY_NAME, "Copy customer name"),
            ),
        ),
        ContextMenuSectionDTO(
            id="customer_row_manage",
            title="Manage",
            items=(
                _action(CustomerContextAction.TOGGLE_VIP, "Toggle VIP"),
                _action(
                    CustomerContextAction.DELETE,
                    "Delete customer",
                    permission_key=PermissionKey.CUSTOMER_DELETE,
                    danger=True,
                ),
            ),
        ),
    )
