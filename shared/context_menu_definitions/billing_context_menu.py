"""Billing context menu definitions.

Definitions only. Existing billing handlers are registered by billing.py.
"""

from __future__ import annotations

from shared.context_menu.dto import ContextMenuActionDTO, ContextMenuItemDTO, ContextMenuSectionDTO


class BillingContextAction:
    EDIT_ITEMS = "billing.current_bill.edit_items"
    UNDO_LAST = "billing.current_bill.undo_last"
    SAVE = "billing.current_bill.save"
    PRINT = "billing.current_bill.print"
    EXPORT_PDF = "billing.current_bill.export_pdf"
    WHATSAPP = "billing.current_bill.whatsapp"
    COPY_INVOICE = "billing.current_bill.copy_invoice"
    COPY_TOTAL = "billing.current_bill.copy_total"
    CLEAR = "billing.current_bill.clear"


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
            id="billing_current_bill_edit",
            title="Bill editing",
            items=(
                _action(BillingContextAction.EDIT_ITEMS, "Edit item qty/price"),
                _action(BillingContextAction.UNDO_LAST, "Undo last item", "Ctrl+Z"),
            ),
        ),
        ContextMenuSectionDTO(
            id="billing_current_bill_delivery",
            title="Save and deliver",
            items=(
                _action(BillingContextAction.SAVE, "Save bill", "F2"),
                _action(BillingContextAction.PRINT, "Print bill", "F5"),
                _action(BillingContextAction.EXPORT_PDF, "Save PDF", "F4"),
                _action(BillingContextAction.WHATSAPP, "WhatsApp bill", "F6"),
            ),
        ),
        ContextMenuSectionDTO(
            id="billing_current_bill_copy",
            title="Copy",
            items=(
                _action(BillingContextAction.COPY_INVOICE, "Copy invoice number"),
                _action(BillingContextAction.COPY_TOTAL, "Copy total amount"),
            ),
        ),
        ContextMenuSectionDTO(
            id="billing_current_bill_manage",
            title="Manage",
            items=(
                _action(BillingContextAction.CLEAR, "Clear bill", "F8", danger=True),
            ),
        ),
    )
