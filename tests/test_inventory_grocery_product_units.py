from decimal import Decimal

import pytest

from src.blite_v6.inventory_grocery.product_units import (
    convert_quantity,
    normalize_unit,
    parse_quantity_input,
    quantity_to_display,
)


def test_normalize_supported_retail_units():
    assert normalize_unit("pieces") == "pcs"
    assert normalize_unit("KG") == "kg"
    assert normalize_unit("ltr") == "L"
    assert normalize_unit("metre") == "meter"
    assert normalize_unit("unknown") == "custom"


def test_mass_and_volume_quantity_conversion():
    assert convert_quantity("1240", "g", "kg") == Decimal("1.24")
    assert convert_quantity("2", "kg", "g") == Decimal("2000")
    assert convert_quantity("500", "ml", "L") == Decimal("0.5")
    assert convert_quantity("1.5", "L", "ml") == Decimal("1500.0")


def test_parse_quantity_input_uses_price_basis():
    parsed = parse_quantity_input("1240g", price_basis="kg")
    assert parsed.quantity == Decimal("1.24")
    assert parsed.entered_unit == "g"
    assert parsed.basis_unit == "kg"


def test_parse_quantity_rejects_invalid_and_cross_dimension_values():
    with pytest.raises(ValueError):
        parse_quantity_input("bad", price_basis="kg")
    with pytest.raises(ValueError):
        parse_quantity_input("0", price_basis="kg")
    with pytest.raises(ValueError):
        parse_quantity_input("1kg", price_basis="L")


def test_quantity_display_hides_piece_unit():
    assert quantity_to_display(Decimal("2"), "pcs") == "2"
    assert quantity_to_display(Decimal("1.2400"), "kg") == "1.24 kg"
