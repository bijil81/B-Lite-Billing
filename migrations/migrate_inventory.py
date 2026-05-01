"""Legacy inventory -> v5 inventory migration."""

from __future__ import annotations

from inventory import get_inventory
from repositories.inventory_repo import InventoryRepository


def _pick(payload: dict, *keys, default=""):
    for key in keys:
        if key in payload and payload.get(key) not in (None, ""):
            return payload.get(key)
    return default


def migrate_inventory(dry_run: bool = True) -> dict:
    inventory = get_inventory()
    repo = InventoryRepository()
    migrated = []
    for key, item in inventory.items():
        payload = {
            "legacy_name": key,
            "category": _pick(item, "category", default=""),
            "brand": _pick(item, "brand", default=""),
            "unit": _pick(item, "unit", default="pcs"),
            "current_qty": _pick(item, "qty", "quantity", "stock", default=0.0),
            "min_qty": _pick(item, "min_qty", "min_stock", default=0.0),
            "cost_price": _pick(item, "cost", "cost_price", default=0.0),
            "sale_price": _pick(item, "price", "sale_price", default=0.0),
            "active": not bool(item.get("inactive", False)),
        }
        if not dry_run:
            repo.upsert_item(payload)
        migrated.append(key)
    return {
        "source_count": len(inventory),
        "migrated": migrated,
        "dry_run": dry_run,
    }
