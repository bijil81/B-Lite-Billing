"""Redeem/coupon validators for v5 services."""

from __future__ import annotations

from validators.common_validators import require_non_negative, require_text


def validate_redeem_code_payload(payload: dict) -> dict:
    return {
        **payload,
        "code": require_text(payload.get("code"), "code").upper(),
        "customer_phone": str(payload.get("customer_phone", "") or "").strip(),
        "customer_name": str(payload.get("customer_name", "") or "").strip(),
        "discount_type": require_text(payload.get("discount_type", "flat"), "discount_type"),
        "discount_value": require_non_negative(payload.get("discount_value", 0.0), "discount_value"),
        "min_bill": require_non_negative(payload.get("min_bill", 0.0), "min_bill"),
        "active": bool(payload.get("active", True)),
        "used": bool(payload.get("used", False)),
        "used_invoice": str(payload.get("used_invoice", "") or "").strip(),
        "valid_until": str(payload.get("valid_until", "") or "").strip(),
    }

