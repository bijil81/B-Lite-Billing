"""Closing report context menu definitions."""

from __future__ import annotations

from shared.context_menu.dto import ContextMenuActionDTO, ContextMenuItemDTO, ContextMenuSectionDTO


class ClosingReportContextAction:
    PREVIEW_BILL = "closing_report.bill.preview"
    SAVE_PDF = "closing_report.save_pdf"
    EXPORT_EXCEL = "closing_report.export_excel"
    COPY_INVOICE = "closing_report.bill.copy_invoice"
    COPY_CUSTOMER = "closing_report.bill.copy_customer"
    COPY_PHONE = "closing_report.bill.copy_phone"
    COPY_TOTAL = "closing_report.bill.copy_total"
    REFRESH = "closing_report.refresh"


def _action(action_id: str, label: str, shortcut: str = "") -> ContextMenuItemDTO:
    return ContextMenuItemDTO.action_item(
        ContextMenuActionDTO(
            id=action_id,
            label=label,
            callback_key=action_id,
            shortcut=shortcut,
        )
    )


def get_sections() -> tuple[ContextMenuSectionDTO, ...]:
    return (
        ContextMenuSectionDTO(
            id="closing_report_primary",
            title="Closing bill",
            items=(
                _action(ClosingReportContextAction.PREVIEW_BILL, "Preview bill"),
                _action(ClosingReportContextAction.SAVE_PDF, "Save closing PDF"),
                _action(ClosingReportContextAction.EXPORT_EXCEL, "Export closing Excel"),
            ),
        ),
        ContextMenuSectionDTO(
            id="closing_report_copy",
            title="Copy",
            items=(
                _action(ClosingReportContextAction.COPY_INVOICE, "Copy invoice number"),
                _action(ClosingReportContextAction.COPY_CUSTOMER, "Copy customer name"),
                _action(ClosingReportContextAction.COPY_PHONE, "Copy phone number"),
                _action(ClosingReportContextAction.COPY_TOTAL, "Copy total amount"),
            ),
        ),
        ContextMenuSectionDTO(
            id="closing_report_maintenance",
            title="Maintenance",
            items=(
                _action(ClosingReportContextAction.REFRESH, "Refresh closing report", "F5"),
            ),
        ),
    )
