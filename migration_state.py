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
