"""
print_utils.py  –  BOBY'S Salon
Utility helpers for the print engine: text formatting,
image handling, line building, and validation.
"""
import os
from typing import List
from branding import get_invoice_branding


# ── Text formatting ────────────────────────────────────────────────────────

def trunc(text: str, width: int) -> str:
    """Truncate text to width characters."""
    return str(text)[:width]


def center_text(text: str, width: int) -> str:
    """Center text in fixed width field, truncating if too long."""
    t = str(text)[:width]
    return t.center(width)


def right_align(label: str, value: str, total_width: int,
                label_max: int = None) -> str:
    """
    Right-align a value with a left label in total_width chars.
    label_max: max chars for label (default: total_width - len(value) - 1)
    """
    value_str = str(value)
    if label_max is None:
        label_max = total_width - len(value_str) - 1
    label_max = max(1, label_max)
    lbl = str(label)[:label_max]
    return f"{lbl:>{label_max}} {value_str:>{total_width - label_max - 1}}"


def separator(char: str, width: int) -> str:
    """Build a separator line of given char and width."""
    return char * width


def blank_line() -> str:
    return ""


def wrap_text(text: str, width: int) -> List[str]:
    """Wrap text to fit within width, breaking at spaces."""
    words  = str(text).split()
    lines  = []
    current = ""
    for word in words:
        if len(current) + len(word) + (1 if current else 0) <= width:
            current = (current + " " + word).strip()
        else:
            if current:
                lines.append(current)
            current = word[:width]
    if current:
        lines.append(current)
    return lines or [""]


