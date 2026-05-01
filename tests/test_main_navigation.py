from __future__ import annotations

from src.blite_v6.app.app_specs import build_module_specs, build_nav_entries
from src.blite_v6.app.navigation import (
    AI_ASSISTANT_KEY,
    ai_tab_runtime_ready,
    cached_frame_key,
    find_nav_entry,
    frame_visibility_plan,
    nav_button_active_plan,
    restore_visible_page_key,
    should_attach_billing_frame,
    should_initialize_ai_tab,
    should_show_ai_runtime_placeholder,
    standard_module_spec,
    switch_access_result,
)


def test_switch_access_result_preserves_denied_message():
    nav = build_nav_entries()
    result = switch_access_result(nav, "settings", lambda entry: False)

    assert result.allowed is False
    assert result.entry is not None
    assert result.entry[1] == "Settings"
    assert result.message == "Settings access is restricted for your role."


def test_switch_access_result_allows_unknown_key_like_legacy():
    result = switch_access_result(build_nav_entries(), "missing", lambda entry: False)

    assert result.allowed is True
    assert result.entry is None
    assert result.message is None


def test_find_nav_entry_and_restore_visible_page_key():
    nav = build_nav_entries()

    assert find_nav_entry(nav, "billing")[1] == "Billing"
    assert restore_visible_page_key("billing", ["dashboard", "billing"]) == "billing"
    assert restore_visible_page_key("billing", ["dashboard"]) is None
    assert restore_visible_page_key(None, ["billing"]) is None


def test_cached_frame_and_module_specs_preserve_ai_special_case():
    frames = {"billing": object()}
    specs = build_module_specs()

    assert cached_frame_key(frames, "billing") == "billing"
    assert cached_frame_key(frames, "missing") is None
    assert standard_module_spec(specs, "billing") == ("billing", "BillingFrame")
    assert standard_module_spec(specs, AI_ASSISTANT_KEY) is None


def test_ai_tab_decisions_preserve_runtime_paths():
    assert should_initialize_ai_tab(AI_ASSISTANT_KEY, True, True, False) is True
    assert should_initialize_ai_tab(AI_ASSISTANT_KEY, True, True, True) is False
    assert ai_tab_runtime_ready(AI_ASSISTANT_KEY, True, True, True) is True
    assert ai_tab_runtime_ready(AI_ASSISTANT_KEY, True, False, True) is False
    assert should_show_ai_runtime_placeholder(AI_ASSISTANT_KEY, True, False, False) is True
    assert should_show_ai_runtime_placeholder(AI_ASSISTANT_KEY, False, False, False) is False


def test_frame_and_nav_button_plans_preserve_active_key_only():
    assert should_attach_billing_frame("billing") is True
    assert should_attach_billing_frame("dashboard") is False
    assert frame_visibility_plan(["dashboard", "billing"], "billing") == [
        ("dashboard", False),
        ("billing", True),
    ]
    assert nav_button_active_plan(["dashboard", "billing"], "dashboard") == [
        ("dashboard", True),
        ("billing", False),
    ]
