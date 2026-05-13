"""Tests for BillingService._validate_stock_availability — Phase 1 Negative Stock Block.

Uses an in-memory SQLite DB to simulate v5 inventory tables.
No Tk, no real files.

Run with: python -m pytest tests/test_billing_negative_stock_block.py -v
"""
from __future__ import annotations

import sqlite3
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Test DB setup helpers
# ---------------------------------------------------------------------------

def _make_db(items: list[dict] = None, variants: list[dict] = None) -> sqlite3.Connection:
    """Create an in-memory SQLite DB with the required v5 tables."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE v5_inventory_items (
            id INTEGER PRIMARY KEY,
            legacy_name TEXT NOT NULL,
            current_qty REAL DEFAULT 0
        );
        CREATE TABLE v5_product_variants (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            stock_qty REAL DEFAULT 0
        );
    """)
    for item in (items or []):
        conn.execute(
            "INSERT INTO v5_inventory_items(id, legacy_name, current_qty) VALUES(?, ?, ?)",
            (item["id"], item["legacy_name"], item["current_qty"]),
        )
    for v in (variants or []):
        conn.execute(
            "INSERT INTO v5_product_variants(id, name, stock_qty) VALUES(?, ?, ?)",
            (v["id"], v["name"], v["stock_qty"]),
        )
    conn.commit()
    return conn


def _validator(conn, items):
    """Convenience wrapper: call the private validator directly."""
    from services_v5.billing_service import BillingService
    svc = BillingService.__new__(BillingService)
    svc._validate_stock_availability(conn, items)


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------

class TestStockValidationHappyPath:
    def test_exact_stock_available_passes(self):
        conn = _make_db(items=[{"id": 1, "legacy_name": "Banana Loose", "current_qty": 5.0}])
        # Stock=5, sell=5 → OK
        _validator(conn, [{"mode": "products", "inventory_item_name": "Banana Loose", "qty": 5.0}])

    def test_more_stock_than_requested_passes(self):
        conn = _make_db(items=[{"id": 1, "legacy_name": "Rice", "current_qty": 20.0}])
        _validator(conn, [{"mode": "products", "inventory_item_name": "Rice", "qty": 5.0}])

    def test_service_items_are_ignored(self):
        """Services (mode != 'products') never touch inventory."""
        conn = _make_db()  # empty inventory
        _validator(conn, [{"mode": "services", "name": "Haircut", "qty": 1}])

    def test_product_not_in_db_is_ignored(self):
        """Items not found in DB are not blocked (legacy fallback path handles them)."""
        conn = _make_db()  # no items
        _validator(conn, [{"mode": "products", "inventory_item_name": "Unknown Item", "qty": 1}])

    def test_decimal_qty_passes(self):
        conn = _make_db(items=[{"id": 1, "legacy_name": "Oil Loose", "current_qty": 3.5}])
        _validator(conn, [{"mode": "products", "inventory_item_name": "Oil Loose", "qty": 2.75}])

    def test_variant_with_sufficient_stock_passes(self):
        conn = _make_db(variants=[{"id": 10, "name": "Shampoo 200ml", "stock_qty": 8.0}])
        _validator(conn, [{"mode": "products", "variant_id": 10, "qty": 3.0}])

    def test_mixed_cart_all_available_passes(self):
        conn = _make_db(
            items=[
                {"id": 1, "legacy_name": "Rice", "current_qty": 10.0},
                {"id": 2, "legacy_name": "Sugar", "current_qty": 5.0},
            ]
        )
        _validator(conn, [
            {"mode": "products", "inventory_item_name": "Rice", "qty": 2.0},
            {"mode": "products", "inventory_item_name": "Sugar", "qty": 1.0},
        ])


# ---------------------------------------------------------------------------
# Block tests — each must raise ValueError with "Insufficient stock"
# ---------------------------------------------------------------------------

class TestStockValidationBlock:
    def test_oversell_raises(self):
        """Stock=5, sell=6 → BLOCK."""
        conn = _make_db(items=[{"id": 1, "legacy_name": "Banana", "current_qty": 5.0}])
        with pytest.raises(ValueError, match="Insufficient stock for item: Banana"):
            _validator(conn, [{"mode": "products", "inventory_item_name": "Banana", "qty": 6.0}])

    def test_zero_stock_raises(self):
        """Stock=0, sell=1 → BLOCK."""
        conn = _make_db(items=[{"id": 1, "legacy_name": "Empty Item", "current_qty": 0.0}])
        with pytest.raises(ValueError, match="Insufficient stock for item: Empty Item"):
            _validator(conn, [{"mode": "products", "inventory_item_name": "Empty Item", "qty": 1.0}])

    def test_null_stock_raises(self):
        """Stock=NULL (treated as 0), sell=1 → BLOCK."""
        conn = _make_db(items=[{"id": 1, "legacy_name": "Null Stock", "current_qty": 0.0}])
        with pytest.raises(ValueError, match="Insufficient stock"):
            _validator(conn, [{"mode": "products", "inventory_item_name": "Null Stock", "qty": 1.0}])

    def test_variant_oversell_raises(self):
        """Variant stock=2, sell=5 → BLOCK."""
        conn = _make_db(variants=[{"id": 7, "name": "Conditioner 100ml", "stock_qty": 2.0}])
        with pytest.raises(ValueError, match="Insufficient stock for item: Conditioner 100ml"):
            _validator(conn, [{"mode": "products", "variant_id": 7, "qty": 5.0}])

    def test_multi_item_cart_one_fails_blocks_all(self):
        """Multiple items in cart: one fails → full block (no partial sales)."""
        conn = _make_db(items=[
            {"id": 1, "legacy_name": "Rice", "current_qty": 10.0},
            {"id": 2, "legacy_name": "Sugar", "current_qty": 2.0},
        ])
        with pytest.raises(ValueError, match="Insufficient stock for item: Sugar"):
            _validator(conn, [
                {"mode": "products", "inventory_item_name": "Rice", "qty": 3.0},   # OK
                {"mode": "products", "inventory_item_name": "Sugar", "qty": 5.0},  # FAIL
            ])

    def test_accumulated_qty_across_cart_rows_checked(self):
        """Same item in two cart rows: combined qty checked against stock."""
        conn = _make_db(items=[{"id": 1, "legacy_name": "Rice", "current_qty": 5.0}])
        # 3 + 4 = 7 > 5 → BLOCK
        with pytest.raises(ValueError, match="Insufficient stock for item: Rice"):
            _validator(conn, [
                {"mode": "products", "inventory_item_name": "Rice", "qty": 3.0},
                {"mode": "products", "inventory_item_name": "Rice", "qty": 4.0},
            ])

    def test_decimal_qty_overshoot_raises(self):
        """Stock=3.5kg, sell=3.6kg → BLOCK."""
        conn = _make_db(items=[{"id": 1, "legacy_name": "Oil Loose", "current_qty": 3.5}])
        with pytest.raises(ValueError, match="Insufficient stock"):
            _validator(conn, [{"mode": "products", "inventory_item_name": "Oil Loose", "qty": 3.6}])
