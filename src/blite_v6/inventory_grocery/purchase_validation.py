"""Pure validation helpers for vendor purchases."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Mapping

from .product_units import decimal_from_value, normalize_unit


TWOPLACES = Decimal("0.01")


@dataclass(frozen=True)
class PurchaseTotals:
    gross_total: float
    tax_total: float
    net_total: float


def money(value: Decimal) -> float:
    return float(value.quantize(TWOPLACES, rounding=ROUND_HALF_UP))


def normalize_gstin(value: object) -> str:
    text = str(value or "").strip().upper()
    if not text:
        return ""
    if len(text) != 15 or not text.isalnum():
        raise ValueError("gstin must be a 15-character alphanumeric value")
    return text


def _non_negative(value: object, field: str, *, default: str = "0") -> Decimal:
    amount = decimal_from_value(value if value not in (None, "") else default, field=field)
    if amount < 0:
        raise ValueError(f"{field} cannot be negative")
    return amount


def validate_vendor_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    name = str(payload.get("name") or payload.get("vendor_name") or "").strip()
    if not name:
        raise ValueError("vendor name is required")
    return {
        "name": name,
        "phone": str(payload.get("phone") or "").strip(),
        "gstin": normalize_gstin(payload.get("gstin")),
        "address": str(payload.get("address") or "").strip(),
        "opening_balance": money(_non_negative(payload.get("opening_balance"), "opening_balance")),
        "active": bool(payload.get("active", True)),
    }


def validate_purchase_item(item: Mapping[str, Any], index: int = 1) -> dict[str, Any]:
    item_name = str(item.get("item_name") or item.get("name") or "").strip()
    if not item_name:
        raise ValueError(f"items[{index}].item_name is required")
    qty = _non_negative(item.get("qty"), f"items[{index}].qty")
    if qty <= 0:
        raise ValueError(f"items[{index}].qty must be greater than zero")
    cost_price = _non_negative(
        item.get("cost_price", item.get("unit_cost")),
        f"items[{index}].cost_price",
    )
    sale_price = _non_negative(item.get("sale_price"), f"items[{index}].sale_price")
    mrp = _non_negative(item.get("mrp"), f"items[{index}].mrp")
    gst_rate = _non_negative(item.get("gst_rate"), f"items[{index}].gst_rate")
    if gst_rate > 100:
        raise ValueError(f"items[{index}].gst_rate must be between 0 and 100")

    line_gross = qty * cost_price
    line_tax = line_gross * gst_rate / Decimal("100")
    return {
        "variant_id": int(item.get("variant_id") or 0),
        "item_name": item_name,
        "qty": float(qty),
        "unit": normalize_unit(item.get("unit") or "pcs"),
        "cost_price": money(cost_price),
        "sale_price": money(sale_price),
        "mrp": money(mrp),
        "gst_rate": money(gst_rate),
        "hsn_sac": str(item.get("hsn_sac") or "").strip(),
        "batch_no": str(item.get("batch_no") or "").strip(),
        "expiry_date": str(item.get("expiry_date") or "").strip(),
        "line_gross": money(line_gross),
        "line_tax": money(line_tax),
        "line_net": money(line_gross + line_tax),
    }


def calculate_purchase_totals(items: list[Mapping[str, Any]]) -> PurchaseTotals:
    gross = sum(Decimal(str(item.get("line_gross", 0))) for item in items)
    tax = sum(Decimal(str(item.get("line_tax", 0))) for item in items)
    return PurchaseTotals(
        gross_total=money(gross),
        tax_total=money(tax),
        net_total=money(gross + tax),
    )


def validate_purchase_invoice_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    vendor_id = int(payload.get("vendor_id") or 0)
    vendor_source = payload.get("vendor") or payload
    vendor_name = str(
        vendor_source.get("name")
        or vendor_source.get("vendor_name")
        or payload.get("vendor_name")
        or ""
    ).strip()
    if vendor_id and not vendor_name:
        vendor = {
            "name": "",
            "phone": "",
            "gstin": "",
            "address": "",
            "opening_balance": 0.0,
            "active": True,
        }
    else:
        vendor = validate_vendor_payload(vendor_source)
    invoice_date = str(payload.get("invoice_date") or payload.get("date") or "").strip()
    if not invoice_date:
        raise ValueError("invoice_date is required")
    invoice_no = str(
        payload.get("invoice_no")
        or payload.get("purchase_invoice_no")
        or payload.get("bill_no")
        or ""
    ).strip()
    raw_items = list(payload.get("items") or [])
    if not raw_items:
        raise ValueError("at least one purchase item is required")
    items = [validate_purchase_item(item, idx) for idx, item in enumerate(raw_items, start=1)]
    totals = calculate_purchase_totals(items)
    return {
        "vendor": vendor,
        "vendor_id": vendor_id,
        "invoice_no": invoice_no,
        "invoice_date": invoice_date,
        "gross_total": totals.gross_total,
        "tax_total": totals.tax_total,
        "net_total": totals.net_total,
        "notes": str(payload.get("notes") or "").strip(),
        "items": items,
    }
