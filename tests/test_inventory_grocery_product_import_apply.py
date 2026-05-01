from __future__ import annotations

from pathlib import Path
import shutil
import uuid

import pytest

from src.blite_v6.inventory_grocery.product_import import build_import_preview
from src.blite_v6.inventory_grocery.product_import_apply import apply_import_preview


@pytest.fixture
def workspace_tmp_dir():
    root = Path(__file__).resolve().parents[1] / ".test-output" / uuid.uuid4().hex
    root.mkdir(parents=True, exist_ok=True)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)
        try:
            root.parent.rmdir()
        except OSError:
            pass


def test_apply_preview_creates_inventory_and_catalog_rows():
    preview = build_import_preview([
        {
            "Product Name": "Rice Packet 1kg",
            "Category": "Grocery",
            "Sale Price": "62",
            "Cost Price": "55",
            "Stock": "10",
            "Unit": "pcs",
            "Barcode": "8901",
        }
    ])
    saved = {}
    catalog_payloads = []
    logs = []

    result = apply_import_preview(
        preview,
        existing_inventory={},
        save_inventory_fn=lambda data: saved.update(data),
        create_catalog_product_fn=lambda payload: catalog_payloads.append(payload),
        refresh_catalog_fn=lambda: None,
        write_batch_log_fn=lambda log: logs.append(log),
        source_file="products.csv",
        imported_on="2026-04-30",
    )

    assert result.created_count == 1
    assert result.updated_count == 0
    assert result.error_count == 0
    assert saved["Rice Packet 1kg"]["category"] == "Grocery"
    assert saved["Rice Packet 1kg"]["price"] == 62.0
    assert saved["Rice Packet 1kg"]["updated"] == "2026-04-30"
    assert catalog_payloads[0]["category_name"] == "Grocery"
    assert catalog_payloads[0]["variants"][0]["barcode"] == "8901"
    assert logs[0].source_file == "products.csv"


def test_apply_preview_updates_barcode_match_and_renames_without_duplicate():
    existing = {
        "Old Rice": {
            "category": "Grocery",
            "barcode": "8901",
            "price": 50,
            "qty": 1,
        }
    }
    preview = build_import_preview(
        [{
            "Product Name": "Rice Packet 1kg",
            "Category": "Grocery",
            "Sale Price": "62",
            "Stock": "10",
            "Barcode": "8901",
        }],
        existing_items=existing,
        duplicate_policy="update",
    )
    saved = {}

    result = apply_import_preview(
        preview,
        existing_inventory=existing,
        save_inventory_fn=lambda data: saved.update(data),
        create_catalog_product_fn=lambda payload: None,
        refresh_catalog_fn=lambda: None,
        write_batch_log_fn=lambda log: None,
        imported_on="2026-04-30",
    )

    assert result.updated_count == 1
    assert "Old Rice" not in saved
    assert saved["Rice Packet 1kg"]["barcode"] == "8901"
    assert saved["Rice Packet 1kg"]["qty"] == 10.0


def test_apply_preview_leaves_skipped_and_error_rows_untouched():
    existing = {"Rice": {"category": "Grocery", "barcode": "8901", "price": 62}}
    preview = build_import_preview(
        [
            {"Product Name": "Rice", "Category": "Grocery", "Sale Price": "62", "Barcode": "8901"},
            {"Product Name": "", "Category": "Grocery", "Sale Price": "10"},
        ],
        existing_items=existing,
    )
    saved = {}
    catalog_payloads = []

    result = apply_import_preview(
        preview,
        existing_inventory=existing,
        save_inventory_fn=lambda data: saved.update(data),
        create_catalog_product_fn=lambda payload: catalog_payloads.append(payload),
        refresh_catalog_fn=lambda: None,
        write_batch_log_fn=lambda log: None,
    )

    assert result.applied_count == 0
    assert result.skipped_count == 1
    assert result.error_count == 1
    assert saved == {}
    assert catalog_payloads == []


