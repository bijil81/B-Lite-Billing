from __future__ import annotations

from typing import Any, Mapping, MutableSequence, Sequence


def normalize_v5_variant_barcode_match(variant: Mapping[str, Any]) -> dict[str, Any]:
    stock = float(variant.get("stock_qty", 0) or 0)
    result = {
        "name": variant.get("variant_name", ""),
        "price": float(variant.get("sale_price", 0) or 0),
        "qty": stock,
        "stock_available": stock > 0,
        "variant_id": variant.get("id"),
    }
    for key in (
        "unit_type",
        "unit_value",
        "pack_label",
        "bill_label",
        "category",
        "category_name",
        "sale_unit",
        "base_unit",
        "unit_multiplier",
        "allow_decimal_qty",
        "is_weighed",
        "gst_rate",
        "hsn_sac",
        "price_includes_tax",
    ):
        if variant.get(key) is not None:
            result[key] = variant.get(key)
    return result


def normalize_legacy_inventory_barcode_match(item_name: str, item: Mapping[str, Any]) -> dict[str, Any]:
    stock = float(item.get("qty", 0) or 0)
    sale_price = float(item.get("price", item.get("cost", 0)) or 0)
    result = {
        "name": item_name,
        "price": sale_price,
        "qty": stock,
        "stock_available": stock > 0,
    }
    for key in (
        "unit",
        "category",
        "category_name",
        "sale_unit",
        "base_unit",
        "unit_multiplier",
        "allow_decimal_qty",
        "is_weighed",
        "gst_rate",
        "hsn_sac",
        "price_includes_tax",
        "bill_label",
    ):
        if item.get(key) is not None:
            result[key] = item.get(key)
    return result


def find_barcode_in_variants(barcode: str, variants: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    clean_barcode = (barcode or "").strip()
    if not clean_barcode:
        return None
    for variant in variants:
        variant_barcode = (variant.get("barcode") or "").strip()
        if variant_barcode and variant_barcode == clean_barcode:
            return normalize_v5_variant_barcode_match(variant)
    return None


def find_barcode_in_inventory(barcode: str, inventory: Mapping[str, Mapping[str, Any]]) -> dict[str, Any] | None:
    clean_barcode = (barcode or "").strip()
    if not clean_barcode:
        return None
    for item_name, item in inventory.items():
        item_barcode = (item.get("barcode") or "").strip()
        if item_barcode and item_barcode == clean_barcode:
            return normalize_legacy_inventory_barcode_match(item_name, item)
    return None


def build_scanned_product_item(found: Mapping[str, Any]) -> dict[str, Any]:
    name = found["name"]
    item = {
        "mode": "products",
        "name": name,
        "price": float(found["price"]),
        "qty": 1,
        "inventory_item_name": name,
    }
    if found.get("variant_id"):
        item["variant_id"] = found["variant_id"]
    for key in (
        "unit_type",
        "unit_value",
        "pack_label",
        "bill_label",
        "category",
        "category_name",
        "sale_unit",
        "base_unit",
        "unit_multiplier",
        "allow_decimal_qty",
        "is_weighed",
        "gst_rate",
        "hsn_sac",
        "price_includes_tax",
    ):
        if found.get(key) is not None:
            item[key] = found.get(key)
    return item


def apply_scanned_product_to_bill(
    bill_items: MutableSequence[dict[str, Any]],
    found: Mapping[str, Any],
) -> dict[str, Any]:
    name = found["name"]
    if not found.get("stock_available", True):
        return {"status": "out_of_stock", "name": name}

    for item in bill_items:
        if item.get("mode") == "products" and item["name"].lower() == name.lower():
            item["qty"] += 1
            return {"status": "incremented", "name": name}

    bill_items.append(build_scanned_product_item(found))
    return {"status": "added", "name": name}
