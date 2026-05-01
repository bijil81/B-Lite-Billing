from __future__ import annotations

import sqlite3

import pytest

from db_core.constraint_migration import migrate_check_constraints, plan_check_constraint_migration


def _connect(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def test_existing_db_constraint_migration_dry_run_blocks_invalid_rows(tmp_path):
    db_path = tmp_path / "dirty.db"
    with _connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE v5_inventory_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                legacy_name TEXT NOT NULL UNIQUE,
                current_qty REAL DEFAULT 0.0,
                min_qty REAL DEFAULT 0.0,
                cost_price REAL DEFAULT 0.0,
                sale_price REAL DEFAULT 0.0
            )
        """)
        conn.execute("""
            INSERT INTO v5_inventory_items
                (legacy_name, current_qty, min_qty, cost_price, sale_price)
            VALUES ('Bad Stock', -1, 0, 10, 20)
        """)

    report = migrate_check_constraints(str(db_path), dry_run=True)

    inventory = next(item for item in report["tables"] if item["table"] == "v5_inventory_items")
    assert report["blocked"] is True
    assert inventory["status"] == "blocked"
    assert inventory["invalid_rows"][0]["legacy_name"] == "Bad Stock"

    after = plan_check_constraint_migration(str(db_path))
    inventory_after = next(item for item in after["tables"] if item["table"] == "v5_inventory_items")
    assert inventory_after["missing_checks"]


def test_existing_db_constraint_migration_applies_clean_table_with_backup(tmp_path):
    db_path = tmp_path / "clean.db"
    backup_dir = tmp_path / "backups"
    with _connect(db_path) as conn:
        conn.execute("CREATE TABLE v5_catalog_products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL)")
        conn.execute("INSERT INTO v5_catalog_products(id, name) VALUES (1, 'Shampoo')")
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
            INSERT INTO v5_product_variants
                (product_id, pack_label, sale_price, cost_price, stock_qty, reorder_level)
            VALUES (1, '100 ml', 120, 80, 5, 1)
        """)

    report = migrate_check_constraints(str(db_path), dry_run=False, backup_dir=str(backup_dir))

    assert "v5_product_variants" in report["applied_tables"]
    assert report["backup_path"]
    assert backup_dir.exists()

    with _connect(db_path) as conn:
        row = conn.execute("SELECT sale_price, stock_qty FROM v5_product_variants").fetchone()
        assert row["sale_price"] == 120
        assert row["stock_qty"] == 5
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("""
                INSERT INTO v5_product_variants
                    (product_id, pack_label, sale_price, cost_price, stock_qty, reorder_level)
                VALUES (1, '200 ml', -1, 80, 5, 1)
            """)


def test_product_variant_schema_rejects_negative_stock_and_prices(tmp_path):
    db_path = tmp_path / "new_schema.db"
    with _connect(db_path) as conn:
        conn.executescript(open("sql/v5_product_variant_schema.sql", "r", encoding="utf-8").read())
        conn.execute("INSERT INTO v5_catalog_products(id, name) VALUES (1, 'Serum')")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("""
                INSERT INTO v5_product_variants
                    (product_id, pack_label, sale_price, cost_price, stock_qty, reorder_level)
                VALUES (1, 'Default', 100, 50, -1, 0)
            """)
