from __future__ import annotations

import re
from typing import Any, Mapping, MutableSequence


_QUANTITY_PATTERN = re.compile(r"^\s*(?P<value>(?:\d+(?:\.\d*)?|\.\d+))\s*(?P<unit>[a-zA-Z]*)\s*$")


def _safe_quantity(value: Any, default: float = 1.0) -> float:
    try:
        qty = float(value)
    except Exception:
        return default
    if qty <= 0:
        return default
    return qty


def normalise_quantity_unit(unit: str | None) -> str:
    clean = (unit or "pcs").strip().lower()
    aliases = {
        "": "pcs",
        "pc": "pcs",
        "piece": "pcs",
        "pieces": "pcs",
        "nos": "pcs",
        "no": "pcs",
        "kg": "kg",
        "kilogram": "kg",
        "kilograms": "kg",
        "kgs": "kg",
        "g": "g",
        "gm": "g",
        "gram": "g",
        "grams": "g",
        "l": "l",
        "ltr": "l",
        "liter": "l",
        "litre": "l",
        "liters": "l",
        "litres": "l",
        "ml": "ml",
        "milliliter": "ml",
        "millilitre": "ml",
        "milliliters": "ml",
        "millilitres": "ml",
    }
    return aliases.get(clean, clean)


def display_quantity_unit(unit: str | None) -> str:
    clean = normalise_quantity_unit(unit)
    return "L" if clean == "l" else clean


def unit_type_for_variant(selected_variant: Mapping[str, Any] | None) -> str:
    if not selected_variant:
        return "pcs"
    return normalise_quantity_unit(
        selected_variant.get("unit_type")
        or selected_variant.get("unit")
        or selected_variant.get("pack_unit")
        or "pcs"
    )


def parse_cart_quantity(raw_quantity: str | None, unit_type: str | None = "pcs") -> float:
    text = (raw_quantity or "").strip().replace(",", "")
    if not text:
        return 1.0

    match = _QUANTITY_PATTERN.match(text)
    if not match:
        return 1.0

    value = _safe_quantity(match.group("value"))
    base_unit = normalise_quantity_unit(unit_type)
    entered_unit = normalise_quantity_unit(match.group("unit"))
    if not match.group("unit") or entered_unit == base_unit:
        return value

    mass_to_kg = {"kg": 1.0, "g": 0.001}
    volume_to_l = {"l": 1.0, "ml": 0.001}
    if base_unit in mass_to_kg and entered_unit in mass_to_kg:
        return value * mass_to_kg[entered_unit] / mass_to_kg[base_unit]
    if base_unit in volume_to_l and entered_unit in volume_to_l:
        return value * volume_to_l[entered_unit] / volume_to_l[base_unit]
    return value


def format_quantity(qty: Any) -> str:
    value = _safe_quantity(qty)
    if value.is_integer():
        return str(int(value))
    return f"{value:.3f}".rstrip("0").rstrip(".")


def format_cart_quantity_label(item: Mapping[str, Any]) -> str:
    qty_text = format_quantity(item.get("qty", 1))
    unit = normalise_quantity_unit(item.get("unit_type") or item.get("unit"))
    if unit and unit != "pcs":
        return f"{qty_text} {display_quantity_unit(unit)}"
    return qty_text


def should_refresh_inventory_cache(cache: object | None, now: float, last_refresh: float, ttl_seconds: float = 30.0) -> bool:
    return cache is None or (now - last_refresh) > ttl_seconds


def product_inventory_name(selected_variant: Mapping[str, Any] | None, fallback_name: str) -> str:
    if selected_variant:
        return selected_variant.get("display_name", fallback_name)
    return fallback_name


def available_stock_for_variant(
    inventory_row: Mapping[str, Any],
    selected_variant: Mapping[str, Any],
) -> float:
    return float(inventory_row.get("qty", selected_variant.get("stock_qty", 0.0)) or 0.0)


def existing_product_quantity_for_inventory_name(
    bill_items: list[Mapping[str, Any]],
    inventory_name: str,
) -> float:
    existing_qty = 0.0
    clean_inventory_name = inventory_name.strip().lower()
    for item in bill_items:
        if item.get("mode") != "products":
            continue
        item_inventory_name = item.get("inventory_item_name", item.get("name", ""))
        if item_inventory_name.strip().lower() == clean_inventory_name:
            existing_qty += _safe_quantity(item.get("qty", 0), default=0.0)
    return existing_qty


def validate_variant_stock(
    *,
    bill_items: list[Mapping[str, Any]],
    selected_variant: Mapping[str, Any] | None,
    inventory_lookup: Mapping[str, Mapping[str, Any]],
    item_name: str,
    requested_qty: float,
) -> dict[str, Any]:
    if not selected_variant:
        return {"ok": True, "message": ""}

    inventory_name = product_inventory_name(selected_variant, item_name)
    inventory_row = inventory_lookup.get(inventory_name, {})
    available_stock = available_stock_for_variant(inventory_row, selected_variant)
    existing_qty = existing_product_quantity_for_inventory_name(bill_items, inventory_name)
    total_qty = existing_qty + requested_qty

    if available_stock <= 0:
        return {"ok": False, "message": "No stock available"}
    if total_qty > available_stock:
        display_qty = format_quantity(available_stock)
        display_unit = display_quantity_unit(unit_type_for_variant(selected_variant))
        suffix = " items" if display_unit == "pcs" else f" {display_unit}"
        return {"ok": False, "message": f"Only {display_qty}{suffix} left in stock"}
    return {"ok": True, "message": ""}


