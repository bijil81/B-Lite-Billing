from __future__ import annotations

from src.blite_v6.billing.catalog_search import (
    build_category_matches,
    category_values_for_mode,
    data_for_mode,
    find_exact_match,
    format_search_result_label,
    normalize_catalog_item,
    should_use_variant_products,
    smart_search,
    variant_selection_for_item,
)


ITEMS = [
    ("S001", "Hair Cut", "Hair", 300.0),
    ("S002", "Hair Spa", "Hair", 800.0),
    ("S003", "Facial", "Skin", 1200.0),
]


def test_data_for_mode_preserves_legacy_mode_selection():
    services = {"Hair": []}
    products = {"Retail": []}

    assert data_for_mode("services", services, products) is services
    assert data_for_mode("products", services, products) is products


def test_variant_product_flag_requires_products_mode_and_enabled_db():
    assert should_use_variant_products("products", True) is True
    assert should_use_variant_products("services", True) is False
    assert should_use_variant_products("products", False) is False


def test_category_values_use_variant_categories_for_products_when_supplied():
    assert category_values_for_mode("products", {}, ["Color", "Care"]) == ["All", "Color", "Care"]
    assert category_values_for_mode("services", {"Hair": [], "Skin": []}) == ["All", "Hair", "Skin"]


def test_build_category_matches_filters_mode_category_and_sorts_by_name():
    codes = {
        "P1": {"type": "product", "name": "Serum", "category": "Care", "price": 250.0},
        "S2": {"type": "service", "name": "Hair Spa", "category": "Hair", "price": 800.0},
        "S1": {"type": "service", "name": "Cut", "category": "Hair", "price": 300.0},
    }

    assert build_category_matches(codes, "services", "Hair") == [
        ("S1", "Cut", "Hair", 300.0),
        ("S2", "Hair Spa", "Hair", 800.0),
    ]


def test_smart_search_prioritizes_startswith_then_contains_and_excludes_no_match():
    matches = smart_search("hair", ITEMS)

    assert matches[:2] == [
        ("S001", "Hair Cut", "Hair", 300.0),
        ("S002", "Hair Spa", "Hair", 800.0),
    ]
    assert smart_search("zzzz", ITEMS) == []
    assert smart_search("", ITEMS) == ITEMS


def test_exact_match_checks_name_and_code_case_insensitively():
    assert find_exact_match("hair cut", ITEMS) == ("S001", "Hair Cut", "Hair", 300.0)
    assert find_exact_match("s002", ITEMS) == ("S002", "Hair Spa", "Hair", 800.0)
    assert find_exact_match("", ITEMS) is None
    assert find_exact_match("missing", ITEMS) is None


def test_variant_selection_preserves_metadata_only_when_variant_mode_is_active():
    meta = {"P1": {"id": 7, "display_name": "Serum 100ml"}}

    assert variant_selection_for_item("P1", meta, True) == {"id": 7, "display_name": "Serum 100ml"}
    assert variant_selection_for_item("P1", meta, False) is None
    assert variant_selection_for_item("missing", meta, True) == {}


def test_search_result_label_matches_legacy_dropdown_text():
    assert format_search_result_label("S001", "Hair Cut", 300.0) == "  S001  Hair Cut  -  Rs300"


def test_catalog_search_accepts_three_to_six_tuple_values():
    code_name_price = ("P001", "Rice Packet", "62")
    name_category_price = ("Tomato Loose", "Vegetables", "45.5")
    four_value = ("P002", "Sunflower Oil", "Grocery", "145")
    five_value = ("P003", "Rice Packet", "Grocery", "62", "8901234567890")
    six_value = ("P004", "Tomato Loose", "Vegetables", "45.5", "barcode", {"unit": "kg"})
    five_name_category_price = ("Tomato Loose", "Vegetables", "45.5", "barcode", {"unit": "kg"})
    mapping_value = {"code": "P005", "display_name": "Rice Bran Oil", "category_name": "Grocery", "sale_price": "125"}

    assert normalize_catalog_item(code_name_price) == ("P001", "Rice Packet", "", 62.0)
    assert normalize_catalog_item(name_category_price) == ("Tomato Loose", "Tomato Loose", "Vegetables", 45.5)
    assert normalize_catalog_item(four_value) == ("P002", "Sunflower Oil", "Grocery", 145.0)
    assert normalize_catalog_item(five_value) == ("P003", "Rice Packet", "Grocery", 62.0)
    assert normalize_catalog_item(six_value) == ("P004", "Tomato Loose", "Vegetables", 45.5)
    assert normalize_catalog_item(five_name_category_price) == ("Tomato Loose", "Tomato Loose", "Vegetables", 45.5)
    assert normalize_catalog_item(mapping_value) == ("P005", "Rice Bran Oil", "Grocery", 125.0)
    assert smart_search("rice", [("bad",), five_value]) == [("P003", "Rice Packet", "Grocery", 62.0)]
    assert find_exact_match("p003", [five_value]) == ("P003", "Rice Packet", "Grocery", 62.0)
