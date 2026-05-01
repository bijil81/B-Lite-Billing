from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

NOTIFICATION_COLOR = "#D4A017"
NOTIFICATION_HOVER_COLOR = "#C58F00"
REMINDER_STAGGER_MS = 100
REMINDER_INTERVAL_MS = 300_000


@dataclass(frozen=True)
class NotificationButtonView:
    text: str
    color: str = NOTIFICATION_COLOR
    hover_color: str = NOTIFICATION_HOVER_COLOR


def notification_button_view(count: int) -> NotificationButtonView:
    safe_count = max(0, int(count or 0))
    text = "Notifications" if safe_count == 0 else f"Notifications ({safe_count})"
    return NotificationButtonView(text=text)


def reminder_popup_schedule(appointments: Iterable[object]) -> list[tuple[int, object]]:
    return [(index * REMINDER_STAGGER_MS, appt) for index, appt in enumerate(appointments)]


def should_force_inventory_refresh(frames: dict, key: str = "inventory") -> bool:
    return frames.get(key) is not None


def today_refresh_allowed(force: bool, now_ts: float, last_ts: float, throttle_seconds: int = 30) -> bool:
    return bool(force or not last_ts or (now_ts - last_ts) >= throttle_seconds)


def admin_existing_panel_available(panel: object | None) -> bool:
    return panel is not None


def logout_username(current_user: dict | None) -> str:
    current_user = current_user or {}
    return str(current_user.get("username", "") or "")
