"""Report and saved bill context menu definitions."""

from __future__ import annotations

from shared.context_menu.constants import PermissionKey
from shared.context_menu.dto import ContextMenuActionDTO, ContextMenuItemDTO, ContextMenuSectionDTO


class ReportContextAction:
    PREVIEW = "reports.sales.preview"
    LOAD_TO_BILL = "reports.sales.load_to_bill"
    PRINT = "reports.sales.print"
    EXPORT_PDF = "reports.sales.export_pdf"
    EXPORT_EXCEL = "reports.sales.export_excel"
    EXPORT_CSV = "reports.sales.export_csv"
    COPY_INVOICE = "reports.sales.copy_invoice"
    COPY_CUSTOMER = "reports.sales.copy_customer"
    COPY_TOTAL = "reports.sales.copy_total"
    REFRESH = "reports.sales.refresh"
    DELETE = "reports.sales.delete"


class SavedBillContextAction:
    OPEN_PDF = "reports.saved_bill.open_pdf"
    PRINT_PDF = "reports.saved_bill.print_pdf"
    WHATSAPP = "reports.saved_bill.whatsapp"
    COPY_INVOICE = "reports.saved_bill.copy_invoice"
    COPY_CUSTOMER = "reports.saved_bill.copy_customer"
    COPY_FILE_PATH = "reports.saved_bill.copy_file_path"
    REFRESH = "reports.saved_bill.refresh"
    DELETE = "reports.saved_bill.delete"


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


def get_sales_sections() -> tuple[ContextMenuSectionDTO, ...]:
    return (
        ContextMenuSectionDTO(
            id="reports_sales_primary",
            title="Sales bill",
            items=(
                _action(ReportContextAction.PREVIEW, "Preview bill"),
                _action(ReportContextAction.LOAD_TO_BILL, "Load to bill"),
                _action(ReportContextAction.PRINT, "Print preview"),
            ),
        ),
        ContextMenuSectionDTO(
            id="reports_sales_export",
            title="Export",
            items=(
                _action(ReportContextAction.EXPORT_PDF, "Export report PDF"),
                _action(ReportContextAction.EXPORT_EXCEL, "Export report Excel"),
                _action(ReportContextAction.EXPORT_CSV, "Export report CSV"),
            ),
        ),
        ContextMenuSectionDTO(
            id="reports_sales_copy",
            title="Copy",
            items=(
                _action(ReportContextAction.COPY_INVOICE, "Copy invoice number"),
                _action(ReportContextAction.COPY_CUSTOMER, "Copy customer name"),
                _action(ReportContextAction.COPY_TOTAL, "Copy total amount"),
            ),
        ),
        ContextMenuSectionDTO(
            id="reports_sales_maintenance",
            title="Maintenance",
            items=(
                _action(ReportContextAction.REFRESH, "Refresh report", "F5"),
                _action(
                    ReportContextAction.DELETE,
                    "Delete bill",
                    permission_key=PermissionKey.INVOICE_DELETE,
                    danger=True,
                ),
            ),
        ),
    )


def get_saved_bill_sections() -> tuple[ContextMenuSectionDTO, ...]:
    return (
        ContextMenuSectionDTO(
            id="saved_bill_primary",
            title="Saved bill",
            items=(
                _action(SavedBillContextAction.OPEN_PDF, "Open PDF"),
                _action(SavedBillContextAction.PRINT_PDF, "Print PDF"),
                _action(SavedBillContextAction.WHATSAPP, "WhatsApp bill"),
            ),
        ),
        ContextMenuSectionDTO(
            id="saved_bill_copy",
            title="Copy",
            items=(
                _action(SavedBillContextAction.COPY_INVOICE, "Copy invoice number"),
                _action(SavedBillContextAction.COPY_CUSTOMER, "Copy customer name"),
                _action(SavedBillContextAction.COPY_FILE_PATH, "Copy file path"),
            ),
        ),
        ContextMenuSectionDTO(
            id="saved_bill_maintenance",
            title="Maintenance",
            items=(
                _action(SavedBillContextAction.REFRESH, "Refresh list", "F5"),
                _action(
                    SavedBillContextAction.DELETE,
                    "Delete saved bill",
                    permission_key=PermissionKey.INVOICE_DELETE,
                    danger=True,
                ),
            ),
        ),
    )
