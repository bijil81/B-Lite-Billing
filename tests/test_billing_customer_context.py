from __future__ import annotations

from datetime import date

from src.blite_v6.billing.customer_context import (
    BIRTHDAY_COUPON_MESSAGE,
    build_phone_lookup_state,
    build_v5_customer_payload,
    format_membership_info,
    is_birthday_month,
    is_valid_lookup_phone,
    normalize_customer_identity,
    should_auto_save_customer,
)


def test_customer_identity_is_normalized_without_guessing_values():
    assert normalize_customer_identity(" 9999999999 ", " Anu ", " 2000-04-15 ") == {
        "phone": "9999999999",
        "name": "Anu",
        "birthday": "2000-04-15",
    }


def test_guest_empty_and_placeholder_customer_should_not_auto_save():
    assert should_auto_save_customer("", "Anu") is False
    assert should_auto_save_customer("9999999999", "") is False
    assert should_auto_save_customer("0000000000", "Anu") is False
    assert should_auto_save_customer("9999999999", "Guest") is False


def test_real_customer_should_auto_save_after_trimming():
    assert should_auto_save_customer(" 9999999999 ", " Anu ") is True


def test_v5_customer_payload_preserves_existing_fields_when_birthday_is_empty():
    payload = build_v5_customer_payload(
        " 9999999999 ",
        " Anu ",
        "",
        {"birthday": "1999-04-10", "vip": 1, "points_balance": "42"},
    )

    assert payload == {
        "phone": "9999999999",
        "name": "Anu",
        "birthday": "1999-04-10",
        "vip": True,
        "points_balance": 42,
    }


def test_lookup_phone_accepts_only_ten_digit_non_placeholder_numbers():
    assert is_valid_lookup_phone("9999999999") is True
    assert is_valid_lookup_phone(" 9999999999 ") is True
    assert is_valid_lookup_phone("0000000000") is False
    assert is_valid_lookup_phone("99999") is False
    assert is_valid_lookup_phone("999999999a") is False
    assert is_valid_lookup_phone("") is False


def test_phone_lookup_state_for_existing_customer_matches_legacy_labels():
    state = build_phone_lookup_state(
        "9999999999",
        {"name": "Anu", "birthday": "2000-04-15", "points": 25, "visits": [{}, {}]},
    )

    assert state["state"] == "existing"
    assert state["customer_name"] == "Anu"
    assert state["birthday"] == "2000-04-15"
    assert state["points_text"] == "Points: 25  |  Visits: 2"
    assert state["customer_status_text"] == "Existing"
    assert state["customer_status_color_key"] == "lime"


def test_phone_lookup_state_for_new_and_invalid_customer_matches_legacy_labels():
    new_state = build_phone_lookup_state("9999999999", None)
    invalid_state = build_phone_lookup_state("99999", None)

    assert new_state["state"] == "new"
    assert new_state["points_text"] == "Points: -"
    assert new_state["customer_status_text"] == "New Customer"
    assert new_state["customer_status_color_key"] == "accent"
    assert invalid_state["state"] == "empty"
    assert invalid_state["customer_status_text"] == ""


def test_membership_info_formats_existing_active_membership_text_and_font():
    info = format_membership_info({
        "status": "Active",
        "discount_pct": 10,
        "wallet_balance": 250,
        "package_name": "Gold",
    })

    assert info["active"] is True
    assert info["discount_pct"] == 10.0
    assert info["text"] == "Gold | 10% off | Wallet: Rs250"
    assert info["font"] == ("Arial", 9, "bold")


def test_membership_info_uses_smaller_font_for_long_text():
    info = format_membership_info({
        "status": "Active",
        "discount_pct": 15,
        "wallet_balance": 999,
        "package_name": "Very Long Premium Membership Package",
    })

    assert info["active"] is True
    assert info["font"] == ("Arial", 8, "bold")


def test_inactive_membership_resets_discount_and_text():
    info = format_membership_info({"status": "Expired", "discount_pct": 50})

    assert info["active"] is False
    assert info["discount_pct"] == 0.0
    assert info["text"] == ""


def test_birthday_month_detection_matches_legacy_month_slice_rule():
    assert is_birthday_month("2000-04-15", today=date(2026, 4, 28)) is True
    assert is_birthday_month("2000-05-15", today=date(2026, 4, 28)) is False
    assert is_birthday_month("", today=date(2026, 4, 28)) is False
    assert BIRTHDAY_COUPON_MESSAGE == "Birthday Month! Apply BDAY25 coupon for 25% off"