def test_apply_preview_reports_save_failure_without_catalog_write():
    preview = build_import_preview([
        {"Product Name": "Tomato Loose", "Category": "Vegetables", "Sale Price": "45", "Stock": "10", "Unit": "kg"}
    ])
    catalog_payloads = []

    def fail_save(_data):
        raise RuntimeError("disk full")

    result = apply_import_preview(
        preview,
        existing_inventory={},
        save_inventory_fn=fail_save,
        create_catalog_product_fn=lambda payload: catalog_payloads.append(payload),
        refresh_catalog_fn=lambda: None,
        write_batch_log_fn=lambda log: None,
    )

    assert result.created_count == 0
    assert result.error_count == 1
    assert "Inventory save failed" in result.rows[0].message
    assert catalog_payloads == []


def test_apply_preview_marks_catalog_failure_after_inventory_save():
    preview = build_import_preview([
        {"Product Name": "Tomato Loose", "Category": "Vegetables", "Sale Price": "45", "Stock": "10", "Unit": "kg"}
    ])
    saved = {}

    def fail_catalog(_payload):
        raise RuntimeError("catalog locked")

    result = apply_import_preview(
        preview,
        existing_inventory={},
        save_inventory_fn=lambda data: saved.update(data),
        create_catalog_product_fn=fail_catalog,
        refresh_catalog_fn=lambda: None,
        write_batch_log_fn=lambda log: None,
    )

    assert "Tomato Loose" in saved
    assert result.error_count == 1
    assert "catalog sync failed" in result.rows[0].message


def test_apply_preview_rejects_duplicate_target_name_on_update():
    existing = {
        "Old Rice": {"category": "Grocery", "barcode": "8901", "price": 62},
        "Rice Packet 1kg": {"category": "Grocery", "barcode": "222", "price": 64},
    }
    preview = build_import_preview(
        [{"Product Name": "Rice Packet 1kg", "Category": "Grocery", "Sale Price": "62", "Barcode": "8901"}],
        existing_items=existing,
        duplicate_policy="update",
    )

    result = apply_import_preview(
        preview,
        existing_inventory=existing,
        save_inventory_fn=lambda data: pytest.fail("save should not be called"),
        create_catalog_product_fn=lambda payload: pytest.fail("catalog should not be called"),
        refresh_catalog_fn=lambda: None,
        write_batch_log_fn=lambda log: None,
    )

    assert result.applied_count == 0
    assert result.error_count == 1
    assert "Target item already exists" in result.rows[0].message


def test_apply_preview_integrates_with_inventory_service_and_catalog(monkeypatch, workspace_tmp_dir):
    import db
    import db_core.connection as connection
    from services_v5.inventory_service import InventoryService
    from services_v5.product_catalog_service import ProductCatalogService

    db_path = workspace_tmp_dir / "import_apply.db"
    monkeypatch.setattr(db, "DB_PATH", str(db_path), raising=False)
    monkeypatch.setattr(connection, "DB_PATH", str(db_path), raising=False)

    preview = build_import_preview([
        {
            "Product Name": "Imported Sunflower Oil 1L",
            "Category": "Grocery",
            "Sale Price": "145",
            "Cost Price": "120",
            "Stock": "6",
            "Unit": "pcs",
            "GST Rate %": "5",
            "Barcode": "89010001",
        }
    ])
    inventory_service = InventoryService()

    result = apply_import_preview(
        preview,
        existing_inventory={},
        save_inventory_fn=inventory_service.sync_legacy_inventory_map,
        write_batch_log_fn=lambda log: None,
        imported_on="2026-04-30",
    )

    inventory = InventoryService().build_legacy_inventory_map()
    variants = ProductCatalogService().list_billable_variants("sunflower")

    assert result.created_count == 1
    assert inventory["Imported Sunflower Oil 1L"]["qty"] == 6.0
    assert inventory["Imported Sunflower Oil 1L"]["gst_rate"] == 5.0
    assert any(row["display_name"] == "Imported Sunflower Oil 1L" for row in variants)
