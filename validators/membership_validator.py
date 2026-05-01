"""Membership validators for v5 services."""

from __future__ import annotations

from validators.common_validators import require_non_negative, require_text


def validate_membership_payload(payload: dict) -> dict:
    start_date = str(payload.get("start_date", "") or "").strip()
    expiry_date = str(payload.get("expiry_date", "") or "").strip()
    if start_date and expiry_date and expiry_date < start_date:
        raise ValueError("expiry_date cannot be earlier than start_date")
    return {
        **payload,
        "customer_phone": require_text(payload.get("customer_phone"), "customer_phone"),
        "plan_name": require_text(payload.get("plan_name"), "plan_name"),
        "customer_name": str(payload.get("customer_name", "") or "").strip(),
        "discount_pct": require_non_negative(payload.get("discount_pct", 0.0), "discount_pct"),
        "wallet_balance": require_non_negative(payload.get("wallet_balance", 0.0), "wallet_balance"),
        "start_date": start_date,
        "expiry_date": expiry_date,
        "status": str(payload.get("status", "Active") or "Active").strip() or "Active",
        "price_paid": require_non_negative(payload.get("price_paid", 0.0), "price_paid"),
        "payment_method": str(payload.get("payment_method", "") or "").strip(),
    }

