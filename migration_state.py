"""Migration/install state helpers for phased JSON -> SQLite rollout."""

from __future__ import annotations

import os
from datetime import datetime

from salon_settings import get_settings, save_settings
from utils import (
    F_APPOINTMENTS,
    F_CUSTOMERS,
    F_EXPENSES,
    F_INVENTORY,
    F_MEMBERSHIPS,
    F_OFFERS,
    F_REDEEM,
    F_REPORT,
    F_SERVICES,
    F_SETTINGS,
    F_STAFF,
    F_USERS,
)


TRACKED_LEGACY_PATHS = [
    F_SERVICES,
    F_CUSTOMERS,
    F_APPOINTMENTS,
    F_EXPENSES,
    F_STAFF,
    F_INVENTORY,
    F_USERS,
    F_OFFERS,
    F_REDEEM,
    F_MEMBERSHIPS,
    F_REPORT,
]

CORE_V5_FLAGS = (
    "use_v5_customers_db",
    "use_v5_appointments_db",
    "use_v5_reports_db",
    "use_v5_billing_db",
    "use_v5_inventory_db",
    "use_v5_staff_db",
    "use_v5_product_variants_db",
)

CORE_V5_TABLES = (
    "v5_customers",
    "v5_appointments",
    "v5_invoices",
    "v5_invoice_items",
    "v5_inventory_items",
    "v5_staff",
    "v5_product_variants",
)


def legacy_data_exists() -> bool:
    return any(os.path.exists(path) for path in TRACKED_LEGACY_PATHS if path != F_SETTINGS)


def is_new_install() -> bool:
    return not legacy_data_exists()


def get_install_mode() -> str:
    cfg = get_settings()
    return str(cfg.get("install_mode", "hybrid")).strip() or "hybrid"


def migration_completed() -> bool:
    cfg = get_settings()
    return bool(cfg.get("migration_completed", False))


def _core_v5_switches_enabled(cfg: dict) -> bool:
    return all(bool(cfg.get(flag, False)) for flag in CORE_V5_FLAGS)


def _core_v5_schema_ready() -> bool:
    try:
        from db_core.connection import connection_scope

        with connection_scope() as conn:
            existing = {
                str(row[0]).strip().lower()
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        return all(name.lower() in existing for name in CORE_V5_TABLES)
    except Exception:
        return False


def initialize_runtime_migration_state() -> dict:
    cfg = get_settings()
    changed = False

    if is_new_install():
        if cfg.get("install_mode") != "sqlite_new":
            cfg["install_mode"] = "sqlite_new"
            changed = True
        if not cfg.get("sqlite_primary_mode", False):
            cfg["sqlite_primary_mode"] = True
            changed = True
    else:
        if cfg.get("migration_completed", False):
            if cfg.get("install_mode") != "hybrid_migrated":
                cfg["install_mode"] = "hybrid_migrated"
                changed = True
            if not cfg.get("sqlite_primary_mode", False):
                cfg["sqlite_primary_mode"] = True
                changed = True
        elif cfg.get("install_mode") == "sqlite_new":
            cfg["install_mode"] = "hybrid"
            changed = True

    # Auto-finalize migration once core modules are fully on v5 and schema is present.
    if not bool(cfg.get("migration_completed", False)):
        if _core_v5_switches_enabled(cfg) and _core_v5_schema_ready():
            cfg["migration_completed"] = True
            cfg["sqlite_primary_mode"] = True
            cfg["install_mode"] = "hybrid_migrated"
            cfg["migration_completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            changed = True

    # Rollout toggles are debug-only; hide after migration completion.
    if bool(cfg.get("migration_completed", False)) and bool(cfg.get("show_database_rollout_controls", False)):
        cfg["show_database_rollout_controls"] = False
        changed = True

    if changed:
        save_settings(cfg)

    return {
        "ok": True,
        "install_mode": cfg.get("install_mode", "hybrid"),
        "migration_completed": bool(cfg.get("migration_completed", False)),
        "sqlite_primary_mode": bool(cfg.get("sqlite_primary_mode", False)),
        "legacy_data_exists": legacy_data_exists(),
    }


def mark_migration_completed() -> bool:
    cfg = get_settings()
    cfg["migration_completed"] = True
    cfg["sqlite_primary_mode"] = True
    cfg["install_mode"] = "hybrid_migrated"
    cfg["migration_completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return bool(save_settings(cfg))
