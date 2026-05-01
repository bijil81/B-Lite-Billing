"""Workflow layer for product/variant catalog."""

from __future__ import annotations

from repositories.brands_repo import BrandsRepository
from repositories.product_categories_repo import ProductCategoriesRepository
from repositories.products_repo import ProductsRepository
from repositories.product_variants_repo import ProductVariantsRepository
from validators.product_validator import (
    build_pack_label,
    build_variant_display_name,
    validate_product_catalog_payload,
)


class ProductCatalogService:
    def __init__(
        self,
        brands_repo: BrandsRepository | None = None,
        categories_repo: ProductCategoriesRepository | None = None,
        products_repo: ProductsRepository | None = None,
        variants_repo: ProductVariantsRepository | None = None,
    ):
        self.brands_repo = brands_repo or BrandsRepository()
        self.categories_repo = categories_repo or ProductCategoriesRepository()
        self.products_repo = products_repo or ProductsRepository()
        self.variants_repo = variants_repo or ProductVariantsRepository()

    def create_product_with_variants(self, payload: dict) -> dict:
        data = validate_product_catalog_payload(payload)
        brand_id = None
        category_id = None
        if data.get("brand_name"):
            brand_id = self.brands_repo.upsert({"name": data["brand_name"]})
        if data.get("category_name"):
            category_id = self.categories_repo.upsert({"name": data["category_name"]})
        product_id = self.products_repo.upsert({
            "brand_id": brand_id,
            "category_id": category_id,
            "name": data["product_name"],
            "base_name": data.get("base_name", data["product_name"]),
            "description": data.get("description", ""),
            "active": True,
        })
        variant_ids = []
        for variant in data["variants"]:
            variant_ids.append(self.variants_repo.upsert_variant({
                **variant,
                "product_id": product_id,
            }))
        return {
            "product_id": product_id,
            "variant_ids": variant_ids,
            "brand_name": data.get("brand_name", ""),
            "category_name": data.get("category_name", ""),
            "product_name": data["product_name"],
        }

    def list_billable_variants(self, query: str = "") -> list[dict]:
        rows = self.variants_repo.search_sellable(query) if query.strip() else self.variants_repo.list_all()
        return [
            {
                **row,
                "display_name": build_variant_display_name(row),
            }
            for row in rows
        ]

    def record_stock_movement(self, payload: dict) -> None:
        self.variants_repo.add_stock_movement(payload)

    def build_inventory_rows(self) -> list[dict]:
        rows = []
        for row in self.variants_repo.list_all(active_only=False):
            rows.append({
                **row,
                "display_name": build_variant_display_name(row),
                "stock_qty": float(row.get("stock_qty", 0.0) or 0.0),
                "sale_price": float(row.get("sale_price", 0.0) or 0.0),
                "cost_price": float(row.get("cost_price", 0.0) or 0.0),
            })
        return rows

    def sync_inventory_row(self, payload: dict) -> bool:
        legacy_name = str(payload.get("legacy_name", payload.get("bill_label", ""))).strip()
        if not legacy_name:
            return False

        unit = str(payload.get("unit", "pcs")).strip() or "pcs"
        current_qty = float(payload.get("current_qty", payload.get("qty", 0.0)) or 0.0)
        min_qty = float(payload.get("min_qty", payload.get("min_stock", 0.0)) or 0.0)
        cost_price = float(payload.get("cost_price", payload.get("cost", 0.0)) or 0.0)
        active = bool(payload.get("active", True))

        for row in self.variants_repo.list_all(active_only=False):
            display_name = build_variant_display_name(row)
            aliases = {
                display_name.strip().lower(),
                str(row.get("variant_name", "")).strip().lower(),
                str(row.get("bill_label", "")).strip().lower(),
            }
            if legacy_name.lower() not in aliases:
                continue
            self.variants_repo.upsert_variant({
                "product_id": row["product_id"],
                "variant_name": str(row.get("variant_name", "")).strip() or legacy_name,
                "unit_value": row.get("unit_value", 0.0),
                "unit_type": unit or str(row.get("unit_type", "pcs")).strip() or "pcs",
                "pack_label": str(row.get("pack_label", "")).strip() or build_pack_label(row.get("unit_value", 0.0), unit),
                "bill_label": str(row.get("bill_label", "")).strip() or legacy_name,
                "sku": str(row.get("sku", "")).strip(),
                "barcode": str(row.get("barcode", "")).strip(),
                "sale_price": float(row.get("sale_price", cost_price) or cost_price),
                "cost_price": cost_price,
                "stock_qty": current_qty,
                "reorder_level": min_qty,
                "sale_unit": payload.get("sale_unit", row.get("sale_unit", unit)),
                "base_unit": payload.get("base_unit", row.get("base_unit", unit)),
                "unit_multiplier": payload.get("unit_multiplier", row.get("unit_multiplier", 1.0)),
                "allow_decimal_qty": payload.get("allow_decimal_qty", row.get("allow_decimal_qty", 0)),
                "mrp": payload.get("mrp", row.get("mrp", 0.0)),
                "gst_rate": payload.get("gst_rate", row.get("gst_rate", 0.0)),
                "cess_rate": payload.get("cess_rate", row.get("cess_rate", 0.0)),
                "hsn_sac": payload.get("hsn_sac", row.get("hsn_sac", "")),
                "price_includes_tax": payload.get("price_includes_tax", row.get("price_includes_tax", 1)),
                "is_weighed": payload.get("is_weighed", row.get("is_weighed", 0)),
                "active": active,
            })
            return True
        return False

    def deactivate_variants_for_inventory_name(self, legacy_name: str) -> int:
        target = str(legacy_name or "").strip().lower()
        if not target:
            return 0
        deactivated = 0
        for row in self.variants_repo.list_all(active_only=False):
            display_name = build_variant_display_name(row)
            aliases = {
                display_name.strip().lower(),
                str(row.get("variant_name", "")).strip().lower(),
                str(row.get("bill_label", "")).strip().lower(),
            }
            if target in aliases and bool(row.get("active", 1)):
                self.variants_repo.deactivate_variant(int(row["id"]))
                deactivated += 1
        return deactivated
