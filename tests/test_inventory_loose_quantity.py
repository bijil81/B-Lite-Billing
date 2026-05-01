from __future__ import annotations


def test_deduct_inventory_for_sale_preserves_decimal_loose_stock(monkeypatch):
    import inventory
    import salon_settings

    inv = {"Rice Loose": {"qty": 5.0, "unit": "kg"}}
    saved = []

    monkeypatch.setattr(inventory, "get_inventory", lambda: inv)
    monkeypatch.setattr(inventory, "save_inventory", lambda data: saved.append(data.copy()) or True)
    monkeypatch.setattr(salon_settings, "get_settings", lambda: {"use_v5_product_variants_db": False})

    inventory.deduct_inventory_for_sale([
        {
            "mode": "products",
            "name": "Rice",
            "inventory_item_name": "Rice Loose",
            "qty": 1.24,
            "unit_type": "kg",
        }
    ])

    assert inv["Rice Loose"]["qty"] == 3.76
    assert saved
