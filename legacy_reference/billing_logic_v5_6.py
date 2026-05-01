"""Focused V5 billing persistence helpers extracted from billing.py."""
from __future__ import annotations

import csv
import os

from adapters.billing_adapter import finalize_invoice_v5
from adapters.customer_adapter import use_v5_customers_db
from utils import F_REPORT, app_log, now_str


def _mirror_invoice_to_csv(
    invoice_no: str,
    customer_name: str,
    customer_phone: str,
    payment_method: str,
    final: float,
    total_discount: float,
    items_str: str,
) -> None:
    try:
        exists = os.path.exists(F_REPORT)
        with open(F_REPORT, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if not exists:
                w.writerow(["Date", "Invoice", "Name", "Phone", "Payment", "Total", "Discount", "Items"])
            w.writerow([
                now_str(),
                invoice_no,
                customer_name,
                customer_phone,
                payment_method,
                round(final, 2),
                round(total_discount, 2),
                items_str,
            ])
    except Exception as e:
        app_log(f"[billing v5 csv mirror] invoice={invoice_no} error={e}")


def save_report_v5(frame, final: float, disc: float, pts_disc: float,
                   offer_disc: float = 0.0, redeem_disc: float = 0.0,
                   mem_disc: float = 0.0):
    from billing import _auto_save_customer, _billing_record_visit, _billing_redeem_points
    from redeem_codes import apply_redeem_code

    if frame._current_invoice in getattr(frame, "_saved_invoices", set()):
        return

    items_str = "|".join(
        f"{it['mode']}~{it['name']}~{it['price']}~{it['qty']}"
        for it in frame.bill_items
    )
    ph = frame.phone_ent.get().strip()
    nm = frame.name_ent.get().strip()
    bd = frame.bday_ent.get().strip() if hasattr(frame, "bday_ent") else ""
    _auto_save_customer(ph, nm, bd)

    result = finalize_invoice_v5({
        "invoice_no": frame._current_invoice,
        "invoice_date": now_str(),
        "customer_phone": ph,
        "customer_name": nm,
        "gross_total": round(final + disc + mem_disc + pts_disc + offer_disc + redeem_disc, 2),
        "discount_total": round(disc + mem_disc + pts_disc + offer_disc + redeem_disc, 2),
        "tax_total": 0.0,
        "net_total": round(final, 2),
        "loyalty_earned": int(final // 100),
        "loyalty_redeemed": int(max(0.0, pts_disc)),
        "redeem_code": frame._applied_redeem_code or "",
        "notes": "Legacy billing cutover save",
        "created_by": frame.app.current_user.get("username", "") if getattr(frame.app, "current_user", None) else "",
        "items": [
            {
                "item_name": it["name"],
                "item_type": "product" if it.get("mode") == "products" else "service",
                "staff_name": it.get("staff", ""),
                "qty": it.get("qty", 1),
                "unit_price": it.get("price", 0),
                "line_total": round(it.get("price", 0) * it.get("qty", 1), 2),
                "discount_amount": 0.0,
                "inventory_item_name": (
                    it.get("inventory_item_name", it["name"])
                    if it.get("mode") == "products" else ""
                ),
                "variant_id": it.get("variant_id", 0),
            }
            for it in frame.bill_items
        ],
        "payments": [{
            "payment_method": frame.payment_var.get(),
            "amount": round(final, 2),
            "reference_no": "",
        }],
    })
    if not bool((result or {}).get("ok", False)):
        raise RuntimeError(f"Invoice save failed for {frame._current_invoice}")

    _mirror_invoice_to_csv(
        invoice_no=frame._current_invoice,
        customer_name=nm,
        customer_phone=ph,
        payment_method=frame.payment_var.get(),
        final=final,
        total_discount=(disc + mem_disc + pts_disc + offer_disc + redeem_disc),
        items_str=items_str,
    )

    if not use_v5_customers_db():
        if ph and ph not in ("0000000000", ""):
            _billing_record_visit(ph, frame._current_invoice, frame.bill_items, final, frame.payment_var.get())
        if frame.use_pts_var.get() and pts_disc > 0:
            _billing_redeem_points(ph, int(max(0.0, pts_disc)))
    if frame._applied_redeem_code:
        try:
            apply_redeem_code(frame._applied_redeem_code, frame._current_invoice, customer_phone=ph)
        except Exception:
            pass

    try:
        from cloud_sync import auto_sync
        auto_sync()
    except Exception:
        pass

    frame._saved_invoices.add(frame._current_invoice)
    frame._bill_completed = True

    # V5.6.1 Phase 1 — Activity log hook
    try:
        from activity_log import log_event
        billed_by = frame.app.current_user.get("username", "") if getattr(frame.app, "current_user", None) else ""
        log_event(
            "bill_created",
            entity="bill",
            entity_id=str(frame._current_invoice),
            user=billed_by,
            details={
                "customer": nm,
                "phone": ph,
                "total": round(final, 2),
                "payment": frame.payment_var.get(),
                "item_count": len(frame.bill_items),
            },
        )
    except Exception:
        pass

    try:
        frame.app.on_bill_saved()
    except Exception:
        pass
