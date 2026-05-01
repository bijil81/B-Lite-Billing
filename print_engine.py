"""
print_engine.py  –  BOBY'S Salon
Dynamic, settings-driven bill generation engine.
Supports: thermal_58mm | thermal_80mm | a4_standard

Architecture
------------
  Section builders   → build_header / build_invoice_info / build_customer /
                        build_items / build_summary / build_footer
  Template renderers → generate_thermal_58mm / generate_thermal_80mm /
                        generate_a4_standard
  Unified dispatcher → generate_bill(template, settings, bill_data)
  Legacy API kept    → generate_thermal_text / generate_bill_pdf /
                        generate_bill_preview_text   (billing.py unchanged)

All sections honour print_settings — disabled sections produce ZERO lines.
"""

import os
from datetime import datetime

from utils import DATA_DIR, load_json, save_json, safe_float, fmt_currency
from branding import get_branding_logo_path, get_invoice_branding
from print_utils import (
    center_text, right_align, trunc, separator, wrap_text,
    clean_for_thermal, fmt_price_compact,
    build_header_lines, build_invoice_lines, build_customer_lines,
    build_item_line_58mm, build_item_line_80mm, build_item_line_a4,
    build_totals_lines, load_logo_for_pdf, logo_to_ascii_art,
)
from src.blite_v6.billing.cart_operations import format_cart_quantity_label

# ── Settings file ──────────────────────────────────────────────────────────
F_PRINT_SETTINGS = os.path.join(DATA_DIR, "print_settings.json")

PRINT_DEFAULTS: dict = {
    "template":                 "thermal_58mm",
    "printer_width":            32,
    "show_logo":                False,
    "logo_path":                get_branding_logo_path("invoice"),
    "logo_max_width":           200,
    "show_shop_name":           True,
    "show_address":             True,
    "show_phone":               True,
    "show_gst_no":              False,
    "show_invoice_number":      True,
    "show_date":                True,
    "show_time":                True,
    "show_customer_name":       True,
    "show_customer_phone":      True,
    "show_payment_method":      True,
    "show_item_numbering":      False,
    "show_item_code":           False,
    "show_services_section":    True,
    "show_products_section":    True,
    "show_subtotal":            True,
    "show_discount":            True,
    "show_membership_discount": True,
    "show_loyalty_points":      True,
    "show_offer_discount":      True,
    "show_gst":                 True,
    "show_grand_total":         True,
    "show_footer":              True,
    "footer_text":              get_invoice_branding()["footer"],
    "show_separator_lines":     True,
    "double_width_total":       True,
}

TEMPLATE_WIDTHS: dict = {
    "thermal_58mm":     32,
    "thermal_72mm":     38,
    "thermal_76mm":     40,
    "thermal_80mm":     42,
    "thermal_112mm":    60,
    "a5_halfpage":      62,
    "a4_standard":      80,
    "invoice_compact":  42,
    "invoice_detailed": 80,
}

# Human-readable labels for printer template dropdown
TEMPLATE_LABELS: dict = {
    "thermal_58mm":     "Thermal 58mm (Default)",
    "thermal_72mm":     "Thermal 72mm",
    "thermal_76mm":     "Thermal 76mm",
    "thermal_80mm":     "Thermal 80mm",
    "thermal_112mm":    "Thermal 112mm (Kitchen)",
    "a5_halfpage":      "A5 Half Page",
    "a4_standard":      "A4 Standard",
    "invoice_compact":  "Invoice Compact",
    "invoice_detailed": "Invoice Detailed",
}

# Map template to page width in mm for PDF generation
TEMPLATE_PAGE_WIDTH_MM: dict = {
    "thermal_58mm":     58,
    "thermal_72mm":     72,
    "thermal_76mm":     76,
    "thermal_80mm":     80,
    "thermal_112mm":    112,
    "a5_halfpage":      148,
    "a4_standard":      210,
    "invoice_compact":  80,
    "invoice_detailed": 210,
}


# ── Settings helpers ───────────────────────────────────────────────────────

def get_print_settings() -> dict:
    """Load print settings, merging with defaults for any missing keys."""
    saved = load_json(F_PRINT_SETTINGS, {})
    return {**PRINT_DEFAULTS, **saved}


def save_print_settings(data: dict) -> bool:
    merged = {**PRINT_DEFAULTS, **data}
    return save_json(F_PRINT_SETTINGS, merged)


