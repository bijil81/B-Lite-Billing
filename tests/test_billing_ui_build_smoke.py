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


def test_build_delegates_phase9_ui_section_helpers():
    source = BILLING_PATH.read_text(encoding="utf-8")
    build_source = _method_source("_build")

    assert "from src.blite_v6.billing.ui_sections import" in source
    assert "resolve_billing_mode" in build_source
    assert "configure_billing_combobox_style" in build_source
    assert "calculate_bill_preview_font" in build_source
    assert "calculate_left_panel_width" in build_source
    assert "create_scrollable_panel" in build_source
    assert "create_intro_card" in build_source
    assert "create_card_section" in build_source
    assert "finish_action_specs" in build_source
    assert "resize_preview_font" in build_source
    assert "sync_billing_split" in build_source


def test_build_delegates_phase9_binding_helpers_and_keeps_widget_attrs():
    source = BILLING_PATH.read_text(encoding="utf-8")
    build_source = _method_source("_build")

    assert "from src.blite_v6.billing.ui_bindings import" in source
    assert "bind_customer_lookup_entries" in build_source
    assert "bind_search_entry" in build_source
    assert "bind_barcode_entry" in build_source
    assert "bind_quantity_entry" in build_source
    assert "bind_discount_entry" in build_source
    assert "bind_bill_preview_text" in build_source

    for attr in [
        "self.btn_svc",
        "self.btn_prd",
        "self.name_ent",
        "self.phone_ent",
        "self.bday_ent",
        "self.cat_cb",
        "self.search_ent",
        "self.scan_entry",
        "self.price_ent",
        "self.qty_lbl",
        "self.qty_ent",
        "self.unit_hint_f",
        "self.unit_badge_lbl",
        "self.unit_helper_lbl",
        "self.disc_ent",
        "self.offer_cb",
        "self.coupon_ent",
        "self.redeem_ent",
        "self.txt",
        "self.total_lbl",
        "self.wa_status_btn",
        "self.fast_btn",
    ]:
        assert attr in build_source


def test_offer_coupon_redeem_rows_use_shared_grid_alignment():
    build_source = _method_source("_build")

    assert "offer_form.grid_columnconfigure(0, minsize=64)" in build_source
    assert "self.offer_cb.grid(row=0, column=1, columnspan=3, sticky=\"ew\")" in build_source
    assert "self.coupon_ent.grid(row=1, column=1, sticky=\"ew\"" in build_source
    assert "self.redeem_ent.grid(row=2, column=1, sticky=\"ew\"" in build_source
