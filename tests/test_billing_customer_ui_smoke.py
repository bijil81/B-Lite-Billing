from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BILLING_PATH = ROOT / "billing.py"
RUNTIME_SERVICES_PATH = ROOT / "src" / "blite_v6" / "billing" / "runtime_services.py"


def _method_source(method_name: str) -> str:
    source = BILLING_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(BILLING_PATH))
    lines = source.splitlines()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == method_name:
            return "\n".join(lines[node.lineno - 1:node.end_lineno])
    raise AssertionError(f"Method not found: {method_name}")


def test_customer_ui_wrappers_delegate_to_phase3_helpers():
    source = BILLING_PATH.read_text(encoding="utf-8")
    runtime_source = RUNTIME_SERVICES_PATH.read_text(encoding="utf-8")

    assert "from src.blite_v6.billing.customer_context import" in source
    assert "from src.blite_v6.billing.customer_suggestions import" in source
    assert "auto_save_customer as _auto_save_customer" in source
    assert "billing_save_customer as _billing_save_customer" in source
    assert "should_auto_save_customer" in runtime_source
    assert "build_v5_customer_payload" in runtime_source
    assert "build_phone_lookup_state" in _method_source("_on_phone_lookup")
    assert "format_membership_info" in _method_source("_check_membership_discount")
    assert "is_birthday_month" in _method_source("_check_birthday_offer")
    assert "find_customer_suggestions" in _method_source("_show_suggestions")
    assert "format_customer_suggestion_label" in _method_source("_build_suggestion_popup")
    assert "clamp_suggestion_index" in _method_source("_hover_suggestion")


def test_suggestion_popup_uses_cached_customer_snapshot():
    popup_source = _method_source("_build_suggestion_popup")

    assert 'getattr(self, "_suggest_customers", {})' in popup_source
    assert "_billing_get_customers()" not in popup_source


def test_customer_name_capitalization_is_attached_after_lookup_bindings():
    source = _method_source("_build")

    lookup_pos = source.index("bind_customer_lookup_entries(self)")
    caps_pos = source.index("attach_first_letter_caps(self.name_ent)")

    assert lookup_pos < caps_pos
