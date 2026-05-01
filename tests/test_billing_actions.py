from __future__ import annotations

from src.blite_v6.billing.billing_actions import (
    bill_action_empty_warning,
    bill_saved_message,
    has_bill_items,
    pdf_error_message,
    pdf_saved_message,
    print_error_message,
    printed_message,
    save_error_message,
    save_report_args_from_totals,
    should_auto_clear_after_print,
)


TOTALS = (100.0, 50.0, 150.0, 10.0, 5.0, 3.0, 2.0, 1.0, 129.0, 19.67)


def test_has_bill_items_and_empty_warning():
    assert has_bill_items([]) is False
    assert has_bill_items([{"name": "Cut"}]) is True
    assert bill_action_empty_warning() == ("Warning", "Bill is empty!")


def test_save_report_args_from_totals_preserves_legacy_argument_order():
    assert save_report_args_from_totals(TOTALS) == {
        "final": 129.0,
        "disc": 10.0,
        "pts_disc": 3.0,
        "offer_disc": 2.0,
        "redeem_disc": 1.0,
        "mem_disc": 5.0,
    }


def test_action_messages_match_legacy_text():
    assert bill_saved_message("bill.pdf") == ("Saved", "Bill saved:\nbill.pdf")
    assert pdf_saved_message("bill.pdf") == ("Saved", "PDF saved:\nbill.pdf")
    assert save_error_message("busy") == ("Error", "Could not save:\nbusy")
    assert pdf_error_message("busy") == ("Error", "Could not save PDF:\nbusy")
    assert printed_message("Printer") == ("Printed", "Printed to: Printer")
    assert print_error_message("offline") == (
        "Print Error",
        "Could not print:\noffline\n\nMake sure thermal printer is set as default.",
    )


def test_auto_clear_after_print_uses_settings_flag():
    assert should_auto_clear_after_print({"auto_clear_after_print": True}) is True
    assert should_auto_clear_after_print({}) is False
