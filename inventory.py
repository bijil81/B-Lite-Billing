"""
inventory.py  —  BOBY'S Salon : Inventory — grid + list view, add/edit
FIXES:
  - Fix R5a: deduct_inventory_for_sale() try/except — crash prevention
  - Fix R5b: _load() try/except wrapper — crash prevention
  - Fix R5c: _quick_update() try/except — error shown to user
  - Fix R5d: _delete() try/except — error shown to user
  - Fix R5e: _import_products() try/except — error shown to user
  - Fix R5f: _import_from_products() try/except — error shown to user
"""
import tkinter as tk
from tkinter import ttk, messagebox
import time
from adapters.product_catalog_adapter import (
    create_product_with_variants_v5,
    use_v5_product_variants_db,
)
from utils import (C, load_json, save_json, safe_float, safe_int,
                   fmt_currency, now_str, today_str, F_INVENTORY, F_SERVICES,
                   popup_window, app_log)
from barcode_utils import generate_barcode_from_product_code
from ui_theme import ModernButton
from ui_theme import apply_treeview_column_alignment, ModernButton
from ui_responsive import make_scrollable
from ui_utils import make_searchable_combobox
from icon_system import get_action_icon
from services_v5.inventory_service import InventoryService
from services_v5.purchase_service import PurchaseService
from soft_delete import get_deleted_products, restore_product, permanent_delete_product
from src.blite_v6.app.window_lifecycle import hide_while_building, reveal_when_ready
from src.blite_v6.inventory_grocery.gst_autofill import resolve_inventory_gst_rate
from src.blite_v6.inventory_grocery.product_form import (
    FORM_UNITS,
    build_inventory_product_form_payload,
    default_sale_unit,
    should_show_grocery_controls,
)
from src.blite_v6.inventory_grocery.product_import_dialog import open_product_import_preview_dialog
from src.blite_v6.inventory_grocery.purchase_form import (
    build_purchase_invoice_payload,
    purchase_item_defaults,
)
from src.blite_v6.inventory_grocery.purchase_history_dialog import open_purchase_history_dialog
from src.blite_v6.inventory_grocery.vendor_master_dialog import open_vendor_master_dialog


def _format_stock_qty(qty):
    try:
        value = float(qty)
    except Exception:
        return str(qty or 0)
    if value.is_integer():
        return str(int(value))
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _is_light_theme():
    value = (C.get("bg") or "#000000").lstrip("#")
    if len(value) != 6:
        return False
    r, g, b = (int(value[i:i+2], 16) for i in (0, 2, 4))
    luminance = (0.299 * r) + (0.587 * g) + (0.114 * b)
    return luminance >= 180


def deduct_inventory_for_sale(bill_items: list):
    """
    Auto-deduct product quantities when a bill is saved.
    Only deducts items with mode='products'.
    Called from billing._save_report() after every bill save.
    """
    try:
        from repositories.product_variants_repo import ProductVariantsRepository
        from salon_settings import get_settings

        products = [it for it in bill_items if it.get("mode") == "products"]
        if not products:
            return
        inv = get_inventory()
        changed = False
        use_v5 = bool(get_settings().get("use_v5_product_variants_db", False))
        variants_repo = ProductVariantsRepository() if use_v5 else None
        for it in products:
            name = it.get("inventory_item_name", it.get("name", "")).strip()
            qty  = safe_float(it.get("qty", 1), 1.0)
            if use_v5 and variants_repo and it.get("variant_id"):
                try:
                    variants_repo.add_stock_movement({
                        "variant_id": int(it.get("variant_id")),
                        "movement_type": "sale",
                        "qty_delta": -qty,
                        "reference_type": "bill",
                        "reference_id": "",
                        "note": it.get("name", ""),
                    })
                except Exception as ve:
                    app_log(f"[deduct_inventory_for_sale v5] {ve}")
            # Try exact match first, then case-insensitive
            if name in inv:
                inv[name]["qty"] = max(0.0, safe_float(inv[name].get("qty", 0), 0.0) - qty)
                changed = True
            else:
                for key in inv:
                    if key.lower() == name.lower():
                        inv[key]["qty"] = max(0.0, safe_float(inv[key].get("qty", 0), 0.0) - qty)
                        changed = True
                        break
        if changed:
            save_inventory(inv)
    except Exception as e:
        app_log(f"[deduct_inventory_for_sale] {e}")