def clean_for_thermal(text: str) -> str:
    """Replace non-ASCII/thermal-unsafe chars with safe equivalents."""
    replacements = {
        "₹": "Rs.",
        "═": "=",
        "─": "-",
        "│": "|",
        "•": "*",
        "\u2019": "'",
        "\u2018": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2026": "...",
        "\u00a0": " ",
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    # Remove remaining non-ASCII
    return text.encode("ascii", errors="replace").decode("ascii")


def clean_for_pdf(text: str) -> str:
    """Replace chars that ReportLab cannot render in Helvetica/Courier."""
    return text.replace("₹", "Rs.").replace("\u2550", "=")


# ── Price / amount formatting ──────────────────────────────────────────────

def fmt_price(amount: float, symbol: str = "Rs.") -> str:
    return f"{symbol}{amount:,.2f}"


def fmt_price_compact(amount: float) -> str:
    """Short format: 1500.00 → 1500.00 (no comma for thermal)."""
    return f"{amount:.2f}"


# ── Image helpers ──────────────────────────────────────────────────────────

def load_logo_for_pdf(logo_path: str, max_width_pt: float,
                      max_height_pt: float = 50.0):
    """
    Load and scale logo for ReportLab.
    Returns (image_path, draw_width, draw_height) or None if unavailable.
    """
    if not logo_path or not os.path.exists(logo_path):
        return None
    try:
        from reportlab.lib.utils import ImageReader
        reader = ImageReader(logo_path)
        iw, ih = reader.getSize()
        if iw <= 0 or ih <= 0:
            return None
        # Scale to fit max_width
        scale   = min(max_width_pt / iw, max_height_pt / ih)
        draw_w  = iw * scale
        draw_h  = ih * scale
        return logo_path, draw_w, draw_h
    except Exception as e:
        try:
            from utils import app_log
            app_log(f"[print_utils logo] {e}")
        except Exception:
            pass
        return None


def logo_to_ascii_art(logo_path: str, width_chars: int = 32) -> str:
    """
    For thermal printers: return a simple text placeholder if logo
    can't be rendered (most thermal drivers don't support images via RAW).
    """
    name = os.path.splitext(os.path.basename(logo_path))[0].upper()
    return center_text(f"[ {name} ]", width_chars)


# ── Bill section builders ──────────────────────────────────────────────────

def build_header_lines(salon_name: str, address: str, phone: str,
                       gst_no: str, width: int, settings: dict) -> List[str]:
    """Build header section lines based on settings."""
    lines = []

    if settings.get("show_logo", False) and settings.get("logo_path", ""):
        logo_path = settings["logo_path"]
        if os.path.exists(logo_path):
            lines.append(logo_to_ascii_art(logo_path, width))
        # For thermal: just a text placeholder — actual image in PDF

    if settings.get("show_shop_name", True):
        lines.append(center_text(salon_name, width))

    if settings.get("show_address", True) and address:
        for ln in wrap_text(address, width):
            lines.append(center_text(ln, width))

    if settings.get("show_phone", True) and phone:
        lines.append(center_text(f"Ph: {phone}", width))

    if settings.get("show_gst_no", False) and gst_no:
        lines.append(center_text(f"GST: {gst_no}", width))

    return lines


def build_invoice_lines(invoice: str, date_str: str, time_str: str,
                        width: int, settings: dict) -> List[str]:
    """Build invoice number + date/time lines."""
    lines = []

    if settings.get("show_invoice_number", True) and invoice:
        lines.append(f"INV: {invoice}")

    date_line = ""
    if settings.get("show_date", True):
        date_line += date_str
    if settings.get("show_time", True):
        sep = "   " if date_line else ""
        date_line += sep + time_str
    if date_line:
        lines.append(date_line)

    return lines


def build_customer_lines(customer_name: str, customer_phone: str,
                         payment: str, width: int,
                         settings: dict) -> List[str]:
    """Build customer info lines."""
    lines = []

    if settings.get("show_customer_name", True) and customer_name:
        lines.append(f"Customer: {trunc(customer_name, width - 10)}")

    if settings.get("show_customer_phone", True) and customer_phone:
        lines.append(f"Phone   : {customer_phone}")

    if settings.get("show_payment_method", True) and payment:
        lines.append(f"Payment : {payment}")

    return lines


def _format_bill_qty(qty) -> str:
    try:
        value = float(qty)
    except Exception:
        return str(qty or "1")
    if value.is_integer():
        return str(int(value))
    return f"{value:.3f}".rstrip("0").rstrip(".")


def build_item_line_58mm(idx: int, name: str, qty: float,
                          price: float, width: int,
                          numbered: bool, qty_label: str | None = None) -> List[str]:
    """Build 2-line item format for 58mm thermal (32 chars)."""
    prefix = f"{idx}. " if numbered else ""
    nm     = trunc(prefix + name, width)
    qty_value = float(qty)
    qty_text = qty_label or _format_bill_qty(qty)
    amt    = price * qty_value
    qty_ln = f"  {qty_text} x {fmt_price_compact(price)}"
    amt_ln = f"{amt:>9.2f}"
    pad    = width - len(amt_ln)
    return [nm, f"{qty_ln:<{pad}}{amt_ln}"]


def build_item_line_80mm(idx: int, name: str, qty: float,
                          price: float, width: int,
                          numbered: bool, qty_label: str | None = None) -> str:
    """Build single-line item format for 80mm thermal (42 chars)."""
    prefix = f"{idx}. " if numbered else ""
    qty_value = float(qty)
    qty_text = qty_label or _format_bill_qty(qty)
    qty_width = max(2, min(8, len(qty_text)))
    name_width = width - qty_width - 11
    nm     = trunc(prefix + name, name_width)
    amt    = price * qty_value
    return f"{nm:<{name_width}} {qty_text:>{qty_width}} {amt:>9.2f}"


def build_item_line_a4(idx: int, name: str, qty: float,
                        price: float, width: int,
                        numbered: bool, qty_label: str | None = None) -> str:
    """Build 4-column item format for A4 (80 chars)."""
    prefix = f"{idx}. " if numbered else ""
    qty_value = float(qty)
    qty_text = qty_label or _format_bill_qty(qty)
    qty_width = max(4, min(10, len(qty_text)))
    nw     = width - qty_width - 23
    nm     = trunc(prefix + name, nw)
    amt    = price * qty_value
    return f"{nm:<{nw}} {qty_text:>{qty_width}} {price:>9.2f} {amt:>10.2f}"


def build_totals_lines(subtotal: float, discount: float,
                       mem_discount: float, mem_pct: int,
                       pts_discount: float,
                       offer_discount: float, offer_name: str,
                       redeem_discount: float, redeem_code: str,
                       gst_amount: float, gst_rate: float, gst_type: str,
                       grand_total: float, width: int,
                       settings: dict,
                       gst_breakdown: list | tuple | None = None,
                       taxable_amount: float | None = None,
                       gst_mode: str = "global") -> List[str]:
    """Build totals section lines driven by settings."""
    lines = []

    if width <= 32:
        lw = width - 9
    elif width <= 42:
        lw = width - 10
    else:
        lw = width - 12

    has_any_discount = any([
        discount > 0     and settings.get("show_discount"),
        mem_discount > 0 and settings.get("show_membership_discount"),
        pts_discount > 0 and settings.get("show_loyalty_points"),
        offer_discount > 0 and settings.get("show_offer_discount"),
        redeem_discount > 0,
        gst_amount > 0   and settings.get("show_gst"),
    ])

    if settings.get("show_subtotal", True) and has_any_discount:
        lines.append(right_align("Sub Total", f"{subtotal:.2f}", width, lw))

    if settings.get("show_discount", True) and discount > 0:
        lines.append(right_align("Discount (-)", f"{discount:.2f}", width, lw))

    if settings.get("show_membership_discount", True) and mem_discount > 0:
        lbl = f"Mem {mem_pct}% (-)" if width <= 32 else f"Member {mem_pct}% (-)"
        lines.append(right_align(lbl, f"{mem_discount:.2f}", width, lw))

    if settings.get("show_loyalty_points", True) and pts_discount > 0:
        lines.append(right_align("Points (-)", f"{pts_discount:.2f}", width, lw))

    if settings.get("show_offer_discount", True) and offer_discount > 0:
        oname = trunc(offer_name or "Offer", 14)
        lines.append(right_align(f"{oname} (-)", f"{offer_discount:.2f}", width, lw))

    if redeem_discount > 0:
        rc = trunc(redeem_code or "Code", 10)
        lines.append(right_align(f"Redeem (-)", f"{redeem_discount:.2f}", width, lw))

    breakdown = tuple(gst_breakdown or ())
    if settings.get("show_gst", True) and gst_amount > 0:
        base = taxable_amount if taxable_amount is not None else grand_total - gst_amount
        lines.append(right_align("Taxable Amt", f"{base:.2f}", width, lw))
        if breakdown and (len(breakdown) > 1 or gst_mode != "global"):
            for group in breakdown:
                rate = getattr(group, "rate", None)
                amount = getattr(group, "gst_amount", 0.0)
                if rate is None:
                    continue
                lines.append(right_align(f"GST {int(round(float(rate)))}%", f"{float(amount):.2f}", width, lw))
            lines.append(right_align("GST Total", f"{gst_amount:.2f}", width, lw))
        else:
            gtype   = "Incl" if gst_type == "inclusive" else "Excl"
            gst_lbl = f"GST {int(gst_rate)}% ({gtype})"
            lines.append(right_align(gst_lbl, f"{gst_amount:.2f}", width, lw))

    if settings.get("show_grand_total", True):
        if settings.get("double_width_total", True):
            lines.append(center_text(f"TOTAL: Rs.{grand_total:.2f}", width))
        else:
            lines.append(right_align("GRAND TOTAL", f"{grand_total:.2f}", width, lw))

    return lines


# ── Validation ─────────────────────────────────────────────────────────────

def validate_print_settings(ps: dict) -> List[str]:
    """
    Validate print settings. Returns list of warning strings.
    Empty list means all good.
    """
    warnings = []

    template = ps.get("template", "")
    valid_templates = {"thermal_58mm", "thermal_80mm", "a4_standard"}
    if template not in valid_templates:
        warnings.append(f"Unknown template '{template}'. "
                        f"Valid: {valid_templates}")

    width = ps.get("printer_width", 32)
    if not isinstance(width, int) or width < 16 or width > 120:
        warnings.append(f"printer_width {width} out of range (16–120).")

    if ps.get("show_logo") and not ps.get("logo_path"):
        warnings.append("show_logo=true but logo_path is empty.")

    logo_path = ps.get("logo_path", "")
    if logo_path and not os.path.exists(logo_path):
        warnings.append(f"logo_path '{logo_path}' does not exist.")

    return warnings


def simulate_settings_cases():
    """
    Simulate 3 test cases as per spec — returns list of (case_name, text).
    Used in print_templates.py tests.
    """
    from print_engine import BillData, generate_thermal_text

    demo_bill = BillData(
        invoice="INV-202603-00001",
        salon_name=get_invoice_branding()["header"],
        address=get_invoice_branding()["address"] or "Kerala, India",
        phone=get_invoice_branding()["phone"] or "9999999999",
        gst_no="",
        customer_name="Priya Menon",
        customer_phone="9012345678",
        payment_method="Cash",
        svc_items=[
            {"mode": "services", "name": "Hair Spa", "price": 800, "qty": 1},
            {"mode": "services", "name": "Facial",   "price": 600, "qty": 1},
        ],
        prd_items=[
            {"mode": "products", "name": "Shampoo", "price": 200, "qty": 2},
        ],
        subtotal=1800.0,
        discount=100.0,
        grand_total=1700.0,
        timestamp="2026-03-20 14:30",
    )

    results = []

    # Case 1: Minimal — no logo, no time, only total
    case1 = {
        "template": "thermal_58mm", "printer_width": 32,
        "show_logo": False, "show_shop_name": True,
        "show_address": False, "show_phone": False, "show_gst_no": False,
        "show_invoice_number": False, "show_date": True, "show_time": False,
        "show_customer_name": False, "show_customer_phone": False,
        "show_payment_method": False, "show_item_numbering": False,
        "show_item_code": False, "show_services_section": True,
        "show_products_section": True, "show_subtotal": False,
        "show_discount": False, "show_membership_discount": False,
        "show_loyalty_points": False, "show_offer_discount": False,
        "show_gst": False, "show_grand_total": True, "show_footer": False,
        "show_separator_lines": True, "double_width_total": True,
    }
    results.append(("Case 1 — Minimal", generate_thermal_text(demo_bill, case1)))

    # Case 2: Full details
    case2 = {
        "template": "thermal_80mm", "printer_width": 42,
        "show_logo": False, "show_shop_name": True,
        "show_address": True, "show_phone": True, "show_gst_no": False,
        "show_invoice_number": True, "show_date": True, "show_time": True,
        "show_customer_name": True, "show_customer_phone": True,
        "show_payment_method": True, "show_item_numbering": True,
        "show_item_code": False, "show_services_section": True,
        "show_products_section": True, "show_subtotal": True,
        "show_discount": True, "show_membership_discount": True,
        "show_loyalty_points": True, "show_offer_discount": True,
        "show_gst": False, "show_grand_total": True,
        "show_footer": True, "footer_text": "Thank You!",
        "show_separator_lines": True, "double_width_total": False,
    }
    results.append(("Case 2 — Full Details", generate_thermal_text(demo_bill, case2)))

    # Case 3: Minimal thermal
    case3 = {
        "template": "thermal_58mm", "printer_width": 32,
        "show_logo": False, "show_shop_name": True,
        "show_address": False, "show_phone": True, "show_gst_no": False,
        "show_invoice_number": True, "show_date": True, "show_time": True,
        "show_customer_name": True, "show_customer_phone": False,
        "show_payment_method": True, "show_item_numbering": False,
        "show_item_code": False, "show_services_section": True,
        "show_products_section": False, "show_subtotal": False,
        "show_discount": True, "show_membership_discount": False,
        "show_loyalty_points": False, "show_offer_discount": False,
        "show_gst": False, "show_grand_total": True,
        "show_footer": True, "footer_text": "Visit Again!",
        "show_separator_lines": True, "double_width_total": True,
    }
    results.append(("Case 3 — Receipt", generate_thermal_text(demo_bill, case3)))

    return results
