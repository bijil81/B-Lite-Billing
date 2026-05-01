"""Bill preview text builder used by Reports."""
from __future__ import annotations

from datetime import datetime
from ast import literal_eval
from typing import Any


WIDTH = 52


def _line(text: str = "") -> str:
    return f"{text}\n"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _format_qty(value: Any) -> str:
    qty = _safe_float(value, 1.0)
    if qty.is_integer():
        return str(int(qty))
    return f"{qty:.3f}".rstrip("0").rstrip(".")


def _load_settings(settings: dict[str, Any] | None) -> dict[str, Any]:
    if settings is not None:
        return settings
    from salon_settings import get_settings

    return get_settings()


def _load_branding(invoice_branding: dict[str, Any] | None) -> dict[str, Any]:
    if invoice_branding is not None:
        return invoice_branding
    from branding import get_invoice_branding

    return get_invoice_branding()


def _parse_report_items(items_raw: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    service_items: list[dict[str, Any]] = []
    product_items: list[dict[str, Any]] = []
    if not items_raw or not items_raw.strip():
        return service_items, product_items

    for segment in items_raw.split("|"):
        segment = segment.strip()
        if not segment:
            continue

        parts = segment.split("~")
        if len(parts) >= 4:
            try:
                mode = parts[0].strip()
                item = {
                    "mode": mode,
                    "name": parts[1].strip(),
                    "price": float(parts[2].strip()),
                    "qty": float(parts[3].strip()),
                }
            except (TypeError, ValueError):
                item = None
            if item:
                if mode == "services":
                    service_items.append(item)
                else:
                    product_items.append(item)
                continue

        old_parts = segment.split(":")
        if len(old_parts) == 2:
            try:
                service_items.append({
                    "mode": "services",
                    "name": old_parts[0].strip(),
                    "price": float(old_parts[1].strip()),
                    "qty": 1.0,
                })
            except (TypeError, ValueError):
                pass

    return service_items, product_items


def _parse_gst_breakdown(raw: Any) -> list[dict[str, Any]]:
    if not raw:
        return []
    if isinstance(raw, (list, tuple)):
        parsed: list[dict[str, Any]] = []
        for entry in raw:
            if isinstance(entry, dict):
                parsed.append(entry)
        return parsed
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return []
        try:
            value = literal_eval(text)
        except Exception:
            return []
        return _parse_gst_breakdown(value)
    return []


def _format_section(items: list[dict[str, Any]], title: str) -> str:
    text = _line(f"{title:^{WIDTH}}")
    text += _line("-" * WIDTH)
    text += _line(f"{'Item':<{WIDTH-32}} {'Qty':>4} {'Rate':>9} {'Amt':>10}")
    text += _line("-" * WIDTH)
    for item in items:
        name = str(item.get("name", ""))[: WIDTH - 32]
        price = _safe_float(item.get("price"))
        qty = _safe_float(item.get("qty"), 1.0)
        amount = price * qty
        text += _line(f"{name:<{WIDTH-32}} {_format_qty(qty):>4} {price:>9.2f} {amount:>10.2f}")
    return text


def build_bill_text(
    row: dict[str, Any],
    *,
    settings: dict[str, Any] | None = None,
    invoice_branding: dict[str, Any] | None = None,
) -> str:
    """Reconstruct a printable bill preview from a report row."""
    cfg = _load_settings(settings)
    branding = _load_branding(invoice_branding)
    business_name = cfg.get("salon_name") or branding.get("header", "B-Lite")
    address = cfg.get("address", "Kollam, Kerala")
    gst_no = cfg.get("gst_no", "")

    service_items, product_items = _parse_report_items(str(row.get("items_raw", "")))
    gst_breakdown = _parse_gst_breakdown(row.get("gst_breakdown"))
    service_subtotal = sum(_safe_float(item.get("price")) * _safe_float(item.get("qty"), 1.0) for item in service_items)
    product_subtotal = sum(_safe_float(item.get("price")) * _safe_float(item.get("qty"), 1.0) for item in product_items)
    total = service_subtotal + product_subtotal
    discount = _safe_float(row.get("discount", 0.0))
    grand_total = max(0.0, total - discount)
    gst_total = _safe_float(row.get("gst_amount", row.get("tax_total", 0.0)))
    taxable_amount = _safe_float(row.get("taxable_amount", grand_total - gst_total))

    raw_date = str(row.get("date", ""))
    try:
        date_obj = datetime.strptime(raw_date[:16], "%Y-%m-%d %H:%M")
        date_text = date_obj.strftime("%d-%m-%Y")
        time_text = date_obj.strftime("%I:%M %p")
    except Exception:
        date_text = raw_date[:10]
        time_text = ""

    text = _line(f"{business_name:^{WIDTH}}")
    text += _line(f"{address:^{WIDTH}}")
    if gst_no:
        text += _line(f"GST: {gst_no}")
    text += _line("=" * WIDTH)
    text += _line(f"Invoice : {str(row.get('invoice', '')):<14}  {date_text}")
    if time_text:
        text += _line(f"Time    : {time_text}")
    text += _line("-" * WIDTH)
    text += _line(f"Customer: {row.get('name', '')}")
    text += _line(f"Phone   : {row.get('phone', '')}")
    text += _line(f"Payment : {row.get('payment', '')}")
    text += _line("=" * WIDTH)

    subtotal_width = WIDTH - 12

    if service_items:
        text += _format_section(service_items, "SERVICES")
        text += _line("-" * WIDTH)
        text += _line(f"{'Services Subtotal':>{subtotal_width}} {service_subtotal:>10.2f}")

    if product_items:
        text += _line("=" * WIDTH)
        text += _format_section(product_items, "PRODUCTS")
        text += _line("-" * WIDTH)
        text += _line(f"{'Products Subtotal':>{subtotal_width}} {product_subtotal:>10.2f}")

    text += _line("=" * WIDTH)
    if discount > 0:
        text += _line(f"{'Sub Total':>{subtotal_width}} {total:>10.2f}")
        text += _line(f"{'Discount (-)':>{subtotal_width}} {discount:>10.2f}")
    text += _line("=" * WIDTH)
    if gst_breakdown and gst_total > 0:
        text += _line(f"{'Taxable Amt':>{subtotal_width}} {taxable_amount:>10.2f}")
        for entry in gst_breakdown:
            try:
                rate = float(entry.get("rate", 0))
                amount = float(entry.get("gst_amount", 0))
            except Exception:
                continue
            text += _line(f"{f'GST {int(round(rate))}%':>{subtotal_width}} {amount:>10.2f}")
        text += _line(f"{'GST Total':>{subtotal_width}} {gst_total:>10.2f}")
    text += _line(f"{'GRAND TOTAL':>{subtotal_width}} {grand_total:>10.2f}")
    text += _line("=" * WIDTH)
    text += _line()
    text += _line(f"{cfg.get('bill_footer', 'Thank You! Visit Again'):^{WIDTH}}")
    return text
