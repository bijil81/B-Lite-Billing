"""Validation helpers for product and variant catalog payloads."""

from __future__ import annotations


def build_pack_label(unit_value: object, unit_type: object) -> str:
    value = str(unit_value or "").strip()
    unit = str(unit_type or "pcs").strip()
    if not value:
        return unit or "pcs"
    if value.endswith(".0"):
        value = value[:-2]
    return f"{value}{unit}"


def validate_variant_payload(payload: dict) -> dict:
    unit_type = str(payload.get("unit_type", "pcs")).strip() or "pcs"
    unit_value = payload.get("unit_value", 0)
    sale_price = float(payload.get("sale_price", 0.0) or 0.0)
    cost_price = float(payload.get("cost_price", 0.0) or 0.0)
    stock_qty = float(payload.get("stock_qty", 0.0) or 0.0)
    reorder_level = float(payload.get("reorder_level", 0.0) or 0.0)
    pack_label = str(payload.get("pack_label", "")).strip() or build_pack_label(unit_value, unit_type)
    if sale_price < 0 or cost_price < 0:
        raise ValueError("Variant prices cannot be negative")
    if stock_qty < 0 or reorder_level < 0:
        raise ValueError("Stock values cannot be negative")
    return {
        **payload,
        "unit_type": unit_type,
        "pack_label": pack_label,
        "sale_price": sale_price,
        "cost_price": cost_price,
        "stock_qty": stock_qty,
        "reorder_level": reorder_level,
    }


def validate_product_catalog_payload(payload: dict) -> dict:
    product_name = str(payload.get("product_name", "")).strip()
    if not product_name:
        raise ValueError("Product name is required")
    variants = payload.get("variants") or []
    if not variants:
        raise ValueError("At least one variant is required")
    normalized = []
    seen = set()
    for variant in variants:
        row = validate_variant_payload(variant)
        key = row.get("pack_label", "").lower()
        if key in seen:
            raise ValueError(f"Duplicate variant pack label: {row.get('pack_label', '')}")
        seen.add(key)
        normalized.append(row)
    return {
        **payload,
        "brand_name": str(payload.get("brand_name", "")).strip(),
        "category_name": str(payload.get("category_name", "")).strip(),
        "product_name": product_name,
        "base_name": str(payload.get("base_name", product_name)).strip() or product_name,
        "description": str(payload.get("description", "")).strip(),
        "variants": normalized,
    }


def build_variant_display_name(row: dict) -> str:
    bill_label = str(row.get("bill_label", "")).strip()
    if bill_label:
        return bill_label
    parts = [
        str(row.get("brand_name", "")).strip(),
        str(row.get("product_name", row.get("base_name", ""))).strip(),
        str(row.get("pack_label", "")).strip(),
    ]
    return " ".join(part for part in parts if part).strip()
