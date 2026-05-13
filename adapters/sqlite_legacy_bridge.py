"""Bridge selected legacy JSON assets to dedicated SQLite v5 storage.

This adapter keeps the old load_json/save_json contract intact while routing
target datasets to relational/settings tables instead of kv-store blobs/files.
"""

from __future__ import annotations

import json
import os

from db_core.connection import connection_scope
from db_core.schema_manager import ensure_v5_schema
from repositories.settings_repo import SettingsRepository
from services_v5.inventory_service import InventoryService
from services_v5.service_master_service import ServiceMasterService


_settings_repo = SettingsRepository()

_SERVICES_KEY = "legacy_services_db_json"
_SERVICES_MIGRATED_KEY = "legacy_services_db_relational_migrated"
_INVOICE_COUNTER_KEY = "legacy_invoice_counter_json"
_service_master = ServiceMasterService()
_inventory_service = InventoryService()


def _basename(path: str) -> str:
    return os.path.basename(str(path or "")).strip().lower()


def _parse_json_blob(raw: str | None, default):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except Exception:
        return default


def load_special_json_v5(path: str, default=None) -> tuple[bool, object]:
    """Return (handled, data)."""
    name = _basename(path)
    if name == "services_db.json":
        _migrate_legacy_services_blob_if_needed()
        return True, _load_services_payload(default if default is not None else {})
    if name == "invoice_counter.json":
        raw = _settings_repo.get(_INVOICE_COUNTER_KEY)
        return True, _parse_json_blob(raw, default if default is not None else {"last": 0, "month": ""})
    if name == "redeem_codes.json":
        return True, _load_redeem_codes(default if default is not None else {})
    return False, default


def save_special_json_v5(path: str, data) -> tuple[bool, bool]:
    """Return (handled, ok)."""
    name = _basename(path)
    if name == "services_db.json":
        return True, _save_services_payload(data)
    if name == "invoice_counter.json":
        return True, _save_invoice_counter_json(data)
    if name == "redeem_codes.json":
        return True, _save_redeem_codes(data)
    return False, False


def _migrate_legacy_services_blob_if_needed() -> None:
    try:
        if _settings_repo.get_bool(_SERVICES_MIGRATED_KEY, False):
            return
        raw = _settings_repo.get(_SERVICES_KEY)
        payload = _parse_json_blob(raw, {})
        if not isinstance(payload, dict) or not payload:
            _settings_repo.set_bool(_SERVICES_MIGRATED_KEY, True)
            return

        if not _service_master.has_services() and payload.get("Services"):
            _service_master.import_legacy_payload(payload, deactivate_missing=False)
        if not _inventory_service.list_items() and payload.get("Products"):
            _inventory_service.sync_legacy_inventory_map(
                _legacy_products_to_inventory_map(payload.get("Products", {}))
            )

        _settings_repo.set(_SERVICES_KEY, "")
        _settings_repo.set_bool(_SERVICES_MIGRATED_KEY, True)
    except Exception:
        return


def _load_services_payload(default) -> dict:
    services = _service_master.list_grouped_services(active_only=True)
    products = _group_legacy_products()
    if services or products:
        return {"Services": services, "Products": products}
    return default if isinstance(default, dict) else {}


def _group_legacy_products() -> dict[str, dict[str, float]]:
    grouped: dict[str, dict[str, float]] = {}
    try:
        inventory = _inventory_service.build_legacy_inventory_map()
        for name, item in inventory.items():
            legacy_name = str(name or "").strip()
            if not legacy_name:
                continue
            category = str(item.get("category", "")).strip() or "General"
            grouped.setdefault(category, {})[legacy_name] = float(
                item.get("price", item.get("sale_price", item.get("cost", 0.0))) or 0.0
            )
    except Exception:
        return {}
    return grouped


def _legacy_products_to_inventory_map(products_blob: dict) -> dict:
    inventory: dict[str, dict] = {}
    if not isinstance(products_blob, dict):
        return inventory
    for category, items in products_blob.items():
        category_name = str(category or "").strip() or "General"
        if not isinstance(items, dict):
            continue
        for name, price in items.items():
            legacy_name = str(name or "").strip()
            if not legacy_name:
                continue
            try:
                price_value = float(price or 0.0)
            except Exception:
                price_value = 0.0
            inventory[legacy_name] = {
                "category": category_name,
                "qty": 0.0,
                "unit": "pcs",
                "min_stock": 5.0,
                "min_qty": 5.0,
                "cost": price_value,
                "price": price_value,
                "inactive": False,
                "bill_label": legacy_name,
                "base_product": legacy_name,
            }
    return inventory


