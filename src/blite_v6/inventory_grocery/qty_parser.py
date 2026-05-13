"""Quantity expression parser for inventory stock fields.

Supports single float input or a simple A + B addition expression.

Rules (enforced):
  - Exactly one '+' operator is allowed (max).  Multiple operators are rejected.
  - Both operands must be non-negative decimal numbers.
  - The computed result must be strictly greater than 0.
  - Letters, symbols other than '+' and '.', or malformed expressions are rejected.

Usage:
    from src.blite_v6.inventory_grocery.qty_parser import parse_qty_expression

    qty = parse_qty_expression("3.04724 + 9.250")   # -> 12.29724
    qty = parse_qty_expression("12.5")               # -> 12.5
    # Raises ValueError for: "abc", "3+4+5", "-1", "0"
"""
from __future__ import annotations

import re


# Pre-compiled pattern: optional sign then digits, optional decimal fraction.
# We only allow positive numbers (no leading minus) because stock quantities
# must be non-negative.
_NUMBER_RE = re.compile(r"^\d+(\.\d+)?$")


def _parse_operand(text: str, field_label: str) -> float:
    """Parse a single operand string to a non-negative float.

    Raises ValueError with a user-facing message if invalid.
    """
    cleaned = text.strip()
    if not cleaned:
        raise ValueError(f"{field_label} cannot be empty.")
    if not _NUMBER_RE.match(cleaned):
        raise ValueError(
            f"'{cleaned}' is not a valid quantity. "
            "Only positive numbers (e.g. 3.5, 0.250) are accepted."
        )
    try:
        value = float(cleaned)
    except ValueError:
        raise ValueError(f"'{cleaned}' could not be converted to a number.")
    if value < 0:
        raise ValueError(f"{field_label} cannot be negative.")
    return value


def parse_qty_expression(text: str) -> float:
    """Parse a quantity expression and return the computed float value.

    Accepted formats:
        "12.5"            -> 12.5
        "3.04724 + 9.250" -> 12.29724
        "1 + 0.5"         -> 1.5

    Raises:
        ValueError: with a user-readable message describing exactly what
                    is wrong with the input.

    The caller is responsible for displaying this message to the user.
    """
    if text is None:
        raise ValueError("Quantity cannot be empty.")

    raw = str(text).strip()

    if not raw:
        raise ValueError("Quantity cannot be empty.")

    # Count the number of '+' characters (strip whitespace first to handle
    # cases like "3 +4" or "3+ 4" uniformly).
    plus_count = raw.count("+")

    if plus_count > 1:
        raise ValueError(
            "Only one '+' is allowed in a quantity expression. "
            f"Got: '{raw}'"
        )

    if plus_count == 1:
        # Split into exactly two parts
        parts = raw.split("+", maxsplit=1)
        left = _parse_operand(parts[0], "First value")
        right = _parse_operand(parts[1], "Second value")
        result = left + right
    else:
        result = _parse_operand(raw, "Quantity")

    # Round to 6 decimal places to avoid floating-point noise while
    # preserving precision for weighed goods (e.g. 3.04724 kg).
    result = round(result, 6)

    if result <= 0:
        raise ValueError(
            f"Quantity must be greater than 0. Got: {result}"
        )

    return result
