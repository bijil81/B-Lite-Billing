from __future__ import annotations

from src.blite_v6.app.app_specs import build_nav_entries
from src.blite_v6.app.runtime_features import (
    ai_feature_update_plan,
    normalize_ai_config,
    runtime_preference_view,
    sidebar_before_nav_key,
)


def test_runtime_preference_view_preserves_animation_fallback():
    assert runtime_preference_view(True).reset_animation_colors is False
    assert runtime_preference_view(False).reset_animation_colors is True
    assert runtime_preference_view(False).refresh_ai_floating_button is True


def test_normalize_ai_config_accepts_only_mapping_values():
    assert normalize_ai_config({"ai_config": {"enabled": False, "model": "x"}}) == {
        "enabled": False,
        "model": "x",
    }
    assert normalize_ai_config({"ai_config": "bad"}) == {}
    assert normalize_ai_config(None) == {}


def test_sidebar_before_nav_key_uses_next_packed_accessible_row():
    nav = build_nav_entries()

    before = sidebar_before_nav_key(
        "offers",
        nav,
        lambda entry: entry[2] != "redeem_codes",
        ["redeem_codes", "staff", "inventory"],
    )

    assert before == "staff"


def test_sidebar_before_nav_key_returns_none_when_no_later_visible_row():
    nav = build_nav_entries()

    assert sidebar_before_nav_key("settings", nav, lambda entry: True, ["settings"]) is None


def test_ai_feature_plan_when_enabled_without_controller():
    plan = ai_feature_update_plan(
        ai_enabled=True,
        ai_available=True,
        has_ai_controller=False,
        current_page_key="billing",
        fallback_key="dashboard",
    )

    assert plan.initialize_ai_controller is True
    assert plan.reset_ai_frame is True
    assert plan.show_ai_nav_row is True
    assert plan.refresh_ai_floating_button is True
    assert plan.destroy_ai_floating_widgets is False
    assert plan.switch_to_key is None


def test_ai_feature_plan_when_disabled_on_ai_page_switches_to_fallback():
    plan = ai_feature_update_plan(
        ai_enabled=False,
        ai_available=True,
        has_ai_controller=True,
        current_page_key="ai_assistant",
        fallback_key="billing",
    )

    assert plan.initialize_ai_controller is False
    assert plan.reset_ai_frame is False
    assert plan.show_ai_nav_row is False
    assert plan.refresh_ai_floating_button is True
    assert plan.destroy_ai_floating_widgets is True
    assert plan.switch_to_key == "billing"
