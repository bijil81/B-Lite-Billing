from __future__ import annotations

import pytest

from src.blite_v6.billing.totals import calculate_billing_totals


def _legacy_calc(
    *,
    items,
    discount_enabled=False,
    discount_value=0.0,
    membership_disc_pct=0.0,
    use_points=False,
    customer_points=None,
    applied_offer=None,
    applied_redeem_code=None,
    apply_offer_fn=None,
    calc_redeem_discount_fn=None,
    gst_enabled=False,
    gst_rate=18.0,
    gst_type="inclusive",
):
    svc = [it for it in items if it["mode"] == "services"]
    prd = [it for it in items if it["mode"] == "products"]
    s_sub = sum(i["price"] * i["qty"] for i in svc)
    p_sub = sum(i["price"] * i["qty"] for i in prd)
    total = s_sub + p_sub

    disc = 0.0
    if discount_enabled:
        disc = min(total, max(0.0, discount_value))

    mem_disc = 0.0
    if membership_disc_pct > 0:
        mem_disc = round(s_sub * membership_disc_pct / 100, 2)
        mem_disc = max(0.0, min(mem_disc, max(0.0, total - disc)))

    pts_disc = 0.0
    missing_customer = False
    if use_points:
        if customer_points is None:
            missing_customer = True
        else:
            remaining_for_points = max(0.0, total - disc - mem_disc)
            pts_disc = float(min(int(customer_points), int(remaining_for_points)))

    offer_disc = 0.0
    if applied_offer:
        offer_disc = apply_offer_fn(applied_offer, items, max(0.0, total - disc - pts_disc))
        offer_disc = max(0.0, offer_disc)

    redeem_disc = 0.0
    if applied_redeem_code:
        redeem_disc = calc_redeem_discount_fn(
            applied_redeem_code,
            max(0.0, total - disc - pts_disc - offer_disc),
        )
        redeem_disc = max(0.0, redeem_disc)

    grand = max(0.0, total - disc - mem_disc - pts_disc - offer_disc - redeem_disc)
    gst = 0.0
    if gst_enabled and grand > 0:
        try:
            rate = float(gst_rate) / 100
            if gst_type == "inclusive":
                gst = grand - (grand / (1 + rate))
            else:
                gst = grand * rate
                grand = grand + gst
        except Exception:
            gst = grand - (grand / 1.18)

    return (s_sub, p_sub, total, disc, mem_disc, pts_disc, offer_disc, redeem_disc, grand, gst, missing_customer)


@pytest.mark.parametrize(
    "case",
    [
        {
            "items": [
                {"mode": "services", "name": "Cut", "price": 350.0, "qty": 1},
                {"mode": "products", "name": "Serum", "price": 210.0, "qty": 2},
            ],
        },
        {
            "items": [{"mode": "services", "name": "Spa", "price": 1000.0, "qty": 1}],
            "discount_enabled": True,
            "discount_value": 125.0,
            "membership_disc_pct": 15.0,
        },
        {
            "items": [{"mode": "services", "name": "Facial", "price": 700.0, "qty": 1}],
            "discount_enabled": True,
            "discount_value": 50.0,
            "membership_disc_pct": 10.0,
            "use_points": True,
            "customer_points": 80,
            "gst_enabled": True,
            "gst_rate": 18.0,
            "gst_type": "inclusive",
        },
        {
            "items": [{"mode": "products", "name": "Cream", "price": 400.0, "qty": 1}],
            "use_points": True,
            "customer_points": None,
            "gst_enabled": True,
            "gst_rate": "bad",
        },
        {
            "items": [{"mode": "services", "name": "Color", "price": 1200.0, "qty": 1}],
            "discount_enabled": True,
            "discount_value": 100.0,
            "use_points": True,
            "customer_points": 40,
            "applied_offer": {"id": "O1"},
            "applied_redeem_code": "R1",
            "gst_enabled": True,
            "gst_rate": 12.0,
            "gst_type": "exclusive",
        },
    ],
)
def test_extracted_totals_match_v5_6_formula(case):
    def apply_offer(_offer, _items, base):
        return min(30.0, base)

    def calc_redeem(_code, base):
        return min(20.0, base)

    case = {
        "apply_offer_fn": apply_offer,
        "calc_redeem_discount_fn": calc_redeem,
        **case,
    }

    legacy = _legacy_calc(**case)
    extracted = calculate_billing_totals(**case)

    assert extracted.as_legacy_tuple() == pytest.approx(legacy[:10])
    assert extracted.points_customer_missing is legacy[10]
