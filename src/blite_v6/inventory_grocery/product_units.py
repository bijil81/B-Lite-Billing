"""Pure unit and quantity helpers for retail/grocery products."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import re


SUPPORTED_UNITS = ("pcs", "kg", "g", "L", "ml", "meter", "custom")

_UNIT_ALIASES = {
    "": "",
    "pc": "pcs",
    "pcs": "pcs",
    "piece": "pcs",
    "pieces": "pcs",
    "kg": "kg",
    "kilogram": "kg",
    "kilograms": "kg",
    "g": "g",
    "gm": "g",
    "gram": "g",
    "grams": "g",
    "l": "L",
    "ltr": "L",
    "liter": "L",
    "litre": "L",
    "liters": "L",
    "litres": "L",
    "ml": "ml",
    "milliliter": "ml",
    "millilitre": "ml",
    "milliliters": "ml",
    "millilitres": "ml",
    "m": "meter",
    "meter": "meter",
    "metre": "meter",
    "meters": "meter",
    "metres": "meter",
    "custom": "custom",
}

_QUANTITY_RE = re.compile(
    r"^\s*(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>[A-Za-z]+)?\s*$"
)


@dataclass(frozen=True)
class ParsedQuantity:
    original: str
    quantity: Decimal
    entered_unit: str
    basis_unit: str


def normalize_unit(unit: str | None) -> str:
    key = str(unit or "").strip().lower()
    normalized = _UNIT_ALIASES.get(key)
    if normalized is None:
        return "custom"
    return normalized


def is_supported_unit(unit: str | None) -> bool:
    return normalize_unit(unit) in SUPPORTED_UNITS


def decimal_from_value(value: object, *, field: str = "value") -> Decimal:
    text = str(value if value is not None else "").strip().replace(",", "")
    if not text:
        raise ValueError(f"{field} is required")
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field} must be a valid number") from exc


def convert_quantity(value: Decimal | int | float | str, from_unit: str, to_unit: str) -> Decimal:
    qty = value if isinstance(value, Decimal) else decimal_from_value(value)
    source = normalize_unit(from_unit)
    target = normalize_unit(to_unit)
    if qty < 0:
        raise ValueError("quantity cannot be negative")
    if source == target or not source:
        return qty
    if source == "g" and target == "kg":
        return qty / Decimal("1000")
    if source == "kg" and target == "g":
        return qty * Decimal("1000")
    if source == "ml" and target == "L":
        return qty / Decimal("1000")
    if source == "L" and target == "ml":
        return qty * Decimal("1000")
    raise ValueError(f"cannot convert {source or 'unknown'} to {target}")


def parse_quantity_input(raw_quantity: str | None, *, price_basis: str = "pcs") -> ParsedQuantity:
    text = str(raw_quantity or "").strip().replace(",", "")
    match = _QUANTITY_RE.match(text)
    if not match:
        raise ValueError("quantity must be a positive number with an optional unit")
    basis = normalize_unit(price_basis) or "pcs"
    entered_unit = normalize_unit(match.group("unit") or basis)
    quantity = decimal_from_value(match.group("value"), field="quantity")
    if quantity <= 0:
        raise ValueError("quantity must be greater than zero")
    converted = convert_quantity(quantity, entered_unit, basis)
    return ParsedQuantity(
        original=text,
        quantity=converted,
        entered_unit=entered_unit,
        basis_unit=basis,
    )


def quantity_to_display(quantity: Decimal, unit: str) -> str:
    normalized = normalize_unit(unit)
    text = format(quantity.normalize(), "f").rstrip("0").rstrip(".")
    if not text:
        text = "0"
    return f"{text} {normalized}" if normalized and normalized != "pcs" else text
