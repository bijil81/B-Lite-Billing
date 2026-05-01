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


def test_discount_wrappers_delegate_to_phase6_helpers():
    source = BILLING_PATH.read_text(encoding="utf-8")

    assert "from src.blite_v6.billing.discounts import" in source
    assert "discount_toggle_state" in _method_source("_toggle_discount")
    assert "build_offer_options" in _method_source("_refresh_offer_dropdown")
    assert "select_offer_state" in _method_source("_on_offer_select")
    assert "normalize_coupon_code" in _method_source("_apply_coupon")
    assert "coupon_apply_state" in _method_source("_apply_coupon")
    assert "clear_offer_state" in _method_source("_clear_offer")
    assert "normalize_coupon_code" in _method_source("_apply_redeem")
    assert "redeem_apply_state" in _method_source("_apply_redeem")
    assert "should_clear_offer_info_after_redeem_clear" in _method_source("_clear_redeem")
