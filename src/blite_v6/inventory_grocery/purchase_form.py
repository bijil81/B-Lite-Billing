"""UI-adjacent helpers for inventory purchase entry."""
from __future__ import annotations

from typing import Any, Mapping


def _text(value: object, default: str = "") -> str:
    text = str(value if value is not None else "").strip()
    return text or default


def _float_text(value: object, default: str = "0") -> str:
    try:
        number = float(value if value not in (None, "") else default)
    except Exception:
        return default
    if number.is_integer():
        return str(int(number))
    return f"{number:.3f}".rstrip("0").rstrip(".")


def purchase_item_defaults(item: Mapping[str, Any] | None) -> dict[str, str]:
    data = dict(item or {})
    return {
        "unit": _text(data.get("unit") or data.get("sale_unit"), "pcs"),
        "qty": "1",
        "cost_price": _float_text(data.get("cost"), "0"),
        "sale_price": _float_text(data.get("price"), "0"),
        "mrp": _float_text(data.get("mrp"), "0"),
        "gst_rate": _float_text(data.get("gst_rate"), "0"),
        "hsn_sac": _text(data.get("hsn_sac")),
        "batch_no": "",
        "expiry_date": "",
    }


def build_purchase_invoice_payload(raw: Mapping[str, Any]) -> dict[str, Any]:
    vendor_id = int(raw.get("vendor_id") or 0)
    vendor = {
        "name": _text(raw.get("vendor_name")),
        "phone": _text(raw.get("vendor_phone")),
        "gstin": _text(raw.get("vendor_gstin")),
        "address": _text(raw.get("vendor_address")),
        "opening_balance": raw.get("vendor_opening_balance", 0),
    }
    payload: dict[str, Any] = {
        "vendor": vendor,
        "vendor_id": vendor_id,
        "invoice_no": _text(raw.get("invoice_no")),
        "invoice_date": _text(raw.get("invoice_date")),
        "notes": _text(raw.get("notes")),
        "items": [
            {
                "item_name": _text(raw.get("item_name")),
                "qty": raw.get("qty"),
                "unit": _text(raw.get("unit"), "pcs"),
                "cost_price": raw.get("cost_price"),
                "sale_price": raw.get("sale_price"),
                "mrp": raw.get("mrp"),
                "gst_rate": raw.get("gst_rate"),
                "hsn_sac": _text(raw.get("hsn_sac")),
                "batch_no": _text(raw.get("batch_no")),
                "expiry_date": _text(raw.get("expiry_date")),
            }
        ],
    }
    if vendor_id and vendor["name"]:
        payload["vendor"] = {"name": vendor["name"]}
    return payload
