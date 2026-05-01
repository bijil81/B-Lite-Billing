"""
v5 schema bootstrapper.

This remains additive and safe to run repeatedly:
- only creates v5-prefixed relational tables/views/indexes
- never drops legacy kv/json storage
- can be called on every startup because all SQL is idempotent
"""

from __future__ import annotations

import glob
import os

from db_core.connection import connection_scope


SQL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sql")
SCHEMA_FILE = os.path.join(SQL_DIR, "v5_schema.sql")
INDEX_FILE = os.path.join(SQL_DIR, "v5_indexes.sql")
VIEWS_FILE = os.path.join(SQL_DIR, "v5_views.sql")

_ADDITIVE_COLUMNS = {
    "v5_customers": {
        "is_deleted": "INTEGER DEFAULT 0",
        "deleted_at": "TEXT DEFAULT ''",
        "deleted_by": "TEXT DEFAULT ''",
    },
    "v5_inventory_items": {
        "is_deleted": "INTEGER DEFAULT 0",
        "deleted_at": "TEXT DEFAULT ''",
        "deleted_by": "TEXT DEFAULT ''",
    },
    "v5_invoices": {
        "is_deleted": "INTEGER DEFAULT 0",
        "deleted_at": "TEXT DEFAULT ''",
        "deleted_by": "TEXT DEFAULT ''",
    },
    "v5_vendors": {
        "opening_balance": "REAL DEFAULT 0.0 CHECK(opening_balance >= 0)",
    },
    "v5_product_variants": {
        "sale_unit": "TEXT DEFAULT 'pcs'",
        "base_unit": "TEXT DEFAULT 'pcs'",
        "unit_multiplier": "REAL DEFAULT 1.0",
        "allow_decimal_qty": "INTEGER DEFAULT 0",
        "mrp": "REAL DEFAULT 0.0",
        "gst_rate": "REAL DEFAULT 0.0",
        "cess_rate": "REAL DEFAULT 0.0",
        "hsn_sac": "TEXT DEFAULT ''",
        "price_includes_tax": "INTEGER DEFAULT 1",
        "is_weighed": "INTEGER DEFAULT 0",
    },
    "v5_product_variant_movements": {
        "qty_unit": "TEXT DEFAULT ''",
        "unit_cost": "REAL DEFAULT 0.0",
        "supplier_name": "TEXT DEFAULT ''",
        "purchase_ref": "TEXT DEFAULT ''",
        "batch_no": "TEXT DEFAULT ''",
        "expiry_date": "TEXT DEFAULT ''",
    },
}


def _read_sql(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _ensure_additive_columns(conn) -> None:
    for table, columns in _ADDITIVE_COLUMNS.items():
        existing = {
            str(row[1]).strip().lower()
            for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
        }
        for name, ddl in columns.items():
            if name.lower() in existing:
                continue
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")


def ensure_v5_schema() -> None:
    schema_sql = _read_sql(SCHEMA_FILE)
    extra_schema_files = [
        path for path in sorted(glob.glob(os.path.join(SQL_DIR, "v5_*.sql")))
        if path not in {SCHEMA_FILE, INDEX_FILE, VIEWS_FILE}
    ]
    index_sql = _read_sql(INDEX_FILE)
    views_sql = _read_sql(VIEWS_FILE)
    if not (schema_sql or extra_schema_files or index_sql or views_sql):
        return

    with connection_scope() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TEXT DEFAULT (datetime('now'))
            )
        """)
        if schema_sql:
            conn.executescript(schema_sql)
            conn.execute(
                "INSERT OR IGNORE INTO schema_migrations(version) VALUES(?)",
                ("v5_schema",)
            )
        for extra_file in extra_schema_files:
            extra_sql = _read_sql(extra_file)
            if not extra_sql:
                continue
            conn.executescript(extra_sql)
            conn.execute(
                "INSERT OR IGNORE INTO schema_migrations(version) VALUES(?)",
                (os.path.basename(extra_file),)
            )
        if index_sql:
            conn.executescript(index_sql)
            conn.execute(
                "INSERT OR IGNORE INTO schema_migrations(version) VALUES(?)",
                ("v5_indexes",)
            )
        if views_sql:
            conn.executescript(views_sql)
            conn.execute(
                "INSERT OR IGNORE INTO schema_migrations(version) VALUES(?)",
                ("v5_views",)
            )
        _ensure_additive_columns(conn)
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations(version) VALUES(?)",
            ("v5_additive_columns",)
        )
