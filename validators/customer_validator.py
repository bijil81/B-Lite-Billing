"""Customer validators for v5 services."""

from __future__ import annotations

from utils import validate_phone
from validators.common_validators import require_text


def validate_customer_payload(payload: dict) -> dict:
    phone = require_text(payload.get("phone"), "phone")
    if not validate_phone(phone):
        raise ValueError("phone must be a valid 10-digit number")
    # Use sentinel None for credit_limit / is_blacklisted so that callers
    # that don't supply these fields (e.g. auto_save_customer during billing)
    # do NOT accidentally overwrite the stored values in the DB.
    raw_limit = payload.get("credit_limit", None)
    clean_limit = float(raw_limit) if raw_limit is not None else None
    raw_bl = payload.get("is_blacklisted", None)
    clean_bl = bool(raw_bl) if raw_bl is not None else None
    return {
        **payload,
        "phone": phone,
        "name": require_text(payload.get("name"), "name"),
        "birthday": str(payload.get("birthday", "") or "").strip(),
        "vip": bool(payload.get("vip", False)),
        "points_balance": int(payload.get("points_balance", 0) or 0),
        "credit_limit": clean_limit,
        "is_blacklisted": clean_bl,
    }
