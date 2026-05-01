"""Pure product validation helpers for retail/grocery inventory."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping

from .product_units import decimal_from_value, normalize_unit


@dataclass(frozen=True)
class ValidationIssue:
    field: str
    message: str


@dataclass(frozen=True)
class ProductValidationResult:
    ok: bool
    normalized: dict[str, Any]
    errors: tuple[ValidationIssue, ...] = ()
    warnings: tuple[ValidationIssue, ...] = ()


def normalize_barcode(value: object) -> str:
    return str(value or "").strip()


def normalize_sku(value: object) -> str:
    return str(value or "").strip().upper()


def validate_gst_rate(value: object, *, required: bool = False) -> Decimal | None:
    text = str(value if value is not None else "").strip()
    if not text:
        if required:
            raise ValueError("gst_rate is required")
        return None
    rate = decimal_from_value(text, field="gst_rate")
    if rate < 0 or rate > 100:
        raise ValueError("gst_rate must be between 0 and 100")
    return rate


def validate_non_negative_decimal(value: object, field: str, *, default: str = "0") -> Decimal:
    raw = value if value not in (None, "") else default
    amount = decimal_from_value(raw, field=field)
    if amount < 0:
        raise ValueError(f"{field} cannot be negative")
    return amount


def below_cost_warning(sale_price: Decimal, cost_price: Decimal) -> ValidationIssue | None:
    if cost_price > 0 and sale_price < cost_price:
        return ValidationIssue(
            "sale_price",
            "Sale price is below cost price; require explicit continue before saving/selling.",
        )
    return None


def validate_product_payload(payload: Mapping[str, Any]) -> ProductValidationResult:
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []
    normalized: dict[str, Any] = {
        "name": str(payload.get("name") or payload.get("product_name") or "").strip(),
        "category": str(payload.get("category") or "").strip(),
        "brand": str(payload.get("brand") or "").strip(),
        "barcode": normalize_barcode(payload.get("barcode")),
        "sku": normalize_sku(payload.get("sku")),
        "unit": normalize_unit(payload.get("unit") or payload.get("unit_type") or "pcs"),
        "price_basis": normalize_unit(payload.get("price_basis") or payload.get("unit") or "pcs"),
        "hsn_sac": str(payload.get("hsn_sac") or "").strip(),
        "tax_inclusive": bool(payload.get("tax_inclusive", True)),
    }

    if not normalized["name"]:
        errors.append(ValidationIssue("name", "Product name is required"))
    if not normalized["category"]:
        errors.append(ValidationIssue("category", "Category is required"))

    for field in ("sale_price", "cost_price", "stock_qty", "reorder_level", "mrp"):
        try:
            normalized[field] = validate_non_negative_decimal(payload.get(field), field)
        except ValueError as exc:
            errors.append(ValidationIssue(field, str(exc)))

    try:
        normalized["gst_rate"] = validate_gst_rate(payload.get("gst_rate"))
    except ValueError as exc:
        errors.append(ValidationIssue("gst_rate", str(exc)))

    sale_price = normalized.get("sale_price")
    cost_price = normalized.get("cost_price")
    if isinstance(sale_price, Decimal) and isinstance(cost_price, Decimal):
        warning = below_cost_warning(sale_price, cost_price)
        if warning:
            warnings.append(warning)

    return ProductValidationResult(
        ok=not errors,
        normalized=normalized,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
