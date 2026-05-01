"""Inventory context menu definitions."""

from __future__ import annotations

from shared.context_menu.constants import PermissionKey
from shared.context_menu.dto import ContextMenuActionDTO, ContextMenuItemDTO, ContextMenuSectionDTO


class InventoryContextAction:
    EDIT = "inventory.row.edit"
    ADD_STOCK = "inventory.row.add_stock"
    COPY_ITEM_NAME = "inventory.row.copy_item_name"
    COPY_BARCODE = "inventory.row.copy_barcode"
    COPY_QTY = "inventory.row.copy_qty"
    SHOW_LOW_STOCK = "inventory.row.show_low_stock"
    SHOW_ALL = "inventory.row.show_all"
    DELETE = "inventory.row.delete"


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
            id="inventory_row_primary",
            title="Inventory item",
            items=(
                _action(InventoryContextAction.EDIT, "Edit product", "F2"),
                _action(InventoryContextAction.ADD_STOCK, "Add stock"),
            ),
        ),
        ContextMenuSectionDTO(
            id="inventory_row_copy",
            title="Copy",
            items=(
                _action(InventoryContextAction.COPY_ITEM_NAME, "Copy product name"),
                _action(InventoryContextAction.COPY_BARCODE, "Copy barcode"),
                _action(InventoryContextAction.COPY_QTY, "Copy quantity"),
            ),
        ),
        ContextMenuSectionDTO(
            id="inventory_row_views",
            title="Views",
            items=(
                _action(InventoryContextAction.SHOW_LOW_STOCK, "Show low stock"),
                _action(InventoryContextAction.SHOW_ALL, "Show all items"),
            ),
        ),
        ContextMenuSectionDTO(
            id="inventory_row_danger",
            title="Danger",
            items=(
                _action(
                    InventoryContextAction.DELETE,
                    "Delete product",
                    permission_key=PermissionKey.INVENTORY_STOCK_REMOVE,
                    danger=True,
                ),
            ),
        ),
    )