def _get_width(ps: dict) -> int:
    tmpl = ps.get("template", "thermal_58mm")
    return TEMPLATE_WIDTHS.get(tmpl, ps.get("printer_width", 32))


# ═══════════════════════════════════════════════════════════════════════════
#  BILL DATA  (unchanged public API)
# ═══════════════════════════════════════════════════════════════════════════

class BillData:
    """
    Unified bill data passed to the engine.
    Decouples billing.py from print logic.
    """
    def __init__(self,
                 invoice:        str   = "",
                 salon_name:     str   = "",
                 address:        str   = "",
                 phone:          str   = "",
                 gst_no:         str   = "",
                 customer_name:  str   = "",
                 customer_phone: str   = "",
                 payment_method: str   = "Cash",
                 svc_items:      list  = None,
                 prd_items:      list  = None,
                 subtotal:       float = 0.0,
                 discount:       float = 0.0,
                 mem_discount:   float = 0.0,
                 mem_pct:        int   = 0,
                 pts_discount:   float = 0.0,
                 offer_discount: float = 0.0,
                 offer_name:     str   = "",
                 redeem_discount:float = 0.0,
                 redeem_code:    str   = "",
                 gst_amount:     float = 0.0,
                 gst_rate:       float = 18.0,
                 gst_type:       str   = "inclusive",
                 taxable_amount: float = 0.0,
                 gst_mode:       str   = "global",
                 gst_breakdown:  list = None,
                 grand_total:    float = 0.0,
                 timestamp:      str   = ""):
        self.invoice         = invoice
        self.salon_name      = salon_name or get_invoice_branding()["header"]
        self.address         = address
        self.phone           = phone
        self.gst_no          = gst_no
        self.customer_name   = customer_name
        self.customer_phone  = customer_phone
        self.payment_method  = payment_method
        self.svc_items       = svc_items or []
        self.prd_items       = prd_items or []
        self.subtotal        = subtotal
        self.discount        = discount
        self.mem_discount    = mem_discount
        self.mem_pct         = mem_pct
        self.pts_discount    = pts_discount
        self.offer_discount  = offer_discount
        self.offer_name      = offer_name
        self.redeem_discount = redeem_discount
        self.redeem_code     = redeem_code
        self.gst_amount      = gst_amount
        self.gst_rate        = gst_rate
        self.gst_type        = gst_type
        self.taxable_amount  = taxable_amount
        self.gst_mode        = gst_mode
        self.gst_breakdown   = tuple(gst_breakdown or [])
        self.grand_total     = grand_total
        self.timestamp       = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M")


# ═══════════════════════════════════════════════════════════════════════════
#  SECTION BUILDERS
#  Each returns list[str]. Returns [] if the section is disabled.
#  No blank lines, no gaps for disabled sections.
# ═══════════════════════════════════════════════════════════════════════════

def build_header(bill: BillData, ps: dict, W: int) -> list:
    """
    Logo (ASCII art for thermal), shop name, address, phone, GST number.
    Calls print_utils.build_header_lines — already settings-aware.
    """
    return build_header_lines(
        salon_name = bill.salon_name,
        address    = bill.address,
        phone      = bill.phone,
        gst_no     = bill.gst_no,
        width      = W,
        settings   = ps,
    )


def build_invoice_info(bill: BillData, ps: dict, W: int) -> list:
    """
    Invoice number, date, time.
    Calls print_utils.build_invoice_lines — already settings-aware.
    """
    try:
        now = datetime.strptime(bill.timestamp[:16], "%Y-%m-%d %H:%M")
    except Exception:
        now = datetime.now()
    return build_invoice_lines(
        invoice  = bill.invoice,
        date_str = now.strftime("%d-%m-%Y"),
        time_str = now.strftime("%I:%M %p"),
        width    = W,
        settings = ps,
    )


def build_customer(bill: BillData, ps: dict, W: int) -> list:
    """
    Customer name, phone, payment method.
    Calls print_utils.build_customer_lines — already settings-aware.
    """
    return build_customer_lines(
        customer_name  = bill.customer_name,
        customer_phone = bill.customer_phone,
        payment        = bill.payment_method,
        width          = W,
        settings       = ps,
    )


