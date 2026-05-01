from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from typing import Any, Callable


LogFn = Callable[[str], None]
NowFn = Callable[[], str]


@dataclass(frozen=True)
class SaveReportDependencies:
    finalize_invoice: Callable[[dict[str, Any]], dict[str, Any]]
    use_v5_customers_db: Callable[[], bool]
    auto_save_customer: Callable[[str, str, str], None]
    record_visit: Callable[[str, str, list[dict[str, Any]], float, str], None]
    redeem_points: Callable[[str, int], None]
    apply_redeem_code: Callable[..., None]
    auto_sync: Callable[[], None]
    log_event: Callable[..., None]
    now: NowFn
    app_log: LogFn


@dataclass(frozen=True)
class SaveLegacyReportDependencies:
    deduct_inventory_for_sale: Callable[[list[dict[str, Any]]], None]
    auto_save_customer: Callable[[str, str, str], None]
    record_visit: Callable[[str, str, list[dict[str, Any]], float, str], None]
    redeem_points: Callable[[str, int], None]
    apply_redeem_code: Callable[..., None]
    auto_sync: Callable[[], None]
    on_bill_saved: Callable[[], None]
    now: NowFn


def format_items_for_legacy_csv(items: list[dict[str, Any]]) -> str:
    segments = []
    for it in items:
        base = [it["mode"], it["name"], it["price"], it["qty"]]
        rich = [
            it.get("unit_type") or it.get("unit") or "",
            it.get("gst_rate", ""),
            it.get("cost_price", ""),
            it.get("category") or it.get("category_name") or "",
        ]
        if any(value not in ("", None) for value in rich):
            base.extend(rich)
        segments.append("~".join(str(value) for value in base))
    return "|".join(segments)


