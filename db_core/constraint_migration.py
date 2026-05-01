"""Backup-first CHECK-constraint migration for existing v5 SQLite tables."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import os
import shutil
import sqlite3
from typing import Iterable

from db import DB_PATH


MIGRATION_VERSION = "v5_check_constraints_20260429"


@dataclass(frozen=True)
class ConstraintSpec:
    table: str
    checks: tuple[str, ...]
    invalid_where: str
    create_sql: str


CONSTRAINT_SPECS: tuple[ConstraintSpec, ...] = (
    ConstraintSpec(
        table="v5_inventory_items",
        checks=("current_qty >= 0", "min_qty >= 0", "cost_price >= 0", "sale_price >= 0"),
        invalid_where="current_qty < 0 OR min_qty < 0 OR cost_price < 0 OR sale_price < 0",
        create_sql="""
            CREATE TABLE v5_inventory_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                legacy_name TEXT NOT NULL UNIQUE,
                category TEXT DEFAULT '',
                brand TEXT DEFAULT '',
                unit TEXT DEFAULT 'pcs',
                current_qty REAL DEFAULT 0.0 CHECK(current_qty >= 0),
                min_qty REAL DEFAULT 0.0 CHECK(min_qty >= 0),
                cost_price REAL DEFAULT 0.0 CHECK(cost_price >= 0),
                sale_price REAL DEFAULT 0.0 CHECK(sale_price >= 0),
                active INTEGER DEFAULT 1,
                is_deleted INTEGER DEFAULT 0,
                deleted_at TEXT DEFAULT '',
                deleted_by TEXT DEFAULT '',
                updated_at TEXT DEFAULT (datetime('now')),
                created_at TEXT DEFAULT (datetime('now'))
            )
        """,
    ),
    ConstraintSpec(
        table="v5_invoices",
        checks=("gross_total >= 0", "discount_total >= 0", "tax_total >= 0", "net_total >= 0"),
        invalid_where="gross_total < 0 OR discount_total < 0 OR tax_total < 0 OR net_total < 0",
        create_sql="""
            CREATE TABLE v5_invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_no TEXT NOT NULL UNIQUE,
                invoice_date TEXT NOT NULL,
                customer_phone TEXT DEFAULT '',
                customer_name TEXT DEFAULT '',
                gross_total REAL DEFAULT 0.0 CHECK(gross_total >= 0),
                discount_total REAL DEFAULT 0.0 CHECK(discount_total >= 0),
                tax_total REAL DEFAULT 0.0 CHECK(tax_total >= 0),
                net_total REAL DEFAULT 0.0 CHECK(net_total >= 0),
                loyalty_earned INTEGER DEFAULT 0,
                loyalty_redeemed INTEGER DEFAULT 0,
                redeem_code TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                created_by TEXT DEFAULT '',
                is_deleted INTEGER DEFAULT 0,
                deleted_at TEXT DEFAULT '',
                deleted_by TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """,
    ),
    ConstraintSpec(
        table="v5_invoice_items",
        checks=("qty >= 0", "unit_price >= 0", "line_total >= 0", "discount_amount >= 0"),
        invalid_where="qty < 0 OR unit_price < 0 OR line_total < 0 OR discount_amount < 0",
        create_sql="""
            CREATE TABLE v5_invoice_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER NOT NULL,
                item_name TEXT NOT NULL,
                item_type TEXT DEFAULT 'service',
                staff_name TEXT DEFAULT '',
                qty REAL DEFAULT 1.0 CHECK(qty >= 0),
                unit_price REAL DEFAULT 0.0 CHECK(unit_price >= 0),
                line_total REAL DEFAULT 0.0 CHECK(line_total >= 0),
                discount_amount REAL DEFAULT 0.0 CHECK(discount_amount >= 0),
                inventory_item_name TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY(invoice_id) REFERENCES v5_invoices(id) ON DELETE CASCADE
            )
        """,
    ),
    ConstraintSpec(
        table="v5_payments",
        checks=("amount >= 0",),
        invalid_where="amount < 0",
        create_sql="""
            CREATE TABLE v5_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER NOT NULL,
                payment_method TEXT NOT NULL,
                amount REAL DEFAULT 0.0 CHECK(amount >= 0),
                reference_no TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY(invoice_id) REFERENCES v5_invoices(id) ON DELETE CASCADE
            )
        """,
    ),
    ConstraintSpec(
        table="v5_product_variants",
        checks=("sale_price >= 0", "cost_price >= 0", "stock_qty >= 0", "reorder_level >= 0"),
        invalid_where="sale_price < 0 OR cost_price < 0 OR stock_qty < 0 OR reorder_level < 0",
        create_sql="""
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
                sale_price REAL DEFAULT 0.0 CHECK(sale_price >= 0),
                cost_price REAL DEFAULT 0.0 CHECK(cost_price >= 0),
                stock_qty REAL DEFAULT 0.0 CHECK(stock_qty >= 0),
                reorder_level REAL DEFAULT 0.0 CHECK(reorder_level >= 0),
                sale_unit TEXT DEFAULT 'pcs',
                base_unit TEXT DEFAULT 'pcs',
                unit_multiplier REAL DEFAULT 1.0,
                allow_decimal_qty INTEGER DEFAULT 0,
                mrp REAL DEFAULT 0.0,
                gst_rate REAL DEFAULT 0.0,
                cess_rate REAL DEFAULT 0.0,
                hsn_sac TEXT DEFAULT '',
                price_includes_tax INTEGER DEFAULT 1,
                is_weighed INTEGER DEFAULT 0,
                active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                UNIQUE(product_id, pack_label),
                FOREIGN KEY(product_id) REFERENCES v5_catalog_products(id) ON DELETE CASCADE
            )
        """,
    ),
)


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _table_sql(conn: sqlite3.Connection, table: str) -> str:
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return str(row["sql"] or "") if row else ""


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    return bool(_table_sql(conn, table))


def _missing_checks(create_sql: str, checks: Iterable[str]) -> list[str]:
    normalized = " ".join(create_sql.lower().replace("\n", " ").split())
    missing = []
    for check in checks:
        compact = check.lower().replace(" ", "")
        if compact not in normalized.replace(" ", ""):
            missing.append(check)
    return missing


def _invalid_rows(conn: sqlite3.Connection, spec: ConstraintSpec) -> list[dict]:
    columns = [str(row["name"]) for row in conn.execute(f"PRAGMA table_info({spec.table})")]
    select_columns = ", ".join([f'"{name}"' for name in columns])
    rows = conn.execute(
        f"SELECT rowid AS rowid, {select_columns} FROM {spec.table} WHERE {spec.invalid_where}"
    ).fetchall()
    return [dict(row) for row in rows]


def _column_names(conn: sqlite3.Connection, table: str) -> list[str]:
    return [str(row["name"]) for row in conn.execute(f"PRAGMA table_info({table})")]


def _rebuild_table(conn: sqlite3.Connection, spec: ConstraintSpec) -> None:
    old_table = f"{spec.table}__old_{MIGRATION_VERSION}"
    new_table = f"{spec.table}__new_{MIGRATION_VERSION}"
    old_cols = _column_names(conn, spec.table)
    conn.execute(f"ALTER TABLE {spec.table} RENAME TO {old_table}")
    conn.execute(spec.create_sql.replace(f"CREATE TABLE {spec.table}", f"CREATE TABLE {new_table}", 1))
    new_cols = _column_names(conn, new_table)
    copy_cols = [name for name in new_cols if name in old_cols]
    col_sql = ", ".join([f'"{name}"' for name in copy_cols])
    conn.execute(f"INSERT INTO {new_table} ({col_sql}) SELECT {col_sql} FROM {old_table}")
    conn.execute(f"DROP TABLE {old_table}")
    conn.execute(f"ALTER TABLE {new_table} RENAME TO {spec.table}")


def _backup_database(db_path: str, backup_dir: str | None = None) -> str:
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found: {db_path}")
    dest_dir = backup_dir or os.path.join(os.path.dirname(db_path), "migration_backups")
    os.makedirs(dest_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(dest_dir, f"{os.path.basename(db_path)}.{MIGRATION_VERSION}.{stamp}.bak")
    shutil.copy2(db_path, dest)
    return dest


def plan_check_constraint_migration(db_path: str | None = None) -> dict:
    target = db_path or DB_PATH
    report = {"db_path": target, "tables": [], "blocked": False}
    with _connect(target) as conn:
        for spec in CONSTRAINT_SPECS:
            current_sql = _table_sql(conn, spec.table)
            if not current_sql:
                report["tables"].append({"table": spec.table, "status": "missing"})
                continue
            missing = _missing_checks(current_sql, spec.checks)
            invalid = _invalid_rows(conn, spec)
            status = "ready" if missing and not invalid else "current" if not missing else "blocked"
            if invalid:
                report["blocked"] = True
            report["tables"].append({
                "table": spec.table,
                "status": status,
                "missing_checks": missing,
                "invalid_rows": invalid,
            })
    return report


def migrate_check_constraints(
    db_path: str | None = None,
    *,
    dry_run: bool = True,
    backup_dir: str | None = None,
) -> dict:
    target = db_path or DB_PATH
    report = plan_check_constraint_migration(target)
    ready_tables = [item["table"] for item in report["tables"] if item["status"] == "ready"]
    report["dry_run"] = dry_run
    report["backup_path"] = ""
    report["applied_tables"] = []
    report["migration_version"] = MIGRATION_VERSION
    if report["blocked"] or dry_run or not ready_tables:
        return report

    report["backup_path"] = _backup_database(target, backup_dir)
    with _connect(target) as conn:
        try:
            conn.execute("PRAGMA foreign_keys = OFF")
            conn.execute("BEGIN IMMEDIATE")
            for spec in CONSTRAINT_SPECS:
                if spec.table not in ready_tables or not _table_exists(conn, spec.table):
                    continue
                _rebuild_table(conn, spec)
                report["applied_tables"].append(spec.table)
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
        finally:
            conn.execute("PRAGMA foreign_keys = ON")
    return report