def build_items(bill: BillData, ps: dict, W: int) -> list:
    """
    Services + Products sections with unified item counter.
    Numbering (1. 2. 3.) applied to BOTH sections when show_item_numbering=True.
    Disabled section → zero lines, zero gaps.
    """
    show_sep = ps.get("show_separator_lines", True)
    thin     = separator("-", W) if show_sep else ""
    thick    = separator("=", W) if show_sep else ""
    numbered = ps.get("show_item_numbering", False)
    counter  = [0]   # shared across services + products for continuous numbering

    def _fmt_section(items: list, title: str) -> list:
        sec = [center_text(title, W)]
        # Column header for wider formats
        if W <= 32:
            if thin:
                sec.append(thin)
        elif W <= 42:
            if thin:
                sec.append(thin)
            sec.append(f"{'Item':<{W - 21}} {'Q':>2} {'Amt':>9}")
            if thin:
                sec.append(thin)
        else:
            nw = W - 27
            if thin:
                sec.append(thin)
            sec.append(f"{'Item':<{nw}} {'Qty':>4} {'Rate':>9} {'Amt':>10}")
            if thin:
                sec.append(thin)

        for it in items:
            counter[0] += 1
            name  = str(it.get("name", ""))
            qty   = float(it.get("qty", 1))
            qty_label = format_cart_quantity_label(it)
            price = float(it.get("price", 0.0))
            if W <= 32:
                sec.extend(
                    build_item_line_58mm(counter[0], name, qty, price, W, numbered, qty_label)
                )
            elif W <= 42:
                sec.append(
                    build_item_line_80mm(counter[0], name, qty, price, W, numbered, qty_label)
                )
            else:
                sec.append(
                    build_item_line_a4(counter[0], name, qty, price, W, numbered, qty_label)
                )
        return sec

    svc_block: list = []
    prd_block: list = []

    if ps.get("show_services_section", True) and bill.svc_items:
        svc_block = _fmt_section(bill.svc_items, "SERVICES")

    if ps.get("show_products_section", True) and bill.prd_items:
        prd_block = _fmt_section(bill.prd_items, "PRODUCTS")

    result: list = []
    result.extend(svc_block)
    if svc_block and prd_block and thick:
        result.append(thick)
    result.extend(prd_block)
    return result


def build_summary(bill: BillData, ps: dict, W: int) -> list:
    """
    Subtotal, discounts, GST, grand total.
    Calls print_utils.build_totals_lines — already settings-aware.
    """
    return build_totals_lines(
        subtotal        = bill.subtotal,
        discount        = bill.discount,
        mem_discount    = bill.mem_discount,
        mem_pct         = bill.mem_pct,
        pts_discount    = bill.pts_discount,
        offer_discount  = bill.offer_discount,
        offer_name      = bill.offer_name,
        redeem_discount = bill.redeem_discount,
        redeem_code     = bill.redeem_code,
        gst_amount      = bill.gst_amount,
        gst_rate        = bill.gst_rate,
        gst_type        = bill.gst_type,
        grand_total     = bill.grand_total,
        width           = W,
        settings        = ps,
        gst_breakdown   = bill.gst_breakdown,
        taxable_amount  = bill.taxable_amount,
        gst_mode        = bill.gst_mode,
    )


def build_footer(bill: BillData, ps: dict, W: int) -> list:
    """Footer message. Returns [] when show_footer=False."""
    if not ps.get("show_footer", True):
        return []
    text = ps.get("footer_text", get_invoice_branding()["footer"]) or get_invoice_branding()["footer"]
    return [center_text(trunc(text, W), W)]


# ═══════════════════════════════════════════════════════════════════════════
#  INTERNAL THERMAL RENDERER
#  Assembles sections with smart separators — no gaps for disabled sections.
# ═══════════════════════════════════════════════════════════════════════════

