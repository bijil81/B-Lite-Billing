"""
print_templates.py  –  BOBY'S Salon
Template definitions, preset configurations, and the Print Settings UI panel.

Templates:
  thermal_58mm  – 32 chars, 58mm paper
  thermal_80mm  – 42 chars, 80mm paper
  a4_standard   – 80 chars, A4 PDF

Changes:
  - Preview now calls generate_bill(template, settings, bill) for correct dispatch
  - Added TEMPLATE_WIDTHS re-export for convenience
  - simulate_settings_cases updated to use generate_bill()
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os

from utils import C, DATA_DIR
from print_engine import get_print_settings, save_print_settings
from ui_theme import ModernButton
from ui_responsive import get_responsive_metrics, scaled_value
from branding import get_branding_logo_path, get_invoice_branding


# ── Template presets ───────────────────────────────────────────────────────

TEMPLATES = {
    "thermal_58mm": {
        "name":          "Thermal 58mm",
        "printer_width": 32,
        "description":   "Standard 58mm thermal printer (32 char wide)",
    },
    "thermal_72mm": {
        "name":          "Thermal 72mm",
        "printer_width": 38,
        "description":   "72mm thermal printer (38 char wide)",
    },
    "thermal_76mm": {
        "name":          "Thermal 76mm",
        "printer_width": 40,
        "description":   "76mm thermal printer (40 char wide)",
    },
    "thermal_80mm": {
        "name":          "Thermal 80mm",
        "printer_width": 42,
        "description":   "Wide 80mm thermal printer (42 char wide)",
    },
    "thermal_112mm": {
        "name":          "Thermal 112mm (Kitchen)",
        "printer_width": 60,
        "description":   "Kitchen/counter 112mm thermal printer (60 char wide)",
    },
    "a5_halfpage": {
        "name":          "A5 Half Page",
        "printer_width": 62,
        "description":   "A5 half-page layout for medium invoices",
    },
    "a4_standard": {
        "name":          "A4 Standard",
        "printer_width": 80,
        "description":   "A4 PDF with logo, table layout, proper margins",
    },
    "invoice_compact": {
        "name":          "Invoice Compact",
        "printer_width": 42,
        "description":   "Compact A4 invoice (thermal 80mm width on A4 page)",
    },
    "invoice_detailed": {
        "name":          "Invoice Detailed",
        "printer_width": 80,
        "description":   "Full A4 invoice with expanded item details",
    },
}

TEMPLATE_WIDTHS = {
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


# ── Preset configurations ──────────────────────────────────────────────────

PRESETS = {
    "Full Receipt": {
        "show_shop_name": True, "show_address": True, "show_phone": True,
        "show_gst_no": False, "show_invoice_number": True,
        "show_date": True, "show_time": True,
        "show_customer_name": True, "show_customer_phone": True,
        "show_payment_method": True, "show_item_numbering": False,
        "show_services_section": True, "show_products_section": True,
        "show_subtotal": True, "show_discount": True,
        "show_membership_discount": True, "show_loyalty_points": True,
        "show_offer_discount": True, "show_gst": True,
        "show_grand_total": True, "show_footer": True,
        "show_separator_lines": True, "double_width_total": True,
    },
    "Minimal Receipt": {
        "show_shop_name": True, "show_address": False, "show_phone": False,
        "show_gst_no": False, "show_invoice_number": True,
        "show_date": True, "show_time": False,
        "show_customer_name": True, "show_customer_phone": False,
        "show_payment_method": True, "show_item_numbering": False,
        "show_services_section": True, "show_products_section": True,
        "show_subtotal": False, "show_discount": True,
        "show_membership_discount": False, "show_loyalty_points": False,
        "show_offer_discount": True, "show_gst": False,
        "show_grand_total": True, "show_footer": True,
        "show_separator_lines": True, "double_width_total": True,
    },
    "GST Invoice": {
        "show_shop_name": True, "show_address": True, "show_phone": True,
        "show_gst_no": True, "show_invoice_number": True,
        "show_date": True, "show_time": True,
        "show_customer_name": True, "show_customer_phone": True,
        "show_payment_method": True, "show_item_numbering": True,
        "show_services_section": True, "show_products_section": True,
        "show_subtotal": True, "show_discount": True,
        "show_membership_discount": True, "show_loyalty_points": True,
        "show_offer_discount": True, "show_gst": True,
        "show_grand_total": True, "show_footer": True,
        "show_separator_lines": True, "double_width_total": False,
    },
    "No Logo / No Footer": {
        "show_shop_name": True, "show_address": True, "show_phone": True,
        "show_gst_no": False, "show_invoice_number": True,
        "show_date": True, "show_time": True,
        "show_customer_name": True, "show_customer_phone": True,
        "show_payment_method": True, "show_item_numbering": False,
        "show_services_section": True, "show_products_section": True,
        "show_subtotal": True, "show_discount": True,
        "show_membership_discount": True, "show_loyalty_points": True,
        "show_offer_discount": True, "show_gst": False,
        "show_grand_total": True, "show_footer": False,
        "show_separator_lines": True, "double_width_total": True,
    },
}


# ── Section toggle groups ──────────────────────────────────────────────────

TOGGLE_SECTIONS = [
    # Header
    ("show_shop_name",           "Shop Name"),
    ("show_address",             "Address"),
    ("show_phone",               "Phone Number"),
    ("show_gst_no",              "GST Number"),
    # Invoice
    ("show_invoice_number",      "Invoice Number"),
    ("show_date",                "Date"),
    ("show_time",                "Time"),
    # Customer
    ("show_customer_name",       "Customer Name"),
    ("show_customer_phone",      "Customer Phone"),
    ("show_payment_method",      "Payment Method"),
    # Items
    ("show_item_numbering",      "Item Numbering (1, 2, 3\u2026)"),
    ("show_services_section",    "Services Section"),
    ("show_products_section",    "Products Section"),
    # Totals
    ("show_subtotal",            "Subtotal Line"),
    ("show_discount",            "Manual Discount"),
    ("show_membership_discount", "Membership Discount"),
    ("show_loyalty_points",      "Loyalty Points Discount"),
    ("show_offer_discount",      "Offer / Coupon Discount"),
    ("show_gst",                 "GST Amount"),
    ("show_grand_total",         "Grand Total"),
    ("double_width_total",       "Highlight Grand Total"),
    # Footer
    ("show_footer",              "Footer Text"),
    ("show_separator_lines",     "Separator Lines (=, -)"),
    # Logo
    ("show_logo",                "Logo (A4 / image)"),
]


# ── Print Settings UI Panel ────────────────────────────────────────────────

class PrintSettingsPanel(tk.Frame):
    """
    Embeddable Print Settings UI panel.
    Shows toggle for every bill section + template selector + live preview.

    Usage:
        panel = PrintSettingsPanel(parent)
        panel.pack(fill=tk.BOTH, expand=True)
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=C["bg"], **kwargs)
        self._vars = {}
        self._ps   = get_print_settings()
        self._responsive = get_responsive_metrics(self.winfo_toplevel())
        self._build()

    def _build(self):
        self._responsive = get_responsive_metrics(self.winfo_toplevel())
        compact = self._responsive.get("mode") == "compact"
        left_panel_width = scaled_value(560, 500, 380)
        preview_min_height = scaled_value(28, 24, 18)
        preset_columns = 2 if compact else 3
        # ── Header bar ────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=C["card"], pady=scaled_value(12, 10, 8))
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="\U0001f5a8\ufe0f  Print / Bill Settings",
                 font=("Arial", scaled_value(15, 14, 12), "bold"),
                 bg=C["card"], fg=C["text"]).pack(side=tk.LEFT, padx=20)
        ModernButton(hdr, text="💾 Save",
                     command=self._save,
                     color=C["teal"], hover_color=C["blue"],
                     width=scaled_value(96, 88, 80), height=scaled_value(34, 32, 30), radius=8,
                     font=("Arial", scaled_value(10, 10, 9), "bold"),
                     ).pack(side=tk.RIGHT, padx=8)
        ModernButton(hdr, text="👁 Preview",
                     command=self._preview,
                     color=C["blue"], hover_color="#154360",
                     width=scaled_value(106, 96, 88), height=scaled_value(34, 32, 30), radius=8,
                     font=("Arial", scaled_value(10, 10, 9), "bold"),
                     ).pack(side=tk.RIGHT, padx=4)

        # ── Main split: left = controls, right = preview ───────────────────
        main = tk.Frame(self, bg=C["bg"])
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)
        if compact:
            main.grid_columnconfigure(0, weight=1)
            main.grid_rowconfigure(1, weight=1)
        else:
            main.grid_columnconfigure(2, weight=1)
            main.grid_rowconfigure(0, weight=1)

        # Left canvas (scrollable controls) — Phase 7: wider left panel
        left_canvas = tk.Canvas(main, bg=C["bg"], highlightthickness=0, width=left_panel_width)
        left_sb     = ttk.Scrollbar(main, orient="vertical",
                                     command=left_canvas.yview)
        left_canvas.configure(yscrollcommand=left_sb.set)
        if compact:
            left_canvas.grid(row=0, column=0, sticky="nsew")
            left_sb.grid(row=0, column=1, sticky="ns", padx=(0, 6))
        else:
            left_canvas.grid(row=0, column=0, sticky="nsw")
            left_sb.grid(row=0, column=1, sticky="ns", padx=(0, 8))

        lf = tk.Frame(left_canvas, bg=C["bg"])
        _win = left_canvas.create_window((0, 0), window=lf, anchor="nw")
        lf.bind("<Configure>",
                lambda e: left_canvas.configure(
                    scrollregion=left_canvas.bbox("all")))
        left_canvas.bind("<Configure>",
                         lambda e: left_canvas.itemconfig(_win, width=e.width))

        def _scroll(e):
            left_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        left_canvas.bind("<Enter>",
                         lambda e: left_canvas.bind_all("<MouseWheel>", _scroll))
        left_canvas.bind("<Leave>",
                         lambda e: left_canvas.unbind_all("<MouseWheel>"))

        # ── Template selector ──────────────────────────────────────────────
        _lf_tmpl_card = tk.Frame(lf, bg=C["card"])
        _lf_tmpl_card.pack(fill=tk.X, padx=8, pady=(0, 4))
        _lfh = tk.Frame(_lf_tmpl_card, bg=C["sidebar"], padx=12, pady=6)
        _lfh.pack(fill=tk.X)
        tk.Label(_lfh, text="📋  Template", font=("Arial",11,"bold"),
                 bg=C["sidebar"], fg=C["text"]).pack(side=tk.LEFT)
        tk.Frame(_lf_tmpl_card, bg=C["accent"], height=2).pack(fill=tk.X)
        tmpl_card = tk.Frame(_lf_tmpl_card, bg=C["card"], padx=12, pady=8)
        tmpl_card.pack(fill=tk.X)

        tk.Label(tmpl_card, text="Paper / Template:",
                 bg=C["card"], fg=C["muted"],
                 font=("Arial", scaled_value(11, 11, 10))).pack(anchor="w")
        self._tmpl_var = tk.StringVar(value=self._ps.get("template", "thermal_58mm"))
        tmpl_cb = ttk.Combobox(tmpl_card, textvariable=self._tmpl_var,
                               values=list(TEMPLATES.keys()),
                               state="readonly", font=("Arial", scaled_value(11, 11, 10)),
                               width=scaled_value(34, 32, 28))
        tmpl_cb.pack(fill=tk.X, ipady=2, pady=(3, 6))
        tmpl_cb.bind("<<ComboboxSelected>>", self._on_template_change)

        self._tmpl_desc = tk.Label(tmpl_card, text="",
                                    bg=C["card"], fg=C["muted"],
                                    font=("Arial", scaled_value(10, 10, 9)),
                                    wraplength=scaled_value(480, 430, 320))
        self._tmpl_desc.pack(anchor="w")
        self._update_tmpl_desc()

        # Preset buttons
        preset_head = tk.Frame(tmpl_card, bg=C["card"])
        preset_head.pack(fill=tk.X, pady=(8, 2))
        tk.Label(preset_head, text="Presets:",
                 bg=C["card"], fg=C["muted"],
                 font=("Arial", scaled_value(10, 10, 9), "bold")).pack(side=tk.LEFT, padx=(0, 6))
        tk.Label(preset_head, text="Quick layouts without button cut-off",
                 bg=C["card"], fg=C["muted"],
                 font=("Arial", scaled_value(9, 9, 8))).pack(side=tk.RIGHT)
        preset_grid = tk.Frame(tmpl_card, bg=C["card"])
        preset_grid.pack(fill=tk.X, pady=(2, 0))
        for col in range(preset_columns):
            preset_grid.grid_columnconfigure(col, weight=1, uniform="preset_buttons")
        for idx, pname in enumerate(PRESETS):
            row = idx // preset_columns
            col = idx % preset_columns
            btn = ModernButton(preset_grid, text=pname,
                         command=lambda p=pname: self._apply_preset(p),
                         color=C["sidebar"], hover_color=C["blue"],
                         width=scaled_value(145, 130, 116), height=scaled_value(32, 30, 28), radius=6,
                         font=("Arial", scaled_value(9, 9, 8), "bold"),
                         )
            btn.grid(row=row, column=col, sticky="ew", padx=(0, 8), pady=(0, 8))

        # ── Footer text ────────────────────────────────────────────────────
        _lf_footer_card = tk.Frame(lf, bg=C["card"])
        _lf_footer_card.pack(fill=tk.X, padx=8, pady=4)
        _lfh = tk.Frame(_lf_footer_card, bg=C["sidebar"], padx=12, pady=6)
        _lfh.pack(fill=tk.X)
        tk.Label(_lfh, text="📝  Footer Text", font=("Arial",11,"bold"),
                 bg=C["sidebar"], fg=C["text"]).pack(side=tk.LEFT)
        tk.Frame(_lf_footer_card, bg=C["accent"], height=2).pack(fill=tk.X)
        footer_card = tk.Frame(_lf_footer_card, bg=C["card"], padx=12, pady=8)
        footer_card.pack(fill=tk.X)
        self._footer_var = tk.StringVar(
            value=self._ps.get("footer_text", get_invoice_branding()["footer"]))
        tk.Entry(footer_card, textvariable=self._footer_var,
                 font=("Arial", 11), bg=C["input"],
                 fg=C["text"], bd=0,
                 insertbackground=C["accent"]).pack(fill=tk.X, ipady=5)

        # ── Logo path ──────────────────────────────────────────────────────
        _lf_logo_card = tk.Frame(lf, bg=C["card"])
        _lf_logo_card.pack(fill=tk.X, padx=8, pady=4)
        _lfh = tk.Frame(_lf_logo_card, bg=C["sidebar"], padx=12, pady=6)
        _lfh.pack(fill=tk.X)
        tk.Label(_lfh, text="🖼  Logo (A4 only)", font=("Arial",11,"bold"),
                 bg=C["sidebar"], fg=C["text"]).pack(side=tk.LEFT)
        tk.Frame(_lf_logo_card, bg=C["blue"], height=2).pack(fill=tk.X)
        logo_card = tk.Frame(_lf_logo_card, bg=C["card"], padx=12, pady=8)
        logo_card.pack(fill=tk.X)
        logo_row = tk.Frame(logo_card, bg=C["card"])
        logo_row.pack(fill=tk.X)
        self._logo_var = tk.StringVar(value=self._ps.get("logo_path", get_branding_logo_path("invoice")))
        tk.Entry(logo_row, textvariable=self._logo_var,
                 font=("Arial", scaled_value(10, 10, 9)), bg=C["input"],
                 fg=C["text"], bd=0,
                 insertbackground=C["accent"],
                 width=scaled_value(40, 34, 24)).pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 6))
        ModernButton(logo_row, text="Browse…",
                     command=self._browse_logo,
                     color=C["sidebar"], hover_color=C["blue"],
                     width=scaled_value(88, 80, 72), height=scaled_value(30, 28, 28), radius=6,
                     font=("Arial", scaled_value(9, 9, 8), "bold"),
                     ).pack(side=tk.LEFT)

        # ── Section toggles ────────────────────────────────────────────────
        _lf_tog_card = tk.Frame(lf, bg=C["card"])
        _lf_tog_card.pack(fill=tk.X, padx=8, pady=4)
        _lfh = tk.Frame(_lf_tog_card, bg=C["sidebar"], padx=12, pady=6)
        _lfh.pack(fill=tk.X)
        tk.Label(_lfh, text="🔘  Section Visibility", font=("Arial",11,"bold"),
                 bg=C["sidebar"], fg=C["text"]).pack(side=tk.LEFT)
        tk.Frame(_lf_tog_card, bg=C["teal"], height=2).pack(fill=tk.X)
        tog_card = tk.Frame(_lf_tog_card, bg=C["card"], padx=12, pady=8)
        tog_card.pack(fill=tk.X)

        qr = tk.Frame(tog_card, bg=C["card"])
        qr.pack(fill=tk.X, pady=(0, 8))
        ModernButton(qr, text="✅ All On",
                     command=lambda: self._set_all(True),
                     color=C["teal"], hover_color=C["blue"],
                     width=80, height=28, radius=6,
                     font=("Arial", 9, "bold"),
                     ).pack(side=tk.LEFT, padx=(0, 6))
        ModernButton(qr, text="❌ All Off",
                     command=lambda: self._set_all(False),
                     color=C["red"], hover_color="#c0392b",
                     width=80, height=28, radius=6,
                     font=("Arial", 9, "bold"),
                     ).pack(side=tk.LEFT)

        for key, label in TOGGLE_SECTIONS:
            var = tk.BooleanVar(value=self._ps.get(key, True))
            self._vars[key] = var
            tk.Checkbutton(tog_card, text=label, variable=var,
                           bg=C["card"], fg=C["text"],
                           selectcolor=C["input"],
                           activebackground=C["card"],
                           activeforeground=C["text"],
                           font=("Arial", 11),
                           cursor="hand2",
                           command=self._preview).pack(anchor="w", pady=1)

        # Validation warnings label
        self._warn_lbl = tk.Label(lf, text="",
                                    bg=C["bg"], fg=C["orange"],
                                    font=("Arial", scaled_value(10, 10, 9)),
                                    wraplength=scaled_value(460, 400, 320),
                                    justify="left")
        self._warn_lbl.pack(anchor="w", padx=8, pady=4)

        # ── Right: live preview ────────────────────────────────────────────
        rp = tk.Frame(main, bg=C["bg"])
        if compact:
            rp.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(10, 0))
        else:
            rp.grid(row=0, column=2, sticky="nsew", padx=(10, 0))
        rp.grid_columnconfigure(0, weight=1)
        rp.grid_rowconfigure(1, weight=1)

        tk.Label(rp, text="\U0001f4c4  Live Preview",
                 font=("Arial", scaled_value(12, 11, 10), "bold"),
                 bg=C["bg"], fg=C["muted"]).grid(row=0, column=0, sticky="w", pady=(4, 4))

        preview_card = tk.Frame(rp, bg=C["card"], padx=scaled_value(12, 10, 8), pady=scaled_value(10, 8, 6))
        preview_card.grid(row=1, column=0, sticky="nsew")
        preview_card.grid_columnconfigure(0, weight=1)
        preview_card.grid_rowconfigure(1, weight=1)

        tk.Label(preview_card,
                 text="Preview stays visible while you adjust template, presets, and bill sections.",
                 bg=C["card"], fg=C["muted"],
                 font=("Arial", scaled_value(9, 9, 8))).grid(row=0, column=0, sticky="w", pady=(0, 8))

        self._preview_txt = tk.Text(
            preview_card, font=("Courier New", scaled_value(10, 9, 8)),
            bg="#ffffff", fg="#1a1a1a",
            padx=10, pady=10, bd=1,
            height=preview_min_height,
            relief="solid", wrap="none")
        self._preview_txt.grid(row=1, column=0, sticky="nsew")

        self._preview()

    # ── Event handlers ─────────────────────────────────────────────────────

    def _on_template_change(self, e=None):
        self._update_tmpl_desc()
        self._preview()

    def _update_tmpl_desc(self):
        tmpl = self._tmpl_var.get()
        info = TEMPLATES.get(tmpl, {})
        self._tmpl_desc.config(text=info.get("description", ""))

    def _apply_preset(self, preset_name: str):
        preset = PRESETS.get(preset_name, {})
        for key, var in self._vars.items():
            if key in preset:
                var.set(preset[key])
        self._preview()

    def _set_all(self, value: bool):
        for var in self._vars.values():
            var.set(value)
        self._preview()

    def _browse_logo(self):
        path = filedialog.askopenfilename(
            title="Select Logo Image",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.gif"),
                       ("All files", "*.*")])
        if path:
            self._logo_var.set(path)

    def _collect_settings(self) -> dict:
        tmpl = self._tmpl_var.get()
        ps   = dict(self._ps)
        ps["template"]      = tmpl
        ps["printer_width"] = TEMPLATES.get(tmpl, {}).get("printer_width", 32)
        ps["footer_text"]   = self._footer_var.get()
        ps["logo_path"]     = self._logo_var.get()
        for key, var in self._vars.items():
            ps[key] = var.get()
        return ps

    def _preview(self, e=None):
        """Generate live preview using generate_bill() for correct dispatch."""
        try:
            from print_engine import generate_bill, BillData
            from print_utils import validate_print_settings

            ps   = self._collect_settings()
            tmpl = ps.get("template", "thermal_58mm")

            demo = BillData(
                invoice        = "INV-202603-00042",
                salon_name     = get_invoice_branding()["header"],
                address        = get_invoice_branding()["address"] or "Kerala, India",
                phone          = get_invoice_branding()["phone"] or "9999999999",
                gst_no         = "29ABCDE1234F1Z5",
                customer_name  = "Priya Menon",
                customer_phone = "9012345678",
                payment_method = "Cash",
                svc_items = [
                    {"mode": "services", "name": "Hair Spa",     "price": 800, "qty": 1},
                    {"mode": "services", "name": "Facial Basic", "price": 600, "qty": 1},
                ],
                prd_items = [
                    {"mode": "products", "name": "Shampoo", "price": 200, "qty": 2},
                ],
                subtotal        = 1800.0,
                discount        = 100.0,
                mem_discount    = 90.0,
                mem_pct         = 10,
                offer_discount  = 50.0,
                offer_name      = "Welcome10",
                gst_amount      = 0.0,
                grand_total     = 1560.0,
                timestamp       = "2026-03-20 14:30",
            )

            warnings = validate_print_settings(ps)
            if warnings:
                self._warn_lbl.config(text="\u26a0  " + " | ".join(warnings))
            else:
                self._warn_lbl.config(text="")

            # Use generate_bill for correct template dispatch
            text = generate_bill(tmpl, ps, demo)
            self._preview_txt.delete("1.0", tk.END)
            self._preview_txt.insert(tk.END, text)

        except Exception as e:
            self._preview_txt.delete("1.0", tk.END)
            self._preview_txt.insert(tk.END, f"Preview error: {e}")

    def _save(self):
        ps = self._collect_settings()
        if save_print_settings(ps):
            self._ps = ps
            messagebox.showinfo("Saved", "\u2705 Print settings saved!")
            self._preview()
        else:
            messagebox.showerror("Error", "Could not save print settings.")

    def refresh(self):
        self._ps = get_print_settings()
        tmpl = self._ps.get("template", "thermal_58mm")
        self._tmpl_var.set(tmpl)
        self._footer_var.set(self._ps.get("footer_text", get_invoice_branding()["footer"]))
        self._logo_var.set(self._ps.get("logo_path", get_branding_logo_path("invoice")))
        for key, var in self._vars.items():
            var.set(self._ps.get(key, True))
        self._update_tmpl_desc()
        self._preview()


