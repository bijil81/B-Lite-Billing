from __future__ import annotations

from src.blite_v6.billing.ui_actions import (
    billing_bind_all_shortcut_specs,
    billing_context_action_specs,
    billing_context_copy_specs,
    billing_root_shortcut_specs,
    billing_widget_shortcut_specs,
    booking_clear_confirmation_message,
    booking_prefill_values,
    build_billing_context_extra,
    context_total_from_totals,
    fast_mode_button_view,
    format_context_clipboard_value,
    has_existing_booking_draft,
    next_fast_mode,
    refresh_action_sequence,
    reload_services_reset_state,
    should_show_billing_context_menu,
)


def test_context_menu_helpers_preserve_legacy_context_values():
    assert should_show_billing_context_menu([]) is False
    assert should_show_billing_context_menu([{"name": "Cut"}]) is True
    assert context_total_from_totals((0, 0, 0, 0, 0, 0, 0, 0, 123.45, 0)) == 123.45
    assert context_total_from_totals(()) == 0.0
    assert build_billing_context_extra([{"name": "Cut"}], "INV-1", 123.45) == {
        "has_bill_items": True,
        "invoice_number": "INV-1",
        "total_amount": 123.45,
    }


def test_context_action_specs_preserve_action_names_and_targets():
    assert billing_context_action_specs() == (
        ("EDIT_ITEMS", "_edit_item_qty"),
        ("UNDO_LAST", "undo_last"),
        ("SAVE", "manual_save"),
        ("PRINT", "print_bill"),
        ("EXPORT_PDF", "save_pdf"),
        ("WHATSAPP", "send_whatsapp"),
        ("CLEAR", "clear_all"),
    )
    assert billing_context_copy_specs() == (
        ("COPY_INVOICE", "invoice_number", "text"),
        ("COPY_TOTAL", "total_amount", "money"),
    )
    assert format_context_clipboard_value({"invoice_number": "INV-1"}, "invoice_number", "text") == "INV-1"
    assert format_context_clipboard_value({"total_amount": 42}, "total_amount", "money") == "42.00"


def test_shortcut_specs_preserve_keyboard_surface():
    assert billing_root_shortcut_specs() == (
        ("<F2>", "manual_save"),
        ("<F4>", "save_pdf"),
        ("<F5>", "print_bill"),
        ("<F6>", "send_whatsapp"),
        ("<F8>", "clear_all"),
        ("<Control-z>", "undo_last"),
    )
    assert billing_bind_all_shortcut_specs() == (("<Control-m>", "_toggle_fast_mode"),)
    assert billing_widget_shortcut_specs() == (
        ("price_ent", "<Return>", "add_item"),
        ("qty_ent", "<Return>", "add_item"),
    )


def test_fast_mode_and_refresh_reload_specs():
    assert next_fast_mode(False) is True
    assert next_fast_mode(True) is False
    assert fast_mode_button_view(True) == {"text": "Fast: ON", "color_key": "teal", "hover_key": "blue"}
    assert fast_mode_button_view(False) == {"text": "Fast: OFF", "color_key": "sidebar", "hover_key": "teal"}
    assert refresh_action_sequence() == (
        "refresh_offer_dropdown",
        "hide_search_popup",
        "hide_customer_suggestions",
    )
    assert reload_services_reset_state() == {
        "inventory_lookup_cache": None,
        "inventory_lookup_cache_time": 0.0,
        "search_text": "",
        "price_text": "",
    }


def test_booking_prefill_helpers_preserve_confirmation_and_values():
    assert has_existing_booking_draft([], "", "") is False
    assert has_existing_booking_draft([], "Anu", "") is True
    assert booking_clear_confirmation_message() == (
        "Convert Booking to Bill",
        "This will start a new bill and clear the current billing draft. Continue?",
    )
    assert booking_prefill_values({"customer_name": "  Anu  ", "phone": " 999 ", "service": " Cut "}) == {
        "customer_name": "Anu",
        "phone": "999",
        "service": "Cut",
    }
