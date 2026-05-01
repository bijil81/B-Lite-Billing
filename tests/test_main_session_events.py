from __future__ import annotations

from src.blite_v6.app.app_events import (
    NOTIFICATION_COLOR,
    NOTIFICATION_HOVER_COLOR,
    admin_existing_panel_available,
    logout_username,
    notification_button_view,
    reminder_popup_schedule,
    should_force_inventory_refresh,
    today_refresh_allowed,
)
from src.blite_v6.app.session_security import (
    normalize_after_ids,
    session_timeout_minutes,
    should_auto_logout,
)


def test_session_timeout_minutes_preserves_fallbacks_and_minimum():
    assert session_timeout_minutes({"session_timeout_minutes": 2}) == 5
    assert session_timeout_minutes({"session_timeout_minutes": "45"}) == 45
    assert session_timeout_minutes({"session_timeout_minutes": "bad"}) == 30
    assert session_timeout_minutes({}) == 30
    assert session_timeout_minutes(None) == 30


def test_should_auto_logout_uses_settings_and_idle_time():
    assert should_auto_logout({"auto_logout": False}, 0.0, 10_000.0) is False
    assert should_auto_logout({"auto_logout": True, "session_timeout_minutes": 5}, 0.0, 299.0) is False
    assert should_auto_logout({"auto_logout": True, "session_timeout_minutes": 5}, 0.0, 300.0) is True


def test_normalize_after_ids_handles_tk_shapes():
    assert normalize_after_ids("") == []
    assert normalize_after_ids("after#1") == ["after#1"]
    assert normalize_after_ids(("after#1", "after#2")) == ["after#1", "after#2"]
    assert normalize_after_ids(None) == []


def test_notification_button_view_preserves_legacy_text_and_colors():
    assert notification_button_view(0).text == "Notifications"
    assert notification_button_view(3).text == "Notifications (3)"
    assert notification_button_view(3).color == NOTIFICATION_COLOR
    assert notification_button_view(3).hover_color == NOTIFICATION_HOVER_COLOR


def test_reminder_popup_schedule_staggers_by_100ms():
    assert reminder_popup_schedule(["a", "b", "c"]) == [(0, "a"), (100, "b"), (200, "c")]


def test_inventory_refresh_today_refresh_admin_and_logout_helpers():
    assert should_force_inventory_refresh({"inventory": object()}) is True
    assert should_force_inventory_refresh({}) is False
    assert today_refresh_allowed(False, now_ts=40.0, last_ts=20.0) is False
    assert today_refresh_allowed(False, now_ts=51.0, last_ts=20.0) is True
    assert today_refresh_allowed(True, now_ts=21.0, last_ts=20.0) is True
    assert admin_existing_panel_available(object()) is True
    assert admin_existing_panel_available(None) is False
    assert logout_username({"username": "boby"}) == "boby"
    assert logout_username({}) == ""
