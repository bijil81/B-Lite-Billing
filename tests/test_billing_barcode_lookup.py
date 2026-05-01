from __future__ import annotations

from src.blite_v6.billing.barcode_lookup import (
    apply_scanned_product_to_bill,
    build_scanned_product_item,
    find_barcode_in_inventory,
    find_barcode_in_variants,
)


def test_find_barcode_in_variants_normalizes_variant_metadata_and_stock():
    found = find_barcode_in_variants("ABC", [
        {"barcode": "NOPE", "variant_name": "Other"},
        {"barcode": " ABC ", "variant_name": "Serum 100ml", "sale_price": "250", "stock_qty": "3", "id": 9},
    ])

    assert found == {
        "name": "Serum 100ml",
        "price": 250.0,
        "qty": 3.0,
        "stock_available": True,
        "variant_id": 9,
    }


def test_find_barcode_in_inventory_uses_price_then_cost_fallback():
    found = find_barcode_in_inventory("LEG", {
        "Cream": {"barcode": "LEG", "cost": "75", "qty": "0"},
    })

    assert found == {
        "name": "Cream",
        "price": 75.0,
        "qty": 0.0,
        "stock_available": False,
    }


def test_build_scanned_product_item_preserves_variant_id_when_present():
    item = build_scanned_product_item({
        "name": "Serum 100ml",
        "price": 250.0,
        "variant_id": 9,
    })

    assert item == {
        "mode": "products",
        "name": "Serum 100ml",
        "price": 250.0,
        "qty": 1,
        "inventory_item_name": "Serum 100ml",
        "variant_id": 9,
    }


def test_apply_scanned_product_to_bill_increments_existing_product_case_insensitively():
    bill_items = [{"mode": "products", "name": "serum 100ml", "price": 250.0, "qty": 1}]

    result = apply_scanned_product_to_bill(bill_items, {
        "name": "Serum 100ml",
        "price": 250.0,
        "stock_available": True,
    })

    assert result == {"status": "incremented", "name": "Serum 100ml"}
    assert bill_items[0]["qty"] == 2


def test_apply_scanned_product_to_bill_adds_new_item_or_rejects_out_of_stock():
    bill_items: list[dict] = []

    out = apply_scanned_product_to_bill(bill_items, {
        "name": "Cream",
        "price": 75.0,
        "stock_available": False,
    })
    added = apply_scanned_product_to_bill(bill_items, {
        "name": "Cream",
        "price": 75.0,
        "stock_available": True,
    })

    assert out == {"status": "out_of_stock", "name": "Cream"}
    assert added == {"status": "added", "name": "Cream"}
    assert bill_items == [{
        "mode": "products",
        "name": "Cream",
        "price": 75.0,
        "qty": 1,
        "inventory_item_name": "Cream",
    }]
