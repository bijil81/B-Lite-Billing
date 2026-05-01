from __future__ import annotations

from adapters import product_catalog_adapter
from src.blite_v6.billing.catalog_search import variant_selection_for_item
from src.blite_v6.billing.cart_operations import parse_cart_quantity, unit_type_for_variant


def test_legacy_inventory_unit_metadata_reaches_billing_selection(monkeypatch):
    monkeypatch.setattr(product_catalog_adapter, "use_v5_product_variants_db", lambda: False)
    monkeypatch.setattr(product_catalog_adapter, "build_item_codes", lambda: {
        "PRI001": {
            "code": "PRI001",
            "name": "Rice Loose",
            "category": "Grocery",
            "price": 60.0,
            "type": "product",
        }
    })
    monkeypatch.setattr(product_catalog_adapter, "load_json", lambda _path, _default: {
        "Rice Loose": {
            "qty": 25.0,
            "unit": "kg",
            "pack_size": 1,
            "bill_label": "Rice Loose",
        }
    })

    matches, variant_meta = product_catalog_adapter.list_billing_product_matches("", "All")
    selected = variant_selection_for_item("PRI001", variant_meta, True)

    assert matches == [("PRI001", "Rice Loose", "Grocery", 60.0)]
    assert selected["unit_type"] == "kg"
    assert selected["stock_qty"] == 25.0
    assert unit_type_for_variant(selected) == "kg"
    assert parse_cart_quantity("1240g", unit_type_for_variant(selected)) == 1.24


def test_inventory_only_product_reaches_billing_category_and_search(monkeypatch):
    inventory_rows = [
        {
            "name": "Test Tomato Loose",
            "category": "Vegetables",
            "unit": "kg",
            "qty": 10.5,
            "cost": 32.25,
            "price": 45.5,
            "allow_decimal_qty": True,
            "is_weighed": True,
        }
    ]
    monkeypatch.setattr(product_catalog_adapter, "use_v5_product_variants_db", lambda: False)
    monkeypatch.setattr(product_catalog_adapter, "build_item_codes", lambda *args, **kwargs: {})
    monkeypatch.setattr(product_catalog_adapter, "load_json", lambda _path, _default: inventory_rows)

    categories = product_catalog_adapter.list_billing_product_categories()
    matches, variant_meta = product_catalog_adapter.list_billing_product_matches("toma", "Vegetables")

    assert "Vegetables" in categories
    assert len(matches) == 1
    code, name, category, price = matches[0]
    assert name == "Test Tomato Loose"
    assert category == "Vegetables"
    assert price == 45.5
    assert variant_meta[code]["unit_type"] == "kg"
    assert variant_meta[code]["allow_decimal_qty"] is True
    assert variant_meta[code]["is_weighed"] is True
