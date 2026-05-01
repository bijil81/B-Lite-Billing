from src.blite_v6.inventory_grocery import billing_inventory_bridge as bridge


def test_inventory_billing_rows_keep_grocery_metadata():
    rows = list(
        bridge.iter_inventory_billing_rows_from_inventory(
            {
                "Test Tomato Loose": {
                    "category": "Vegetables",
                    "unit": "kg",
                    "sale_unit": "kg",
                    "base_unit": "kg",
                    "qty": 10.5,
                    "cost": 32.25,
                    "price": 45.5,
                    "allow_decimal_qty": True,
                    "is_weighed": True,
                    "gst_rate": 5,
                    "hsn_sac": "0702",
                }
            }
        )
    )

    assert len(rows) == 1
    row = rows[0]
    assert row["display_name"] == "Test Tomato Loose"
    assert row["category_name"] == "Vegetables"
    assert row["sale_price"] == 45.5
    assert row["unit_type"] == "kg"
    assert row["stock_qty"] == 10.5
    assert row["allow_decimal_qty"] is True
    assert row["is_weighed"] is True


def test_inventory_products_merge_without_overwriting_legacy(monkeypatch):
    monkeypatch.setattr(
        bridge,
        "iter_inventory_billing_rows",
        lambda: iter(
            [
                {
                    "display_name": "Test Rice Packet 1kg",
                    "category_name": "Grocery",
                    "sale_price": 62.0,
                },
                {
                    "display_name": "Legacy Shampoo",
                    "category_name": "Hair Care",
                    "sale_price": 200.0,
                },
            ]
        ),
    )

    merged = bridge.merge_inventory_products({"Hair Care": {"Legacy Shampoo": 199.0}})

    assert merged["Grocery"]["Test Rice Packet 1kg"] == 62.0
    assert merged["Hair Care"]["Legacy Shampoo"] == 199.0


def test_inventory_matches_append_for_billing_search(monkeypatch):
    monkeypatch.setattr(
        bridge,
        "iter_inventory_billing_rows",
        lambda: iter(
            [
                {
                    "code": "INV-TOMATO",
                    "display_name": "Test Tomato Loose",
                    "category_name": "Vegetables",
                    "sale_price": 45.5,
                    "barcode": "",
                    "allow_decimal_qty": True,
                    "is_weighed": True,
                },
                {
                    "code": "INV-RICE",
                    "display_name": "Test Rice Packet 1kg",
                    "category_name": "Grocery",
                    "sale_price": 62.0,
                    "barcode": "",
                    "allow_decimal_qty": False,
                    "is_weighed": False,
                },
            ]
        ),
    )
    matches = []
    meta = {}
    seen = set()

    bridge.append_inventory_product_matches(
        matches,
        meta,
        seen,
        query="toma",
        category="Vegetables",
    )

    assert matches == [("INV-TOMATO", "Test Tomato Loose", "Vegetables", 45.5)]
    assert meta["INV-TOMATO"]["allow_decimal_qty"] is True
    assert seen == {("test tomato loose", "vegetables")}


def test_inventory_billing_rows_accept_list_rows_and_ui_aliases():
    rows = list(
        bridge.iter_inventory_billing_rows_from_inventory(
            [
                {
                    "Item Name": "Test Rice Packet 1kg",
                    "Category": "Grocery",
                    "Unit (Measurement)": "pcs",
                    "Quantity": "10",
                    "Cost per Unit (Rs)": "55",
                    "Sale Price (Rs)": "62",
                    "GST Rate %": "5",
                    "HSN/SAC (Optional)": "1006",
                    "deleted": False,
                },
                {
                    "name": "Deleted Item",
                    "category": "Grocery",
                    "price": 10,
                    "deleted": True,
                },
            ]
        )
    )

    assert len(rows) == 1
    row = rows[0]
    assert row["display_name"] == "Test Rice Packet 1kg"
    assert row["category_name"] == "Grocery"
    assert row["unit_type"] == "pcs"
    assert row["stock_qty"] == 10.0
    assert row["cost_price"] == 55.0
    assert row["sale_price"] == 62.0
    assert row["gst_rate"] == 5.0


def test_billing_product_adapter_reads_active_inventory_service_rows(monkeypatch):
    from adapters import product_catalog_adapter
    import services_v5.inventory_service as inventory_service_module

    class FakeInventoryService:
        def build_legacy_inventory_map(self):
            return {
                "Test Rice Packet 1kg": {
                    "category": "Grocery",
                    "qty": 10,
                    "unit": "pcs",
                    "price": 62,
                    "cost": 55,
                }
            }

    monkeypatch.setattr(inventory_service_module, "InventoryService", FakeInventoryService)
    monkeypatch.setattr(product_catalog_adapter, "use_v5_product_variants_db", lambda: False)
    monkeypatch.setattr(product_catalog_adapter, "build_item_codes", lambda: {})
    monkeypatch.setattr(product_catalog_adapter, "load_json", lambda _path, default: default)

    matches, variant_meta = product_catalog_adapter.list_billing_product_matches("rice", "All")

    assert [(name, category, price) for _code, name, category, price in matches] == [
        ("Test Rice Packet 1kg", "Grocery", 62.0)
    ]
    code = matches[0][0]
    assert code.startswith("INV")
    assert variant_meta[code]["unit_type"] == "pcs"
    assert product_catalog_adapter.list_billing_product_categories() == ["Grocery"]
