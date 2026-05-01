"""Inventory product-master form helpers for retail/grocery fields.

These helpers keep the Tk form thin and preserve the legacy inventory shape
while carrying richer product-master fields into the v5 product catalog.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping

from .product_units import normalize_unit
from .product_validation import ProductValidationResult, validate_product_payload
from .gst_autofill import autofill_inventory_gst_rate


FORM_UNITS = ("pcs", "kg", "g", "L", "ml", "meter", "custom")
DECIMAL_QTY_UNITS = {"kg", "g", "L", "ml", "meter"}


@dataclass(frozen=True)
class ProductFormPayload:
    validation: ProductValidationResult
    inventory_item: dict[str, Any]
    catalog_payload: dict[str, Any]


def _decimal_to_float(value: object, default: float = 0.0) -> float:
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value if value not in (None, "") else default)
    except Exception:
        return default


def _text(value: object, default: str = "") -> str:
    text = str(value if value is not None else "").strip()
    return text or default


def _bool(value: object, default: bool = False) -> bool:
    if value in (None, ""):
        return default
    if isinstance(value, str):
        return value.strip().lower() in {"1", "yes", "true", "on", "y"}
    return bool(value)


def default_sale_unit(unit: object) -> str:
    normalized = normalize_unit(unit or "pcs") or "pcs"
    return normalized if normalized in FORM_UNITS else "custom"


def should_show_grocery_controls(settings: Mapping[str, Any] | None) -> bool:
    cfg = dict(settings or {})
    return bool(
        cfg.get("retail_grocery_enabled")
        or cfg.get("grocery_mode")
        or cfg.get("billing_mode") in {"mixed", "product_only"}
    )


def build_inventory_product_form_payload(
    raw: Mapping[str, Any],
    *,
    settings: Mapping[str, Any] | None = None,
) -> ProductFormPayload:
    raw = autofill_inventory_gst_rate(raw, settings=settings)
    unit = default_sale_unit(raw.get("unit") or "pcs")
    sale_unit = default_sale_unit(raw.get("sale_unit") or unit)
    base_unit = default_sale_unit(raw.get("base_unit") or sale_unit)
    category = _text(raw.get("category"), "Uncategorized")
    name = _text(raw.get("name"))
    bill_label = _text(raw.get("bill_label"), name)
    base_product = _text(raw.get("base_product"), name)
    cost_price = raw.get("cost_price", raw.get("cost", 0))
    sale_price = raw.get("sale_price", raw.get("price", cost_price))
    stock_qty = raw.get("stock_qty", raw.get("qty", 0))
    reorder_level = raw.get("reorder_level", raw.get("min_stock", 0))
    allow_decimal = _bool(raw.get("allow_decimal_qty"), unit in DECIMAL_QTY_UNITS)
    is_weighed = _bool(raw.get("is_weighed"), unit in {"kg", "g"})
    tax_inclusive = _bool(raw.get("tax_inclusive", raw.get("price_includes_tax")), True)

    validation = validate_product_payload(
        {
            "name": name,
            "category": category,
            "sale_price": sale_price,
            "cost_price": cost_price,
            "stock_qty": stock_qty,
            "reorder_level": reorder_level,
            "unit": unit,
            "price_basis": sale_unit,
            "barcode": raw.get("barcode", ""),
            "sku": raw.get("sku", ""),
            "gst_rate": raw.get("gst_rate", ""),
            "hsn_sac": raw.get("hsn_sac", ""),
            "mrp": raw.get("mrp", 0),
            "tax_inclusive": tax_inclusive,
        }
    )
    normalized = validation.normalized

    unit_multiplier = _decimal_to_float(raw.get("unit_multiplier", 1), 1.0)
    if unit_multiplier <= 0:
        unit_multiplier = 1.0
    pack_size = _text(raw.get("pack_size"))
    unit_value = _decimal_to_float(pack_size, 1.0) if pack_size else 1.0
    pack_label = f"{pack_size}{unit}".strip() if pack_size else unit

    inventory_item = {
        "category": category,
        "brand": _text(raw.get("brand")),
        "base_product": base_product,
        "pack_size": pack_size,
        "bill_label": bill_label,
        "barcode": normalized.get("barcode", ""),
        "sku": normalized.get("sku", ""),
        "qty": _decimal_to_float(normalized.get("stock_qty")),
        "unit": unit,
        "sale_unit": sale_unit,
        "base_unit": base_unit,
        "unit_multiplier": unit_multiplier,
        "allow_decimal_qty": allow_decimal,
        "is_weighed": is_weighed,
        "min_stock": _decimal_to_float(normalized.get("reorder_level")),
        "cost": _decimal_to_float(normalized.get("cost_price")),
        "price": _decimal_to_float(normalized.get("sale_price")),
        "mrp": _decimal_to_float(normalized.get("mrp")),
        "gst_rate": _decimal_to_float(normalized.get("gst_rate")),
        "hsn_sac": normalized.get("hsn_sac", ""),
        "price_includes_tax": tax_inclusive,
    }

    catalog_payload = {
        "brand_name": inventory_item["brand"] or "Generic",
        "category_name": category,
        "product_name": base_product,
        "base_name": base_product,
        "variants": [
            {
                "variant_name": name,
                "unit_value": unit_value,
                "unit_type": unit,
                "pack_label": pack_label,
                "bill_label": bill_label,
                "sku": inventory_item["sku"],
                "barcode": inventory_item["barcode"],
                "sale_price": inventory_item["price"],
                "cost_price": inventory_item["cost"],
                "stock_qty": inventory_item["qty"],
                "reorder_level": inventory_item["min_stock"],
                "sale_unit": sale_unit,
                "base_unit": base_unit,
                "unit_multiplier": unit_multiplier,
                "allow_decimal_qty": int(allow_decimal),
                "mrp": inventory_item["mrp"],
                "gst_rate": inventory_item["gst_rate"],
                "hsn_sac": inventory_item["hsn_sac"],
                "price_includes_tax": int(tax_inclusive),
                "is_weighed": int(is_weighed),
            }
        ],
    }

    return ProductFormPayload(validation, inventory_item, catalog_payload)