def _save_services_payload(data) -> bool:
    try:
        payload = data if isinstance(data, dict) else {}
        split_payload = "Services" in payload or "Products" in payload
        services_blob = payload.get("Services", {}) if split_payload else payload
        products_blob = payload.get("Products", {}) if split_payload else None

        _service_master.sync_grouped_services(services_blob, deactivate_missing=True)
        if isinstance(products_blob, dict):
            _inventory_service.sync_legacy_inventory_map(
                _legacy_products_to_inventory_map(products_blob)
            )

        _settings_repo.set(_SERVICES_KEY, "")
        _settings_repo.set_bool(_SERVICES_MIGRATED_KEY, True)
        return True
    except Exception:
        return False


def _save_invoice_counter_json(data) -> bool:
    try:
        payload = data if isinstance(data, dict) else {"last": 0, "month": ""}
        payload = {
            "last": int(payload.get("last", 0) or 0),
            "month": str(payload.get("month", "") or ""),
        }
        _settings_repo.set(_INVOICE_COUNTER_KEY, json.dumps(payload, ensure_ascii=False))
        return True
    except Exception:
        return False


def _load_redeem_codes(default) -> dict:
    ensure_v5_schema()
    with connection_scope() as conn:
        rows = conn.execute(
            """
            SELECT
                code, customer_phone, customer_name, discount_type,
                discount_value, used, used_invoice, valid_until,
                created_at, note, used_on
            FROM v5_redeem_codes
            WHERE COALESCE(active, 1) = 1
            ORDER BY created_at DESC, code DESC
            """
        ).fetchall()

    if not rows:
        return default if isinstance(default, dict) else {}

    result: dict[str, dict] = {}
    for row in rows:
        code = str(row["code"] or "").strip()
        if not code:
            continue
        result[code] = {
            "discount_type": str(row["discount_type"] or "flat"),
            "value": float(row["discount_value"] or 0.0),
            "phone": str(row["customer_phone"] or ""),
            "name": str(row["customer_name"] or ""),
            "expiry": str(row["valid_until"] or ""),
            "note": str(row["note"] or ""),
            "used": bool(row["used"]),
            "used_on": str(row["used_on"] or ""),
            "used_invoice": str(row["used_invoice"] or ""),
            "created": str(row["created_at"] or ""),
        }
    return result


def _save_redeem_codes(data) -> bool:
    if not isinstance(data, dict):
        return False
    ensure_v5_schema()

    incoming_codes = {str(code).strip() for code in data.keys() if str(code).strip()}
    with connection_scope() as conn:
        for code, item in data.items():
            code_s = str(code or "").strip()
            if not code_s:
                continue
            item = item if isinstance(item, dict) else {}
            conn.execute(
                """
                INSERT INTO v5_redeem_codes(
                    code, customer_phone, customer_name, discount_type,
                    discount_value, min_bill, active, used, used_invoice,
                    valid_until, note, used_on, updated_at
                ) VALUES(?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(code) DO UPDATE SET
                    customer_phone = excluded.customer_phone,
                    customer_name = excluded.customer_name,
                    discount_type = excluded.discount_type,
                    discount_value = excluded.discount_value,
                    min_bill = excluded.min_bill,
                    active = 1,
                    used = excluded.used,
                    used_invoice = excluded.used_invoice,
                    valid_until = excluded.valid_until,
                    note = excluded.note,
                    used_on = excluded.used_on,
                    updated_at = excluded.updated_at
                """,
                (
                    code_s,
                    str(item.get("phone", item.get("customer_phone", "")) or ""),
                    str(item.get("name", item.get("customer_name", "")) or ""),
                    str(item.get("discount_type", "flat") or "flat"),
                    float(item.get("value", item.get("discount_value", 0.0)) or 0.0),
                    float(item.get("min_bill", 0.0) or 0.0),
                    1 if bool(item.get("used", False)) else 0,
                    str(item.get("used_invoice", "") or ""),
                    str(item.get("expiry", item.get("valid_until", "")) or ""),
                    str(item.get("note", "") or ""),
                    str(item.get("used_on", "") or ""),
                ),
            )

        if incoming_codes:
            placeholders = ",".join("?" for _ in incoming_codes)
            conn.execute(
                f"UPDATE v5_redeem_codes SET active = 0, updated_at = datetime('now') WHERE code NOT IN ({placeholders})",
                tuple(incoming_codes),
            )
        else:
            conn.execute(
                "UPDATE v5_redeem_codes SET active = 0, updated_at = datetime('now')"
            )
    return True
