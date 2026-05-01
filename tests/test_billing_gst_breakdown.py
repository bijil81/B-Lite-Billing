from __future__ import annotations

import pytest

from src.blite_v6.billing.gst_breakdown import build_gst_computation
from src.blite_v6.billing.totals import calculate_billing_totals


def test_global_gst_breakdown_matches_legacy_total():
    totals = calculate_billing_totals(
        items=[
            {"mode": "services", "name": "Cut", "price": 118.0, "qty": 1},
            {"mode": "products", "name": "Serum", "price": 236.0, "qty": 1},
        ],
        gst_enabled=True,
        gst_rate=18.0,
        gst_type="inclusive",
    )

    assert totals.gst_amount == pytest.approx(54.0)
    assert totals.grand_total == pytest.approx(354.0)
    assert totals.taxable_amount == pytest.approx(300.0)
    assert len(totals.gst_breakdown) == 1
    assert totals.gst_breakdown[0].rate == 18.0


def test_item_wise_gst_breakdown_groups_multiple_rates():
    computation = build_gst_computation(
        [
            {"mode": "services", "name": "Cut", "price": 118.0, "qty": 1},
            {"mode": "products", "name": "Rice", "price": 105.0, "qty": 1, "gst_rate": 5, "price_includes_tax": True},
            {"mode": "products", "name": "Oil", "price": 112.0, "qty": 1, "gst_rate": 12, "price_includes_tax": True},
        ],
        gross_before_discount=335.0,
        gross_after_discount=335.0,
        gst_rate=18.0,
        gst_type="inclusive",
        product_wise_gst_enabled=True,
        gst_rate_source="item",
        missing_item_gst_policy="global",
    )

    rates = [round(group.rate, 2) for group in computation.rate_summary]
    assert rates == [5.0, 12.0, 18.0]
    assert computation.gst_amount == pytest.approx(35.0)
    assert computation.grand_total == pytest.approx(335.0)
    assert computation.taxable_amount == pytest.approx(300.0)


def test_item_wise_exclusive_product_adds_tax_on_top():
    computation = build_gst_computation(
        [
            {"mode": "products", "name": "Hair Dryer", "price": 1000.0, "qty": 1, "gst_rate": 18, "price_includes_tax": False},
        ],
        gross_before_discount=1000.0,
        gross_after_discount=1000.0,
        gst_rate=18.0,
        gst_type="exclusive",
        product_wise_gst_enabled=True,
        gst_rate_source="item",
        missing_item_gst_policy="global",
    )

    assert computation.gst_amount == pytest.approx(180.0)
    assert computation.grand_total == pytest.approx(1180.0)
    assert computation.taxable_amount == pytest.approx(1000.0)


def test_item_wise_hybrid_gst_uses_category_rate_when_item_rate_missing():
    computation = build_gst_computation(
        [
            {"mode": "products", "name": "Test Rice Packet 1kg", "category": "Grocery", "price": 105.0, "qty": 1},
        ],
        gross_before_discount=105.0,
        gross_after_discount=105.0,
        gst_rate=18.0,
        gst_type="inclusive",
        product_wise_gst_enabled=True,
        gst_rate_source="hybrid",
        missing_item_gst_policy="global",
        gst_category_rate_map={"grocery": 5.0},
    )

    assert computation.rate_summary[0].rate == pytest.approx(5.0)
    assert computation.gst_amount == pytest.approx(5.0)
    assert computation.taxable_amount == pytest.approx(100.0)
