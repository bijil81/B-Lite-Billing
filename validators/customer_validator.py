"""Customer validators for v5 services."""

from __future__ import annotations

from utils import validate_phone
from validators.common_validators import require_text


def validate_customer_payload(payload: dict) -> dict:
    phone = require_text(payload.get("phone"), "phone")
    if not validate_phone(phone):
        raise ValueError("phone must be a valid 10-digit number")
    return {
        **payload,
        "phone": phone,
        "name": require_text(payload.get("name"), "name"),
        "birthday": str(payload.get("birthday", "") or "").strip(),
        "vip": bool(payload.get("vip", False)),
        "points_balance": int(payload.get("points_balance", 0) or 0),
    }
