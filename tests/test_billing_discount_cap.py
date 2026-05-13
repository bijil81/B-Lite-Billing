"""Tests for discount stacking cap — Phase 1.

Pure logic tests — no DB, no Tk.

Run with: python -m pytest tests/test_billing_discount_cap.py -v
"""
from __future__ import annotations

import pytest
from src.blite_v6.billing.totals import (
    _cap_combined_discounts,
    _MAX_DISCOUNT_FRACTION,
    calculate_billing_totals,
)


# ---------------------------------------------------------------------------
# _cap_combined_discounts unit tests
# ---------------------------------------------------------------------------

class TestCapCombinedDiscounts:
    def test_no_cap_when_under_limit(self):
        """Under 90% → values pass through unchanged."""
        d, m, p, o, r, triggered = _cap_combined_discounts(
            total=100.0, discount=40.0, membership_discount=0.0,
            points_discount=0.0, offer_discount=0.0, redeem_discount=0.0,
        )
        assert triggered is False
        assert d == 40.0

    def test_exact_90_percent_not_capped(self):
        """Exactly 90% combined → no cap triggered."""
        _, _, _, _, _, triggered = _cap_combined_discounts(
            total=100.0, discount=90.0, membership_discount=0.0,
            points_discount=0.0, offer_discount=0.0, redeem_discount=0.0,
        )
        assert triggered is False

    def test_over_90_triggers_cap(self):
        """120% discount → capped, triggered=True."""
        d, m, p, o, r, triggered = _cap_combined_discounts(
            total=100.0, discount=120.0, membership_discount=0.0,
            points_discount=0.0, offer_discount=0.0, redeem_discount=0.0,
        )
        assert triggered is True
        assert d + m + p + o + r <= 90.0 + 0.01  # within rounding

    def test_stacked_discounts_over_limit(self):
        """Multiple discount types stacked over 90%."""
        d, m, p, o, r, triggered = _cap_combined_discounts(
            total=100.0, discount=30.0, membership_discount=25.0,
            points_discount=20.0, offer_discount=15.0, redeem_discount=20.0,
        )
        # Combined = 110 → triggered, sum <= 90
        assert triggered is True
        total_disc = d + m + p + o + r
        assert total_disc <= 90.0 + 0.05  # allow tiny rounding

    def test_zero_total_never_triggers(self):
        """total=0 → no cap applied (avoid division by zero)."""
        _, _, _, _, _, triggered = _cap_combined_discounts(
            total=0.0, discount=0.0, membership_discount=0.0,
            points_discount=0.0, offer_discount=0.0, redeem_discount=0.0,
        )
        assert triggered is False

    def test_proportional_scaling_preserves_ratio(self):
        """When capped, each component is scaled proportionally."""
        d, m, p, o, r, triggered = _cap_combined_discounts(
            total=100.0, discount=50.0, membership_discount=50.0,
            points_discount=0.0, offer_discount=0.0, redeem_discount=0.0,
        )
        assert triggered is True
        # Both were equal → after scaling, still equal
        assert abs(d - m) < 0.05


# ---------------------------------------------------------------------------
# calculate_billing_totals integration tests
# ---------------------------------------------------------------------------

def _items(total_price: float) -> list:
    return [{"mode": "services", "price": total_price, "qty": 1}]


class TestBillingTotalsDiscountCap:
    def test_grand_total_never_negative(self):
        """Total=100, discount=120% → grand_total == 10 (90% cap)."""
        result = calculate_billing_totals(
            items=_items(100.0),
            discount_enabled=True,
            discount_value=120.0,
        )
        assert result.grand_total >= 0.0
        assert result.grand_total == pytest.approx(10.0, abs=0.05)

    def test_normal_discount_unchanged(self):
        """50% discount on 100 → grand_total = 50 (no cap needed)."""
        result = calculate_billing_totals(
            items=_items(100.0),
            discount_enabled=True,
            discount_value=50.0,
        )
        assert result.grand_total == pytest.approx(50.0, abs=0.01)

    def test_zero_discount_unchanged(self):
        """No discount → grand_total = total."""
        result = calculate_billing_totals(items=_items(100.0))
        assert result.grand_total == pytest.approx(100.0, abs=0.01)

    def test_decimal_amounts_accurate(self):
        """Decimal totals are handled precisely."""
        result = calculate_billing_totals(
            items=_items(199.99),
            discount_enabled=True,
            discount_value=99.99,
        )
        assert result.grand_total >= 0.0
        assert result.grand_total == pytest.approx(100.0, abs=0.02)

    def test_membership_plus_manual_discount_capped(self):
        """Manual 50% + membership 50% → stacked 100% → capped at 90%."""
        result = calculate_billing_totals(
            items=_items(100.0),
            discount_enabled=True,
            discount_value=50.0,
            membership_disc_pct=50.0,
        )
        assert result.grand_total >= 10.0 - 0.10  # at least 10 (100 - 90%)
        assert result.grand_total >= 0.0

    def test_zero_total_no_crash(self):
        """Zero-value bill → no crash, grand_total=0."""
        result = calculate_billing_totals(items=_items(0.0))
        assert result.grand_total == 0.0
