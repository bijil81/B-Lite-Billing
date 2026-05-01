from __future__ import annotations

from src.blite_v6.settings.tab_specs import (
    advanced_feature_status_items,
    optional_tab_plan,
    settings_tab_defs,
)


def test_settings_tab_defs_inserts_ai_before_advanced_when_enabled():
    tabs = settings_tab_defs({"feature_ai_assistant": True})
    keys = [key for key, _label in tabs]

    assert keys.count("ai") == 1
    assert keys.index("ai") < keys.index("advanced")
    assert tabs[keys.index("ai")] == ("ai", "AI Assistant")


def test_settings_tab_defs_omits_ai_when_disabled():
    tabs = settings_tab_defs({"feature_ai_assistant": False})
    keys = [key for key, _label in tabs]

    assert "ai" not in keys
    assert keys == [
        "info",
        "theme",
        "bill",
        "sec",
        "pref",
        "notif",
        "backup",
        "advanced",
        "license",
        "about",
    ]


def test_optional_tab_plan_tracks_ai_visibility_and_fallback_target():
    enabled = optional_tab_plan({"feature_ai_assistant": True})
    disabled = optional_tab_plan({"feature_ai_assistant": False})

    assert enabled.ai_enabled is True
    assert enabled.ai_key == "ai"
    assert enabled.insert_before_key == "advanced"
    assert disabled.ai_enabled is False
    assert disabled.fallback_select_key == "advanced"


def test_advanced_feature_status_items_match_existing_copy_and_colors():
    colors = {"green": "green", "gold": "gold", "muted": "muted"}

    items = advanced_feature_status_items(
        ai_enabled=True,
        mobile_enabled=False,
        whatsapp_api_enabled=True,
        multibranch_enabled=False,
        colors=colors,
    )

    assert items == [
        {
            "label": "AI Assistant",
            "state": "ON",
            "caption": "Sidebar tab and floating AI tools.",
            "color": "green",
        },
        {
            "label": "Mobile Viewer",
            "state": "OFF",
            "caption": "Optional tab inside Cloud Sync only.",
            "color": "muted",
        },
        {
            "label": "Premium APIs",
            "state": "READY",
            "caption": "Customer-funded optional integrations.",
            "color": "gold",
        },
    ]


def test_salon_settings_imports_tab_spec_helpers():
    import salon_settings

    assert salon_settings.settings_tab_defs is settings_tab_defs
    assert salon_settings.optional_tab_plan is optional_tab_plan
    assert salon_settings.advanced_feature_status_items is advanced_feature_status_items

