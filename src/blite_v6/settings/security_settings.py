from __future__ import annotations

from typing import Mapping


def current_username(current_user: object, default: str = "admin") -> str:
    try:
        getter = getattr(current_user, "get")
        username = getter("username", default)
    except Exception:
        username = default
    return str(username or default).strip().lower() or default


def password_visibility_show_value(show_passwords: bool) -> str:
    return "" if show_passwords else "*"


def validate_new_password(new_password: str, confirm_password: str) -> tuple[bool, str]:
    new_value = str(new_password).strip()
    confirm_value = str(confirm_password).strip()
    if len(new_value) < 8:
        return False, "Min 8 characters required."
    if new_value != confirm_value:
        return False, "Passwords do not match."
    return True, ""


def normalize_session_timeout_minutes(value: object, default: int = 30) -> int:
    try:
        minutes = int(str(value).strip())
    except Exception:
        return default
    if minutes <= 0:
        return default
    return minutes


def build_security_payload(
    current_settings: Mapping,
    *,
    auto_logout: bool,
    require_pw_bill: bool,
    session_timeout_minutes: object | None = None,
) -> dict:
    cfg = dict(current_settings)
    cfg["auto_logout"] = bool(auto_logout)
    cfg["require_pw_bill"] = bool(require_pw_bill)
    if session_timeout_minutes is not None:
        cfg["session_timeout_minutes"] = normalize_session_timeout_minutes(session_timeout_minutes)
    return cfg

