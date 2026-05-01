from __future__ import annotations

from src.blite_v6.billing.cart_operations import (
    add_or_merge_cart_item,
    build_cart_item,
    existing_product_quantity_for_inventory_name,
    format_cart_quantity_label,
    parse_cart_quantity,
    remove_item_at,
    should_refresh_inventory_cache,
    undo_last_item,
    update_item_price,
    update_item_quantity,
    validate_variant_stock,
)


def test_quantity_parser_preserves_legacy_default_and_minimum():
    assert parse_cart_quantity("3") == 3
    assert parse_cart_quantity("") == 1
    assert parse_cart_quantity("0") == 1
    assert parse_cart_quantity("bad") == 1


def test_quantity_parser_supports_loose_grocery_units():
    assert parse_cart_quantity("1.24", unit_type="kg") == 1.24
    assert parse_cart_quantity("1240g", unit_type="kg") == 1.24
    assert parse_cart_quantity("2kg", unit_type="g") == 2000
    assert parse_cart_quantity("500ml", unit_type="L") == 0.5
    assert parse_cart_quantity("1.5L", unit_type="ml") == 1500


def test_quantity_labels_hide_piece_unit_and_show_loose_unit():
    assert format_cart_quantity_label({"qty": 2, "unit_type": "pcs"}) == "2"
    assert format_cart_quantity_label({"qty": 1.24, "unit_type": "kg"}) == "1.24 kg"
    assert format_cart_quantity_label({"qty": 0.5, "unit_type": "L"}) == "0.5 L"


def test_inventory_cache_refresh_uses_legacy_ttl_rule():
    assert should_refresh_inventory_cache(None, now=100.0, last_refresh=99.0) is True
    assert should_refresh_inventory_cache({}, now=120.0, last_refresh=100.0) is False
    assert should_refresh_inventory_cache({}, now=131.0, last_refresh=100.0) is True


def test_variant_stock_validation_counts_existing_inventory_name_quantity():
    bill_items = [
        {"mode": "products", "name": "Serum", "qty": 2.25, "inventory_item_name": "Serum 100ml"},
        {"mode": "services", "name": "Hair Cut", "qty": 10},
    ]
    selected_variant = {"display_name": "Serum 100ml", "stock_qty": 5, "unit_type": "pcs"}

    ok = validate_variant_stock(
        bill_items=bill_items,
        selected_variant=selected_variant,
        inventory_lookup={"Serum 100ml": {"qty": 5}},
        item_name="Serum",
        requested_qty=2.5,
    )
    too_many = validate_variant_stock(
        bill_items=bill_items,
        selected_variant=selected_variant,
        inventory_lookup={"Serum 100ml": {"qty": 4}},
        item_name="Serum",
        requested_qty=2.5,
    )

    assert existing_product_quantity_for_inventory_name(bill_items, "serum 100ml") == 2.25
    assert ok == {"ok": True, "message": ""}
    assert too_many == {"ok": False, "message": "Only 4 items left in stock"}


def test_variant_stock_validation_reports_empty_stock():
    result = validate_variant_stock(
        bill_items=[],
        selected_variant={"display_name": "Serum 100ml", "stock_qty": 0},
        inventory_lookup={},
        item_name="Serum",
        requested_qty=1,
    )

    assert result == {"ok": False, "message": "No stock available"}


def test_build_cart_item_preserves_variant_metadata_for_products_only():
    variant = {
        "id": 9,
        "display_name": "Serum 100ml",
        "category_name": "Hair Care",
        "unit_type": "ml",
        "unit_value": 100,
        "pack_label": "100 ml",
        "bill_label": "Serum 100ml",
        "cost_price": 180,
        "gst_rate": 5,
        "price_includes_tax": False,
    }

    assert build_cart_item(mode="products", name="Serum", price=250, qty=1, selected_variant=variant) == {
        "mode": "products",
        "name": "Serum",
        "price": 250.0,
        "qty": 1,
        "variant_id": 9,
        "inventory_item_name": "Serum 100ml",
        "category": "Hair Care",
        "category_name": "Hair Care",
        "unit_type": "ml",
        "unit_value": 100,
        "pack_label": "100 ml",
        "bill_label": "Serum 100ml",
        "cost_price": 180,
        "gst_rate": 5,
        "price_includes_tax": False,
    }
    assert "variant_id" not in build_cart_item(mode="services", name="Cut", price=300, qty=1, selected_variant=variant)


def test_add_or_merge_cart_item_merges_same_mode_name_and_price():
    bill_items = [{"mode": "products", "name": "Serum", "price": 250.0, "qty": 1}]
    result = add_or_merge_cart_item(
        bill_items,
        mode="products",
        name="serum",
        price=250.0,
        qty=2,
        selected_variant={"id": 9, "display_name": "Serum 100ml"},
    )

    assert result["action"] == "merged"
    assert bill_items == [{
        "mode": "products",
        "name": "Serum",
        "price": 250.0,
        "qty": 3,
        "variant_id": 9,
        "inventory_item_name": "Serum 100ml",
        "unit_type": "pcs",
    }]


def test_add_or_merge_cart_item_keeps_different_units_separate():
    bill_items = [{
        "mode": "products",
        "name": "Rice",
        "price": 60.0,
        "qty": 1.0,
        "variant_id": 1,
        "inventory_item_name": "Rice Loose",
        "unit_type": "kg",
    }]
    result = add_or_merge_cart_item(
        bill_items,
        mode="products",
        name="rice",
        price=60.0,
        qty=1,
        selected_variant={"id": 2, "display_name": "Rice 1kg Pack", "unit_type": "pcs"},
    )

    assert result["action"] == "added"
    assert len(bill_items) == 2


def test_add_or_merge_cart_item_adds_new_item_when_price_differs():
    bill_items = [{"mode": "services", "name": "Cut", "price": 300.0, "qty": 1}]
    result = add_or_merge_cart_item(bill_items, mode="services", name="Cut", price=350.0, qty=1)

    assert result["action"] == "added"
    assert len(bill_items) == 2


def test_edit_remove_and_undo_operations_mutate_existing_cart_safely():
    bill_items = [{"mode": "services", "name": "Cut", "price": 300.0, "qty": 2}]

    assert update_item_quantity(bill_items, 0, 5) is True
    assert update_item_price(bill_items, 0, 350.0) is True
    assert undo_last_item(bill_items) is True
    assert bill_items[0]["qty"] == 4
    assert remove_item_at(bill_items, 0) == {"mode": "services", "name": "Cut", "price": 350.0, "qty": 4}
    assert undo_last_item(bill_items) is False


def test_undo_removes_decimal_loose_product_line():
    bill_items = [{"mode": "products", "name": "Rice", "price": 60.0, "qty": 1.24, "unit_type": "kg"}]

    assert undo_last_item(bill_items) is True
    assert bill_items == []
