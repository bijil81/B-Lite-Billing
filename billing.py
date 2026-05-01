# -*- coding: utf-8 -*-
"""
Billing workspace wrapper for service/product bill composition.

The billing logic is split across src.blite_v6.billing helper modules.
Keep BillingFrame as the public Tkinter entry point used by main.py.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import difflib
import time
from datetime import datetime
from utils import (C, load_json, save_json, safe_float, sanitize_filename,
                   F_SERVICES, F_REPORT, BILLS_DIR, resource_path,
                   next_invoice, now_str, today_str, month_str,
                   fmt_currency, open_file_cross_platform, popup_window,
                   app_log, validate_phone, open_print_text_fallback)
from branding import get_invoice_branding
from salon_settings import get_settings
from ui_theme import ModernButton
from ui_responsive import get_responsive_metrics, scaled_value
from src.blite_v6.app.window_lifecycle import hide_while_building, reveal_when_ready
from icon_system import get_action_icon, get_nav_icon
from adapters.product_catalog_adapter import (
    list_billing_product_categories,
    list_billing_product_matches,
    refresh_product_catalog_cache,
    use_v5_product_variants_db,
)
from services_v5.inventory_service import InventoryService
from offers import (get_active_offers, apply_offer, find_coupon, get_offers, safe_text)
from redeem_codes import (validate_code, apply_redeem_code, calc_redeem_discount)
from src.blite_v6.billing.barcode_lookup import (
    apply_scanned_product_to_bill,
    find_barcode_in_inventory,
    find_barcode_in_variants,
)
from src.blite_v6.billing.bill_document import (
    apply_printer_width,
    build_bill_data_kwargs,
    build_pdf_path,
)
from src.blite_v6.billing.billing_actions import (
    bill_action_empty_warning,
    bill_saved_message,
    has_bill_items,
    pdf_error_message,
    pdf_saved_message,
    print_error_message,
    printed_message,
    save_error_message,
    save_report_args_from_totals,
    should_auto_clear_after_print,
)
from src.blite_v6.billing.catalog_search import (
    build_category_matches,
    category_values_for_mode,
    data_for_mode,
    find_exact_match,
    format_search_result_label,
    normalize_catalog_item,
    should_use_variant_products,
    smart_search,
    variant_selection_for_item,
)
from src.blite_v6.billing.cart_operations import (
    add_or_merge_cart_item,
    format_cart_quantity_label,
    parse_cart_quantity,
    remove_item_at,
    should_refresh_inventory_cache,
    unit_type_for_variant,
    undo_last_item,
    update_item_price,
    update_item_quantity,
    validate_variant_stock,
)
from src.blite_v6.billing.profit_warning import build_below_cost_warning_state
from src.blite_v6.billing.customer_context import (
    BIRTHDAY_COUPON_MESSAGE,
    build_phone_lookup_state,
    format_membership_info,
    is_birthday_month,
    is_valid_lookup_phone,
)
from src.blite_v6.billing.customer_suggestions import (
    clamp_suggestion_index,
    find_customer_suggestions,
    format_customer_suggestion_label,
    get_customer_suggestion_stats,
)
from src.blite_v6.billing.discounts import (
    build_offer_options,
    clear_offer_state,
    coupon_apply_state,
    discount_toggle_state,
    normalize_coupon_code,
    redeem_apply_state,
    select_offer_state,
    should_clear_offer_info_after_redeem_clear,
)
from src.blite_v6.billing.sale_margin_warning import build_sale_margin_warning_state
from src.blite_v6.billing.report_persistence import (
    SaveLegacyReportDependencies,
    save_report_legacy_core,
)
from src.blite_v6.billing.sale_margin_alerts import build_sale_margin_alert_text
from src.blite_v6.settings.billing_alert_preferences import is_below_cost_alert_enabled
from src.blite_v6.billing.runtime_services import (
    auto_save_customer as _auto_save_customer,
    billing_card_fg as _billing_card_fg,
    billing_entry_fg as _billing_entry_fg,
    billing_get_customers as _billing_get_customers,
    billing_record_visit as _billing_record_visit,
    billing_redeem_points as _billing_redeem_points,
    billing_save_customer as _billing_save_customer,
    load_services_products as _load_services_products,
)
from src.blite_v6.billing.totals import calculate_billing_totals
from src.blite_v6.billing.ui_actions import (
    billing_bind_all_shortcut_specs,
    billing_context_action_specs,
    billing_context_copy_specs,
    billing_root_shortcut_specs,
    billing_widget_shortcut_specs,
    booking_clear_confirmation_message,
    booking_prefill_values,
    build_billing_context_extra,
    context_total_from_totals,
    fast_mode_button_view,
    format_context_clipboard_value,
    has_existing_booking_draft,
    next_fast_mode,
    refresh_action_sequence,
    reload_services_reset_state,
    should_show_billing_context_menu,
)
from src.blite_v6.billing.ui_bindings import (
    bind_barcode_entry,
    bind_bill_preview_text,
    bind_customer_lookup_entries,
    bind_discount_entry,
    bind_quantity_entry,
    bind_search_entry,
)
from src.blite_v6.billing.ui_sections import (
    calculate_bill_preview_font,
    calculate_left_panel_width,
    configure_billing_combobox_style,
    create_card_section,
    create_intro_card,
    create_scrollable_panel,
    finish_action_specs,
    quantity_unit_hint_view,
    resize_preview_font,
    resolve_billing_mode,
    sync_billing_split,
)
from src.blite_v6.billing.whatsapp_actions import (
    extract_whatsapp_error,
    invalid_phone_message,
    whatsapp_manual_send_message,
    whatsapp_exception_message,
    whatsapp_send_error_message,
    whatsapp_send_success_message,
    whatsapp_session_result,
    whatsapp_status_view,
)
from src.blite_v6.ui.input_behaviors import (
    attach_display_date_mask,
    attach_first_letter_caps,
    date_for_display,
)
# Billing workspace frame
class BillingFrame(tk.Frame):

    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app          = app
        self.mode         = "services"
        self.bill_items   = []
        self._inventory_lookup_cache = None
        self._inventory_lookup_cache_time = 0.0
        self.payment_var  = tk.StringVar(value="Cash")
        self.gst_enabled  = tk.BooleanVar(value=False)
        self.disc_enabled = tk.BooleanVar(value=False)

        self.services_data, self.products_data = _load_services_products()
        self._current_invoice     = next_invoice()
        self._applied_offer       = None
        self._applied_redeem_code = None
        self._membership_disc_pct = 0.0

        self.fast_mode = False
        self._saved_invoices = set()  # Fix: duplicate bill save guard
        self._sale_margin_alert_job = None
        self._sale_margin_alert_blink_job = None
        self._sale_margin_alert_blink_state = False
        self._sale_margin_alert_text = ""

        self._build()
        self._bind_shortcuts()
        self.set_mode(self._initial_billing_mode)
        self.clear_all()

    # ==================== BUILD ====================
    def _build(self):
        cfg      = get_settings()
        billing_mode_state = resolve_billing_mode(cfg)
        billing_mode = billing_mode_state["billing_mode"]
        show_services = billing_mode_state["show_services"]
        show_products = billing_mode_state["show_products"]
        self._billing_mode = billing_mode
        self._show_services = show_services
        self._show_products = show_products
        self._initial_billing_mode = billing_mode_state["initial_mode"]
        W        = self
        ui_scale = float(cfg.get("ui_scale", 1.0))
        metrics  = get_responsive_metrics(W)
        compact_mode = metrics["mode"] == "compact"
        section_title_font = ("Arial", scaled_value(14, 13, 12), "bold")
        section_meta_font = ("Arial", scaled_value(10, 9, 9))
        label_font = ("Arial", scaled_value(11, 10, 9))
        entry_font = ("Arial", scaled_value(11, 10, 9))
        compact_pad = scaled_value(12, 10, 8)
        compact_inner_pad = scaled_value(10, 8, 6)
        action_btn_h = scaled_value(40, 36, 32)
        action_font = ("Arial", scaled_value(11, 10, 9), "bold")

        configure_billing_combobox_style(C)

        try:
            _sh = self.winfo_screenheight()
        except Exception:
            _sh = 768
        bill_font = calculate_bill_preview_font(_sh)
        self._print_font = int(cfg.get("print_font_size", 7))

        try:
            _sw = W.winfo_screenwidth()
        except Exception:
            _sw = 1366
        lp_width = calculate_left_panel_width(
            _sw,
            ui_scale,
            compact_mode,
            scaled_value(340, 290, 240),
            scaled_value(500, 420, 320),
        )
        preview_ratio = metrics["preview_ratio"]
        paned = ttk.PanedWindow(W, orient="horizontal")
        paned.pack(fill=tk.BOTH, expand=True, padx=(8, 10), pady=6)
        self._responsive_paned = paned

        # Left billing composer pane
        left_panel = create_scrollable_panel(paned, lp_width, C)
        lp_outer = left_panel["outer"]
        paned.add(lp_outer, weight=scaled_value(4, 5, 6))
        lp = left_panel["body"]

        # Workspace intro
        create_intro_card(
            lp,
            C,
            section_title_font,
            section_meta_font,
            compact_pad,
            scaled_value(12, 10, 8),
        )

        # Mode buttons
        mf_outer = tk.Frame(lp, bg=C["card"])
        mf_outer.pack(fill=tk.X, pady=(0, 8))
        mf_head = tk.Frame(mf_outer, bg=C["sidebar"], padx=compact_pad, pady=scaled_value(6, 5, 4))
        mf_head.pack(fill=tk.X)
        tk.Label(mf_head, text="Billing Mode",
                 font=(label_font[0], label_font[1], "bold"),
                 bg=C["sidebar"], fg=C["text"]).pack(side=tk.LEFT)
        tk.Label(mf_head, text="Choose what you are adding",
                 font=section_meta_font,
                 bg=C["sidebar"], fg=C["muted"]).pack(side=tk.RIGHT)
        tk.Frame(mf_outer, bg=C["blue"], height=2).pack(fill=tk.X)
        mf = tk.Frame(mf_outer, bg=C["card"], padx=compact_pad, pady=compact_inner_pad)
        mf.pack(fill=tk.X)
        svc_icon = get_nav_icon("billing")
        prd_icon = get_nav_icon("inventory")
        self.btn_svc = ModernButton(mf, text="Services",
            image=svc_icon, compound="left",
            command=lambda: self.set_mode("services"),
            color=C["teal"], hover_color=C["blue"],
            width=scaled_value(140, 120, 100), height=scaled_value(38, 34, 30), radius=8, font=action_font)
        if show_services:
            self.btn_svc.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4 if show_products else 0))
        self.btn_prd = ModernButton(mf, text="Products",
            image=prd_icon, compound="left",
            command=lambda: self.set_mode("products"),
            color=C["sidebar"], hover_color=C["blue"],
            width=scaled_value(140, 120, 100), height=scaled_value(38, 34, 30), radius=8, font=action_font)
        if show_products:
            self.btn_prd.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Customer section
        cx = create_card_section(
            lp,
            C,
            "Customer",
            "Existing or walk-in lookup",
            C["teal"],
            (label_font[0], label_font[1], "bold"),
            section_meta_font,
            header_padx=compact_pad,
            header_pady=scaled_value(6, 5, 4),
            body_padx=compact_pad,
            body_pady=compact_inner_pad,
        )

        nf = tk.Frame(cx, bg=C["card"])
        nf.pack(fill=tk.X, pady=(0, 4))
        tk.Label(nf, text="Name:", bg=C["card"],
                 fg=C["muted"], font=label_font).pack(anchor="w")
        self.name_ent = tk.Entry(nf, font=entry_font,
                                 bg=C["input"], fg=_billing_entry_fg(),
                                 bd=0, insertbackground=C["accent"])
        self.name_ent.pack(fill=tk.X, ipady=5)
        self._suggest_name_host = tk.Frame(nf, bg=C["card"])
        self._suggest_name_host.pack(fill=tk.X, pady=(2, 0))
        self._suggest_name_host.pack_forget()

        pf = tk.Frame(cx, bg=C["card"])
        pf.pack(fill=tk.X)
        tk.Label(pf, text="Phone:", bg=C["card"],
                 fg=C["muted"], font=label_font).pack(anchor="w")
        self.phone_ent = tk.Entry(pf, font=entry_font,
                                  bg=C["input"], fg=_billing_entry_fg(),
                                  bd=0, insertbackground=C["accent"])
        self.phone_ent.pack(fill=tk.X, ipady=5)
        self._suggest_phone_host = tk.Frame(pf, bg=C["card"])
        self._suggest_phone_host.pack(fill=tk.X, pady=(2, 0))
        self._suggest_phone_host.pack_forget()

        self._suggest_win   = None
        self._suggest_list  = None
        self._suggest_items = []
        self._suggest_field = None
        self._suggest_customers = {}

        bind_customer_lookup_entries(self)
        attach_first_letter_caps(self.name_ent)

        bd_row = tk.Frame(cx, bg=C["card"])
        bd_row.pack(fill=tk.X, pady=(6, 0))
        tk.Label(bd_row, text="Birthday (DD-MM-YYYY):",
                 bg=C["card"], fg=C["muted"],
                 font=label_font).pack(side=tk.LEFT, padx=(0, 6))
        self.bday_ent = tk.Entry(bd_row, font=entry_font,
                                   bg=C["input"], fg=_billing_entry_fg(C["gold"]),
                                   bd=0, width=14,
                                   insertbackground=C["accent"])
        self.bday_ent.pack(side=tk.LEFT, ipady=4)
        attach_display_date_mask(self.bday_ent)
        self.new_cust_lbl = tk.Label(bd_row, text="",
                                     bg=C["card"], fg=C["lime"],
                                     font=("Arial", 10, "bold"))
        self.new_cust_lbl.pack(side=tk.RIGHT)

        pts_row = tk.Frame(cx, bg=C["card"])
        pts_row.pack(fill=tk.X, pady=(4, 0))
        self.pts_lbl = tk.Label(pts_row, text="Points: -",
                                bg=C["card"], fg=C["gold"],
                                font=("Arial", 11))
        self.pts_lbl.pack(side=tk.LEFT)
        self.package_info_lbl = tk.Label(
            cx,
            text="",
            bg=C["card"],
            fg=C["gold"],
            font=("Arial", 9, "bold"),
            justify="left",
            anchor="w",
            wraplength=320,
        )
        self.package_info_lbl.pack(fill=tk.X, pady=(4, 0))
        cx.bind("<Configure>", self._on_customer_panel_resize)
        self.phone_ent.bind("<FocusOut>", self._on_phone_lookup)

        # Add Item Box
        self.s_box = create_card_section(
            lp,
            C,
            "Add Services",
            "Search and add with quantity",
            C["accent"],
            ("Arial", 11, "bold"),
            ("Arial", 9),
        )
        self._sbox_lbl = self.s_box.section_title_label

        tk.Label(self.s_box, text="Category:", bg=C["card"],
                 fg=C["muted"], font=("Arial", 11)).pack(anchor="w")
        self.cat_v  = tk.StringVar(value="All")
        self.cat_cb = ttk.Combobox(self.s_box, textvariable=self.cat_v,
                                   state="readonly", font=("Arial", 11),
                                   style="Billing.TCombobox")
        self.cat_cb.pack(fill=tk.X, pady=(2, 4))
        self.cat_cb.bind("<<ComboboxSelected>>",
                         lambda e: self._on_cat_selected())
        self.cat_cb.bind("<MouseWheel>", lambda e: "break")

        tk.Label(self.s_box, text="Search (name / code):", bg=C["card"],
                 fg=C["muted"], font=("Arial", 11)).pack(anchor="w")
        self.search_var = tk.StringVar()

        # Search suggestion row
        self._ss_row = tk.Frame(self.s_box, bg=C["input"],
                                highlightthickness=1,
                                highlightbackground=C["input"],
                                highlightcolor=C["teal"])
        self._ss_row.pack(fill=tk.X, pady=(2, 4))

        self.search_ent = tk.Entry(self._ss_row,
                                   textvariable=self.search_var,
                                   font=("Arial", 12),
                                   bg=C["input"], fg=C["text"],
                                   bd=0, insertbackground=C["accent"],
                                   relief="flat")
        self.search_ent.pack(side=tk.LEFT, fill=tk.X,
                             expand=True, ipady=6, padx=(6, 0))

        def _toggle_dropdown(e=None):
            self._ss_toggle_pending = True
            is_open = bool(self._ss_win and self._ss_win.winfo_exists())
            self.after(10, lambda: setattr(self, "_ss_toggle_pending", False))
            if is_open:
                self._ss_suppress_focus = True          # block FocusIn after close
                self.after(300, lambda: setattr(        # release after focus settles
                    self, "_ss_suppress_focus", False))
                self._ss_hide()
                self._ss_arrow_btn.config(text="v")
            else:
                self.search_ent.focus_set()
                self._ss_show_all_for_cat()
                self._ss_arrow_btn.config(text="^")

        self._ss_arrow_btn = tk.Button(
            self._ss_row, text="v",
            command=_toggle_dropdown,
            bg=C["input"], fg=C["muted"],
            font=("Arial", 9), bd=0,
            padx=8, pady=0,
            cursor="hand2", relief="flat",
            activebackground=C["teal"],
            activeforeground="white")
        self._ss_arrow_btn.pack(side=tk.RIGHT, fill=tk.Y)

        self._ss_host = tk.Frame(self.s_box, bg=C["card"])
        self._ss_host.pack(fill=tk.X, pady=(0, 4))
        self._ss_host.pack_forget()

        self._ss_win            = None
        self._ss_lb             = None
        self._ss_items          = []
        self._ss_toggle_pending = False
        self._ss_suppress_focus = False

        bind_search_entry(self)

        # Phase 6: Barcode scanner field - dedicated scan input for cashier-speed lookup.
        # USB barcode scanners act as keyboard input and send Enter after the barcode.
        self._scan_var = tk.StringVar()
        scan_outer = tk.Frame(self.s_box, bg=C["card"])
        scan_outer.pack(fill=tk.X, pady=(4, 4))
        scan_header = tk.Frame(scan_outer, bg=C["sidebar"], padx=12, pady=4)
        scan_header.pack(fill=tk.X)
        tk.Label(scan_header, text="Barcode Scan",
                 font=("Arial", 10, "bold"),
                 bg=C["sidebar"], fg=C["text"]).pack(side=tk.LEFT)
        tk.Label(scan_header, text="Scan barcode or type barcode and press Enter",
                 font=("Arial", 8), bg=C["sidebar"], fg=C["muted"]).pack(side=tk.RIGHT)
        tk.Frame(scan_outer, bg=C["teal"], height=2).pack(fill=tk.X)
        scan_row_f = tk.Frame(scan_outer, bg=C["card"], padx=12, pady=6)
        scan_row_f.pack(fill=tk.X)
        self.scan_entry = tk.Entry(scan_row_f, textvariable=self._scan_var,
                                   font=("Arial", 12), bg=C["input"],
                                   fg=C["text"], bd=0,
                                   insertbackground=C["accent"])
        self.scan_entry.pack(side=tk.LEFT, fill=tk.X, expand=True,
                             ipady=6, padx=(0, 6))
        bind_barcode_entry(self)
        self.scan_label = tk.Label(scan_row_f, text="",
                                   bg=C["card"], fg=C["muted"],
                                   font=("Arial", 9))
        self.scan_label.pack(side=tk.RIGHT)

        pr_row = tk.Frame(self.s_box, bg=C["card"])
        pr_row.pack(fill=tk.X, pady=(0, 6))

        pf2 = tk.Frame(pr_row, bg=C["card"])
        pf2.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        tk.Label(pf2, text="Price (Rs):", bg=C["card"],
                 fg=C["muted"], font=("Arial", 11)).pack(anchor="w")
        self.price_ent = tk.Entry(pf2, font=("Arial", 12, "bold"),
                                  bg=C["input"], fg=_billing_entry_fg(C["accent"]),
                                  bd=0, insertbackground=C["accent"])
        self.price_ent.pack(fill=tk.X, ipady=5)

        qf = tk.Frame(pr_row, bg=C["card"])
        qf.pack(side=tk.RIGHT, fill=tk.Y)
        qty_head = tk.Frame(qf, bg=C["card"])
        qty_head.pack(fill=tk.X)
        self.qty_lbl = tk.Label(qty_head, text="Qty:", bg=C["card"],
                                fg=C["muted"], font=("Arial", 11))
        self.qty_lbl.pack(side=tk.LEFT, anchor="w")
        self.unit_hint_f = tk.Frame(qty_head, bg=C["card"])
        self.unit_hint_f.pack(side=tk.RIGHT, padx=(8, 0))
        self.unit_badge_lbl = tk.Label(
            self.unit_hint_f,
            text="Unit: select item",
            bg=C["sidebar"],
            fg=C["text"],
            font=("Arial", 8, "bold"),
            padx=7,
            pady=1,
        )
        self.unit_badge_lbl.pack()
        self.qty_ent = tk.Entry(qf, font=("Arial", 12, "bold"),
                                bg=C["input"], fg=_billing_entry_fg(C["lime"]),
                                bd=0, width=16,
                                insertbackground=C["accent"])
        self.qty_ent.pack(fill=tk.X, ipady=5)
        self.qty_ent.insert(0, "1")
        bind_quantity_entry(self)

        self.unit_helper_lbl = tk.Label(
            qf,
            text="Unit updates after product select",
            bg=C["card"],
            fg=C["muted"],
            font=("Arial", 8),
        )
        self.unit_helper_lbl.pack(anchor="e")
        self._refresh_quantity_unit_hint()

        ab=tk.Frame(self.s_box,bg=C["card"]); ab.pack(fill=tk.X,pady=(6,0))
        add_icon = get_action_icon("add")
        clear_icon = get_action_icon("clear")
        save_icon = get_action_icon("save")
        pdf_icon = get_action_icon("pdf")
        print_icon = get_action_icon("print")
        wa_icon = get_action_icon("whatsapp")

        ModernButton(ab,text="Add Item",image=add_icon,compound="left",command=self.add_item,
            color=C["accent"],hover_color=C["purple"],width=140,height=36,radius=8,
            font=("Arial",11,"bold")).pack(side=tk.LEFT,fill=tk.X,expand=True,padx=(0,3))
        ModernButton(ab,text="Undo Last",image=clear_icon,compound="left",command=self.undo_last,
            color=C["orange"],hover_color="#d35400",width=80,height=36,radius=8,
            font=("Arial",11,"bold")).pack(side=tk.LEFT)

        # Options
        ob = create_card_section(
            lp,
            C,
            "Pricing & Payment",
            "GST, discounts, points, payment mode",
            C["blue"],
            ("Arial", 11, "bold"),
            ("Arial", 9),
        )

        or1 = tk.Frame(ob, bg=C["card"])
        or1.pack(fill=tk.X)
        tk.Checkbutton(or1, text="GST 18%",
                       variable=self.gst_enabled,
                       command=self._refresh_bill,
                       bg=C["card"], fg=_billing_card_fg(),
                       activeforeground=_billing_card_fg(),
                       selectcolor=C["input"],
                       font=("Arial", 11),
                       cursor="hand2").pack(side=tk.LEFT, padx=(0, 12))
        tk.Checkbutton(or1, text="Discount",
                       variable=self.disc_enabled,
                       command=self._toggle_discount,
                       bg=C["card"], fg=_billing_card_fg(),
                       activeforeground=_billing_card_fg(),
                       selectcolor=C["input"],
                       font=("Arial", 11),
                       cursor="hand2").pack(side=tk.LEFT)

        or2 = tk.Frame(ob, bg=C["card"])
        or2.pack(fill=tk.X, pady=(6, 0))
        tk.Label(or2, text="Disc Rs:", bg=C["card"],
                 fg=C["muted"], font=("Arial", 11)).pack(side=tk.LEFT, padx=(0, 5))
        self.disc_ent = tk.Entry(or2, font=("Arial", 11),
                                  bg=C["input"], fg=_billing_entry_fg(C["lime"]),
                                  bd=0, width=10,
                                  insertbackground=C["accent"])
        self.disc_ent.pack(side=tk.LEFT, ipady=4)
        bind_discount_entry(self)
        self.disc_ent.config(state="disabled")
        self.disc_ent.bind("<KeyRelease>", lambda e: self.after_idle(self._refresh_bill))
        self.disc_ent.bind("<FocusOut>", lambda e: self.after_idle(self._refresh_bill))
        self.sale_margin_alert_box = tk.Frame(ob, bg=C["card"])
        self.sale_margin_alert_box.pack(fill=tk.X)
        self.sale_margin_alert_lbl = tk.Label(
            self.sale_margin_alert_box,
            text="",
            bg="#7f1d1d",
            fg="white",
            font=("Arial", 10, "bold"),
            anchor="w",
            justify="left",
            wraplength=scaled_value(420, 360, 280),
            padx=10,
            pady=5,
            relief="solid",
            bd=1,
        )

        or3 = tk.Frame(ob, bg=C["card"])
        or3.pack(fill=tk.X, pady=(6, 0))
        self.use_pts_var = tk.BooleanVar(value=False)
        tk.Checkbutton(or3, text="Use Loyalty Points",
                       variable=self.use_pts_var,
                       command=self._refresh_bill,
                       bg=C["card"], fg=_billing_card_fg(C["gold"]),
                       activeforeground=_billing_card_fg(C["gold"]),
                       selectcolor=C["input"],
                       font=("Arial", 11),
                       cursor="hand2").pack(side=tk.LEFT)
        self.pts_disc_lbl = tk.Label(or3, text="",
                                     bg=C["card"], fg=_billing_card_fg(C["gold"]),
                                     font=("Arial", 11))
        self.pts_disc_lbl.pack(side=tk.LEFT, padx=6)

        or4 = tk.Frame(ob, bg=C["card"])
        or4.pack(fill=tk.X, pady=(8, 0))
        tk.Label(or4, text="Pay:", bg=C["card"],
                 fg=C["muted"], font=("Arial", 11)).pack(side=tk.LEFT, padx=(0, 6))
        for pm in ["Cash", "Card", "UPI"]:
            tk.Radiobutton(or4, text=pm,
                           variable=self.payment_var, value=pm,
                           bg=C["card"], fg=_billing_card_fg(),
                           activeforeground=_billing_card_fg(),
                           selectcolor=C["input"],
                           font=("Arial", 11),
                           command=self._refresh_bill,
                           cursor="hand2").pack(side=tk.LEFT, padx=4)

        # Offers / Coupon
        of = create_card_section(
            lp,
            C,
            "Offer / Coupon",
            "Promotions and redeem support",
            C["gold"],
            ("Arial", 11, "bold"),
            ("Arial", 9),
            title_fg=C["gold"],
        )

        offer_form = tk.Frame(of, bg=C["card"])
        offer_form.pack(fill=tk.X)
        offer_form.grid_columnconfigure(0, minsize=64)
        offer_form.grid_columnconfigure(1, weight=1, minsize=130)
        offer_form.grid_columnconfigure(2, minsize=84)
        offer_form.grid_columnconfigure(3, minsize=84)

        tk.Label(offer_form, text="Offer:", bg=C["card"],
                 fg=C["muted"], font=("Arial", 11), anchor="w").grid(
                     row=0, column=0, sticky="w", padx=(0, 6)
                 )
        self.offer_var = tk.StringVar(value="No Offer")
        self.offer_cb  = ttk.Combobox(offer_form, textvariable=self.offer_var,
                                       state="readonly", font=("Arial", 11),
                                       width=34,
                                       style="Billing.TCombobox")
        self.offer_cb.grid(row=0, column=1, columnspan=3, sticky="ew")
        self.offer_cb.bind("<<ComboboxSelected>>", self._on_offer_select)
        self.offer_cb.bind("<MouseWheel>", lambda e: "break")
        self._refresh_offer_dropdown()

        tk.Label(offer_form, text="Coupon:", bg=C["card"],
                 fg=C["muted"], font=("Arial", 11), anchor="w").grid(
                     row=1, column=0, sticky="w", padx=(0, 6), pady=(8, 0)
                 )
        self.coupon_ent = tk.Entry(offer_form, font=("Arial", 12),
                                    bg=C["input"], fg=_billing_entry_fg(C["gold"]),
                                    bd=0,
                                    insertbackground=C["accent"])
        self.coupon_ent.grid(row=1, column=1, sticky="ew", ipady=4, padx=(0, 8), pady=(8, 0))
        ModernButton(offer_form,text="Apply",image=add_icon,compound="left",command=self._apply_coupon,
            color=C["teal"],hover_color=C["blue"],width=76,height=30,radius=8,
            font=("Arial",10,"bold")).grid(row=1, column=2, sticky="ew", pady=(8, 0))
        ModernButton(offer_form,text="Clear",image=clear_icon,compound="left",command=self._clear_offer,
            color=C["red"],hover_color="#c0392b",width=76,height=30,radius=8,
            font=("Arial",10,"bold")).grid(row=1, column=3, sticky="ew", padx=(6,0), pady=(8, 0))

        tk.Label(offer_form, text="Redeem:", bg=C["card"],
                 fg=C["muted"], font=("Arial", 11), anchor="w").grid(
                     row=2, column=0, sticky="w", padx=(0, 6), pady=(8, 0)
                 )
        self.redeem_ent = tk.Entry(offer_form, font=("Arial", 12),
                                    bg=C["input"], fg=_billing_entry_fg(C["lime"]),
                                    bd=0,
                                    insertbackground=C["accent"])
        self.redeem_ent.grid(row=2, column=1, sticky="ew", ipady=4, padx=(0, 8), pady=(8, 0))
        ModernButton(offer_form,text="Apply",image=add_icon,compound="left",command=self._apply_redeem,
            color=C["purple"],hover_color="#7d3c98",width=76,height=30,radius=8,
            font=("Arial",10,"bold")).grid(row=2, column=2, sticky="ew", pady=(8, 0))
        ModernButton(offer_form,text="Clear",image=clear_icon,compound="left",command=self._clear_redeem,
            color=C["red"],hover_color="#c0392b",width=76,height=30,radius=8,
            font=("Arial",10,"bold")).grid(row=2, column=3, sticky="ew", padx=(6,0), pady=(8, 0))

        self.offer_info_lbl = tk.Label(of, text="",
                                       bg=C["card"], fg=C["gold"],
                                       font=("Arial", 11, "bold"))
        self.offer_info_lbl.pack(anchor="w", pady=(4, 0))

        # Right live preview pane
        rp = tk.Frame(paned, bg=C["bg"])
        paned.add(rp, weight=scaled_value(5, 5, 4))

        header_outer = tk.Frame(rp, bg=C["card"])
        header_outer.pack(fill=tk.X, pady=(0, 4))
        tk.Frame(header_outer, bg=C["teal"], height=2).pack(fill=tk.X)
        ib=tk.Frame(header_outer,bg=C["card"],pady=8,padx=12); ib.pack(fill=tk.X)

        meta_col = tk.Frame(ib, bg=C["card"])
        meta_col.pack(side=tk.LEFT, fill=tk.X, expand=True)
        top_meta = tk.Frame(meta_col, bg=C["card"])
        top_meta.pack(fill=tk.X)
        self.inv_lbl=tk.Label(top_meta,text=f"  {self._current_invoice}  ",
            font=("Courier New",10,"bold"),bg=C["teal"],fg="white",relief="flat",padx=6,pady=3)
        self.inv_lbl.pack(side=tk.LEFT)
        tk.Label(top_meta, text="Live Bill Preview",
                 font=("Arial", scaled_value(12, 11, 10), "bold"),
                 bg=C["card"], fg=C["text"]).pack(side=tk.LEFT, padx=(10, 0))
        tk.Label(meta_col,text="F2 Save   F4 PDF   F5 Print   F6 WhatsApp   F8 Clear",
            font=section_meta_font,bg=C["card"],fg=C["muted"]).pack(anchor="w", pady=(4, 0))

        command_col = tk.Frame(ib, bg=C["card"])
        command_col.pack(side=tk.RIGHT)

        self.total_lbl = tk.Label(command_col, text="Total: Rs0.00",
                                  font=("Arial", scaled_value(14, 12, 11), "bold"),
                                  bg=C["card"], fg=C["lime"])
        self.total_lbl.pack(side=tk.RIGHT, padx=(10, 0))

        self.wa_status_btn=ModernButton(command_col,text="WA: ?",
            command=self._check_wa_status_billing,
            color=C["sidebar"],hover_color=C["blue"],width=scaled_value(88, 84, 76),height=scaled_value(28, 26, 24),radius=8,
            font=("Arial",scaled_value(9, 9, 8),"bold")); self.wa_status_btn.pack(side=tk.RIGHT,padx=6)
        self.fast_btn=ModernButton(command_col,text="Fast: OFF",
            command=self._toggle_fast_mode,
            color=C["sidebar"],hover_color=C["teal"],width=scaled_value(100, 92, 82),height=scaled_value(28, 26, 24),radius=8,
            font=("Arial",scaled_value(9, 9, 8),"bold")); self.fast_btn.pack(side=tk.RIGHT,padx=(0,4))

        preview_head = tk.Frame(rp, bg=C["bg"])
        preview_head.pack(fill=tk.X, pady=(2, 4))
        tk.Label(preview_head, text="Invoice Preview",
                 font=("Arial", scaled_value(10, 10, 9), "bold"),
                 bg=C["bg"], fg=C["text"]).pack(side=tk.LEFT)
        tk.Label(preview_head, text="Use the left composer to keep building the current bill.",
                 font=section_meta_font,
                 bg=C["bg"], fg=C["muted"]).pack(side=tk.RIGHT)

        # Bill preview text
        self.txt = tk.Text(rp, font=("Courier New", bill_font),
                           bg="#ffffff", fg="#1a1a1a",
                           padx=18, pady=18, bd=0)
        self.txt.pack(fill=tk.BOTH, expand=True)
        bind_bill_preview_text(self)

        # Bind preview resizing to the right panel only.
        # Prevents stale width when left panel is dragged
        rp.bind("<Configure>", lambda event: resize_preview_font(rp, self.txt, event))

        footer = tk.Frame(rp, bg=C["card"], padx=10, pady=8)
        footer.pack(fill=tk.X, pady=(6, 0))
        tk.Frame(footer, bg=C["teal"], height=2).pack(fill=tk.X, side=tk.TOP)
        footer_body = tk.Frame(footer, bg=C["card"], pady=8)
        footer_body.pack(fill=tk.X)
        tk.Label(footer_body, text="Finish & Share",
                 font=(label_font[0], label_font[1], "bold"),
                 bg=C["card"], fg=C["text"]).pack(side=tk.LEFT)
        tk.Label(footer_body, text="Save, print, export PDF, send WhatsApp, or clear the draft.",
                 font=section_meta_font,
                 bg=C["card"], fg=C["muted"]).pack(side=tk.LEFT, padx=(10, 0))

        bf=tk.Frame(rp,bg=C["bg"],pady=8); bf.pack(fill=tk.X)
        bf_secondary = tk.Frame(bf, bg=C["bg"])
        bf_secondary.pack(side=tk.LEFT, fill=tk.X, expand=True)
        bf_primary = tk.Frame(bf, bg=C["bg"])
        bf_primary.pack(side=tk.RIGHT)

        action_widths = {
            "print": scaled_value(130, 118, 96),
            "pdf": scaled_value(130, 118, 96),
            "save": scaled_value(132, 120, 98),
            "wa": scaled_value(118, 108, 88),
            "clear": scaled_value(118, 108, 88),
        }
        action_targets = {"secondary": bf_secondary, "primary": bf_primary}
        for spec in finish_action_specs(action_widths):
            target = action_targets[spec["group"]]
            t = spec["text"]
            btn_icon = {
                "PRINT": print_icon,
                "PDF": pdf_icon,
                "SAVE": save_icon,
                "WA": wa_icon,
                "CLEAR": clear_icon,
            }.get(t)
            btn_color = C[spec["color_key"]] if "color_key" in spec else spec["color"]
            ModernButton(target,text=t,image=btn_icon,compound="left",command=getattr(self, spec["command"]),color=btn_color,hover_color=spec["hover"],
                width=spec["width"],height=action_btn_h,radius=9,font=action_font,
                ).pack(side=tk.LEFT,padx=3)

        # Step 7: Set initial fast mode button state
        self._update_fast_mode_ui()

        def _sync_billing_split(_event=None):
            sync_billing_split(paned, lp_outer, W, get_responsive_metrics, scaled_value)

        paned.bind("<Configure>", _sync_billing_split)
        self.after_idle(_sync_billing_split)

    # ==================== HELPERS ====================
    def _get_data(self):
        return data_for_mode(self.mode, self.services_data, self.products_data)

    def _use_v5_variant_products(self):
        return should_use_variant_products(self.mode, use_v5_product_variants_db())

    def _get_v5_variant_matches(self, query: str = "", category: str = "All"):
        matches, variant_meta = list_billing_product_matches(query, category)
        self._ss_variant_meta = variant_meta
        return matches

    def _get_v5_variant_categories(self):
        return list_billing_product_categories()

    def _apply_search_selection(self, item):
        code, name, cat, price = normalize_catalog_item(item)
        self.search_var.set(name)
        self.price_ent.delete(0, tk.END)
        self.price_ent.insert(0, str(price))
        self._selected_product_category = cat or None
        variant_meta = getattr(self, "_ss_variant_meta", {})
        self._selected_product_variant = variant_selection_for_item(
            code,
            variant_meta,
            self._use_v5_variant_products() or code in variant_meta,
        )
        self._refresh_quantity_unit_hint()

    def _refresh_quantity_unit_hint(self):
        try:
            view = quantity_unit_hint_view(
                current_mode=getattr(self, "mode", "services"),
                selected_variant=getattr(self, "_selected_product_variant", None),
            )
            if hasattr(self, "qty_lbl"):
                self.qty_lbl.configure(text=view["qty_label"])
            if not hasattr(self, "unit_hint_f"):
                return
            if view["visible"]:
                if not self.unit_hint_f.winfo_ismapped():
                    self.unit_hint_f.pack(side=tk.RIGHT, padx=(8, 0))
                if view.get("show_helper") and hasattr(self, "unit_helper_lbl") and not self.unit_helper_lbl.winfo_ismapped():
                    self.unit_helper_lbl.pack(anchor="e")
                elif not view.get("show_helper") and hasattr(self, "unit_helper_lbl"):
                    self.unit_helper_lbl.pack_forget()
                self.unit_badge_lbl.configure(text=view["unit_badge"])
                self.unit_helper_lbl.configure(text=view["helper"])
            else:
                self.unit_hint_f.pack_forget()
                if hasattr(self, "unit_helper_lbl"):
                    self.unit_helper_lbl.pack_forget()
        except Exception as e:
            app_log(f"[_refresh_quantity_unit_hint] {e}")

    def set_mode(self, mode: str):
        if mode == "services" and not getattr(self, "_show_services", True):
            return
        if mode == "products" and not getattr(self, "_show_products", True):
            return
        self.mode = mode
        self._selected_product_variant = None
        if mode == "services":
            self._sbox_lbl.config(text="Add Services")
            self.btn_svc.set_color(C["teal"], C["blue"])
            self.btn_prd.set_color(C["sidebar"], C["blue"])
        else:
            self._sbox_lbl.config(text="Add Products")
            self.btn_prd.set_color(C["teal"], C["blue"])
            self.btn_svc.set_color(C["sidebar"], C["blue"])
        self._refresh_cats()
        self._refresh_quantity_unit_hint()
        self.search_var.set("")
        self.price_ent.delete(0, tk.END)
        # Phase 6: focus barcode scan field when in products mode
        if mode == "products" and hasattr(self, "scan_entry"):
            self.after(100, self._focus_scan_entry)
        else:
            self.after(100, lambda: (self.search_ent.focus_set(),))

    def _refresh_cats(self):
        product_categories = self._get_v5_variant_categories() if self.mode == "products" else None
        values = category_values_for_mode(self.mode, self._get_data(), product_categories)
        self.cat_cb["values"] = values
        if self.cat_v.get() not in self.cat_cb["values"]:
            self.cat_v.set("All")

    def _on_cat_selected(self):
        self._selected_product_variant = None
        self._refresh_quantity_unit_hint()
        self.search_var.set("")
        self._ss_hide()
        self.search_ent.focus_set()
        self._ss_show_all_for_cat()

    def _ss_show_all_for_cat(self):
        if self.mode == "products":
            matches = self._get_v5_variant_matches("", self.cat_v.get())
            if matches:
                self._ss_items = matches
                self._ss_show(matches)
            else:
                self._ss_hide()
            return
        from utils import build_item_codes
        matches = build_category_matches(build_item_codes(), self.mode, self.cat_v.get())
        if matches:
            self._ss_items = matches
            self._ss_show(matches)

    def _ss_on_focus(self, e=None):
        # Dropdown opens only after the user types.
        pass

    # Search ranking wrapper
    def _smart_search(self, query, items):
        """Re-rank a pre-filtered list of (code, name, cat, price) tuples.

        Priority tiers:
          100 pts for exact code/name match.
           60 pts for prefix match.
          +0-50 for fuzzy/substring ranking.

        Items scoring 0 are excluded from the result.
        Falls back to the original list if nothing scores > 0.
        """
        return smart_search(query, items)

    # Search suggestion typing handler
    def _ss_typing(self, e=None):
        q   = self.search_var.get().strip()
        cat = self.cat_v.get()
        if not q:
            self._ss_hide()   # Empty search keeps the dropdown hidden.
            return
        if self.mode == "products":
            matches = self._get_v5_variant_matches(q, cat)
            if not matches:
                self._ss_hide()
                return
            self._ss_items = matches
            self._ss_show(matches)
            return
        from utils import search_items, build_item_codes
        mode = "services" if self.mode == "services" else "products"
        candidates = build_category_matches(build_item_codes(), self.mode, cat)
        matches = self._smart_search(q, candidates)
        if cat == "All" and not matches:
            results = search_items(q, mode=mode, limit=14)
            matches = [(r["code"], r["name"], r["category"], r["price"])
                       for r in results]

        if not matches:
            self._ss_hide()
            return
        self._ss_items = matches
        self._ss_show(matches)

    def _ss_show(self, matches):
        self._ss_hide()
        try:
            display_items = []
            display_rows = []
            for item in matches:
                try:
                    code, name, _cat, price = normalize_catalog_item(item)
                except Exception as e:
                    app_log(f"[SmartSearch row skipped] {e}", "warning")
                    continue
                display_items.append(item)
                display_rows.append((code, name, price))
            if not display_items:
                return

            frame = tk.Frame(
                self._ss_host,
                bg=C["card"],
                highlightthickness=1,
                highlightbackground=C["teal"])
            sb = ttk.Scrollbar(frame, orient="vertical")
            lb = tk.Listbox(
                frame,
                font=("Arial", 10),
                bg=C["card"], fg=C["text"],
                selectbackground=C["teal"],
                selectforeground="white",
                activestyle="none",
                selectmode=tk.SINGLE,
                bd=0, highlightthickness=0,
                exportselection=False,
                yscrollcommand=sb.set,
                height=min(len(matches), 8))
            sb.config(command=lb.yview)
            sb.pack(side=tk.RIGHT, fill=tk.Y)
            lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            frame.pack(fill=tk.X)
            self._ss_host.pack(fill=tk.X, pady=(0, 4), after=self._ss_row)
            self._ss_win = frame
            self._ss_lb = lb
            self._ss_items = display_items
            self._ss_arrow_btn.config(text="^")

            for code, name, price in display_rows:
                lb.insert(tk.END, format_search_result_label(code, name, price))

            def _paint(selected_idx=None, hover_idx=None, listbox=lb):
                for i in range(listbox.size()):
                    bg = C["card"]
                    fg = C["text"]
                    if selected_idx is not None and i == selected_idx:
                        bg = C["teal"]
                        fg = "white"
                    elif hover_idx is not None and i == hover_idx:
                        bg = "#1a6b5a"
                        fg = "white"
                    listbox.itemconfig(i, bg=bg, fg=fg)

            def _on_motion(e, listbox=lb):
                idx = listbox.nearest(e.y)
                sel = listbox.curselection()
                _paint(sel[0] if sel else None, idx)

            def _on_leave(e, listbox=lb):
                sel = listbox.curselection()
                _paint(sel[0] if sel else None)

            def _on_click(e, listbox=lb):
                idx = listbox.nearest(e.y)
                if idx < 0:
                    return "break"
                listbox.selection_clear(0, tk.END)
                listbox.selection_set(idx)
                self._ss_select(idx)
                return "break"

            def _on_key_nav(e, listbox=lb):
                sel = listbox.curselection()
                cur = sel[0] if sel else -1
                if e.keysym == "Down":
                    nxt = min(cur + 1, listbox.size() - 1) if cur >= 0 else 0
                elif e.keysym == "Up":
                    if cur <= 0:
                        self.search_ent.focus_set()
                        return "break"
                    nxt = cur - 1
                else:
                    return None
                listbox.selection_clear(0, tk.END)
                listbox.selection_set(nxt)
                listbox.activate(nxt)
                listbox.see(nxt)
                _paint(nxt)
                return "break"

            def _on_lb_enter(e, listbox=lb):
                sel = listbox.curselection()
                idx = sel[0] if sel else listbox.index("active")
                self._ss_select(idx)
                return "break"

            lb.selection_clear(0, tk.END)
            lb.selection_set(0)
            lb.activate(0)
            _paint(0)
            lb.bind("<Motion>", _on_motion)
            lb.bind("<Leave>", _on_leave)
            lb.bind("<ButtonRelease-1>", _on_click)
            lb.bind("<Double-Button-1>", _on_click)
            lb.bind("<Up>", _on_key_nav)
            lb.bind("<Down>", _on_key_nav)
            lb.bind("<Return>", _on_lb_enter)
            lb.bind("<Escape>", lambda e: (self._ss_hide(), self.search_ent.focus_set(), "break")[-1])
            lb.bind("<FocusOut>", lambda e: self.after(120, self._ss_check_focus))
        except Exception as e:
            app_log(f"[SmartSearch show] {e}")

    def _ss_on_search_focusout(self, e=None):
        """Hide dropdown only if focus didn't move to the listbox."""
        if self._ss_toggle_pending:
            return
        self.after(120, self._ss_check_focus)

    def _ss_check_focus(self):
        """Hide dropdown only if focus is outside the search controls."""
        try:
            focused = self.focus_get()
            if focused in (self.search_ent, self._ss_lb, self._ss_arrow_btn):
                return
            while focused is not None:
                if focused == self._ss_win:
                    return
                focused = getattr(focused, "master", None)
            self._ss_hide()
        except Exception:
            self._ss_hide()

    def _ss_focus(self, e=None):
        """Arrow from search entry moves focus into inline listbox."""
        if not self._ss_lb or self._ss_lb.size() == 0:
            return
        self._ss_lb.focus_set()
        sel = self._ss_lb.curselection()
        idx = sel[0] if sel else 0
        self._ss_lb.selection_clear(0, tk.END)
        self._ss_lb.selection_set(idx)
        self._ss_lb.activate(idx)
        self._ss_lb.see(idx)
        for i in range(self._ss_lb.size()):
            self._ss_lb.itemconfig(i, bg=C["card"], fg=C["text"])
        self._ss_lb.itemconfig(idx, bg=C["teal"], fg="white")

    def _ss_enter(self, e=None):
        """ENTER in search entry selects current match and moves to qty."""
        query = self.search_var.get().strip()

        if getattr(self, "fast_mode", False):
            exact = self._get_exact_match(query)
            if exact:
                self._apply_search_selection(exact)
                self.add_item()
                return

        if self._ss_lb and self._ss_lb.size() > 0:
            sel = self._ss_lb.curselection()
            idx = sel[0] if sel else 0
            self._ss_select(idx)
        else:
            if self.search_var.get().strip():
                self.add_item()

    def _ss_click(self, e=None):
        if not self._ss_lb:
            return
        sel = self._ss_lb.curselection()
        if sel:
            self._ss_select(sel[0])

    def _ss_lb_enter(self, e=None):
        if not self._ss_lb:
            return
        sel = self._ss_lb.curselection()
        idx = sel[0] if sel else self._ss_lb.index("active")
        self._ss_select(idx)

    def _ss_double(self, e=None):
        if not self._ss_lb:
            return
        sel = self._ss_lb.curselection()
        if sel:
            self._ss_select(sel[0])

    def _get_exact_match(self, query):
        """Return item tuple if query exactly matches a name or code, else None."""
        return find_exact_match(query, getattr(self, "_ss_items", []))

    def _ss_select(self, idx, add_immediately: bool = False):
        """Fill search+price from selected item."""
        try:
            item = self._ss_items[idx]
            self._apply_search_selection(item)
            self._ss_hide()
            if add_immediately:
                self.after_idle(self.add_item)
            else:
                self.after_idle(self._focus_qty_entry)
        except Exception as e:
            app_log(f"[SmartSearch select] {e}")

    def _focus_qty_entry(self):
        try:
            self._ss_hide()
            self.qty_ent.focus_force()
            self.qty_ent.icursor(tk.END)
            self.qty_ent.select_range(0, tk.END)
        except Exception as e:
            app_log(f"[_focus_qty_entry] {e}")

    def _focus_discount_entry(self):
        try:
            if str(self.disc_ent.cget("state")) == "disabled":
                return
            self.disc_ent.focus_force()
            self.disc_ent.icursor(tk.END)
            self.disc_ent.select_range(0, tk.END)
        except Exception as e:
            app_log(f"[_focus_discount_entry] {e}")

    # ==================== PHASE 6: BARCODE SCANNER ====================

    def _on_barcode_enter(self, e=None):
        """Handle Enter in the barcode scan field.

        USB barcode scanners send characters then Enter.
        This method looks up the barcode in inventory and adds the
        product to the bill in one step for cashier-speed scanning.
        """
        barcode = self._scan_var.get().strip()
        if not barcode:
            return

        # Look up barcode in inventory
        found = self._lookup_barcode(barcode)
        if not found:
            self.scan_label.config(text="Not found", fg=C.get("red", "#e94560"))
            self._scan_var.set("")
            self.after(1500, lambda: self.scan_label.config(text="", fg=C.get("muted", "#94a3b8")))
            return

        scan_result = apply_scanned_product_to_bill(self.bill_items, found)
        if scan_result["status"] == "out_of_stock":
            self.scan_label.config(text="Out of stock", fg=C.get("red", "#e94560"))
            self.after(1500, lambda: self.scan_label.config(text="", fg=C.get("muted", "#94a3b8")))
            self._scan_var.set("")
            return

        name = scan_result["name"]
        self.scan_label.config(text=name, fg=C.get("teal", "#00b894"))
        self._refresh_bill()
        self._scan_var.set("")
        self.after(1500, lambda: self.scan_label.config(text="", fg=C.get("muted", "#94a3b8")))

    def _lookup_barcode(self, barcode: str) -> dict | None:
        """Look up a product barcode in inventory.

        Returns a dict with name, price, qty info or None.
        """
        try:
            from utils import load_json, F_INVENTORY
            from services_v5.inventory_service import InventoryService

            # Try v5 variants first
            from repositories.product_variants_repo import ProductVariantsRepository
            from salon_settings import get_settings
            use_v5 = bool(get_settings().get("use_v5_product_variants_db", False))

            if use_v5:
                repo = ProductVariantsRepository()
                found = find_barcode_in_variants(barcode, repo.get_all())
                if found:
                    return found

            # Fall back to legacy inventory lookup
            inv = InventoryService().build_legacy_inventory_map()
            if not inv:
                inv = load_json(F_INVENTORY, {})

            return find_barcode_in_inventory(barcode, inv)

        except Exception as ex:
            app_log(f"[_lookup_barcode] {ex}")

        return None

    def _on_scan_focus_out(self):
        """Keep scan field ready unless the user intentionally moved to another input."""
        try:
            if getattr(self, "mode", "") != "products" or not hasattr(self, "scan_entry"):
                return
            focus = self.focus_get()
            allowed_focus = {
                getattr(self, "scan_entry", None),
                getattr(self, "search_ent", None),
                getattr(self, "qty_ent", None),
                getattr(self, "price_ent", None),
                getattr(self, "name_ent", None),
                getattr(self, "phone_ent", None),
                getattr(self, "disc_ent", None),
            }
            if focus in allowed_focus:
                return
            if focus is None:
                self._focus_scan_entry()
        except Exception as e:
            app_log(f"[_on_scan_focus_out] {e}")

    def _focus_scan_entry(self):
        """Focus the barcode scan entry field (for cashier-mode)."""
        try:
            self._scan_var.set("")
            self.scan_entry.focus_set()
        except Exception as e:
            app_log(f"[_focus_scan_entry] {e}")

    def _ss_hide(self):
        try:
            if self._ss_win and self._ss_win.winfo_exists():
                self._ss_win.destroy()
        except Exception:
            pass
        self._ss_win = None
        self._ss_lb = None
        try:
            if self._ss_host.winfo_exists():
                self._ss_host.pack_forget()
        except Exception:
            pass
        try:
            self._ss_arrow_btn.config(text="v")
        except Exception:
            pass

    # ==================== AUTOCOMPLETE ====================

    def _on_customer_keyrelease(self, e, field: str):
        if getattr(e, "keysym", "") in {"Up", "Down", "Return", "Escape"}:
            return
        self._prepare_new_bill_if_completed(field)
        self._show_suggestions(field)

    def _on_customer_escape(self, e=None):
        self._hide_suggestions()
        return "break"

    def _show_suggestions(self, field: str):
        if field == "name":
            query = self.name_ent.get().strip().lower()
        else:
            query = self.phone_ent.get().strip().lower()

        if len(query) < 1:
            self._hide_suggestions()
            return

        customers = _billing_get_customers()
        matches = find_customer_suggestions(customers, field, query, limit=8)
        if not matches:
            self._hide_suggestions()
            return

        self._suggest_items = matches
        self._suggest_field = field
        self._suggest_customers = customers
        self._build_suggestion_popup(matches)

    def _build_suggestion_popup(self, matches):
        self._hide_suggestions()
        host = self._suggest_name_host if self._suggest_field == "name" else self._suggest_phone_host
        frame = tk.Frame(
            host,
            bg=C["card"],
            highlightthickness=1,
            highlightbackground=C["teal"])
        sb = ttk.Scrollbar(frame, orient="vertical")
        lb = tk.Listbox(
            frame,
            font=("Arial", 12),
            bg="#2d2d44", fg=C["text"],
            selectbackground=C["teal"],
            selectforeground="white",
            bd=0, highlightthickness=1,
            highlightcolor=C["teal"],
            activestyle="none",
            exportselection=False,
            yscrollcommand=sb.set,
            height=min(len(matches), 8))
        sb.config(command=lb.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        frame.pack(fill=tk.X)
        host.pack(fill=tk.X, pady=(2, 0))
        self._suggest_win = frame
        self._suggest_list = lb

        customers = getattr(self, "_suggest_customers", {}) or {}
        for nm, ph in matches:
            try:
                stats = get_customer_suggestion_stats(customers.get(ph, {}))
            except Exception:
                stats = {"points": 0, "visits": 0}
            lb.insert(tk.END, format_customer_suggestion_label(nm, ph, **stats))

        def on_select(e=None):
            sel = lb.curselection()
            if not sel:
                return "break"
            nm, ph = self._suggest_items[sel[0]]
            self._fill_customer(nm, ph)
            self._hide_suggestions()
            return "break"

        lb.selection_clear(0, tk.END)
        lb.selection_set(0)
        lb.activate(0)
        lb.bind("<ButtonRelease-1>", on_select)
        lb.bind("<Double-Button-1>", on_select)
        lb.bind("<Return>", on_select)
        lb.bind("<Escape>", lambda e: self._on_customer_escape(e))
        lb.bind("<Up>", lambda e: self._move_suggestion_selection(-1))
        lb.bind("<Down>", lambda e: self._move_suggestion_selection(1))
        lb.bind("<FocusOut>", lambda e: self.after(120, self._hide_suggestions_if_safe))
        lb.bind("<Motion>", lambda e: self._hover_suggestion(lb.nearest(e.y)))

    def _hover_suggestion(self, idx: int):
        if not self._suggest_list:
            return
        idx = clamp_suggestion_index(idx, self._suggest_list.size())
        self._suggest_list.selection_clear(0, tk.END)
        self._suggest_list.selection_set(idx)
        self._suggest_list.activate(idx)
        self._suggest_list.see(idx)

    def _move_suggestion_selection(self, delta: int):
        if not self._suggest_list or self._suggest_list.size() == 0:
            return "break"
        sel = self._suggest_list.curselection()
        idx = sel[0] if sel else 0
        idx = clamp_suggestion_index(idx + delta, self._suggest_list.size())
        self._hover_suggestion(idx)
        return "break"

    def _commit_customer_suggestion(self, e=None, field: str = "name"):
        if self._suggest_list and self._suggest_list.size() > 0:
            sel = self._suggest_list.curselection()
            idx = sel[0] if sel else 0
            nm, ph = self._suggest_items[idx]
            self._fill_customer(nm, ph)
            self._hide_suggestions()
            return "break"

        query = self.name_ent.get().strip() if field == "name" else self.phone_ent.get().strip()
        if len(self._suggest_items) == 1 and query:
            nm, ph = self._suggest_items[0]
            self._fill_customer(nm, ph)
            self._hide_suggestions()
            return "break"

        if field == "phone":
            self._on_phone_lookup()
            return "break"
        return None

    def _fill_customer(self, name: str, phone: str):
        self._prepare_new_bill_if_completed()
        self.name_ent.delete(0, tk.END)
        self.name_ent.insert(0, name)
        self.phone_ent.delete(0, tk.END)
        self.phone_ent.insert(0, phone)
        self._on_phone_lookup()
        self.name_ent.icursor(tk.END)
        self.phone_ent.icursor(tk.END)

    def _hide_suggestions(self):
        try:
            if self._suggest_win and self._suggest_win.winfo_exists():
                self._suggest_win.destroy()
        except Exception:
            pass
        self._suggest_win = None
        self._suggest_list = None
        for host_name in ("_suggest_name_host", "_suggest_phone_host"):
            host = getattr(self, host_name, None)
            try:
                if host and host.winfo_exists():
                    host.pack_forget()
            except Exception:
                pass

    def _hide_suggestions_if_safe(self):
        try:
            focused = self.focus_get()
            if focused in (self.name_ent, self.phone_ent, self._suggest_list):
                return
            while focused is not None:
                if focused == self._suggest_win:
                    return
                focused = getattr(focused, "master", None)
        except Exception:
            pass
        self._hide_suggestions()

    def _on_root_click(self, e=None):
        if e is None:
            self._ss_hide()
            self._hide_suggestions()
            return

    def _focus_suggestion(self, e=None, move: int = 1):
        if not self._suggest_list or self._suggest_list.size() == 0:
            try:
                is_phone = (self.phone_ent.focus_get() == self.phone_ent)
            except Exception:
                is_phone = False
            field = getattr(self, "_suggest_field", None) or ("phone" if is_phone else "name")
            self._show_suggestions(field)
        if self._suggest_list and self._suggest_list.size() > 0:
            self._suggest_list.focus_set()
            sel = self._suggest_list.curselection()
            idx = sel[0] if sel else 0
            if sel:
                idx = clamp_suggestion_index(idx + move, self._suggest_list.size())
            self._hover_suggestion(idx)
        return "break"

    def _on_phone_lookup(self, e=None):
        self.after(120, self._hide_suggestions_if_safe)
        try:
            ph = self.phone_ent.get().strip()
            c = _billing_get_customers().get(ph) if is_valid_lookup_phone(ph) else None
            state = build_phone_lookup_state(ph, c)
            if state["state"] == "existing":
                self.name_ent.delete(0, tk.END)
                self.name_ent.insert(0, state["customer_name"])
                self.bday_ent.delete(0, tk.END)
                self.bday_ent.insert(0, date_for_display(state["birthday"]))
            self.pts_lbl.config(text=state["points_text"])
            self.new_cust_lbl.config(
                text=state["customer_status_text"],
                fg=C[state["customer_status_color_key"]] if state["customer_status_color_key"] else C["text"],
            )
            self.package_info_lbl.config(text=state["package_text"])
            if state["state"] == "existing":
                self._check_membership_discount(ph)
                self._check_birthday_offer(ph, c)
        except Exception as e:
            app_log(f"[_on_phone_lookup] {e}")

    def _check_membership_discount(self, phone: str):
        try:
            from membership import get_customer_membership
            info = format_membership_info(get_customer_membership(phone))
            if info["active"]:
                self._membership_disc_pct = info["discount_pct"]
                self.package_info_lbl.config(text=info["text"], fg=C["gold"], font=info["font"])
                self._refresh_bill()
            else:
                self._membership_disc_pct = 0.0
                self.package_info_lbl.config(text="")
        except Exception:
            self._membership_disc_pct = 0.0
            self.package_info_lbl.config(text="")

    def _on_customer_panel_resize(self, event=None):
        if not hasattr(self, "package_info_lbl"):
            return
        width = max(220, int((event.width if event else 320) - 28))
        self.package_info_lbl.config(wraplength=width, justify="left", anchor="w")

    def _check_birthday_offer(self, phone: str, customer: dict):
        try:
            bd = customer.get("birthday", "")
            if is_birthday_month(bd):
                self.offer_info_lbl.config(text=BIRTHDAY_COUPON_MESSAGE)
        except Exception:
            pass

    def _prepare_new_bill_if_completed(self, trigger_field: str | None = None):
        if not getattr(self, "_bill_completed", False):
            return False
        if not getattr(self, "bill_items", None):
            self._bill_completed = False
            return False

        keep_name = ""
        keep_phone = ""
        if trigger_field == "name":
            keep_name = self.name_ent.get()
        elif trigger_field == "phone":
            keep_phone = self.phone_ent.get()

        self.clear_all()

        if keep_name:
            self.name_ent.insert(0, keep_name)
            self.name_ent.icursor(tk.END)
        if keep_phone:
            self.phone_ent.insert(0, keep_phone)
            self.phone_ent.icursor(tk.END)
        return True

    def _toggle_discount(self):
        state = discount_toggle_state(self.disc_enabled.get(), self.disc_ent.get())
        self.disc_ent.config(state="normal")
        self.disc_ent.delete(0, tk.END)
        self.disc_ent.insert(0, state["value"])
        self.disc_ent.config(state=state["entry_state"])
        if state["focus_discount"]:
            self.after_idle(self._focus_discount_entry)
        self._refresh_bill()

    def _get_inventory_lookup_map(self):
        now = time.time()
        if should_refresh_inventory_cache(self._inventory_lookup_cache, now, self._inventory_lookup_cache_time):
            self._inventory_lookup_cache = InventoryService().build_legacy_inventory_map()
            self._inventory_lookup_cache_time = now
        return self._inventory_lookup_cache

    # ==================== BILL LOGIC ====================
    def _edit_item_qty(self, e=None):
        """
        Issue B fix: all close paths call grab_release() before destroy().
        """
        if not self.bill_items:
            return
        win = tk.Toplevel(self)
        hide_while_building(win)
        win.title("Edit Bill Items")
        win.configure(bg=C["bg"])
        popup_window(win, 400, 340)
        win.grab_set()

        def _safe_close():
            try: win.grab_release()
            except Exception: pass
            try: win.destroy()
            except Exception: pass

        win.protocol("WM_DELETE_WINDOW", _safe_close)

        tk.Label(win, text="Select item to edit or remove:",
                 bg=C["bg"], fg=C["muted"],
                 font=("Arial", 11, "bold")).pack(anchor="w",
                                                   padx=14, pady=(14, 6))
        lb = tk.Listbox(win, font=("Arial", 11),
                        bg=C["input"], fg=C["text"],
                        selectbackground=C["teal"],
                        bd=0, height=8)
        lb.pack(fill=tk.BOTH, expand=True, padx=14)
        for it in self.bill_items:
            lb.insert(tk.END,
                      f"  {it['name'][:28]}  "
                      f"x{format_cart_quantity_label(it)}  "
                      f"@Rs{it['price']:.0f}")
        if lb.size() > 0:
            lb.selection_set(0)
            lb.activate(0)
            lb.focus_set()

        def apply_qty():
            sel = lb.curselection()
            if not sel:
                _safe_close(); return
            idx  = sel[0]
            item = self.bill_items[idx]
            import tkinter.simpledialog as sd
            new_qty_raw = sd.askstring(
                "Quantity",
                "New qty for: " + item["name"],
                initialvalue=format_cart_quantity_label(item),
                parent=win)
            new_qty = parse_cart_quantity(
                new_qty_raw,
                unit_type=item.get("unit_type") or item.get("unit") or "pcs",
            ) if new_qty_raw is not None else None
            if update_item_quantity(self.bill_items, idx, new_qty):
                self._refresh_bill()
            _safe_close()

        def remove_item():
            sel = lb.curselection()
            if not sel: return
            remove_item_at(self.bill_items, sel[0])
            self._refresh_bill()
            _safe_close()

        def edit_price():
            sel = lb.curselection()
            if not sel: return
            idx  = sel[0]
            item = self.bill_items[idx]
            import tkinter.simpledialog as sd
            new_p = sd.askfloat(
                "Price", "New price for: " + item["name"],
                initialvalue=item["price"],
                minvalue=0, parent=win)
            if update_item_price(self.bill_items, idx, new_p):
                self._refresh_bill()
            _safe_close()

        bb=tk.Frame(win,bg=C["bg"]); bb.pack(fill=tk.X,padx=14,pady=8)
        for txt,clr,hclr,cmd in [
            ("Update Qty",C["teal"],C["blue"],apply_qty),
            ("Edit Price",C["blue"],"#154360",edit_price),
            ("Remove",C["red"],"#c0392b",remove_item),
        ]:
            ModernButton(bb,text=txt,command=cmd,color=clr,hover_color=hclr,
                width=118,height=34,radius=8,font=("Arial",10,"bold"),
                ).pack(side=tk.LEFT,padx=(0,6))
        lb.bind("<Return>", lambda e: apply_qty())
        lb.bind("<Double-Button-1>", lambda e: apply_qty())
        lb.bind("<Escape>", lambda e: (_safe_close(), "break")[-1])
        reveal_when_ready(win)

    def add_item(self):
        sel   = self.search_var.get().strip()
        price = self.price_ent.get().strip()

        if not sel:
            messagebox.showwarning("Warning",
                                   "Search and select a service/product.")
            return
        if not price:
            messagebox.showwarning("Warning",
                                   "Select an item from the dropdown first.")
            return

        p = safe_float(price, None)
        if p is None or p < 0:
            messagebox.showerror("Error", "Invalid price.")
            return
        selected_variant = getattr(self, "_selected_product_variant", None)
        selected_category = getattr(self, "_selected_product_category", None)
        qty_unit = unit_type_for_variant(selected_variant) if self.mode == "products" else "pcs"
        qty = parse_cart_quantity(self.qty_ent.get(), unit_type=qty_unit)
        warning = None
        warning_message = ""

        if self.mode == "products" and selected_variant:
            stock_result = validate_variant_stock(
                bill_items=self.bill_items,
                selected_variant=selected_variant,
                inventory_lookup=self._get_inventory_lookup_map(),
                item_name=sel,
                requested_qty=qty,
            )
            if not stock_result["ok"]:
                messagebox.showwarning("No stock", stock_result["message"])
                return
            cost_price = selected_variant.get("cost_price", selected_variant.get("cost", 0.0))
            warning = build_below_cost_warning_state(
                bill_items=self.bill_items,
                item_name=sel,
                sale_price=p,
                qty=qty,
                cost_price=cost_price,
                discount_enabled=self.disc_enabled.get(),
                discount_value=self.disc_ent.get() or 0,
            )
            warning_message = warning.message.replace("\n\nContinue anyway?", "").strip()

        add_or_merge_cart_item(
            self.bill_items,
            mode=self.mode,
            name=sel,
            price=float(p),
            qty=qty,
            selected_variant=selected_variant,
            selected_category=selected_category,
        )
        self._refresh_bill()
        if self.mode == "products" and selected_variant and warning and warning.should_warn:
            self._show_sale_margin_alert(message=warning_message)
        self._reset_form()

    def _reset_form(self):
        try:
            self._ss_hide()
            self._selected_product_variant = None
            self._selected_product_category = None
            self._refresh_quantity_unit_hint()
            self.search_var.set("")
            self.price_ent.delete(0, tk.END)
            self.qty_ent.delete(0, tk.END)
            self.qty_ent.insert(0, "1")
            if self.mode == "products" and hasattr(self, "scan_entry"):
                self.after_idle(self._focus_scan_entry)
            else:
                self.after_idle(lambda: (self.search_ent.focus_set(),
                                         self.search_ent.select_range(0, tk.END)))
        except Exception as e:
            app_log(f"[_reset_form] {e}")

    def undo_last(self):
        if not self.bill_items: return
        try:
            if undo_last_item(self.bill_items):
                self._refresh_bill()
        except Exception as e:
            app_log(f"[undo_last] {e}")

    # ==================== OFFER HELPERS ====================
    def _refresh_offer_dropdown(self):
        offers = get_active_offers()
        self.offer_cb["values"] = build_offer_options(offers, safe_text)
        self._offers_list = offers

    def _on_offer_select(self, e=None):
        try:
            sel = self.offer_var.get()
            state = select_offer_state(sel, self._offers_list, self.offer_cb["values"], safe_text)
            self._applied_offer = state["applied_offer"]
            self.offer_info_lbl.config(text=state["info_text"])
            if state["clear_coupon"]:
                self.coupon_ent.delete(0, tk.END)
            self._refresh_bill()
        except Exception as e:
            app_log(f"[_on_offer_select] {e}")

    def _apply_coupon(self):
        code = normalize_coupon_code(self.coupon_ent.get())
        if not code:
            messagebox.showwarning("Coupon", "Enter a coupon code.")
            return
        try:
            offer = find_coupon(code)
            state = coupon_apply_state(code, offer, safe_text)
            if state["valid"]:
                self._applied_offer = state["applied_offer"]
                self.offer_var.set("No Offer")
                self.offer_info_lbl.config(text=state["info_text"])
                self._refresh_bill()
            else:
                messagebox.showerror("Invalid Coupon", state["error_text"])
                self._applied_offer = None
                self._refresh_bill()
        except Exception as e:
            messagebox.showerror("Coupon Error", f"Could not apply coupon: {e}")

    def _clear_offer(self):
        state = clear_offer_state()
        self._applied_offer       = state["applied_offer"]
        self._applied_redeem_code = state["applied_redeem_code"]
        self.redeem_ent.delete(0, tk.END)
        self.offer_var.set(state["offer_var"])
        self.coupon_ent.delete(0, tk.END)
        self.offer_info_lbl.config(text=state["info_text"])
        self._refresh_bill()

    def _apply_redeem(self):
        code = normalize_coupon_code(self.redeem_ent.get())
        if not code:
            messagebox.showwarning("Redeem", "Enter a redeem code.")
            return
        try:
            valid, info = validate_code(code)
            state = redeem_apply_state(code, valid, info)
            if state["valid"]:
                self._applied_redeem_code = state["applied_redeem_code"]
                self.offer_info_lbl.config(text=state["info_text"])
                self._refresh_bill()
            else:
                messagebox.showerror("Invalid Code", state["error_text"])
                self._applied_redeem_code = None
                self._refresh_bill()
        except Exception as e:
            messagebox.showerror("Redeem Error", f"Could not apply code: {e}")

    def _clear_redeem(self):
        self._applied_redeem_code = None
        self.redeem_ent.delete(0, tk.END)
        if should_clear_offer_info_after_redeem_clear(self._applied_offer):
            self.offer_info_lbl.config(text="")
        self._refresh_bill()

    def _calc_totals_detail(self):
        customer_points = None
        if self.use_pts_var.get():
            ph = self.phone_ent.get().strip()
            c = _billing_get_customers().get(ph)
            if c:
                customer_points = int(c.get("points", 0))

        gst_rate = 18.0
        gst_type = "inclusive"
        product_wise_gst_enabled = False
        gst_rate_source = "global"
        missing_item_gst_policy = "global"
        try:
            _sc = get_settings()
            gst_rate = _sc.get("gst_rate", 18.0)
            gst_type = _sc.get("gst_type", "inclusive")
            product_wise_gst_enabled = bool(_sc.get("product_wise_gst_enabled", False))
            gst_rate_source = _sc.get("gst_rate_source", "global")
            missing_item_gst_policy = _sc.get("missing_item_gst_policy", "global")
        except Exception:
            pass

        totals = calculate_billing_totals(
            items=self.bill_items,
            discount_enabled=self.disc_enabled.get(),
            discount_value=safe_float(self.disc_ent.get() or 0),
            membership_disc_pct=getattr(self, "_membership_disc_pct", 0),
            use_points=self.use_pts_var.get(),
            customer_points=customer_points,
            applied_offer=self._applied_offer,
            applied_redeem_code=self._applied_redeem_code,
            apply_offer_fn=apply_offer,
            calc_redeem_discount_fn=(
                lambda code, subtotal: calc_redeem_discount(
                    code,
                    subtotal,
                    customer_phone=self.phone_ent.get().strip(),
                )
            ),
            gst_enabled=self.gst_enabled.get(),
            gst_rate=gst_rate,
            gst_type=gst_type,
            product_wise_gst_enabled=product_wise_gst_enabled,
            gst_rate_source=gst_rate_source,
            missing_item_gst_policy=missing_item_gst_policy,
        )

        if self.use_pts_var.get() and totals.points_customer_missing:
            self.use_pts_var.set(False)
        elif self.use_pts_var.get():
            self.pts_disc_lbl.config(text=f"Points used: Rs{totals.points_discount:.0f}")
        else:
            self.pts_disc_lbl.config(text="")

        return totals

    def _calc_totals(self):
        return self._calc_totals_detail().as_legacy_tuple()

    def _sale_margin_warning_state_from_totals(self, totals):
        discount_total = (
            totals.discount
            + totals.membership_discount
            + totals.points_discount
            + totals.offer_discount
            + totals.redeem_discount
        )
        return build_sale_margin_warning_state(
            bill_items=self.bill_items,
            gross_before_discount=totals.total,
            discount_total=discount_total,
        )

    def _below_cost_alert_enabled(self) -> bool:
        try:
            return is_below_cost_alert_enabled(get_settings())
        except Exception:
            return True

    def _cancel_sale_margin_alert_jobs(self):
        try:
            if self._sale_margin_alert_job is not None:
                self.after_cancel(self._sale_margin_alert_job)
        except Exception:
            pass
        try:
            if self._sale_margin_alert_blink_job is not None:
                self.after_cancel(self._sale_margin_alert_blink_job)
        except Exception:
            pass
        self._sale_margin_alert_job = None
        self._sale_margin_alert_blink_job = None

    def _hide_sale_margin_alert(self):
        self._cancel_sale_margin_alert_jobs()
        try:
            self.sale_margin_alert_lbl.config(text="", bg="#7f1d1d")
            if self.sale_margin_alert_lbl.winfo_ismapped():
                self.sale_margin_alert_lbl.pack_forget()
            self._sale_margin_alert_text = ""
        except Exception:
            pass

    def _blink_sale_margin_alert(self):
        try:
            if not self.sale_margin_alert_lbl.winfo_ismapped():
                return
            self._sale_margin_alert_blink_state = not self._sale_margin_alert_blink_state
            bg = "#b91c1c" if self._sale_margin_alert_blink_state else "#7f1d1d"
            self.sale_margin_alert_lbl.config(bg=bg)
            self._sale_margin_alert_blink_job = self.after(450, self._blink_sale_margin_alert)
        except Exception:
            pass

    def _show_sale_margin_alert(self, state=None, message: str | None = None):
        if not self._below_cost_alert_enabled():
            self._hide_sale_margin_alert()
            return
        if message is None and state is not None:
            message = build_sale_margin_alert_text(state)
        if not message:
            self._hide_sale_margin_alert()
            return
        if message == self._sale_margin_alert_text and self.sale_margin_alert_lbl.winfo_ismapped():
            return
        self._cancel_sale_margin_alert_jobs()
        try:
            self.sale_margin_alert_lbl.config(text=message, bg="#7f1d1d")
            if not self.sale_margin_alert_lbl.winfo_ismapped():
                self.sale_margin_alert_lbl.pack(fill=tk.X, pady=(6, 0))
            self._sale_margin_alert_text = message
            self._sale_margin_alert_blink_state = False
            self._blink_sale_margin_alert()
        except Exception as e:
            app_log(f"[_show_sale_margin_alert] {e}")

    def _sync_sale_margin_alert(self, totals=None):
        try:
            if not self._below_cost_alert_enabled():
                self._hide_sale_margin_alert()
                return
            if not has_bill_items(self.bill_items):
                self._hide_sale_margin_alert()
                return
            current_totals = totals if totals is not None else self._calc_totals_detail()
            state = self._sale_margin_warning_state_from_totals(current_totals)
            if state.should_warn:
                self._show_sale_margin_alert(state)
            else:
                self._hide_sale_margin_alert()
        except Exception as e:
            app_log(f"[_sync_sale_margin_alert] {e}")

    def _confirm_no_below_cost_sale(self) -> bool:
        try:
            if not self._below_cost_alert_enabled():
                self._hide_sale_margin_alert()
                return True
            self._sync_sale_margin_alert()
        except Exception as e:
            app_log(f"[_confirm_no_below_cost_sale] {e}")
        return True

    def _refresh_bill(self):
        """Generate bill preview using print_engine."""
        try:
            self._refresh_bill_inner()
        except Exception as e:
            app_log(f"[_refresh_bill] {e}")

    def _refresh_bill_inner(self):
        """Render the current live bill preview."""
        from print_engine import generate_thermal_text, BillData, get_print_settings

        cfg = get_settings()
        totals = self._calc_totals_detail()
        ps = apply_printer_width(get_print_settings(), cfg)
        bill = BillData(**build_bill_data_kwargs(
            invoice=self._current_invoice,
            settings=cfg,
            invoice_branding=get_invoice_branding(),
            customer_name=self.name_ent.get(),
            customer_phone=self.phone_ent.get(),
            payment_method=self.payment_var.get(),
            bill_items=self.bill_items,
            totals=totals.as_legacy_tuple(),
            membership_disc_pct=getattr(self, "_membership_disc_pct", 0),
            applied_offer=self._applied_offer,
            applied_redeem_code=self._applied_redeem_code,
            now=datetime.now(),
            totals_detail=totals,
        ))

        text = generate_thermal_text(bill, ps)
        self.txt.delete("1.0", tk.END)
        self.txt.insert(tk.END, text)
        self.total_lbl.config(text=f"Total: Rs{totals.grand_total:.2f}")
        self._sync_sale_margin_alert(totals)

    # ==================== SAVE / PRINT ====================
    def _build_bill_data(self):
        """Build BillData for PDF generation."""
        try:
            return self._build_bill_data_inner()
        except Exception as e:
            app_log(f"[_build_bill_data] {e}")
            return None

    def _build_bill_data_inner(self):
        """Build BillData for PDF/print/WhatsApp output."""
        from print_engine import BillData

        cfg = get_settings()
        totals = self._calc_totals_detail()
        return BillData(**build_bill_data_kwargs(
            invoice=self._current_invoice,
            settings=cfg,
            invoice_branding=get_invoice_branding(),
            customer_name=self.name_ent.get(),
            customer_phone=self.phone_ent.get(),
            payment_method=self.payment_var.get(),
            bill_items=self.bill_items,
            totals=totals.as_legacy_tuple(),
            membership_disc_pct=getattr(self, "_membership_disc_pct", 0),
            applied_offer=self._applied_offer,
            applied_redeem_code=self._applied_redeem_code,
            now=datetime.now(),
            totals_detail=totals,
        ))

    def _pdf_path(self) -> str:
        return build_pdf_path(
            bills_dir=BILLS_DIR,
            invoice=self._current_invoice,
            customer_name=self.name_ent.get(),
            sanitize_filename=sanitize_filename,
        )

    def _save_report(self, final: float, disc: float, pts_disc: float,
                     offer_disc: float = 0.0, redeem_disc: float = 0.0,
                     mem_disc: float = 0.0):
        from adapters.billing_adapter import use_v5_billing_db
        if use_v5_billing_db():
            return self._save_report_v5(final, disc, pts_disc, offer_disc, redeem_disc, mem_disc)
        # Duplicate bill save guard
        def _deduct_inventory_for_sale(items):
            from inventory import deduct_inventory_for_sale
            deduct_inventory_for_sale(items)

        def _auto_sync():
            from cloud_sync import auto_sync
            auto_sync()

        deps = SaveLegacyReportDependencies(
            deduct_inventory_for_sale=_deduct_inventory_for_sale,
            auto_save_customer=_auto_save_customer,
            record_visit=_billing_record_visit,
            redeem_points=_billing_redeem_points,
            apply_redeem_code=apply_redeem_code,
            auto_sync=_auto_sync,
            on_bill_saved=lambda: self.app.on_bill_saved(),
            now=now_str,
        )
        return save_report_legacy_core(
            self,
            final=final,
            disc=disc,
            pts_disc=pts_disc,
            offer_disc=offer_disc,
            redeem_disc=redeem_disc,
            mem_disc=mem_disc,
            report_path=F_REPORT,
            deps=deps,
        )

    def _save_report_v5(self, final: float, disc: float, pts_disc: float,
                        offer_disc: float = 0.0, redeem_disc: float = 0.0,
                        mem_disc: float = 0.0):
        from billing_logic import save_report_v5
        return save_report_v5(self, final, disc, pts_disc, offer_disc, redeem_disc, mem_disc)

    def _auto_clear_after_print_or_save(self):
        try:
            if should_auto_clear_after_print(get_settings()):
                self.after(500, self.clear_all)
        except Exception as e:
            app_log(f"[_auto_clear_after_print_or_save] {e}")

    def manual_save(self):
        if not has_bill_items(self.bill_items):
            title, msg = bill_action_empty_warning()
            messagebox.showwarning(title, msg)
            return
        if not self._confirm_no_below_cost_sale():
            return
        path = self._pdf_path()
        try:
            from print_engine import generate_bill_pdf
            bill = self._build_bill_data()
            generate_bill_pdf(bill, path, self._print_font)
            report_args = save_report_args_from_totals(self._calc_totals())
            self._save_report(**report_args)
            title, msg = bill_saved_message(path)
            messagebox.showinfo(title, msg)
            self._auto_clear_after_print_or_save()
        except Exception as e:
            title, msg = save_error_message(e)
            messagebox.showerror(title, msg)

    def save_pdf(self):
        """Bug 6 fix: cross-platform file open."""
        if not has_bill_items(self.bill_items):
            title, msg = bill_action_empty_warning()
            messagebox.showwarning(title, msg)
            return
        if not self._confirm_no_below_cost_sale():
            return
        path = self._pdf_path()
        try:
            from print_engine import generate_bill_pdf
            bill = self._build_bill_data()
            generate_bill_pdf(bill, path, self._print_font)
            report_args = save_report_args_from_totals(self._calc_totals())
            self._save_report(**report_args)
            title, msg = pdf_saved_message(path)
            messagebox.showinfo(title, msg)
            open_file_cross_platform(path)    # Bug 6 fix
            self._auto_clear_after_print_or_save()
        except Exception as e:
            title, msg = pdf_error_message(e)
            messagebox.showerror(title, msg)

    def print_bill(self):
        if not has_bill_items(self.bill_items):
            title, msg = bill_action_empty_warning()
            messagebox.showwarning(title, msg)
            return
        if not self._confirm_no_below_cost_sale():
            return
        try:
            import win32print
            pn   = win32print.GetDefaultPrinter()
            hprn = win32print.OpenPrinter(pn)
            try:
                content = self.txt.get("1.0", tk.END)
                win32print.StartDocPrinter(hprn, 1, ("Salon Bill", None, "RAW"))
                win32print.StartPagePrinter(hprn)
                win32print.WritePrinter(hprn, content.encode("utf-8"))
                win32print.EndPagePrinter(hprn)
                win32print.EndDocPrinter(hprn)
                report_args = save_report_args_from_totals(self._calc_totals())
                self._save_report(**report_args)
                path = self._pdf_path()
                from print_engine import generate_bill_pdf
                generate_bill_pdf(self._build_bill_data(), path,
                                  self._print_font)
                title, msg = printed_message(pn)
                messagebox.showinfo(title, msg)
                self._auto_clear_after_print_or_save()
            finally:
                win32print.ClosePrinter(hprn)
        except ImportError as e:
            content = self.txt.get("1.0", tk.END)
            path = open_print_text_fallback(content, f"{self._current_invoice}_print.txt")
            messagebox.showwarning(
                "Print Fallback",
                "Direct printer module is missing, so Windows print fallback was used.\n\n"
                f"Detail: {e}\n\n"
                f"Print file: {path}")
        except Exception as e:
            title, msg = print_error_message(e)
            messagebox.showerror(title, msg)

    def send_whatsapp(self):
        if not has_bill_items(self.bill_items):
            title, msg = bill_action_empty_warning()
            messagebox.showwarning(title, msg)
            return
        if not self._confirm_no_below_cost_sale():
            return
        ph = self.phone_ent.get().strip()
        if not validate_phone(ph):
            title, msg = invalid_phone_message()
            messagebox.showerror(title, msg)
            return

        report_args = save_report_args_from_totals(self._calc_totals())

        cfg   = get_settings()
        sph   = cfg.get("phone", "")
        raw   = self.txt.get("1.0", tk.END)
        from whatsapp_helper import build_billing_whatsapp_text
        msg = build_billing_whatsapp_text(raw, footer_phone=sph)

        import threading

        def _set_wa_status(status):
            view = whatsapp_status_view(status)
            self.wa_status_btn.set_text(view["text"])
            self.wa_status_btn.set_color(
                C[view["color_key"]],
                C.get(view["hover"], view["hover"]),
            )

        def _send():
            try:
                from whatsapp_helper import send_text, get_session_snapshot
                self.after(0, lambda: _set_wa_status("sending"))
                ok = send_text(
                    ph,
                    msg,
                    wait_for_login=25,
                    manual_send_timeout=7,
                    auto_send_fallback=True,
                )
                snapshot = get_session_snapshot()
                if ok:
                    self._save_report(**report_args)
                    dialog_title, dialog_msg = whatsapp_send_success_message()
                    self.after(0, lambda: (
                        _set_wa_status("ready"),
                        messagebox.showinfo(dialog_title, dialog_msg),
                    ))
                elif snapshot.get("state") == "WAITING_MANUAL_SEND":
                    self.after(0, lambda: _set_wa_status("manual"))
                else:
                    err = extract_whatsapp_error(snapshot)
                    dialog_title, dialog_msg = whatsapp_send_error_message(err)
                    self.after(0, lambda: (
                        _set_wa_status("login"),
                        messagebox.showerror(dialog_title, dialog_msg),
                    ))
            except Exception as exc:
                dialog_title, dialog_msg = whatsapp_exception_message(exc)
                self.after(0, lambda: (
                    _set_wa_status("error"),
                    messagebox.showerror(dialog_title, dialog_msg),
                ))

        threading.Thread(target=_send, daemon=True).start()

    def _check_wa_status_billing(self):
        import threading

        def _set_wa_status(status):
            view = whatsapp_status_view(status)
            self.wa_status_btn.set_text(view["text"])
            self.wa_status_btn.set_color(
                C[view["color_key"]],
                C.get(view["hover"], view["hover"]),
            )

        _set_wa_status("opening")

        def _chk():
            try:
                from whatsapp_helper import ensure_session_ready
                snap = ensure_session_ready(wait_for_login=12)
                if snap.get("state") not in {
                    "READY",
                    "DEFAULT_BROWSER_OPEN",
                    "WAITING_FOR_LOGIN",
                    "WAITING_MANUAL_SEND",
                    "BROWSER_CLOSED",
                    "STARTING_BROWSER",
                    "OPENING_WHATSAPP",
                    "NOT_STARTED",
                }:
                    snap = {
                        "state": "WAITING_MANUAL_SEND",
                        "message": "App-controlled WhatsApp is not ready; bill send will open the default browser",
                    }
                result = whatsapp_session_result(snap)

                def _apply_result():
                    _set_wa_status(result["status"])
                    if result["message_kind"] == "error":
                        messagebox.showerror(*result["message"])

                self.after(0, _apply_result)
            except Exception as exc:
                self.after(0, lambda: (
                    _set_wa_status("error"),
                    messagebox.showerror(
                        "WhatsApp",
                        f"Could not initialize WhatsApp.\n\n{exc}"),
                ))

        threading.Thread(target=_chk, daemon=True).start()

    def clear_all(self):
        """Bug 1 fix: removed duplicate _membership_disc_pct reset."""
        self.bill_items = []
        self._bill_completed      = False
        self._current_invoice     = next_invoice()
        self._applied_offer       = None
        self._applied_redeem_code = None
        self._membership_disc_pct = 0.0   # single reset (Bug 1 fix)
        self._saved_invoices      = set()  # Fix: reset duplicate guard on new bill

        # Bug 5 fix: clean invoice label format
        self.inv_lbl.config(text=f"  {self._current_invoice}")

        self.name_ent.delete(0, tk.END)
        self.phone_ent.delete(0, tk.END)
        self.disc_enabled.set(False)
        self.disc_ent.config(state="normal")
        self.disc_ent.delete(0, tk.END)
        self.disc_ent.insert(0, "0")
        self.disc_ent.config(state="disabled")

        try:
            _s = get_settings()
            self.gst_enabled.set(_s.get("gst_always_on", False))
            self.payment_var.set(_s.get("default_payment", "Cash"))
        except Exception:
            self.gst_enabled.set(False)
            self.payment_var.set("Cash")

        self.use_pts_var.set(False)
        self.pts_lbl.config(text="Points: -")
        self.pts_disc_lbl.config(text="")
        self.bday_ent.delete(0, tk.END)
        self.new_cust_lbl.config(text="")
        self.package_info_lbl.config(text="")
        self._hide_suggestions()
        self.redeem_ent.delete(0, tk.END)
        self.offer_var.set("No Offer")
        self.coupon_ent.delete(0, tk.END)
        self.offer_info_lbl.config(text="")
        self._hide_sale_margin_alert()
        self._refresh_offer_dropdown()
        self._selected_product_variant = None
        self._refresh_quantity_unit_hint()
        self.search_var.set("")
        self.price_ent.delete(0, tk.END)
        self.qty_ent.delete(0, tk.END)
        self.qty_ent.insert(0, "1")
        self._refresh_bill()

    def refresh(self):
        """Called when switching to billing tab."""
        for action in refresh_action_sequence():
            try:
                if action == "refresh_offer_dropdown":
                    self._refresh_offer_dropdown()
                elif action == "hide_search_popup":
                    self._ss_hide()
                elif action == "hide_customer_suggestions":
                    self._hide_suggestions()
            except Exception:
                pass

    def prefill_from_booking(self, booking):
        values = booking_prefill_values(booking)
        if has_existing_booking_draft(self.bill_items, self.name_ent.get(), self.phone_ent.get()):
            title, msg = booking_clear_confirmation_message()
            if not messagebox.askyesno(title, msg):
                return
        self.clear_all()
        self.name_ent.insert(0, values["customer_name"])
        self.phone_ent.insert(0, values["phone"])
        service_name = values["service"]
        if service_name:
            try:
                self.set_mode("services")
            except Exception:
                pass
            exact = self._get_exact_match(service_name)
            if exact:
                self._apply_search_selection(exact)
                self.add_item()
            else:
                self.search_var.set(service_name)
        try:
            self._refresh_bill()
        except Exception:
            pass

    def _right_click_menu(self, e=None):
        """
        Bug 4 fix: removed finally: grab_release() which prevented
        menu items from being clicked on Windows.
        """
        if not should_show_billing_context_menu(self.bill_items): return
        try:
            self._register_billing_context_menu_callbacks()
            from shared.context_menu.constants import WidgetType
            from shared.context_menu.menu_context_factory import build_context
            from shared.context_menu.renderer import renderer_service
            from shared.context_menu_definitions.billing_context_menu import get_sections

            total_amount = context_total_from_totals(self._calc_totals())
            context = build_context(
                "billing",
                entity_type="current_bill",
                entity_id=self._current_invoice,
                widget_type=WidgetType.TEXT,
                widget_id="billing_preview",
                screen_x=getattr(e, "x_root", None),
                screen_y=getattr(e, "y_root", None),
                user_role=self.app.current_user.get("role", "") if getattr(self.app, "current_user", None) else "",
                extra=build_billing_context_extra(self.bill_items, self._current_invoice, total_amount),
            )
            menu = renderer_service.build_menu(self, get_sections(), context)
            menu.tk_popup(e.x_root, e.y_root)   # Bug 4 fix: no grab_release here
        except Exception as exc:
            app_log(f"[billing context menu] {exc}")

    def _register_billing_context_menu_callbacks(self):
        from shared.context_menu.action_adapter import action_adapter
        from shared.context_menu.clipboard_service import clipboard_service
        from shared.context_menu_definitions.billing_context_menu import BillingContextAction

        for action_name, method_name in billing_context_action_specs():
            action_adapter.register(
                getattr(BillingContextAction, action_name),
                lambda _ctx, _act, method_name=method_name: getattr(self, method_name)(),
            )
        for action_name, extra_key, value_type in billing_context_copy_specs():
            action_adapter.register(
                getattr(BillingContextAction, action_name),
                lambda ctx, _act, extra_key=extra_key, value_type=value_type: clipboard_service.copy_text(
                    self,
                    format_context_clipboard_value(ctx.extra, extra_key, value_type),
                ),
            )

    def _bind_shortcuts(self):
        """Keyboard shortcuts for fast billing."""
        root = self.winfo_toplevel()
        for sequence, method_name in billing_root_shortcut_specs():
            root.bind(sequence, lambda _event, method_name=method_name: getattr(self, method_name)())
        for sequence, method_name in billing_bind_all_shortcut_specs():
            self.bind_all(sequence, lambda _event, method_name=method_name: getattr(self, method_name)())
        # Search entry has its own Return binding from _build().
        # Price and quantity entries add the selected item directly.
        for widget_name, sequence, method_name in billing_widget_shortcut_specs():
            getattr(self, widget_name).bind(
                sequence,
                lambda _event, method_name=method_name: getattr(self, method_name)(),
            )

    def _toggle_fast_mode(self):
        try:
            self.fast_mode = next_fast_mode(self.fast_mode)
            self._update_fast_mode_ui()
        except Exception as e:
            app_log(f"[_toggle_fast_mode] {e}")

    def _update_fast_mode_ui(self):
        try:
            if hasattr(self, "fast_btn"):
                view = fast_mode_button_view(self.fast_mode)
                self.fast_btn.set_text(view["text"])
                self.fast_btn.set_color(C[view["color_key"]], C[view["hover_key"]])
        except Exception as e:
            app_log(f"[_update_fast_mode_ui] {e}")

    def reload_services(self):
        """Called after admin panel closes to refresh service data."""
        try:
            refresh_product_catalog_cache()
            reset_state = reload_services_reset_state()
            self._inventory_lookup_cache = reset_state["inventory_lookup_cache"]
            self._inventory_lookup_cache_time = reset_state["inventory_lookup_cache_time"]
            self.services_data, self.products_data = _load_services_products()
            self._refresh_cats()
            self._selected_product_variant = None
            self._refresh_quantity_unit_hint()
            self.search_var.set(reset_state["search_text"])
            self.price_ent.delete(0, tk.END)
            self.price_ent.insert(0, reset_state["price_text"])
        except Exception as e:
            app_log(f"[reload_services] {e}")