def _render_thermal(bill: BillData, ps: dict, W: int) -> str:
    """
    Core composer for all thermal / text-based templates.
    Separators appear only between present (non-empty) sections.
    All lines are cleaned for thermal (non-ASCII replaced).
    """
    show_sep = ps.get("show_separator_lines", True)
    SEP      = separator("=", W) if show_sep else ""
    THIN     = separator("-", W) if show_sep else ""

    # ── Collect each section ──────────────────────────────────────────────
    hdr   = build_header(bill, ps, W)
    inv   = build_invoice_info(bill, ps, W)
    cust  = build_customer(bill, ps, W)
    items = build_items(bill, ps, W)
    summ  = build_summary(bill, ps, W)
    foot  = build_footer(bill, ps, W)

    # ── Assemble: separator only between two PRESENT sections ─────────────
    parts: list = []

    #  Header → SEP → Invoice
    if hdr:
        parts.extend(hdr)
        next_present = inv or cust or items or summ or foot
        if SEP and next_present:
            parts.append(SEP)

    #  Invoice → THIN → Customer / Items
    if inv:
        parts.extend(inv)
        next_present = cust or items or summ or foot
        if THIN and next_present:
            parts.append(THIN)

    #  Customer → SEP → Items / Summary
    if cust:
        parts.extend(cust)
        next_present = items or summ or foot
        if SEP and next_present:
            parts.append(SEP)

    #  Items block (separators between services/products handled inside build_items)
    if items:
        parts.extend(items)

    #  SEP → Summary → THIN before grand total → SEP
    if summ:
        if SEP and (hdr or inv or cust or items):
            parts.append(SEP)
        # Split: all discount lines first, then THIN, then grand total (last line)
        if ps.get("show_grand_total", True) and THIN and len(summ) > 1:
            parts.extend(summ[:-1])
            parts.append(THIN)
            parts.append(summ[-1])
        else:
            parts.extend(summ)
        if SEP:
            parts.append(SEP)

    #  Footer (no leading blank — separator above is enough)
    if foot:
        parts.extend(foot)

    # ── Clean for thermal output ──────────────────────────────────────────
    return "\n".join(clean_for_thermal(ln) for ln in parts)


# ═══════════════════════════════════════════════════════════════════════════
#  TEMPLATE FUNCTIONS  (public, named by paper size)
# ═══════════════════════════════════════════════════════════════════════════

def generate_thermal_58mm(bill: BillData, ps: dict = None) -> str:
    """
    Generate 58mm thermal receipt text (32 chars wide).
    Forces width=32 regardless of ps['printer_width'].
    """
    if ps is None:
        ps = get_print_settings()
    effective = {**ps, "printer_width": 32, "template": "thermal_58mm"}
    return _render_thermal(bill, effective, 32)


def generate_thermal_80mm(bill: BillData, ps: dict = None) -> str:
    """
    Generate 80mm thermal receipt text (42 chars wide).
    Forces width=42 regardless of ps['printer_width'].
    """
    if ps is None:
        ps = get_print_settings()
    effective = {**ps, "printer_width": 42, "template": "thermal_80mm"}
    return _render_thermal(bill, effective, 42)


def generate_a4_standard(bill: BillData, ps: dict = None) -> str:
    """
    Generate A4 text layout (80 chars wide) — text preview only.
    For actual A4 PDF use generate_a4_pdf().
    """
    if ps is None:
        ps = get_print_settings()
    effective = {**ps, "printer_width": 80, "template": "a4_standard"}
    return _render_thermal(bill, effective, 80)


def generate_bill(template: str, settings: dict, bill_data: BillData) -> str:
    """
    Unified text-generation entry point.

    Args:
        template  : 'thermal_58mm' | 'thermal_72mm' | 'thermal_76mm' |
                    'thermal_80mm' | 'thermal_112mm' | 'a5_halfpage' |
                    'a4_standard' | 'invoice_compact' | 'invoice_detailed'
        settings  : print settings dict (merged with PRINT_DEFAULTS internally)
        bill_data : BillData instance

    Returns:
        Receipt text string (monospace, newline-separated).
    """
    effective = {**PRINT_DEFAULTS, **settings, "template": template}
    if template == "thermal_80mm" or template == "invoice_compact":
        return generate_thermal_80mm(bill_data, effective)
    elif template in ("a4_standard", "a5_halfpage", "invoice_detailed"):
        return generate_a4_standard(bill_data, effective)
    elif template == "thermal_72mm":
        effective["printer_width"] = 38
        return _render_thermal(bill_data, effective, 38)
    elif template == "thermal_76mm":
        effective["printer_width"] = 40
        return _render_thermal(bill_data, effective, 40)
    elif template == "thermal_112mm":
        effective["printer_width"] = 60
        return _render_thermal(bill_data, effective, 60)
    else:
        return generate_thermal_58mm(bill_data, effective)


# ── Backward-compatible alias (billing.py / print_templates.py use this) ──

