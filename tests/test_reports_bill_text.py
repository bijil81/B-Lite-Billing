from __future__ import annotations

import ast
from pathlib import Path

from src.blite_v6.reports.bill_text import build_bill_text


SETTINGS = {
    "salon_name": "B-Lite Test Store",
    "address": "Kollam",
    "gst_no": "GST-TEST",
    "bill_footer": "Visit Again",
}


def _row(**overrides):
    row = {
        "date": "2026-04-29 10:30:00",
        "invoice": "INV-001",
        "name": "Anu",
        "phone": "9999999999",
        "payment": "UPI",
        "discount": 0.0,
        "items_raw": "",
    }
    row.update(overrides)
    return row


def test_build_bill_text_supports_legacy_colon_items():
    text = build_bill_text(
        _row(items_raw="Hair Cut:300"),
        settings=SETTINGS,
        invoice_branding={"header": "Fallback"},
    )

    assert "B-Lite Test Store" in text
    assert "GST: GST-TEST" in text
    assert "Invoice : INV-001" in text
    assert "29-04-2026" in text
    assert "SERVICES" in text
    assert "Hair Cut" in text
    assert "300.00" in text
    assert "GRAND TOTAL" in text


def test_build_bill_text_keeps_service_product_totals_and_discount():
    text = build_bill_text(
        _row(
            items_raw="services~Hair Cut~300~1|products~Serum~200~2",
            discount=50.0,
        ),
        settings=SETTINGS,
        invoice_branding={"header": "Fallback"},
    )

    assert "SERVICES" in text
    assert "PRODUCTS" in text
    assert "Services Subtotal" in text
    assert "Products Subtotal" in text
    assert "Discount (-)" in text
    assert "650.00" in text


def test_build_bill_text_preserves_decimal_loose_product_quantity():
    text = build_bill_text(
        _row(items_raw="products~Rice~59.90~1.24"),
        settings=SETTINGS,
        invoice_branding={"header": "Fallback"},
    )

    assert "PRODUCTS" in text
    assert "Rice" in text
    assert "1.24" in text
    assert "74.28" in text


def test_build_bill_text_shows_saved_gst_breakdown_when_present():
    text = build_bill_text(
        _row(
            items_raw="products~Oil~112~1",
            gst_amount=12.0,
            taxable_amount=100.0,
            gst_breakdown=[{"rate": 12, "gst_amount": 12.0}],
        ),
        settings=SETTINGS,
        invoice_branding={"header": "Fallback"},
    )

    assert "Taxable Amt" in text
    assert "GST 12%" in text
    assert "GST Total" in text


def test_reports_py_uses_extracted_bill_text_builder():
    reports_path = Path(__file__).resolve().parents[1] / "reports.py"
    module = ast.parse(reports_path.read_text(encoding="utf-8"))
    assert not any(
        isinstance(node, ast.FunctionDef) and node.name == "_build_bill_text"
        for node in module.body
    )
    assert "build_bill_text as _build_bill_text" in reports_path.read_text(encoding="utf-8")
