from __future__ import annotations

from src.blite_v6.inventory_grocery.purchase_form import (
    build_purchase_invoice_payload,
    purchase_item_defaults,
)


def test_purchase_item_defaults_read_inventory_tax_and_price_fields():
    defaults = purchase_item_defaults({
        "unit": "kg",
        "cost": 32.25,
        "price": 45.5,
        "mrp": 50,
        "gst_rate": 5,
        "hsn_sac": "0702",
    })

    assert defaults == {
        "unit": "kg",
        "qty": "1",
        "cost_price": "32.25",
        "sale_price": "45.5",
        "mrp": "50",
        "gst_rate": "5",
        "hsn_sac": "0702",
        "batch_no": "",
        "expiry_date": "",
    }


def test_purchase_form_payload_uses_existing_vendor_id_without_blank_overwrite_fields():
    payload = build_purchase_invoice_payload({
        "vendor_id": 7,
        "vendor_name": "Fresh Farms",
        "vendor_phone": "",
        "invoice_no": "PF-1",
        "invoice_date": "2026-04-30",
        "item_name": "Test Tomato Loose",
        "qty": "2.5",
        "unit": "kg",
        "cost_price": "30",
    })

    assert payload["vendor_id"] == 7
    assert payload["vendor"] == {"name": "Fresh Farms"}
    assert payload["items"][0]["item_name"] == "Test Tomato Loose"
    assert payload["items"][0]["qty"] == "2.5"


def test_purchase_form_payload_accepts_multiple_items():
    payload = build_purchase_invoice_payload({
        "vendor_name": "Fresh Farms",
        "invoice_no": "PF-2",
        "invoice_date": "2026-04-30",
        "items": [
            {"item_name": "Tomato", "qty": "2", "unit": "kg", "cost_price": "30"},
            {"item_name": "Onion", "qty": "5", "unit": "kg", "cost_price": "20"},
        ],
    })

    assert len(payload["items"]) == 2
    assert payload["items"][0]["item_name"] == "Tomato"
    assert payload["items"][1]["item_name"] == "Onion"
