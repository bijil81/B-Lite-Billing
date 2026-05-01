"""Purchase history dialog for vendor workflow."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from ui_theme import ModernButton
from utils import C, fmt_currency, popup_window, app_log
from src.blite_v6.app.window_lifecycle import hide_while_building, reveal_when_ready
from src.blite_v6.inventory_grocery.cost_tracker import list_purchase_invoices, list_purchase_items
from src.blite_v6.inventory_grocery.vendor_service import VendorService


def open_purchase_history_dialog(parent, *, vendor_id: int | None = None, vendor_name: str = ""):
    svc = VendorService()
    win = tk.Toplevel(parent)
    hide_while_building(win)
    win.title("Purchase History")
    popup_window(win, 1280, 800)
    win.configure(bg=C["bg"])
    try:
        win.minsize(1080, 700)
        win.resizable(True, True)
    except Exception:
        pass

    def _close(event=None):
        try:
            win.destroy()
        except Exception:
            pass

    win.protocol("WM_DELETE_WINDOW", _close)
    win.bind("<Escape>", _close)

    hdr = tk.Frame(win, bg=C["sidebar"], padx=20, pady=10)
    hdr.pack(fill=tk.X)
    tk.Label(hdr, text="Purchase History", bg=C["sidebar"], fg=C["text"], font=("Arial", 14, "bold")).pack(anchor="w")
    tk.Label(
        hdr,
        text="Review purchase invoices, item lines, and vendor spend history.",
        bg=C["sidebar"],
        fg=C["muted"],
        font=("Arial", 10),
    ).pack(anchor="w", pady=(2, 0))

    body = tk.Frame(win, bg=C["bg"], padx=16, pady=12)
    body.pack(fill=tk.BOTH, expand=True)

    top = tk.Frame(body, bg=C["bg"])
    top.pack(fill=tk.X)
    tk.Label(top, text="Vendor:", bg=C["bg"], fg=C["muted"], font=("Arial", 10)).pack(side=tk.LEFT)
    vendor_var = tk.StringVar(value=vendor_name or "All Vendors")
    vendor_cb = ttk.Combobox(top, textvariable=vendor_var, font=("Arial", 11), width=30, state="readonly")
    vendor_cb.pack(side=tk.LEFT, padx=(8, 8), ipady=3)
    tk.Label(top, text="Search Invoice:", bg=C["bg"], fg=C["muted"], font=("Arial", 10)).pack(side=tk.LEFT, padx=(8, 0))
    search_var = tk.StringVar()
    search_ent = tk.Entry(top, textvariable=search_var, bg=C["input"], fg=C["text"], bd=0, font=("Arial", 11))
    search_ent.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0), ipady=4)

    columns = ("Invoice", "Date", "Vendor", "Gross", "GST", "Net", "Items")
    inv_wrap = tk.Frame(body, bg=C["bg"])
    inv_wrap.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
    invoice_tree = ttk.Treeview(inv_wrap, columns=columns, show="headings", height=12)
    for col in columns:
        invoice_tree.heading(col, text=col)
    invoice_tree.column("Invoice", width=130, minwidth=100)
    invoice_tree.column("Date", width=110, minwidth=90)
    invoice_tree.column("Vendor", width=210, minwidth=140)
    invoice_tree.column("Gross", width=100, minwidth=80, anchor="e")
    invoice_tree.column("GST", width=90, minwidth=70, anchor="e")
    invoice_tree.column("Net", width=100, minwidth=80, anchor="e")
    invoice_tree.column("Items", width=70, minwidth=50, anchor="center")
    invoice_tree.pack(fill=tk.BOTH, expand=True)
    inv_scroll = ttk.Scrollbar(inv_wrap, orient="vertical", command=invoice_tree.yview)
    inv_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    invoice_tree.configure(yscrollcommand=inv_scroll.set)

    items_lbl = tk.Label(body, text="Selected Invoice Items", bg=C["bg"], fg=C["muted"], font=("Arial", 10, "bold"))
    items_lbl.pack(anchor="w", pady=(10, 4))

    item_cols = ("Item", "Qty", "Unit", "Cost", "GST", "Net", "Batch", "Expiry")
    item_wrap = tk.Frame(body, bg=C["bg"])
    item_wrap.pack(fill=tk.BOTH, expand=True)
    item_tree = ttk.Treeview(item_wrap, columns=item_cols, show="headings", height=10)
    for col in item_cols:
        item_tree.heading(col, text=col)
    item_tree.column("Item", width=240, minwidth=140)
    item_tree.column("Qty", width=70, minwidth=50, anchor="e")
    item_tree.column("Unit", width=70, minwidth=50, anchor="center")
    item_tree.column("Cost", width=100, minwidth=80, anchor="e")
    item_tree.column("GST", width=80, minwidth=60, anchor="e")
    item_tree.column("Net", width=100, minwidth=80, anchor="e")
    item_tree.column("Batch", width=110, minwidth=80)
    item_tree.column("Expiry", width=100, minwidth=80)
    item_tree.pack(fill=tk.BOTH, expand=True)
    item_scroll = ttk.Scrollbar(item_wrap, orient="vertical", command=item_tree.yview)
    item_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    item_tree.configure(yscrollcommand=item_scroll.set)

    footer = tk.Frame(body, bg=C["bg"])
    footer.pack(fill=tk.X, pady=(12, 0))

    current_invoices: dict[str, dict] = {}
    vendor_rows: list[dict] = []

    def _refresh_vendor_list():
        try:
            rows = svc.list_vendors(active_only=False)
        except Exception as exc:
            app_log(f"[purchase history vendors] {exc}")
            rows = []
        vendor_rows[:] = rows
        labels = ["All Vendors"] + [str(row.get("name", "")).strip() for row in rows if str(row.get("name", "")).strip()]
        vendor_cb["values"] = labels
        if vendor_name:
            vendor_var.set(vendor_name)

    def _selected_vendor_id() -> int | None:
        selected = vendor_var.get().strip()
        if not selected or selected == "All Vendors":
            return None
        for row in vendor_rows:
            if str(row.get("name", "")).strip().lower() == selected.lower():
                return int(row.get("id") or 0)
        return None

    def _refresh_invoices():
        for item_id in invoice_tree.get_children():
            invoice_tree.delete(item_id)
        current_invoices.clear()
        q = search_var.get().strip().lower()
        try:
            rows = list_purchase_invoices(_selected_vendor_id(), limit=400)
        except Exception as exc:
            app_log(f"[purchase history invoices] {exc}")
            rows = []
        for row in rows:
            invoice_no = str(row.get("invoice_no", "")).strip()
            vendor_text = str(row.get("vendor_name", "")).strip()
            if q and q not in invoice_no.lower() and q not in vendor_text.lower():
                continue
            item_id = invoice_tree.insert(
                "",
                tk.END,
                values=(
                    invoice_no,
                    row.get("invoice_date", ""),
                    vendor_text,
                    fmt_currency(row.get("gross_total", 0)),
                    fmt_currency(row.get("tax_total", 0)),
                    fmt_currency(row.get("net_total", 0)),
                    int(row.get("item_count", 0) or 0),
                ),
            )
            current_invoices[item_id] = row

    def _load_items(event=None):
        for item_id in item_tree.get_children():
            item_tree.delete(item_id)
        sel = invoice_tree.selection()
        if not sel:
            return
        row = current_invoices.get(sel[0], {})
        invoice_id = int(row.get("id") or 0)
        if not invoice_id:
            return
        try:
            items = list_purchase_items(invoice_id)
        except Exception as exc:
            app_log(f"[purchase history items] {exc}")
            items = []
        for item in items:
            item_tree.insert(
                "",
                tk.END,
                values=(
                    item.get("item_name", ""),
                    item.get("qty", ""),
                    item.get("unit", ""),
                    fmt_currency(item.get("cost_price", 0)),
                    fmt_currency(item.get("gst_rate", 0)),
                    fmt_currency(item.get("line_net", 0)),
                    item.get("batch_no", ""),
                    item.get("expiry_date", ""),
                ),
            )

    def _open_vendor_master():
        from src.blite_v6.inventory_grocery.vendor_master_dialog import open_vendor_master_dialog

        open_vendor_master_dialog(parent, on_change=lambda: (_refresh_vendor_list(), _refresh_invoices()))

    invoice_tree.bind("<<TreeviewSelect>>", _load_items)
    invoice_tree.bind("<Double-1>", _load_items)

    ModernButton(footer, text="Vendor Master", command=_open_vendor_master, color=C["purple"], hover_color="#6c3483", width=140, height=34, radius=8, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 6))
    ModernButton(footer, text="Refresh", command=lambda: (_refresh_vendor_list(), _refresh_invoices()), color=C["teal"], hover_color=C["blue"], width=100, height=34, radius=8, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 6))
    ModernButton(footer, text="Close", command=_close, color=C["sidebar"], hover_color=C["blue"], width=90, height=34, radius=8, font=("Arial", 10, "bold")).pack(side=tk.LEFT)

    vendor_cb.bind("<<ComboboxSelected>>", lambda e: _refresh_invoices())
    search_var.trace_add("write", lambda *_: _refresh_invoices())

    _refresh_vendor_list()
    _refresh_invoices()
    win.after(0, lambda: search_ent.focus_set())
    reveal_when_ready(win)