def generate_thermal_text(bill: BillData, ps: dict = None) -> str:
    """
    Generate monospace receipt text — dispatches to correct template.
    Kept for backward compatibility; billing.py calls this directly.
    """
    if ps is None:
        ps = get_print_settings()
    tmpl = ps.get("template", "thermal_58mm")
    if "80" in tmpl or tmpl in ("invoice_compact",):
        return generate_thermal_80mm(bill, ps)
    elif "a4" in tmpl.lower() or tmpl in ("a5_halfpage", "invoice_detailed"):
        return generate_a4_standard(bill, ps)
    elif "72" in tmpl:
        effective = {**ps, "printer_width": 38, "template": "thermal_72mm"}
        return _render_thermal(bill, effective, 38)
    elif "76" in tmpl:
        effective = {**ps, "printer_width": 40, "template": "thermal_76mm"}
        return _render_thermal(bill, effective, 40)
    elif "112" in tmpl:
        effective = {**ps, "printer_width": 60, "template": "thermal_112mm"}
        return _render_thermal(bill, effective, 60)
    else:
        return generate_thermal_58mm(bill, ps)


# ═══════════════════════════════════════════════════════════════════════════
#  A4 PDF GENERATOR  (ReportLab)
# ═══════════════════════════════════════════════════════════════════════════

