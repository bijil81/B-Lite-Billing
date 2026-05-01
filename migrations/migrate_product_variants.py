"""Legacy inventory to product-variant foundation migration."""

from __future__ import annotations

from inventory import get_inventory
from services_v5.product_catalog_service import ProductCatalogService
from validators.product_validator import build_pack_label


GENERIC_BRAND = "Generic"


def migrate_product_variants(dry_run: bool = True) -> dict:
    inventory = get_inventory()
    service = ProductCatalogService()
    migrated = []
    for legacy_name, item in inventory.items():
        unit_type = str(item.get("unit", "pcs")).strip() or "pcs"
        payload = {
            "brand_name": str(item.get("brand", "")).strip() or GENERIC_BRAND,
            "category_name": str(item.get("category", "")).strip() or "Uncategorized",
            "product_name": legacy_name,
            "base_name": legacy_name,
            "variants": [{
                "variant_name": "Default",
                "unit_value": 1,
                "unit_type": unit_type,
                "pack_label": build_pack_label(1, unit_type),
                "bill_label": legacy_name,
                "sale_price": float(item.get("price", item.get("sale_price", 0.0)) or 0.0),
                "cost_price": float(item.get("cost", item.get("cost_price", 0.0)) or 0.0),
                "stock_qty": float(item.get("qty", item.get("stock", 0.0)) or 0.0),
                "reorder_level": float(item.get("min_stock", item.get("min_qty", 0.0)) or 0.0),
            }],
        }
        if not dry_run:
            service.create_product_with_variants(payload)
        migrated.append(legacy_name)
    return {
        "source_count": len(inventory),
        "migrated": migrated,
        "dry_run": dry_run,
        "notes": "Legacy items are mapped 1:1 as default variants; manual cleanup can split them into true size variants later.",
    }
