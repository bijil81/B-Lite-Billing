"""Bridge inventory-created products into the billing product picker.

Inventory is still the stable product master for V6 source mode.  The v5
variant tables are optional during rollout, so billing must also see active
inventory rows even when the SQLite product-variant switch is off.
"""
from __future__ import annotations

import hashlib
from collections.abc import Iterable as IterableABC
from typing import Any, Iterable, Mapping

from utils import F_INVENTORY, load_json


def _text(value: object, default: str = "") -> str:
    text = str(value if value is not None else "").strip()
    return text or default


def _float(value: object, default: float = 0.0) -> float:
    try:
        return float(value if value not in (None, "") else default)
    except Exception:
        return default


def _bool(value: object, default: bool = False) -> bool:
    if value in (None, ""):
        return default
    if isinstance(value, str):
        return value.strip().lower() in {"1", "yes", "true", "on", "y"}
    return bool(value)


def _first_value(row: Mapping[str, Any], *keys: str, default: object = None) -> object:
    for key in keys:
        if key in row and row.get(key) not in (None, ""):
            return row.get(key)
    return default


def _first_text(row: Mapping[str, Any], *keys: str, default: str = "") -> str:
    return _text(_first_value(row, *keys, default=default), default)


def _stable_inventory_code(name: str, category: str, barcode: str = "") -> str:
    seed = f"{category}|{name}|{barcode}".encode("utf-8", errors="ignore")
    return "INV" + hashlib.sha1(seed).hexdigest()[:10].upper()


def _is_active_inventory_row(row: Mapping[str, Any]) -> bool:
    if _bool(row.get("deleted")) or _bool(row.get("is_deleted")):
        return False
    if "active" in row and not _bool(row.get("active"), True):
        return False
    return True


def _iter_inventory_source_rows(inventory: object) -> Iterable[tuple[str, Mapping[str, Any]]]:
    if isinstance(inventory, Mapping):
        for nested_key in ("items", "products", "inventory"):
            nested = inventory.get(nested_key)
            if isinstance(nested, IterableABC) and not isinstance(nested, (str, bytes, Mapping)):
                yield from _iter_inventory_source_rows(nested)

        for legacy_name, raw_row in inventory.items():
            if isinstance(raw_row, Mapping):
                yield _text(legacy_name), raw_row
        return

    if isinstance(inventory, IterableABC) and not isinstance(inventory, (str, bytes)):
        for raw_row in inventory:
            if isinstance(raw_row, Mapping):
                legacy_name = _first_text(
                    raw_row,
                    "legacy_name",
                    "inventory_item_name",
                    "name",
                    "item_name",
                    "product_name",
                    "Item Name",
                )
                yield legacy_name, raw_row


