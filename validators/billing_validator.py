"""Billing-specific validators for transactional cutover."""

from __future__ import annotations

from validators.common_validators import require_non_negative, require_text


def validate_invoice_payload(payload: dict) -> dict:
    items = payload.get("items", []) or []
    payments = payload.get("payments", []) or []
    if not items:
        raise ValueError("At least one invoice item is required")
    if not payments:
        raise ValueError("At least one payment row is required")

    validated = {
        **payload,
        "invoice_no": require_text(payload.get("invoice_no"), "invoice_no"),
        "invoice_date": require_text(payload.get("invoice_date"), "invoice_date"),
        "gross_total": require_non_negative(payload.get("gross_total", 0.0), "gross_total"),
        "discount_total": require_non_negative(payload.get("discount_total", 0.0), "discount_total"),
        "tax_total": require_non_negative(payload.get("tax_total", 0.0), "tax_total"),
        "net_total": require_non_negative(payload.get("net_total", 0.0), "net_total"),
        "items": items,
        "payments": payments,
    }

    for idx, item in enumerate(items, start=1):
        qty = require_non_negative(item.get("qty", 1.0), f"items[{idx}].qty")
        unit_price = require_non_negative(item.get("unit_price", item.get("price", 0.0)), f"items[{idx}].unit_price")
        line_total = require_non_negative(item.get("line_total", item.get("total", 0.0)), f"items[{idx}].line_total")
        expected_line_total = round(float(qty) * float(unit_price), 2)
        if abs(float(line_total) - expected_line_total) > 0.01:
            raise ValueError(f"items[{idx}].line_total mismatch")

    payment_total = 0.0
    for idx, payment in enumerate(payments, start=1):
        amount = require_non_negative(payment.get("amount", 0.0), f"payments[{idx}].amount")
        payment_total += float(amount)

    gross_total = float(validated["gross_total"])
    discount_total = float(validated["discount_total"])
    tax_total = float(validated["tax_total"])
    net_total = float(validated["net_total"])
    expected_net_total = round(gross_total - discount_total + tax_total, 2)

    if abs(expected_net_total - net_total) > 0.01:
        raise ValueError("net_total mismatch with gross/discount/tax")
    if abs(round(payment_total, 2) - net_total) > 0.01:
        raise ValueError("payment total mismatch with net_total")

    return validated
