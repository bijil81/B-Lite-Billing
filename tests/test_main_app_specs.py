from __future__ import annotations

from src.blite_v6.app.app_specs import (
    action_allows_role,
    build_action_roles,
    build_module_specs,
    build_nav_entries,
    first_allowed_nav_key,
    nav_entry_allows_role,
    normalize_role,
)


def test_nav_entries_preserve_legacy_order_and_roles():
    nav = build_nav_entries()

    assert [entry[2] for entry in nav] == [
        "dashboard",
        "billing",
        "customers",
        "appointments",
        "membership",
        "offers",
        "redeem_codes",
        "cloud_sync",
        "staff",
        "inventory",
        "expenses",
        "whatsapp_bulk",
        "reports",
        "closing_report",
        "ai_assistant",
        "settings",
    ]
    assert nav[1] == ("\U0001F9FE", "Billing", "billing", ["owner", "manager", "receptionist", "staff"])
    assert nav[-1] == ("\u2699", "Settings", "settings", ["owner"])


def test_role_policy_preserves_first_allowed_navigation():
    nav = build_nav_entries()

    assert first_allowed_nav_key(nav, "owner") == "dashboard"
    assert first_allowed_nav_key(nav, "manager") == "dashboard"
    assert first_allowed_nav_key(nav, "receptionist") == "dashboard"
    assert first_allowed_nav_key(nav, "staff") == "billing"
    assert first_allowed_nav_key(nav, "unknown") is None


def test_nav_access_preserves_case_and_blank_role_handling():
    billing_entry = build_nav_entries()[1]
    settings_entry = build_nav_entries()[-1]

    assert normalize_role(" Manager ") == "manager"
    assert normalize_role("") == "staff"
    assert nav_entry_allows_role(billing_entry, "") is True
    assert nav_entry_allows_role(settings_entry, " manager ") is False
    assert nav_entry_allows_role(settings_entry, "OWNER") is True
    assert nav_entry_allows_role(None, "owner") is False


def test_action_roles_preserve_owner_manager_permissions():
    action_roles = build_action_roles()

    assert action_allows_role(action_roles, "admin_panel", "owner") is True
    assert action_allows_role(action_roles, "admin_panel", "manager") is False
    assert action_allows_role(action_roles, "delete_bill", "manager") is True
    assert action_allows_role(action_roles, "delete_bill", "staff") is False
    assert action_allows_role(action_roles, "missing_permission", "owner") is False


def test_module_specs_preserve_main_navigation_targets():
    specs = build_module_specs()

    assert specs["billing"] == ("billing", "BillingFrame")
    assert specs["appointments"] == ("booking_calendar", "BookingCalendarFrame")
    assert specs["settings"] == ("salon_settings", "SettingsFrame")
    assert "ai_assistant" not in specs
    assert "accounting" in specs
