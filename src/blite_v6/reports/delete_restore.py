"""Delete, restore, and context-menu data helpers for ReportsFrame."""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Callable


ADMIN_DELETE_ROLES = frozenset({"owner", "admin", "manager"})


def is_admin_or_manager(role: Any) -> bool:
    return str(role or "").strip().lower() in ADMIN_DELETE_ROLES


def deleted_bills_role_note(can_permanent_delete: bool) -> str:
    note = "Restore available for billing/report users"
    if can_permanent_delete:
        note += " | Permanent delete available for owner/admin/manager"
    return note


def build_report_sales_context_row(
    row_id: str,
    values: tuple[Any, ...] | list[Any],
    row: dict[str, Any] | None,
) -> dict[str, Any]:
    row = row or {}
    invoice_no = str(row.get("invoice", values[2] if len(values) > 2 else "")).strip()
    return {
        "row_id": row_id,
        "date": values[0] if len(values) > 0 else "",
        "time": values[1] if len(values) > 1 else "",
        "invoice": invoice_no,
        "customer": row.get("name", values[3] if len(values) > 3 else ""),
        "phone": row.get("phone", values[4] if len(values) > 4 else ""),
        "payment": row.get("payment", values[5] if len(values) > 5 else ""),
        "discount": values[6] if len(values) > 6 else "",
        "total": values[7] if len(values) > 7 else "",
    }


def selected_report_bill_from_row(
    iid: str,
    row: dict[str, Any] | None,
    bills_dir: str,
    *,
    path_exists: Callable[[str], bool] = os.path.exists,
) -> dict[str, str]:
    row = row or {}
    invoice_no = str(row.get("invoice", "")).strip()
    customer_name = str(row.get("name", "")).strip()
    file_name = f"{invoice_no}_{customer_name}.pdf" if invoice_no else ""
    file_path = os.path.join(bills_dir, file_name) if file_name else ""
    if file_path and not path_exists(file_path):
        file_path = ""
        file_name = ""
    return {
        "iid": iid,
        "invoice_no": invoice_no,
        "customer_name": customer_name,
        "file_path": file_path,
        "file_name": file_name,
    }


def delete_target_label(bill: dict[str, Any] | None) -> str:
    bill = bill or {}
    return (
        str(bill.get("invoice_no", "")).strip()
        or str(bill.get("file_name", "")).strip()
        or "selected bill"
    )


def delete_confirm_prompt(bill: dict[str, Any] | None, source_label: str) -> str:
    return (
        f"Move {delete_target_label(bill)} to deleted history?\n\n"
        f"Source: {source_label}\n"
        "You can restore it from View Deleted."
    )


def deleted_bill_tree_values(entry: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(entry.get("invoice_no", "")),
        str(entry.get("customer_name", "")),
        str(entry.get("deleted_at", "")),
        str(entry.get("deleted_by", "")),
    )


def normalize_deleted_db_entry(row: dict[str, Any]) -> dict[str, Any] | None:
    invoice_no = str(row.get("invoice_no", "")).strip()
    if not invoice_no:
        return None
    customer_name = str(row.get("customer_name", "")).strip()
    display_name = str(row.get("name", "")).strip()
    if not customer_name and display_name.startswith(invoice_no):
        customer_name = _customer_name_from_display_name(display_name, invoice_no)
    return {
        "invoice_no": invoice_no,
        "customer_name": customer_name,
        "deleted_at": str(row.get("deleted_at", "")).strip(),
        "deleted_by": str(row.get("deleted_by", "")).strip(),
        "has_db_record": True,
        "trash_file": "",
        "trash_name": "",
    }


def build_delete_audit_map(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    audit_map: dict[str, dict[str, Any]] = {}
    for row in rows:
        invoice_no = str(row.get("entity_key", "")).strip()
        action = str(row.get("action", "")).strip().lower()
        if not invoice_no or action != "deleted" or invoice_no in audit_map:
            continue
        audit_map[invoice_no] = row
    return audit_map


def merge_trash_pdf_entry(
    entries: dict[str, dict[str, Any]],
    audit_map: dict[str, dict[str, Any]],
    trash_dir: str,
    fname: str,
    *,
    mtime_func: Callable[[str], float] = os.path.getmtime,
) -> None:
    if not str(fname).lower().endswith(".pdf"):
        return
    stem = fname[:-4]
    parts = stem.split("_")
    invoice_no = parts[0].strip() if parts else ""
    customer_name = "_".join(parts[1:]).strip() if len(parts) > 1 else ""
    if not invoice_no:
        return

    entry = entries.get(invoice_no, {
        "invoice_no": invoice_no,
        "customer_name": customer_name,
        "deleted_at": "",
        "deleted_by": "",
        "has_db_record": False,
        "trash_file": "",
        "trash_name": "",
    })
    audit = audit_map.get(invoice_no, {})
    if not entry.get("customer_name"):
        entry["customer_name"] = customer_name
    if not entry.get("deleted_at"):
        entry["deleted_at"] = str(audit.get("performed_at", "")).strip()
    if not entry.get("deleted_by"):
        entry["deleted_by"] = str(audit.get("performed_by", "")).strip()
    trash_file = os.path.join(trash_dir, fname)
    if not entry.get("deleted_at"):
        try:
            entry["deleted_at"] = datetime.fromtimestamp(mtime_func(trash_file)).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            entry["deleted_at"] = ""
    entry["trash_file"] = trash_file
    entry["trash_name"] = fname
    entries[invoice_no] = entry


def sort_deleted_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        entries,
        key=lambda item: (item.get("deleted_at", ""), item.get("invoice_no", "")),
        reverse=True,
    )


def _customer_name_from_display_name(display_name: str, invoice_no: str) -> str:
    remainder = display_name[len(invoice_no):].strip()
    for separator in ("-", "–", "—", "|", ":"):
        if remainder.startswith(separator):
            return remainder[1:].strip()
    return remainder
