from __future__ import annotations

from pathlib import Path
import shutil
import sqlite3
import uuid

import pytest

from db_core.constraint_migration import migrate_check_constraints
from src.blite_v6.inventory_grocery.schema_migration import (
    MIGRATION_VERSION,
    migrate_inventory_grocery_schema,
    plan_inventory_grocery_schema,
)


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


def _connect(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _columns(conn, table: str) -> set[str]:
    return {str(row["name"]) for row in conn.execute(f"PRAGMA table_info({table})")}


def _create_legacy_variant_schema(conn: sqlite3.Connection, *, with_negative: bool = False) -> None:
    conn.execute("CREATE TABLE v5_catalog_products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL)")
    conn.execute("INSERT INTO v5_catalog_products(id, name) VALUES (1, 'Rice')")
    conn.execute("""
        CREATE TABLE v5_product_variants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            variant_name TEXT DEFAULT '',
            unit_value REAL DEFAULT 0.0,
            unit_type TEXT DEFAULT 'pcs',
            pack_label TEXT DEFAULT '',
            bill_label TEXT DEFAULT '',
            sku TEXT DEFAULT '',
            barcode TEXT DEFAULT '',
            sale_price REAL DEFAULT 0.0,
            cost_price REAL DEFAULT 0.0,
            stock_qty REAL DEFAULT 0.0,
            reorder_level REAL DEFAULT 0.0
        )
    """)
    conn.execute("""
        CREATE TABLE v5_product_variant_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            variant_id INTEGER NOT NULL,
            movement_type TEXT NOT NULL,
            qty_delta REAL NOT NULL,
            reference_type TEXT DEFAULT '',
            reference_id TEXT DEFAULT '',
            note TEXT DEFAULT ''
        )
    """)
    sale_price = -1 if with_negative else 70
    conn.execute("""
        INSERT INTO v5_product_variants
            (product_id, pack_label, sale_price, cost_price, stock_qty, reorder_level)
        VALUES (1, 'Loose', ?, 55, 12, 2)
    """, (sale_price,))


def test_inventory_grocery_schema_dry_run_reports_without_altering(workspace_tmp_dir):
    db_path = workspace_tmp_dir / "legacy.db"
    with _connect(db_path) as conn:
        _create_legacy_variant_schema(conn)

    report = migrate_inventory_grocery_schema(str(db_path), dry_run=True)

    assert report["migration_version"] == MIGRATION_VERSION
    variants = next(item for item in report["tables"] if item["table"] == "v5_product_variants")
    assert variants["status"] == "ready"
    assert any(column["name"] == "gst_rate" for column in variants["missing_columns"])
    assert any(table["table"] == "v5_vendors" and table["status"] == "ready" for table in report["new_tables"])
    assert report["backup_path"] == ""

    with _connect(db_path) as conn:
        assert "gst_rate" not in _columns(conn, "v5_product_variants")
        assert "v5_vendors" not in {
            str(row["name"])
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }


def test_inventory_grocery_schema_apply_is_backup_first_and_preserves_rows(workspace_tmp_dir):
    db_path = workspace_tmp_dir / "legacy.db"
    backup_dir = workspace_tmp_dir / "backups"
    with _connect(db_path) as conn:
        _create_legacy_variant_schema(conn)

    report = migrate_inventory_grocery_schema(str(db_path), dry_run=False, backup_dir=str(backup_dir))

    assert report["backup_path"]
    assert backup_dir.exists()
    assert {"table": "v5_product_variants", "name": "gst_rate"} in report["applied_columns"]
    assert "v5_vendors" in report["applied_tables"]

    with _connect(db_path) as conn:
        variant_columns = _columns(conn, "v5_product_variants")
        movement_columns = _columns(conn, "v5_product_variant_movements")
        assert {"sale_unit", "base_unit", "unit_multiplier", "mrp", "gst_rate", "hsn_sac"} <= variant_columns
        assert {"qty_unit", "unit_cost", "supplier_name", "purchase_ref", "batch_no", "expiry_date"} <= movement_columns
        row = conn.execute("""
            SELECT sale_price, cost_price, stock_qty, sale_unit, base_unit, unit_multiplier, gst_rate
            FROM v5_product_variants
        """).fetchone()
        assert row["sale_price"] == 70
        assert row["cost_price"] == 55
        assert row["stock_qty"] == 12
        assert row["sale_unit"] == "pcs"
        assert row["base_unit"] == "pcs"
        assert row["unit_multiplier"] == 1
        assert row["gst_rate"] == 0
        assert conn.execute("SELECT version FROM schema_migrations WHERE version=?", (MIGRATION_VERSION,)).fetchone()


def test_inventory_grocery_schema_reports_invalid_existing_values_without_rewrite(workspace_tmp_dir):
    db_path = workspace_tmp_dir / "dirty.db"
    with _connect(db_path) as conn:
        _create_legacy_variant_schema(conn, with_negative=True)

    report = migrate_inventory_grocery_schema(str(db_path), dry_run=True)

    assert report["data_warnings"]
    assert report["data_warnings"][0]["sale_price"] == -1
    with _connect(db_path) as conn:
        row = conn.execute("SELECT sale_price FROM v5_product_variants").fetchone()
        assert row["sale_price"] == -1


def test_fresh_product_variant_schema_contains_grocery_columns(workspace_tmp_dir):
    db_path = workspace_tmp_dir / "fresh.db"
    with _connect(db_path) as conn:
        conn.executescript(open("sql/v5_product_variant_schema.sql", "r", encoding="utf-8").read())
        variant_columns = _columns(conn, "v5_product_variants")
        movement_columns = _columns(conn, "v5_product_variant_movements")
        assert {"sale_unit", "base_unit", "unit_multiplier", "mrp", "gst_rate", "hsn_sac"} <= variant_columns
        assert {"qty_unit", "unit_cost", "supplier_name", "purchase_ref", "batch_no", "expiry_date"} <= movement_columns
        assert _columns(conn, "v5_purchase_invoice_items")


def test_constraint_rebuild_preserves_grocery_columns(workspace_tmp_dir):
    db_path = workspace_tmp_dir / "rebuild.db"
    with _connect(db_path) as conn:
        _create_legacy_variant_schema(conn)
    migrate_inventory_grocery_schema(
        str(db_path),
        dry_run=False,
        backup_dir=str(workspace_tmp_dir / "grocery_backups"),
    )

    report = migrate_check_constraints(
        str(db_path),
        dry_run=False,
        backup_dir=str(workspace_tmp_dir / "constraint_backups"),
    )

    assert "v5_product_variants" in report["applied_tables"]
    with _connect(db_path) as conn:
        assert "gst_rate" in _columns(conn, "v5_product_variants")
        row = conn.execute("SELECT pack_label, sale_unit, gst_rate FROM v5_product_variants").fetchone()
        assert row["pack_label"] == "Loose"
        assert row["sale_unit"] == "pcs"
        assert row["gst_rate"] == 0


def test_missing_database_blocks_cleanly(workspace_tmp_dir):
    db_path = workspace_tmp_dir / "missing.db"

    report = plan_inventory_grocery_schema(str(db_path))

    assert report["blocked"] is True
    assert "Database not found" in report["error"]
