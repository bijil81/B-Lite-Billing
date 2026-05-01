from __future__ import annotations

from src.blite_v6.settings.notifications import (
    build_notifications_payload,
    dismissed_count_label,
    normalize_popup_time,
    reset_dismissed_payload,
)
from src.blite_v6.settings.preferences import (
    build_preferences_payload,
    preferences_saved_message,
)
from src.blite_v6.settings.security_settings import (
    build_security_payload,
    current_username,
    normalize_session_timeout_minutes,
    password_visibility_show_value,
    validate_new_password,
)


def test_security_password_helpers_match_existing_messages():
    assert password_visibility_show_value(True) == ""
    assert password_visibility_show_value(False) == "*"
    assert validate_new_password("", "") == (False, "Min 8 characters required.")
    assert validate_new_password("1234567", "1234567") == (False, "Min 8 characters required.")
    assert validate_new_password("12345678", "87654321") == (False, "Passwords do not match.")
    assert validate_new_password("12345678", "12345678") == (True, "")


def test_security_payload_preserves_settings_and_normalizes_timeout():
    cfg = {"salon_name": "Demo", "session_timeout_minutes": 45}

    result = build_security_payload(
        cfg,
        auto_logout=True,
        require_pw_bill=False,
        session_timeout_minutes="bad",
    )

    assert result["salon_name"] == "Demo"
    assert result["auto_logout"] is True
    assert result["require_pw_bill"] is False
    assert result["session_timeout_minutes"] == 30
    assert normalize_session_timeout_minutes("0") == 30
    assert normalize_session_timeout_minutes("15") == 15
    assert cfg == {"salon_name": "Demo", "session_timeout_minutes": 45}


def test_current_username_fallbacks():
    assert current_username({"username": " Owner "}) == "owner"
    assert current_username({}) == "admin"
    assert current_username(object()) == "admin"


def test_preferences_payload_and_saved_message():
    cfg = {"salon_name": "Demo", "unknown": "keep"}

    result = build_preferences_payload(
        cfg,
        default_payment="UPI",
        show_points_on_bill=False,
        auto_clear_after_print=True,
        show_whatsapp_confirm=False,
        show_ai_floating_button=True,
        enable_animations=False,
        use_v5_customers_db=True,
        use_v5_appointments_db=False,
        use_v5_reports_db=True,
        use_v5_billing_db=False,
        use_v5_inventory_db=True,
        use_v5_staff_db=False,
        use_v5_product_variants_db=True,
        start_with_windows=True,
        default_report_period="Today",
    )

    assert result["salon_name"] == "Demo"
    assert result["unknown"] == "keep"
    assert result["default_payment"] == "UPI"
    assert result["show_points_on_bill"] is False
    assert result["auto_clear_after_print"] is True
    assert result["show_whatsapp_confirm"] is False
    assert result["show_ai_floating_button"] is True
    assert result["enable_animations"] is False
    assert result["use_v5_customers_db"] is True
    assert result["use_v5_product_variants_db"] is True
    assert result["start_with_windows"] is True
    assert result["default_report_period"] == "Today"
    assert preferences_saved_message(start_with_windows=False, startup_ok=False) == "Preferences saved!"
    assert "Could not set Windows startup" in preferences_saved_message(
        start_with_windows=True,
        startup_ok=False,
    )
    assert cfg == {"salon_name": "Demo", "unknown": "keep"}


def test_notifications_payload_popup_boundaries_and_reset():
    cfg = {"salon_name": "Demo", "notif_dismissed": ["low_stock", "birthday"]}

    result = build_notifications_payload(
        cfg,
        birthday=False,
        low_stock=True,
        appointments=False,
        popup_time="99",
    )

    assert result["salon_name"] == "Demo"
    assert result["notif_birthday"] is False
    assert result["notif_low_stock"] is True
    assert result["notif_appointments"] is False
    assert result["notif_popup_time"] == 5
    assert normalize_popup_time("10") == 10
    assert normalize_popup_time("bad") == 5
    assert dismissed_count_label(cfg["notif_dismissed"]) == "Dismissed: 2 item(s)"
    assert dismissed_count_label(None) == "Dismissed: 0 item(s)"

    reset = reset_dismissed_payload(cfg)
    assert reset["notif_dismissed"] == []
    assert cfg["notif_dismissed"] == ["low_stock", "birthday"]


def test_salon_settings_imports_phase5_helpers():
    import salon_settings
    from src.blite_v6.settings import notifications, preferences, security_settings

    assert salon_settings.build_security_payload is security_settings.build_security_payload
    assert salon_settings.build_preferences_payload is preferences.build_preferences_payload
    assert salon_settings.build_notifications_payload is notifications.build_notifications_payload
    assert salon_settings.dismissed_count_label is notifications.dismissed_count_label

