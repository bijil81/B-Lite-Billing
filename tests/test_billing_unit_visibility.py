from __future__ import annotations

from src.blite_v6.billing.ui_sections import quantity_unit_hint_view


def test_quantity_unit_hint_hides_for_service_mode():
    assert quantity_unit_hint_view(current_mode="services", selected_variant=None) == {
        "visible": False,
        "qty_label": "Qty:",
        "unit_badge": "",
        "helper": "",
        "show_helper": False,
    }


def test_quantity_unit_hint_prompts_until_product_is_selected():
    view = quantity_unit_hint_view(current_mode="products", selected_variant=None)

    assert view["visible"] is True
    assert view["qty_label"] == "Qty:"
    assert view["unit_badge"] == "Unit: select item"
    assert view["helper"] == ""
    assert view["show_helper"] is False


def test_quantity_unit_hint_shows_loose_mass_and_volume_examples():
    kg_view = quantity_unit_hint_view(
        current_mode="products",
        selected_variant={"unit_type": "kg"},
    )
    litre_view = quantity_unit_hint_view(
        current_mode="products",
        selected_variant={"unit_type": "L"},
    )
    pcs_view = quantity_unit_hint_view(
        current_mode="products",
        selected_variant={"unit_type": "pcs"},
    )

    assert kg_view["qty_label"] == "Qty (kg):"
    assert kg_view["unit_badge"] == "Unit: kg"
    assert kg_view["helper"] == "Enter 1.24 or 1240g"
    assert kg_view["show_helper"] is True
    assert litre_view["qty_label"] == "Qty (L):"
    assert litre_view["helper"] == "Enter 0.5 or 500ml"
    assert pcs_view["qty_label"] == "Qty (pcs):"
    assert pcs_view["helper"] == "Pieces / packets"
    assert pcs_view["show_helper"] is False
