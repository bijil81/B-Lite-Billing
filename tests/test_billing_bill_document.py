from __future__ import annotations

from datetime import datetime

from src.blite_v6.billing.bill_document import (
    apply_printer_width,
    build_bill_data_kwargs,
    build_pdf_path,
    offer_name_from,
    resolve_invoice_branding,
    resolve_print_width,
    split_bill_items,
)


TOTALS = (300.0, 250.0, 550.0, 50.0, 30.0, 20.0, 10.0, 5.0, 435.0, 66.36)


def test_split_bill_items_preserves_service_product_order():
    items = [
        {"mode": "services", "name": "Cut"},
        {"mode": "products", "name": "Serum"},
        {"mode": "services", "name": "Spa"},
    ]

    services, products = split_bill_items(items)

    assert services == [{"mode": "services", "name": "Cut"}, {"mode": "services", "name": "Spa"}]
    assert products == [{"mode": "products", "name": "Serum"}]


def test_print_width_prefers_print_width_chars_then_bill_width_with_fallback():
    assert resolve_print_width({"print_width_chars": "42", "bill_width": 32}) == 42
    assert resolve_print_width({"bill_width": "40"}) == 40
    assert resolve_print_width({"print_width_chars": "bad", "bill_width": "40"}) == 32
    assert apply_printer_width({"copies": 1}, {"print_width_chars": 48}) == {"copies": 1, "printer_width": 48}


def test_invoice_branding_uses_settings_then_branding_fallbacks():
    branding = {"header": "Fallback Salon", "address": "Fallback Address", "phone": "999"}

    assert resolve_invoice_branding({"salon_name": "B Lite", "address": "", "phone": ""}, branding) == {
        "salon_name": "B Lite",
        "address": "Fallback Address",
        "phone": "999",
        "gst_no": "",
    }


def test_bill_data_kwargs_match_legacy_billdata_fields():
    items = [
        {"mode": "services", "name": "Cut", "qty": 1, "price": 300.0},
        {"mode": "products", "name": "Serum", "qty": 1, "price": 250.0},
    ]
    kwargs = build_bill_data_kwargs(
        invoice="INV-1",
        settings={"salon_name": "B Lite", "gst_rate": "18", "gst_type": "inclusive"},
        invoice_branding={"header": "Fallback", "address": "Addr", "phone": "Phone"},
        customer_name="Anu",
        customer_phone="9999999999",
        payment_method="Cash",
        bill_items=items,
        totals=TOTALS,
        membership_disc_pct=10.5,
        applied_offer={"name": "Birthday"},
        applied_redeem_code="R5",
        now=datetime(2026, 4, 28, 10, 5),
    )

    assert kwargs["invoice"] == "INV-1"
    assert kwargs["salon_name"] == "B Lite"
    assert kwargs["svc_items"] == [items[0]]
    assert kwargs["prd_items"] == [items[1]]
    assert kwargs["subtotal"] == 550.0
    assert kwargs["discount"] == 50.0
    assert kwargs["mem_discount"] == 30.0
    assert kwargs["mem_pct"] == 10
    assert kwargs["pts_discount"] == 20.0
    assert kwargs["offer_discount"] == 10.0
    assert kwargs["offer_name"] == "Birthday"
    assert kwargs["redeem_discount"] == 5.0
    assert kwargs["redeem_code"] == "R5"
    assert kwargs["gst_amount"] == 66.36
    assert kwargs["gst_rate"] == 18.0
    assert kwargs["gst_type"] == "inclusive"
    assert kwargs["taxable_amount"] == 368.64
    assert kwargs["gst_mode"] == "global"
    assert kwargs["gst_breakdown"] == ()
    assert kwargs["grand_total"] == 435.0
    assert kwargs["timestamp"] == "2026-04-28 10:05"


def test_offer_name_and_pdf_path_match_legacy_defaults():
    assert offer_name_from(None) == ""
    assert offer_name_from({"name": "Birthday"}) == "Birthday"
    assert build_pdf_path(
        bills_dir="G:/Bills",
        invoice="INV-1",
        customer_name="Anu Nair",
        sanitize_filename=lambda value: value.replace(" ", "_"),
    ) == "G:/Bills\\INV-1_Anu_Nair.pdf"
    assert build_pdf_path(
        bills_dir="G:/Bills",
        invoice="INV-2",
        customer_name="",
        sanitize_filename=lambda value: value,
    ) == "G:/Bills\\INV-2_Guest.pdf"
