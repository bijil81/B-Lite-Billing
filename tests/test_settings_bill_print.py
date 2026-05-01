from __future__ import annotations

from src.blite_v6.settings.bill_gst import (
    bill_gst_saved_message,
    build_bill_gst_payload,
    parse_gst_rate,
)
from src.blite_v6.settings.print_settings import (
    build_print_preview_text,
    build_print_settings_payload,
    parse_print_width,
    print_settings_saved_message,
)


def test_bill_gst_payload_preserves_settings_and_parses_rate():
    cfg = {"salon_name": "Demo", "unknown": "keep"}

    result = build_bill_gst_payload(
        cfg,
        billing_mode="product_only",
        gst_always_on=True,
        gst_type="exclusive",
        gst_rate_text="12.5",
        product_wise_gst_enabled=True,
        gst_rate_source="item",
        missing_item_gst_policy="warn",
        bill_footer=" Thank you \n",
    )

    assert result["salon_name"] == "Demo"
    assert result["unknown"] == "keep"
    assert result["billing_mode"] == "product_only"
    assert result["gst_always_on"] is True
    assert result["gst_type"] == "exclusive"
    assert result["gst_rate"] == 12.5
    assert result["product_wise_gst_enabled"] is True
    assert result["gst_rate_source"] == "item"
    assert result["missing_item_gst_policy"] == "warn"
    assert result["bill_footer"] == "Thank you"
    assert cfg == {"salon_name": "Demo", "unknown": "keep"}


def test_bill_gst_rate_and_message_match_existing_fallbacks():
    assert parse_gst_rate("") == 18.0
    assert parse_gst_rate("bad") == 18.0

    msg = bill_gst_saved_message(
        {
            "billing_mode": "service_only",
            "gst_always_on": False,
            "gst_type": "inclusive",
            "gst_rate": 18.0,
            "product_wise_gst_enabled": True,
            "gst_rate_source": "hybrid",
        }
    )

    assert msg == (
        "Saved!\nMode: Service Business\nGST: Manual | Inclusive | 18.0%\n"
        "Tax Mode: Hybrid / Auto | Item GST ON\nGST Master: 0 category rules\n"
        "GST Classification: 0 item rules"
    )


def test_print_payload_preserves_settings_and_parses_width():
    cfg = {"salon_name": "Demo", "other": True}

    result = build_print_settings_payload(
        cfg,
        paper_size="58mm",
        font_size=7,
        width_text="32",
    )

    assert result["salon_name"] == "Demo"
    assert result["other"] is True
    assert result["paper_size"] == "58mm"
    assert result["print_font_size"] == 7
    assert result["print_width_chars"] == 32
    assert cfg == {"salon_name": "Demo", "other": True}


def test_print_width_and_message_match_existing_fallbacks():
    assert parse_print_width("bad") == 48

    msg = print_settings_saved_message(
        {"paper_size": "A4", "print_width_chars": 64, "print_font_size": 12}
    )

    assert msg == "Print settings saved!\nPaper: A4  Width: 64  Font: 12pt"


def test_print_preview_text_uses_shop_address_width_and_font_line():
    text = build_print_preview_text(
        {"salon_name": "B-Lite Technologies", "address": "Eraviputhoor Kadai"},
        paper_size="80mm",
        font_size=9,
        width_text="48",
    )

    lines = text.splitlines()
    assert len(lines[0]) == 48
    assert lines[0].strip() == "B-Lite Technologies"
    assert lines[1].strip() == "Eraviputhoor Kadai"
    assert "Invoice : INV00001     18-03-2026" in text
    assert "Paper:80mm  Width:48 cols  Font:9pt" in text


def test_salon_settings_imports_bill_and_print_helpers():
    import salon_settings
    from src.blite_v6.settings import bill_gst, print_settings

    assert salon_settings.build_bill_gst_payload is bill_gst.build_bill_gst_payload
    assert salon_settings.bill_gst_saved_message is bill_gst.bill_gst_saved_message
    assert salon_settings.build_print_settings_payload is print_settings.build_print_settings_payload
    assert salon_settings.print_settings_saved_message is print_settings.print_settings_saved_message
