from __future__ import annotations

from src.blite_v6.reports import saved_bills
from src.blite_v6.reports.saved_bills import (
    build_saved_bill_preview_text,
    find_report_row_by_invoice,
    list_saved_bill_files,
    parse_saved_bill_filename,
    selected_saved_bill_from_tree,
)


def test_parse_saved_bill_filename_keeps_customer_underscores():
    assert parse_saved_bill_filename("INV-001_Anu_Mol.pdf") == ("INV-001", "Anu_Mol")
    assert parse_saved_bill_filename("INV-002.pdf") == ("INV-002", "")


def test_list_saved_bill_files_filters_and_formats_metadata(tmp_path):
    saved_bills._PDF_LIST_CACHE.clear()
    first = tmp_path / "INV-002_Binu.pdf"
    second = tmp_path / "INV-001_Anu.pdf"
    ignored = tmp_path / "notes.txt"
    first.write_bytes(b"%PDF-1.4\n")
    second.write_bytes(b"%PDF-1.4\n")
    ignored.write_text("ignore", encoding="utf-8")

    rows = list_saved_bill_files(str(tmp_path), "anu")

    assert len(rows) == 1
    assert rows[0].invoice_no == "INV-001"
    assert rows[0].customer_name == "Anu"
    assert rows[0].tree_values[0:2] == ("INV-001", "Anu")
    assert rows[0].file_path == str(second)


def test_selected_saved_bill_from_tree_builds_context_payload():
    payload = selected_saved_bill_from_tree(
        "row-1",
        ("INV-010", "Meera", "29-04-2026", "5KB"),
        {"row-1": r"C:\Bills\INV-010_Meera.pdf"},
    )

    assert payload == {
        "iid": "row-1",
        "invoice_no": "INV-010",
        "customer_name": "Meera",
        "file_path": r"C:\Bills\INV-010_Meera.pdf",
        "file_name": "INV-010_Meera.pdf",
    }


def test_find_report_row_by_invoice_matches_trimmed_invoice():
    rows = [{"invoice": " INV-1 ", "phone": "9999999999"}, {"invoice": "INV-2"}]

    assert find_report_row_by_invoice(rows, "INV-1") == rows[0]
    assert find_report_row_by_invoice(rows, "missing") is None


def test_build_saved_bill_preview_uses_report_fallback_when_pdf_text_unavailable(monkeypatch, tmp_path):
    pdf = tmp_path / "INV-500_Anu.pdf"
    pdf.write_bytes(b"not really a pdf")
    rows = [{"invoice": "INV-500", "name": "Anu"}]

    monkeypatch.setattr(saved_bills, "extract_pdf_text", lambda _path: None)
    text = build_saved_bill_preview_text(str(pdf), rows, lambda row: f"fallback {row['name']}")

    assert text == "fallback Anu"


def test_build_saved_bill_preview_returns_open_pdf_message_without_report_match(monkeypatch, tmp_path):
    pdf = tmp_path / "INV-404_Unknown.pdf"
    pdf.write_bytes(b"not really a pdf")

    monkeypatch.setattr(saved_bills, "extract_pdf_text", lambda _path: None)
    text = build_saved_bill_preview_text(str(pdf), [], lambda _row: "unused")

    assert "INV-404_Unknown.pdf" in text
    assert "Inline PDF text preview is not available" in text
