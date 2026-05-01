"""
soft_delete.py  --  BOBY'S Salon : Soft-delete & undo safety  v5.6.1 Phase 3

Provides:
  - Migration helpers to add is_deleted / deleted_at / deleted_by to v5 tables
    and legacy tables (customers, inventory as JSON flags)
  - soft_delete() / restore() / permanent_delete() helpers
  - deleted-item listing for all entities
  - audit helpers for deleted-items history
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Optional

from utils import (
    app_log,
    F_CUSTOMERS,
    F_INVENTORY,
    load_json,
    save_json,
    now_str,
)
from db_core.connection import connection_scope
from db_core.schema_manager import ensure_v5_schema

# ---------------------------------------------------------------------------
#  Migration – v5 tables (additive only)
# ---------------------------------------------------------------------------

def migrate_v5_soft_delete() -> dict:
    """Add is_deleted / deleted_at / deleted_by columns to v5 tables.

    Safe to call repeatedly – uses IF NOT EXISTS.
    """
    result = {"ok": [], "errors": []}
    ensure_v5_schema()

    columns = [
        ("v5_customers", "is_deleted"),
        ("v5_customers", "deleted_at"),
        ("v5_customers", "deleted_by"),
        ("v5_inventory_items", "is_deleted"),
        ("v5_inventory_items", "deleted_at"),
        ("v5_inventory_items", "deleted_by"),
        ("v5_invoices", "is_deleted"),
        ("v5_invoices", "deleted_at"),
        ("v5_invoices", "deleted_by"),
    ]

    col_types = {
        "is_deleted": "INTEGER DEFAULT 0",
        "deleted_at": "TEXT DEFAULT ''",
        "deleted_by": "TEXT DEFAULT ''",
    }

    try:
        with connection_scope() as conn:
            for table, col in columns:
                sql = (
                    f"ALTER TABLE {table} ADD COLUMN {col} {col_types[col]}"
                )
                try:
                    conn.execute(sql)
                except Exception:
                    # Column already exists
                    pass
            conn.commit()
        result["ok"] = [f"{t}.{c}" for t, c in columns]
    except Exception as e:
        app_log(f"[soft_delete migration v5] {e}")
        result["errors"].append(str(e))

    return result


# ---------------------------------------------------------------------------
#  Migration – legacy layer (customers & inventory JSON)
# ---------------------------------------------------------------------------

def migrate_legacy_soft_delete() -> dict:
    """Add soft-delete flags to legacy JSON records.

    Idempotent – only adds missing keys.
    """
    result = {"ok": [], "errors": []}

    # Customers
    try:
        data = load_json(F_CUSTOMERS, {})
        changed = False
        for ph, c in data.items():
            if "is_deleted" not in c:
                c["is_deleted"] = False
                c["deleted_at"] = ""
                c["deleted_by"] = ""
                changed = True
        if changed:
            save_json(F_CUSTOMERS, data)
        result["ok"].append("customers")
    except Exception as e:
        app_log(f"[soft_delete migration legacy customers] {e}")
        result["errors"].append(f"customers: {e}")

    # Inventory
    try:
        from inventory import get_inventory, save_inventory
        data = get_inventory()
        changed = False
        for name, item in data.items():
            if "is_deleted" not in item:
                item["is_deleted"] = False
                item["deleted_at"] = ""
                item["deleted_by"] = ""
                changed = True
        if changed:
            save_inventory(data)
        result["ok"].append("inventory")
    except Exception as e:
        app_log(f"[soft_delete migration legacy inventory] {e}")
        result["errors"].append(f"inventory: {e}")

    return result


def run_all_migrations() -> dict:
    result = {}
    result["v5"] = migrate_v5_soft_delete()
    result["legacy"] = migrate_legacy_soft_delete()
    return result


# ---------------------------------------------------------------------------
#  Customer soft-delete helpers
# ---------------------------------------------------------------------------

def soft_delete_customer(phone: str, deleted_by: str = "") -> bool:
    try:
        # Try v5 first
        ensure_v5_schema()
        with connection_scope() as conn:
            row = conn.execute(
                "SELECT id FROM v5_customers WHERE legacy_phone = ?",
                (phone.strip(),),
            ).fetchone()
            if row:
                conn.execute(
                    """
                    UPDATE v5_customers
                    SET is_deleted = 1, deleted_at = datetime('now'), deleted_by = ?
                    WHERE legacy_phone = ?
                    """,
                    (deleted_by, phone.strip()),
                )
                conn.commit()
                log_delete_audit("customer", phone, deleted_by)
                return True
    except Exception as e:
        app_log(f"[soft_delete_customer v5] {e}")

    # Fallback: legacy
    try:
        data = load_json(F_CUSTOMERS, {})
        if phone in data:
            data[phone]["is_deleted"] = True
            data[phone]["deleted_at"] = now_str()
            data[phone]["deleted_by"] = deleted_by
            save_json(F_CUSTOMERS, data)
            log_delete_audit("customer", phone, deleted_by)
            return True
    except Exception as e:
        app_log(f"[soft_delete_customer legacy] {e}")
    return False


def restore_customer(phone: str, restored_by: str = "") -> bool:
    try:
        ensure_v5_schema()
        with connection_scope() as conn:
            row = conn.execute(
                "SELECT id FROM v5_customers WHERE legacy_phone = ?",
                (phone.strip(),),
            ).fetchone()
            if row:
                conn.execute(
                    """
                    UPDATE v5_customers
                    SET is_deleted = 0, deleted_at = '', deleted_by = ''
                    WHERE legacy_phone = ?
                    """,
                    (phone.strip(),),
                )
                conn.commit()
                log_restore_audit("customer", phone, restored_by)
                return True
    except Exception as e:
        app_log(f"[restore_customer v5] {e}")

    try:
        data = load_json(F_CUSTOMERS, {})
        if phone in data:
            data[phone]["is_deleted"] = False
            data[phone]["deleted_at"] = ""
            data[phone]["deleted_by"] = ""
            save_json(F_CUSTOMERS, data)
            log_restore_audit("customer", phone, restored_by)
            return True
    except Exception as e:
        app_log(f"[restore_customer legacy] {e}")
    return False


def permanent_delete_customer(phone: str, deleted_by: str = "") -> bool:
    try:
        ensure_v5_schema()
        with connection_scope() as conn:
            row = conn.execute(
                "SELECT id FROM v5_customers WHERE legacy_phone = ?",
                (phone.strip(),),
            ).fetchone()
            if row:
                conn.execute(
                    "DELETE FROM v5_customers WHERE legacy_phone = ?",
                    (phone.strip(),),
                )
                conn.commit()
                log_permanent_delete_audit("customer", phone, deleted_by)
                return True
    except Exception as e:
        app_log(f"[permanent_delete_customer v5] {e}")

    try:
        data = load_json(F_CUSTOMERS, {})
        if phone in data:
            log_permanent_delete_audit("customer", phone, deleted_by)
            data.pop(phone, None)
            save_json(F_CUSTOMERS, data)
            return True
    except Exception as e:
        app_log(f"[permanent_delete_customer legacy] {e}")
    return False


def get_deleted_customers() -> list[dict]:
    results = []

    # v5
    try:
        ensure_v5_schema()
        with connection_scope() as conn:
            rows = conn.execute(
                """
                SELECT legacy_phone as phone, name, is_deleted, deleted_at, deleted_by
                FROM v5_customers
                WHERE is_deleted = 1
                ORDER BY deleted_at DESC
                """
            ).fetchall()
            for r in rows:
                results.append({
                    "type": "customer",
                    "key": r["phone"],
                    "phone": r["phone"],
                    "name": r["name"],
                    "deleted_at": r["deleted_at"] or "",
                    "deleted_by": r["deleted_by"] or "",
                })
    except Exception as e:
        app_log(f"[get_deleted_customers v5] {e}")

    # Legacy – only if v5 returned nothing (avoid duplicates)
    if not results:
        try:
            data = load_json(F_CUSTOMERS, {})
            for ph, c in data.items():
                if c.get("is_deleted"):
                    results.append({
                        "type": "customer",
                        "key": ph,
                        "phone": ph,
                        "name": c.get("name", ""),
                        "deleted_at": c.get("deleted_at", ""),
                        "deleted_by": c.get("deleted_by", ""),
                    })
        except Exception as e:
            app_log(f"[get_deleted_customers legacy] {e}")

    return results


# ---------------------------------------------------------------------------
#  Inventory / Product soft-delete helpers
# ---------------------------------------------------------------------------

def soft_delete_product(legacy_name: str, deleted_by: str = "") -> bool:
    try:
        ensure_v5_schema()
        with connection_scope() as conn:
            row = conn.execute(
                "SELECT id FROM v5_inventory_items WHERE legacy_name = ?",
                (legacy_name.strip(),),
            ).fetchone()
            if row:
                conn.execute(
                    """
                    UPDATE v5_inventory_items
                    SET is_deleted = 1, deleted_at = datetime('now'), deleted_by = ?
                    WHERE legacy_name = ?
                    """,
                    (deleted_by, legacy_name.strip()),
                )
                conn.commit()
                log_delete_audit("product", legacy_name, deleted_by)
                return True
    except Exception as e:
        app_log(f"[soft_delete_product v5] {e}")

    try:
        from inventory import get_inventory, save_inventory
        data = get_inventory()
        if legacy_name in data:
            data[legacy_name]["is_deleted"] = True
            data[legacy_name]["deleted_at"] = now_str()
            data[legacy_name]["deleted_by"] = deleted_by
            save_inventory(data)
            log_delete_audit("product", legacy_name, deleted_by)
            return True
    except Exception as e:
        app_log(f"[soft_delete_product legacy] {e}")
    return False


def restore_product(legacy_name: str, restored_by: str = "") -> bool:
    try:
        ensure_v5_schema()
        with connection_scope() as conn:
            row = conn.execute(
                "SELECT id FROM v5_inventory_items WHERE legacy_name = ?",
                (legacy_name.strip(),),
            ).fetchone()
            if row:
                conn.execute(
                    """
                    UPDATE v5_inventory_items
                    SET is_deleted = 0, active = 1, deleted_at = '', deleted_by = ''
                    WHERE legacy_name = ?
                    """,
                    (legacy_name.strip(),),
                )
                conn.commit()
                log_restore_audit("product", legacy_name, restored_by)
                return True
    except Exception as e:
        app_log(f"[restore_product v5] {e}")

    try:
        from inventory import get_inventory, save_inventory
        data = get_inventory()
        if legacy_name in data:
            data[legacy_name]["is_deleted"] = False
            data[legacy_name]["deleted_at"] = ""
            data[legacy_name]["deleted_by"] = ""
            save_inventory(data)
            log_restore_audit("product", legacy_name, restored_by)
            return True
    except Exception as e:
        app_log(f"[restore_product legacy] {e}")
    return False


def permanent_delete_product(legacy_name: str, deleted_by: str = "") -> bool:
    try:
        ensure_v5_schema()
        with connection_scope() as conn:
            row = conn.execute(
                "SELECT id FROM v5_inventory_items WHERE legacy_name = ?",
                (legacy_name.strip(),),
            ).fetchone()
            if row:
                conn.execute(
                    "DELETE FROM v5_inventory_items WHERE legacy_name = ?",
                    (legacy_name.strip(),),
                )
                conn.commit()
                log_permanent_delete_audit("product", legacy_name, deleted_by)
                return True
    except Exception as e:
        app_log(f"[permanent_delete_product v5] {e}")

    try:
        from inventory import get_inventory, save_inventory
        data = get_inventory()
        if legacy_name in data:
            log_permanent_delete_audit("product", legacy_name, deleted_by)
            data.pop(legacy_name, None)
            save_inventory(data)
            return True
    except Exception as e:
        app_log(f"[permanent_delete_product legacy] {e}")
    return False


def get_deleted_products() -> list[dict]:
    results = []

    # v5 inventory
    try:
        ensure_v5_schema()
        with connection_scope() as conn:
            rows = conn.execute(
                """
                SELECT legacy_name as name, category, is_deleted, deleted_at, deleted_by
                FROM v5_inventory_items
                WHERE is_deleted = 1
                ORDER BY deleted_at DESC
                """
            ).fetchall()
            for r in rows:
                results.append({
                    "type": "product",
                    "key": r["name"],
                    "name": r["name"],
                    "category": r["category"] or "",
                    "deleted_at": r["deleted_at"] or "",
                    "deleted_by": r["deleted_by"] or "",
                })
    except Exception as e:
        app_log(f"[get_deleted_products v5] {e}")

    if not results:
        try:
            data = load_json(F_INVENTORY, {})
            for nm, item in data.items():
                if item.get("is_deleted"):
                    results.append({
                        "type": "product",
                        "key": nm,
                        "name": nm,
                        "category": item.get("category", ""),
                        "deleted_at": item.get("deleted_at", ""),
                        "deleted_by": item.get("deleted_by", ""),
                    })
        except Exception as e:
            app_log(f"[get_deleted_products legacy] {e}")

    return results


# ---------------------------------------------------------------------------
#  Bill / Invoice soft-delete helpers (v5 invoices only)
# ---------------------------------------------------------------------------

def soft_delete_bill(invoice_no: str, deleted_by: str = "") -> bool:
    try:
        ensure_v5_schema()
        with connection_scope() as conn:
            row = conn.execute(
                "SELECT id FROM v5_invoices WHERE invoice_no = ?",
                (invoice_no.strip(),),
            ).fetchone()
            if row:
                conn.execute(
                    """
                    UPDATE v5_invoices
                    SET is_deleted = 1, deleted_at = datetime('now'), deleted_by = ?
                    WHERE invoice_no = ?
                    """,
                    (deleted_by, invoice_no.strip()),
                )
                conn.commit()
                log_delete_audit("bill", invoice_no, deleted_by)
                return True
    except Exception as e:
        app_log(f"[soft_delete_bill v5] {e}")

    # CSV fallback – mark in audit only (CSV is append-only)
    log_delete_audit("bill", invoice_no, deleted_by)
    app_log(f"[soft_delete_bill] No v5 invoice found for {invoice_no}, audited only")
    return False


def restore_bill(invoice_no: str, restored_by: str = "") -> bool:
    try:
        ensure_v5_schema()
        with connection_scope() as conn:
            row = conn.execute(
                "SELECT id FROM v5_invoices WHERE invoice_no = ?",
                (invoice_no.strip(),),
            ).fetchone()
            if row:
                conn.execute(
                    """
                    UPDATE v5_invoices
                    SET is_deleted = 0, deleted_at = '', deleted_by = ''
                    WHERE invoice_no = ?
                    """,
                    (invoice_no.strip(),),
                )
                conn.commit()
                log_restore_audit("bill", invoice_no, restored_by)
                return True
    except Exception as e:
        app_log(f"[restore_bill v5] {e}")
    return False


def permanent_delete_bill(invoice_no: str, deleted_by: str = "") -> bool:
    try:
        ensure_v5_schema()
        with connection_scope() as conn:
            row = conn.execute(
                "SELECT id FROM v5_invoices WHERE invoice_no = ?",
                (invoice_no.strip(),),
            ).fetchone()
            if row:
                conn.execute(
                    "DELETE FROM v5_invoices WHERE invoice_no = ?",
                    (invoice_no.strip(),),
                )
                conn.commit()
                log_permanent_delete_audit("bill", invoice_no, deleted_by)
                return True
    except Exception as e:
        app_log(f"[permanent_delete_bill v5] {e}")
    return False


def get_deleted_bills() -> list[dict]:
    results = []
    try:
        ensure_v5_schema()
        with connection_scope() as conn:
            rows = conn.execute(
                """
                SELECT invoice_no, customer_name, is_deleted, deleted_at, deleted_by
                FROM v5_invoices
                WHERE is_deleted = 1
                ORDER BY deleted_at DESC
                """
            ).fetchall()
            for r in rows:
                results.append({
                    "type": "bill",
                    "key": r["invoice_no"],
                    "name": f"{r['invoice_no']} – {r['customer_name']}",
                    "invoice_no": r["invoice_no"],
                    "deleted_at": r["deleted_at"] or "",
                    "deleted_by": r["deleted_by"] or "",
                })
    except Exception as e:
        app_log(f"[get_deleted_bills v5] {e}")
    return results


# ---------------------------------------------------------------------------
#  Audit log table for soft-delete history
# ---------------------------------------------------------------------------

def ensure_delete_audit_table():
    ensure_v5_schema()
    with connection_scope() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS soft_delete_audit (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type   TEXT NOT NULL,
                entity_key    TEXT NOT NULL,
                action        TEXT NOT NULL,
                performed_by  TEXT DEFAULT '',
                performed_at  TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sda_type
            ON soft_delete_audit(entity_type)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sda_key
            ON soft_delete_audit(entity_key)
        """)
        conn.commit()


