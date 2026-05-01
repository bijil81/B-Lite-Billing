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


def test_cart_wrappers_delegate_to_phase5_helpers():
    source = BILLING_PATH.read_text(encoding="utf-8")

    assert "from src.blite_v6.billing.cart_operations import" in source
    assert "should_refresh_inventory_cache" in _method_source("_get_inventory_lookup_map")
    assert "update_item_quantity" in _method_source("_edit_item_qty")
    assert "remove_item_at" in _method_source("_edit_item_qty")
    assert "update_item_price" in _method_source("_edit_item_qty")
    assert "parse_cart_quantity" in _method_source("add_item")
    assert "validate_variant_stock" in _method_source("add_item")
    assert "build_below_cost_warning_state" in _method_source("add_item")
    assert "add_or_merge_cart_item" in _method_source("add_item")
    assert "build_sale_margin_warning_state" in source
    assert "undo_last_item" in _method_source("undo_last")