def generate_a4_pdf(bill: BillData, output_path: str,
                    ps: dict = None) -> str:
    """
    Generate A4 PDF bill using ReportLab.
    Logo is rendered as a real image (PNG/JPG) on A4.
    Returns output_path on success.
    """
    if ps is None:
        ps = get_print_settings()

    try:
        from reportlab.pdfgen import canvas as rl_canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib import colors as rl_colors
    except ImportError:
        raise ImportError("reportlab not installed. Run: pip install reportlab")

    pw, ph = A4
    c      = rl_canvas.Canvas(output_path, pagesize=A4)
    margin = 15 * mm
    y      = ph - margin

    def ln(n: float = 6):
        nonlocal y
        y -= n

    def draw_line(x1=None, x2=None, color: str = "#cccccc"):
        nonlocal y
        c.setStrokeColor(rl_colors.HexColor(color))
        c.setLineWidth(0.5)
        c.line(x1 or margin, y, x2 or (pw - margin), y)
        ln(4)

    def text(txt, x=None, font: str = "Helvetica", size: int = 10,
             bold: bool = False, center_: bool = False,
             color: str = "#1a1a1a"):
        nonlocal y
        if bold:
            font = font.replace("Helvetica", "Helvetica-Bold")
        c.setFont(font, size)
        c.setFillColor(rl_colors.HexColor(color))
        if center_:
            c.drawCentredString(pw / 2, y, str(txt)[:100])
        else:
            c.drawString(x or margin, y, str(txt)[:120])
        ln(size + 4)

    # ── Header ──────────────────────────────────────────────────────────────
    if ps.get("show_logo") and ps.get("logo_path"):
        logo_result = load_logo_for_pdf(
            ps["logo_path"],
            max_width_pt  = float(ps.get("logo_max_width", 200)),
            max_height_pt = 50.0,
        )
        if logo_result:
            img_path, draw_w, draw_h = logo_result
            try:
                c.drawImage(img_path, pw / 2 - draw_w / 2,
                            y - draw_h, draw_w, draw_h)
                y -= (draw_h + 6)
            except Exception:
                pass  # silently skip if image fails

    if ps.get("show_shop_name"):
        text(bill.salon_name, font="Helvetica-Bold", size=16,
             center_=True, color="#1a1a2e")

    if ps.get("show_address") and bill.address:
        text(bill.address, size=9, center_=True, color="#555555")

    if ps.get("show_phone") and bill.phone:
        text(f"Phone: {bill.phone}", size=9, center_=True, color="#555555")

    if ps.get("show_gst_no") and bill.gst_no:
        text(f"GSTIN: {bill.gst_no}", size=9, center_=True, color="#555555")

    draw_line(color="#0f3460")

    # ── Invoice details ──────────────────────────────────────────────────────
    try:
        now = datetime.strptime(bill.timestamp[:16], "%Y-%m-%d %H:%M")
    except Exception:
        now = datetime.now()

    row_y  = y
    left_x = margin

    if ps.get("show_invoice_number") and bill.invoice:
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(rl_colors.HexColor("#1a1a2e"))
        c.drawString(left_x, row_y, f"INV: {bill.invoice}")
        row_y -= 14

    date_parts = []
    if ps.get("show_date"):
        date_parts.append(now.strftime("%d-%m-%Y"))
    if ps.get("show_time"):
        date_parts.append(now.strftime("%I:%M %p"))
    if date_parts:
        c.setFont("Helvetica", 9)
        c.setFillColor(rl_colors.HexColor("#555555"))
        c.drawString(left_x, row_y, "   ".join(date_parts))
        row_y -= 12

    y = row_y - 4

    # ── Customer block ───────────────────────────────────────────────────────
    if ps.get("show_customer_name") and bill.customer_name:
        c.setFont("Helvetica", 10)
        c.setFillColor(rl_colors.HexColor("#1a1a2e"))
        c.drawString(margin, y, f"Customer : {bill.customer_name}")
        ln(13)
    if ps.get("show_customer_phone") and bill.customer_phone:
        c.setFont("Helvetica", 10)
        c.drawString(margin, y, f"Phone    : {bill.customer_phone}")
        ln(13)
    if ps.get("show_payment_method") and bill.payment_method:
        c.setFont("Helvetica", 10)
        c.drawString(margin, y, f"Payment  : {bill.payment_method}")
        ln(13)

    draw_line()

    # ── Items table ──────────────────────────────────────────────────────────
    col_name = margin
    col_qty  = pw - margin - 80
    col_rate = pw - margin - 50
    col_amt  = pw - margin - 10

    def table_header():
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(rl_colors.HexColor("#0f3460"))
        c.drawString(col_name, y, "#  Item")
        c.drawRightString(col_qty,  y, "Qty")
        c.drawRightString(col_rate, y, "Rate")
        c.drawRightString(col_amt,  y, "Amount")
        ln(4)
        draw_line(color="#aaaaaa")

    def table_row(idx: int, it: dict):
        nonlocal y
        if y < 60:
            c.showPage()
            y = ph - margin
            table_header()
        prefix = f"{idx}. " if ps.get("show_item_numbering") else "  "
        nm     = trunc(prefix + it.get("name", ""), 55)
        price  = float(it.get("price", 0))
        qty    = float(it.get("qty", 1))
        qty_label = format_cart_quantity_label(it)
        amt    = price * qty
        c.setFont("Helvetica", 9)
        c.setFillColor(rl_colors.black)
        c.drawString(col_name, y, nm)
        c.drawRightString(col_qty,  y, qty_label)
        c.drawRightString(col_rate, y, f"Rs.{price:.2f}")
        c.drawRightString(col_amt,  y, f"Rs.{amt:.2f}")
        ln(13)

    counter = [0]

    if ps.get("show_services_section") and bill.svc_items:
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(rl_colors.HexColor("#16a085"))
        c.drawString(margin, y, "SERVICES")
        ln(12)
        table_header()
        for it in bill.svc_items:
            counter[0] += 1
            table_row(counter[0], it)

    if ps.get("show_products_section") and bill.prd_items:
        ln(4)
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(rl_colors.HexColor("#2980b9"))
        c.drawString(margin, y, "PRODUCTS")
        ln(12)
        table_header()
        for it in bill.prd_items:
            counter[0] += 1
            table_row(counter[0], it)

    draw_line()

    # ── Totals ───────────────────────────────────────────────────────────────
    total_x = pw - margin - 160
    val_x   = pw - margin

    def total_row(label: str, value: float,
                  bold: bool = False, color: str = "#1a1a2e"):
        nonlocal y
        font = "Helvetica-Bold" if bold else "Helvetica"
        c.setFont(font, 10)
        c.setFillColor(rl_colors.HexColor(color))
        c.drawString(total_x, y, label)
        c.drawRightString(val_x, y, f"Rs.{value:.2f}")
        ln(14)

    has_disc = any([
        bill.discount       > 0,
        bill.mem_discount   > 0,
        bill.pts_discount   > 0,
        bill.offer_discount > 0,
        bill.redeem_discount> 0,
        bill.gst_amount     > 0,
    ])

    if ps.get("show_subtotal") and has_disc:
        total_row("Sub Total", bill.subtotal)

    if ps.get("show_discount") and bill.discount > 0:
        total_row("Discount (-)", bill.discount, color="#e74c3c")

    if ps.get("show_membership_discount") and bill.mem_discount > 0:
        total_row(f"Member {bill.mem_pct}% (-)", bill.mem_discount, color="#e74c3c")

    if ps.get("show_loyalty_points") and bill.pts_discount > 0:
        total_row("Points (-)", bill.pts_discount, color="#e74c3c")

    if ps.get("show_offer_discount") and bill.offer_discount > 0:
        oname = trunc(bill.offer_name or "Offer", 18)
        total_row(f"{oname} (-)", bill.offer_discount, color="#e74c3c")

    if bill.redeem_discount > 0:
        total_row("Redeem Code (-)", bill.redeem_discount, color="#e74c3c")

    if ps.get("show_gst") and bill.gst_amount > 0:
        gtype = "Incl" if bill.gst_type == "inclusive" else "Excl"
        total_row(f"GST {int(bill.gst_rate)}% ({gtype})", bill.gst_amount)

    # Grand total — highlighted box
    if ps.get("show_grand_total"):
        draw_line(color="#0f3460")
        c.setFillColor(rl_colors.HexColor("#1a1a2e"))
        c.rect(total_x - 8, y - 4, val_x - total_x + 20, 22, fill=1, stroke=0)
        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(rl_colors.white)
        c.drawString(total_x, y + 4, "GRAND TOTAL")
        c.drawRightString(val_x, y + 4, f"Rs.{bill.grand_total:.2f}")
        ln(24)

    # ── Footer ───────────────────────────────────────────────────────────────
    if ps.get("show_footer"):
        footer = ps.get("footer_text", get_invoice_branding()["footer"])
        c.setFont("Helvetica-Oblique", 10)
        c.setFillColor(rl_colors.HexColor("#555555"))
        c.drawCentredString(pw / 2, 30, trunc(footer, 80))

    c.save()
    return output_path


