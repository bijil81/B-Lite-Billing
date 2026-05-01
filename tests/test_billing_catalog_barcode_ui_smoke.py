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


def test_catalog_wrappers_delegate_to_phase4_helpers():
    source = BILLING_PATH.read_text(encoding="utf-8")

    assert "from src.blite_v6.billing.catalog_search import" in source
    assert "data_for_mode" in _method_source("_get_data")
    assert "should_use_variant_products" in _method_source("_use_v5_variant_products")
    assert "variant_selection_for_item" in _method_source("_apply_search_selection")
    assert "category_values_for_mode" in _method_source("_refresh_cats")
    assert "build_category_matches" in _method_source("_ss_show_all_for_cat")
    assert "smart_search" in _method_source("_smart_search")
    assert "build_category_matches" in _method_source("_ss_typing")
    assert "format_search_result_label" in _method_source("_ss_show")
    assert "find_exact_match" in _method_source("_get_exact_match")


def test_barcode_wrappers_delegate_to_phase4_helpers():
    source = BILLING_PATH.read_text(encoding="utf-8")

    assert "from src.blite_v6.billing.barcode_lookup import" in source
    assert "apply_scanned_product_to_bill" in _method_source("_on_barcode_enter")
    assert "find_barcode_in_variants" in _method_source("_lookup_barcode")
    assert "find_barcode_in_inventory" in _method_source("_lookup_barcode")
