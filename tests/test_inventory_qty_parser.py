"""Tests for qty_parser.parse_qty_expression — Phase 1 Smart Quantity Input.

All tests are pure: no DB, no Tk, no inventory state.
Run with: python -m pytest tests/test_inventory_qty_parser.py -v
"""
import pytest

from src.blite_v6.inventory_grocery.qty_parser import parse_qty_expression


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------

class TestValidSingleValues:
    def test_integer_string(self):
        assert parse_qty_expression("5") == 5.0

    def test_simple_decimal(self):
        assert parse_qty_expression("12.5") == 12.5

    def test_high_precision_decimal(self):
        assert parse_qty_expression("3.04724") == pytest.approx(3.04724, rel=1e-6)

    def test_leading_trailing_whitespace_ignored(self):
        assert parse_qty_expression("  7.0  ") == 7.0

    def test_minimum_positive_value(self):
        assert parse_qty_expression("0.000001") == pytest.approx(0.000001)


class TestAdditionExpressions:
    def test_basic_addition(self):
        result = parse_qty_expression("3.04724 + 9.250")
        assert result == pytest.approx(12.29724, rel=1e-6)

    def test_addition_no_spaces(self):
        assert parse_qty_expression("3.04724+9.250") == pytest.approx(12.29724, rel=1e-6)

    def test_addition_extra_whitespace(self):
        assert parse_qty_expression("  1.5  +  2.5  ") == pytest.approx(4.0)

    def test_addition_of_integers(self):
        assert parse_qty_expression("10 + 5") == 15.0

    def test_addition_produces_precise_result(self):
        # 1.001 + 1.001 = 2.002 (not floating-point garbage)
        result = parse_qty_expression("1.001 + 1.001")
        assert result == pytest.approx(2.002, rel=1e-6)


# ---------------------------------------------------------------------------
# Rejection tests — each must raise ValueError
# ---------------------------------------------------------------------------

class TestInvalidInput:
    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="empty"):
            parse_qty_expression("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError, match="empty"):
            parse_qty_expression("   ")

    def test_none_raises(self):
        with pytest.raises(ValueError):
            parse_qty_expression(None)

    def test_letters_raise(self):
        with pytest.raises(ValueError):
            parse_qty_expression("abc")

    def test_letters_in_expression_raise(self):
        with pytest.raises(ValueError):
            parse_qty_expression("3 + abc")

    def test_multiple_plus_operators_rejected(self):
        with pytest.raises(ValueError, match="one '\\+'"):
            parse_qty_expression("3 + 4 + 5")

    def test_subtraction_rejected(self):
        with pytest.raises(ValueError):
            parse_qty_expression("10 - 2")

    def test_multiplication_rejected(self):
        with pytest.raises(ValueError):
            parse_qty_expression("3 * 4")

    def test_division_rejected(self):
        with pytest.raises(ValueError):
            parse_qty_expression("10 / 2")

    def test_negative_single_value_rejected(self):
        with pytest.raises(ValueError):
            parse_qty_expression("-5")

    def test_zero_rejected(self):
        with pytest.raises(ValueError, match="greater than 0"):
            parse_qty_expression("0")

    def test_zero_addition_rejected(self):
        # 0 + 0 = 0 — must be rejected
        with pytest.raises(ValueError, match="greater than 0"):
            parse_qty_expression("0 + 0")

    def test_zero_plus_nonzero_accepted(self):
        # 0 + 5 = 5 — valid (one operand is 0, result > 0)
        assert parse_qty_expression("0 + 5") == 5.0

    def test_comma_decimal_rejected(self):
        # Comma separators are NOT supported
        with pytest.raises(ValueError):
            parse_qty_expression("3,5")

    def test_malformed_double_decimal_rejected(self):
        with pytest.raises(ValueError):
            parse_qty_expression("3.4.5")


# ---------------------------------------------------------------------------
# Integration: validate_product_payload accepts expressions via stock_qty
# ---------------------------------------------------------------------------

class TestProductValidationIntegration:
    def test_expression_accepted_in_product_form(self):
        from decimal import Decimal
        from src.blite_v6.inventory_grocery.product_validation import validate_product_payload

        result = validate_product_payload({
            "name": "Banana Loose",
            "category": "Fruit",
            "sale_price": "38",
            "cost_price": "28",
            "stock_qty": "3.04724 + 9.250",
            "reorder_level": "5",
            "unit": "kg",
        })

        assert result.ok is True
        assert result.errors == ()
        assert result.normalized["stock_qty"] == pytest.approx(Decimal("12.29724"), rel=1e-6)

    def test_invalid_expression_yields_validation_error(self):
        from src.blite_v6.inventory_grocery.product_validation import validate_product_payload

        result = validate_product_payload({
            "name": "Banana Loose",
            "category": "Fruit",
            "sale_price": "38",
            "cost_price": "28",
            "stock_qty": "abc",
            "unit": "kg",
        })

        assert result.ok is False
        fields = {issue.field for issue in result.errors}
        assert "stock_qty" in fields

    def test_multi_operator_expression_yields_validation_error(self):
        from src.blite_v6.inventory_grocery.product_validation import validate_product_payload

        result = validate_product_payload({
            "name": "Banana Loose",
            "category": "Fruit",
            "sale_price": "38",
            "cost_price": "28",
            "stock_qty": "3 + 4 + 5",
            "unit": "kg",
        })

        assert result.ok is False
        fields = {issue.field for issue in result.errors}
        assert "stock_qty" in fields
