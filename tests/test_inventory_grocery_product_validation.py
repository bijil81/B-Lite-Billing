from decimal import Decimal

from src.blite_v6.inventory_grocery.product_validation import (
    below_cost_warning,
    normalize_barcode,
    normalize_sku,
    validate_gst_rate,
    validate_product_payload,
)


def test_product_payload_normalizes_valid_retail_item():
    result = validate_product_payload({
        "name": "Rice Loose",
        "category": "Grocery",
        "sale_price": "60",
        "cost_price": "55",
        "stock_qty": "25.5",
        "reorder_level": "5",
        "unit": "kg",
        "price_basis": "kg",
        "barcode": " 890123 ",
        "sku": " rice001 ",
        "gst_rate": "5",
    })

    assert result.ok is True
    assert result.errors == ()
    assert result.warnings == ()
    assert result.normalized["sale_price"] == Decimal("60")
    assert result.normalized["stock_qty"] == Decimal("25.5")
    assert result.normalized["barcode"] == "890123"
    assert result.normalized["sku"] == "RICE001"


def test_product_payload_rejects_negative_financial_and_stock_values():
    result = validate_product_payload({
        "name": "Bad Item",
        "category": "Grocery",
        "sale_price": "-1",
        "cost_price": "0",
        "stock_qty": "-2",
        "gst_rate": "101",
    })

    fields = {issue.field for issue in result.errors}
    assert result.ok is False
    assert {"sale_price", "stock_qty", "gst_rate"}.issubset(fields)


def test_below_cost_returns_warning_not_silent_rewrite():
    warning = below_cost_warning(Decimal("40"), Decimal("50"))

    assert warning is not None
    assert warning.field == "sale_price"


def test_product_payload_allows_below_cost_with_warning_payload():
    result = validate_product_payload({
        "name": "Promo Item",
        "category": "Retail",
        "sale_price": "40",
        "cost_price": "50",
        "stock_qty": "1",
        "gst_rate": "18",
    })

    assert result.ok is True
    assert result.normalized["sale_price"] == Decimal("40")
    assert result.normalized["cost_price"] == Decimal("50")
    assert [warning.field for warning in result.warnings] == ["sale_price"]


def test_gst_and_identifier_normalization():
    assert validate_gst_rate("0") == Decimal("0")
    assert validate_gst_rate("18") == Decimal("18")
    assert normalize_barcode(" 123 456 ") == "123 456"
    assert normalize_sku(" abc-01 ") == "ABC-01"
