"""Compatibility adapter for gradual product-variant rollout."""

from __future__ import annotations

from salon_settings import get_settings
from services_v5.product_catalog_service import ProductCatalogService
from utils import F_SERVICES, build_item_codes, load_json


_PRODUCT_SERVICE = ProductCatalogService()


def use_v5_product_variants_db() -> bool:
    return bool(get_settings().get("use_v5_product_variants_db", False))


def create_product_with_variants_v5(payload: dict) -> dict:
    return _PRODUCT_SERVICE.create_product_with_variants(payload)


def search_product_variants_v5(query: str = "") -> list[dict]:
    return _PRODUCT_SERVICE.list_billable_variants(query)


def refresh_product_catalog_cache() -> None:
    build_item_codes(force=True)


def get_billing_services_products_snapshot() -> tuple[dict, dict]:
    data = load_json(F_SERVICES, {})
    services = data.get("Services", {}) if ("Services" in data or "Products" in data) else data
    legacy_products = data.get("Products", {}) if ("Services" in data or "Products" in data) else {}

    if not use_v5_product_variants_db():
        return services, legacy_products

    rows = _PRODUCT_SERVICE.list_billable_variants("")
    if not rows:
        return services, legacy_products

    sqlite_products: dict[str, dict[str, float]] = {}
    for row in rows:
        category = str(row.get("category_name", "")).strip() or "General"
        name = str(row.get("display_name", "")).strip() or str(row.get("product_name", "")).strip()
        if not name:
            continue
        sqlite_products.setdefault(category, {})[name] = float(row.get("sale_price", 0.0) or 0.0)
    return services, sqlite_products


def list_billing_product_matches(query: str = "", category: str = "All") -> tuple[list[tuple], dict]:
    rows = _PRODUCT_SERVICE.list_billable_variants(query) if use_v5_product_variants_db() else []
    matches: list[tuple] = []
    variant_meta: dict[str, dict] = {}
    seen_keys: set[tuple[str, str]] = set()

    for row in rows:
        cat = str(row.get("category_name", "")).strip() or "General"
        if category != "All" and cat != category:
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
        matches.append((code, name, cat, price))
        variant_meta[code] = row
        seen_keys.add((name.lower(), cat.lower()))

    q = query.strip().lower()
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

    matches.sort(key=lambda x: x[1].lower())
    return matches, variant_meta


def list_billing_product_categories() -> list[str]:
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
    return sorted(cats)
