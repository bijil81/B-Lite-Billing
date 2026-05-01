"""
closing_report.py  Ã¢â‚¬â€œ  BOBY'S Salon : Daily Closing Report PDF + Profit Analysis
FIXES:
  - Fix R11a: app_log + open_file_cross_platform imported from utils
  - Fix R11b: _read_bills_for_date() try/except Ã¢â‚¬â€ corrupt CSV crash prevention
  - Fix R11c: generate_closing_pdf() try/except Ã¢â‚¬â€ PDF gen failure logged
  - Fix R11d: _preview() try/except wrapper Ã¢â‚¬â€ crash prevention
  - Fix R11e: _preview_bill() try/except Ã¢â‚¬â€ bill preview crash prevention
  - Fix R11f: _save_pdf() cross-platform file open (os.startfile Ã¢â€ â€™ utils)
  - Fix R11g: _load_profit() try/except Ã¢â‚¬â€ CSV read crash prevention
  - Fix R11h: _profit_month() try/except Ã¢â‚¬â€ crash prevention
  - Fix R11i: _profit_all() try/except Ã¢â‚¬â€ crash prevention
  - Fix R11j: refresh() try/except Ã¢â‚¬â€ crash prevention
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime
import csv, os
from collections import defaultdict
from utils import (C, safe_float, fmt_currency, F_REPORT,
                   DATA_DIR, today_str, month_str, load_json, F_EXPENSES,
                   app_log, open_file_cross_platform)
from date_helpers import attach_date_mask, display_to_iso_date, iso_to_display_date, today_display_str, validate_display_date
from ui_theme import apply_treeview_column_alignment, ModernButton
from ui_responsive import get_responsive_metrics, scaled_value
from expenses import get_expenses
from branding import get_company_name, get_invoice_branding
from db_core.connection import connection_scope
from db_core.schema_manager import ensure_v5_schema
from src.blite_v6.reports.retail_summary import build_closing_retail_summary, format_quantity


def _read_bills_for_date(dt: str) -> list:
    """Fix R11b: try/except Ã¢â‚¬â€ returns [] on corrupt/unreadable CSV."""
    rows = []
    try:
        ensure_v5_schema()
        with connection_scope() as conn:
            db_rows = conn.execute(
                """
                SELECT i.invoice_date AS date,
                       i.invoice_no AS invoice,
                       i.customer_name AS name,
                       i.customer_phone AS phone,
                       COALESCE((SELECT p.payment_method
                                 FROM v5_payments p
                                 WHERE p.invoice_id = i.id
                                 ORDER BY p.id LIMIT 1), '') AS payment,
                       i.net_total AS total,
                       i.discount_total AS discount,
                       i.tax_total AS gst_amount,
                       MAX(0, i.net_total - i.tax_total) AS taxable_amount,
                       COALESCE(i.created_by, '') AS created_by,
                       COALESCE(substr(i.invoice_date, 12, 5), '') AS time,
                       COALESCE((SELECT GROUP_CONCAT(
                                    ii.item_type || '~' || ii.item_name || '~' || printf('%.2f', ii.unit_price) || '~' || printf('%.2f', ii.qty),
                                    '|'
                                )
                                FROM v5_invoice_items ii
                                WHERE ii.invoice_id = i.id), '') AS items_raw
                FROM v5_invoices i
                WHERE substr(i.invoice_date, 1, 10) = ?
                ORDER BY i.invoice_date DESC, i.invoice_no DESC
                """,
                (dt,),
            ).fetchall()
            if db_rows:
                return [dict(row) for row in db_rows]
    except Exception as e:
        app_log(f"[_read_bills_for_date:db] {e}")
    if not os.path.exists(F_REPORT): return rows
    try:
        with open(F_REPORT, "r", encoding="utf-8") as f:
            r   = csv.reader(f)
            hdr = next(r, None)
            new = hdr and len(hdr) >= 6
            for row in r:
                if not row: continue
                if new and len(row) >= 6:
                    if row[0][:10] != dt: continue
                    rows.append({
                        "date": row[0], "invoice": row[1],
                        "name": row[2], "phone": row[3],
                        "payment": row[4], "total": safe_float(row[5]),
                        "discount": safe_float(row[6]) if len(row)>6 else 0,
                        "gst_amount": 0.0,
                        "taxable_amount": safe_float(row[5]),
                        "created_by": row[8] if len(row) > 8 else "",
                        "time": row[0][11:16] if len(row[0]) >= 16 else "",
                        "items_raw": row[7] if len(row)>7 else "",
                    })
                else:
                    if len(row) >= 4 and row[0][:10] == dt:
                        rows.append({
                            "date": row[0], "invoice": "---",
                            "name": row[1], "phone": row[2],
                            "payment": "---", "total": safe_float(row[3]),
                            "discount": 0,
                            "gst_amount": 0.0,
                            "taxable_amount": safe_float(row[3]),
                            "created_by": "",
                            "time": row[0][11:16] if len(row[0]) >= 16 else "",
                            "items_raw": row[4] if len(row)>4 else "",
                        })
    except Exception as e:
        app_log(f"[_read_bills_for_date] {e}")
    return rows


def generate_closing_pdf(dt: str) -> str:
    """Generate closing report PDF. Returns file path.
    Fix R11c: try/except Ã¢â‚¬â€ PDF gen failure properly logged."""
    try:
        return _generate_closing_pdf_inner(dt)
    except Exception as e:
        app_log(f"[generate_closing_pdf] {e}")
        raise  # re-raise so caller (_save_pdf) can show user error


def _generate_closing_pdf_inner(dt: str) -> str:
    """Inner PDF generator Ã¢â‚¬â€ called by generate_closing_pdf."""
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4

    bills    = _read_bills_for_date(dt)
    expenses = [e for e in get_expenses() if e.get("date","")[:10] == dt]
    retail_summary = build_closing_retail_summary(bills, expenses)

    total_rev  = retail_summary.revenue
    total_disc = retail_summary.discount
    total_exp  = retail_summary.expenses
    net_profit = retail_summary.net_profit

    payment_summary = defaultdict(float)
    for b in bills:
        payment_summary[b["payment"]] += b["total"]

    # PDF
    file_name = f"Closing_Report_{dt}.pdf"
    out_path  = os.path.join(DATA_DIR, file_name)
    c = canvas.Canvas(out_path, pagesize=A4)
    W, H = A4
    y    = H - 40

    def line(text, x=40, size=10, bold=False, color=(0,0,0)):
        nonlocal y
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.setFillColorRGB(*color)
        c.drawString(x, y, text)
        y -= size + 5

    def divider():
        nonlocal y
        c.setStrokeColorRGB(0.8, 0.8, 0.8)
        c.line(40, y, W-40, y)
        y -= 10

    # Header
    c.setFillColorRGB(0.1, 0.1, 0.18)
    c.rect(0, H-70, W, 70, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(W/2, H-35, get_invoice_branding()["header"])
    c.setFont("Helvetica", 10)
    c.drawCentredString(W/2, H-52, f"Daily Closing Report  |  {dt}")
    y = H - 85

    # Summary
    line("SUMMARY", bold=True, size=13,
         color=(0.1, 0.1, 0.5))
    divider()
    for lbl, val, col in [
        ("Total Bills",       str(len(bills)),         (0,0,0)),
        ("Gross Sales",       fmt_currency(retail_summary.gross_sales), (0, 0.5, 0.2)),
        ("Service Sales",     fmt_currency(retail_summary.service_revenue), (0, 0.35, 0.7)),
        ("Product Sales",     fmt_currency(retail_summary.product_revenue), (0, 0.35, 0.7)),
        ("Total Discount",    fmt_currency(total_disc),(0.8, 0.3, 0)),
        ("Net Revenue",       fmt_currency(total_rev), (0, 0.5, 0.2)),
        ("GST Total",         fmt_currency(retail_summary.gst_total), (0.25, 0.25, 0.25)),
        ("Total Expenses",    fmt_currency(total_exp), (0.8, 0, 0)),
        ("NET PROFIT",        fmt_currency(net_profit),
         (0, 0.5, 0.2) if net_profit >= 0 else (0.8, 0, 0)),
    ]:
        c.setFont("Helvetica-Bold", 10)
        c.setFillColorRGB(0.4, 0.4, 0.4)
        c.drawString(40, y, lbl + ":")
        c.setFont("Helvetica-Bold", 11)
        c.setFillColorRGB(*col)
        c.drawRightString(W-40, y, val)
        y -= 18

    y -= 10
    # Payment breakdown
    if payment_summary:
        line("PAYMENT BREAKDOWN", bold=True, size=11,
             color=(0.1, 0.1, 0.5))
        divider()
        for pm, amt in payment_summary.items():
            c.setFont("Helvetica", 10)
            c.setFillColorRGB(0, 0, 0)
            c.drawString(60, y, f"- {pm}")
            c.drawRightString(W-40, y, fmt_currency(amt))
            y -= 16
        y -= 8

    # Top services
    if retail_summary.top_services:
        line("TOP SERVICES TODAY", bold=True, size=11,
             color=(0.1, 0.1, 0.5))
        divider()
        for svc in retail_summary.top_services:
            c.setFont("Helvetica", 10)
            c.setFillColorRGB(0, 0, 0)
            qty = format_quantity(svc.quantity)
            c.drawString(60, y, f"- {svc.name[:38]} ({qty})")
            c.drawRightString(W-40, y, fmt_currency(svc.revenue))
            y -= 16
        y -= 8

    if retail_summary.top_products:
        if y < 140:
            c.showPage()
            y = H - 40
        line("TOP PRODUCTS TODAY", bold=True, size=11,
             color=(0.1, 0.1, 0.5))
        divider()
        for product in retail_summary.top_products:
            c.setFont("Helvetica", 10)
            c.setFillColorRGB(0, 0, 0)
            unit = f" {product.unit}" if product.unit else ""
            qty = format_quantity(product.quantity)
            c.drawString(60, y, f"- {product.name[:34]} ({qty}{unit})")
            c.drawRightString(W-40, y, fmt_currency(product.revenue))
            y -= 16
        y -= 8

    if retail_summary.gst_rows:
        if y < 120:
            c.showPage()
            y = H - 40
        line("GST SUMMARY", bold=True, size=11,
             color=(0.1, 0.1, 0.5))
        divider()
        for gst_row in retail_summary.gst_rows:
            c.setFont("Helvetica", 10)
            c.setFillColorRGB(0, 0, 0)
            rate_text = "GST Unspecified" if gst_row.rate < 0 else f"GST {format_quantity(gst_row.rate)}%"
            c.drawString(60, y, rate_text)
            c.drawRightString(W-140, y, fmt_currency(gst_row.taxable_amount))
            c.drawRightString(W-40, y, fmt_currency(gst_row.gst_amount))
            y -= 16
        y -= 8

    # Bill list
    if y < 200:
        c.showPage()
        y = H - 40

    line("BILL LIST", bold=True, size=11, color=(0.1,0.1,0.5))
    divider()
    c.setFont("Helvetica-Bold", 9)
    c.setFillColorRGB(0.3, 0.3, 0.3)
    for hdr_txt, hx in [("Invoice",40),("Customer",120),
                          ("Phone",260),("Pay",360),("Total",480)]:
        c.drawString(hx, y, hdr_txt)
    y -= 14
    c.line(40, y+2, W-40, y+2)
    y -= 8

    for b in bills:
        if y < 60:
            c.showPage()
            y = H - 40
        c.setFont("Helvetica", 9)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(40,  y, b["invoice"][:12])
        c.drawString(120, y, b["name"][:18])
        c.drawString(260, y, b["phone"][:12])
        c.drawString(360, y, b["payment"][:8])
        c.drawRightString(W-40, y, fmt_currency(b["total"]))
        y -= 14

    # Expenses
    if expenses:
        y -= 10
        if y < 120:
            c.showPage(); y = H - 40
        line("EXPENSES", bold=True, size=11, color=(0.8,0,0))
        divider()
        for e in expenses:
            if y < 60: c.showPage(); y = H-40
            c.setFont("Helvetica", 9)
            c.setFillColorRGB(0,0,0)
            c.drawString(40,  y, e.get("category",""))
            c.drawString(160, y, e.get("description","")[:30])
            c.drawRightString(W-40, y, fmt_currency(e["amount"]))
            y -= 14

    # Footer
    c.setFont("Helvetica", 8)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.drawCentredString(W/2, 30,
                         f"Generated: {datetime.now().strftime('%d-%m-%Y %I:%M %p')}  |  {get_company_name()}")
    c.save()
    return out_path


class ClosingReportFrame(tk.Frame):

    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self._responsive = get_responsive_metrics(parent.winfo_toplevel())
        self._build()

    def _build(self):
        self._responsive = get_responsive_metrics(self.winfo_toplevel())
        compact = self._responsive["mode"] == "compact"
        hdr = tk.Frame(self, bg=C["card"], pady=10)
        hdr.pack(fill=tk.X)
        left_f = tk.Frame(hdr, bg=C["card"])
        left_f.pack(side=tk.LEFT, padx=20)
        tk.Label(left_f, text="Daily Closing Report",
                 font=("Arial", 15, "bold"),
                 bg=C["card"], fg=C["text"]).pack(anchor="w")
        tk.Label(left_f, text="End-of-day summary, PDFs & profit analysis",
                 font=("Arial", 10), bg=C["card"], fg=C["muted"]).pack(anchor="w")
        tk.Frame(self, bg=C["teal"], height=2).pack(fill=tk.X)

        top_band = tk.Frame(self, bg=C["bg"])
        top_band.pack(fill=tk.X, padx=15, pady=(6, 4))
        intro = tk.Frame(top_band, bg=C["card"], padx=16, pady=9)
        intro.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(intro, text="Closing Workspace",
                 font=("Arial", 12, "bold"),
                 bg=C["card"], fg=C["text"]).pack(anchor="w")
        tk.Label(intro, text="Review the day, export the summary PDF, and inspect service performance.",
                 font=("Arial", 10), bg=C["card"], fg=C["muted"]).pack(anchor="w", pady=(4, 0))

        snap_wrap = tk.Frame(top_band, bg=C["bg"], width=scaled_value(620, 520, 420))
        snap_wrap.pack(side=tk.RIGHT, padx=(12, 0))
        if compact:
            snap_wrap.pack(fill=tk.X, expand=True, pady=(8, 0))
        else:
            snap_wrap.pack_propagate(False)
        snap_hdr = tk.Frame(snap_wrap, bg=C["bg"])
        snap_hdr.pack(fill=tk.X, pady=(0, 4))
        tk.Label(snap_hdr, text="Daily Snapshot",
                 font=("Arial", 11, "bold"),
                 bg=C["bg"], fg=C["text"]).pack(anchor="w")
        tk.Label(snap_hdr, text="Bills, revenue, expenses, and net profit for the selected day.",
                 font=("Arial", 9), bg=C["bg"], fg=C["muted"]).pack(anchor="w", pady=(2, 0))
        self.cr_cards = tk.Frame(snap_wrap, bg=C["bg"])
        self.cr_cards.pack(fill=tk.X)
        for col in range(4):
            self.cr_cards.grid_columnconfigure(col, weight=1, uniform="closing_summary")

        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))

        t1 = tk.Frame(nb, bg=C["bg"])
        t2 = tk.Frame(nb, bg=C["bg"])

        nb.add(t1, text="Closing Report")
        nb.add(t2, text="Service Profit Analysis")

        self._build_closing(t1)
        self._build_profit(t2)

    
    def _export_excel(self):
        """Phase 4: Export daily closing to multi-sheet Excel."""
        dt = self.cr_date.get().strip()
        if validate_display_date(dt):
            dt_iso = display_to_iso_date(dt)
        else:
            dt_iso = dt
        try:
            from exports.export_engine import export_daily_closing_excel
            path = export_daily_closing_excel(dt_iso)
            if path:
                messagebox.showinfo('Exported', 'Closing report Excel saved:\n' + path)
                try:
                    open_file_cross_platform(path)
                except Exception:
                    pass
            else:
                messagebox.showinfo('Export Info', 'No data found for the selected date.')
        except Exception as e:
            messagebox.showerror('Export Error', str(e))

    def _build_closing(self, parent):
        shell = tk.Frame(parent, bg=C["bg"])
        shell.pack(fill=tk.BOTH, expand=True, padx=15, pady=(6, 8))

        pane = tk.PanedWindow(shell, orient=tk.HORIZONTAL,
                               sashrelief=tk.RAISED, sashwidth=6,
                               bg=C["bg"])
        pane.pack(fill=tk.BOTH, expand=True)

        left_wrap = tk.Frame(pane, bg=C["bg"])
        pane.add(left_wrap, minsize=scaled_value(500, 430, 360), stretch="never")

        left_card = tk.Frame(left_wrap, bg=C["card"])
        left_card.pack(fill=tk.BOTH, expand=True)
        left_hdr = tk.Frame(left_card, bg=C.get("nav", C["card"]))
        left_hdr.pack(fill=tk.X)
        tk.Label(left_hdr, text="Closing Controls",
                 font=("Arial", 11, "bold"),
                 bg=C.get("nav", C["card"]), fg=C["text"]).pack(side=tk.LEFT, padx=12, pady=6)

        ctrl = tk.Frame(left_card, bg=C["card"], pady=9, padx=12)
        ctrl.pack(fill=tk.X)

        tk.Label(ctrl, text="Date:", bg=C["card"],
                 fg=C["muted"], font=("Arial", 11)).pack(side=tk.LEFT, padx=(0, 6))
        self.cr_date = tk.Entry(ctrl, font=("Arial", 12),
                                 bg=C["input"], fg=C["text"],
                                 bd=0, width=14,
                                 insertbackground=C["accent"])
        self.cr_date.pack(side=tk.LEFT, ipady=6, padx=(0, 10))
        self.cr_date.insert(0, today_display_str())
        attach_date_mask(self.cr_date)

        for txt, clr, hclr, cmd in [
            ("Preview",  C["blue"],   "#154360", self._preview),
            ("Save PDF", C["purple"], "#6c3483", self._save_pdf),
            ("Export Excel", C["green"], "#1a7a45", self._export_excel),
        ]:
            ModernButton(ctrl, text=txt, command=cmd,
                         color=clr, hover_color=hclr,
                         width=scaled_value(112, 102, 92), height=scaled_value(34, 32, 28), radius=8,
                         font=("Arial",scaled_value(10, 10, 9),"bold"),
                         ).pack(side=tk.LEFT, padx=4)

        ModernButton(ctrl, text="Today",
                     command=lambda: (self.cr_date.delete(0,tk.END),
                                      self.cr_date.insert(0, today_display_str()),
                                      self._preview()),
                     color=C["teal"], hover_color=C["blue"],
                     width=scaled_value(94, 86, 78), height=scaled_value(34, 32, 28), radius=8,
                     font=("Arial",scaled_value(10, 10, 9),"bold"),
                     ).pack(side=tk.LEFT, padx=4)

        list_area = tk.Frame(left_card, bg=C["card"])
        list_area.pack(fill=tk.BOTH, expand=True)

        self._show_bill_audit = str(
            getattr(getattr(self, "app", None), "current_user", {}).get("role", "staff")
        ).strip().lower() in {"owner", "admin", "manager"}
        cols = ("Invoice", "Time", "Customer", "Phone", "Payment", "Discount", "Total")
        self.cr_tree = ttk.Treeview(list_area, columns=cols,
                                     show="headings", height=14)
        self._cr_cols = cols
        init_widths = {
            "Invoice": scaled_value(120, 108, 96),
            "Time": scaled_value(76, 72, 68),
            "Customer": scaled_value(138, 126, 114),
            "Phone": scaled_value(112, 104, 96),
            "Payment": scaled_value(96, 88, 80),
            "Discount": scaled_value(98, 92, 86),
            "Total": scaled_value(118, 110, 102),
        }
        for col in cols:
            self.cr_tree.heading(col, text=col)
            self.cr_tree.column(col, width=init_widths.get(col, scaled_value(110, 96, 84)))
        apply_treeview_column_alignment(self.cr_tree)
        vsb = ttk.Scrollbar(list_area, orient="vertical",
                             command=self.cr_tree.yview)
        self.cr_tree.configure(yscrollcommand=vsb.set)
        self.cr_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        vsb.pack(side=tk.LEFT, fill=tk.Y)
        list_area.bind("<Configure>", self._resize_closing_columns, add="+")

        right_f = tk.Frame(pane, bg=C["bg"])
        pane.add(right_f, minsize=scaled_value(440, 390, 320))

        prev_hdr = tk.Frame(right_f, bg=C["card"], pady=6, padx=10)
        prev_hdr.pack(fill=tk.X)
        tk.Label(prev_hdr, text="Bill Preview",
                 font=("Arial", 11, "bold"),
                 bg=C["card"], fg=C["text"]).pack(side=tk.LEFT)
        tk.Label(prev_hdr,
                 text="Click a bill row on the left to see full bill here",
                 font=("Arial", 10), bg=C["card"],
                 fg=C["gold"]).pack(side=tk.RIGHT)
        self.cr_audit_note_lbl = tk.Label(
            right_f,
            text="",
            font=("Arial", 10, "bold"),
            bg=C["bg"],
            fg=C["teal"],
            anchor="w",
            padx=4,
            pady=4,
        )
        self.cr_audit_note_lbl.pack(fill=tk.X, padx=(2, 0), pady=(4, 2))

        self.cr_preview = tk.Text(right_f,
                                   font=("Courier New", 12),
                                   bg="#fafafa", fg="#2d3436",
                                   padx=10, pady=10, bd=0,
                                   state="disabled", wrap="none")
        pvsb = ttk.Scrollbar(right_f, orient="vertical",
                              command=self.cr_preview.yview)
        self.cr_preview.configure(yscrollcommand=pvsb.set)
        self.cr_preview.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        pvsb.pack(side=tk.LEFT, fill=tk.Y)

        self.cr_tree.bind("<<TreeviewSelect>>", self._preview_bill)
        self.cr_tree.bind("<Button-3>", self._show_closing_report_context_menu)

        self._preview()

    def _show_closing_report_context_menu(self, event):
        row_id = self.cr_tree.identify_row(event.y)
        if not row_id:
            return "break"
        try:
            self.cr_tree.selection_set(row_id)
            self.cr_tree.focus(row_id)
            values = self.cr_tree.item(row_id, "values")
            if not values:
                return "break"
            self._preview_bill()
            self._register_closing_report_context_menu_callbacks()

            from shared.context_menu.constants import WidgetType
            from shared.context_menu.menu_context_factory import build_context
            from shared.context_menu.renderer import renderer_service
            from shared.context_menu_definitions.closing_report_context_menu import get_sections

            selected_row = {
                "row_id": row_id,
                "invoice": values[0] if len(values) > 0 else "",
                "time": values[1] if len(values) > 1 else "",
                "customer": values[2] if len(values) > 2 else "",
                "phone": values[3] if len(values) > 3 else "",
                "payment": values[4] if len(values) > 4 else "",
                "discount": values[5] if len(values) > 5 else "",
                "total": values[6] if len(values) > 6 else "",
            }
            context = build_context(
                "closing_report",
                entity_type="closing_bill",
                entity_id=selected_row["invoice"],
                selected_row=selected_row,
                selection_count=1,
                user_role=self.app.current_user.get("role", "") if getattr(self.app, "current_user", None) else "",
                widget_type=WidgetType.TREEVIEW,
                widget_id="closing_report_bill_grid",
                screen_x=event.x_root,
                screen_y=event.y_root,
                extra={"has_closing_bill": True},
            )
            menu = renderer_service.build_menu(self, get_sections(), context)
            menu.tk_popup(event.x_root, event.y_root)
            return "break"
        except Exception as exc:
            app_log(f"[closing report context menu] {exc}")
            return "break"

    def _register_closing_report_context_menu_callbacks(self):
        from shared.context_menu.action_adapter import action_adapter
        from shared.context_menu.clipboard_service import clipboard_service
        from shared.context_menu_definitions.closing_report_context_menu import ClosingReportContextAction

        action_adapter.register(ClosingReportContextAction.PREVIEW_BILL, lambda _ctx, _act: self._preview_bill())
        action_adapter.register(ClosingReportContextAction.SAVE_PDF, lambda _ctx, _act: self._save_pdf())
        action_adapter.register(ClosingReportContextAction.EXPORT_EXCEL, lambda _ctx, _act: self._export_excel())
        action_adapter.register(
            ClosingReportContextAction.COPY_INVOICE,
            lambda ctx, _act: clipboard_service.copy_text(self, ctx.selected_row.get("invoice", "")),
        )
        action_adapter.register(
            ClosingReportContextAction.COPY_CUSTOMER,
            lambda ctx, _act: clipboard_service.copy_text(self, ctx.selected_row.get("customer", "")),
        )
        action_adapter.register(
            ClosingReportContextAction.COPY_PHONE,
            lambda ctx, _act: clipboard_service.copy_text(self, ctx.selected_row.get("phone", "")),
        )
        action_adapter.register(
            ClosingReportContextAction.COPY_TOTAL,
            lambda ctx, _act: clipboard_service.copy_text(self, ctx.selected_row.get("total", "")),
        )
        action_adapter.register(ClosingReportContextAction.REFRESH, lambda _ctx, _act: self._preview())

    def _preview(self):
        """Fix R11d: try/except wrapper Ã¢â‚¬â€ crash prevention."""
        try:
            self._preview_inner()
        except Exception as e:
            app_log(f"[_preview] {e}")

    def _preview_inner(self):
        dt    = self.cr_date.get().strip()
        if not validate_display_date(dt):
            messagebox.showerror("Error", "Date must be DD-MM-YYYY format.\nExample: 15-06-2026")
            return
        dt = display_to_iso_date(dt)
        bills = _read_bills_for_date(dt)
        exps  = [e for e in get_expenses()
                 if e.get("date","")[:10] == dt]

        for i in self.cr_tree.get_children(): self.cr_tree.delete(i)
        for b in bills:
            self.cr_tree.insert("", tk.END, values=(
                b["invoice"], b.get("time", str(b.get("date", ""))[11:16]), b["name"], b["phone"],
                b["payment"],
                fmt_currency(b["discount"]),
                fmt_currency(b["total"]),
            ))
        if hasattr(self, "cr_audit_note_lbl"):
            self.cr_audit_note_lbl.config(
                text="Click a bill row to view billed-by audit info here." if self._show_bill_audit else ""
            )

        total_rev = sum(b["total"] for b in bills)
        total_exp = sum(safe_float(e.get("amount", 0)) for e in exps)
        profit    = total_rev - total_exp

        for w in self.cr_cards.winfo_children():
            w.destroy()
        card_items = [
            ("Bills",       str(len(bills)),         C["purple"]),
            ("Revenue",     fmt_currency(total_rev), C["teal"]),
            ("Expenses",    fmt_currency(total_exp), C["orange"]),
            ("Net Profit",  fmt_currency(profit),
             C["green"] if profit >= 0 else C["red"]),
        ]
        for idx, (lbl, val, col) in enumerate(card_items):
            card = tk.Frame(self.cr_cards, bg=col, padx=scaled_value(14, 12, 10), pady=scaled_value(8, 8, 6), height=scaled_value(58, 54, 48))
            card.grid(row=0, column=idx, sticky="nsew",
                      padx=(0, 8 if idx < 3 else 0))
            card.grid_propagate(False)
            tk.Label(card, text=val, font=("Arial", scaled_value(14, 13, 11), "bold"),
                     bg=col, fg="white").pack(anchor="w")
            tk.Label(card, text=lbl, font=("Arial", scaled_value(10, 10, 9)),
                     bg=col, fg="white").pack(anchor="w")

    def _preview_bill(self, e=None):
        """Show full bill text for selected row in closing report.
        Fix R11e: try/except Ã¢â‚¬â€ bill preview crash prevention."""
        sel = self.cr_tree.selection()
        if not sel: return
        try:
            self._preview_bill_inner(e)
        except Exception as ex:
            app_log(f"[_preview_bill] {ex}")

    def _preview_bill_inner(self, e=None):
        sel = self.cr_tree.selection()
        if not sel: return
        v   = self.cr_tree.item(sel[0], "values")
        inv = str(v[0]).strip()
        dt  = self.cr_date.get().strip()
        if validate_display_date(dt):
            dt = display_to_iso_date(dt)

        from reports import _build_bill_text

        matched = next((b for b in _read_bills_for_date(dt) if str(b.get("invoice", "")).strip() == inv), None)
        audit_note = ""
        if matched:
            bill_time = matched.get("time", str(matched.get("date", ""))[11:16]).strip()
            created_by = str(matched.get("created_by", "")).strip()
            billed_by = created_by or "Unknown"
            if hasattr(self, "cr_audit_note_lbl"):
                self.cr_audit_note_lbl.config(
                    text=f"Billed By: {billed_by}    Time: {bill_time or '--:--'}"
                )

        self.cr_preview.config(state="normal")
        self.cr_preview.delete("1.0", tk.END)
        if matched:
            bill_text = _build_bill_text(matched)
            self.cr_preview.insert(tk.END, bill_text + audit_note)
        else:
            # Fallback: show basic info from tree
            info = (f"Invoice  : {v[0]}\n"
                    f"Time     : {v[1]}\n"
                    f"Customer : {v[2]}\n"
                    f"Phone    : {v[3]}\n"
                    f"Payment  : {v[4]}\n"
                    f"Discount : {v[5]}\n"
                    f"Total    : {v[6]}\n"
                    + "\n"
                    f"(Detailed bill data not available)")
            self.cr_preview.insert(tk.END, info)
        self.cr_preview.config(state="disabled")

    def _save_pdf(self):
        """Fix R11f: cross-platform file open."""
        dt = self.cr_date.get().strip()
        if validate_display_date(dt):
            dt = display_to_iso_date(dt)
        try:
            path = generate_closing_pdf(dt)
            messagebox.showinfo("Saved", f"Closing report saved:\n{path}")
            try:
                open_file_cross_platform(path)
            except Exception:
                pass
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # Ã¢â€â‚¬Ã¢â€â‚¬ Profit Analysis Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
    def _build_profit(self, parent):
        ctrl_card = tk.Frame(parent, bg=C["card"])
        ctrl_card.pack(fill=tk.X, padx=15, pady=(8, 8))

        hdr = tk.Frame(ctrl_card, bg=C.get("nav", C["card"]))
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="Service Profit Controls",
                 font=("Arial", 11, "bold"),
                 bg=C.get("nav", C["card"]), fg=C["text"]).pack(side=tk.LEFT, padx=14, pady=8)
        tk.Label(hdr, text="Switch between this month and all-time performance",
                 font=("Arial", 10),
                 bg=C.get("nav", C["card"]), fg=C["muted"]).pack(side=tk.RIGHT, padx=14, pady=8)

        ctrl = tk.Frame(ctrl_card, bg=C["card"], pady=10, padx=14)
        ctrl.pack(fill=tk.X)

        for txt, cmd in [
            ("This Month", self._profit_month),
            ("All Time",   self._profit_all),
        ]:
            ModernButton(ctrl, text=txt, command=cmd,
                         color=C["teal"], hover_color=C["blue"],
                         width=scaled_value(124, 116, 96), height=scaled_value(34, 32, 28), radius=8,
                         font=("Arial",scaled_value(10, 10, 9),"bold"),
                         ).pack(side=tk.LEFT, padx=(0,6))

        body = tk.Frame(parent, bg=C["bg"])
        body.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 8))

        cols = ("Service", "Times Used", "Total Revenue", "% of Revenue")
        self.pa_tree = ttk.Treeview(body, columns=cols,
                                     show="headings", height=20)
        self._pa_cols = cols
        for col in cols:
            self.pa_tree.heading(col, text=col,
                                  command=lambda c=col: self._sort_pa(c))
            self.pa_tree.column(col, width=scaled_value(160, 140, 120))
        apply_treeview_column_alignment(self.pa_tree)
        vsb = ttk.Scrollbar(body, orient="vertical",
                             command=self.pa_tree.yview)
        self.pa_tree.configure(yscrollcommand=vsb.set)
        self.pa_tree.pack(fill=tk.BOTH, expand=True,
                           side=tk.LEFT)
        vsb.pack(side=tk.LEFT, fill=tk.Y)
        body.bind("<Configure>", self._resize_profit_columns, add="+")

        self._sort_pa_col = "Total Revenue"
        self._profit_month()

    def _load_profit(self, from_d="", to_d=""):
        """Fix R11g: try/except wrapper Ã¢â‚¬â€ CSV read crash prevention."""
        try:
            self._load_profit_inner(from_d, to_d)
        except Exception as e:
            app_log(f"[_load_profit] {e}")

    def _load_profit_inner(self, from_d="", to_d=""):
        for i in self.pa_tree.get_children(): self.pa_tree.delete(i)
        svc_rev   = defaultdict(float)
        svc_count = defaultdict(int)
        all_total = 0.0

        if os.path.exists(F_REPORT):
            with open(F_REPORT, "r", encoding="utf-8") as f:
                r   = csv.reader(f)
                hdr = next(r, None)
                ir  = 6 if (hdr and len(hdr) >= 7) else -1
                for row in r:
                    if not row: continue
                    if from_d and row[0][:10] < from_d: continue
                    if to_d   and row[0][:10] > to_d:   continue
                    if ir > 0 and len(row) > ir:
                        for seg in row[ir].split("|"):
                            parts = seg.split("~")
                            if len(parts)==4 and parts[0]=="services":
                                try:
                                    amt = float(parts[2])*int(parts[3])
                                    svc_rev[parts[1]]   += amt
                                    svc_count[parts[1]] += int(parts[3])
                                    all_total           += amt
                                except Exception:
                                    pass

        rows = sorted(svc_rev.items(),
                       key=lambda x: x[1], reverse=True)
        for svc, rev in rows:
            pct = (rev / all_total * 100) if all_total else 0
            self.pa_tree.insert("", tk.END, values=(
                svc,
                svc_count[svc],
                fmt_currency(rev),
                f"{pct:.1f}%",
            ))

    def _profit_month(self):
        """Fix R11h: try/except Ã¢â‚¬â€ crash prevention."""
        try:
            mo = date.today().strftime("%Y-%m-01")
            self._load_profit(from_d=mo, to_d=today_str())
        except Exception as e:
            app_log(f"[_profit_month] {e}")

    def _profit_all(self):
        """Fix R11i: try/except Ã¢â‚¬â€ crash prevention."""
        try:
            self._load_profit()
        except Exception as e:
            app_log(f"[_profit_all] {e}")

    def _sort_pa(self, col):
        self._sort_pa_col = col
        rows = [(self.pa_tree.set(k, col), k)
                for k in self.pa_tree.get_children("")]
        try:
            rows.sort(key=lambda x: float(
                x[0].replace("Ã¢â€šÂ¹","").replace(",","").replace("%","")),
                       reverse=True)
        except Exception:
            rows.sort(reverse=True)
        for i, (_, k) in enumerate(rows):
            self.pa_tree.move(k, "", i)

    def _resize_closing_columns(self, event=None):
        if event is None:
            return
        width = max(520, event.width - 18)
        col_map = {
            "Invoice": max(92, int(width * 0.13)),
            "Time": max(68, int(width * 0.09)),
            "Customer": max(118, int(width * 0.17)),
            "Phone": max(96, int(width * 0.13)),
            "Payment": max(78, int(width * 0.11)),
            "Discount": max(92, int(width * 0.11)),
        }
        used = sum(col_map.values())
        col_map["Total"] = max(114, width - used)
        for col in self._cr_cols:
            self.cr_tree.column(col, width=col_map[col])

    def _resize_profit_columns(self, event=None):
        if event is None:
            return
        width = max(520, event.width - 18)
        col_map = {
            "Service": max(200, int(width * 0.42)),
            "Times Used": max(92, int(width * 0.16)),
            "Total Revenue": max(118, int(width * 0.22)),
        }
        used = sum(col_map.values())
        col_map["% of Revenue"] = max(108, width - used)
        for col in self._pa_cols:
            self.pa_tree.column(col, width=col_map[col])

    def refresh(self):
        """Fix R11j: try/except Ã¢â‚¬â€ crash prevention."""
        try:
            self._preview()
            self._profit_month()
        except Exception as e:
            app_log(f"[closing_report refresh] {e}")
