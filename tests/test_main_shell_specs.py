from __future__ import annotations

from src.blite_v6.app.app_shell import build_shell_metrics, sidebar_drag_bounds
from src.blite_v6.app.shell_sections import (
    logo_section_view,
    topbar_action_button_specs,
    user_section_view,
)


def test_shell_metrics_preserve_responsive_sidebar_math():
    metrics = build_shell_metrics(
        {"ui_scale": 1.25},
        {"mode": "compact", "sidebar_w": 180, "padding": 6, "font_sz": 10, "btn_h": 30},
    )

    assert metrics.ui_scale == 1.25
    assert metrics.compact is True
    assert metrics.sidebar_width == 225
    assert metrics.nav_font_size == 13
    assert metrics.nav_padx == 15
    assert metrics.nav_pady == 7
    assert metrics.sidebar_button_height == 35
    assert metrics.user_button_width == 201


def test_shell_metrics_have_safe_fallbacks_for_missing_values():
    metrics = build_shell_metrics({"ui_scale": "bad"}, {})

    assert metrics.ui_scale == 1.0
    assert metrics.responsive["mode"] == "medium"
    assert metrics.sidebar_width == 190
    assert metrics.nav_font_size == 11
    assert metrics.sidebar_button_height == 32


def test_sidebar_drag_bounds_preserve_legacy_limits():
    assert sidebar_drag_bounds({"sidebar_w": 190}) == (160, 270)
    assert sidebar_drag_bounds({"sidebar_w": 120}) == (140, 260)


def test_logo_section_view_preserves_compact_and_regular_sizes():
    assert logo_section_view(False, 190).frame_pady == 16
    assert logo_section_view(False, 190).fallback_font_size == 13
    assert logo_section_view(False, 190).max_logo_width == 148
    assert logo_section_view(True, 140).frame_pady == 12
    assert logo_section_view(True, 140).max_logo_width == 120


def test_user_section_view_preserves_avatar_role_and_logout_specs():
    view = user_section_view(
        {"name": "Boby", "role": "owner"},
        nav_font_size=11,
        sidebar_button_height=30,
        user_button_width=166,
    )

    assert view.name == "Boby"
    assert view.avatar_initial == "B"
    assert view.role_text == "OWNER"
    assert view.role_color_key == "accent"
    assert view.logout_width == 166
    assert view.logout_height == 30
    assert view.logout_font_size == 10


def test_topbar_action_specs_preserve_owner_and_staff_buttons():
    owner_specs = topbar_action_button_specs(True)
    staff_specs = topbar_action_button_specs(False)

    assert [spec.key for spec in owner_specs] == ["admin", "help", "alerts"]
    assert [spec.key for spec in staff_specs] == ["help", "alerts"]
    assert owner_specs[0].command_name == "_open_admin"
    assert staff_specs[-1].text == "Notifications"
    assert staff_specs[-1].width == 160
