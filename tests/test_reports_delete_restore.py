from __future__ import annotations

import os

from src.blite_v6.reports.delete_restore import (
    build_delete_audit_map,
    build_report_sales_context_row,
    delete_confirm_prompt,
    delete_target_label,
    deleted_bill_tree_values,
    deleted_bills_role_note,
    is_admin_or_manager,
    merge_trash_pdf_entry,
    normalize_deleted_db_entry,
    selected_report_bill_from_row,
    sort_deleted_entries,
)


def test_is_admin_or_manager_accepts_only_privileged_roles():
    assert is_admin_or_manager(" owner ") is True
    assert is_admin_or_manager("ADMIN") is True
    assert is_admin_or_manager("manager") is True
    assert is_admin_or_manager("staff") is False
    assert is_admin_or_manager("") is False


def test_build_report_sales_context_row_prefers_raw_row_over_tree_values():
    values = ("29-04-2026", "10:30", "INV-1", "Tree Name", "111", "Cash", "Rs0", "Rs300")
    row = {"invoice": " INV-2 ", "name": "Raw Name", "phone": "999", "payment": "UPI"}

    selected = build_report_sales_context_row("I001", values, row)

    assert selected["row_id"] == "I001"
    assert selected["invoice"] == "INV-2"
    assert selected["customer"] == "Raw Name"
    assert selected["phone"] == "999"
    assert selected["payment"] == "UPI"
    assert selected["total"] == "Rs300"


def test_selected_report_bill_from_row_keeps_pdf_only_when_it_exists():
    existing = selected_report_bill_from_row(
        "row-1",
        {"invoice": "INV-1", "name": "Anu"},
        "C:/Bills",
        path_exists=lambda _path: True,
    )
    missing = selected_report_bill_from_row(
        "row-1",
        {"invoice": "INV-1", "name": "Anu"},
        "C:/Bills",
        path_exists=lambda _path: False,
    )

    assert existing["invoice_no"] == "INV-1"
    assert existing["customer_name"] == "Anu"
    assert existing["file_name"] == "INV-1_Anu.pdf"
    assert existing["file_path"].endswith(os.path.join("Bills", "INV-1_Anu.pdf"))
    assert missing["file_name"] == ""
    assert missing["file_path"] == ""


def test_delete_prompt_and_deleted_tree_values_are_stable():
    bill = {"invoice_no": "INV-1", "file_name": "INV-1_Anu.pdf"}
    entry = {
        "invoice_no": "INV-1",
        "customer_name": "Anu",
        "deleted_at": "2026-04-29 10:30:00",
        "deleted_by": "admin",
    }

    assert delete_target_label(bill) == "INV-1"
    assert delete_target_label({"file_name": "INV-1_Anu.pdf"}) == "INV-1_Anu.pdf"
    assert "Source: Sales List" in delete_confirm_prompt(bill, "Sales List")
    assert deleted_bill_tree_values(entry) == ("INV-1", "Anu", "2026-04-29 10:30:00", "admin")
    assert deleted_bills_role_note(False) == "Restore available for billing/report users"
    assert "Permanent delete" in deleted_bills_role_note(True)


def test_normalize_deleted_db_entry_and_audit_map():
    entry = normalize_deleted_db_entry(
        {
            "invoice_no": " INV-1 ",
            "name": "INV-1 - Anu",
            "deleted_at": " 2026-04-29 ",
            "deleted_by": " admin ",
        }
    )
    audit_map = build_delete_audit_map(
        [
            {"entity_key": "INV-1", "action": "deleted", "performed_by": "admin"},
            {"entity_key": "INV-2", "action": "restored", "performed_by": "admin"},
            {"entity_key": "INV-1", "action": "deleted", "performed_by": "other"},
        ]
    )

    assert entry["invoice_no"] == "INV-1"
    assert entry["customer_name"] == "Anu"
    assert entry["deleted_at"] == "2026-04-29"
    assert entry["deleted_by"] == "admin"
    assert entry["has_db_record"] is True
    assert list(audit_map) == ["INV-1"]
    assert audit_map["INV-1"]["performed_by"] == "admin"
    assert normalize_deleted_db_entry({"invoice_no": ""}) is None


def test_merge_trash_pdf_entry_combines_file_audit_and_existing_db_record():
    entries = {
        "INV-1": {
            "invoice_no": "INV-1",
            "customer_name": "",
            "deleted_at": "",
            "deleted_by": "",
            "has_db_record": True,
            "trash_file": "",
            "trash_name": "",
        }
    }
    audit_map = {
        "INV-1": {"performed_at": "2026-04-29 10:30:00", "performed_by": "admin"}
    }

    merge_trash_pdf_entry(entries, audit_map, "C:/Trash", "INV-1_Anu.pdf")

    assert entries["INV-1"]["customer_name"] == "Anu"
    assert entries["INV-1"]["deleted_at"] == "2026-04-29 10:30:00"
    assert entries["INV-1"]["deleted_by"] == "admin"
    assert entries["INV-1"]["trash_name"] == "INV-1_Anu.pdf"
    assert entries["INV-1"]["trash_file"].endswith(os.path.join("Trash", "INV-1_Anu.pdf"))


def test_sort_deleted_entries_orders_latest_first():
    rows = [
        {"invoice_no": "INV-1", "deleted_at": "2026-04-28"},
        {"invoice_no": "INV-3", "deleted_at": "2026-04-29"},
        {"invoice_no": "INV-2", "deleted_at": "2026-04-29"},
    ]

    sorted_rows = sort_deleted_entries(rows)

    assert [row["invoice_no"] for row in sorted_rows] == ["INV-3", "INV-2", "INV-1"]