class InventoryFrame(tk.Frame):

    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app      = app
        self._view    = "table"   # table | card
        self._sort_col = "Item"
        self._sort_rev = False
        self._inv_page = 0
        self._INV_PAGE_SIZE = 200
        self._inv_total = 0
        self._inv_max_page = 0
        self._last_search = ""
        self._last_cat = "All"
        self._last_load_ts = 0.0
        self._force_next_refresh = False
        self._build()

    def _build(self):
        # Header (UI v3)
        hdr = tk.Frame(self, bg=C["card"], pady=10)
        hdr.pack(fill=tk.X)
        left_f = tk.Frame(hdr, bg=C["card"])
        left_f.pack(side=tk.LEFT, padx=20)
        tk.Label(left_f, text="Inventory / Stock",
                 font=("Arial",15,"bold"),
                 bg=C["card"], fg=C["text"]).pack(anchor="w")
        tk.Label(left_f, text="Track products, stock levels & alerts",
                 font=("Arial",10), bg=C["card"], fg=C["muted"]).pack(anchor="w")
        add_icon = get_action_icon("add")
        filter_icon = get_action_icon("filter")
        edit_icon = get_action_icon("edit")
        delete_icon = get_action_icon("delete")
        import_icon = get_action_icon("import_excel") or get_action_icon("browse")

        ModernButton(hdr, text="Add Item",
                     image=add_icon, compound="left",
                     command=self._add_dialog,
                     color=C["teal"], hover_color=C["blue"],
                     width=132, height=36, radius=8,
                     font=("Arial",10,"bold"),
                     ).pack(side=tk.RIGHT, padx=10, pady=6)
        ModernButton(hdr, text="Import",
                     image=import_icon, compound="left",
                     command=self._import_dialog,
                     color=C["orange"], hover_color=C["blue"],
                     width=118, height=36, radius=8,
                     font=("Arial",10,"bold"),
                     ).pack(side=tk.RIGHT, padx=(0, 10), pady=6)
        ModernButton(hdr, text="Purchase Bill",
                     image=add_icon, compound="left",
                     command=self._purchase_dialog,
                     color=C["purple"], hover_color=C["blue"],
                     width=150, height=36, radius=8,
                     font=("Arial",10,"bold"),
                     ).pack(side=tk.RIGHT, padx=(0, 0), pady=6)
        tk.Frame(self, bg=C["teal"], height=2).pack(fill=tk.X)

        top_band = tk.Frame(self, bg=C["bg"])
        top_band.pack(fill=tk.X, padx=15, pady=(10, 8))

        intro = tk.Frame(top_band, bg=C["card"], padx=16, pady=10)
        intro.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(intro, text="Inventory Workspace",
                 font=("Arial", 13, "bold"),
                 bg=C["card"], fg=C["text"]).pack(anchor="w")
        tk.Label(intro,
                 text="Monitor stock, search products fast, and update quantities without leaving the grid.",
                 font=("Arial", 10),
                 bg=C["card"], fg=C["muted"]).pack(anchor="w", pady=(3, 0))

        # Summary cards
        self.cards_f = tk.Frame(top_band, bg=C["bg"])
        self.cards_f.pack(side=tk.LEFT, padx=(12, 0))

        # Toolbar
        tb_outer = tk.Frame(self, bg=C["card"])
        tb_outer.pack(fill=tk.X, padx=15, pady=(0, 8))
        tb_head = tk.Frame(tb_outer, bg=C["sidebar"], padx=12, pady=6)
        tb_head.pack(fill=tk.X)
        tk.Label(tb_head, text="Search & Filter",
                 bg=C["sidebar"], fg=C["text"],
                 font=("Arial", 11, "bold")).pack(side=tk.LEFT)
        tk.Label(tb_head, text="Find items by name and narrow by category",
                 bg=C["sidebar"], fg=C["muted"],
                 font=("Arial", 9)).pack(side=tk.RIGHT)
        tk.Frame(tb_outer, bg=C["teal"], height=2).pack(fill=tk.X)
        tb = tk.Frame(tb_outer, bg=C["card"], pady=10, padx=12)
        tb.pack(fill=tk.X)

        # Search
        tk.Label(tb, text="Search:", bg=C["card"], fg=C["muted"]).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        se = tk.Entry(tb, textvariable=self.search_var,
                      font=("Arial",12), bg=C["input"],
                      fg=C["text"], bd=0, width=22,
                      insertbackground=C["accent"])
        se.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, padx=(4,10))
        self.search_var.trace("w", lambda *a: (self._reset_inv_page(), self._load()))

        # Category filter
        tk.Label(tb, text="Category:", bg=C["card"],
                 fg=C["muted"], font=("Arial",11)).pack(side=tk.LEFT, padx=(0,4))
        self.cat_filter = tk.StringVar(value="All")
        self.cat_cb = ttk.Combobox(tb, textvariable=self.cat_filter,
                                    state="readonly", font=("Arial",11), width=16)
        self.cat_cb.pack(side=tk.LEFT, padx=(0,10))
        self.cat_cb["values"] = ["All"]
        self.cat_cb.bind("<<ComboboxSelected>>", lambda e: (self._reset_inv_page(), self._load()))

        ModernButton(tb, text="Low Stock",
                     image=filter_icon, compound="left",
                     command=self._show_low,
                     color=C["orange"], hover_color="#d35400",
                     width=108, height=30, radius=8,
                     font=("Arial",10,"bold"),
                     ).pack(side=tk.LEFT, padx=(0,6))

        ModernButton(tb, text="All Items",
                     image=filter_icon, compound="left",
                     command=self._show_all,
                     color=C["blue"], hover_color="#154360",
                     width=108, height=30, radius=8,
                     font=("Arial",10,"bold"),
                     ).pack(side=tk.LEFT)

        ModernButton(tb, text="Clear",
                     image=get_action_icon("clear"), compound="left",
                     command=lambda: (self.search_var.set(""), self.cat_filter.set("All"), self._load()),
                     color=C["sidebar"], hover_color=C["blue"],
                     width=92, height=30, radius=8,
                     font=("Arial",10,"bold"),
                     ).pack(side=tk.LEFT, padx=(8, 0))

        # Phase 5.6.1 Phase 2: visible search result count label
        self._inv_result_label = tk.Label(tb, text="", bg=C["card"],
                                          fg=C["muted"], font=("Arial", 10))
        self._inv_result_label.pack(side=tk.LEFT, padx=(12, 0))

        # Quick update bar (UI v3)
        _qf_o = tk.Frame(self, bg=C["card"])
        _qf_o.pack(fill=tk.X, padx=15, pady=(0,8))
        _qfh = tk.Frame(_qf_o, bg=C["sidebar"], padx=12, pady=6)
        _qfh.pack(fill=tk.X)
        tk.Label(_qfh, text="Quick Stock Update",
                 font=("Arial",11,"bold"),
                 bg=C["sidebar"], fg=C["text"]).pack(side=tk.LEFT)
        tk.Label(_qfh, text="Adjust quantity without opening the full editor",
                 font=("Arial",9),
                 bg=C["sidebar"], fg=C["muted"]).pack(side=tk.RIGHT)
        tk.Frame(_qf_o, bg=C["teal"], height=2).pack(fill=tk.X)
        qf = tk.Frame(_qf_o, bg=C["card"], padx=12, pady=8)
        qf.pack(fill=tk.X)

        qrow = tk.Frame(qf, bg=C["card"])
        qrow.pack(fill=tk.X)

        tk.Label(qrow, text="Item:", bg=C["card"],
                 fg=C["muted"], font=("Arial",11)).pack(side=tk.LEFT, padx=(0,4))
        self.q_item = tk.StringVar()
        self.q_cb   = tk.Entry(qrow, textvariable=self.q_item,
                                font=("Arial",12), width=28,
                                bg=C["input"], fg=C["text"],
                                bd=0, insertbackground=C["accent"])
        self.q_cb.pack(side=tk.LEFT, padx=(0,10), ipady=4)

        # Smart search popup for inventory item
        self._inv_ss_win   = None
        self._inv_ss_lb    = None
        self._inv_ss_items = []

        self.q_cb.bind("<KeyRelease>",  self._inv_ss_typing)
        self.q_cb.bind("<Down>",        self._inv_ss_focus)
        self.q_cb.bind("<Up>",          lambda e: self._inv_ss_focus(e, move=-1))
        self.q_cb.bind("<Return>",      self._inv_ss_enter)
        self.q_cb.bind("<Escape>",      lambda e: self._inv_ss_hide())
        self.q_cb.bind("<FocusOut>",
                        lambda e: self.after(200, self._inv_ss_hide))

        tk.Label(qrow, text="Qty:", bg=C["card"],
                 fg=C["muted"], font=("Arial",11)).pack(side=tk.LEFT, padx=(0,4))
        self.q_qty = tk.Entry(qrow, font=("Arial",12),
                               bg=C["input"], fg=C["text"],
                               bd=0, width=8, insertbackground=C["accent"])
        self.q_qty.pack(side=tk.LEFT, ipady=5, padx=(0,10))
        self.q_qty.insert(0,"1")

        tk.Label(qrow, text="Type:", bg=C["card"],
                 fg=C["muted"], font=("Arial",11)).pack(side=tk.LEFT, padx=(0,4))
        self.q_type = tk.StringVar(value="Add (Purchase)")
        ttk.Combobox(qrow, textvariable=self.q_type,
                     values=["Add (Purchase)","Remove (Use)","Set (Correction)"],
                     state="readonly", font=("Arial",12),
                     width=18).pack(side=tk.LEFT, padx=(0,10))

        self._quick_update_btn = ModernButton(
            qrow, text="Update",
            command=self._quick_update,
            color=C["teal"], hover_color=C["blue"],
            width=96, height=32, radius=8,
            font=("Arial",10,"bold"),
        )
        self._quick_update_btn.pack(side=tk.LEFT)

        content = tk.Frame(self, bg=C["bg"])
        content.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))

        table_outer = tk.Frame(content, bg=C["card"])
        table_outer.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        table_head = tk.Frame(table_outer, bg=C["sidebar"], padx=12, pady=6)
        table_head.pack(fill=tk.X)
        tk.Label(table_head, text="Stock Grid",
                 bg=C["sidebar"], fg=C["text"],
                 font=("Arial", 11, "bold")).pack(side=tk.LEFT)
        tk.Label(table_head, text="Double click an item to edit details",
                 bg=C["sidebar"], fg=C["muted"],
                 font=("Arial", 9)).pack(side=tk.RIGHT)
        tk.Frame(table_outer, bg=C["blue"], height=2).pack(fill=tk.X)

        table_wrap = tk.Frame(table_outer, bg=C["card"])
        table_wrap.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        # Main table — UI improved: alignment, row height, zebra, status colors
        cols = ("Item","Category","Qty","Unit","Min Stock","Status","Cost Rs","Value Rs","Updated")
        self.tree = ttk.Treeview(table_wrap, columns=cols,
                                  show="headings", height=15)

        widths = [200, 130, 60, 60, 80, 80, 90, 95, 110]
        for col, w in zip(cols, widths):
            self.tree.heading(col, text=col,
                              command=lambda c=col: self._sort(c))
            self.tree.column(col, width=w, minwidth=40)
        apply_treeview_column_alignment(self.tree)

        vsb = ttk.Scrollbar(table_wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        vsb.pack(side=tk.LEFT, fill=tk.Y, padx=(0,0), pady=(0,0))

        # Inventory pagination nav container
        self._inv_pager_wrap = tk.Frame(table_wrap, bg=C["card"])
        self._inv_pager_wrap.pack(fill=tk.X)

        self.tree.bind("<Double-1>", lambda e: self._edit_dialog())
        self.tree.bind("<Button-3>", self._show_inventory_context_menu)

        # Row tags — status colors + zebra striping
        if _is_light_theme():
            ok_alt_bg = "#eef2ff"
            low_fg, low_bg = "#b45309", "#fff7ed"
            out_fg, out_bg = "#b91c1c", "#fef2f2"
        else:
            ok_alt_bg = "#1e1e32"
            low_fg, low_bg = "#f39c12", "#2a1f0a"
            out_fg, out_bg = "#e94560", "#2a0a0f"

        self.tree.tag_configure("low",      foreground=low_fg,
                                             background=low_bg)
        self.tree.tag_configure("out",      foreground=out_fg,
                                             background=out_bg)
        self.tree.tag_configure("ok",       foreground=C["text"])
        self.tree.tag_configure("ok_alt",   foreground=C["text"],
                                             background=ok_alt_bg)
        self.tree.tag_configure("low_alt",  foreground=low_fg,
                                             background=low_bg)
        self.tree.tag_configure("out_alt",  foreground=out_fg,
                                             background=out_bg)

        actions_outer = tk.Frame(content, bg=C["card"], width=240)
        actions_outer.pack(side=tk.LEFT, fill=tk.Y, padx=(12, 0))
        actions_outer.pack_propagate(False)
        actions_head = tk.Frame(actions_outer, bg=C["sidebar"], padx=12, pady=6)
        actions_head.pack(fill=tk.X)
        tk.Label(actions_head, text="Actions",
                 bg=C["sidebar"], fg=C["text"],
                 font=("Arial", 11, "bold")).pack(side=tk.LEFT)
        tk.Label(actions_head, text="Operate on selected stock item",
                 bg=C["sidebar"], fg=C["muted"],
                 font=("Arial", 9)).pack(side=tk.RIGHT)
        tk.Frame(actions_outer, bg=C["purple"], height=2).pack(fill=tk.X)

        bb = tk.Frame(actions_outer, bg=C["card"], padx=12, pady=12)
        bb.pack(fill=tk.BOTH, expand=True)
        tk.Label(bb, text="Select an inventory row and use these actions.",
                 bg=C["card"], fg=C["muted"],
                 justify="left", wraplength=200,
                 font=("Arial", 10)).pack(anchor="w", pady=(0, 10))
        for txt,clr,hclr,cmd in [
            ("Edit",  C["blue"], "#154360", self._edit_dialog),
            ("Purchase Bill", C["purple"], "#6c3483", self._purchase_dialog),
            ("Vendor Master", C["teal"], "#154360", self._vendor_master_dialog),
            ("Purchase History", C["orange"], "#b9770e", self._purchase_history_dialog),
            ("Import Preview", C["orange"], "#d35400", self._import_dialog),
            ("Delete", C["red"],  "#c0392b", self._delete),
            ("View Deleted", C["purple"], "#6c3483", self._show_deleted_products),
        ]:
            btn_icon = (
                edit_icon if txt == "Edit"
                else delete_icon if txt == "Delete"
                else import_icon if txt == "Import Preview"
                else add_icon
            )
            ModernButton(bb, text=txt, image=btn_icon, compound="left", command=cmd,
                         color=clr, hover_color=hclr,
                         width=200, height=38, radius=8,
                         font=("Arial",10,"bold"),
                         ).pack(fill=tk.X, pady=4)

        self._load()

    def _rbac_denied(self) -> bool:
        if self.app.has_permission("manage_inventory"):
            return False
        messagebox.showerror("Access Denied",
                             "Inventory management is restricted for your role.")
        return True

    # ── Sort ───────────────────────────────────
    def _sort(self, col):
        self._sort_rev = not self._sort_rev if self._sort_col==col else False
        self._sort_col = col
        self._load()

    # ── Load ───────────────────────────────────
    def _load(self, low_only=False):
        try:
            self._load_inner(low_only)
        except Exception as e:
            app_log(f"[inventory _load] {e}")

    def _load_inner(self, low_only=False):
        for i in self.tree.get_children(): self.tree.delete(i)
        inv   = get_inventory()
        q     = self.search_var.get().lower()
        cat_f = self.cat_filter.get()

        # Refresh category list
        cats = sorted(
            set(
                v.get("category", "")
                for v in inv.values()
                if v.get("category", "")
            )
        )
        cat_values = ["All"] + cats
        self.cat_cb["values"] = cat_values
        self.cat_cb.configure(state="readonly")
        if self.cat_filter.get() not in ["All"] + cats:
            self.cat_filter.set("All")

        # Refresh quick update combobox
        # q_cb is now a smart-search Entry — no values needed

        total_items = low_items = 0
        total_value = 0.0
        rows = []

        for name, item in inv.items():
            qty   = safe_float(item.get("qty",0), 0.0)
            mins  = safe_float(item.get("min_stock",5), 5.0)
            cost  = safe_float(item.get("cost",0))
            cat   = item.get("category","")
            is_low = qty <= mins
            is_out = qty == 0

            if q and q not in name.lower() and q not in cat.lower(): continue
            if cat_f != "All" and cat != cat_f: continue
            if low_only and not is_low: continue

            status = "OUT" if is_out else ("LOW" if is_low else "OK")
            value  = qty * cost
            total_value += value
            total_items += 1
            if is_low: low_items += 1

            rows.append((name, cat, qty, item.get("unit","pcs"),
                          mins, status, cost, value,
                          item.get("updated",""), is_out, is_low))

        # Sort
        col_idx = ["Item","Category","Qty","Unit","Min Stock",
                    "Status","Cost Rs","Value Rs","Updated"].index(self._sort_col)
        try:
            rows.sort(key=lambda r: r[col_idx], reverse=self._sort_rev)
        except Exception:
            pass

        # Pagination: clamp page and slice
        total = len(rows)
        max_page = max(0, (total - 1) // self._INV_PAGE_SIZE)
        self._inv_page = min(self._inv_page, max_page)
        start = self._inv_page * self._INV_PAGE_SIZE
        end = start + self._INV_PAGE_SIZE
        page_rows = rows[start:end]
        self._inv_total = total
        self._inv_max_page = max_page

        for idx_r, r in enumerate(page_rows):
            name,cat,qty,unit,mins,status,cost,value,upd,is_out,is_low = r
            base = "out" if is_out else ("low" if is_low else "ok")
            # Zebra: alternate rows get _alt tag
            tag  = base + ("_alt" if idx_r % 2 == 1 else "")
            self.tree.insert("", tk.END, values=(
                name, cat, _format_stock_qty(qty), unit, _format_stock_qty(mins), status,
                fmt_currency(cost), fmt_currency(value), upd
            ), tags=(tag,))

        # Update cards (UI v3)
        for w in self.cards_f.winfo_children(): w.destroy()
        _icons = {"Total Items": "Items", "Low Stock": "Low", "Out of Stock": "Out", "Total Value": "Value"}
        _cols  = {
            "Total Items":  C["blue"],
            "Low Stock":    C["orange"] if low_items else C["sidebar"],
            "Out of Stock": C["red"] if any(r[9] for r in rows) else C["sidebar"],
            "Total Value":  C["purple"],
        }
        for lbl,val in [
            ("Total Items",  str(total_items)),
            ("Low Stock",    str(low_items)),
            ("Out of Stock", str(sum(1 for r in rows if r[9]))),
            ("Total Value",  fmt_currency(total_value)),
        ]:
            col = _cols[lbl]
            card = tk.Frame(self.cards_f, bg=C["card"], padx=16, pady=10)
            card.pack(side=tk.LEFT, padx=(0,10))
            tk.Label(card, text=f"{_icons[lbl]}  {val}",
                     font=("Arial",16,"bold"),
                     bg=C["card"], fg=col).pack(anchor="w")
            tk.Label(card, text=lbl, font=("Arial",10),
                     bg=C["card"], fg=C["muted"]).pack(anchor="w")
            tk.Frame(card, bg=col, height=3).pack(fill=tk.X, pady=(6,0))

        # Update pagination nav
        self._update_inv_pagination(total, max_page)
        self._last_load_ts = time.monotonic()

    def _reset_inv_page(self):
        self._inv_page = 0

    def _inv_prev_page(self):
        if self._inv_page > 0:
            self._inv_page -= 1
            self._load()

    def _inv_next_page(self):
        if self._inv_page < self._inv_max_page:
            self._inv_page += 1
            self._load()

    def _update_inv_pagination(self, total, max_page):
        # Phase 5.6.1 Phase 2: update visible result count label
        shown = min(total, self._INV_PAGE_SIZE) if total > 0 else 0
        q = self.search_var.get().strip()
        cat = self.cat_filter.get()
        if hasattr(self, "_inv_result_label"):
            if total == 0 and (q or cat != "All"):
                label_text = "No matching products"
            elif q or cat != "All":
                label_text = f"Showing {shown} of {total} product{'s' if total != 1 else ''}"
            else:
                label_text = f"{total} product{'s' if total != 1 else ''}"
            self._inv_result_label.config(text=label_text)

        # Recreate the pattern from reports.py / customers.py
        if not hasattr(self, "_inv_pager_wrap"):
            return
        for w in self._inv_pager_wrap.winfo_children():
            w.destroy()
        if total <= self._INV_PAGE_SIZE:
            return
        actual = self._inv_page + 1
        pages = max(1, max_page + 1)
        tk.Button(
            self._inv_pager_wrap, text="< Prev",
            command=self._inv_prev_page,
            bg=C.get("sidebar", "#2d2d44"), fg=C.get("text", "#e8e8e8"),
            font=("Arial", 9), bd=0, relief="flat", cursor="hand2",
            state="normal" if self._inv_page > 0 else "disabled",
        ).pack(side=tk.LEFT, padx=4)
        tk.Label(
            self._inv_pager_wrap,
            text=f"Page {actual}/{pages} ({total} items)",
            bg=C.get("bg", "#0f0f23"), fg=C.get("muted", "#94a3b8"),
            font=("Arial", 9),
        ).pack(side=tk.LEFT, padx=8)
        tk.Button(
            self._inv_pager_wrap, text="Next >",
            command=self._inv_next_page,
            bg=C.get("sidebar", "#2d2d44"), fg=C.get("text", "#e8e8e8"),
            font=("Arial", 9), bd=0, relief="flat", cursor="hand2",
            state="normal" if self._inv_page < max_page else "disabled",
        ).pack(side=tk.LEFT, padx=4)

    def _show_low(self):
        self._inv_page = 0
        self.search_var.set("")
        self.cat_filter.set("All")
        self._load(low_only=True)

    def _show_all(self):
        self._inv_page = 0
        self.search_var.set("")
        self.cat_filter.set("All")
        self._load()

    # ── Item Form ──────────────────────────────
    def _item_form(self, title, name="", edit=False):
        inv  = get_inventory()
        item = inv.get(name,{})
        categories = sorted({str(v.get("category", "")).strip() for v in inv.values() if str(v.get("category", "")).strip()})
        brands = sorted({str(v.get("brand", "")).strip() for v in inv.values() if str(v.get("brand", "")).strip()})
        base_products = sorted({
            str(v.get("base_product", k)).strip()
            for k, v in inv.items()
            if str(v.get("base_product", k)).strip()
        })
        win  = tk.Toplevel(self)
        hide_while_building(win)
        win.title(title)
        popup_window(win, 760, 780)
        win.configure(bg=C["bg"])
        try:
            win.minsize(760, 640)
            win.resizable(True, True)
            win.attributes("-topmost", False)
        except Exception:
            pass
        def _close_dialog(event=None):
            try:
                if win.grab_current() == win:
                    win.grab_release()
            except Exception:
                pass
            try:
                if win.winfo_exists():
                    win.destroy()
            except Exception:
                pass
            return "break" if event is not None else None
        win.protocol("WM_DELETE_WINDOW", _close_dialog)
        win.bind("<Escape>", _close_dialog)

        dh = tk.Frame(win, bg=C["sidebar"], padx=20, pady=10)
        dh.pack(fill=tk.X)
        tk.Label(dh, text=title, font=("Arial",13,"bold"),
                 bg=C["sidebar"], fg=C["text"]).pack(side=tk.LEFT)
        tk.Frame(win, bg=C["teal"], height=2).pack(fill=tk.X)

        f, _canvas, _container = make_scrollable(
            win, bg=C["bg"], padx=30, pady=10)
        def _scroll_form(event):
            try:
                step = -1 if int(getattr(event, "delta", 0) or 0) > 0 else 1
                _canvas.yview_scroll(step, "units")
                return "break"
            except Exception:
                return None

        def _bind_form_scroll(widget):
            try:
                widget.bind("<MouseWheel>", _scroll_form, add="+")
            except Exception:
                pass
            try:
                for child in widget.winfo_children():
                    _bind_form_scroll(child)
            except Exception:
                pass

        f.grid_columnconfigure(0, weight=1)
        f.grid_columnconfigure(1, weight=1)
        left_col = tk.Frame(f, bg=C["bg"])
        right_col = tk.Frame(f, bg=C["bg"])
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        right_col.grid(row=0, column=1, sticky="nsew")

        entries = {}
        try:
            from salon_settings import get_settings
            settings_snapshot = get_settings()
            grocery_controls_visible = should_show_grocery_controls(settings_snapshot)
        except Exception:
            settings_snapshot = {}
            grocery_controls_visible = True
        unit_default = default_sale_unit(item.get("unit", "pcs") or "pcs")
        sale_unit_default = default_sale_unit(item.get("sale_unit", unit_default) or unit_default)
        base_unit_default = default_sale_unit(item.get("base_unit", sale_unit_default) or sale_unit_default)
        initial_category_value = str(item.get("category", "")).strip()
        initial_name_value = str(item.get("name", "")).strip() or name
        initial_base_product_value = str(item.get("base_product", "")).strip()
        initial_hsn_sac_value = str(item.get("hsn_sac", "")).strip()
        initial_sku_value = str(item.get("sku", "")).strip()
        initial_barcode_value = str(item.get("barcode", "")).strip()
        initial_gst_rate_value = str(item.get("gst_rate", "")).strip()
        decimal_default = bool(item.get("allow_decimal_qty", unit_default in {"kg", "g", "L", "ml", "meter"}))
        weighed_default = bool(item.get("is_weighed", unit_default in {"kg", "g"}))
        tax_inclusive_var = tk.BooleanVar(value=bool(item.get("price_includes_tax", True)))
        allow_decimal_var = tk.BooleanVar(value=decimal_default)
        weighed_var = tk.BooleanVar(value=weighed_default)

        def _combo(parent, label, key, values, value="", readonly=False, searchable=False):
            tk.Label(parent, text=label, bg=C["bg"],
                     fg=C["muted"], font=("Arial", 12)).pack(anchor="w", pady=(8, 2))
            clean_values = [str(v).strip() for v in values if str(v).strip()]
            if readonly:
                clean_values = [""] + [v for v in clean_values if v]
                safe_value = str(value).strip() if str(value).strip() in clean_values else ""
            else:
                safe_value = str(value).strip()
            var = tk.StringVar(value=safe_value)
            cb = ttk.Combobox(
                parent,
                textvariable=var,
                values=clean_values,
                state="readonly" if readonly else "normal",
                font=("Arial", 11),
            )
            cb.pack(fill=tk.X, ipady=4)
            if searchable and not readonly:
                make_searchable_combobox(cb, clean_values)
            entries[key] = cb
            return cb

        def _entry(parent, label, key, default="", disabled=False):
            tk.Label(parent, text=label, bg=C["bg"],
                     fg=C["muted"], font=("Arial", 12)).pack(anchor="w", pady=(8, 2))
            e = tk.Entry(parent, font=("Arial", 11),
                         bg=C["input"], fg=C["text"],
                         bd=0, insertbackground=C["accent"])
            e.pack(fill=tk.X, ipady=6)
            e.insert(0, default)
            if disabled:
                e.config(state="disabled")
            entries[key] = e
            return e

        category_combo = _combo(left_col, "Category:", "category", categories, item.get("category", ""), readonly=False)
        _combo(left_col, "Brand (Optional):", "brand", brands, item.get("brand", ""), readonly=True)
        _combo(left_col, "Base Product (Optional):", "base_product", base_products, item.get("base_product", name), readonly=True)
        _entry(left_col, "Item Name:", "name", name, disabled=edit)
        _entry(left_col, "Bill Label (Optional):", "bill_label", item.get("bill_label", name))
        _entry(left_col, "SKU (Optional):", "sku", item.get("sku", ""))
        _entry(left_col, "MRP (Rs Optional):", "mrp", str(item.get("mrp", "")))
        gst_rate_entry = _entry(left_col, "GST Rate %:", "gst_rate", str(item.get("gst_rate", "")))
        _entry(left_col, "HSN/SAC (Optional):", "hsn_sac", item.get("hsn_sac", ""))

        gst_manual_override = False

        def _maybe_autofill_gst_rate(event=None, force=False):
            nonlocal gst_manual_override
            if not force and gst_manual_override:
                return
            preview_payload = {
                "name": entries["name"].get().strip() if "name" in entries else "",
                "base_product": entries["base_product"].get().strip() if "base_product" in entries else "",
                "category": category_combo.get().strip(),
                "hsn_sac": entries["hsn_sac"].get().strip() if "hsn_sac" in entries else "",
                "sku": entries["sku"].get().strip() if "sku" in entries else "",
                "barcode": entries.get("barcode", bc_entry).get().strip(),
            }
            resolved_rate = resolve_inventory_gst_rate(preview_payload, settings=settings_snapshot)
            if resolved_rate is None:
                category_value = preview_payload["category"]
                if category_value and initial_category_value and category_value == initial_category_value and initial_gst_rate_value:
                    current_text = gst_rate_entry.get().strip()
                    if current_text != initial_gst_rate_value:
                        gst_rate_entry.delete(0, tk.END)
                        gst_rate_entry.insert(0, initial_gst_rate_value)
                return
            resolved_text = f"{resolved_rate:g}"
            current_text = gst_rate_entry.get().strip()
            if current_text == resolved_text:
                return
            gst_rate_entry.delete(0, tk.END)
            gst_rate_entry.insert(0, resolved_text)

        def _mark_gst_manual_override(event=None):
            nonlocal gst_manual_override
            if gst_rate_entry.get().strip():
                gst_manual_override = True

        gst_rate_entry.bind("<KeyRelease>", _mark_gst_manual_override)
        category_combo.bind("<<ComboboxSelected>>", lambda event: _maybe_autofill_gst_rate(event))
        category_combo.bind("<FocusOut>", lambda event: _maybe_autofill_gst_rate(event))
        if "base_product" in entries:
            entries["base_product"].bind("<<ComboboxSelected>>", lambda event: _maybe_autofill_gst_rate(event))
        if "name" in entries:
            entries["name"].bind("<FocusOut>", lambda event: _maybe_autofill_gst_rate(event))
        if "hsn_sac" in entries:
            entries["hsn_sac"].bind("<FocusOut>", lambda event: _maybe_autofill_gst_rate(event))
        if "sku" in entries:
            entries["sku"].bind("<FocusOut>", lambda event: _maybe_autofill_gst_rate(event))
        bc_entry.bind("<FocusOut>", lambda event: _maybe_autofill_gst_rate(event))
        _maybe_autofill_gst_rate(force=not gst_manual_override)

        unit_combo = _combo(right_col, "Unit (Measurement):", "unit", FORM_UNITS, unit_default, readonly=True)
        sale_unit_combo = _combo(right_col, "Sale Unit / Price Basis:", "sale_unit", FORM_UNITS, sale_unit_default, readonly=True)
        if grocery_controls_visible:
            base_unit_combo = _combo(right_col, "Base Unit:", "base_unit", FORM_UNITS, base_unit_default, readonly=True)
        else:
            base_unit_combo = None
        _entry(right_col, "Pack Size Value (Optional):", "pack_size", str(item.get("pack_size", "")))
        _entry(right_col, "Quantity:", "qty", str(item.get("qty", 0)))
        _entry(right_col, "Min Stock Alert:", "min_stock", str(item.get("min_stock", 5)))
        _entry(right_col, "Cost per Unit (Rs):", "cost", str(item.get("cost", 0)))
        _entry(right_col, "Sale Price (Rs):", "sale_price", str(item.get("price", item.get("cost", 0))))

        def _check(parent, text, variable):
            chk = tk.Checkbutton(
                parent,
                text=text,
                variable=variable,
                bg=C["bg"],
                fg=C["text"],
                selectcolor=C["input"],
                activebackground=C["bg"],
                activeforeground=C["text"],
                font=("Arial", 10),
                anchor="w",
            )
            chk.pack(fill=tk.X, anchor="w", pady=(8, 0))
            return chk

        _check(right_col, "Price includes tax", tax_inclusive_var)
        if grocery_controls_visible:
            _check(right_col, "Allow decimal quantity", allow_decimal_var)
            _check(right_col, "Weighed / loose item", weighed_var)

        def _sync_unit_fields(event=None):
            unit_value = entries["unit"].get().strip() or "pcs"
            if unit_value:
                sale_unit_combo.set(unit_value)
                if base_unit_combo is not None:
                    base_unit_combo.set(unit_value)
                if unit_value in {"kg", "g", "L", "ml", "meter"}:
                    allow_decimal_var.set(True)
                if unit_value in {"kg", "g"}:
                    weighed_var.set(True)

        unit_combo.bind("<<ComboboxSelected>>", _sync_unit_fields)

        # Phase 5.6.1 Phase 2: Barcode field with Generate/Clear buttons
        tk.Label(right_col, text="Barcode (Optional):", bg=C["bg"],
                 fg=C["muted"], font=("Arial", 12)).pack(anchor="w", pady=(8, 2))
        bc_row = tk.Frame(right_col, bg=C["bg"])
        bc_row.pack(fill=tk.X)
        bc_entry = tk.Entry(bc_row, font=("Arial", 11),
                            bg=C["input"], fg=C["text"],
                            bd=0, insertbackground=C["accent"], width=18)
        bc_entry.pack(side=tk.LEFT, ipady=6, expand=True, fill=tk.X, padx=(0, 4))
        bc_entry.insert(0, item.get("barcode", ""))
        entries["barcode"] = bc_entry

        def _generate_barcode():
            nm = entries["name"].get().strip() if "name" in entries else name
            if nm:
                bc = generate_barcode_from_product_code(nm)
                bc_entry.delete(0, tk.END)
                bc_entry.insert(0, bc)

        def _clear_barcode():
            bc_entry.delete(0, tk.END)

        ModernButton(bc_row, text="Generate",
                     command=_generate_barcode,
                     color=C["teal"], hover_color=C["blue"],
                     width=90, height=30, radius=6,
                     font=("Arial", 9, "bold"),
                     ).pack(side=tk.LEFT, padx=(0, 4))
        ModernButton(bc_row, text="Clear",
                     command=_clear_barcode,
                     color=C["sidebar"], hover_color=C["blue"],
                     width=70, height=30, radius=6,
                     font=("Arial", 9, "bold"),
                     ).pack(side=tk.LEFT)

        def _save():
            _maybe_autofill_gst_rate(force=False)
            raw_payload = {
                "name": entries["name"].get().strip(),
                "category": entries["category"].get().strip(),
                "brand": entries["brand"].get().strip(),
                "base_product": entries["base_product"].get().strip(),
                "pack_size": entries["pack_size"].get().strip(),
                "qty": entries["qty"].get().strip(),
                "unit": entries["unit"].get().strip() or "pcs",
                "sale_unit": entries["sale_unit"].get().strip() or entries["unit"].get().strip() or "pcs",
                "base_unit": entries["base_unit"].get().strip() if "base_unit" in entries else entries["unit"].get().strip(),
                "bill_label": entries["bill_label"].get().strip(),
                "barcode": entries.get("barcode", bc_entry).get().strip(),
                "sku": entries["sku"].get().strip(),
                "min_stock": entries["min_stock"].get().strip(),
                "cost": entries["cost"].get().strip(),
                "sale_price": entries["sale_price"].get().strip(),
                "mrp": entries["mrp"].get().strip(),
                "gst_rate": entries["gst_rate"].get().strip(),
                "hsn_sac": entries["hsn_sac"].get().strip(),
                "initial_name": initial_name_value,
                "initial_category": initial_category_value,
                "initial_base_product": initial_base_product_value,
                "initial_hsn_sac": initial_hsn_sac_value,
                "initial_sku": initial_sku_value,
                "initial_barcode": initial_barcode_value,
                "initial_gst_rate": initial_gst_rate_value,
                "gst_rate_touched": gst_manual_override,
                "price_includes_tax": tax_inclusive_var.get(),
                "allow_decimal_qty": allow_decimal_var.get(),
                "is_weighed": weighed_var.get(),
            }
            form_payload = build_inventory_product_form_payload(raw_payload, settings=settings_snapshot)
            if form_payload.validation.errors:
                messagebox.showerror(
                    "Invalid Item",
                    "\n".join(issue.message for issue in form_payload.validation.errors),
                )
                return
            if form_payload.validation.warnings:
                warning_text = "\n".join(issue.message for issue in form_payload.validation.warnings)
                if not messagebox.askyesno(
                    "Below Cost Warning",
                    f"{warning_text}\n\nContinue and save this item?",
                    default="no",
                ):
                    return
            nm = raw_payload["name"]
            cat = form_payload.inventory_item["category"]
            brand = form_payload.inventory_item["brand"]
            base_product = form_payload.inventory_item["base_product"]
            bill_label = form_payload.inventory_item["bill_label"]
            barcode = form_payload.inventory_item["barcode"]
            qty = safe_float(form_payload.inventory_item["qty"], 0.0)
            unit = form_payload.inventory_item["unit"]
            mins = safe_float(form_payload.inventory_item["min_stock"], 5.0)
            cost = safe_float(form_payload.inventory_item["cost"], 0.0)
            if not nm:
                messagebox.showerror("Error","Item name required."); return
            inv2 = get_inventory()
            if not edit and nm in inv2:
                messagebox.showerror("Error","Item already exists."); return

            # Phase 6: Duplicate barcode check
            if barcode:
                duplicates = []
                for existing_name in inv2:
                    if existing_name == nm and edit:
                        continue
                    existing_bc = str(inv2[existing_name].get("barcode", "")).strip()
                    if existing_bc and existing_bc == barcode:
                        duplicates.append(existing_name)
                if duplicates:
                    dup_names = ", ".join(duplicates[:3])
                    if len(duplicates) > 3:
                        dup_names += f" (+{len(duplicates)-3} more)"
                    result = messagebox.askyesno(
                        "Duplicate Barcode",
                        f"The barcode '{barcode}' is already used by: {dup_names}\n\n"
                        f"Using duplicate barcodes may cause scan errors at billing.\n\n"
                        f"Do you want to continue and save this duplicate?",
                        default="no")
                    if not result:
                        return

            key = name if edit else nm
            sale_price = safe_float(form_payload.inventory_item["price"], cost)
            inv2[key] = dict(form_payload.inventory_item)
            inv2[key]["updated"] = today_str()
            save_inventory(inv2)
            _close_dialog()

            def _post_save_refresh():
                try:
                    create_product_with_variants_v5(form_payload.catalog_payload)
                except Exception as e:
                    app_log(f"[_item_form v5 variant save] {e}")

                self._load()
                for item_id in self.tree.get_children():
                    values = self.tree.item(item_id, "values")
                    if values and values[0] == nm:
                        self.tree.selection_set(item_id)
                        self.tree.focus(item_id)
                        self.tree.see(item_id)
                        break
                messagebox.showinfo("Saved", "Inventory item saved.")
                if qty <= mins:
                    messagebox.showwarning("Low Stock",
                                            f"'{nm}' is low!\n{_format_stock_qty(qty)} {unit} remaining.")

            self.after(10, _post_save_refresh)

        actions = tk.Frame(win, bg=C["card"], padx=30, pady=10)
        actions.pack(fill=tk.X, side=tk.BOTTOM)
        ModernButton(actions, text="Save Item",
                     command=_save,
                     color=C["teal"], hover_color=C["blue"],
                     width=240, height=38, radius=8,
                     font=("Arial",11,"bold"),
                     ).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ModernButton(actions, text="Cancel",
                     command=_close_dialog,
                     color=C["sidebar"], hover_color=C["blue"],
                     width=140, height=38, radius=8,
                     font=("Arial",11,"bold"),
                     ).pack(side=tk.LEFT, padx=(10, 0))
        win.after(0, lambda: _bind_form_scroll(win))
        win.after(0, lambda: (
            win.grab_set(),
            entries["name"].focus_set() if "name" in entries else None
        ))
        reveal_when_ready(win)

    def _import_products(self):
        """Import all products from services_db.json into inventory."""
        try:
            from utils import load_json, F_SERVICES
            data = load_json(F_SERVICES, {})
            products = data.get("Products", {})
            if not products:
                messagebox.showwarning("No Products",
                                        "No products found in services database.\n"
                                        "Add products via Admin Panel first.")
                return
            inv = get_inventory()
            added = 0
            skipped = 0
            for cat, items in products.items():
                for name, price in items.items():
                    unit = "pcs"
                    cost = float(price)
                    if name not in inv:
                        inv[name] = {
                            "category": cat,
                            "qty": 0,
                            "unit": unit,
                            "min_stock": 5,
                            "cost": cost,
                            "price": cost,
                            "updated": today_str(),
                        }
                        added += 1
                    else:
                        skipped += 1
                        inv[name]["category"] = cat
                        inv[name]["cost"] = cost
                        inv[name]["price"] = float(inv[name].get("price", cost) or cost)
                        inv[name]["updated"] = today_str()
                    create_product_with_variants_v5({
                        "brand_name": str(inv[name].get("brand", "")).strip() or "Generic",
                        "category_name": cat or "Uncategorized",
                        "product_name": str(inv[name].get("base_product", name)).strip() or name,
                        "base_name": str(inv[name].get("base_product", name)).strip() or name,
                        "variants": [{
                            "variant_name": name,
                            "unit_value": 1,
                            "unit_type": unit,
                            "pack_label": unit,
                            "bill_label": str(inv[name].get("bill_label", name)).strip() or name,
                            "sale_price": float(inv[name].get("price", cost) or cost),
                            "cost_price": cost,
                            "stock_qty": float(inv[name].get("qty", 0) or 0),
                            "reorder_level": float(inv[name].get("min_stock", 5) or 5),
                        }],
                    })
            save_inventory(inv)
            self._load()
            messagebox.showinfo("Import Complete",
                                 f"Imported {added} products!\\n"
                                 f"Skipped {skipped} (already existed)\\n\\n"
                                 f"Stock quantity is set to 0.\n"
                                 f"Update actual quantities using Quick Stock Update.")
        except Exception as e:
            messagebox.showerror("Import Error", f"Could not import: {e}")

    def _purchase_dialog(self):
        if self._rbac_denied():
            return
        inv = get_inventory()
        sel = self.tree.selection()
        selected_name = ""
        if sel:
            try:
                selected_name = str(self.tree.item(sel[0], "values")[0]).strip()
            except Exception:
                selected_name = ""

        service = PurchaseService()
        try:
            vendors = service.list_vendors(active_only=True)
        except Exception as exc:
            app_log(f"[purchase dialog vendors] {exc}")
            vendors = []
        vendor_by_name = {
            str(vendor.get("name", "")).strip(): vendor
            for vendor in vendors
            if str(vendor.get("name", "")).strip()
        }

        win = tk.Toplevel(self)
        hide_while_building(win)
        win.title("Purchase Bill")
        popup_window(win, 900, 780)
        win.configure(bg=C["bg"])
        try:
            win.minsize(760, 640)
            win.resizable(True, True)
        except Exception:
            pass

        def _close(event=None):
            try:
                if win.grab_current() == win:
                    win.grab_release()
            except Exception:
                pass
            try:
                win.destroy()
            except Exception:
                pass

        header = tk.Frame(win, bg=C["card"], padx=18, pady=12)
        header.pack(fill=tk.X)
        tk.Label(header, text="Purchase Bill",
                 bg=C["card"], fg=C["text"],
                 font=("Arial", 14, "bold")).pack(anchor="w")
        tk.Label(header, text="Record supplier purchase and increase stock with audit movement.",
                 bg=C["card"], fg=C["muted"],
                 font=("Arial", 10)).pack(anchor="w", pady=(3, 0))

        actions = tk.Frame(win, bg=C["card"], padx=18, pady=10)
        actions.pack(fill=tk.X, side=tk.BOTTOM)

        body, _canvas, _container = make_scrollable(win, bg=C["bg"], padx=18, pady=12)

        def _scroll_purchase_form(event):
            try:
                step = -1 if int(getattr(event, "delta", 0) or 0) > 0 else 1
                _canvas.yview_scroll(step, "units")
                return "break"
            except Exception:
                return None

        def _bind_purchase_scroll(widget):
            try:
                widget.bind("<MouseWheel>", _scroll_purchase_form, add="+")
            except Exception:
                pass

        columns = tk.Frame(body, bg=C["bg"])
        columns.pack(fill=tk.X)
        left = tk.Frame(columns, bg=C["bg"])
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 12))
        right = tk.Frame(columns, bg=C["bg"])
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        fields = {}

        def _label(parent, text):
            tk.Label(parent, text=text, bg=C["bg"], fg=C["muted"],
                     font=("Arial", 11)).pack(anchor="w", pady=(8, 2))

        def _entry(parent, key, text, default="", width=28):
            _label(parent, text)
            e = tk.Entry(parent, font=("Arial", 11), bg=C["input"], fg=C["text"],
                         bd=0, width=width, insertbackground=C["accent"])
            e.pack(fill=tk.X, ipady=5)
            e.insert(0, str(default or ""))
            _bind_purchase_scroll(e)
            fields[key] = e
            return e

        _label(left, "Vendor:")
        vendor_var = tk.StringVar()
        vendor_cb = ttk.Combobox(left, textvariable=vendor_var, font=("Arial", 11), width=30)
        vendor_cb.pack(fill=tk.X, ipady=3)
        _bind_purchase_scroll(vendor_cb)
        make_searchable_combobox(vendor_cb, sorted(vendor_by_name))
        fields["vendor_name"] = vendor_cb
        vendor_id_var = tk.IntVar(value=0)

        _entry(left, "vendor_phone", "Phone:")
        _entry(left, "vendor_gstin", "GSTIN:")
        _entry(left, "vendor_address", "Address:")
        _entry(left, "invoice_no", "Purchase Invoice No:")
        _entry(left, "invoice_date", "Date:", today_str())

        _label(right, "Item:")
        item_var = tk.StringVar(value=selected_name)
        item_cb = ttk.Combobox(right, textvariable=item_var, font=("Arial", 11), width=30)
        item_cb.pack(fill=tk.X, ipady=3)
        _bind_purchase_scroll(item_cb)
        make_searchable_combobox(item_cb, sorted(inv))
        fields["item_name"] = item_cb

        qty_entry = _entry(right, "qty", "Qty:", "1")
        _label(right, "Unit:")
        unit_var = tk.StringVar(value="pcs")
        unit_cb = ttk.Combobox(right, textvariable=unit_var, values=FORM_UNITS,
                               font=("Arial", 11), width=12)
        unit_cb.pack(fill=tk.X, ipady=3)
        _bind_purchase_scroll(unit_cb)
        fields["unit"] = unit_cb
        _entry(right, "cost_price", "Cost Price (Rs):")
        _entry(right, "sale_price", "Sale Price (Rs):")
        _entry(right, "mrp", "MRP:")
        _entry(right, "gst_rate", "GST Rate %:")
        _entry(right, "hsn_sac", "HSN/SAC:")
        _entry(right, "batch_no", "Batch No:")
        _entry(right, "expiry_date", "Expiry Date:")

        notes = tk.Text(body, height=3, font=("Arial", 10), bg=C["input"], fg=C["text"],
                        bd=0, insertbackground=C["accent"])
        tk.Label(body, text="Notes:", bg=C["bg"], fg=C["muted"],
                 font=("Arial", 11)).pack(anchor="w", padx=18)
        notes.pack(fill=tk.X, padx=18, pady=(2, 10))
        _bind_purchase_scroll(notes)

        def _set_entry(key, value):
            widget = fields.get(key)
            if not widget:
                return
            try:
                widget.delete(0, tk.END)
                widget.insert(0, str(value or ""))
            except Exception:
                pass

        def _fill_vendor(event=None):
            vendor = vendor_by_name.get(vendor_var.get().strip())
            if not vendor:
                vendor_id_var.set(0)
                return
            vendor_id_var.set(int(vendor.get("id") or 0))
            _set_entry("vendor_phone", vendor.get("phone", ""))
            _set_entry("vendor_gstin", vendor.get("gstin", ""))
            _set_entry("vendor_address", vendor.get("address", ""))

        def _fill_item(event=None):
            item = inv.get(item_var.get().strip(), {})
            defaults = purchase_item_defaults(item)
            for key, value in defaults.items():
                if key == "unit":
                    unit_var.set(value)
                else:
                    _set_entry(key, value)
            try:
                qty_entry.focus_set()
                qty_entry.selection_range(0, tk.END)
            except Exception:
                pass

        vendor_cb.bind("<<ComboboxSelected>>", _fill_vendor)
        item_cb.bind("<<ComboboxSelected>>", _fill_item)
        item_cb.bind("<FocusOut>", _fill_item, add="+")
        if selected_name:
            _fill_item()

        def _save_purchase():
            item_name = item_var.get().strip()
            vendor_name = vendor_var.get().strip()
            if not vendor_name:
                messagebox.showerror("Invalid Purchase", "Vendor name is required.")
                return
            if not item_name:
                messagebox.showerror("Invalid Purchase", "Item is required.")
                return
            raw = {
                "vendor_id": vendor_id_var.get(),
                "vendor_name": vendor_name,
                "vendor_phone": fields["vendor_phone"].get(),
                "vendor_gstin": fields["vendor_gstin"].get(),
                "vendor_address": fields["vendor_address"].get(),
                "invoice_no": fields["invoice_no"].get(),
                "invoice_date": fields["invoice_date"].get(),
                "item_name": item_name,
                "qty": fields["qty"].get(),
                "unit": unit_var.get(),
                "cost_price": fields["cost_price"].get(),
                "sale_price": fields["sale_price"].get(),
                "mrp": fields["mrp"].get(),
                "gst_rate": fields["gst_rate"].get(),
                "hsn_sac": fields["hsn_sac"].get(),
                "batch_no": fields["batch_no"].get(),
                "expiry_date": fields["expiry_date"].get(),
                "notes": notes.get("1.0", tk.END),
            }
            try:
                result = service.save_purchase_invoice(build_purchase_invoice_payload(raw))
            except Exception as exc:
                messagebox.showerror("Purchase Error", f"Could not save purchase bill:\n{exc}")
                return
            _close()
            self._load()
            self._select_inventory_item(item_name)
            messagebox.showinfo(
                "Purchase Saved",
                "Purchase bill saved.\n\n"
                f"Gross: {fmt_currency(result.get('gross_total', 0))}\n"
                f"GST: {fmt_currency(result.get('tax_total', 0))}\n"
                f"Net: {fmt_currency(result.get('net_total', 0))}",
            )

        ModernButton(actions, text="Vendor Master",
                     command=self._vendor_master_dialog,
                     color=C["purple"], hover_color="#6c3483",
                     width=140, height=38, radius=8,
                     font=("Arial", 11, "bold")).pack(side=tk.LEFT, padx=(0, 10))
        ModernButton(actions, text="Purchase History",
                     command=self._purchase_history_dialog,
                     color=C["orange"], hover_color="#d35400",
                     width=160, height=38, radius=8,
                     font=("Arial", 11, "bold")).pack(side=tk.LEFT, padx=(0, 10))
        ModernButton(actions, text="Save Purchase",
                     command=_save_purchase,
                     color=C["teal"], hover_color=C["blue"],
                     width=220, height=38, radius=8,
                     font=("Arial", 11, "bold")).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ModernButton(actions, text="Cancel",
                     command=_close,
                     color=C["sidebar"], hover_color=C["blue"],
                     width=120, height=38, radius=8,
                     font=("Arial", 11, "bold")).pack(side=tk.LEFT, padx=(10, 0))
        win.bind("<Escape>", _close)
        win.after(0, lambda: _bind_purchase_scroll(win))
        reveal_when_ready(win)

    def _vendor_master_dialog(self):
        if self._rbac_denied():
            return
        try:
            open_vendor_master_dialog(self, on_change=self._load)
        except Exception as e:
            messagebox.showerror("Vendor Error", f"Could not open vendor master:\n{e}")

    def _purchase_history_dialog(self):
        if self._rbac_denied():
            return
        try:
            open_purchase_history_dialog(self)
        except Exception as e:
            messagebox.showerror("Purchase History Error", f"Could not open purchase history:\n{e}")

    def _import_dialog(self):
        if self._rbac_denied():
            return
        open_product_import_preview_dialog(
            self,
            get_inventory_fn=get_inventory,
            save_inventory_fn=save_inventory,
            refresh_inventory_fn=self._load,
        )

    def _add_dialog(self):
        if self._rbac_denied(): return
        self._item_form("Add Item")

    def _edit_dialog(self):
        if self._rbac_denied(): return
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select","Select an item."); return
        name = self.tree.item(sel[0],"values")[0]
        self._item_form(f"Edit: {name}", name, edit=True)

    def _select_inventory_item(self, name: str) -> None:
        target = str(name or "").strip()
        if not target:
            return
        try:
            for item_id in self.tree.get_children():
                values = self.tree.item(item_id, "values")
                if values and str(values[0]).strip() == target:
                    self.tree.selection_set(item_id)
                    self.tree.focus(item_id)
                    self.tree.see(item_id)
                    break
        except Exception:
            pass

    def _show_inventory_context_menu(self, event):
        row_id = self.tree.identify_row(event.y)
        if not row_id:
            return "break"
        try:
            self.tree.selection_set(row_id)
            self.tree.focus(row_id)
            values = self.tree.item(row_id, "values")
            if not values:
                return "break"
            self._register_inventory_context_menu_callbacks()

            from shared.context_menu.constants import WidgetType
            from shared.context_menu.menu_context_factory import build_context
            from shared.context_menu.renderer import renderer_service
            from shared.context_menu_definitions.inventory_context_menu import get_sections

            item_name = values[0] if len(values) > 0 else ""
            inv_item = get_inventory().get(item_name, {})
            selected_row = {
                "row_id": row_id,
                "item_name": item_name,
                "category": values[1] if len(values) > 1 else "",
                "qty": values[2] if len(values) > 2 else "",
                "unit": values[3] if len(values) > 3 else "",
                "status": values[5] if len(values) > 5 else "",
                "barcode": inv_item.get("barcode", ""),
            }
            context = build_context(
                "inventory",
                entity_type="stock_item",
                entity_id=item_name,
                selected_row=selected_row,
                selection_count=1,
                user_role=self.app.current_user.get("role", "") if getattr(self.app, "current_user", None) else "",
                widget_type=WidgetType.TREEVIEW,
                widget_id="inventory_stock_grid",
                screen_x=event.x_root,
                screen_y=event.y_root,
                extra={"has_stock_item": True},
            )
            menu = renderer_service.build_menu(self, get_sections(), context)
            menu.tk_popup(event.x_root, event.y_root)
            return "break"
        except Exception as exc:
            app_log(f"[inventory context menu] {exc}")
            return "break"

    def _register_inventory_context_menu_callbacks(self):
        from shared.context_menu.action_adapter import action_adapter
        from shared.context_menu.clipboard_service import clipboard_service
        from shared.context_menu_definitions.inventory_context_menu import InventoryContextAction

        action_adapter.register(InventoryContextAction.EDIT, lambda _ctx, _act: self._edit_dialog())
        action_adapter.register(InventoryContextAction.ADD_STOCK, lambda ctx, _act: self._prefill_quick_stock(ctx))
        action_adapter.register(
            InventoryContextAction.COPY_ITEM_NAME,
            lambda ctx, _act: clipboard_service.copy_text(self, ctx.selected_row.get("item_name", "")),
        )
        action_adapter.register(
            InventoryContextAction.COPY_BARCODE,
            lambda ctx, _act: clipboard_service.copy_text(self, ctx.selected_row.get("barcode", "")),
        )
        action_adapter.register(
            InventoryContextAction.COPY_QTY,
            lambda ctx, _act: clipboard_service.copy_text(self, ctx.selected_row.get("qty", "")),
        )
        action_adapter.register(InventoryContextAction.SHOW_LOW_STOCK, lambda _ctx, _act: self._show_low())
        action_adapter.register(InventoryContextAction.SHOW_ALL, lambda _ctx, _act: self._show_all())
        action_adapter.register(InventoryContextAction.DELETE, lambda _ctx, _act: self._delete())

    def _prefill_quick_stock(self, context):
        item_name = str(context.selected_row.get("item_name", "") or context.entity_id or "").strip()
        if not item_name:
            return
        self.q_item.set(item_name)
        self.q_type.set("Add (Purchase)")
        self.q_qty.delete(0, tk.END)
        self.q_qty.insert(0, "1")
        try:
            self.q_qty.focus_set()
            self.q_qty.selection_range(0, tk.END)
        except Exception:
            pass

    def _quick_update(self):
        name = self.q_item.get().strip()
        qty  = safe_float(self.q_qty.get(),0.0)
        typ  = self.q_type.get()
        if not name:
            messagebox.showerror("Error","Select an item."); return
        try:
            if hasattr(self, "_quick_update_btn"):
                self._quick_update_btn.set_text("Updating...")
                self.update_idletasks()
            inv  = get_inventory()
            item = inv.get(name)
            if not item:
                messagebox.showerror("Error","Item not found."); return
            current_qty = safe_float(item.get("qty", 0), 0.0)
            if "Add" in typ:
                new_qty = current_qty + qty
            elif "Remove" in typ:
                new_qty = max(0, current_qty - qty)
            else:
                new_qty = qty
            item["qty"] = new_qty
            item["updated"] = today_str()
            try:
                InventoryService().update_quantity(name, new_qty)
            except Exception as fast_exc:
                app_log(f"[inventory quick update fast path] {fast_exc}")
                save_inventory(inv)
            self._load()
            self._select_inventory_item(name)
            if item["qty"] <= item.get("min_stock",5):
                messagebox.showwarning("Low Stock",
                                        f"'{name}' is running low!\n"
                                        f"Current: {_format_stock_qty(item['qty'])} {item.get('unit','pcs')}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not update stock: {e}")
        finally:
            if hasattr(self, "_quick_update_btn"):
                self._quick_update_btn.set_text("Update")

    def _delete(self):
        if self._rbac_denied(): return
        sel = self.tree.selection()
        if not sel: return
        name = self.tree.item(sel[0],"values")[0]
        if messagebox.askyesno("Delete",f"Delete '{name}' from inventory?"):
            try:
                current_user = self.app.current_user.get("name", "Unknown")
                InventoryService().delete_item(name)
                self._load()
            except Exception as e:
                messagebox.showerror("Error", f"Could not delete: {e}")

    def _is_admin_or_owner(self) -> bool:
        role = str(self.app.current_user.get("role", "")).strip().lower()
        return role in ("owner", "admin", "manager")

    def _show_deleted_products(self):
        from adapters.product_catalog_adapter import use_v5_product_variants_db as _use_v5_pv
        if _use_v5_pv():
            from adapters.product_catalog_adapter import get_deleted_products_v5
            deleted = get_deleted_products_v5() or []
        else:
            deleted = get_deleted_products() or []
        win = tk.Toplevel(self)
        hide_while_building(win)
        win.title("Deleted Products — Recycle Bin")
        popup_window(win, 820, 620)
        win.configure(bg=C["bg"])
        try:
            win.attributes("-topmost", False)
        except Exception:
            pass

        def _close(event=None):
            try:
                if win.grab_current() == win:
                    win.grab_release()
            except Exception:
                pass
            try:
                if win.winfo_exists():
                    win.destroy()
            except Exception:
                pass
            return "break" if event is not None else None
        win.protocol("WM_DELETE_WINDOW", _close)
        win.bind("<Escape>", _close)

        # Header
        hdr = tk.Frame(win, bg=C["sidebar"], padx=20, pady=10)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="Deleted Products", font=("Arial",13,"bold"),
                 bg=C["sidebar"], fg=C["text"]).pack(side=tk.LEFT)
        self._deleted_products_count_lbl = tk.Label(
            hdr, text=f"{len(deleted)} item(s) in recycle bin",
            font=("Arial",10), bg=C["sidebar"], fg=C["muted"]
        )
        self._deleted_products_count_lbl.pack(side=tk.RIGHT)
        tk.Frame(win, bg=C["purple"], height=2).pack(fill=tk.X)

        role_note = "Restore available for inventory managers"
        if self._is_admin_or_owner():
            role_note += " | Permanent delete available for owner/admin/manager"
        tk.Label(win, text=role_note, font=("Arial",10),
                 bg=C["bg"], fg=C["muted"]).pack(fill=tk.X, padx=12, pady=(8, 0))

        cols = ("Item Name", "Category", "Deleted Date", "Deleted By")
        tree_wrap = tk.Frame(win, bg=C["bg"])
        tree_wrap.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        tree = ttk.Treeview(tree_wrap, columns=cols, show="headings", height=16)
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=160, minwidth=60)
        tree.column("Item Name", width=220, minwidth=80)

        vsb = ttk.Scrollbar(tree_wrap, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        is_light = _is_light_theme()
        for idx, item in enumerate(deleted):
            bg = C["card"] if idx % 2 == 0 else (C["bg"] if is_light else "#1e1e32")
            tree.insert("", tk.END, values=(
                item.get("name",""),
                item.get("category",""),
                item.get("deleted_at",""),
                item.get("deleted_by",""),
            ), tags=("row",))
            tree.tag_configure("row", background=bg, foreground=C["text"])

        btn_bar = tk.Frame(win, bg=C["bg"], padx=12, pady=8)
        btn_bar.pack(fill=tk.X)

        from adapters.product_catalog_adapter import use_v5_product_variants_db

        def refresh_deleted_products_list():
            for i in tree.get_children():
                tree.delete(i)
            if use_v5_product_variants_db():
                from adapters.product_catalog_adapter import get_deleted_products_v5
                new_list = get_deleted_products_v5() or []
            else:
                new_list = get_deleted_products() or []
            self._deleted_products_count_lbl.config(text=f"{len(new_list)} item(s) in recycle bin")
            for idx, item in enumerate(new_list):
                bg = C["card"] if idx % 2 == 0 else (C["bg"] if is_light else "#1e1e32")
                tree.insert("", tk.END, values=(
                    item.get("name",""),
                    item.get("category",""),
                    item.get("deleted_at",""),
                    item.get("deleted_by",""),
                ), tags=("row",))
                tree.tag_configure("row", background=bg, foreground=C["text"])

        def refresh_billing_item_cache():
            """Refresh billing autocomplete product cache after restore/delete."""
            try:
                from utils import build_item_codes
                build_item_codes(force=True)
            except Exception:
                pass

        def _restore():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Select", "Select a product to restore.")
                return
            name = tree.item(sel[0], "values")[0]
            if not messagebox.askyesno("Restore", f"Restore '{name}' to active inventory?"):
                return
            current_user = self.app.current_user.get("name", "Unknown")
            ok = False
            if use_v5_product_variants_db():
                from adapters.product_catalog_adapter import restore_product_v5
                ok = restore_product_v5(name, restored_by=current_user)
            else:
                ok = restore_product(name, restored_by=current_user)
            if ok:
                messagebox.showinfo("Restored", f"'{name}' has been restored.")
                self._load()
                refresh_deleted_products_list()
                refresh_billing_item_cache()
            else:
                messagebox.showerror("Error", f"Could not restore '{name}'. Check logs.")

        def _permanent_delete():
            if not self._is_admin_or_owner():
                messagebox.showerror("Access Denied", "Only owners and managers can permanently delete.")
                return
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Select", "Select a product to permanently delete.")
                return
            name = tree.item(sel[0], "values")[0]
            if not messagebox.askyesno("Permanent Delete",
                    f"Permanently delete '{name}'?\n\nThis action CANNOT be undone."):
                return
            if not messagebox.askyesno("Confirm Permanent Delete",
                    f"Are you SURE?\n'{name}' will be irreversibly removed."):
                return
            current_user = self.app.current_user.get("name", "Unknown")
            if use_v5_product_variants_db():
                from adapters.product_catalog_adapter import permanent_delete_product_v5
                permanent_delete_product_v5(name)
            else:
                permanent_delete_product(name, deleted_by=current_user)
            messagebox.showinfo("Deleted", f"'{name}' has been permanently deleted.")
            self._load()
            refresh_deleted_products_list()
            refresh_billing_item_cache()

        ModernButton(btn_bar, text="Restore Selected", command=_restore,
                     color=C["teal"], hover_color=C["blue"],
                     width=150, height=34, radius=8,
                     font=("Arial",10,"bold"),
                     ).pack(side=tk.LEFT, padx=6)

        if self._is_admin_or_owner():
            ModernButton(btn_bar, text="Permanently Delete", command=_permanent_delete,
                         color=C["red"], hover_color="#c0392b",
                         width=170, height=34, radius=8,
                         font=("Arial",10,"bold"),
                         ).pack(side=tk.LEFT, padx=6)

        ModernButton(btn_bar, text="Close", command=_close,
                     color=C["sidebar"], hover_color=C["blue"],
                     width=90, height=34, radius=8,
                     font=("Arial",10,"bold"),
                     ).pack(side=tk.RIGHT, padx=6)

        win.after(0, win.grab_set)
        reveal_when_ready(win)

    def _import_from_products(self):
        """Import all products from services_db.json into inventory."""
        try:
            from utils import load_json, F_SERVICES
            from datetime import date
            db = load_json(F_SERVICES, {})
            products = db.get("Products", {})
            if not products:
                messagebox.showwarning("No Products",
                                        "No products found in services_db.json")
                return
            inv = get_inventory()
            added = updated = 0
            today = date.today().strftime("%Y-%m-%d")
            for cat, items in products.items():
                for iname, price in items.items():
                    cost = float(price)
                    if iname not in inv:
                        inv[iname] = {
                            "category": cat,
                            "qty": 0,
                            "unit": "pcs",
                            "min_stock": 3,
                            "cost": cost,
                            "price": cost,
                            "updated": today,
                        }
                        added += 1
                    else:
                        inv[iname]["cost"] = cost
                        inv[iname]["price"] = float(inv[iname].get("price", cost) or cost)
                        inv[iname]["category"] = cat
                        inv[iname]["updated"] = today
                        updated += 1
                    create_product_with_variants_v5({
                        "brand_name": str(inv[iname].get("brand", "")).strip() or "Generic",
                        "category_name": cat or "Uncategorized",
                        "product_name": str(inv[iname].get("base_product", iname)).strip() or iname,
                        "base_name": str(inv[iname].get("base_product", iname)).strip() or iname,
                        "variants": [{
                            "variant_name": iname,
                            "unit_value": 1,
                            "unit_type": str(inv[iname].get("unit", "pcs")).strip() or "pcs",
                            "pack_label": str(inv[iname].get("unit", "pcs")).strip() or "pcs",
                            "bill_label": str(inv[iname].get("bill_label", iname)).strip() or iname,
                            "sale_price": float(inv[iname].get("price", cost) or cost),
                            "cost_price": cost,
                            "stock_qty": float(inv[iname].get("qty", 0) or 0),
                            "reorder_level": float(inv[iname].get("min_stock", 3) or 3),
                        }],
                    })
            save_inventory(inv)
            self._load()
            msg = (f"Import complete!\n\n"
                    f"Added:   {added} new items\n"
                    f"Updated: {updated} existing items\n\n"
                    "Set quantity for each item using Quick Update.")
            messagebox.showinfo("Import Done", msg)
        except Exception as e:
            messagebox.showerror("Import Error", f"Could not import: {e}")

    def refresh(self):
        if not getattr(self, "_force_next_refresh", False) and time.monotonic() - getattr(self, "_last_load_ts", 0.0) < 5:
            return
        self._force_next_refresh = False
        self._load()

    # INVENTORY SMART SEARCH
    def _inv_ss_typing(self, e=None):
        if getattr(e, "keysym", "") in {"Up", "Down", "Return", "Escape"}:
            return
        q = self.q_item.get().strip()
        if not q:
            self._inv_ss_hide(); return
        ql = q.lower()
        results = []
        for name, item in get_inventory().items():
            cat = str(item.get("category", "")).strip()
            brand = str(item.get("brand", "")).strip()
            base_product = str(item.get("base_product", name)).strip()
            if (
                ql in name.lower()
                or ql in cat.lower()
                or ql in brand.lower()
                or ql in base_product.lower()
            ):
                results.append({
                    "code": cat[:3].upper() if cat else "INV",
                    "name": name,
                    "category": cat,
                    "price": float(item.get("cost", 0.0) or 0.0),
                })
        results.sort(key=lambda r: r["name"].lower())
        results = results[:12]
        if not results:
            self._inv_ss_hide(); return
        self._inv_ss_items = results
        self._inv_ss_show(results)

    def _inv_ss_show(self, results):
        self._inv_ss_hide()
        try:
            x = self.q_cb.winfo_rootx()
            y = self.q_cb.winfo_rooty() + self.q_cb.winfo_height()
            w = max(340, self.q_cb.winfo_width())
            h = min(len(results) * 28, 200)
            self._inv_ss_win = tk.Toplevel(self)
            self._inv_ss_win.wm_overrideredirect(True)
            self._inv_ss_win.geometry(f"{w}x{h}+{x}+{y}")
            self._inv_ss_win.lift()
            sb = ttk.Scrollbar(self._inv_ss_win, orient="vertical")
            self._inv_ss_lb = tk.Listbox(
                self._inv_ss_win, font=("Arial",10),
                bg=C["card"], fg=C["text"],
                selectbackground=C["teal"], selectforeground="white",
                activestyle="none", bd=0, highlightthickness=0,
                yscrollcommand=sb.set)
            sb.config(command=self._inv_ss_lb.yview)
            sb.pack(side=tk.RIGHT, fill=tk.Y)
            self._inv_ss_lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            for r in results:
                self._inv_ss_lb.insert(
                    tk.END,
                    f"  {r['code']}  {r['name']}  -  Rs{r['price']:.0f}")
            if self._inv_ss_lb.size() > 0:
                self._inv_ss_lb.selection_set(0)
                self._inv_ss_lb.activate(0)
            self._inv_ss_lb.bind("<ButtonRelease-1>", self._inv_ss_click)
            self._inv_ss_lb.bind("<Double-Button-1>", self._inv_ss_click)
            self._inv_ss_lb.bind("<Return>",          self._inv_ss_click)
            self._inv_ss_lb.bind("<Up>",              lambda e: self._inv_ss_move(-1))
            self._inv_ss_lb.bind("<Down>",            lambda e: self._inv_ss_move(1))
            self._inv_ss_lb.bind("<Escape>",          lambda e: self._inv_ss_hide())
        except Exception as ex:
            app_log(f"[InvSearch] {ex}")

    def _inv_ss_focus(self, e=None, move: int = 1):
        if self._inv_ss_lb and self._inv_ss_lb.size() > 0:
            self._inv_ss_lb.focus_set()
            sel = self._inv_ss_lb.curselection()
            idx = sel[0] if sel else 0
            if sel:
                idx = max(0, min(idx + move, self._inv_ss_lb.size() - 1))
            self._inv_ss_lb.selection_clear(0, tk.END)
            self._inv_ss_lb.selection_set(idx)
            self._inv_ss_lb.activate(idx)
            self._inv_ss_lb.see(idx)
            return "break"

    def _inv_ss_move(self, delta: int):
        return self._inv_ss_focus(move=delta)

    def _inv_ss_enter(self, e=None):
        if self._inv_ss_lb and self._inv_ss_lb.size() > 0:
            sel = self._inv_ss_lb.curselection()
            if not sel:
                self._inv_ss_lb.selection_set(0)
                self._inv_ss_lb.activate(0)
            self._inv_ss_click()
            return "break"

    def _inv_ss_click(self, e=None):
        if not self._inv_ss_lb: return
        sel = self._inv_ss_lb.curselection()
        if sel:
            item = self._inv_ss_items[sel[0]]
            self.q_item.set(item["name"])
            self._inv_ss_hide()
            # Focus qty entry
            try:
                self.q_qty.focus_set()
                self.q_qty.select_range(0, tk.END)
            except Exception as e:
                app_log(f"[inventory smart search focus] {e}")

    def _inv_ss_hide(self):
        try:
            if self._inv_ss_win:
                self._inv_ss_win.destroy()
                self._inv_ss_win = None
                self._inv_ss_lb  = None
        except Exception as e:
            app_log(f"[inventory smart search hide] {e}")

    

# v5 inventory compatibility overrides ---------------------------------------
def get_inventory() -> dict:
    data = InventoryService().build_legacy_inventory_map()
    if data:
        return data
    return load_json(F_INVENTORY, {})


def save_inventory(data: dict) -> bool:
    InventoryService().sync_legacy_inventory_map(data)
    return True
