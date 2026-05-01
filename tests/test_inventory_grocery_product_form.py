from src.blite_v6.inventory_grocery.product_form import (
    build_inventory_product_form_payload,
    should_show_grocery_controls,
)
from src.blite_v6.inventory_grocery.gst_autofill import resolve_inventory_gst_rate
from src.blite_v6.settings.gst_classification_master import resolve_gst_classification_rate


def test_packet_product_master_payload_preserves_price_barcode_and_tax_fields():
    payload = build_inventory_product_form_payload(
        {
            "name": "Rice Packet 1kg",
            "category": "Grocery",
            "brand": "House",
            "base_product": "Rice",
            "pack_size": "1",
            "qty": "12",
            "unit": "pcs",
            "sale_unit": "pcs",
            "barcode": "8901234567890",
            "sku": " rice-1kg ",
            "cost": "55",
            "sale_price": "62",
            "mrp": "65",
            "gst_rate": "5",
            "hsn_sac": "1006",
            "min_stock": "3",
            "price_includes_tax": True,
        }
    )

    assert payload.validation.ok
    item = payload.inventory_item
    assert item["category"] == "Grocery"
    assert item["sku"] == "RICE-1KG"
    assert item["barcode"] == "8901234567890"
    assert item["price"] == 62.0
    assert item["cost"] == 55.0
    assert item["mrp"] == 65.0
    assert item["gst_rate"] == 5.0
    assert item["hsn_sac"] == "1006"
    assert item["allow_decimal_qty"] is False

    variant = payload.catalog_payload["variants"][0]
    assert variant["sale_unit"] == "pcs"
    assert variant["price_includes_tax"] == 1
    assert variant["stock_qty"] == 12.0


def test_loose_grocery_product_defaults_decimal_and_weighed_flags():
    payload = build_inventory_product_form_payload(
        {
            "name": "Tomato Loose",
            "category": "Vegetables",
            "qty": "10.5",
            "unit": "kg",
            "cost": "32.25",
            "sale_price": "45.50",
            "min_stock": "2.5",
        }
    )

    assert payload.validation.ok
    item = payload.inventory_item
    assert item["unit"] == "kg"
    assert item["sale_unit"] == "kg"
    assert item["base_unit"] == "kg"
    assert item["allow_decimal_qty"] is True
    assert item["is_weighed"] is True
    assert item["qty"] == 10.5
    assert item["min_stock"] == 2.5


def test_new_category_is_accepted_and_normalized_to_inventory_shape():
    payload = build_inventory_product_form_payload(
        {
            "name": "Green Gram",
            "category": " Pulses ",
            "qty": "4",
            "unit": "kg",
            "cost": "90",
            "sale_price": "112",
        }
    )

    assert payload.validation.ok
    assert payload.inventory_item["category"] == "Pulses"
    assert payload.catalog_payload["category_name"] == "Pulses"


def test_below_cost_requires_explicit_ui_decision():
    payload = build_inventory_product_form_payload(
        {
            "name": "Below Cost Item",
            "category": "Test",
            "qty": "1",
            "unit": "pcs",
            "cost": "100",
            "sale_price": "80",
        }
    )

    assert payload.validation.ok
    assert payload.validation.warnings
    assert "below cost" in payload.validation.warnings[0].message.lower()


def test_inventory_gst_autofill_uses_category_master_before_global_fallback():
    assert resolve_inventory_gst_rate("Vegetables", settings={"gst_rate": 18, "gst_category_rate_map": {"Vegetables": 0}}) == 0.0
    assert resolve_inventory_gst_rate("Unknown Category", settings={"gst_rate": 18, "gst_category_rate_map": {"Vegetables": 0}}) == 18.0


def test_inventory_form_payload_autofills_blank_gst_from_settings():
    payload = build_inventory_product_form_payload(
        {
            "name": "Sunflower Oil",
            "category": "Oil",
            "qty": "1",
            "unit": "pcs",
            "cost": "120",
            "sale_price": "145",
            "gst_rate": "",
        },
        settings={"gst_rate": 18, "gst_category_rate_map": {"Oil": 5}},
    )

    assert payload.validation.ok
    assert payload.inventory_item["gst_rate"] == 5.0


def test_inventory_form_payload_autofills_from_classification_rule_before_category():
    payload = build_inventory_product_form_payload(
        {
            "name": "Sunflower Oil 1L",
            "base_product": "Sunflower Oil",
            "category": "Vegetables",
            "qty": "1",
            "unit": "pcs",
            "cost": "120",
            "sale_price": "145",
            "gst_rate": "",
        },
        settings={
            "gst_rate": 18,
            "gst_category_rate_map": {"Vegetables": 0},
            "gst_classification_rules": [
                {"field": "name", "mode": "contains", "pattern": "Sunflower Oil", "rate": 5}
            ],
        },
    )

    assert payload.validation.ok
    assert payload.inventory_item["gst_rate"] == 5.0


def test_inventory_form_payload_preserves_explicit_gst_rate():
    payload = build_inventory_product_form_payload(
        {
            "name": "Custom GST Item",
            "category": "Grocery",
            "qty": "1",
            "unit": "pcs",
            "cost": "100",
            "sale_price": "120",
            "gst_rate": "12",
        },
        settings={"gst_rate": 18, "gst_category_rate_map": {"Grocery": 5}},
    )

    assert payload.validation.ok
    assert payload.inventory_item["gst_rate"] == 12.0


def test_inventory_form_payload_switches_gst_when_classification_changes_in_edit_session():
    payload = build_inventory_product_form_payload(
        {
            "name": "Sunflower Oil 1L",
            "initial_name": "Sunflower Oil 1L",
            "initial_category": "Oil",
            "category": "Vegetables",
            "initial_base_product": "Sunflower Oil",
            "base_product": "Sunflower Oil",
            "initial_hsn_sac": "",
            "initial_sku": "",
            "initial_barcode": "",
            "initial_gst_rate": "5",
            "qty": "1",
            "unit": "pcs",
            "cost": "120",
            "sale_price": "160",
            "gst_rate": "5",
        },
        settings={
            "gst_rate": 18,
            "gst_category_rate_map": {"Vegetables": 0, "Oil": 5},
            "gst_classification_rules": [
                {"field": "name", "mode": "contains", "pattern": "Sunflower Oil", "rate": 12}
            ],
        },
    )

    assert payload.validation.ok
    assert payload.inventory_item["gst_rate"] == 12.0


def test_classification_rule_resolver_prioritizes_exact_matches():
    assert resolve_gst_classification_rate(
        {"name": "Sunflower Oil 1L", "hsn_sac": "1507"},
        rules=[
            {"field": "name", "mode": "contains", "pattern": "Oil", "rate": 12},
            {"field": "hsn_sac", "mode": "exact", "pattern": "1507", "rate": 5},
        ],
    ) == 5.0


def test_grocery_controls_can_follow_retail_product_mode_settings():
    assert should_show_grocery_controls({"retail_grocery_enabled": True})
    assert should_show_grocery_controls({"billing_mode": "product_only"})
    assert not should_show_grocery_controls({"billing_mode": "service_only"})
