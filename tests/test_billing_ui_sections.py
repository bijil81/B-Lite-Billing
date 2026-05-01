from __future__ import annotations

from src.blite_v6.billing.ui_sections import (
    calculate_bill_preview_font,
    calculate_left_panel_width,
    finish_action_specs,
    resolve_billing_mode,
)


def test_resolve_billing_mode_preserves_legacy_initial_mode():
    assert resolve_billing_mode({}) == {
        "billing_mode": "mixed",
        "show_services": True,
        "show_products": True,
        "initial_mode": "services",
    }
    assert resolve_billing_mode({"billing_mode": "service_only"})["initial_mode"] == "services"
    assert resolve_billing_mode({"billing_mode": "product_only"}) == {
        "billing_mode": "product_only",
        "show_services": False,
        "show_products": True,
        "initial_mode": "products",
    }


def test_calculate_bill_preview_font_keeps_legacy_bounds():
    assert calculate_bill_preview_font(320) == 9
    assert calculate_bill_preview_font(960) == 12
    assert calculate_bill_preview_font(2000) == 14


def test_calculate_left_panel_width_uses_legacy_ratios_and_bounds():
    assert calculate_left_panel_width(1366, 1.0, False, 340, 500) == 437
    assert calculate_left_panel_width(1366, 1.0, True, 340, 500) == 491
    assert calculate_left_panel_width(800, 1.0, False, 340, 500) == 340
    assert calculate_left_panel_width(2400, 1.2, False, 340, 500) == 500


def test_finish_action_specs_preserve_labels_commands_and_grouping():
    specs = finish_action_specs({"print": 1, "pdf": 2, "save": 3, "wa": 4, "clear": 5})

    assert [spec["text"] for spec in specs] == ["PRINT", "PDF", "SAVE", "WA", "CLEAR"]
    assert [spec["command"] for spec in specs] == ["print_bill", "save_pdf", "manual_save", "send_whatsapp", "clear_all"]
    assert [spec["group"] for spec in specs] == ["secondary", "secondary", "primary", "primary", "primary"]
    assert [spec["width"] for spec in specs] == [1, 2, 3, 4, 5]