# ── Test case simulator (called from print_utils) ──────────────────────────

def simulate_settings_cases():
    """
    Simulate 3 test cases as per spec — returns list of (case_name, text).
    Uses generate_bill() for correct per-template dispatch.
    """
    from print_engine import BillData, generate_bill

    demo_bill = BillData(
        invoice        = "INV-202603-00001",
        salon_name     = get_invoice_branding()["header"],
        address        = get_invoice_branding()["address"] or "Kerala, India",
        phone          = get_invoice_branding()["phone"] or "9999999999",
        gst_no         = "",
        customer_name  = "Priya Menon",
        customer_phone = "9012345678",
        payment_method = "Cash",
        svc_items = [
            {"mode": "services", "name": "Hair Spa", "price": 800, "qty": 1},
            {"mode": "services", "name": "Facial",   "price": 600, "qty": 1},
        ],
        prd_items = [
            {"mode": "products", "name": "Shampoo", "price": 200, "qty": 2},
        ],
        subtotal   = 1800.0,
        discount   = 100.0,
        grand_total = 1700.0,
        timestamp  = "2026-03-20 14:30",
    )

    results = []

    # Case 1: Minimal — no logo, no time, only total
    case1 = {
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
    results.append(("Case 1 \u2014 Minimal",
                    generate_bill("thermal_58mm", case1, demo_bill)))

    # Case 2: Full GST bill
    case2 = {
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
    results.append(("Case 2 \u2014 Full Details",
                    generate_bill("thermal_80mm", case2, demo_bill)))

    # Case 3: Thermal compact
    case3 = {
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
    results.append(("Case 3 \u2014 Receipt",
                    generate_bill("thermal_58mm", case3, demo_bill)))

    return results