# ═══════════════════════════════════════════════════════════════════════════
#  THERMAL PDF GENERATOR  (58mm / 80mm)
# ═══════════════════════════════════════════════════════════════════════════

def generate_thermal_pdf(bill: BillData, output_path: str,
                          ps: dict = None, font_size: int = 7) -> str:
    """
    Generate thermal-format PDF using monospace text layout.
    Uses fixed-width Courier font for 58mm / 80mm paper.
    """
    if ps is None:
        ps = get_print_settings()

    try:
        from reportlab.pdfgen import canvas as rl_canvas
        from reportlab.lib.units import mm
    except ImportError:
        raise ImportError("reportlab not installed. Run: pip install reportlab")

    tmpl = ps.get("template", "thermal_58mm")
    tmpl_page = TEMPLATE_PAGE_WIDTH_MM.get(tmpl)
    if tmpl_page is not None:
        if tmpl in ("a4_standard", "a5_halfpage", "invoice_compact", "invoice_detailed"):
            return generate_a4_pdf(bill, output_path, ps)
        page_w = tmpl_page * mm
    elif "80" in tmpl or "a4" in tmpl.lower():
        return generate_a4_pdf(bill, output_path, ps)
    elif "72" in tmpl or "76" in tmpl:
        page_w = 76 * mm
    elif "112" in tmpl:
        page_w = 112 * mm
    else:
        page_w = 58 * mm

    text_content = generate_thermal_text(bill, ps)
    lines        = text_content.split("\n")
    line_gap     = font_size + 3
    page_h       = max(100 * mm, len(lines) * line_gap + 20)

    c = rl_canvas.Canvas(output_path, pagesize=(page_w, page_h))
    y = page_h - 8

    for line in lines:
        if y <= 10:
            c.showPage()
            y = page_h - 8
        safe = line.replace("\u20b9", "Rs.").replace("\u2550", "=")[:80]
        if "TOTAL" in safe.upper() or "INV:" in safe:
            c.setFont("Courier-Bold", font_size + 1)
        else:
            c.setFont("Courier", font_size)
        c.drawString(3, y, safe)
        y -= line_gap

    c.save()
    return output_path


# ═══════════════════════════════════════════════════════════════════════════
#  UNIFIED ENTRY POINTS  (called by billing.py — do not rename)
# ═══════════════════════════════════════════════════════════════════════════

def generate_bill_pdf(bill: BillData, output_path: str,
                       font_size: int = 7) -> str:
    """
    Main PDF entry point — picks thermal or A4 based on template setting.
    Called by billing.py. Do not rename.
    """
    ps   = get_print_settings()
    tmpl = ps.get("template", "thermal_58mm")
    # New templates in Phase 5.6.1 Phase 2
    page_templates = {"a4_standard", "a5_halfpage", "invoice_compact", "invoice_detailed"}
    if tmpl in page_templates:
        return generate_a4_pdf(bill, output_path, ps)
    else:
        return generate_thermal_pdf(bill, output_path, ps, font_size)


