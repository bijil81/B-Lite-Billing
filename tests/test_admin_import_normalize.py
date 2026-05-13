from admin import _normalize_import_rows


def test_old_services_db_import_uses_products_section_for_products_tab():
    payload = {
        "Services": {
            "Treatments": {
                "Under Eye": 400,
            },
        },
        "Products": {
            "Hair Care": {
                "Shampoo 100ml": 199,
            },
        },
    }

    rows = _normalize_import_rows(payload, "Products")

    assert rows == [
        {
            "Item Name": "Shampoo 100ml",
            "Category": "Hair Care",
            "Price": 199,
            "Stock": 0,
            "Unit": "pcs",
        }
    ]


def test_old_services_db_import_uses_services_section_for_services_tab():
    payload = {
        "Services": {
            "Treatments": {
                "Under Eye": 400,
            },
        },
        "Products": {
            "Hair Care": {
                "Shampoo 100ml": 199,
            },
        },
    }

    rows = _normalize_import_rows(payload, "Services")

    assert rows == [
        {
            "Item Name": "Under Eye",
            "Category": "Treatments",
            "Price": 400,
        }
    ]
