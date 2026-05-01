"""
Reports screen wrapper for sales lists, saved bills, exports, charts, and service summaries.

The heavy report logic is split into src.blite_v6.reports helper modules.
Keep ReportsFrame as the public Tkinter entry point used by main.py.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
import os
from utils import (C, fmt_currency,
                   today_str, month_str,
                   popup_window, app_log, validate_phone,
                   open_file_cross_platform, open_print_text_fallback)
from date_helpers import attach_date_mask, display_to_iso_date, iso_to_display_date, today_display_str, validate_display_date
from ui_theme import apply_treeview_column_alignment, ModernButton
from icon_system import get_action_icon
from src.blite_v6.app.window_lifecycle import hide_while_building, reveal_when_ready
from reports_data import read_report_rows
from reports_export import export_current_tree_csv
from reports_data import invalidate_report_cache
from src.blite_v6.reports.bill_text import build_bill_text as _build_bill_text
from src.blite_v6.reports.saved_bills import (
    build_saved_bill_preview_text,
    find_report_row_by_invoice,
    list_saved_bill_files,
    selected_saved_bill_from_tree,
)
from src.blite_v6.reports.report_view import (
    build_report_summary,
    max_report_page,
    paginate_report_rows,
    report_result_message,
    report_tree_values,
)
from src.blite_v6.reports.export_actions import (
    build_export_ui_result,
    collect_report_filters,
    run_customer_ledger_export,
    run_date_export,
    run_search_export,
    selected_customer_from_row,
)
from src.blite_v6.reports.service_report import (
    build_service_report_rows,
    max_service_report_page,
    paginate_service_report_rows,
    product_report_tree_values,
    service_report_tree_values,
)
from src.blite_v6.reports.delete_restore import (
    build_delete_audit_map,
    build_report_sales_context_row,
    delete_confirm_prompt,
    delete_target_label,
    deleted_bill_tree_values,
    deleted_bills_role_note,
    is_admin_or_manager,
    merge_trash_pdf_entry,
    normalize_deleted_db_entry,
    selected_report_bill_from_row,
    sort_deleted_entries,
)
from src.blite_v6.reports.chart_data import (
    daily_revenue_series,
    monthly_revenue_series,
    payment_revenue_series,
    top_services_revenue_series,
)
from src.blite_v6.reports.grocery_report_view import GroceryReportPanel

_REPORT_CACHE = {}
_REPORT_SOURCE_CACHE = {}
_REPORT_CACHE_MAX_SIZE = 50  # Phase 4: prevent unbounded cache growth


class ReportsFrame(tk.Frame):

    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app    = app
        self._rmap  = {}
        self._rows  = []
        self._report_page = 0        # Phase 3B: pagination state
        self._service_page = 0       # Phase 3B: service report pagination
        self._REPORT_PAGE_SIZE = 80  # Phase 3B: show 80 rows per page
        self._build()

    def _build(self):
        # Header (UI polish)
        hdr = tk.Frame(self, bg=C["bg"], pady=6)
        hdr.pack(fill=tk.X)
        left_f = tk.Frame(hdr, bg=C["bg"])
        left_f.pack(side=tk.LEFT, padx=20)
        tk.Label(left_f, text="Sales Reports",
                 font=("Arial", 17, "bold"),
                 bg=C["bg"], fg=C["text"]).pack(anchor="w")
        tk.Label(left_f, text="Analyse sales, bills, service revenue, and saved invoice activity",
                 font=("Arial", 10), bg=C["bg"], fg=C["muted"]).pack(anchor="w")
        excel_icon = get_action_icon("import_excel")
        csv_icon = get_action_icon("import_json")
        ModernButton(hdr, text="Export Excel",
                     image=excel_icon, compound="left",
                     command=self._export_excel,
                     color=C["green"], hover_color="#1a7a45",
                     width=90, height=32, radius=8,
                     font=("Arial",10,"bold"),
                     ).pack(side=tk.RIGHT, padx=(0,6), pady=6)
        ModernButton(hdr, text="Export CSV",
                     image=csv_icon, compound="left",
                     command=self._export_csv,
                     color=C["blue"], hover_color="#154360",
                     width=80, height=32, radius=8,
                     font=("Arial",10,"bold"),
                     ).pack(side=tk.RIGHT, padx=(0,4), pady=6)
        pdf_icon_btn = get_action_icon("pdf")
        ModernButton(hdr, text="Export PDF",
                     image=pdf_icon_btn, compound="left",
                     command=self._export_pdf,
                     color=C["red"], hover_color="#a01515",
                     width=84, height=32, radius=8,
                     font=("Arial",10,"bold"),
                     ).pack(side=tk.RIGHT, padx=(0,4), pady=6)
        gst_icon = get_action_icon("import_excel")
        ModernButton(hdr, text="GST Export",
                     image=gst_icon, compound="left",
                     command=self._export_gst,
                     color=C["orange"], hover_color="#a06200",
                     width=84, height=32, radius=8,
                     font=("Arial",10,"bold"),
                     ).pack(side=tk.RIGHT, padx=(0,4), pady=6)
        more_icon = get_action_icon("import_excel")
        ModernButton(hdr, text="More Exports",
                     image=more_icon, compound="left",
                     command=self._open_export_center,
                     color=C["teal"], hover_color=C["blue"],
                     width=108, height=32, radius=8,
                     font=("Arial",10,"bold"),
                     ).pack(side=tk.RIGHT, padx=(0,4), pady=6)
        trash_icon = get_action_icon("delete")
        ModernButton(hdr, text="View Deleted",
                     image=trash_icon, compound="left",
                     command=self._show_deleted_bills,
                     color=C["purple"], hover_color="#6c3fa0",
                     width=110, height=32, radius=8,
                     font=("Arial",10,"bold"),
                     ).pack(side=tk.RIGHT, padx=(0,6), pady=6)
        tk.Frame(self, bg=C["teal"], height=2).pack(fill=tk.X)
        top_band = tk.Frame(self, bg=C["bg"])
        top_band.pack(fill=tk.X, padx=15, pady=8)
        intro = tk.Frame(top_band, bg=C["card"], padx=18, pady=12)
        intro.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(intro, text="Reports Workspace",
                 font=("Arial", 16, "bold"),
                 bg=C["card"], fg=C["text"]).pack(anchor="w")
        tk.Label(intro, text="Filter quickly, review bills, and export data without leaving the workspace.",
                 font=("Arial", 10), bg=C["card"], fg=C["muted"]).pack(anchor="w", pady=(4, 0))

        self.cards_f = tk.Frame(top_band, bg=C["bg"])
        self.cards_f.pack(side=tk.LEFT, padx=(12, 0))

        # Notebook
        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))

        self.tab_list    = tk.Frame(nb, bg=C["bg"])
        self.tab_charts  = tk.Frame(nb, bg=C["bg"])
        self.tab_bills   = tk.Frame(nb, bg=C["bg"])
        self.tab_service = tk.Frame(nb, bg=C["bg"])
        self.tab_grocery = tk.Frame(nb, bg=C["bg"])
        nb.add(self.tab_list,    text="Sales List")
        nb.add(self.tab_charts,  text="Charts")
        nb.add(self.tab_bills,   text="Saved Bills (PDF)")
        nb.add(self.tab_service, text="Service Report")
        nb.add(self.tab_grocery, text="Grocery Reports")
        nb.bind("<<NotebookTabChanged>>",
                lambda e: self._on_tab_change(nb))

        self._build_list_tab()
        self._build_charts_tab()
        self._build_bills_tab()
        self._build_service_tab()
        self._build_grocery_tab()
        self._load()

    def _build_grocery_tab(self):
        self.grocery_report_panel = GroceryReportPanel(
            self.tab_grocery,
            read_rows=_read_report,
        )
        self.grocery_report_panel.pack(fill=tk.BOTH, expand=True)

    # Summary cards
    def _update_cards(self, rows):
        for w in self.cards_f.winfo_children(): w.destroy()
        summary = build_report_summary(rows, today_str(), month_str())

        for lbl, val, col in [
            ("Today",          fmt_currency(summary.today_total), C["teal"]),
            ("This Month",     fmt_currency(summary.month_total), C["blue"]),
            ("Filtered Total", fmt_currency(summary.filtered_total), C["purple"]),
            ("Bills",          str(summary.count), C["orange"]),
            ("Avg Bill",       fmt_currency(summary.average), C["green"]),
        ]:
            card = tk.Frame(self.cards_f, bg=col, padx=18, pady=8)
            card.pack(side=tk.LEFT, padx=(0, 6))
            tk.Label(card, text=val, font=("Arial", 12, "bold"),
                     bg=col, fg="white").pack()
            tk.Label(card, text=lbl, font=("Arial", 10),
                     bg=col, fg="white").pack()

    # Sales list tab
    def _build_list_tab(self):
        # Filter bar
        ff_wrap = tk.Frame(self.tab_list, bg=C["card"], pady=8)
        ff_wrap.pack(fill=tk.X, padx=5, pady=(2, 8))
        ff = tk.Frame(ff_wrap, bg=C["card"])
        ff.pack(fill=tk.X, padx=14)

        tk.Label(ff, text="Search", bg=C["card"], fg=C["muted"],
                 font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0,4))
        self.search_var = tk.StringVar()
        se = tk.Entry(ff, textvariable=self.search_var,
                      font=("Arial", 12), bg=C["input"],
                      fg=C["text"], bd=0, width=20,
                      insertbackground=C["accent"])
        se.pack(side=tk.LEFT, ipady=4, padx=(0, 10))

        for lbl_txt, attr, default in [
            ("From:", "from_ent", iso_to_display_date(date.today().strftime("%Y-%m-01"))),
            ("To:",   "to_ent",   today_display_str()),
        ]:
            tk.Label(ff, text=lbl_txt, bg=C["card"],
                     fg=C["muted"], font=("Arial", 11)).pack(side=tk.LEFT, padx=(0,3))
            e = tk.Entry(ff, font=("Arial", 12), bg=C["input"],
                         fg=C["text"], bd=0, width=13,
                         insertbackground=C["accent"])
            e.pack(side=tk.LEFT, ipady=4, padx=(0, 8))
            e.insert(0, default)
            attach_date_mask(e)
            e.bind("<FocusOut>", lambda ev: (self._reset_report_pagination(), self._load()))
            setattr(self, attr, e)

        print_icon = get_action_icon("print")
        add_icon = get_action_icon("add")
        refresh_icon = get_action_icon("refresh")
        pdf_icon = get_action_icon("pdf")
        wa_icon = get_action_icon("whatsapp")
        delete_icon = get_action_icon("delete")
        restore_icon = get_action_icon("restore")
        clear_icon = get_action_icon("clear")

        for txt, col, cmd in [
            ("Filter",     C["teal"],   lambda: (self._reset_report_pagination(), self._load())),
            ("Today",      C["blue"],   lambda: (self._reset_report_pagination(), self._set_today())),
            ("This Month", C["purple"], lambda: (self._reset_report_pagination(), self._set_month())),
            ("All",        "#636e72",   lambda: (self._reset_report_pagination(), self._set_all())),
        ]:
            btn_icon = {
                "Filter": refresh_icon,
                "Today": refresh_icon,
                "This Month": refresh_icon,
                "All": clear_icon,
            }.get(txt)
            ModernButton(ff, text=txt, image=btn_icon, compound="left", command=cmd,
                         color=col, hover_color=C["blue"],
                         width=100, height=30, radius=8,
                         font=("Arial",10,"bold"),
                         ).pack(side=tk.LEFT, padx=2)

        self.search_var.trace("w", lambda *a: (self._reset_report_pagination(), self._load()))

        # Phase 5.6.1 Phase 2: visible search result count label
        self._report_result_label = tk.Label(ff, text="", bg=C["card"],
                                             fg=C["muted"], font=("Arial", 10))
        self._report_result_label.pack(side=tk.LEFT, padx=(4, 0))

        # Saved bill file list pane
        pane = tk.PanedWindow(self.tab_list, orient=tk.HORIZONTAL,
                               sashrelief=tk.RAISED, sashwidth=6,
                               bg=C["bg"])
        pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))

        # Sales table pane
        left_f = tk.Frame(pane, bg=C["bg"])
        pane.add(left_f, minsize=580)

        self._show_bill_audit = str(
            getattr(getattr(self, "app", None), "current_user", {}).get("role", "staff")
        ).strip().lower() in {"owner", "admin", "manager"}
        cols = ("Date", "Time", "Invoice", "Customer", "Phone", "Pay", "Discount", "Total")
        self.tree = ttk.Treeview(left_f, columns=cols,
                                  show="headings", height=20)
        widths = [112, 78, 102, 160, 116, 82, 92, 120]
        for col, w in zip(cols, widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w)
        apply_treeview_column_alignment(self.tree)

        vsb = ttk.Scrollbar(left_f, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        vsb.pack(side=tk.LEFT, fill=tk.Y)

        # Phase 3B: pagination nav container for sales list
        self._report_pager_wrap = tk.Frame(left_f, bg=C["bg"])
        self._report_pager_wrap.pack(fill=tk.X)

        # Preview and quick actions pane
        right_f = tk.Frame(pane, bg=C["bg"])
        pane.add(right_f, minsize=300)

        preview_hdr = tk.Frame(right_f, bg=C["card"], pady=8, padx=12)
        preview_hdr.pack(fill=tk.X)
        preview_top = tk.Frame(preview_hdr, bg=C["card"])
        preview_top.pack(fill=tk.X)
        tk.Label(preview_top, text="Preview & Quick Actions",
                 font=("Arial", 12, "bold"),
                 bg=C["card"], fg=C["text"]).pack(side=tk.LEFT)
        action_row = tk.Frame(preview_top, bg=C["card"])
        action_row.pack(side=tk.RIGHT)
        ModernButton(action_row, text="Load to Bill", image=add_icon, compound="left",
                     command=self._load_to_bill,
                     color=C["teal"], hover_color=C["blue"],
                     width=110, height=28, radius=8,
                     font=("Arial",9,"bold"),
                     ).pack(side=tk.LEFT, padx=(0,6))
        ModernButton(action_row, text="Print", image=print_icon, compound="left",
                     command=self._print_preview,
                     color=C["blue"], hover_color="#154360",
                     width=80, height=28, radius=8,
                     font=("Arial",9,"bold"),
                     ).pack(side=tk.LEFT, padx=(0,6))
        ModernButton(action_row, text="Delete Bill", image=delete_icon, compound="left",
                     command=self._delete_selected_report_bill,
                     color=C["red"], hover_color="#c0392b",
                     width=110, height=28, radius=8,
                     font=("Arial",9,"bold"),
                     ).pack(side=tk.LEFT)
        tk.Label(preview_hdr,
                 text="Select a bill from the list",
                 font=("Arial", 10),
                 bg=C["card"], fg=C["muted"]).pack(anchor="e", pady=(6, 0))
        self.audit_note_lbl = tk.Label(
            right_f,
            text="",
            font=("Arial", 10, "bold"),
            bg=C["bg"],
            fg=C["teal"],
            anchor="w",
            padx=4,
            pady=4,
        )
        self.audit_note_lbl.pack(fill=tk.X, padx=(2, 0), pady=(4, 2))

        self.preview_txt = tk.Text(
            right_f,
            font=("Courier New", 11),
            bg="#fafafa", fg="#2d3436",
            padx=12, pady=12, bd=0,
            state="disabled", wrap="none")
        pvsb = ttk.Scrollbar(right_f, orient="vertical",
                              command=self.preview_txt.yview)
        self.preview_txt.configure(yscrollcommand=pvsb.set)
        self.preview_txt.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        pvsb.pack(side=tk.LEFT, fill=tk.Y)
        self.after(80, lambda: pane.sash_place(0, int(max(600, self.tab_list.winfo_width() * 0.60)), 1))

        # Bind single + double click
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>",         self._on_select)
        self.tree.bind("<Button-3>", self._show_report_sales_context_menu)

    def _show_report_sales_context_menu(self, event):
        row_id = self.tree.identify_row(event.y)
        if not row_id:
            return "break"
        try:
            self.tree.selection_set(row_id)
            self.tree.focus(row_id)
            values = self.tree.item(row_id, "values")
            if not values:
                return "break"
            self._on_select()
            self._register_report_context_menu_callbacks()

            from shared.context_menu.constants import WidgetType
            from shared.context_menu.menu_context_factory import build_context
            from shared.context_menu.renderer import renderer_service
            from shared.context_menu_definitions.report_context_menu import get_sales_sections

            row = self._rmap.get(row_id, {}) or {}
            selected_row = build_report_sales_context_row(row_id, values, row)
            invoice_no = selected_row["invoice"]
            context = build_context(
                "reports",
                entity_type="sales_bill",
                entity_id=invoice_no,
                selected_row=selected_row,
                selection_count=1,
                user_role=self.app.current_user.get("role", "") if getattr(self.app, "current_user", None) else "",
                widget_type=WidgetType.TREEVIEW,
                widget_id="reports_sales_grid",
                screen_x=event.x_root,
                screen_y=event.y_root,
                extra={"has_sales_bill": True},
            )
            menu = renderer_service.build_menu(self, get_sales_sections(), context)
            menu.tk_popup(event.x_root, event.y_root)
            return "break"
        except Exception as exc:
            app_log(f"[reports sales context menu] {exc}")
            return "break"

    def _on_select(self, e=None):
        """Show full bill preview when a report row is selected."""
        sel = self.tree.selection()
        if not sel: return
        r = self._rmap.get(sel[0], {})
        if not r: return
        try:
            bill_text = _build_bill_text(r)
            if self._show_bill_audit:
                billed_by = str(r.get("created_by", "")).strip() or "Unknown"
                billed_time = str(r.get("time", str(r.get("date", ""))[11:16])).strip() or "--:--"
                self.audit_note_lbl.config(text=f"Billed By: {billed_by}    Time: {billed_time}")
            else:
                self.audit_note_lbl.config(text="")
            self.preview_txt.config(state="normal")
            self.preview_txt.delete("1.0", tk.END)
            self.preview_txt.insert(tk.END, bill_text)
            self.preview_txt.config(state="disabled")
        except Exception as e:
            app_log(f"[_on_select] {e}")

    # Charts tab
    def _build_charts_tab(self):
        self._chart_frame = tk.Frame(self.tab_charts, bg=C["bg"])
        self._chart_frame.pack(fill=tk.BOTH, expand=True)
        self._chart_type  = tk.StringVar(value="daily")

        ctrl = tk.Frame(self.tab_charts, bg=C["bg"])
        ctrl.pack(fill=tk.X, padx=15, pady=8, before=self._chart_frame)
        tk.Label(ctrl, text="Chart:", bg=C["bg"],
                 fg=C["muted"], font=("Arial", 12)).pack(side=tk.LEFT, padx=(0, 8))
        for txt, val in [("Daily (30 days)", "daily"),
                          ("Monthly",         "monthly"),
                          ("Payment Method",  "payment"),
                          ("Top Services",    "services")]:
            tk.Radiobutton(ctrl, text=txt,
                           variable=self._chart_type, value=val,
                           bg=C["bg"], fg=C["text"],
                           selectcolor=C["input"], font=("Arial", 11),
                           command=self._draw_chart,
                           cursor="hand2").pack(side=tk.LEFT, padx=6)

    # Saved bills tab
    def _build_bills_tab(self):
        from utils import BILLS_DIR
        pdf_icon = get_action_icon("pdf")
        print_icon = get_action_icon("print")
        wa_icon = get_action_icon("whatsapp")
        delete_icon = get_action_icon("delete")

        # Toolbar
        tb_wrap = tk.Frame(self.tab_bills, bg=C["card"], pady=8)
        tb_wrap.pack(fill=tk.X, padx=10, pady=(2, 8))
        tb = tk.Frame(tb_wrap, bg=C["card"])
        tb.pack(fill=tk.X, padx=14)

        tk.Label(tb, text="Search", bg=C["card"], fg=C["muted"],
                 font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        self.bill_search = tk.StringVar()
        se = tk.Entry(tb, textvariable=self.bill_search,
                      font=("Arial",12), bg=C["input"],
                      fg=C["text"], bd=0, width=25,
                      insertbackground=C["accent"])
        se.pack(side=tk.LEFT, ipady=5, padx=(4,10))
        self.bill_search.trace("w", lambda *a: self._load_bills())

        ModernButton(tb, text="Refresh",
                     command=self._load_bills,
                     color=C["teal"], hover_color=C["blue"],
                     width=96, height=30, radius=8,
                     font=("Arial",10,"bold"),
                     ).pack(side=tk.LEFT, padx=(0,6))

        ModernButton(tb, text="Open Folder",
                     command=lambda: (open_file_cross_platform(BILLS_DIR) if os.path.exists(BILLS_DIR) else None),
                     color=C["blue"], hover_color="#154360",
                     width=116, height=30, radius=8,
                     font=("Arial",10,"bold"),
                     ).pack(side=tk.LEFT)

        self.bill_count_lbl = tk.Label(tb, text="",
                                        bg=C["card"], fg=C["muted"],
                                        font=("Arial",11))
        self.bill_count_lbl.pack(side=tk.RIGHT)

        # Split pane: left=file list, right=preview
        pane = tk.PanedWindow(self.tab_bills, orient=tk.HORIZONTAL,
                               sashrelief=tk.RAISED, sashwidth=6,
                               bg=C["bg"])
        pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0,5))

        # Saved bill file list pane
        left_f = tk.Frame(pane, bg=C["bg"])
        pane.add(left_f, minsize=320)

        cols = ("Invoice", "Customer", "Date", "Size")
        self.bills_tree = ttk.Treeview(left_f, columns=cols,
                                        show="headings", height=20)
        for col, w in zip(cols, [100, 160, 120, 70]):
            self.bills_tree.heading(col, text=col)
            self.bills_tree.column(col, width=w)
        apply_treeview_column_alignment(self.bills_tree)
        vsb = ttk.Scrollbar(left_f, orient="vertical",
                             command=self.bills_tree.yview)
        self.bills_tree.configure(yscrollcommand=vsb.set)
        self.bills_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        vsb.pack(side=tk.LEFT, fill=tk.Y)

        # Saved bill preview pane
        right_f = tk.Frame(pane, bg=C["bg"])
        pane.add(right_f, minsize=460)

        # Action buttons
        act_f = tk.Frame(right_f, bg=C["card"], pady=8, padx=12)
        act_f.pack(fill=tk.X)
        tk.Label(act_f, text="Saved Bill Preview",
                 font=("Arial",12,"bold"),
                 bg=C["card"], fg=C["text"]).pack(side=tk.LEFT)

        for txt, col, cmd in [
            ("Open PDF",  C["blue"],   self._open_bill_pdf),
            ("Print",     "#0984e3",   self._print_bill_pdf),
            ("WhatsApp",  "#25d366",   self._wa_bill),
            ("Delete",    C["red"],    self._delete_bill),
        ]:
            btn_icon = {
                "Open PDF": pdf_icon,
                "Print": print_icon,
                "WhatsApp": wa_icon,
                "Delete": delete_icon,
            }.get(txt)
            ModernButton(act_f, text=txt, image=btn_icon, compound="left", command=cmd,
                         color=col, hover_color=C["blue"],
                         width=104, height=28, radius=8,
                         font=("Arial",9,"bold"),
                         ).pack(side=tk.RIGHT, padx=2)

        # PDF text preview
        self.bill_preview = tk.Text(right_f,
                                     font=("Courier New",11),
                                     bg="#fafafa", fg="#2d3436",
                                     padx=12, pady=12, bd=0,
                                     state="disabled", wrap="none")
        pvsb = ttk.Scrollbar(right_f, orient="vertical",
                              command=self.bill_preview.yview)
        self.bill_preview.configure(yscrollcommand=pvsb.set)
        self.bill_preview.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        pvsb.pack(side=tk.LEFT, fill=tk.Y)

        self.bills_tree.bind("<<TreeviewSelect>>", self._preview_bill_file)
        self.bills_tree.bind("<Double-1>", lambda e: self._open_bill_pdf())
        self.bills_tree.bind("<Button-3>", self._show_saved_bill_context_menu)

        self._bills_files = {}   # filename -> filepath

    def _show_saved_bill_context_menu(self, event):
        row_id = self.bills_tree.identify_row(event.y)
        if not row_id:
            return "break"
        try:
            self.bills_tree.selection_set(row_id)
            self.bills_tree.focus(row_id)
            values = self.bills_tree.item(row_id, "values")
            if not values:
                return "break"
            self._preview_bill_file()
            self._register_report_context_menu_callbacks()

            from shared.context_menu.constants import WidgetType
            from shared.context_menu.menu_context_factory import build_context
            from shared.context_menu.renderer import renderer_service
            from shared.context_menu_definitions.report_context_menu import get_saved_bill_sections

            bill = self._get_selected_saved_bill() or {}
            selected_row = {
                "row_id": row_id,
                "invoice": bill.get("invoice_no", values[0] if len(values) > 0 else ""),
                "customer": bill.get("customer_name", values[1] if len(values) > 1 else ""),
                "date": values[2] if len(values) > 2 else "",
                "size": values[3] if len(values) > 3 else "",
                "file_path": bill.get("file_path", ""),
                "file_name": bill.get("file_name", ""),
            }
            context = build_context(
                "reports",
                entity_type="saved_bill",
                entity_id=selected_row["invoice"],
                selected_row=selected_row,
                selection_count=1,
                user_role=self.app.current_user.get("role", "") if getattr(self.app, "current_user", None) else "",
                widget_type=WidgetType.TREEVIEW,
                widget_id="reports_saved_bills_grid",
                screen_x=event.x_root,
                screen_y=event.y_root,
                extra={"has_saved_bill": True},
            )
            menu = renderer_service.build_menu(self, get_saved_bill_sections(), context)
            menu.tk_popup(event.x_root, event.y_root)
            return "break"
        except Exception as exc:
            app_log(f"[reports saved bill context menu] {exc}")
            return "break"

    def _load_bills(self):
        """Load saved bill files and log failures without closing Reports."""
        try:
            self._load_bills_inner()
        except Exception as e:
            app_log(f"[_load_bills] {e}")

    def _load_bills_inner(self):
        from utils import BILLS_DIR
        for i in self.bills_tree.get_children(): self.bills_tree.delete(i)
        self._bills_files = {}

        q = self.bill_search.get().lower()
        saved_files = list_saved_bill_files(BILLS_DIR, q)

        for saved_file in saved_files:
            iid = self.bills_tree.insert("", tk.END,
                                          values=saved_file.tree_values)
            self._bills_files[iid] = saved_file.file_path

        count = len(self._bills_files)
        self.bill_count_lbl.config(text=f"Total: {count} bills")

    def _preview_bill_file(self, e=None):
        """Show text preview extracted from saved PDF."""
        sel = self.bills_tree.selection()
        if not sel: return
        fpath = self._bills_files.get(sel[0])
        if not fpath: return

        self.bill_preview.config(state="normal")
        self.bill_preview.delete("1.0", tk.END)
        preview_text = build_saved_bill_preview_text(fpath, self._rows, _build_bill_text)
        self.bill_preview.insert(tk.END, preview_text)
        self.bill_preview.config(state="disabled")

    def _open_bill_pdf(self):
        """Fix R10e: cross-platform open + try/except."""
        sel = self.bills_tree.selection()
        if not sel:
            messagebox.showwarning("Select","Select a bill."); return
        fpath = self._bills_files.get(sel[0])
        if fpath and os.path.exists(fpath):
            try:
                from utils import open_file_cross_platform
                open_file_cross_platform(fpath)
            except Exception as e:
                app_log(f"[_open_bill_pdf] {e}")
                messagebox.showerror("Error", f"Could not open file: {e}")

    def _print_bill_pdf(self):
        sel = self.bills_tree.selection()
        if not sel:
            messagebox.showwarning("Select","Select a bill."); return
        fpath = self._bills_files.get(sel[0])
        if not fpath: return
        try:
            import win32api
            win32api.ShellExecute(0,"print",fpath,None,".",0)
            messagebox.showinfo("Printing","Sent to printer!")
        except Exception:
            try:
                open_file_cross_platform(fpath)
            except Exception:
                pass
            messagebox.showinfo("Open PDF", "PDF opened. Use File -> Print to print.")

    def _wa_bill(self):
        sel = self.bills_tree.selection()
        if not sel:
            messagebox.showwarning("Select","Select a bill."); return
        values = self.bills_tree.item(sel[0],"values")
        fname = values[1] if len(values) > 1 else ""   # customer name
        # Match phone from report
        inv_no = values[0] if values else ""
        matched = find_report_row_by_invoice(self._rows, inv_no)
        phone = matched.get("phone","") if matched else ""
        # Fix R10f: centralized phone validation
        if not validate_phone(phone):
            import tkinter.simpledialog
            phone_dialog = tkinter.simpledialog.askstring(
                "Phone","Enter customer phone (10 digits):") or ""
            phone = phone_dialog.strip()
        if not validate_phone(phone):
            messagebox.showerror("Error","Valid phone required."); return
        fpath = self._bills_files.get(sel[0])
        import threading
        def _send():
            try:
                from whatsapp_helper import send_image
                ok = send_image(phone, fpath,
                                 f"Dear {fname}, please find your bill. Thank you!")
                self.after(0, lambda: messagebox.showinfo(
                    "WhatsApp", "Bill sent!" if ok else "Send failed"))
            except Exception as ex:
                self.after(0, lambda: messagebox.showerror("Error",str(ex)))
        threading.Thread(target=_send, daemon=True).start()

    def _get_selected_saved_bill(self) -> dict | None:
        sel = self.bills_tree.selection()
        if not sel:
            return None
        iid = sel[0]
        values = self.bills_tree.item(iid, "values")
        return selected_saved_bill_from_tree(iid, values, self._bills_files)

    def _get_selected_report_bill(self) -> dict | None:
        from utils import BILLS_DIR
        sel = self.tree.selection()
        if not sel:
            return None
        return selected_report_bill_from_row(sel[0], self._rmap.get(sel[0], {}) or {}, BILLS_DIR)

    def _register_report_context_menu_callbacks(self):
        from shared.context_menu.action_adapter import action_adapter
        from shared.context_menu.clipboard_service import clipboard_service
        from shared.context_menu_definitions.report_context_menu import ReportContextAction, SavedBillContextAction

        action_adapter.register(ReportContextAction.PREVIEW, lambda _ctx, _act: self._on_select())
        action_adapter.register(ReportContextAction.LOAD_TO_BILL, lambda _ctx, _act: self._load_to_bill())
        action_adapter.register(ReportContextAction.PRINT, lambda _ctx, _act: self._print_preview())
        action_adapter.register(ReportContextAction.EXPORT_PDF, lambda _ctx, _act: self._export_pdf())
        action_adapter.register(ReportContextAction.EXPORT_EXCEL, lambda _ctx, _act: self._export_excel())
        action_adapter.register(ReportContextAction.EXPORT_CSV, lambda _ctx, _act: self._export_csv())
        action_adapter.register(
            ReportContextAction.COPY_INVOICE,
            lambda ctx, _act: clipboard_service.copy_text(self, ctx.selected_row.get("invoice", "")),
        )
        action_adapter.register(
            ReportContextAction.COPY_CUSTOMER,
            lambda ctx, _act: clipboard_service.copy_text(self, ctx.selected_row.get("customer", "")),
        )
        action_adapter.register(
            ReportContextAction.COPY_TOTAL,
            lambda ctx, _act: clipboard_service.copy_text(self, ctx.selected_row.get("total", "")),
        )
        action_adapter.register(ReportContextAction.REFRESH, lambda _ctx, _act: self._load())
        action_adapter.register(ReportContextAction.DELETE, lambda _ctx, _act: self._delete_selected_report_bill())

        action_adapter.register(SavedBillContextAction.OPEN_PDF, lambda _ctx, _act: self._open_bill_pdf())
        action_adapter.register(SavedBillContextAction.PRINT_PDF, lambda _ctx, _act: self._print_bill_pdf())
        action_adapter.register(SavedBillContextAction.WHATSAPP, lambda _ctx, _act: self._wa_bill())
        action_adapter.register(
            SavedBillContextAction.COPY_INVOICE,
            lambda ctx, _act: clipboard_service.copy_text(self, ctx.selected_row.get("invoice", "")),
        )
        action_adapter.register(
            SavedBillContextAction.COPY_CUSTOMER,
            lambda ctx, _act: clipboard_service.copy_text(self, ctx.selected_row.get("customer", "")),
        )
        action_adapter.register(
            SavedBillContextAction.COPY_FILE_PATH,
            lambda ctx, _act: clipboard_service.copy_text(self, ctx.selected_row.get("file_path", "")),
        )
        action_adapter.register(SavedBillContextAction.REFRESH, lambda _ctx, _act: self._load_bills())
        action_adapter.register(SavedBillContextAction.DELETE, lambda _ctx, _act: self._delete_bill())

    def _delete_bill_entry(self, bill: dict, *, source_label: str) -> bool:
        invoice_no = str(bill.get("invoice_no", "")).strip()
        customer_name = str(bill.get("customer_name", "")).strip()
        fpath = str(bill.get("file_path", "")).strip()
        fname = str(bill.get("file_name", "")).strip()
        actor = self.app.current_user.get("username", "") if hasattr(self.app, "current_user") else ""

        if not invoice_no and not fpath:
            messagebox.showwarning("Select", "Select a bill to delete.")
            return False

        target_label = delete_target_label(bill)
        prompt = delete_confirm_prompt(bill, source_label)
        if not messagebox.askyesno("Move to Trash", prompt):
            return False

        try:
            from soft_delete import soft_delete_bill
            from utils import TRASH_DIR
            import shutil

            os.makedirs(TRASH_DIR, exist_ok=True)
            moved_pdf = False
            if fpath and os.path.exists(fpath):
                if not fname:
                    fname = os.path.basename(fpath)
                shutil.move(fpath, os.path.join(TRASH_DIR, fname))
                moved_pdf = True
            if invoice_no:
                soft_delete_bill(invoice_no, deleted_by=actor)

            invalidate_report_cache()
            self._load()
            self._load_bills()
            if moved_pdf:
                messagebox.showinfo(
                    "Moved",
                    f"{target_label} moved to deleted history.\nPDF was moved to Trash and can be restored from View Deleted."
                )
            else:
                messagebox.showinfo(
                    "Deleted",
                    f"{target_label} moved to deleted history.\nThis bill had no saved PDF, so only the report record was soft-deleted."
                )
            return True
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return False

    def _delete_selected_report_bill(self):
        if not self.app.has_permission("delete_bill"):
            messagebox.showerror("Access Denied",
                                 "Bill deletion is restricted for your role.")
            return
        try:
            from salon_settings import get_settings
            cfg = get_settings()
            if cfg.get("require_pw_bill", False):
                import tkinter.simpledialog
                pwd = tkinter.simpledialog.askstring("Password Required",
                    "Enter your password to delete this bill:", show="*")
                if pwd is None:
                    return
                from auth import verify_login
                user = verify_login(self.app.current_user.get("username", ""), pwd)
                if user is None:
                    messagebox.showerror("Access Denied", "Incorrect password.")
                    return
        except Exception as e:
            app_log(f"[_delete_selected_report_bill password check] {e}")

        bill = self._get_selected_report_bill()
        if not bill:
            messagebox.showwarning("Select", "Select a bill row.")
            return
        self._delete_bill_entry(bill, source_label="Sales List")

    def _get_deleted_bill_entries(self) -> list[dict]:
        from soft_delete import get_deleted_bills, get_delete_audit_history
        from utils import TRASH_DIR

        entries: dict[str, dict] = {}
        try:
            for row in get_deleted_bills():
                entry = normalize_deleted_db_entry(row)
                if entry:
                    entries[entry["invoice_no"]] = entry
        except Exception as e:
            app_log(f"[_get_deleted_bill_entries db] {e}")

        audit_map: dict[str, dict] = {}
        try:
            audit_map = build_delete_audit_map(get_delete_audit_history("bill", limit=500))
        except Exception as e:
            app_log(f"[_get_deleted_bill_entries audit] {e}")

        try:
            os.makedirs(TRASH_DIR, exist_ok=True)
            for fname in sorted(os.listdir(TRASH_DIR), reverse=True):
                merge_trash_pdf_entry(entries, audit_map, TRASH_DIR, fname)
        except Exception as e:
            app_log(f"[_get_deleted_bill_entries trash] {e}")

        return sort_deleted_entries(list(entries.values()))

    def _delete_bill(self):
        if not self.app.has_permission("delete_bill"):
            messagebox.showerror("Access Denied",
                                 "Bill deletion is restricted for your role.")
            return
        try:
            from salon_settings import get_settings
            cfg = get_settings()
            if cfg.get("require_pw_bill", False):
                import tkinter.simpledialog
                pwd = tkinter.simpledialog.askstring("Password Required",
                    "Enter your password to delete this bill:", show="*")
                if pwd is None:
                    return
                from auth import verify_login
                user = verify_login(self.app.current_user.get("username", ""), pwd)
                if user is None:
                    messagebox.showerror("Access Denied", "Incorrect password.")
                    return
        except Exception as e:
            app_log(f"[_delete_bill password check] {e}")

        bill = self._get_selected_saved_bill()
        if not bill:
            return
        self._delete_bill_entry(bill, source_label="Saved Bills (PDF)")

    def _restore_bill(self):
        self._show_deleted_bills()
    def _on_tab_change(self, nb):
        idx = nb.index("current")
        if idx == 1: self._draw_chart()
        if idx == 2: self._load_bills()
        if idx == 3: self._gen_service_report()

    def _draw_chart(self):
        for w in self._chart_frame.winfo_children(): w.destroy()
        ct = self._chart_type.get()
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

            fig, ax = plt.subplots(figsize=(9, 4.2), facecolor="#1a1a2e")
            ax.set_facecolor("#16213e")
            ax.tick_params(colors="#94a3b8", labelsize=8)
            for spine in ax.spines.values():
                spine.set_edgecolor("#2d2d44")

            rows = _read_report()

            if ct == "daily":
                series = daily_revenue_series(rows, date.today())
                lbls = list(series.labels)
                vals = list(series.values)
                ax.bar(range(len(lbls)), vals, color="#ff79c6", width=0.7)
                ax.set_xticks(range(0, len(lbls), 5))
                ax.set_xticklabels([lbls[i] for i in range(0, len(lbls), 5)],
                                    rotation=30, ha="right")
                ax.set_title("Daily Revenue (Last 30 Days)",
                              color="#e8e8e8", fontsize=11)

            elif ct == "monthly":
                series = monthly_revenue_series(rows)
                lbls = list(series.labels)
                vals = list(series.values)
                ax.bar(range(len(lbls)), vals, color="#50fa7b", width=0.6)
                ax.set_xticks(range(len(lbls)))
                ax.set_xticklabels(lbls, rotation=30, ha="right")
                ax.set_title("Monthly Revenue", color="#e8e8e8", fontsize=11)

            elif ct == "payment":
                series = payment_revenue_series(rows)
                if series.values:
                    lbls = list(series.labels)
                    vals = list(series.values)
                    colors = ["#ff79c6","#50fa7b","#f39c12","#2980b9"]
                    ax.pie(vals, labels=lbls, colors=colors[:len(lbls)],
                            autopct="%1.1f%%",
                            textprops={"color":"#e8e8e8","fontsize":9})
                    ax.set_title("Revenue by Payment Method",
                                  color="#e8e8e8", fontsize=11)

            elif ct == "services":
                series = top_services_revenue_series(rows)
                if series.values:
                    lbls = list(series.labels)
                    vals = list(series.values)
                    ax.barh(range(len(lbls)), vals, color="#8be9fd")
                    ax.set_yticks(range(len(lbls)))
                    ax.set_yticklabels(lbls, fontsize=8)
                    ax.set_title("Top 10 Services by Revenue",
                                  color="#e8e8e8", fontsize=11)

            ax.yaxis.set_tick_params(labelcolor="#94a3b8")
            plt.tight_layout()
            canvas = FigureCanvasTkAgg(fig, master=self._chart_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            plt.close(fig)

        except ImportError:
            tk.Label(self._chart_frame,
                     text="Charts are unavailable in this source run.\nRebuild with matplotlib support to enable graphs.",
                     font=("Arial", 12), bg=C["bg"],
                     fg=C["muted"]).pack(expand=True)

    # Sales list loader
    def _load(self):
        """Load report rows and log failures without closing Reports."""
        try:
            self._load_inner()
        except Exception as e:
            app_log(f"[reports _load] {e}")

    def _load_inner(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        self._rmap = {}

        fd = getattr(self, "from_ent", None)
        fd = fd.get().strip() if fd else ""
        td = getattr(self, "to_ent",   None)
        td = td.get().strip() if td else ""
        sq = getattr(self, "search_var", tk.StringVar()).get().strip()

        if fd and not validate_display_date(fd):
            messagebox.showerror("Error", "From date must be DD-MM-YYYY format.\nExample: 01-03-2026")
            return
        if td and not validate_display_date(td):
            messagebox.showerror("Error", "To date must be DD-MM-YYYY format.\nExample: 25-03-2026")
            return
        fd = display_to_iso_date(fd) if fd else ""
        td = display_to_iso_date(td) if td else ""

        self._rows = _read_report(fd, td, sq)
        self._display_rows = list(self._rows)  # snapshot for pagination slicing

        # Reset service report pagination on reload
        if hasattr(self, "reset_service_pagination"):
            self._reset_service_pagination()

        # Phase 3B: clamp page index and build page slice
        page = paginate_report_rows(self._display_rows, self._report_page, self._REPORT_PAGE_SIZE)
        self._report_page = page.page

        for r in page.rows:
            node = self.tree.insert(
                "",
                tk.END,
                values=report_tree_values(r, display_date=iso_to_display_date, currency=fmt_currency),
            )
            self._rmap[node] = r

        self._update_cards(self._rows)
        self._update_report_pagination(page.total, page.max_page)

        # Clear preview
        if hasattr(self, "audit_note_lbl"):
            self.audit_note_lbl.config(
                text="Click a bill row to view billed-by audit info here." if self._show_bill_audit else ""
            )
        self.preview_txt.config(state="normal")
        self.preview_txt.delete("1.0", tk.END)
        self.preview_txt.insert(tk.END, "\n\n  Click a bill row to preview it here.")
        self.preview_txt.config(state="disabled")

    # Phase 3B: reports pagination helpers
    def _reset_report_pagination(self):
        self._report_page = 0

    def _report_prev_page(self):
        if self._report_page > 0:
            self._report_page -= 1
            self._load_inner()

    def _report_next_page(self):
        total = len(self._display_rows)
        max_page = max_report_page(total, self._REPORT_PAGE_SIZE)
        if self._report_page < max_page:
            self._report_page += 1
            self._load_inner()

    def _update_report_pagination(self, total, max_page):
        # Phase 5.6.1 Phase 2: update visible result count label
        sq = self.search_var.get().strip() if hasattr(self, "search_var") else ""
        if hasattr(self, "_report_result_label"):
            self._report_result_label.config(
                text=report_result_message(total, self._REPORT_PAGE_SIZE, sq)
            )

        for w in self._report_pager_wrap.winfo_children():
            w.destroy()
        if total <= self._REPORT_PAGE_SIZE:
            return
        actual = self._report_page + 1
        pages = max(1, max_page + 1)
        tk.Button(
            self._report_pager_wrap, text="< Prev",
            command=self._report_prev_page,
            bg=C.get("sidebar", "#2d2d44"), fg=C.get("text", "#e8e8e8"),
            font=("Arial", 9), bd=0, relief="flat", cursor="hand2",
            state="normal" if self._report_page > 0 else "disabled",
        ).pack(side=tk.LEFT, padx=4)
        tk.Label(
            self._report_pager_wrap,
            text=f"Page {actual}/{pages} ({total} bills)",
            bg=C.get("bg", "#0f0f23"), fg=C.get("muted", "#94a3b8"),
            font=("Arial", 9),
        ).pack(side=tk.LEFT, padx=8)
        tk.Button(
            self._report_pager_wrap, text="Next >",
            command=self._report_next_page,
            bg=C.get("sidebar", "#2d2d44"), fg=C.get("text", "#e8e8e8"),
            font=("Arial", 9), bd=0, relief="flat", cursor="hand2",
            state="normal" if self._report_page < max_page else "disabled",
        ).pack(side=tk.LEFT, padx=4)

    def _load_to_bill(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select a bill row."); return
        r   = self._rmap.get(sel[0], {})
        raw = r.get("items_raw", "")
        if not raw:
            messagebox.showwarning("Empty", "No items in this bill."); return
        if not messagebox.askyesno("Load Bill",
                                    "Load this bill's items to current bill?"): return
        items = []
        for seg in raw.split("|"):
            parts = seg.split("~")
            if len(parts) == 4:
                mode, nm, pr, qty = parts
                try:
                    items.append({"mode": mode, "name": nm,
                                   "price": float(pr), "qty": int(qty)})
                except Exception as e:
                    app_log(f"[reports load_to_bill parse] {e}")
        try:
            bf = self.app.billing_frame
            bf.bill_items = items
            bf.name_ent.delete(0, tk.END)
            bf.name_ent.insert(0, r.get("name", ""))
            bf.phone_ent.delete(0, tk.END)
            bf.phone_ent.insert(0, r.get("phone", ""))
            bf._refresh_bill()
            self.app.switch_to("billing")
            messagebox.showinfo("Loaded",
                                 f"Loaded {len(items)} items to billing!")
        except Exception as e:
            app_log(f"[_load_to_bill] {e}")  # Fix R10i
            messagebox.showerror("Error", str(e))

    def _print_preview(self):
        """Print the previewed bill."""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select a bill to print."); return
        r = self._rmap.get(sel[0], {})
        bill_text = _build_bill_text(r)
        try:
            import win32print
            pn   = win32print.GetDefaultPrinter()
            hprn = win32print.OpenPrinter(pn)
            try:
                win32print.StartDocPrinter(hprn, 1, ("Salon Bill", None, "RAW"))
                win32print.StartPagePrinter(hprn)
                win32print.WritePrinter(hprn, bill_text.encode("utf-8"))
                win32print.EndPagePrinter(hprn)
                win32print.EndDocPrinter(hprn)
                messagebox.showinfo("Printed", f"Bill printed to: {pn}")
            finally:
                win32print.ClosePrinter(hprn)
        except ImportError as e:
            path = open_print_text_fallback(
                bill_text,
                f"{r.get('invoice', 'bill')}_print.txt",
            )
            messagebox.showwarning(
                "Print Fallback",
                "Direct printer module is missing, so Windows print fallback was used.\n\n"
                f"Detail: {e}\n\n"
                f"Print file: {path}")
        except Exception as e:
            messagebox.showerror("Print Error", f"Could not print:\n{e}")

    # Date filter shortcuts
    def _set_today(self):
        self.from_ent.delete(0, tk.END); self.from_ent.insert(0, today_display_str())
        self.to_ent.delete(0, tk.END);   self.to_ent.insert(0, today_display_str())
        self._load()

    def _set_month(self):
        self.from_ent.delete(0, tk.END)
        self.from_ent.insert(0, iso_to_display_date(date.today().strftime("%Y-%m-01")))
        self.to_ent.delete(0, tk.END); self.to_ent.insert(0, today_display_str())
        self._load()

    def _set_all(self):
        self.from_ent.delete(0, tk.END)
        self.to_ent.delete(0, tk.END)
        self._load()

    # Export actions
    def _export_csv(self):
        """Export current report list to CSV"""
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            title="Save CSV Report",
            defaultextension=".csv",
            initialfile="sales_report.csv",
            filetypes=[("CSV files","*.csv"),("All","*.*")])
        if not path: return
        try:
            export_current_tree_csv(path, self.tree)
            messagebox.showinfo("Exported", "CSV saved:\n" + path)
        except Exception as ex:
            messagebox.showerror("Export Error", str(ex))

    def _export_excel(self):
        """Phase 4: Use improved export engine with date range support."""
        try:
            from exports.export_engine import export_sales_report_excel
            result = run_search_export(
                export_sales_report_excel,
                self._current_report_filters(),
                "Excel saved",
                "No data found for the selected filters.",
            )
            self._handle_export_result(*result)
        except Exception as ex:
            messagebox.showerror("Export Error", str(ex))

    # Phase 4 export action wrappers
    def _export_pdf(self):
        """Export filtered sales report to PDF."""
        try:
            from exports.export_engine import export_sales_report_pdf
            result = run_search_export(
                export_sales_report_pdf,
                self._current_report_filters(),
                "PDF saved",
                "No data found for the selected date range.",
            )
            self._handle_export_result(*result)
        except Exception as ex:
            messagebox.showerror("Export Error", str(ex))

    def _export_gst(self):
        """Export GST summary for filtered date range."""
        try:
            from exports.export_engine import export_gst_summary_excel
            result = run_date_export(
                export_gst_summary_excel,
                self._current_report_filters(),
                "GST summary saved",
                "No data found for the selected date range.",
            )
            self._handle_export_result(*result)
        except Exception as ex:
            messagebox.showerror("Export Error", str(ex))

    def _current_report_filters(self):
        from_d = self.from_ent.get().strip() if hasattr(self, "from_ent") else ""
        to_d = self.to_ent.get().strip() if hasattr(self, "to_ent") else ""
        search = getattr(self, "search_var", None)
        search_val = search.get().strip() if search else ""
        return collect_report_filters(from_d, to_d, search_val)

    def _handle_export_result(self, path, success_prefix, empty_message, open_after=True):
        result = build_export_ui_result(
            path,
            success_prefix,
            empty_message,
            open_after=open_after,
        )
        messagebox.showinfo(result.title, result.message)
        if result.success and result.should_open and result.path:
            try:
                open_file_cross_platform(result.path)
            except Exception:
                pass
        return result.success

    def _selected_report_customer(self):
        sel = self.tree.selection() if hasattr(self, "tree") else ()
        if not sel:
            return "", ""
        return selected_customer_from_row(self._rmap.get(sel[0], {}) or {})

    def _open_export_center(self):
        win = tk.Toplevel(self)
        hide_while_building(win)
        win.configure(bg=C["bg"])
        popup_window(win, 520, 420, title="More Exports", resizable=False)

        tk.Label(win, text="Advanced Export Center",
                 font=("Arial", 15, "bold"),
                 bg=C["bg"], fg=C["accent"]).pack(pady=(14, 6))
        tk.Label(win,
                 text="Use the current report filters. Customer ledger exports the selected row customer when available.",
                 font=("Arial", 10),
                 bg=C["bg"], fg=C["muted"], wraplength=470, justify="center").pack(pady=(0, 12))

        body = tk.Frame(win, bg=C["bg"])
        body.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 12))
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)

        def add_btn(row, col, text, color, hover, cmd):
            ModernButton(body, text=text, command=cmd,
                         color=color, hover_color=hover,
                         width=210, height=38, radius=8,
                         font=("Arial", 10, "bold")
                         ).grid(row=row, column=col, padx=6, pady=6, sticky="ew")

        add_btn(0, 0, "Transactions Excel", C["blue"], "#154360", self._export_transactions)
        add_btn(0, 1, "Payment Summary", C["green"], "#1a7a45", self._export_payment_summary)
        add_btn(1, 0, "Profit Summary", C["purple"], "#6c3483", self._export_profit_summary)
        add_btn(1, 1, "Customer Ledger", C["teal"], C["blue"], self._export_customer_ledger)
        add_btn(2, 0, "Supplier Ledger", C["orange"], "#a06200", self._export_supplier_ledger)

        tk.Label(body,
                 text="Supplier ledger needs real purchase data. If the app has no purchase table yet, it will show an info message instead of creating a misleading file.",
                 font=("Arial", 9),
                 bg=C["bg"], fg=C["muted"], wraplength=450, justify="left").grid(row=3, column=0, columnspan=2, pady=(10, 4), sticky="w")

        ModernButton(win, text="Close", command=win.destroy,
                     color=C["sidebar"], hover_color=C["blue"],
                     width=100, height=34, radius=8,
                     font=("Arial", 10, "bold")).pack(pady=(0, 14))
        reveal_when_ready(win)

    def _export_transactions(self):
        try:
            from exports.export_engine import export_transactions_excel
            result = run_search_export(
                export_transactions_excel,
                self._current_report_filters(),
                "Transactions export saved",
                "No transactions found for the selected filters.",
            )
            self._handle_export_result(*result)
        except Exception as ex:
            messagebox.showerror("Export Error", str(ex))

    def _export_payment_summary(self):
        try:
            from exports.export_engine import export_payment_summary_excel
            result = run_date_export(
                export_payment_summary_excel,
                self._current_report_filters(),
                "Payment summary saved",
                "No payment data found for the selected date range.",
            )
            self._handle_export_result(*result)
        except Exception as ex:
            messagebox.showerror("Export Error", str(ex))

    def _export_profit_summary(self):
        try:
            from exports.export_engine import export_profit_summary_excel
            result = run_date_export(
                export_profit_summary_excel,
                self._current_report_filters(),
                "Profit summary saved",
                "No service revenue found for the selected date range.",
            )
            self._handle_export_result(*result)
        except Exception as ex:
            messagebox.showerror("Export Error", str(ex))

    def _export_customer_ledger(self):
        try:
            from exports.export_engine import export_customer_ledger_excel
            phone, name = self._selected_report_customer()
            result = run_customer_ledger_export(
                export_customer_ledger_excel,
                self._current_report_filters(),
                phone,
                name,
                "No customer ledger data found for the selected filters.",
            )
            self._handle_export_result(*result)
        except Exception as ex:
            messagebox.showerror("Export Error", str(ex))

    def _export_supplier_ledger(self):
        try:
            from exports.export_engine import export_supplier_ledger_excel
            result = run_date_export(
                export_supplier_ledger_excel,
                self._current_report_filters(),
                "Supplier ledger saved",
                "Supplier purchase data is not configured in this build yet, so no supplier ledger could be generated."
            )
            self._handle_export_result(*result)
        except Exception as ex:
            messagebox.showerror("Export Error", str(ex))

    def _build_service_tab(self):
        f = self.tab_service
        ctrl_wrap = tk.Frame(f, bg=C["card"], pady=8)
        ctrl_wrap.pack(fill=tk.X, padx=10, pady=(2, 8))
        ctrl = tk.Frame(ctrl_wrap, bg=C["card"])
        ctrl.pack(fill=tk.X, padx=14)

        tk.Label(ctrl, text="From:", bg=C["card"],
                 fg=C["muted"], font=("Arial", 10)).pack(side=tk.LEFT, padx=(0,4))
        self.sr_from = tk.Entry(ctrl, font=("Arial", 10),
                                 bg=C["input"], fg=C["text"],
                                 bd=0, width=13, insertbackground=C["accent"])
        self.sr_from.pack(side=tk.LEFT, ipady=5, padx=(0,8))
        self.sr_from.insert(0, iso_to_display_date(date.today().strftime("%Y-%m-01")))
        attach_date_mask(self.sr_from)

        tk.Label(ctrl, text="To:", bg=C["card"],
                 fg=C["muted"], font=("Arial", 10)).pack(side=tk.LEFT, padx=(0,4))
        self.sr_to = tk.Entry(ctrl, font=("Arial", 10),
                               bg=C["input"], fg=C["text"],
                               bd=0, width=13, insertbackground=C["accent"])
        self.sr_to.pack(side=tk.LEFT, ipady=5, padx=(0,8))
        self.sr_to.insert(0, today_display_str())
        attach_date_mask(self.sr_to)

        ModernButton(ctrl, text="Generate Report",
                     command=lambda: (self._reset_service_pagination(), self._gen_service_report()),
                     color=C["teal"], hover_color=C["blue"],
                     width=110, height=30, radius=8,
                     font=("Arial",10,"bold"),
                     ).pack(side=tk.LEFT)

        # Pane: left=services, right=products
        pane = tk.PanedWindow(f, orient=tk.HORIZONTAL,
                               sashwidth=6, bg=C["bg"])
        pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0,8))

        # Left: Services
        lf = tk.Frame(pane, bg=C["bg"])
        pane.add(lf, minsize=360)
        tk.Label(lf, text="Service-wise Revenue",
                 bg=C["bg"], fg=C["accent"],
                 font=("Arial", 11, "bold")).pack(anchor="w", pady=4)
        cols = ("Service","Count","Revenue","Avg")
        self.sr_tree = ttk.Treeview(lf, columns=cols,
                                     show="headings", height=18)
        for col,w in zip(cols,[200,60,100,90]):
            self.sr_tree.heading(col, text=col,
                                  command=lambda c=col: self._sort_sr(c))
            self.sr_tree.column(col, width=w)
        apply_treeview_column_alignment(self.sr_tree)
        vsb = ttk.Scrollbar(lf, orient="vertical", command=self.sr_tree.yview)
        self.sr_tree.configure(yscrollcommand=vsb.set)
        self.sr_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        vsb.pack(side=tk.LEFT, fill=tk.Y)

        # Right: Products
        rf = tk.Frame(pane, bg=C["bg"])
        pane.add(rf, minsize=320)
        tk.Label(rf, text="Product-wise Sales",
                 bg=C["bg"], fg=C["accent"],
                 font=("Arial", 11, "bold")).pack(anchor="w", pady=4)
        cols2 = ("Product","Count","Revenue")
        self.pr_tree = ttk.Treeview(rf, columns=cols2,
                                     show="headings", height=18)
        for col,w in zip(cols2,[200,60,100]):
            self.pr_tree.heading(col, text=col)
            self.pr_tree.column(col, width=w)
        apply_treeview_column_alignment(self.pr_tree)
        vsb2 = ttk.Scrollbar(rf, orient="vertical", command=self.pr_tree.yview)
        self.pr_tree.configure(yscrollcommand=vsb2.set)
        self.pr_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        vsb2.pack(side=tk.LEFT, fill=tk.Y)

        self._sr_sort_col = "Revenue"
        self._sr_sort_rev = True

        # Pagination for service report
        self._sr_page = 0
        self._SR_PAGE_SIZE = 80
        self._sr_display_rows = []
        self._pr_page = 0
        self._pr_display_rows = []

        # Pager containers
        self._sr_pager_wrap = tk.Frame(lf, bg=C["bg"])
        self._sr_pager_wrap.pack(fill=tk.X)
        self._pr_pager_wrap = tk.Frame(rf, bg=C["bg"])
        self._pr_pager_wrap.pack(fill=tk.X)


    def _sort_sr(self, col):
        self._sr_sort_rev = not self._sr_sort_rev if self._sr_sort_col == col else True
        self._sr_sort_col = col
        self._gen_service_report()

    def _gen_service_report(self):
        """Refresh the service report and log failures without closing Reports."""
        try:
            self._gen_service_report_inner()
        except Exception as e:
            app_log(f"[_gen_service_report] {e}")

    def _gen_service_report_inner(self):
        for t in (self.sr_tree, self.pr_tree):
            for i in t.get_children(): t.delete(i)

        fd_text = self.sr_from.get().strip()
        td_text = self.sr_to.get().strip()
        fd = display_to_iso_date(fd_text) if validate_display_date(fd_text) else fd_text
        td = display_to_iso_date(td_text) if validate_display_date(td_text) else td_text

        rows = _read_report(fd, td)
        report = build_service_report_rows(
            rows,
            sort_col=self._sr_sort_col,
            sort_reverse=self._sr_sort_rev,
        )
        self._sr_display_rows = list(report.services)
        self._pr_display_rows = list(report.products)

        # Clamp and paginate services
        sr_page = paginate_service_report_rows(
            self._sr_display_rows,
            self._sr_page,
            self._SR_PAGE_SIZE,
        )
        self._sr_page = sr_page.page
        for row in sr_page.rows:
            self.sr_tree.insert("", tk.END, values=service_report_tree_values(row, fmt_currency))
        self._update_sr_pagination(sr_page.total, sr_page.max_page)

        # Clamp and paginate products
        pr_page = paginate_service_report_rows(
            self._pr_display_rows,
            self._pr_page,
            self._SR_PAGE_SIZE,
        )
        self._pr_page = pr_page.page
        for row in pr_page.rows:
            self.pr_tree.insert("", tk.END, values=product_report_tree_values(row, fmt_currency))
        self._update_pr_pagination(pr_page.total, pr_page.max_page)

    # Service report pagination helpers

    def _reset_service_pagination(self):
        self._sr_page = 0
        self._pr_page = 0

    def _sr_prev_page(self):
        if self._sr_page > 0:
            self._sr_page -= 1
            self._gen_service_report()

    def _sr_next_page(self):
        total = len(self._sr_display_rows)
        max_page = max_service_report_page(total, self._SR_PAGE_SIZE)
        if self._sr_page < max_page:
            self._sr_page += 1
            self._gen_service_report()

    def _update_sr_pagination(self, total, max_page):
        for w in self._sr_pager_wrap.winfo_children():
            w.destroy()
        if total <= self._SR_PAGE_SIZE:
            self._sr_pager_wrap.pack_forget()
            return
        self._sr_pager_wrap.pack(fill=tk.X, pady=(4, 0))
        actual = self._sr_page + 1
        pages = max(1, max_page + 1)
        tk.Button(
            self._sr_pager_wrap, text="< Prev",
            command=self._sr_prev_page,
            bg=C.get("sidebar", "#2d2d44"), fg=C.get("text", "#e8e8e8"),
            font=("Arial", 9), bd=0, relief="flat", cursor="hand2",
            state="normal" if self._sr_page > 0 else "disabled",
        ).pack(side=tk.LEFT, padx=4)
        tk.Label(
            self._sr_pager_wrap,
            text=f"Page {actual}/{pages} ({total})",
            bg=C.get("bg", "#0f0f23"), fg=C.get("muted", "#94a3b8"),
            font=("Arial", 9),
        ).pack(side=tk.LEFT, padx=8)
        tk.Button(
            self._sr_pager_wrap, text="Next >",
            command=self._sr_next_page,
            bg=C.get("sidebar", "#2d2d44"), fg=C.get("text", "#e8e8e8"),
            font=("Arial", 9), bd=0, relief="flat", cursor="hand2",
            state="normal" if self._sr_page < max_page else "disabled",
        ).pack(side=tk.LEFT, padx=4)

    def _pr_prev_page(self):
        if self._pr_page > 0:
            self._pr_page -= 1
            self._gen_service_report()

    def _pr_next_page(self):
        total = len(self._pr_display_rows)
        max_page = max_service_report_page(total, self._SR_PAGE_SIZE)
        if self._pr_page < max_page:
            self._pr_page += 1
            self._gen_service_report()

    def _update_pr_pagination(self, total, max_page):
        for w in self._pr_pager_wrap.winfo_children():
            w.destroy()
        if total <= self._SR_PAGE_SIZE:
            self._pr_pager_wrap.pack_forget()
            return
        self._pr_pager_wrap.pack(fill=tk.X, pady=(4, 0))
        actual = self._pr_page + 1
        pages = max(1, max_page + 1)
        tk.Button(
            self._pr_pager_wrap, text="< Prev",
            command=self._pr_prev_page,
            bg=C.get("sidebar", "#2d2d44"), fg=C.get("text", "#e8e8e8"),
            font=("Arial", 9), bd=0, relief="flat", cursor="hand2",
            state="normal" if self._pr_page > 0 else "disabled",
        ).pack(side=tk.LEFT, padx=4)
        tk.Label(
            self._pr_pager_wrap,
            text=f"Page {actual}/{pages} ({total})",
            bg=C.get("bg", "#0f0f23"), fg=C.get("muted", "#94a3b8"),
            font=("Arial", 9),
        ).pack(side=tk.LEFT, padx=8)
        tk.Button(
            self._pr_pager_wrap, text="Next >",
            command=self._pr_next_page,
            bg=C.get("sidebar", "#2d2d44"), fg=C.get("text", "#e8e8e8"),
            font=("Arial", 9), bd=0, relief="flat", cursor="hand2",
            state="normal" if self._pr_page < max_page else "disabled",
        ).pack(side=tk.LEFT, padx=4)

    def _is_admin_or_owner(self) -> bool:
        role = str(self.app.current_user.get("role", "")).strip().lower()
        return is_admin_or_manager(role)

    def _show_deleted_bills(self):
        """Open a unified dialog showing deleted bills from DB soft-delete and PDF trash."""
        from soft_delete import (
            restore_bill,
            permanent_delete_bill,
            log_restore_audit,
            log_permanent_delete_audit,
        )
        from utils import TRASH_DIR, BILLS_DIR
        import shutil

        restore_icon = get_action_icon("restore")
        clear_icon = get_action_icon("delete")
        admin_mgr = self._is_admin_or_owner()

        deleted = self._get_deleted_bill_entries()
        if not deleted:
            messagebox.showinfo("Trash", "No deleted bills found.")
            return

        win = tk.Toplevel(self)
        hide_while_building(win)
        win.title("Deleted Bills")
        popup_window(win, 760, 500)
        win.configure(bg=C["bg"])
        win.grab_set()
        win.protocol("WM_DELETE_WINDOW", lambda: (win.grab_release(), win.destroy()))

        tk.Label(win, text="Deleted Bills",
                 font=("Arial",13,"bold"),
                 bg=C["bg"], fg=C["accent"]).pack(pady=(14,8))
        tk.Label(win,
                 text="Restore or permanently delete bills from one place.",
                 font=("Arial",10),
                 bg=C["bg"], fg=C["muted"]).pack(pady=(0,8))
        deleted_bill_count_lbl = tk.Label(
            win,
            text=f"{len(deleted)} bill(s) in deleted history",
            font=("Arial", 10),
            bg=C["bg"], fg=C["muted"]
        )
        deleted_bill_count_lbl.pack(pady=(0, 8))
        role_note = deleted_bills_role_note(admin_mgr)
        tk.Label(win, text=role_note, font=("Arial",10),
                 bg=C["bg"], fg=C["muted"]).pack(pady=(0,8))

        cols = ("Invoice No", "Customer", "Deleted Date", "Deleted By")
        tree = ttk.Treeview(win, columns=cols, show="headings", height=12)
        for col, w in zip(cols, [110, 220, 170, 150]):
            tree.heading(col, text=col)
            tree.column(col, width=w)
        apply_treeview_column_alignment(tree)

        vsb = ttk.Scrollbar(win, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(fill=tk.BOTH, expand=True, padx=14)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        deleted_map: dict[str, dict] = {}

        def refresh_deleted_tree():
            deleted_map.clear()
            for iid in tree.get_children():
                tree.delete(iid)
            entries = self._get_deleted_bill_entries()
            deleted_bill_count_lbl.config(text=f"{len(entries)} bill(s) in deleted history")
            for entry in entries:
                iid = tree.insert("", tk.END, values=deleted_bill_tree_values(entry))
                deleted_map[iid] = entry

        refresh_deleted_tree()

        def _restore():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Select", "Select a bill to restore.")
                return
            entry = deleted_map.get(sel[0], {})
            inv = entry.get("invoice_no", "")
            if not messagebox.askyesno(
                    "Restore Bill",
                    f"Restore invoice {inv}?\nIt will appear in reports and saved bills again."):
                return
            user = self.app.current_user.get("username", "") if hasattr(self.app, "current_user") else ""
            restored_any = False
            db_restored = False
            if entry.get("has_db_record"):
                db_restored = bool(restore_bill(inv, restored_by=user))
                restored_any = restored_any or db_restored
            trash_file = entry.get("trash_file", "")
            if trash_file and os.path.exists(trash_file):
                os.makedirs(BILLS_DIR, exist_ok=True)
                shutil.move(trash_file, os.path.join(BILLS_DIR, entry.get("trash_name") or os.path.basename(trash_file)))
                restored_any = True
                if not db_restored and inv:
                    log_restore_audit("bill", inv, user)
            if restored_any:
                invalidate_report_cache()
                self._load()
                self._load_bills()
                refresh_deleted_tree()
                if not tree.get_children():
                    win.grab_release()
                    win.destroy()
                messagebox.showinfo("Restored", f"Invoice {inv} restored!")
            else:
                messagebox.showinfo("Info", f"Could not restore {inv}.")

        def _permanent_delete():
            if not admin_mgr:
                messagebox.showwarning("Access Denied",
                    "Only owners/managers can permanently delete bills.")
                return
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Select", "Select a bill to delete.")
                return
            entry = deleted_map.get(sel[0], {})
            inv = entry.get("invoice_no", "")
            if not messagebox.askyesno(
                    "Permanent Delete",
                    f"Permanently delete invoice {inv}?\nThis CANNOT be undone."):
                return
            user = self.app.current_user.get("username", "") if hasattr(self.app, "current_user") else ""
            deleted_any = False
            db_deleted = False
            if entry.get("has_db_record"):
                db_deleted = bool(permanent_delete_bill(inv, deleted_by=user))
                deleted_any = deleted_any or db_deleted
            trash_file = entry.get("trash_file", "")
            if trash_file and os.path.exists(trash_file):
                os.remove(trash_file)
                deleted_any = True
                if not db_deleted and inv:
                    log_permanent_delete_audit("bill", inv, user)
            if deleted_any:
                invalidate_report_cache()
                self._load()
                self._load_bills()
                refresh_deleted_tree()
                if not tree.get_children():
                    win.grab_release()
                    win.destroy()
                messagebox.showinfo("Deleted", f"Invoice {inv} permanently deleted.")
            else:
                messagebox.showinfo("Info", f"Could not delete {inv}.")

        bb = tk.Frame(win, bg=C["bg"])
        bb.pack(fill=tk.X, padx=14, pady=8)
        ModernButton(bb, text="Restore Selected", image=restore_icon, compound="left",
                     command=_restore,
                     color=C["teal"], hover_color=C["blue"],
                     width=154, height=34, radius=8,
                     font=("Arial",10,"bold"),
                     ).pack(side=tk.LEFT, padx=(0,8))
        if admin_mgr:
            ModernButton(bb, text="Permanent Delete", image=clear_icon, compound="left",
                         command=_permanent_delete,
                         color=C["red"], hover_color="#c0392b",
                         width=154, height=34, radius=8,
                         font=("Arial",10,"bold"),
                         ).pack(side=tk.LEFT)
        ModernButton(bb, text="Close",
                     command=lambda: (win.grab_release(), win.destroy()),
                     color=C["sidebar"], hover_color=C["blue"],
                     width=110, height=34, radius=8,
                     font=("Arial",10,"bold"),
                     ).pack(side=tk.RIGHT)
        tree.bind("<Return>", lambda e: _restore())
        tree.bind("<Double-Button-1>", lambda e: _restore())
        tree.bind("<Escape>", lambda e: (win.grab_release(), win.destroy(), "break")[-1])
        reveal_when_ready(win)
    def refresh(self):
        """Reload report data and log failures without closing Reports."""
        try:
            self._load()
        except Exception as e:
            app_log(f"[reports refresh] {e}")

# v5 report reader override --------------------------------------------------
def _read_report(from_d="", to_d="", search="") -> list:
    return read_report_rows(from_d, to_d, search)
