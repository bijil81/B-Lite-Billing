from __future__ import annotations

from src.blite_v6.billing.split_layout import BILLING_LEFT_RATIO, billing_left_width


def test_billing_split_targets_52_48_when_space_allows():
    assert BILLING_LEFT_RATIO == 0.52
    assert billing_left_width(1680, min_left=620, min_preview=340) == 873


def test_billing_split_keeps_left_and_preview_guards():
    assert billing_left_width(900, min_left=620, min_preview=340) == 620
    assert billing_left_width(1200, min_left=620, min_preview=700) == 620
