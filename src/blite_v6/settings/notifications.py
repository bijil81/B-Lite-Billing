from __future__ import annotations

from typing import Mapping


ALLOWED_POPUP_TIMES = {0, 3, 5, 10, 30}


def normalize_popup_time(value: object, default: int = 5) -> int:
    try:
        popup_time = int(str(value).strip())
    except Exception:
        return default
    return popup_time if popup_time in ALLOWED_POPUP_TIMES else default


def dismissed_count_label(dismissed: object) -> str:
    try:
        count = len(dismissed)  # type: ignore[arg-type]
    except Exception:
        count = 0
    return f"Dismissed: {count} item(s)"


def build_notifications_payload(
    current_settings: Mapping,
    *,
    birthday: bool,
    low_stock: bool,
    appointments: bool,
    popup_time: object,
) -> dict:
    cfg = dict(current_settings)
    cfg["notif_birthday"] = bool(birthday)
    cfg["notif_low_stock"] = bool(low_stock)
    cfg["notif_appointments"] = bool(appointments)
    cfg["notif_popup_time"] = normalize_popup_time(popup_time)
    return cfg


def reset_dismissed_payload(current_settings: Mapping) -> dict:
    cfg = dict(current_settings)
    cfg["notif_dismissed"] = []
    return cfg