def generate_bill_preview_text(bill: BillData) -> str:
    """
    Generate preview text for the billing screen's text widget.
    Always uses monospace thermal layout (preview is always text).
    Called by billing.py. Do not rename.
    """
    ps = get_print_settings()
    return generate_thermal_text(bill, ps)


# ═══════════════════════════════════════════════════════════════════════════
#  SELF-TEST  (run directly: python print_engine.py)
# ═══════════════════════════════════════════════════════════════════════════

def _run_tests():
    """
    Test Case 1: Minimal bill
    Test Case 2: Full GST bill
    Test Case 3: Thermal compact
    """
    demo = BillData(
        invoice        = "INV-202603-00001",
        salon_name     = get_invoice_branding()["header"],
        address        = get_invoice_branding()["address"] or "Kerala, India",
        phone          = get_invoice_branding()["phone"] or "9999999999",
        gst_no         = "29ABCDE1234F1Z5",
        customer_name  = "Priya Menon",
        customer_phone = "9012345678",
        payment_method = "Cash",
        svc_items = [
            {"mode": "services", "name": "Hair Spa",     "price": 800.0, "qty": 1},
            {"mode": "services", "name": "Facial Basic", "price": 600.0, "qty": 1},
        ],
        prd_items = [
            {"mode": "products", "name": "Shampoo 200ml", "price": 200.0, "qty": 2},
        ],
        subtotal        = 1800.0,
        discount        = 100.0,
        mem_discount    = 90.0,
        mem_pct         = 10,
        pts_discount    = 0.0,
        offer_discount  = 50.0,
        offer_name      = "Welcome10",
        gst_amount      = 0.0,
        grand_total     = 1560.0,
        timestamp       = "2026-03-20 14:30",
    )

    cases = [
        # Case 1 — Minimal
        ("Case 1 — Minimal 58mm", "thermal_58mm", {
            "show_logo": False, "show_shop_name": True,
            "show_address": False, "show_phone": False, "show_gst_no": False,
            "show_invoice_number": False, "show_date": True, "show_time": False,
            "show_customer_name": False, "show_customer_phone": False,
            "show_payment_method": False, "show_item_numbering": False,
            "show_services_section": True, "show_products_section": True,
            "show_subtotal": False, "show_discount": False,
            "show_membership_discount": False, "show_loyalty_points": False,
            "show_offer_discount": False, "show_gst": False,
            "show_grand_total": True, "show_footer": False,
            "show_separator_lines": True, "double_width_total": True,
        }),
        # Case 2 — Full GST
        ("Case 2 — Full GST 80mm", "thermal_80mm", {
            "show_logo": False, "show_shop_name": True,
            "show_address": True, "show_phone": True, "show_gst_no": True,
            "show_invoice_number": True, "show_date": True, "show_time": True,
            "show_customer_name": True, "show_customer_phone": True,
            "show_payment_method": True, "show_item_numbering": True,
            "show_services_section": True, "show_products_section": True,
            "show_subtotal": True, "show_discount": True,
            "show_membership_discount": True, "show_loyalty_points": True,
            "show_offer_discount": True, "show_gst": True,
            "show_grand_total": True,
            "show_footer": True, "footer_text": "Thank You! Visit Again",
            "show_separator_lines": True, "double_width_total": False,
        }),
        # Case 3 — Thermal compact
        ("Case 3 — Compact 58mm", "thermal_58mm", {
            "show_logo": False, "show_shop_name": True,
            "show_address": False, "show_phone": True, "show_gst_no": False,
            "show_invoice_number": True, "show_date": True, "show_time": True,
            "show_customer_name": True, "show_customer_phone": False,
            "show_payment_method": True, "show_item_numbering": False,
            "show_services_section": True, "show_products_section": False,
            "show_subtotal": False, "show_discount": True,
            "show_membership_discount": False, "show_loyalty_points": False,
            "show_offer_discount": False, "show_gst": False,
            "show_grand_total": True,
            "show_footer": True, "footer_text": "Visit Again!",
            "show_separator_lines": True, "double_width_total": True,
        }),
    ]

    for name, tmpl, overrides in cases:
        print(f"\n{'=' * 50}")
        print(f"  {name}")
        print(f"{'=' * 50}")
        result = generate_bill(tmpl, overrides, demo)
        print(result)
        # Verify no crash, no empty separator-only lines at start/end
        assert result.strip(), f"{name}: output is blank!"
        print(f"[OK] {name} — {len(result.splitlines())} lines")


if __name__ == "__main__":
    _run_tests()
