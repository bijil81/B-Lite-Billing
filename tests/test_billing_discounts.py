from __future__ import annotations

from src.blite_v6.billing.discounts import (
    build_offer_options,
    clear_offer_state,
    coupon_apply_state,
    coupon_invalid_text,
    discount_toggle_state,
    format_redeem_value,
    normalize_coupon_code,
    redeem_apply_state,
    select_offer_state,
    should_clear_offer_info_after_redeem_clear,
)


def safe_text(value):
    return str(value or "").strip()


def test_discount_toggle_state_preserves_legacy_entry_behavior():
    assert discount_toggle_state(True, "") == {
        "entry_state": "normal",
        "value": "0",
        "focus_discount": True,
    }
    assert discount_toggle_state(True, "25")["value"] == "25"
    assert discount_toggle_state(False, "25") == {
        "entry_state": "disabled",
        "value": "0",
        "focus_discount": False,
    }


def test_offer_options_format_percentage_flat_and_fallback_names():
    offers = [
        {"name": "Birthday", "type": "percentage", "value": 25},
        {"name": "Cashback", "type": "flat", "value": 100},
        {"name": "", "type": object(), "value": "bad"},
    ]

    assert build_offer_options(offers, safe_text) == [
        "No Offer",
        "Birthday (percentage - 25%)",
        "Cashback (flat - Rs100)",
        "Offer",
    ]


def test_select_offer_state_maps_combobox_value_to_offer_index():
    offers = [{"name": "Birthday", "description": "Birthday offer"}]
    values = ["No Offer", "Birthday (percentage - 25%)"]

    selected = select_offer_state(values[1], offers, values, safe_text)
    none_selected = select_offer_state("No Offer", offers, values, safe_text)

    assert selected == {"applied_offer": offers[0], "info_text": "Birthday offer", "clear_coupon": True}
    assert none_selected == {"applied_offer": None, "info_text": "", "clear_coupon": True}


def test_coupon_code_and_apply_state_match_legacy_text():
    code = normalize_coupon_code(" bday25 ")
    offer = {"name": "Birthday"}

    assert code == "BDAY25"
    assert coupon_apply_state(code, offer, safe_text) == {
        "valid": True,
        "applied_offer": offer,
        "offer_var": "No Offer",
        "info_text": "Coupon 'BDAY25' applied! - Birthday",
        "error_text": "",
    }
    assert coupon_apply_state(code, None, safe_text)["error_text"] == "Coupon 'BDAY25' is invalid or expired."
    assert coupon_invalid_text(code) == "Coupon 'BDAY25' is invalid or expired."


def test_clear_offer_state_resets_offer_and_redeem_together():
    assert clear_offer_state() == {
        "applied_offer": None,
        "applied_redeem_code": None,
        "offer_var": "No Offer",
        "info_text": "",
    }


def test_redeem_state_formats_flat_and_percentage_values():
    flat = redeem_apply_state("R100", True, {"value": 100, "discount_type": "flat"})
    pct = redeem_apply_state("R10", True, {"value": 10, "discount_type": "percentage"})
    invalid = redeem_apply_state("BAD", False, "Invalid")

    assert format_redeem_value(100, "flat") == "Rs100"
    assert format_redeem_value(10, "percentage") == "10%"
    assert flat == {
        "valid": True,
        "applied_redeem_code": "R100",
        "info_text": "Redeem 'R100' - Rs100 discount! (valid)",
        "error_text": "",
    }
    assert pct["info_text"] == "Redeem 'R10' - 10% discount! (valid)"
    assert invalid == {
        "valid": False,
        "applied_redeem_code": None,
        "info_text": "",
        "error_text": "Invalid",
    }


def test_redeem_clear_only_clears_info_when_no_offer_is_applied():
    assert should_clear_offer_info_after_redeem_clear(None) is True
    assert should_clear_offer_info_after_redeem_clear({"name": "Offer"}) is False