def iter_inventory_billing_rows_from_inventory(
    inventory: object,
) -> Iterable[dict[str, Any]]:
    for legacy_name, raw_row in _iter_inventory_source_rows(inventory):
        if not _is_active_inventory_row(raw_row):
            continue

        display_name = (
            _first_text(raw_row, "bill_label", "display_name", "item_name", "name", "Item Name")
            or _text(legacy_name)
        )
        if not display_name:
            continue

        raw_category = _first_text(raw_row, "category", "category_name", "Category")
        category = raw_category or "General"
        barcode = _first_text(raw_row, "barcode", "Barcode")
        sku = _first_text(raw_row, "sku", "SKU")
        code = sku or barcode or _stable_inventory_code(display_name, category, barcode)
        unit = _first_text(raw_row, "unit", "unit_type", "Unit (Measurement)", "Unit", default="pcs")
        pack_size = _first_text(raw_row, "pack_size", "unit_value", "Pack Size Value (Optional)")
        unit_value = _float(pack_size, 1.0) if pack_size else 1.0
        sale_price = _float(
            _first_value(
                raw_row,
                "price",
                "sale_price",
                "selling_price",
                "sell_price",
                "Sale Price (Rs)",
                "cost",
                "cost_price",
                default=0.0,
            )
        )

        yield {
            "code": code,
            "display_name": display_name,
            "product_name": _first_text(raw_row, "base_product", "product_name", default=display_name),
            "category_name": category,
            "category_was_default": not bool(raw_category),
            "sale_price": sale_price,
            "barcode": barcode,
            "sku": sku,
            "bill_label": display_name,
            "unit_type": unit,
            "unit_value": unit_value,
            "pack_label": pack_size or unit,
            "stock_qty": _float(_first_value(raw_row, "qty", "stock_qty", "quantity", "Quantity", default=0.0)),
            "reorder_level": _float(_first_value(raw_row, "min_stock", "reorder_level", "min_qty", "Min Stock Alert", default=0.0)),
            "cost_price": _float(_first_value(raw_row, "cost", "cost_price", "Cost per Unit (Rs)", default=0.0)),
            "sale_unit": _first_text(raw_row, "sale_unit", "price_basis", "Sale Unit / Price Basis", default=unit),
            "base_unit": _first_text(raw_row, "base_unit", "Base Unit", default=unit),
            "unit_multiplier": _float(_first_value(raw_row, "unit_multiplier", default=1.0), 1.0),
            "allow_decimal_qty": _bool(_first_value(raw_row, "allow_decimal_qty", "allow_decimal", "decimal_qty")),
            "is_weighed": _bool(_first_value(raw_row, "is_weighed", "weighed", "loose_item")),
            "gst_rate": _float(_first_value(raw_row, "gst_rate", "GST Rate %", default=0.0)),
            "hsn_sac": _first_text(raw_row, "hsn_sac", "HSN/SAC (Optional)"),
            "price_includes_tax": _bool(_first_value(raw_row, "price_includes_tax", "tax_inclusive", default=True), True),
            "inventory_item_name": _text(legacy_name),
        }


def iter_inventory_billing_rows(
    inventory: object | None = None,
) -> Iterable[dict[str, Any]]:
    if inventory is None:
        inventory = load_json(F_INVENTORY, {})
    yield from iter_inventory_billing_rows_from_inventory(inventory)


def _iter_rows(inventory: object | None) -> Iterable[dict[str, Any]]:
    if inventory is None:
        return iter_inventory_billing_rows()
    return iter_inventory_billing_rows(inventory)


def inventory_product_categories(inventory: object | None = None) -> set[str]:
    return {
        row["category_name"]
        for row in _iter_rows(inventory)
        if _text(row.get("category_name"))
    }


def merge_inventory_products(
    product_map: Mapping[str, Any],
    inventory: object | None = None,
) -> dict[str, dict[str, float]]:
    merged: dict[str, dict[str, float]] = {
        str(cat): dict(items or {})
        for cat, items in dict(product_map or {}).items()
        if isinstance(items, Mapping)
    }
    for row in _iter_rows(inventory):
        category = row["category_name"]
        name = row["display_name"]
        bucket = merged.setdefault(category, {})
        bucket.setdefault(name, float(row["sale_price"] or 0.0))
    return merged


def append_inventory_product_matches(
    matches: list[tuple],
    variant_meta: dict[str, dict],
    seen_keys: set[tuple[str, str]],
    *,
    query: str = "",
    category: str = "All",
    existing_codes: set[str] | None = None,
    inventory: object | None = None,
) -> None:
    q = query.strip().lower()
    codes = {str(code).lower() for code in (existing_codes or set())}
    seen_names = {name for name, _cat in seen_keys}
    for row in _iter_rows(inventory):
        cat = row["category_name"]
        name = row["display_name"]
        code = row["code"]
        barcode = row["barcode"]
        if category != "All" and cat != category:
            continue
        if q and q not in code.lower() and q not in name.lower() and q not in cat.lower() and q not in barcode.lower():
            continue
        key = (name.lower(), cat.lower())
        if key in seen_keys or (row.get("category_was_default") and name.lower() in seen_names):
            continue
        final_code = code
        if final_code.lower() in codes:
            final_code = _stable_inventory_code(name, cat, barcode)
        matches.append((final_code, name, cat, float(row["sale_price"] or 0.0)))
        variant_meta[final_code] = dict(row)
        seen_keys.add(key)
        seen_names.add(name.lower())
        codes.add(final_code.lower())
