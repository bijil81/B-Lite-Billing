"""
customers.py  —  BOBY'S Salon : Customer management + visit history
FIXES:
  - Bug 13: Added VIP toggle button to _build() button row
             (_toggle_vip was defined but never connected to a button)
  - Fix R1a: record_visit() wrapped in try/except — crash prevention
  - Fix R1b: redeem_points() wrapped in try/except — returns 0.0 on error
  - Fix R1c: _cust_form() phone 10-digit validation added
  - Fix R1d: _cust_form() birthday YYYY-MM-DD format validation added
  - Fix R1e: _delete() wrapped in try/except — error shown to user
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date
from utils import (C, load_json, save_json, F_CUSTOMERS,
                   safe_float, fmt_currency, now_str,
                   app_log, validate_phone, popup_window)
from date_helpers import attach_date_mask, display_to_iso_date, iso_to_display_date, validate_display_date
from ui_theme import ModernButton
from ui_responsive import make_scrollable, get_responsive_metrics, scaled_value, fit_toplevel
from icon_system import get_action_icon
from src.blite_v6.app.window_lifecycle import hide_while_building, reveal_when_ready
from src.blite_v6.ui.input_behaviors import attach_first_letter_caps


# ─────────────────────────────────────────
#  CUSTOMERS FRAME
# ─────────────────────────────────────────
class CustomersFrame(tk.Frame):

    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self._responsive = get_responsive_metrics(parent.winfo_toplevel())
        self._history_resize_job = None
        self._build()

    def _build(self):
        self._responsive = get_responsive_metrics(self.winfo_toplevel())
        compact = self._responsive["mode"] == "compact"
        action_w = scaled_value(210, 192, 174)
        tools_w = scaled_value(270, 238, 210)
        clear_w = scaled_value(98, 90, 82)
        add_w = scaled_value(172, 158, 142)
        body_pad = scaled_value(12, 10, 8)
        btn_h = self._responsive["btn_h"]
        # Header
        hdr = tk.Frame(self, bg=C["card"], pady=10)
        hdr.pack(fill=tk.X)
        left_f = tk.Frame(hdr, bg=C["card"])
        left_f.pack(side=tk.LEFT, padx=20)
        tk.Label(left_f, text="Customer Management",
                 font=("Arial", 16, "bold"),
                 bg=C["card"], fg=C["text"]).pack(anchor="w")
        tk.Label(left_f, text="Manage customers, visits & loyalty points",
                 font=("Arial", 10),
                 bg=C["card"], fg=C["muted"]).pack(anchor="w")
        ModernButton(hdr, text="Add Customer", image=get_action_icon("add"), compound="left",
                     command=self._add_dialog,
                     color=C["teal"], hover_color=C["blue"],
                     width=add_w, height=scaled_value(36, 34, 30), radius=8,
                     font=("Arial", scaled_value(10, 10, 9), "bold"),
                     ).pack(side=tk.RIGHT, padx=15, pady=6)
        tk.Frame(self, bg=C["teal"], height=2).pack(fill=tk.X)

        intro = tk.Frame(self, bg=C["card"], padx=16, pady=10)
        intro.pack(fill=tk.X, padx=15, pady=(10, 8))
        tk.Label(intro, text="Customer Workspace",
                 font=("Arial", 13, "bold"),
                 bg=C["card"], fg=C["text"]).pack(anchor="w")
        tk.Label(intro,
                 text="Search quickly, review activity, and take action from one focused screen.",
                 font=("Arial", 10),
                 bg=C["card"], fg=C["muted"]).pack(anchor="w", pady=(3, 0))

        search_outer = tk.Frame(self, bg=C["card"])
        search_outer.pack(fill=tk.X, padx=15, pady=(0, 8))
        search_head = tk.Frame(search_outer, bg=C["sidebar"], padx=12, pady=6)
        search_head.pack(fill=tk.X)
        tk.Label(search_head, text="Search & Filter",
                 bg=C["sidebar"], fg=C["text"],
                 font=("Arial", 11, "bold")).pack(side=tk.LEFT)
        tk.Label(search_head, text="Find by customer name or phone number",
                 bg=C["sidebar"], fg=C["muted"],
                 font=("Arial", 9)).pack(side=tk.RIGHT)
        tk.Frame(search_outer, bg=C["teal"], height=2).pack(fill=tk.X)

        sf = tk.Frame(search_outer, bg=C["card"], pady=10, padx=12)
        sf.pack(fill=tk.X)
        tk.Label(sf, text="Search:", bg=C["card"],
                 fg=C["muted"]).pack(side=tk.LEFT, padx=(0, 8))
        self.search_var = tk.StringVar()
        se = tk.Entry(sf, textvariable=self.search_var,
                      font=("Arial", 11), bg=C["input"],
                      fg=C["text"], bd=0, width=30,
                      insertbackground=C["accent"])
        se.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6)
        self.search_var.trace("w", lambda *a: self._load())
        ModernButton(sf, text="Clear", image=get_action_icon("clear"), compound="left",
                     command=lambda: self.search_var.set(""),
                     color=C["sidebar"], hover_color=C["blue"],
                     width=clear_w, height=btn_h, radius=8,
                     font=("Arial", scaled_value(10, 10, 9), "bold")
                     ).pack(side=tk.LEFT, padx=(10, 0))

        # Phase 5.6.1 Phase 2: visible search result count label
        self._cust_result_label = tk.Label(sf, text="", bg=C["card"],
                                           fg=C["muted"], font=("Arial", 10))
        self._cust_result_label.pack(side=tk.LEFT, padx=(12, 0))

        self.cards_frame = tk.Frame(self, bg=C["bg"])
        self.cards_frame.pack(fill=tk.X, padx=15, pady=(0, 8))

        content = tk.Frame(self, bg=C["bg"])
        content.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))

        list_outer = tk.Frame(content, bg=C["card"])
        list_outer.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        list_head = tk.Frame(list_outer, bg=C["sidebar"], padx=12, pady=6)
        list_head.pack(fill=tk.X)
        tk.Label(list_head, text="Customer Directory",
                 bg=C["sidebar"], fg=C["text"],
                 font=("Arial", 11, "bold")).pack(side=tk.LEFT)
        tk.Label(list_head, text="Double click a row to open visit history",
                 bg=C["sidebar"], fg=C["muted"],
                 font=("Arial", 9)).pack(side=tk.RIGHT)
        tk.Frame(list_outer, bg=C["blue"], height=2).pack(fill=tk.X)

        table_wrap = tk.Frame(list_outer, bg=C["card"])
        table_wrap.pack(fill=tk.BOTH, expand=True, padx=body_pad, pady=body_pad)

        cols = ("Name", "Phone", "Visits", "Points",
                "Total Spent", "Last Visit")
        self.tree = ttk.Treeview(table_wrap, columns=cols,
                                  show="headings", height=16)
        self._tree_cols = cols
        for col in cols:
            self.tree.heading(col, text=col, anchor="w",
                              command=lambda c=col: self._sort(c))
            self.tree.column(col, width=scaled_value(140, 128, 112), anchor="w")

        vsb = ttk.Scrollbar(table_wrap, orient="vertical",
                            command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(fill=tk.BOTH, expand=True,
                       side=tk.LEFT)
        vsb.pack(side=tk.LEFT, fill=tk.Y,
                 padx=(0, 0), pady=(0, 0))

        # Phase 3B: pagination nav container (shown below tree)
        self._pager_wrap = tk.Frame(list_outer, bg=C["card"])

        table_wrap.pack(fill=tk.BOTH, expand=True, padx=body_pad, pady=body_pad)
        table_wrap.bind("<Configure>", self._resize_directory_columns, add="+")

        self.tree.bind("<Double-1>", lambda e: self._view_history())
        self.tree.bind("<Button-3>", self._show_customer_context_menu)

        tools_outer = tk.Frame(content, bg=C["card"], width=tools_w)
        tools_outer.pack(side=tk.LEFT, fill=tk.Y, padx=(12, 0))
        tools_outer.pack_propagate(False)
        tools_head = tk.Frame(tools_outer, bg=C["sidebar"], padx=12, pady=6)
        tools_head.pack(fill=tk.X)
        tk.Label(tools_head, text="Actions",
                 bg=C["sidebar"], fg=C["text"],
                 font=("Arial", 11, "bold")).pack(side=tk.LEFT)
        tk.Label(tools_head, text="Operate on selected customer",
                 bg=C["sidebar"], fg=C["muted"],
                 font=("Arial", 9)).pack(side=tk.RIGHT)
        tk.Frame(tools_outer, bg=C["purple"], height=2).pack(fill=tk.X)

        bb = tk.Frame(tools_outer, bg=C["card"], padx=body_pad, pady=body_pad)
        bb.pack(fill=tk.BOTH, expand=True)
        tk.Label(bb, text="Choose a customer in the list, then use one of these actions.",
                 bg=C["card"], fg=C["muted"],
                 justify="left", wraplength=max(150, tools_w - (body_pad * 2) - 8),
                 font=("Arial", scaled_value(10, 10, 9))).pack(anchor="w", pady=(0, 10))

        # UI v3 - ModernButton action row
        _PRI  = "#0ea5e9"
        _PRIH = "#0284c7"
        for txt, icon_name, clr, hclr, cmd in [
            ("View History",   "search",  _PRI,      _PRIH,      self._view_history),
            ("Edit Customer",  "edit",    _PRI,      _PRIH,      self._edit_dialog),
            ("Loyalty Points", "save",    _PRI,      _PRIH,      self._view_points),
            ("Toggle VIP",     "refresh", C["gold"], "#d4a017",  self._toggle_vip),
            ("Delete",         "delete",  C["orange"], "#d97706",  self._delete),
        ]:
            ModernButton(bb, text=txt, image=get_action_icon(icon_name), compound="left", command=cmd,
                         color=clr, hover_color=hclr,
                         width=action_w, height=scaled_value(40, 36, 32), radius=10,
                         font=("Arial", scaled_value(10, 10, 9), "bold"),
                         ).pack(fill=tk.X, pady=4)

        ModernButton(bb, text="View Deleted", image=get_action_icon("search"), compound="left",
                     command=self._show_deleted_customers,
                     color=C["purple"], hover_color="#7c3aed",
                     width=action_w, height=scaled_value(40, 36, 32), radius=10,
                     font=("Arial", scaled_value(10, 10, 9), "bold"),
                     ).pack(fill=tk.X, pady=4)

        self._sort_col = "Name"
        self._sort_rev = False
        self._load()

    def _sort(self, col):
        self._sort_rev = (not self._sort_rev
                          if self._sort_col == col else False)
        self._sort_col = col
        self._load()

    def _load(self):
        self._show_load("Loading customers...")
        self.after(10, lambda: self._do_load())

    def _do_load(self):
        try:
            q = self.search_var.get().lower().strip()
            customers = get_customers()
            self._hide_load()
        except Exception as e:
            self._hide_load()
            return

        rows = []

        total_cust   = len(customers)
        total_spent  = 0.0
        total_visits = 0

        for ph, c in customers.items():
            name   = c.get("name", "")
            visits = c.get("visits", [])
            pts    = c.get("points", 0)
            spent  = sum(v.get("total", 0) for v in visits)
            last   = visits[-1]["date"] if visits else ""

            total_spent  += spent
            total_visits += len(visits)

            if q and q not in name.lower() and q not in ph:
                continue
            rows.append((name, ph, len(visits), pts,
                         round(spent, 2), last))

        sort_idx = ["Name", "Phone", "Visits", "Points",
                    "Total Spent", "Last Visit"].index(self._sort_col)
        rows.sort(key=lambda r: r[sort_idx], reverse=self._sort_rev)

        # Phase 3B: paginate customer list to prevent UI freeze
        # on machines with 1000+ customers
        page_size = 50
        total = len(rows)
        max_page = max(0, (total - 1) // page_size)
        if not hasattr(self, "_cust_page"):
            self._cust_page = 0
        self._cust_page = min(self._cust_page, max_page)

        for i in self.tree.get_children():
            self.tree.delete(i)

        start = self._cust_page * page_size
        end = start + page_size
        for r in rows[start:end]:
            self.tree.insert("", tk.END,
                              values=(r[0], r[1], r[2], r[3],
                                      fmt_currency(r[4]), r[5]))

        # Update pagination controls
        self._update_cust_pagination(total, max_page)

        for w in self.cards_frame.winfo_children():
            w.destroy()
        # UI v3 - stat cards with accent bottom line
        for lbl, val, col, prefix in [
            ("Total Customers", str(total_cust),           C["teal"],   "Total"),
            ("Total Visits",    str(total_visits),         C["blue"],   "Visits"),
            ("Total Revenue",   fmt_currency(total_spent), C["purple"], "Revenue"),
        ]:
            card = tk.Frame(self.cards_frame, bg=C["card"],
                            padx=18, pady=10, relief="flat")
            card.pack(side=tk.LEFT, padx=(0, 10))
            tk.Label(card, text=f"{prefix}  {val}",
                     font=("Arial", 16, "bold"),
                     bg=C["card"], fg=col).pack(anchor="w")
            tk.Label(card, text=lbl,
                     font=("Arial", 10),
                     bg=C["card"], fg=C["muted"]).pack(anchor="w")
            tk.Frame(card, bg=col, height=3).pack(fill=tk.X, pady=(6, 0))

    # Phase 5.6.1 Phase 2: lightweight loading indicator
    def _show_load(self, text="Loading customers..."):
        try:
            self._hide_load()
            self._load_lbl = tk.Label(self, text=text,
                bg=C["bg"], fg=C["muted"], font=("Arial", 10, "italic"))
            self._load_lbl.pack(pady=2)
        except Exception:
            pass

    def _hide_load(self):
        if hasattr(self, "_load_lbl") and self._load_lbl:
            try:
                self._load_lbl.destroy()
            except Exception:
                pass
            self._load_lbl = None

    # Phase 3B: customer pagination helpers
    def _update_cust_pagination(self, total, max_page):
        """Update or create pagination controls below the tree."""
        # Phase 5.6.1 Phase 2: update visible result count label
        shown = min(total, 50) if total > 0 else 0
        q = self.search_var.get().strip() if hasattr(self, "search_var") else ""
        if hasattr(self, "_cust_result_label"):
            if total == 0 and q:
                label_text = "No matching customers"
            elif q:
                label_text = f"{shown} matching customer{'s' if shown != 1 else ''}"
            else:
                label_text = f"Showing {shown} of {total} customer{'s' if total != 1 else ''}"
            self._cust_result_label.config(text=label_text)

        if not hasattr(self, "_pager_wrap"):
            return

        # Clear old controls
        for w in self._pager_wrap.winfo_children():
            w.destroy()

        if total <= 50:
            self._pager_wrap.pack_forget()
            return

        self._pager_wrap.pack(fill=tk.X, padx=12, pady=(0, 8))

        actual = self._cust_page + 1
        tk.Button(
            self._pager_wrap, text="< Prev",
            command=self._cust_prev_page,
            bg=C["sidebar"], fg=C["text"],
            font=("Arial", 10), bd=0, relief="flat", cursor="hand2",
            state="normal" if self._cust_page > 0 else "disabled",
        ).pack(side=tk.LEFT, padx=4)

        tk.Label(
            self._pager_wrap,
            text=f"Page {actual}/{max_page + 1}  ({total} customers)",
            bg=C["bg"], fg=C["muted"], font=("Arial", 10),
        ).pack(side=tk.LEFT, padx=8)

        tk.Button(
            self._pager_wrap, text="Next >",
            command=self._cust_next_page,
            bg=C["sidebar"], fg=C["text"],
            font=("Arial", 10), bd=0, relief="flat", cursor="hand2",
            state="normal" if self._cust_page < max_page else "disabled",
        ).pack(side=tk.LEFT, padx=4)

    def _cust_prev_page(self):
        if self._cust_page > 0:
            self._cust_page -= 1
            self._load()

    def _cust_next_page(self):
        self._cust_page += 1
        self._load()

    def _selected_phone(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Please select a customer.")
            return None
        return self.tree.item(sel[0], "values")[1]

    def _show_customer_context_menu(self, event):
        row_id = self.tree.identify_row(event.y)
        if not row_id:
            return "break"
        try:
            self.tree.selection_set(row_id)
            self.tree.focus(row_id)
            values = self.tree.item(row_id, "values")
            if not values:
                return "break"
            self._register_customer_context_menu_callbacks()

            from shared.context_menu.constants import WidgetType
            from shared.context_menu.menu_context_factory import build_context
            from shared.context_menu.renderer import renderer_service
            from shared.context_menu_definitions.customer_context_menu import get_sections

            selected_row = {
                "row_id": row_id,
                "name": values[0] if len(values) > 0 else "",
                "phone": values[1] if len(values) > 1 else "",
                "visits": values[2] if len(values) > 2 else "",
                "points": values[3] if len(values) > 3 else "",
                "total_spent": values[4] if len(values) > 4 else "",
                "last_visit": values[5] if len(values) > 5 else "",
            }
            context = build_context(
                "customers",
                entity_type="customer",
                entity_id=selected_row["phone"],
                selected_row=selected_row,
                selection_count=1,
                user_role=self.app.current_user.get("role", "") if getattr(self.app, "current_user", None) else "",
                widget_type=WidgetType.TREEVIEW,
                widget_id="customer_directory",
                screen_x=event.x_root,
                screen_y=event.y_root,
                extra={"has_customer": True},
            )
            menu = renderer_service.build_menu(self, get_sections(), context)
            menu.tk_popup(event.x_root, event.y_root)
            return "break"
        except Exception as exc:
            app_log(f"[customer context menu] {exc}")
            return "break"

    def _register_customer_context_menu_callbacks(self):
        from shared.context_menu.action_adapter import action_adapter
        from shared.context_menu.clipboard_service import clipboard_service
        from shared.context_menu_definitions.customer_context_menu import CustomerContextAction

        action_adapter.register(CustomerContextAction.VIEW_HISTORY, lambda _ctx, _act: self._view_history())
        action_adapter.register(CustomerContextAction.EDIT, lambda _ctx, _act: self._edit_dialog())
        action_adapter.register(CustomerContextAction.LOYALTY_POINTS, lambda _ctx, _act: self._view_points())
        action_adapter.register(CustomerContextAction.CREATE_BILL, lambda ctx, _act: self._create_bill_from_context(ctx))
        action_adapter.register(
            CustomerContextAction.COPY_PHONE,
            lambda ctx, _act: clipboard_service.copy_text(self, ctx.selected_row.get("phone", "")),
        )
        action_adapter.register(
            CustomerContextAction.COPY_NAME,
            lambda ctx, _act: clipboard_service.copy_text(self, ctx.selected_row.get("name", "")),
        )
        action_adapter.register(CustomerContextAction.TOGGLE_VIP, lambda _ctx, _act: self._toggle_vip())
        action_adapter.register(CustomerContextAction.DELETE, lambda _ctx, _act: self._delete())

    def _create_bill_from_context(self, context):
        phone = str(context.selected_row.get("phone", "") or context.entity_id or "").strip()
        name = str(context.selected_row.get("name", "") or "").strip()
        if not phone:
            messagebox.showwarning("Select", "Please select a customer.")
            return
        try:
            self.app.switch_to("billing")
            billing_frame = getattr(self.app, "frames", {}).get("billing")
            if billing_frame is None:
                return
            has_draft = bool(
                getattr(billing_frame, "bill_items", None)
                or billing_frame.name_ent.get().strip()
                or billing_frame.phone_ent.get().strip()
            )
            if has_draft:
                messagebox.showwarning(
                    "Billing draft active",
                    "Billing already has an active draft. Clear or save it before creating a bill for this customer.",
                )
                return
            billing_frame.name_ent.insert(0, name)
            billing_frame.phone_ent.insert(0, phone)
            try:
                billing_frame._refresh_bill()
            except Exception:
                pass
        except Exception as exc:
            app_log(f"[customer create bill] {exc}")

    def _add_dialog(self, prefill_phone="", prefill_name=""):
        self._cust_form("Add Customer", prefill_phone, prefill_name)

    def _edit_dialog(self):
        ph = self._selected_phone()
        if not ph: return
        c = get_customers().get(ph, {})
        self._cust_form("Edit Customer", ph, c.get("name", ""),
                        c.get("birthday", ""), edit_mode=True)

    def _cust_form(self, title, phone="", name="",
                   birthday="", edit_mode=False):
        from adapters.customer_adapter import use_v5_customers_db
        if use_v5_customers_db():
            return self._cust_form_v5(title, phone, name, birthday, edit_mode)
        win = tk.Toplevel(self)
        hide_while_building(win)
        win.title(title)
        win.configure(bg=C["bg"])
        popup_window(win, 460, 400)
        fit_toplevel(
            win,
            scaled_value(520, 480, 440),
            scaled_value(460, 430, 390),
            min_width=400,
            min_height=340,
        )
        win.grab_set()
        win.protocol("WM_DELETE_WINDOW",
                     lambda: (win.grab_release(), win.destroy()))

        # UI v3 — dialog header bar
        dh = tk.Frame(win, bg=C["sidebar"], padx=20, pady=10)
        dh.pack(fill=tk.X)
        tk.Label(dh, text=title,
                 font=("Arial", 13, "bold"),
                 bg=C["sidebar"], fg=C["text"]).pack(side=tk.LEFT)
        tk.Frame(win, bg=C["teal"], height=2).pack(fill=tk.X)

        f, _canvas, _container = make_scrollable(
            win, bg=C["bg"], padx=30, pady=10)

        fields  = [("Name:", name), ("Phone:", phone),
                   ("Birthday (DD-MM-YYYY):", iso_to_display_date(birthday))]
        entries = []
        for idx, (lbl, val) in enumerate(fields):
            tk.Label(f, text=lbl, bg=C["bg"],
                     fg=C["muted"], font=("Arial", 12)).pack(anchor="w")
            e = tk.Entry(f, font=("Arial", 11), bg=C["input"],
                         fg=C["text"], bd=0, insertbackground=C["accent"])
            e.pack(fill=tk.X, ipady=6, pady=(3, 10))
            e.insert(0, val)
            if idx == 0:
                attach_first_letter_caps(e)
            if idx == 2:
                attach_date_mask(e)
            entries.append(e)

        if edit_mode:
            entries[1].config(state="disabled")

        def _save():
            nm = entries[0].get().strip()
            ph = entries[1].get().strip()
            bd = entries[2].get().strip()
            if not nm or not ph:
                messagebox.showerror("Error", "Name and Phone required.")
                return
            # Phone validation
            if not validate_phone(ph):
                messagebox.showerror("Error",
                                     "Phone must be exactly 10 digits.")
                return
            # Birthday format validation
            if bd:
                if not validate_display_date(bd):
                    messagebox.showerror("Error",
                                         "Birthday must be DD-MM-YYYY format.\n"
                                         "Example: 15-06-1995")
                    return
                bd = display_to_iso_date(bd)
            customers = get_customers()
            if not edit_mode and ph in customers:
                messagebox.showerror("Error", "Phone already exists.")
                return
            is_edit = ph in customers
            if ph not in customers:
                customers[ph] = {
                    "name": nm, "phone": ph, "birthday": bd,
                    "points": 0, "visits": [], "created": now_str()
                }
            else:
                customers[ph]["name"]     = nm
                customers[ph]["birthday"] = bd
            save_customers(customers)

            # V5.6.1 Phase 1 — Activity log
            try:
                from activity_log import log_event
                evt = "customer_edited" if is_edit else "customer_created"
                log_event(
                    evt,
                    entity="customer",
                    entity_id=ph,
                    details={"name": nm, "birthday": bd},
                )
            except Exception:
                pass

            win.grab_release()
            win.destroy()
            self._load()
            messagebox.showinfo("Saved", "Customer saved!")

        ModernButton(f, text="Save Customer", image=get_action_icon("save"), compound="left",
                     command=_save,
                     color=C["teal"], hover_color=C["blue"],
                     width=scaled_value(360, 320, 280), height=scaled_value(38, 36, 32), radius=8,
                     font=("Arial", scaled_value(11, 10, 9), "bold"),
                     ).pack(fill=tk.X, pady=(4, 0))
        reveal_when_ready(win)

    def _cust_form_v5(self, title, phone="", name="", birthday="", edit_mode=False):
        from adapters.customer_adapter import save_customer_v5
        win = tk.Toplevel(self)
        hide_while_building(win)
        win.title(title)
        win.configure(bg=C["bg"])
        popup_window(win, 400, 320)
        win.grab_set()
        win.protocol("WM_DELETE_WINDOW", lambda: (win.grab_release(), win.destroy()))
        dh = tk.Frame(win, bg=C["sidebar"], padx=20, pady=10)
        dh.pack(fill=tk.X)
        tk.Label(dh, text=title, font=("Arial", 13, "bold"), bg=C["sidebar"], fg=C["text"]).pack(side=tk.LEFT)
        tk.Frame(win, bg=C["teal"], height=2).pack(fill=tk.X)
        f, _canvas, _container = make_scrollable(win, bg=C["bg"], padx=30, pady=10)
        fields = [("Name:", name), ("Phone:", phone), ("Birthday (DD-MM-YYYY):", iso_to_display_date(birthday))]
        entries = []
        for idx, (lbl, val) in enumerate(fields):
            tk.Label(f, text=lbl, bg=C["bg"], fg=C["muted"], font=("Arial", 12)).pack(anchor="w")
            e = tk.Entry(f, font=("Arial", 11), bg=C["input"], fg=C["text"], bd=0, insertbackground=C["accent"])
            e.pack(fill=tk.X, ipady=6, pady=(3, 10))
            e.insert(0, val)
            if idx == 0:
                attach_first_letter_caps(e)
            if idx == 2:
                attach_date_mask(e)
            entries.append(e)
        if edit_mode:
            entries[1].config(state="disabled")

        def _save():
            nm = entries[0].get().strip()
            ph = entries[1].get().strip()
            bd = entries[2].get().strip()
            if not nm or not ph:
                messagebox.showerror("Error", "Name and Phone required.")
                return
            if not validate_phone(ph):
                messagebox.showerror("Error", "Phone must be exactly 10 digits.")
                return
            if bd:
                if not validate_display_date(bd):
                    messagebox.showerror("Error", "Birthday must be DD-MM-YYYY format.\nExample: 15-06-1995")
                    return
                bd = display_to_iso_date(bd)
            customers = get_customers()
            if not edit_mode and ph in customers:
                messagebox.showerror("Error", "Phone already exists.")
                return
            existing = customers.get(ph, {})
            save_customer_v5({
                "phone": ph,
                "name": nm,
                "birthday": bd,
                "vip": existing.get("vip", False),
                "points_balance": existing.get("points", 0),
            })

            # V5.6.1 Phase 1 — Activity log
            try:
                from activity_log import log_event
                evt = "customer_edited" if edit_mode else "customer_created"
                log_event(
                    evt,
                    entity="customer",
                    entity_id=ph,
                    details={"name": nm},
                )
            except Exception:
                pass

            win.grab_release()
            win.destroy()
            self._load()
            messagebox.showinfo("Saved", "Customer saved!")

        ModernButton(f, text="Save Customer", image=get_action_icon("save"), compound="left", command=_save, color=C["teal"], hover_color=C["blue"], width=340, height=38, radius=8, font=("Arial", 11, "bold")).pack(fill=tk.X, pady=(4, 0))
        reveal_when_ready(win)

    def _view_history(self):
        ph = self._selected_phone()
        if not ph: return
        c = get_customers().get(ph, {})

        win = tk.Toplevel(self)
        hide_while_building(win)
        win.title(f"Visit History — {c.get('name', '')} ({ph})")
        win.configure(bg=C["bg"])
        popup_window(win, 780, 500)
        fit_toplevel(
            win,
            scaled_value(980, 880, 780),
            scaled_value(620, 560, 500),
            min_width=700,
            min_height=420,
        )

        # UI v3 — history popup header
        hh = tk.Frame(win, bg=C["sidebar"], padx=16, pady=10)
        hh.pack(fill=tk.X)
        tk.Label(hh,
                 text=f"Customer  {c.get('name', '')}  |  {ph}",
                 font=("Arial", 12, "bold"),
                 bg=C["sidebar"], fg=C["text"]).pack(side=tk.LEFT)
        tk.Label(hh,
                 text=f"Points: {c.get('points', 0)}",
                 font=("Arial", 11, "bold"),
                 bg=C["sidebar"], fg=C["gold"]).pack(side=tk.RIGHT)
        tk.Frame(win, bg=C["blue"], height=2).pack(fill=tk.X)

        cols = ("Date", "Invoice", "Total", "Payment", "Items")
        tree = ttk.Treeview(win, columns=cols, show="headings", height=14)
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=scaled_value(150, 130, 110))

        vsb = ttk.Scrollbar(win, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(fill=tk.BOTH, expand=True, padx=10, side=tk.LEFT)
        vsb.pack(side=tk.LEFT, fill=tk.Y, pady=5)
        win.bind("<Configure>", lambda e, tree=tree: self._schedule_history_resize(tree), add="+")

        for v in reversed(c.get("visits", [])):
            items_str = ", ".join(
                f"{it.get('name', '')}Ã—{it.get('qty', 1)}"
                for it in v.get("items", []))
            tree.insert("", tk.END, values=(
                v.get("date", ""),
                v.get("invoice", ""),
                fmt_currency(v.get("total", 0)),
                v.get("payment", ""),
                items_str[:60],
            ))
        reveal_when_ready(win)

    def _view_points(self):
        ph = self._selected_phone()
        if not ph: return
        c   = get_customers().get(ph, {})
        pts = c.get("points", 0)
        messagebox.showinfo(
            "Loyalty Points",
            f"Customer : {c.get('name', '')}\n"
            f"Phone    : {ph}\n"
            f"Points   : {pts} pts\n"
            f"Value    : {fmt_currency(pts)}\n\n"
            f"(₹100 spent = 1 point = ₹1 discount)")

    def _toggle_vip(self):
        """Bug 13 fix: button now exists in _build() button row."""
        from adapters.customer_adapter import use_v5_customers_db
        if use_v5_customers_db():
            return self._toggle_vip_v5()
        ph = self._selected_phone()
        if not ph: return
        customers = get_customers()
        c = customers.get(ph, {})
        c["vip"] = not c.get("vip", False)
        customers[ph] = c
        save_customers(customers)
        self._load()
        status = "â­ VIP" if c["vip"] else "Normal"
        messagebox.showinfo("Updated",
                             f"{c.get('name', ph)} is now {status}")

    def _toggle_vip_v5(self):
        from adapters.customer_adapter import set_customer_vip_v5
        ph = self._selected_phone()
        if not ph:
            return
        customers = get_customers()
        c = customers.get(ph, {})
        c["vip"] = not c.get("vip", False)
        set_customer_vip_v5(ph, c["vip"])
        self._load()
        status = "VIP" if c["vip"] else "Normal"
        messagebox.showinfo("Updated", f"{c.get('name', ph)} is now {status}")

    def _is_admin_or_owner(self) -> bool:
        role = str(self.app.current_user.get("role", "")).strip().lower()
        return role in ("owner", "admin", "manager")

    def refresh_deleted_customer_cache(self) -> None:
        """Refresh billing customer cache after restore/delete so autocomplete stays current."""
        try:
            from adapters.customer_adapter import use_v5_customers_db
            if use_v5_customers_db():
                from adapters.customer_adapter import _service
                _service._invalidate_customer_cache()
        except Exception:
            pass

    def _delete(self):
        from adapters.customer_adapter import use_v5_customers_db
        if use_v5_customers_db():
            return self._delete_v5()
        ph = self._selected_phone()
        if not ph:
            return
        c = get_customers().get(ph, {})
        if messagebox.askyesno(
                "Delete Customer",
                f"Delete '{c.get('name', '')}'?\n\n"
                "This will move the customer to the trash (soft delete). "
                "Deleted customers can be restored."):
            actor = self.app.current_user.get("username", "")
            try:
                from soft_delete import soft_delete_customer
                soft_delete_customer(ph, deleted_by=actor)
                self._load()

                # V5.6.1 Phase 1 — Activity log
                try:
                    from activity_log import log_event
                    log_event(
                        "customer_soft_deleted",
                        entity="customer",
                        entity_id=ph,
                        details={"name": c.get("name", ""), "deleted_by": actor},
                    )
                except Exception:
                    pass
            except Exception as e:
                messagebox.showerror("Error", f"Could not delete: {e}")

    def _delete_v5(self):
        from adapters.customer_adapter import use_v5_customers_db, soft_delete_customer_v5
        ph = self._selected_phone()
        if not ph:
            return
        c = get_customers().get(ph, {})
        if messagebox.askyesno(
                "Delete Customer",
                f"Delete '{c.get('name', '')}'?\n\n"
                "This will move the customer to the trash (soft delete). "
                "Deleted customers can be restored."):
            actor = self.app.current_user.get("username", "")
            try:
                soft_delete_customer_v5(ph, deleted_by=actor)
                self._load()
            except Exception as e:
                messagebox.showerror("Error", f"Could not delete: {e}")

    def _delete_legacy(self, phone):
        """Hard-delete a customer from the legacy JSON store."""
        data = get_customers()
        data.pop(phone, None)
        save_customers(data)
        self._load()

    def _delete_legacy_v5(self, phone):
        """Hard-delete a customer from the V5 database."""
        from adapters.customer_adapter import delete_customer_v5
        delete_customer_v5(phone)
        self._load()

    def _show_deleted_customers(self):
        """Open a dialog listing soft-deleted customers with restore / permanent delete."""
        from adapters.customer_adapter import use_v5_customers_db
        win = tk.Toplevel(self)
        hide_while_building(win)
        win.title("Deleted Customers")
        win.configure(bg=C["bg"])
        popup_window(win, 700, 450)
        fit_toplevel(win, 780, 500, min_width=560, min_height=380)
        win.grab_set()
        win.protocol("WM_DELETE_WINDOW", lambda: (win.grab_release(), win.destroy()))

        dh = tk.Frame(win, bg=C["sidebar"], padx=20, pady=10)
        dh.pack(fill=tk.X)
        tk.Label(dh, text="Deleted Customers (Trash)",
                 font=("Arial", 13, "bold"), bg=C["sidebar"], fg=C["text"]).pack(side=tk.LEFT)
        deleted_count_lbl = tk.Label(
            dh,
            text="0 customer(s) in trash",
            font=("Arial", 10), bg=C["sidebar"], fg=C["muted"]
        )
        deleted_count_lbl.pack(side=tk.RIGHT)
        tk.Frame(win, bg=C["purple"], height=2).pack(fill=tk.X)

        role_note = "Restore available for customer managers"
        if self._is_admin_or_owner():
            role_note += " | Permanent delete available for owner/admin/manager"
        tk.Label(win, text=role_note, font=("Arial", 10),
                 bg=C["bg"], fg=C["muted"]).pack(fill=tk.X, padx=14, pady=(8, 0))

        table_f = tk.Frame(win, bg=C["card"])
        table_f.pack(fill=tk.BOTH, expand=True, padx=14, pady=10)

        cols = ("Name", "Phone", "Deleted Date", "Deleted By")
        tree = ttk.Treeview(table_f, columns=cols, show="headings", height=14)
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=150)

        vsb = ttk.Scrollbar(table_f, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        vsb.pack(side=tk.LEFT, fill=tk.Y)

        # Load deleted customers from soft-delete module
        if use_v5_customers_db():
            from adapters.customer_adapter import get_deleted_customers_v5
            try:
                deleted_list = get_deleted_customers_v5()
            except Exception:
                deleted_list = []
        else:
            from soft_delete import get_deleted_customers
            try:
                deleted_list = get_deleted_customers()
            except Exception:
                deleted_list = []
        deleted_count_lbl.config(text=f"{len(deleted_list)} customer(s) in trash")

        for entry in deleted_list:
            tree.insert("", tk.END, values=(
                entry.get("name", ""),
                entry.get("phone", ""),
                entry.get("deleted_at", ""),
                entry.get("deleted_by", ""),
            ))

        # Action buttons
        btn_frame = tk.Frame(win, bg=C["card"], padx=14, pady=10)
        btn_frame.pack(fill=tk.X)

        admin = self._is_admin_or_owner()

        def _restore_selected():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Select", "Please select a customer to restore.")
                return
            phone = tree.item(sel[0], "values")[1]
            if messagebox.askyesno(
                    "Restore",
                    f"Restore this customer?"):
                restored_by = self.app.current_user.get("username", "")
                try:
                    if use_v5_customers_db():
                        from adapters.customer_adapter import restore_customer_v5
                        restore_customer_v5(phone)
                    else:
                        from soft_delete import restore_customer
                        restore_customer(phone, restored_by=restored_by)
                    self._load()
                    refresh_deleted_list()
                    self.refresh_deleted_customer_cache()
                    messagebox.showinfo("Restored", "Customer has been restored.")
                except Exception as e:
                    messagebox.showerror("Error", f"Could not restore: {e}")

        def _permanent_delete_selected():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Select", "Please select a customer.")
                return
            values = tree.item(sel[0], "values")
            name, phone = values[0], values[1]
            if messagebox.askyesno(
                    "Permanent Delete",
                    f"Permanently delete '{name}' ({phone})?\n\n"
                    "This action CANNOT be undone. All data will be lost."):
                deleted_by = self.app.current_user.get("username", "")
                try:
                    if use_v5_customers_db():
                        from adapters.customer_adapter import permanent_delete_customer_v5
                        permanent_delete_customer_v5(phone)
                    else:
                        from soft_delete import permanent_delete_customer
                        permanent_delete_customer(phone, deleted_by=deleted_by)
                    self._load()
                    refresh_deleted_list()
                    self.refresh_deleted_customer_cache()
                    messagebox.showinfo("Deleted", "Customer permanently deleted.")
                except Exception as e:
                    messagebox.showerror("Error", f"Could not delete: {e}")

        def refresh_deleted_list():
            for i in tree.get_children():
                tree.delete(i)
            if use_v5_customers_db():
                from adapters.customer_adapter import get_deleted_customers_v5
                try:
                    new_list = get_deleted_customers_v5()
                except Exception:
                    new_list = []
            else:
                from soft_delete import get_deleted_customers
                try:
                    new_list = get_deleted_customers()
                except Exception:
                    new_list = []
            deleted_count_lbl.config(text=f"{len(new_list)} customer(s) in trash")
            for entry in new_list:
                tree.insert("", tk.END, values=(
                    entry.get("name", ""),
                    entry.get("phone", ""),
                    entry.get("deleted_at", ""),
                    entry.get("deleted_by", ""),
                ))

        ModernButton(btn_frame, text="Restore Selected", image=get_action_icon("refresh"),
                     compound="left", command=_restore_selected,
                     color=C["teal"], hover_color=C["blue"],
                     width=180, height=38, radius=8,
                     font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 10))

        if admin:
            perm_btn = ModernButton(btn_frame, text="Permanent Delete",
                                     image=get_action_icon("delete"), compound="left",
                                     command=_permanent_delete_selected,
                                     color="#ef4444", hover_color="#dc2626",
                                     width=200, height=38, radius=8,
                                     font=("Arial", 10, "bold"))
            perm_btn.pack(side=tk.LEFT)

        ModernButton(btn_frame, text="Close",
                     command=lambda: (win.grab_release(), win.destroy()),
                     color=C["sidebar"], hover_color=C["blue"],
                     width=110, height=38, radius=8,
                     font=("Arial", 10, "bold")).pack(side=tk.RIGHT)
        reveal_when_ready(win)

    def refresh(self):
        self._load()

    def _resize_directory_columns(self, event=None):
        if event is None:
            return
        width = max(560, event.width - 18)
        col_map = {
            "Name": max(130, int(width * 0.24)),
            "Phone": max(110, int(width * 0.16)),
            "Visits": max(68, int(width * 0.09)),
            "Points": max(68, int(width * 0.09)),
            "Total Spent": max(110, int(width * 0.17)),
            "Last Visit": max(120, width - (
                max(130, int(width * 0.24)) +
                max(110, int(width * 0.16)) +
                max(68, int(width * 0.09)) +
                max(68, int(width * 0.09)) +
                max(110, int(width * 0.17))
            )),
        }
        for col in self._tree_cols:
            self.tree.column(col, width=col_map[col], anchor="w")

    def _schedule_history_resize(self, tree):
        if self._history_resize_job:
            try:
                self.after_cancel(self._history_resize_job)
            except Exception:
                pass
        self._history_resize_job = self.after(80, lambda: self._resize_history_columns(tree))

    def _resize_history_columns(self, tree):
        try:
            width = max(680, tree.winfo_width())
        except Exception:
            return
        allocations = {
            "Date": max(118, int(width * 0.16)),
            "Invoice": max(84, int(width * 0.12)),
            "Total": max(86, int(width * 0.11)),
            "Payment": max(82, int(width * 0.11)),
        }
        used = sum(allocations.values())
        allocations["Items"] = max(220, width - used - 32)
        for col, val in allocations.items():
            tree.column(col, width=val, anchor="w")

# v5 compatibility overrides -------------------------------------------------
def get_customers() -> dict:
    from adapters.customer_adapter import get_customers_legacy_map_v5, use_v5_customers_db
    if use_v5_customers_db():
        return get_customers_legacy_map_v5()
    data = load_json(F_CUSTOMERS, {})
    return {ph: c for ph, c in data.items() if not c.get("is_deleted")}


def save_customers(data: dict) -> bool:
    from adapters.customer_adapter import save_customer_v5, use_v5_customers_db
    if use_v5_customers_db():
        for phone, customer in data.items():
            save_customer_v5({
                "phone": phone,
                "name": customer.get("name", ""),
                "birthday": customer.get("birthday", ""),
                "vip": customer.get("vip", False),
                "points_balance": customer.get("points", 0),
            })
        return True
    return save_json(F_CUSTOMERS, data)


def add_or_update_customer(phone: str, name: str):
    from adapters.customer_adapter import save_customer_v5, use_v5_customers_db
    if not phone or phone == "0000000000":
        return
    if use_v5_customers_db():
        existing = get_customers().get(phone, {})
        save_customer_v5({
            "phone": phone,
            "name": name,
            "birthday": existing.get("birthday", ""),
            "vip": existing.get("vip", False),
            "points_balance": existing.get("points", 0),
        })
        return
    customers = get_customers()
    if phone not in customers:
        customers[phone] = {
            "name": name,
            "phone": phone,
            "birthday": "",
            "points": 0,
            "visits": [],
            "created": now_str(),
        }
    else:
        customers[phone]["name"] = name
    save_customers(customers)


def record_visit(phone: str, invoice: str, items: list, total: float, payment: str):
    from adapters.customer_adapter import record_visit_v5, use_v5_customers_db
    if not phone or phone == "0000000000":
        return
    try:
        if use_v5_customers_db():
            return record_visit_v5(phone, invoice, total, payment)
        customers = get_customers()
        if phone not in customers:
            return
        points_earned = int(total // 100)
        customers[phone]["visits"].append({
            "date": now_str(),
            "invoice": invoice,
            "items": items,
            "total": round(total, 2),
            "payment": payment,
        })
        customers[phone]["points"] = customers[phone].get("points", 0) + points_earned
        save_customers(customers)
        return points_earned
    except Exception as e:
        app_log(f"[record_visit] {e}")


def redeem_points(phone: str, points: int) -> float:
    from adapters.customer_adapter import redeem_points_v5, use_v5_customers_db
    try:
        if use_v5_customers_db():
            return redeem_points_v5(phone, points)
        customers = get_customers()
        cust = customers.get(phone)
        if not cust:
            return 0.0
        available = cust.get("points", 0)
        use = min(points, available)
        discount = float(use)
        cust["points"] -= use
        save_customers(customers)
        return discount
    except Exception as e:
        app_log(f"[redeem_points] {e}")
        return 0.0
