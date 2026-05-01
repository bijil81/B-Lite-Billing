"""Expense context menu definitions."""

from __future__ import annotations

from shared.context_menu.dto import ContextMenuActionDTO, ContextMenuItemDTO, ContextMenuSectionDTO


class ExpenseContextAction:
    EDIT = "expenses.row.edit"
    COPY_AMOUNT = "expenses.row.copy_amount"
    COPY_DESCRIPTION = "expenses.row.copy_description"
    COPY_CATEGORY = "expenses.row.copy_category"
    REFRESH = "expenses.refresh"
    DELETE = "expenses.row.delete"


def _action(action_id: str, label: str, shortcut: str = "", danger: bool = False) -> ContextMenuItemDTO:
    return ContextMenuItemDTO.action_item(
        ContextMenuActionDTO(
            id=action_id,
            label=label,
            callback_key=action_id,
            shortcut=shortcut,
            danger=danger,
        )
    )


def get_sections() -> tuple[ContextMenuSectionDTO, ...]:
    return (
        ContextMenuSectionDTO(
            id="expense_row_primary",
            title="Expense row",
            items=(
                _action(ExpenseContextAction.EDIT, "Edit expense", "F2"),
            ),
        ),
        ContextMenuSectionDTO(
            id="expense_row_copy",
            title="Copy",
            items=(
                _action(ExpenseContextAction.COPY_AMOUNT, "Copy amount"),
                _action(ExpenseContextAction.COPY_DESCRIPTION, "Copy description"),
                _action(ExpenseContextAction.COPY_CATEGORY, "Copy category"),
            ),
        ),
        ContextMenuSectionDTO(
            id="expense_row_maintenance",
            title="Maintenance",
            items=(
                _action(ExpenseContextAction.REFRESH, "Refresh expenses", "F5"),
                _action(ExpenseContextAction.DELETE, "Delete expense", danger=True),
            ),
        ),
    )