def build_invoice_payload(
    frame: Any,
    *,
    final: float,
    disc: float,
    pts_disc: float,
    offer_disc: float = 0.0,
    redeem_disc: float = 0.0,
    mem_disc: float = 0.0,
    now: NowFn,
) -> dict[str, Any]:
    customer_phone = frame.phone_ent.get().strip()
    customer_name = frame.name_ent.get().strip()
    billed_by = frame.app.current_user.get("username", "") if getattr(frame.app, "current_user", None) else ""
    total_discount = disc + mem_disc + pts_disc + offer_disc + redeem_disc

    return {
        "invoice_no": frame._current_invoice,
        "invoice_date": now(),
        "customer_phone": customer_phone,
        "customer_name": customer_name,
        "gross_total": round(final + total_discount, 2),
        "discount_total": round(total_discount, 2),
        "tax_total": 0.0,
        "net_total": round(final, 2),
        "loyalty_earned": int(final // 100),
        "loyalty_redeemed": int(max(0.0, pts_disc)),
        "redeem_code": frame._applied_redeem_code or "",
        "redeem_discount": round(redeem_disc, 2),
        "notes": "Legacy billing cutover save",
        "created_by": billed_by,
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
    }


def mirror_invoice_to_csv(
    *,
    report_path: str,
    invoice_no: str,
    customer_name: str,
    customer_phone: str,
    payment_method: str,
    final: float,
    total_discount: float,
    items_str: str,
    now: NowFn,
    app_log: LogFn,
) -> None:
    try:
        exists = os.path.exists(report_path)
        with open(report_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not exists:
                writer.writerow(["Date", "Invoice", "Name", "Phone", "Payment", "Total", "Discount", "Items"])
            writer.writerow([
                now(),
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


def save_report_v5_core(
    frame: Any,
    *,
    final: float,
    disc: float,
    pts_disc: float,
    report_path: str,
    deps: SaveReportDependencies,
    offer_disc: float = 0.0,
    redeem_disc: float = 0.0,
    mem_disc: float = 0.0,
) -> None:
    if frame._current_invoice in getattr(frame, "_saved_invoices", set()):
        return

    items_str = format_items_for_legacy_csv(frame.bill_items)
    customer_phone = frame.phone_ent.get().strip()
    customer_name = frame.name_ent.get().strip()
    birthday = frame.bday_ent.get().strip() if hasattr(frame, "bday_ent") else ""
    total_discount = disc + mem_disc + pts_disc + offer_disc + redeem_disc

    deps.auto_save_customer(customer_phone, customer_name, birthday)

    result = deps.finalize_invoice(build_invoice_payload(
        frame,
        final=final,
        disc=disc,
        pts_disc=pts_disc,
        offer_disc=offer_disc,
        redeem_disc=redeem_disc,
        mem_disc=mem_disc,
        now=deps.now,
    ))
    if not bool((result or {}).get("ok", False)):
        raise RuntimeError(f"Invoice save failed for {frame._current_invoice}")

    mirror_invoice_to_csv(
        report_path=report_path,
        invoice_no=frame._current_invoice,
        customer_name=customer_name,
        customer_phone=customer_phone,
        payment_method=frame.payment_var.get(),
        final=final,
        total_discount=total_discount,
        items_str=items_str,
        now=deps.now,
        app_log=deps.app_log,
    )

    if not deps.use_v5_customers_db():
        if customer_phone and customer_phone not in ("0000000000", ""):
            deps.record_visit(customer_phone, frame._current_invoice, frame.bill_items, final, frame.payment_var.get())
        if frame.use_pts_var.get() and pts_disc > 0:
            deps.redeem_points(customer_phone, int(max(0.0, pts_disc)))

    if frame._applied_redeem_code:
        try:
            deps.apply_redeem_code(frame._applied_redeem_code, frame._current_invoice, customer_phone=customer_phone)
        except Exception:
            pass

    try:
        deps.auto_sync()
    except Exception:
        pass

    frame._saved_invoices.add(frame._current_invoice)
    frame._bill_completed = True

    try:
        billed_by = frame.app.current_user.get("username", "") if getattr(frame.app, "current_user", None) else ""
        deps.log_event(
            "bill_created",
            entity="bill",
            entity_id=str(frame._current_invoice),
            user=billed_by,
            details={
                "customer": customer_name,
                "phone": customer_phone,
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


def save_report_legacy_core(
    frame: Any,
    *,
    final: float,
    disc: float,
    pts_disc: float,
    report_path: str,
    deps: SaveLegacyReportDependencies,
    offer_disc: float = 0.0,
    redeem_disc: float = 0.0,
    mem_disc: float = 0.0,
) -> None:
    if frame._current_invoice in getattr(frame, "_saved_invoices", set()):
        return
    frame._saved_invoices.add(frame._current_invoice)

    items_str = format_items_for_legacy_csv(frame.bill_items)
    exists = os.path.exists(report_path)
    billed_by = frame.app.current_user.get("username", "") if getattr(frame.app, "current_user", None) else ""
    total_discount = disc + mem_disc + pts_disc + offer_disc + redeem_disc

    with open(report_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not exists:
            writer.writerow(["Date", "Invoice", "Name", "Phone", "Payment", "Total", "Discount", "Items", "Created By"])
        writer.writerow([
            deps.now(),
            frame._current_invoice,
            frame.name_ent.get(),
            frame.phone_ent.get(),
            frame.payment_var.get(),
            round(final, 2),
            round(total_discount, 2),
            items_str,
            billed_by,
        ])

    try:
        deps.deduct_inventory_for_sale(frame.bill_items)
    except Exception:
        pass

    customer_phone = frame.phone_ent.get().strip()
    customer_name = frame.name_ent.get().strip()
    birthday = frame.bday_ent.get().strip() if hasattr(frame, "bday_ent") else ""
    deps.auto_save_customer(customer_phone, customer_name, birthday)

    if customer_phone and customer_phone not in ("0000000000", ""):
        deps.record_visit(customer_phone, frame._current_invoice, frame.bill_items, final, frame.payment_var.get())

    if frame.use_pts_var.get() and pts_disc > 0:
        deps.redeem_points(customer_phone, int(max(0.0, pts_disc)))

    if frame._applied_redeem_code:
        try:
            deps.apply_redeem_code(
                frame._applied_redeem_code,
                frame._current_invoice,
                customer_phone=customer_phone,
            )
        except Exception:
            pass

    try:
        deps.auto_sync()
    except Exception:
        pass

    try:
        deps.on_bill_saved()
    except Exception:
        pass
