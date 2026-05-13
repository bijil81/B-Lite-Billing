"""Tests for InventoryService.reduce_stock() — Phase 2 Stock Reduction Backend.

These tests are pure service-layer tests using an in-memory SQLite database.
No Tk, no real files on disk.

Run with: python -m pytest tests/test_inventory_stock_reduction.py -v
"""
from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock, patch, call
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_item(legacy_name: str, current_qty: float) -> dict:
    return {
        "id": 1,
        "legacy_name": legacy_name,
        "current_qty": current_qty,
        "category": "Test",
        "brand": "",
        "unit": "kg",
        "min_qty": 1.0,
        "cost_price": 10.0,
        "sale_price": 15.0,
        "active": 1,
        "is_deleted": 0,
    }


def _service_with_mocks(item: dict | None):
    """Return an InventoryService whose repo and catalog are mocked."""
    from services_v5.inventory_service import InventoryService

    repo = MagicMock()
    repo.get_item.return_value = item
    repo.update_quantity.return_value = None
    repo.add_movement.return_value = None

    catalog = MagicMock()
    catalog.sync_inventory_row.return_value = None

    svc = InventoryService(repo=repo, catalog_service=catalog)
    return svc, repo, catalog


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------

class TestReduceStockHappyPath:
    def test_basic_reduction_updates_quantity(self):
        item = _make_item("Banana Loose", current_qty=10.0)
        svc, repo, _ = _service_with_mocks(item)

        svc.reduce_stock("Banana Loose", qty=2.5, reason="Damaged")

        repo.update_quantity.assert_called_once_with("Banana Loose", pytest.approx(7.5))

    def test_reduction_records_movement_log(self):
        item = _make_item("Rice", current_qty=50.0)
        svc, repo, _ = _service_with_mocks(item)

        svc.reduce_stock("Rice", qty=5.0, reason="Expired", reduced_by="admin")

        repo.add_movement.assert_called_once()
        payload = repo.add_movement.call_args[0][0]
        assert payload["movement_type"] == "damage"
        assert payload["qty_delta"] == pytest.approx(-5.0)
        assert "Expired" in payload["note"]
        assert "admin" in payload["note"]

    def test_reduction_movement_type_is_damage(self):
        item = _make_item("Sugar", current_qty=20.0)
        svc, repo, _ = _service_with_mocks(item)

        svc.reduce_stock("Sugar", qty=1.0, reason="Wastage")

        payload = repo.add_movement.call_args[0][0]
        assert payload["movement_type"] == "damage"
        assert payload["reference_type"] == "manual_reduction"

    def test_reduction_syncs_catalog(self):
        item = _make_item("Oil", current_qty=15.0)
        svc, repo, catalog = _service_with_mocks(item)

        svc.reduce_stock("Oil", qty=3.0, reason="Damaged")

        catalog.sync_inventory_row.assert_called_once()

    def test_exact_qty_reduction_zeroes_stock(self):
        item = _make_item("Exact Item", current_qty=5.0)
        svc, repo, _ = _service_with_mocks(item)

        svc.reduce_stock("Exact Item", qty=5.0, reason="Damaged")

        repo.update_quantity.assert_called_once_with("Exact Item", pytest.approx(0.0))

    def test_fractional_reduction_precision(self):
        item = _make_item("Loose Item", current_qty=3.04724)
        svc, repo, _ = _service_with_mocks(item)

        svc.reduce_stock("Loose Item", qty=1.02, reason="Wastage")

        repo.update_quantity.assert_called_once_with(
            "Loose Item", pytest.approx(2.02724, rel=1e-5)
        )

    def test_reduced_by_not_required(self):
        item = _make_item("Item X", current_qty=10.0)
        svc, repo, _ = _service_with_mocks(item)

        # Should not raise
        svc.reduce_stock("Item X", qty=1.0, reason="Damaged")

        payload = repo.add_movement.call_args[0][0]
        # No "By:" segment in note when reduced_by is empty
        assert "By:" not in payload["note"]


# ---------------------------------------------------------------------------
# Validation rejection tests
# ---------------------------------------------------------------------------

class TestReduceStockValidation:
    def test_zero_qty_raises(self):
        item = _make_item("Item", current_qty=10.0)
        svc, _, _ = _service_with_mocks(item)

        with pytest.raises(ValueError, match="greater than 0"):
            svc.reduce_stock("Item", qty=0, reason="Damaged")

    def test_negative_qty_raises(self):
        item = _make_item("Item", current_qty=10.0)
        svc, _, _ = _service_with_mocks(item)

        with pytest.raises(ValueError, match="greater than 0"):
            svc.reduce_stock("Item", qty=-3.0, reason="Damaged")

    def test_none_qty_raises(self):
        item = _make_item("Item", current_qty=10.0)
        svc, _, _ = _service_with_mocks(item)

        with pytest.raises(ValueError):
            svc.reduce_stock("Item", qty=None, reason="Damaged")

    def test_empty_reason_raises(self):
        item = _make_item("Item", current_qty=10.0)
        svc, _, _ = _service_with_mocks(item)

        with pytest.raises(ValueError, match="reason is required"):
            svc.reduce_stock("Item", qty=2.0, reason="")

    def test_whitespace_only_reason_raises(self):
        item = _make_item("Item", current_qty=10.0)
        svc, _, _ = _service_with_mocks(item)

        with pytest.raises(ValueError, match="reason is required"):
            svc.reduce_stock("Item", qty=2.0, reason="   ")

    def test_nonexistent_item_raises(self):
        svc, _, _ = _service_with_mocks(item=None)  # repo returns None

        with pytest.raises(ValueError, match="not found"):
            svc.reduce_stock("Ghost Item", qty=1.0, reason="Damaged")

    def test_qty_exceeds_stock_raises(self):
        item = _make_item("Low Stock Item", current_qty=3.0)
        svc, repo, _ = _service_with_mocks(item)

        with pytest.raises(ValueError, match="only 3.0 units are in stock"):
            svc.reduce_stock("Low Stock Item", qty=5.0, reason="Damaged")

    def test_qty_exceeds_stock_does_not_update_db(self):
        """On over-reduction, neither update_quantity nor add_movement should be called."""
        item = _make_item("Stock Guard", current_qty=3.0)
        svc, repo, _ = _service_with_mocks(item)

        with pytest.raises(ValueError):
            svc.reduce_stock("Stock Guard", qty=10.0, reason="Damaged")

        repo.update_quantity.assert_not_called()
        repo.add_movement.assert_not_called()

    def test_empty_item_name_raises(self):
        svc, _, _ = _service_with_mocks(item=None)

        with pytest.raises(ValueError, match="cannot be empty"):
            svc.reduce_stock("", qty=1.0, reason="Damaged")
