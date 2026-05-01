"""Compatibility adapter for gradual product-variant rollout."""

from __future__ import annotations

from salon_settings import get_settings
from services_v5.product_catalog_service import ProductCatalogService
from utils import F_INVENTORY, F_SERVICES, app_log, build_item_codes, load_json
from src.blite_v6.inventory_grocery.billing_inventory_bridge import (
    append_inventory_product_matches,
    iter_inventory_billing_rows,
    inventory_product_categories,
    merge_inventory_products,
)


_PRODUCT_SERVICE = ProductCatalogService()


def _load_inventory_for_billing() -> dict:
    """Read the active inventory source used by InventoryFrame saves."""
    try:
        from services_v5.inventory_service import InventoryService
        inventory = InventoryService().build_legacy_inventory_map()
        if inventory:
            return inventory
    except Exception as exc:
        app_log(f"[_load_inventory_for_billing] InventoryService fallback: {exc}")
    return load_json(F_INVENTORY, {})


def use_v5_product_variants_db() -> bool:
    return bool(get_settings().get("use_v5_product_variants_db", False))


def create_product_with_variants_v5(payload: dict) -> dict:
    return _PRODUCT_SERVICE.create_product_with_variants(payload)


def get_deleted_products_v5() -> list[dict]:
    """Return soft-deleted inventory items for the Deleted Products dialog."""
    from soft_delete import get_deleted_products
    return get_deleted_products()


def restore_product_v5(legacy_name: str, *, restored_by: str = "") -> bool:
    """Restore a soft-deleted product and refresh billing item cache."""
    from services_v5.inventory_service import InventoryService
    ok = False
    try:
        InventoryService().restore_item(legacy_name)
        ok = True
    except Exception:
        from soft_delete import restore_product
        ok = restore_product(legacy_name, restored_by=restored_by)
    if ok:
        build_item_codes(force=True)
    return ok


def permanent_delete_product_v5(legacy_name: str) -> bool:
    """Permanently delete a product from both v5 and legacy."""
    from soft_delete import permanent_delete_product
    return permanent_delete_product(legacy_name)


def search_product_variants_v5(query: str = "") -> list[dict]:
    return _PRODUCT_SERVICE.list_billable_variants(query)


def refresh_product_catalog_cache() -> None:
    build_item_codes(force=True)


def get_billing_services_products_snapshot() -> tuple[dict, dict]:
    data = load_json(F_SERVICES, {})
    inventory = _load_inventory_for_billing()
    services = data.get("Services", {}) if ("Services" in data or "Products" in data) else data
    legacy_products = data.get("Products", {}) if ("Services" in data or "Products" in data) else {}

    if not use_v5_product_variants_db():
        return services, merge_inventory_products(legacy_products, inventory)

    rows = _PRODUCT_SERVICE.list_billable_variants("")
    if not rows:
        return services, merge_inventory_products(legacy_products, inventory)

    sqlite_products: dict[str, dict[str, float]] = {}
    for row in rows:
        category = str(row.get("category_name", "")).strip() or "General"
        name = str(row.get("display_name", "")).strip() or str(row.get("product_name", "")).strip()
        if not name:
            continue
        sqlite_products.setdefault(category, {})[name] = float(row.get("sale_price", 0.0) or 0.0)
    return services, merge_inventory_products(sqlite_products, inventory)


def list_billing_product_matches(query: str = "", category: str = "All") -> tuple[list[tuple], dict]:
    from repositories.inventory_repo import InventoryRepository
    rows = _PRODUCT_SERVICE.list_billable_variants(query) if use_v5_product_variants_db() else []
    matches: list[tuple] = []
    variant_meta: dict[str, dict] = {}
    seen_keys: set[tuple[str, str]] = set()

    # Build set of soft-deleted legacy names from v5_inventory_items
    deleted_legacy_names: set[str] = set()
    if use_v5_product_variants_db():
        try:
            from db_core.connection import connection_scope
            from db_core.schema_manager import ensure_v5_schema
            ensure_v5_schema()
            with connection_scope() as conn:
                for row in conn.execute(
                    "SELECT legacy_name FROM v5_inventory_items WHERE is_deleted = 1"
                ).fetchall():
                    deleted_legacy_names.add(str(row["legacy_name"]).strip().lower())
        except Exception:
            pass

    for row in rows:
        cat = str(row.get("category_name", "")).strip() or "General"
        if category != "All" and cat != category:
            continue
        legacy_name = str(row.get("bill_label", "")).strip().lower() or str(row.get("display_name", "")).strip().lower()
        if legacy_name in deleted_legacy_names:
            continue
        code = (
            str(row.get("sku", "")).strip()
            or str(row.get("barcode", "")).strip()
            or f"PV{int(row.get('id', 0) or 0):05d}"
        )
        name = str(row.get("display_name", "")).strip() or str(row.get("product_name", "")).strip()
        if not name:
            continue
        price = float(row.get("sale_price", 0.0) or 0.0)
        barcode = str(row.get("barcode", "")).strip()
        matches.append((code, name, cat, price))
        variant_meta[code] = row
        seen_keys.add((name.lower(), cat.lower()))

    q = query.strip().lower()
    inventory = _load_inventory_for_billing()
    inventory_rows = list(iter_inventory_billing_rows(inventory))
    inventory_by_name = {
        str(row.get("display_name", "")).strip().lower(): row
        for row in inventory_rows
        if str(row.get("display_name", "")).strip()
    }
    for code, item in build_item_codes().items():
        if item.get("type") != "product":
            continue
        cat = str(item.get("category", "")).strip()
        name = str(item.get("name", "")).strip()
        if category != "All" and cat != category:
            continue
        if q and q not in code.lower() and q not in name.lower() and q not in cat.lower():
            continue
        key = (name.lower(), cat.lower())
        if key in seen_keys:
            continue
        matches.append((code, name, cat, float(item.get("price", 0.0) or 0.0)))
        seen_keys.add(key)
        inv_row = inventory_by_name.get(name.lower(), {})
        if inv_row:
            variant_meta[code] = {
                "id": None,
                "display_name": name,
                "unit_type": str(inv_row.get("unit_type", "pcs")).strip() or "pcs",
                "unit_value": float(inv_row.get("unit_value", 1) or 1),
                "pack_label": str(inv_row.get("pack_label", "")).strip() or str(inv_row.get("unit_type", "pcs")).strip() or "pcs",
                "bill_label": str(inv_row.get("bill_label", name)).strip() or name,
                "stock_qty": float(inv_row.get("stock_qty", 0.0) or 0.0),
                "sale_price": float(item.get("price", 0.0) or 0.0),
            }

    append_inventory_product_matches(
        matches,
        variant_meta,
        seen_keys,
        query=query,
        category=category,
        existing_codes={str(code) for code, *_rest in matches},
        inventory=inventory,
    )

    matches.sort(key=lambda x: x[1].lower())
    return matches, variant_meta


def list_billing_product_categories() -> list[str]:
    inventory = _load_inventory_for_billing()
    rows = _PRODUCT_SERVICE.list_billable_variants("") if use_v5_product_variants_db() else []
    cats = {
        str(row.get("category_name", "")).strip()
        for row in rows
        if str(row.get("category_name", "")).strip()
    }
    for item in build_item_codes().values():
        if item.get("type") == "product":
            cat = str(item.get("category", "")).strip()
            if cat:
                cats.add(cat)
    cats.update(inventory_product_categories(inventory))
    return sorted(cats)
