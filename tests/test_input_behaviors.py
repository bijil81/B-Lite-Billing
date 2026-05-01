from src.blite_v6.ui.input_behaviors import date_for_display, first_letter_caps


def test_first_letter_caps_preserves_existing_uppercase_and_codes():
    assert first_letter_caps("biji kumar") == "Biji Kumar"
    assert first_letter_caps("b-lite technologies") == "B-Lite Technologies"
    assert first_letter_caps("GST customer") == "GST Customer"


def test_date_for_display_converts_iso_dates_only():
    assert date_for_display("1981-12-17") == "17-12-1981"
    assert date_for_display("17-12-1981") == "17-12-1981"
    assert date_for_display("") == ""
