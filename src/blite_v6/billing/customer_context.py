from __future__ import annotations

from datetime import date
from typing import Any, Mapping


BIRTHDAY_COUPON_MESSAGE = "Birthday Month! Apply BDAY25 coupon for 25% off"


def normalize_customer_identity(phone: str | None, name: str | None, birthday: str | None = "") -> dict[str, str]:
    return {
        "phone": (phone or "").strip(),
        "name": (name or "").strip(),
        "birthday": (birthday or "").strip(),
    }


def should_auto_save_customer(phone: str | None, name: str | None) -> bool:
    identity = normalize_customer_identity(phone, name)
    return (
        bool(phone)
        and bool(name)
        and identity["phone"] not in ("0000000000", "")
        and identity["name"] not in ("Guest", "")
    )


def build_v5_customer_payload(
    phone: str,
    name: str,
    birthday: str = "",
    existing: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    existing = existing or {}
    identity = normalize_customer_identity(phone, name, birthday)
    return {
        "phone": identity["phone"],
        "name": identity["name"],
        "birthday": identity["birthday"] or existing.get("birthday", ""),
        "vip": bool(existing.get("vip", 0)),
        "points_balance": int(existing.get("points_balance", 0) or 0),
    }


def is_valid_lookup_phone(phone: str | None) -> bool:
    clean_phone = (phone or "").strip()
    return bool(clean_phone) and clean_phone != "0000000000" and clean_phone.isdigit() and len(clean_phone) == 10


def build_phone_lookup_state(phone: str | None, customer: Mapping[str, Any] | None) -> dict[str, Any]:
    if not is_valid_lookup_phone(phone):
        return {
            "state": "empty",
            "customer_name": "",
            "birthday": "",
            "points": 0,
            "visits": 0,
            "points_text": "Points: -",
            "customer_status_text": "",
            "customer_status_color_key": "",
            "package_text": "",
        }

    if not customer:
        return {
            "state": "new",
            "customer_name": "",
            "birthday": "",
            "points": 0,
            "visits": 0,
            "points_text": "Points: -",
            "customer_status_text": "New Customer",
            "customer_status_color_key": "accent",
            "package_text": "",
        }

    points = int(customer.get("points", 0) or 0)
    visits = len(customer.get("visits", []) or [])
    return {
        "state": "existing",
        "customer_name": customer.get("name", ""),
        "birthday": customer.get("birthday", ""),
        "points": points,
        "visits": visits,
        "points_text": f"Points: {points}  |  Visits: {visits}",
        "customer_status_text": "Existing",
        "customer_status_color_key": "lime",
        "package_text": "",
    }


def format_membership_info(membership: Mapping[str, Any] | None) -> dict[str, Any]:
    if not membership or membership.get("status") != "Active":
        return {
            "active": False,
            "discount_pct": 0.0,
            "text": "",
            "font": ("Arial", 9, "bold"),
        }

    discount_pct = float(membership.get("discount_pct", 0) or 0)
    wallet = float(membership.get("wallet_balance", 0) or 0)
    package_name = membership.get("package_name", "Member")
    text = f"{package_name}"
    if discount_pct > 0:
        text += f" | {discount_pct:.0f}% off"
    if wallet > 0:
        text += f" | Wallet: Rs{wallet:.0f}"
    font = ("Arial", 9, "bold") if len(text) < 42 else ("Arial", 8, "bold")
    return {
        "active": True,
        "discount_pct": discount_pct,
        "text": text,
        "font": font,
    }


def is_birthday_month(birthday: str | None, today: date | None = None) -> bool:
    if not birthday:
        return False
    today = today or date.today()
    birthday_text = str(birthday)
    try:
        return birthday_text[5:7] == today.strftime("%m")
    except Exception:
        return False
