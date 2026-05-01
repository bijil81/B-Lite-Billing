from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Callable, Mapping


TotalsTuple = tuple[float, float, float, float, float, float, float, float, float, float]


def split_bill_items(items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    service_items = [item for item in items if item["mode"] == "services"]
    product_items = [item for item in items if item["mode"] == "products"]
    return service_items, product_items


def resolve_print_width(settings: Mapping[str, Any], default_width: int = 32) -> int:
    raw_width = settings.get("print_width_chars", settings.get("bill_width", default_width))
    try:
        return int(float(raw_width))
    except Exception:
        return default_width


def apply_printer_width(print_settings: dict[str, Any], settings: Mapping[str, Any]) -> dict[str, Any]:
    print_settings["printer_width"] = resolve_print_width(settings)
    return print_settings


def resolve_invoice_branding(settings: Mapping[str, Any], invoice_branding: Mapping[str, str]) -> dict[str, str]:
    return {
        "salon_name": settings.get("salon_name") or invoice_branding["header"],
        "address": settings.get("address") or invoice_branding["address"],
        "phone": settings.get("phone") or invoice_branding["phone"],
        "gst_no": settings.get("gst_no", ""),
    }


def offer_name_from(applied_offer: Mapping[str, Any] | None) -> str:
    return applied_offer.get("name", "Offer") if applied_offer else ""


def build_bill_data_kwargs(
    *,
    invoice: str,
    settings: Mapping[str, Any],
    invoice_branding: Mapping[str, str],
    customer_name: str,
    customer_phone: str,
    payment_method: str,
    bill_items: list[dict[str, Any]],
    totals: TotalsTuple,
    membership_disc_pct: float,
    applied_offer: Mapping[str, Any] | None,
    applied_redeem_code: str | None,
    now: datetime,
    totals_detail: Any | None = None,
) -> dict[str, Any]:
    (_service_subtotal, _product_subtotal, total, disc, mem_disc, pts_disc,
     offer_disc, redeem_disc, grand, gst) = totals
    service_items, product_items = split_bill_items(bill_items)
    branding = resolve_invoice_branding(settings, invoice_branding)

    return {
        "invoice": invoice,
        "salon_name": branding["salon_name"],
        "address": branding["address"],
        "phone": branding["phone"],
        "gst_no": branding["gst_no"],
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "payment_method": payment_method,
        "svc_items": service_items,
        "prd_items": product_items,
        "subtotal": total,
        "discount": disc,
        "mem_discount": mem_disc,
        "mem_pct": int(membership_disc_pct),
        "pts_discount": pts_disc,
        "offer_discount": offer_disc,
        "offer_name": offer_name_from(applied_offer),
        "redeem_discount": redeem_disc,
        "redeem_code": applied_redeem_code or "",
        "gst_amount": gst,
        "gst_rate": float(settings.get("gst_rate", 18.0)),
        "gst_type": settings.get("gst_type", "inclusive"),
        "taxable_amount": getattr(totals_detail, "taxable_amount", round(grand - gst, 2)),
        "gst_mode": getattr(totals_detail, "gst_mode", "global"),
        "gst_breakdown": getattr(totals_detail, "gst_breakdown", ()),
        "grand_total": grand,
        "timestamp": now.strftime("%Y-%m-%d %H:%M"),
    }


def build_pdf_path(
    *,
    bills_dir: str,
    invoice: str,
    customer_name: str,
    sanitize_filename: Callable[[str], str],
) -> str:
    safe_name = sanitize_filename(customer_name or "Guest")
    return os.path.join(bills_dir, f"{invoice}_{safe_name}.pdf")