def log_delete_audit(entity_type: str, entity_key: str, performed_by: str):
    ensure_delete_audit_table()
    try:
        with connection_scope() as conn:
            conn.execute(
                """
                INSERT INTO soft_delete_audit(entity_type, entity_key, action, performed_by)
                VALUES (?, ?, 'deleted', ?)
                """,
                (entity_type, entity_key, performed_by),
            )
            conn.commit()
    except Exception as e:
        app_log(f"[log_delete_audit] {e}")


def log_restore_audit(entity_type: str, entity_key: str, performed_by: str):
    ensure_delete_audit_table()
    try:
        with connection_scope() as conn:
            conn.execute(
                """
                INSERT INTO soft_delete_audit(entity_type, entity_key, action, performed_by)
                VALUES (?, ?, 'restored', ?)
                """,
                (entity_type, entity_key, performed_by),
            )
            conn.commit()
    except Exception as e:
        app_log(f"[log_restore_audit] {e}")


def log_permanent_delete_audit(entity_type: str, entity_key: str, performed_by: str):
    ensure_delete_audit_table()
    try:
        with connection_scope() as conn:
            conn.execute(
                """
                INSERT INTO soft_delete_audit(entity_type, entity_key, action, performed_by)
                VALUES (?, ?, 'permanent_deleted', ?)
                """,
                (entity_type, entity_key, performed_by),
            )
            conn.commit()
    except Exception as e:
        app_log(f"[log_permanent_delete_audit] {e}")


def get_delete_audit_history(
    entity_type: str | None = None,
    limit: int = 200,
) -> list[dict]:
    ensure_delete_audit_table()
    try:
        with connection_scope() as conn:
            if entity_type:
                rows = conn.execute(
                    """
                    SELECT entity_type, entity_key, action, performed_by, performed_at
                    FROM soft_delete_audit
                    WHERE entity_type = ?
                    ORDER BY performed_at DESC
                    LIMIT ?
                    """,
                    (entity_type, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT entity_type, entity_key, action, performed_by, performed_at
                    FROM soft_delete_audit
                    ORDER BY performed_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
            return [
                {
                    "entity_type": r["entity_type"],
                    "entity_key": r["entity_key"],
                    "action": r["action"],
                    "performed_by": r["performed_by"] or "",
                    "performed_at": r["performed_at"] or "",
                }
                for r in rows
            ]
    except Exception as e:
        app_log(f"[get_delete_audit_history] {e}")
        return []
