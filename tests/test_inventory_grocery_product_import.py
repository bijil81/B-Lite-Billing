from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from src.blite_v6.inventory_grocery.product_import import (
    build_import_preview,
    default_column_mapping,
    parse_csv_text,
    parse_json_text,
    parse_xlsx_file,
)


def test_default_mapping_accepts_supplier_style_headers():
    mapping = default_column_mapping([
        "Product Name",
        "Product Category",
        "Selling Price",
        "GST %",
        "Unit (Measurement)",
    ])

    assert mapping["name"] == "Product Name"
    assert mapping["category"] == "Product Category"
    assert mapping["sale_price"] == "Selling Price"
    assert mapping["gst_rate"] == "GST %"
    assert mapping["unit"] == "Unit (Measurement)"


def test_csv_preview_creates_valid_rows_with_normalized_inventory_payload():
    rows = parse_csv_text(
        "Product Name,Category,Sale Price,Cost Price,Stock,Unit,GST Rate %,HSN/SAC,Barcode\n"
        "Rice Packet 1kg,Grocery,62,55,10,pcs,5,1006,8901\n"
    )

    preview = build_import_preview(rows)

    assert preview.ok_to_import
    assert preview.created_count == 1
    row = preview.rows[0]
    assert row.action == "create"
    assert row.inventory_item["price"] == 62.0
    assert row.inventory_item["cost"] == 55.0
    assert row.inventory_item["gst_rate"] == 5.0
    assert row.catalog_payload["category_name"] == "Grocery"


def test_missing_required_fields_are_row_errors_not_crashes():
    preview = build_import_preview([
        {"Product Name": "Nameless Price", "Category": "Grocery"},
        {"Product Name": "", "Category": "Grocery", "Sale Price": "10"},
    ])

    assert preview.ok_to_import is False
    assert preview.error_count == 2
    assert preview.rows[0].errors[0].field == "sale_price"
    assert preview.rows[1].errors[0].field == "name"


def test_duplicate_barcode_and_sku_inside_file_are_errors():
    rows = [
        {"Product Name": "A", "Category": "Grocery", "Sale Price": "10", "Barcode": "111", "SKU": "sku-1"},
        {"Product Name": "B", "Category": "Grocery", "Sale Price": "11", "Barcode": "111", "SKU": "sku-1"},
    ]

    preview = build_import_preview(rows)

    assert preview.rows[0].action == "create"
    assert preview.rows[1].action == "error"
    fields = {issue.field for issue in preview.rows[1].errors}
    assert {"barcode", "sku"}.issubset(fields)


def test_existing_duplicate_policy_can_skip_update_or_error():
    rows = [{"Product Name": "Rice", "Category": "Grocery", "Sale Price": "62", "Barcode": "8901"}]
    existing = {"Old Rice": {"barcode": "8901", "sku": "RICE"}}

    skipped = build_import_preview(rows, existing_items=existing)
    updated = build_import_preview(rows, existing_items=existing, duplicate_policy="update")
    errored = build_import_preview(rows, existing_items=existing, duplicate_policy="error")

    assert skipped.rows[0].action == "skip"
    assert skipped.rows[0].match_key == "barcode:Old Rice"
    assert updated.rows[0].action == "update"
    assert errored.rows[0].action == "error"


def test_below_cost_row_is_warning_by_default_and_error_when_policy_requires():
    rows = [{"Product Name": "Promo", "Category": "Grocery", "Sale Price": "40", "Cost Price": "50"}]

    warned = build_import_preview(rows)
    blocked = build_import_preview(rows, below_cost_policy="error")

    assert warned.rows[0].action == "create"
    assert warned.warning_count == 1
    assert warned.rows[0].warnings[0].field == "sale_price"
    assert blocked.rows[0].action == "error"
    assert blocked.rows[0].errors[0].field == "sale_price"


def test_json_parser_accepts_list_or_wrapped_products():
    direct = parse_json_text(json.dumps([
        {"Product Name": "Rice", "Category": "Grocery", "Sale Price": "62"}
    ]))
    wrapped = parse_json_text(json.dumps({
        "products": [{"Product Name": "Tomato", "Category": "Vegetables", "Sale Price": "45"}]
    }))

    assert direct[0]["Product Name"] == "Rice"
    assert wrapped[0]["Product Name"] == "Tomato"


def test_empty_preview_reports_file_error():
    preview = build_import_preview([])

    assert preview.ok_to_import is False
    assert preview.error_count == 1
    assert preview.errors[0].field == "file"


def test_xlsx_parser_reads_header_rows():
    openpyxl = pytest.importorskip("openpyxl")
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(["Product Name", "Category", "Sale Price"])
    sheet.append(["Rice", "Grocery", 62])
    tmp_dir = Path(__file__).resolve().parents[1] / ".test-output"
    tmp_dir.mkdir(exist_ok=True)
    path = tmp_dir / f"products_{uuid.uuid4().hex}.xlsx"

    try:
        workbook.save(path)
        rows = parse_xlsx_file(path)
    finally:
        try:
            path.unlink(missing_ok=True)
            tmp_dir.rmdir()
        except OSError:
            pass

    assert rows == [{"Product Name": "Rice", "Category": "Grocery", "Sale Price": 62}]
