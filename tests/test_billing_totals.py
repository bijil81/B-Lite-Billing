from __future__ import annotations

import pytest

from src.blite_v6.billing.totals import calculate_billing_totals


def test_subtotals_and_direct_discount_are_capped():
    totals = calculate_billing_totals(
        items=[
            {"mode": "services", "name": "Hair Cut", "price": 300.0, "qty": 2},
            {"mode": "products", "name": "Serum", "price": 250.0, "qty": 1},
        ],
        discount_enabled=True,
        discount_value=9999.0,
    )

    # 9999 discount on total 850 is first pre-capped to 850 by min(total, ...),
    # then the 90% combined-discount cap reduces it to 765 (90% of 850).
    # grand_total = 850 - 765 = 85 (salon always keeps at least 10%).
    assert totals.service_subtotal == 600.0
    assert totals.product_subtotal == 250.0
    assert totals.total == 850.0
    assert totals.discount == pytest.approx(765.0, abs=0.05)
    assert totals.grand_total == pytest.approx(85.0, abs=0.05)


def test_membership_discount_applies_to_service_subtotal_only():
    totals = calculate_billing_totals(
        items=[
            {"mode": "services", "name": "Hair Cut", "price": 400.0, "qty": 1},
            {"mode": "products", "name": "Serum", "price": 600.0, "qty": 1},
        ],
        discount_enabled=True,
        discount_value=100.0,
        membership_disc_pct=10.0,
    )

    assert totals.membership_discount == 40.0
    assert totals.grand_total == 860.0


def test_points_use_remaining_amount_after_direct_and_membership_discount():
    totals = calculate_billing_totals(
        items=[{"mode": "services", "name": "Spa", "price": 500.0, "qty": 1}],
        discount_enabled=True,
        discount_value=100.0,
        membership_disc_pct=10.0,
        use_points=True,
        customer_points=999,
    )

    # total=500, discount=100, membership=45 (10% of 450 remaining).
    # Combined discount before cap = 100+45+350 = 495 = 99%.
    # 90% cap: max_allowed = 450. discounts scaled proportionally.
    # grand_total must be at least 10% of 500 = 50.
    assert totals.grand_total == pytest.approx(50.0, abs=0.10)
    assert totals.grand_total >= 0.0


def test_missing_customer_points_preserves_zero_discount_and_reports_missing_customer():
    totals = calculate_billing_totals(
        items=[{"mode": "services", "name": "Spa", "price": 500.0, "qty": 1}],
        use_points=True,
        customer_points=None,
    )

    assert totals.points_discount == 0.0
    assert totals.points_customer_missing is True


def test_offer_and_redeem_base_matches_v5_ordering():
    offer_bases: list[float] = []
    redeem_bases: list[float] = []

    def apply_offer(_offer, _items, base):
        offer_bases.append(base)
        return 25.0

    def calc_redeem(_code, base):
        redeem_bases.append(base)
        return 10.0

    totals = calculate_billing_totals(
        items=[{"mode": "services", "name": "Spa", "price": 500.0, "qty": 1}],
        discount_enabled=True,
        discount_value=50.0,
        membership_disc_pct=10.0,
        use_points=True,
        customer_points=20,
        applied_offer={"id": "OFFER"},
        applied_redeem_code="R10",
        apply_offer_fn=apply_offer,
        calc_redeem_discount_fn=calc_redeem,
    )

    assert offer_bases == [380.0]
    assert redeem_bases == [355.0]
    assert totals.grand_total == 345.0


def test_gst_inclusive_and_exclusive_modes_match_legacy_math():
    inclusive = calculate_billing_totals(
        items=[{"mode": "services", "name": "Spa", "price": 118.0, "qty": 1}],
        gst_enabled=True,
        gst_rate=18.0,
        gst_type="inclusive",
    )
    exclusive = calculate_billing_totals(
        items=[{"mode": "services", "name": "Spa", "price": 100.0, "qty": 1}],
        gst_enabled=True,
        gst_rate=18.0,
        gst_type="exclusive",
    )

    assert inclusive.gst_amount == pytest.approx(18.0)
    assert inclusive.grand_total == pytest.approx(118.0)
    assert exclusive.gst_amount == pytest.approx(18.0)
    assert exclusive.grand_total == pytest.approx(118.0)
