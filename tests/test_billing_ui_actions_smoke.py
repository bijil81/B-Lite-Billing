from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BILLING_PATH = ROOT / "billing.py"


def _method_source(method_name: str) -> str:
    source = BILLING_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(BILLING_PATH))
    lines = source.splitlines()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == method_name:
            return "\n".join(lines[node.lineno - 1:node.end_lineno])
    raise AssertionError(f"Method not found: {method_name}")


def test_phase10_wrappers_delegate_to_ui_action_helpers():
    source = BILLING_PATH.read_text(encoding="utf-8")

    assert "from src.blite_v6.billing.ui_actions import" in source
    assert "refresh_action_sequence" in _method_source("refresh")
    assert "booking_prefill_values" in _method_source("prefill_from_booking")
    assert "has_existing_booking_draft" in _method_source("prefill_from_booking")
    assert "booking_clear_confirmation_message" in _method_source("prefill_from_booking")
    assert "should_show_billing_context_menu" in _method_source("_right_click_menu")
    assert "context_total_from_totals" in _method_source("_right_click_menu")
    assert "build_billing_context_extra" in _method_source("_right_click_menu")
    assert "billing_context_action_specs" in _method_source("_register_billing_context_menu_callbacks")
    assert "billing_context_copy_specs" in _method_source("_register_billing_context_menu_callbacks")
    assert "format_context_clipboard_value" in _method_source("_register_billing_context_menu_callbacks")
    assert "billing_root_shortcut_specs" in _method_source("_bind_shortcuts")
    assert "billing_bind_all_shortcut_specs" in _method_source("_bind_shortcuts")
    assert "billing_widget_shortcut_specs" in _method_source("_bind_shortcuts")
    assert "next_fast_mode" in _method_source("_toggle_fast_mode")
    assert "fast_mode_button_view" in _method_source("_update_fast_mode_ui")
    assert "reload_services_reset_state" in _method_source("reload_services")


def test_phase10_wrappers_keep_external_side_effects_in_billing_py():
    assert "root.bind" in _method_source("_bind_shortcuts")
    assert "self.bind_all" in _method_source("_bind_shortcuts")
    assert "action_adapter.register" in _method_source("_register_billing_context_menu_callbacks")
    assert "clipboard_service.copy_text" in _method_source("_register_billing_context_menu_callbacks")
    assert "renderer_service.build_menu" in _method_source("_right_click_menu")
    assert "menu.tk_popup" in _method_source("_right_click_menu")
    assert "refresh_product_catalog_cache" in _method_source("reload_services")
