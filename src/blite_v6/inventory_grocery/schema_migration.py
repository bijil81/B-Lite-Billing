"""Backup-first additive schema migration for grocery inventory support."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import os
import shutil
import sqlite3
from typing import Iterable

from db import DB_PATH


MIGRATION_VERSION = "inventory_grocery_g2_20260430"


@dataclass(frozen=True)
class AdditiveColumn:
    table: str
    name: str
    ddl: str


PRODUCT_VARIANT_COLUMNS: tuple[AdditiveColumn, ...] = (
    AdditiveColumn("v5_product_variants", "sale_unit", "TEXT DEFAULT 'pcs'"),
    AdditiveColumn("v5_product_variants", "base_unit", "TEXT DEFAULT 'pcs'"),
    AdditiveColumn("v5_product_variants", "unit_multiplier", "REAL DEFAULT 1.0"),
    AdditiveColumn("v5_product_variants", "allow_decimal_qty", "INTEGER DEFAULT 0"),
    AdditiveColumn("v5_product_variants", "mrp", "REAL DEFAULT 0.0"),
    AdditiveColumn("v5_product_variants", "gst_rate", "REAL DEFAULT 0.0"),
    AdditiveColumn("v5_product_variants", "cess_rate", "REAL DEFAULT 0.0"),
    AdditiveColumn("v5_product_variants", "hsn_sac", "TEXT DEFAULT ''"),
    AdditiveColumn("v5_product_variants", "price_includes_tax", "INTEGER DEFAULT 1"),
    AdditiveColumn("v5_product_variants", "is_weighed", "INTEGER DEFAULT 0"),
)


MOVEMENT_COLUMNS: tuple[AdditiveColumn, ...] = (
    AdditiveColumn("v5_product_variant_movements", "qty_unit", "TEXT DEFAULT ''"),
    AdditiveColumn("v5_product_variant_movements", "unit_cost", "REAL DEFAULT 0.0"),
    AdditiveColumn("v5_product_variant_movements", "supplier_name", "TEXT DEFAULT ''"),
    AdditiveColumn("v5_product_variant_movements", "purchase_ref", "TEXT DEFAULT ''"),
    AdditiveColumn("v5_product_variant_movements", "batch_no", "TEXT DEFAULT ''"),
    AdditiveColumn("v5_product_variant_movements", "expiry_date", "TEXT DEFAULT ''"),
)


VENDOR_COLUMNS: tuple[AdditiveColumn, ...] = (
    AdditiveColumn("v5_vendors", "opening_balance", "REAL DEFAULT 0.0 CHECK(opening_balance >= 0)"),
)


ADDITIVE_COLUMNS: tuple[AdditiveColumn, ...] = (
    PRODUCT_VARIANT_COLUMNS + MOVEMENT_COLUMNS + VENDOR_COLUMNS
)


ADDITIVE_TABLE_SQL: tuple[tuple[str, str], ...] = (
    (
        "v5_vendors",
        """
        CREATE TABLE IF NOT EXISTS v5_vendors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            phone TEXT DEFAULT '',
            gstin TEXT DEFAULT '',
            address TEXT DEFAULT '',
            opening_balance REAL DEFAULT 0.0 CHECK(opening_balance >= 0),
            active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
        """,
    ),
    (
        "v5_purchase_invoices",
        """
        CREATE TABLE IF NOT EXISTS v5_purchase_invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id INTEGER,
            invoice_no TEXT DEFAULT '',
            invoice_date TEXT DEFAULT '',
            gross_total REAL DEFAULT 0.0 CHECK(gross_total >= 0),
            tax_total REAL DEFAULT 0.0 CHECK(tax_total >= 0),
            net_total REAL DEFAULT 0.0 CHECK(net_total >= 0),
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(vendor_id) REFERENCES v5_vendors(id) ON DELETE SET NULL
        )
        """,
    ),
    (
        "v5_purchase_invoice_items",
        """
        CREATE TABLE IF NOT EXISTS v5_purchase_invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            purchase_invoice_id INTEGER NOT NULL,
            variant_id INTEGER,
            item_name TEXT NOT NULL,
            qty REAL DEFAULT 0.0 CHECK(qty >= 0),
            unit TEXT DEFAULT 'pcs',
            cost_price REAL DEFAULT 0.0 CHECK(cost_price >= 0),
            sale_price REAL DEFAULT 0.0 CHECK(sale_price >= 0),
            mrp REAL DEFAULT 0.0 CHECK(mrp >= 0),
            gst_rate REAL DEFAULT 0.0 CHECK(gst_rate >= 0),
            hsn_sac TEXT DEFAULT '',
            batch_no TEXT DEFAULT '',
            expiry_date TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(purchase_invoice_id) REFERENCES v5_purchase_invoices(id) ON DELETE CASCADE,
            FOREIGN KEY(variant_id) REFERENCES v5_product_variants(id) ON DELETE SET NULL
        )
        """,
    ),
)


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return bool(row)


def _column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    return {str(row["name"]) for row in conn.execute(f"PRAGMA table_info({table})")}


def _missing_columns(conn: sqlite3.Connection, table: str, columns: Iterable[AdditiveColumn]) -> list[dict]:
    if not _table_exists(conn, table):
        return []
    existing = _column_names(conn, table)
    return [
        {"name": column.name, "ddl": column.ddl}
        for column in columns
        if column.name not in existing
    ]


def _financial_stock_warnings(conn: sqlite3.Connection) -> list[dict]:
    if not _table_exists(conn, "v5_product_variants"):
        return []
    columns = _column_names(conn, "v5_product_variants")
    checks = [
        ("sale_price", "sale_price < 0"),
        ("cost_price", "cost_price < 0"),
        ("stock_qty", "stock_qty < 0"),
        ("reorder_level", "reorder_level < 0"),
    ]
    active_checks = [(field, where) for field, where in checks if field in columns]
    if not active_checks:
        return []
    where_sql = " OR ".join(where for _, where in active_checks)
    select_cols = ["rowid"]
    for name in ("id", "product_id", "pack_label", "sale_price", "cost_price", "stock_qty", "reorder_level"):
        if name in columns:
            select_cols.append(f'"{name}"')
    rows = conn.execute(
        f"SELECT {', '.join(select_cols)} FROM v5_product_variants WHERE {where_sql} LIMIT 50"
    ).fetchall()
    return [dict(row) for row in rows]


def _backup_database(db_path: str, backup_dir: str | None = None) -> str:
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found: {db_path}")
    dest_dir = backup_dir or os.path.join(os.path.dirname(db_path), "migration_backups")
    os.makedirs(dest_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(dest_dir, f"{os.path.basename(db_path)}.{MIGRATION_VERSION}.{stamp}.bak")
    shutil.copy2(db_path, dest)
    return dest


def plan_inventory_grocery_schema(db_path: str | None = None) -> dict:
    target = db_path or DB_PATH
    report = {
        "db_path": target,
        "migration_version": MIGRATION_VERSION,
        "tables": [],
        "new_tables": [],
        "data_warnings": [],
        "blocked": False,
    }
    if not os.path.exists(target):
        report["blocked"] = True
        report["error"] = f"Database not found: {target}"
        return report

    by_table: dict[str, list[AdditiveColumn]] = {}
    for column in ADDITIVE_COLUMNS:
        by_table.setdefault(column.table, []).append(column)

    with _connect(target) as conn:
        for table, columns in by_table.items():
            if not _table_exists(conn, table):
                report["tables"].append({"table": table, "status": "missing_table", "missing_columns": []})
                continue
            missing = _missing_columns(conn, table, columns)
            status = "ready" if missing else "current"
            report["tables"].append({"table": table, "status": status, "missing_columns": missing})

        for table, _sql in ADDITIVE_TABLE_SQL:
            status = "current" if _table_exists(conn, table) else "ready"
            report["new_tables"].append({"table": table, "status": status})

        report["data_warnings"] = _financial_stock_warnings(conn)
    return report


def migrate_inventory_grocery_schema(
    db_path: str | None = None,
    *,
    dry_run: bool = True,
    backup_dir: str | None = None,
) -> dict:
    target = db_path or DB_PATH
    report = plan_inventory_grocery_schema(target)
    report["dry_run"] = dry_run
    report["backup_path"] = ""
    report["applied_columns"] = []
    report["applied_tables"] = []
    if report["blocked"]:
        return report

    columns_to_apply = [
        (table["table"], column)
        for table in report["tables"]
        if table["status"] == "ready"
        for column in table["missing_columns"]
    ]
    tables_to_apply = [item["table"] for item in report["new_tables"] if item["status"] == "ready"]
    if dry_run or (not columns_to_apply and not tables_to_apply):
        return report

    report["backup_path"] = _backup_database(target, backup_dir)
    with _connect(target) as conn:
        try:
            conn.execute("BEGIN IMMEDIATE")
            for table, sql in ADDITIVE_TABLE_SQL:
                if table not in tables_to_apply:
                    continue
                conn.execute(sql)
                report["applied_tables"].append(table)
            for table, column in columns_to_apply:
                conn.execute(f'ALTER TABLE "{table}" ADD COLUMN "{column["name"]}" {column["ddl"]}')
                report["applied_columns"].append({"table": table, "name": column["name"]})
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TEXT DEFAULT (datetime('now'))
                )
            """)
            conn.execute(
                "INSERT OR REPLACE INTO schema_migrations(version, applied_at) VALUES(?, datetime('now'))",
                (MIGRATION_VERSION,),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return report