def build_cart_item(
    *,
    mode: str,
    name: str,
    price: float,
    qty: float,
    selected_variant: Mapping[str, Any] | None = None,
    selected_category: str | None = None,
) -> dict[str, Any]:
    item = {"mode": mode, "name": name, "price": float(price), "qty": qty}
    if mode == "products" and selected_variant:
        item["variant_id"] = selected_variant.get("id")
        item["inventory_item_name"] = selected_variant.get("display_name", name)
        item_category = (
            selected_variant.get("category")
            or selected_variant.get("category_name")
            or selected_category
        )
        if item_category:
            item["category"] = item_category
            item["category_name"] = item_category
        item["unit_type"] = unit_type_for_variant(selected_variant)
        for key in (
            "unit_value",
            "pack_label",
            "bill_label",
            "sale_unit",
            "base_unit",
            "unit_multiplier",
            "allow_decimal_qty",
            "is_weighed",
            "cost_price",
            "gst_rate",
            "hsn_sac",
            "price_includes_tax",
        ):
            if selected_variant.get(key) is not None:
                item[key] = selected_variant.get(key)
    elif mode == "products" and selected_category:
        item["category"] = selected_category
        item["category_name"] = selected_category
    return item


def _same_product_variant(
    item: Mapping[str, Any],
    selected_variant: Mapping[str, Any] | None,
    fallback_name: str,
) -> bool:
    if not selected_variant:
        return True
    existing_variant_id = item.get("variant_id")
    new_variant_id = selected_variant.get("id")
    if existing_variant_id is not None and new_variant_id is not None and existing_variant_id != new_variant_id:
        return False

    existing_name = item.get("inventory_item_name")
    new_name = selected_variant.get("display_name", fallback_name)
    if existing_name and new_name and str(existing_name).strip().lower() != str(new_name).strip().lower():
        return False

    existing_unit = normalise_quantity_unit(item.get("unit_type") or item.get("unit"))
    new_unit = unit_type_for_variant(selected_variant)
    return existing_unit == new_unit or existing_unit == "pcs"


def add_or_merge_cart_item(
    bill_items: MutableSequence[dict[str, Any]],
    *,
    mode: str,
    name: str,
    price: float,
    qty: float,
    selected_variant: Mapping[str, Any] | None = None,
    selected_category: str | None = None,
) -> dict[str, Any]:
    for item in bill_items:
        if (
            item["mode"] == mode
            and item["name"].lower() == name.lower()
            and abs(item["price"] - price) < 0.001
            and (mode != "products" or _same_product_variant(item, selected_variant, name))
        ):
            item["qty"] += qty
            if mode == "products" and selected_variant:
                item.setdefault("variant_id", selected_variant.get("id"))
                item.setdefault("inventory_item_name", selected_variant.get("display_name", name))
                item_category = (
                    selected_variant.get("category")
                    or selected_variant.get("category_name")
                    or selected_category
                )
                if item_category:
                    item.setdefault("category", item_category)
                    item.setdefault("category_name", item_category)
                item.setdefault("unit_type", unit_type_for_variant(selected_variant))
                for key in (
                    "unit_value",
                    "pack_label",
                    "bill_label",
                    "sale_unit",
                    "base_unit",
                    "unit_multiplier",
                    "allow_decimal_qty",
                    "is_weighed",
                    "cost_price",
                    "gst_rate",
                    "hsn_sac",
                    "price_includes_tax",
                ):
                    if selected_variant.get(key) is not None:
                        item.setdefault(key, selected_variant.get(key))
            return {"action": "merged", "item": item}

    item = build_cart_item(
        mode=mode,
        name=name,
        price=price,
        qty=qty,
        selected_variant=selected_variant,
        selected_category=selected_category,
    )
    bill_items.append(item)
    return {"action": "added", "item": item}


def update_item_quantity(bill_items: MutableSequence[dict[str, Any]], index: int, new_qty: float | None) -> bool:
    qty = _safe_quantity(new_qty, default=0.0)
    if qty > 0:
        bill_items[index]["qty"] = qty
        return True
    return False


def update_item_price(bill_items: MutableSequence[dict[str, Any]], index: int, new_price: float | None) -> bool:
    if new_price is not None:
        bill_items[index]["price"] = new_price
        return True
    return False


def remove_item_at(bill_items: MutableSequence[dict[str, Any]], index: int) -> dict[str, Any]:
    return bill_items.pop(index)


def undo_last_item(bill_items: MutableSequence[dict[str, Any]]) -> bool:
    if not bill_items:
        return False
    last = bill_items[-1]
    qty = _safe_quantity(last.get("qty"), default=0.0)
    unit = normalise_quantity_unit(last.get("unit_type") or last.get("unit"))
    if unit == "pcs" and qty > 1 and qty.is_integer():
        last["qty"] -= 1
    else:
        bill_items.pop()
    return True
