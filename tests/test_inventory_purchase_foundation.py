from __future__ import annotations

from pathlib import Path
import shutil
import sqlite3
import uuid

import pytest


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


def _use_db(monkeypatch, workspace_tmp_dir):
    import db
    import db_core.connection as connection

    db_path = workspace_tmp_dir / "purchase_foundation.db"
    monkeypatch.setattr(db, "DB_PATH", str(db_path), raising=False)
    monkeypatch.setattr(connection, "DB_PATH", str(db_path), raising=False)
    return db_path


def _connect(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _seed_variant_and_inventory(db_path):
    from db_core.schema_manager import ensure_v5_schema

    ensure_v5_schema()
    with _connect(db_path) as conn:
        conn.execute("INSERT INTO v5_product_categories(name) VALUES('Vegetables')")
        category_id = conn.execute("SELECT id FROM v5_product_categories WHERE name='Vegetables'").fetchone()["id"]
        conn.execute(
            "INSERT INTO v5_catalog_products(category_id, name, base_name) VALUES(?, 'Test Tomato', 'Test Tomato')",
            (category_id,),
        )
        product_id = conn.execute("SELECT id FROM v5_catalog_products WHERE name='Test Tomato'").fetchone()["id"]
        conn.execute(
            """
            INSERT INTO v5_product_variants(
                product_id, variant_name, pack_label, bill_label, unit_type,
                sale_unit, base_unit, sale_price, cost_price, stock_qty, gst_rate, hsn_sac
            ) VALUES(?, 'Loose', 'Loose', 'Test Tomato Loose', 'kg',
                'kg', 'kg', 45.5, 32.25, 9.26, 5, '0702')
            """,
            (product_id,),
        )
        conn.execute(
            """
            INSERT INTO v5_inventory_items(
                legacy_name, category, unit, current_qty, min_qty, cost_price, sale_price
            ) VALUES('Test Tomato Loose', 'Vegetables', 'kg', 9.26, 5, 32.25, 45.5)
            """
        )
        conn.commit()
        return int(conn.execute("SELECT id FROM v5_product_variants").fetchone()["id"])


def test_vendor_duplicate_upsert_updates_existing_row(monkeypatch, workspace_tmp_dir):
    db_path = _use_db(monkeypatch, workspace_tmp_dir)
    from services_v5.purchase_service import PurchaseService

    service = PurchaseService()
    first = service.save_vendor({
        "name": "Fresh Farms",
        "phone": "111",
        "gstin": "32ABCDE1234F1Z5",
        "opening_balance": 100,
    })
    second = service.save_vendor({
        "name": "Fresh Farms",
        "phone": "222",
        "gstin": "32ABCDE1234F1Z5",
        "opening_balance": 250,
    })

    assert second["vendor_id"] == first["vendor_id"]
    with _connect(db_path) as conn:
        rows = conn.execute("SELECT name, phone, opening_balance FROM v5_vendors").fetchall()
        assert len(rows) == 1
        assert rows[0]["phone"] == "222"
        assert rows[0]["opening_balance"] == 250


def test_purchase_invoice_increases_variant_and_inventory_stock(monkeypatch, workspace_tmp_dir):
    db_path = _use_db(monkeypatch, workspace_tmp_dir)
    variant_id = _seed_variant_and_inventory(db_path)
    from services_v5.purchase_service import PurchaseService

    result = PurchaseService().save_purchase_invoice({
        "vendor": {"name": "Fresh Farms", "phone": "999"},
        "invoice_no": "PF-1001",
        "invoice_date": "2026-04-30",
        "items": [
            {
                "item_name": "Test Tomato Loose",
                "qty": "2.5",
                "unit": "kg",
                "cost_price": "30",
                "sale_price": "46",
                "mrp": "50",
                "gst_rate": "5",
                "hsn_sac": "0702",
                "batch_no": "B1",
            }
        ],
    })

    assert result["gross_total"] == 75.0
    assert result["tax_total"] == 3.75
    assert result["net_total"] == 78.75
    with _connect(db_path) as conn:
        variant = conn.execute("SELECT * FROM v5_product_variants WHERE id=?", (variant_id,)).fetchone()
        inventory = conn.execute(
            "SELECT * FROM v5_inventory_items WHERE legacy_name='Test Tomato Loose'"
        ).fetchone()
        purchase_item = conn.execute("SELECT * FROM v5_purchase_invoice_items").fetchone()
        variant_movement = conn.execute("SELECT * FROM v5_product_variant_movements").fetchone()
        inventory_movement = conn.execute("SELECT * FROM v5_inventory_movements").fetchone()

    assert variant["stock_qty"] == pytest.approx(11.76)
    assert variant["cost_price"] == 30
    assert variant["sale_price"] == 46
    assert variant["gst_rate"] == 5
    assert inventory["current_qty"] == pytest.approx(11.76)
    assert inventory["cost_price"] == 30
    assert purchase_item["variant_id"] == variant_id
    assert purchase_item["qty"] == 2.5
    assert variant_movement["movement_type"] == "purchase"
    assert variant_movement["qty_delta"] == 2.5
    assert variant_movement["qty_unit"] == "kg"
    assert variant_movement["supplier_name"] == "Fresh Farms"
    assert inventory_movement["movement_type"] == "purchase"
    assert inventory_movement["qty_delta"] == 2.5


def test_purchase_validation_rejects_bad_rows():
    from src.blite_v6.inventory_grocery.purchase_validation import (
        validate_purchase_invoice_payload,
        validate_vendor_payload,
    )

    with pytest.raises(ValueError, match="gstin"):
        validate_vendor_payload({"name": "Bad GST", "gstin": "SHORT"})
    with pytest.raises(ValueError, match="qty must be greater"):
        validate_purchase_invoice_payload({
            "vendor": {"name": "Fresh Farms"},
            "invoice_date": "2026-04-30",
            "items": [{"item_name": "Rice", "qty": 0, "cost_price": 10}],
        })


def test_purchase_invoice_accepts_existing_vendor_id(monkeypatch, workspace_tmp_dir):
    db_path = _use_db(monkeypatch, workspace_tmp_dir)
    variant_id = _seed_variant_and_inventory(db_path)
    from services_v5.purchase_service import PurchaseService

    service = PurchaseService()
    vendor = service.save_vendor({"name": "Saved Supplier"})
    result = service.save_purchase_invoice({
        "vendor_id": vendor["vendor_id"],
        "invoice_no": "PF-1002",
        "invoice_date": "2026-04-30",
        "items": [
            {
                "variant_id": variant_id,
                "item_name": "Test Tomato Loose",
                "qty": "1.25",
                "unit": "kg",
                "cost_price": "31",
            }
        ],
    })

    assert result["vendor_id"] == vendor["vendor_id"]
    with _connect(db_path) as conn:
        movement = conn.execute(
            "SELECT supplier_name, qty_delta FROM v5_product_variant_movements ORDER BY id DESC LIMIT 1"
        ).fetchone()
    assert movement["supplier_name"] == "Saved Supplier"
    assert movement["qty_delta"] == 1.25
