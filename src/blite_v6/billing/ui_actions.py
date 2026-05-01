from __future__ import annotations

from typing import Any, Mapping


def should_show_billing_context_menu(bill_items: list[dict[str, Any]] | None) -> bool:
    return bool(bill_items)


def context_total_from_totals(totals: tuple[Any, ...] | None) -> float:
    try:
        return float((totals or ())[8])
    except Exception:
        return 0.0


def build_billing_context_extra(
    bill_items: list[dict[str, Any]] | None,
    invoice_number: str,
    total_amount: float,
) -> dict[str, Any]:
    return {
        "has_bill_items": bool(bill_items),
        "invoice_number": invoice_number,
        "total_amount": total_amount,
    }


def billing_context_action_specs() -> tuple[tuple[str, str], ...]:
    return (
        ("EDIT_ITEMS", "_edit_item_qty"),
        ("UNDO_LAST", "undo_last"),
        ("SAVE", "manual_save"),
        ("PRINT", "print_bill"),
        ("EXPORT_PDF", "save_pdf"),
        ("WHATSAPP", "send_whatsapp"),
        ("CLEAR", "clear_all"),
    )


def billing_context_copy_specs() -> tuple[tuple[str, str, str], ...]:
    return (
        ("COPY_INVOICE", "invoice_number", "text"),
        ("COPY_TOTAL", "total_amount", "money"),
    )


def format_context_clipboard_value(extra: Mapping[str, Any], key: str, value_type: str) -> str:
    value = extra.get(key, "")
    if value_type == "money":
        return f"{float(value or 0.0):.2f}"
    return str(value)


def billing_root_shortcut_specs() -> tuple[tuple[str, str], ...]:
    return (
        ("<F2>", "manual_save"),
        ("<F4>", "save_pdf"),
        ("<F5>", "print_bill"),
        ("<F6>", "send_whatsapp"),
        ("<F8>", "clear_all"),
        ("<Control-z>", "undo_last"),
    )


def billing_bind_all_shortcut_specs() -> tuple[tuple[str, str], ...]:
    return (("<Control-m>", "_toggle_fast_mode"),)


def billing_widget_shortcut_specs() -> tuple[tuple[str, str, str], ...]:
    return (
        ("price_ent", "<Return>", "add_item"),
        ("qty_ent", "<Return>", "add_item"),
    )


def next_fast_mode(current: bool) -> bool:
    return not current


def fast_mode_button_view(fast_mode: bool) -> dict[str, str]:
    if fast_mode:
        return {"text": "Fast: ON", "color_key": "teal", "hover_key": "blue"}
    return {"text": "Fast: OFF", "color_key": "sidebar", "hover_key": "teal"}


def refresh_action_sequence() -> tuple[str, ...]:
    return ("refresh_offer_dropdown", "hide_search_popup", "hide_customer_suggestions")


def has_existing_booking_draft(bill_items: list[dict[str, Any]] | None, name: str, phone: str) -> bool:
    return bool(bill_items or name.strip() or phone.strip())


def booking_clear_confirmation_message() -> tuple[str, str]:
    return (
        "Convert Booking to Bill",
        "This will start a new bill and clear the current billing draft. Continue?",
    )


def booking_prefill_values(booking: Mapping[str, Any] | None) -> dict[str, str]:
    booking = dict(booking or {})
    return {
        "customer_name": str(booking.get("customer_name", "")).strip(),
        "phone": str(booking.get("phone", "")).strip(),
        "service": str(booking.get("service", "")).strip(),
    }


def reload_services_reset_state() -> dict[str, Any]:
    return {
        "inventory_lookup_cache": None,
        "inventory_lookup_cache_time": 0.0,
        "search_text": "",
        "price_text": "",
    }
