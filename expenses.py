"""
expenses.py  —  BOBY'S Salon : Expenses tracker + P&L
FIXES:
  - Fix R5n: _build_cards() try/except — crash prevention + safe e.get()
  - Fix R5o: _add_expense() save block try/except — error shown to user
  - Fix R5p: _load() try/except — crash prevention
  - Fix R5q: _delete() save block try/except — error shown to user
  - Fix R5r: refresh() try/except — crash prevention
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date
import csv, os
import time
from utils import (C, load_json, save_json, safe_float,
                   F_EXPENSES, F_REPORT, fmt_currency,
                   now_str, today_str, month_str, app_log, popup_window)
from date_helpers import attach_date_mask, display_to_iso_date, iso_to_display_date, today_display_str, validate_display_date
from ui_theme import apply_treeview_column_alignment, ModernButton
from src.blite_v6.app.window_lifecycle import hide_while_building, reveal_when_ready

CATEGORIES = [
    "Salary", "Staff Bonus", "Staff Advance",
    "Rent", "Electricity", "Water", "Internet",
    "Product Purchase", "Equipment", "Maintenance",
    "Cleaning", "Advertising", "Transport",
    "Donation", "Medical", "Tax/GST",
    "Other", "Miscellaneous",
]
SALARY_CATS = {"Salary", "Staff Bonus", "Staff Advance"}
_EXPENSE_REVENUE_CACHE = {}

def _normalize_expense_date(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return today_str()
    if validate_display_date(raw):
        return display_to_iso_date(raw)
    try:
        datetime.strptime(raw, "%Y-%m-%d")
        return raw
    except Exception:
        return raw

def get_expenses() -> list:
    return load_json(F_EXPENSES, [])

def save_expenses(data: list) -> bool:
    return save_json(F_EXPENSES, data)

def get_revenue_for_period(from_d: str, to_d: str) -> float:
    report_mtime = os.path.getmtime(F_REPORT) if os.path.exists(F_REPORT) else 0
    cache_key = (from_d, to_d, report_mtime)
    cached = _EXPENSE_REVENUE_CACHE.get(cache_key)
    if cached and (time.time() - cached["time"]) <= 2.0:
        return cached["value"]
    total = 0.0
    try:
        if not os.path.exists(F_REPORT): return 0.0
        with open(F_REPORT, "r", encoding="utf-8") as f:
            r   = csv.reader(f)
            hdr = next(r, None)
            ti  = 5 if (hdr and len(hdr) >= 6) else 3
            for row in r:
                if row and len(row) > ti:
                    dt = row[0][:10]
                    if from_d <= dt <= to_d:
                        total += safe_float(row[ti])
    except Exception:
        pass
    _EXPENSE_REVENUE_CACHE[cache_key] = {"time": time.time(), "value": total}
    return total


class ExpensesFrame(tk.Frame):

    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self._build()

    def _rbac_denied(self) -> bool:
        if self.app.has_permission("manage_expenses"):
            return False
        messagebox.showerror("Access Denied",
                             "Expense management is restricted for your role.")
        return True

    def _expense_staff_names(self, include_current=""):
        names = []
        try:
            from staff import get_staff
            active_names = []
            inactive_names = []
            for sid, s in get_staff().items():
                nm = s.get("name", "") or s.get("full_name", "") or sid
                if not nm:
                    continue
                is_active = not bool(s.get("inactive", False))
                if "active" in s:
                    is_active = bool(s.get("active", True)) and not bool(s.get("inactive", False))
                if is_active:
                    active_names.append(nm)
                else:
                    inactive_names.append(nm)
            names = sorted(set(active_names))
            if include_current:
                include_current = include_current.strip()
            if include_current and include_current not in names:
                names.append(include_current)
        except Exception as e:
            app_log(f"[Expenses staff load] {e}")
        return names

    def _build(self):
        # Header (UI v3)
        hdr = tk.Frame(self, bg=C["card"], pady=10)
        hdr.pack(fill=tk.X)
        left_f = tk.Frame(hdr, bg=C["card"])
        left_f.pack(side=tk.LEFT, padx=20)
        tk.Label(left_f, text="Expenses & Profit / Loss",
                 font=("Arial", 15, "bold"),
                 bg=C["card"], fg=C["text"]).pack(anchor="w")
        tk.Label(left_f, text="Track expenses, P&L and salary",
                 font=("Arial", 10), bg=C["card"], fg=C["muted"]).pack(anchor="w")
        tk.Frame(self, bg=C["teal"], height=2).pack(fill=tk.X)

        top_band = tk.Frame(self, bg=C["bg"])
        top_band.pack(fill=tk.X, padx=15, pady=(8, 6))
        top_band.grid_columnconfigure(0, weight=1)
        top_band.grid_columnconfigure(1, weight=0)

        intro = tk.Frame(top_band, bg=C["card"], padx=18, pady=12, height=110)
        intro.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        intro.grid_propagate(False)
        tk.Label(intro, text="Expenses Workspace",
                 bg=C["card"], fg=C["text"],
                 font=("Arial", 11, "bold")).pack(anchor="w")
        tk.Label(intro, text="Capture outgoing cash flow, review P&L quickly, and manage salary-linked expenses from one screen.",
                 bg=C["card"], fg=C["muted"],
                 font=("Arial", 10)).pack(anchor="w", pady=(4, 0))

        self.cards = tk.Frame(top_band, bg=C["bg"], width=420, height=110)
        self.cards.grid(row=0, column=1, sticky="ne")
        self.cards.grid_propagate(False)
        self._build_cards()

        # Add Expense Form (UI v3)
        _af_o = tk.Frame(self, bg=C["card"])
        _af_o.pack(fill=tk.X, padx=15, pady=(0,8))
        _afh = tk.Frame(_af_o, bg=C["sidebar"], padx=12, pady=6)
        _afh.pack(fill=tk.X)
        tk.Label(_afh, text="Add Expense", font=("Arial",11,"bold"),
                 bg=C["sidebar"], fg=C["text"]).pack(side=tk.LEFT)
        tk.Frame(_af_o, bg=C["accent"], height=2).pack(fill=tk.X)
        af = tk.Frame(_af_o, bg=C["card"], padx=12, pady=10)
        af.pack(fill=tk.X)

        row1 = tk.Frame(af, bg=C["card"])
        row1.pack(fill=tk.X)

        # Date
        tk.Label(row1, text="Date:", bg=C["card"],
                 fg=C["muted"], font=("Arial", 11)).pack(side=tk.LEFT, padx=(0, 4))
        self.date_ent = tk.Entry(row1, font=("Arial", 12),
                                  bg=C["input"], fg=C["text"],
                                  bd=0, width=13,
                                  insertbackground=C["accent"])
        self.date_ent.pack(side=tk.LEFT, ipady=5, padx=(0, 12))
        self.date_ent.insert(0, today_display_str())
        attach_date_mask(self.date_ent)

        # Category
        tk.Label(row1, text="Category:", bg=C["card"],
                 fg=C["muted"], font=("Arial", 11)).pack(side=tk.LEFT, padx=(0, 4))
        self.cat_var = tk.StringVar(value=CATEGORIES[0])
        self._cat_cb = ttk.Combobox(row1, textvariable=self.cat_var,
                     values=CATEGORIES, state="readonly",
                     font=("Arial", 12),
                     width=14)
        self._cat_cb.pack(side=tk.LEFT, padx=(0, 4))
        self.cat_var.trace("w", self._on_cat_change)

        # Staff picker (shown when Salary/Bonus/Advance selected)
        self._staff_lbl = tk.Label(row1, text="Staff:",
                                    bg=C["card"], fg=C["muted"],
                                    font=("Arial", 11))
        self._staff_var = tk.StringVar()
        self._staff_cb  = ttk.Combobox(row1,
                                        textvariable=self._staff_var,
                                        state="readonly",
                                        font=("Arial", 11), width=16)
        # Hidden by default - shown for salary categories

        # Amount
        tk.Label(row1, text="Amount Rs:", bg=C["card"],
                 fg=C["muted"], font=("Arial", 11)).pack(side=tk.LEFT, padx=(0, 4))
        self.amt_ent = tk.Entry(row1, font=("Arial", 12),
                                 bg=C["input"], fg=C["lime"],
                                 bd=0, width=12,
                                  insertbackground=C["accent"])
        self.amt_ent.pack(side=tk.LEFT, ipady=5, padx=(0, 6))

        row2 = tk.Frame(af, bg=C["card"])
        row2.pack(fill=tk.X, pady=(6, 0))

        tk.Label(row2, text="Description:", bg=C["card"],
                 fg=C["muted"], font=("Arial", 11)).pack(side=tk.LEFT, padx=(0, 4))
        self.desc_ent = tk.Entry(row2, font=("Arial", 12),
                                  bg=C["input"], fg=C["text"],
                                  bd=0, insertbackground=C["accent"])
        self.desc_ent.pack(side=tk.LEFT, fill=tk.X, expand=True,
                            ipady=5, padx=(0, 10))

        ModernButton(row2, text="Add",
                     command=self._open_add_popup,
                     color=C["teal"], hover_color=C["blue"],
                     width=90, height=32, radius=8,
                     font=("Arial",10,"bold"),
                     ).pack(side=tk.LEFT)

        # Expense List
        # Filter bar
        ff_wrap = tk.Frame(self, bg=C["card"])
        ff_wrap.pack(fill=tk.X, padx=15, pady=(0, 8))
        ff_head = tk.Frame(ff_wrap, bg=C["sidebar"], padx=12, pady=6)
        ff_head.pack(fill=tk.X)
        tk.Label(ff_head, text="Search & Period",
                 font=("Arial", 11, "bold"),
                 bg=C["sidebar"], fg=C["text"]).pack(side=tk.LEFT)
        tk.Label(ff_head, text="Filter the expense ledger by date range",
                 bg=C["sidebar"], fg=C["muted"],
                 font=("Arial", 9)).pack(side=tk.RIGHT)
        tk.Frame(ff_wrap, bg=C["teal"], height=2).pack(fill=tk.X)

        ff = tk.Frame(ff_wrap, bg=C["card"], padx=12, pady=10)
        ff.pack(fill=tk.X)

        tk.Label(ff, text="From:", bg=C["card"],
                 fg=C["muted"], font=("Arial", 11)).pack(side=tk.LEFT, padx=(0, 4))
        self.from_ent = tk.Entry(ff, font=("Arial", 12), width=13,
                                  bg=C["input"], fg=C["text"],
                                  bd=0, insertbackground=C["accent"])
        self.from_ent.pack(side=tk.LEFT, ipady=4, padx=(0, 8))
        self.from_ent.insert(0, iso_to_display_date(date.today().strftime("%Y-%m-01")))
        attach_date_mask(self.from_ent)

        tk.Label(ff, text="To:", bg=C["card"],
                 fg=C["muted"], font=("Arial", 11)).pack(side=tk.LEFT, padx=(0, 4))
        self.to_ent = tk.Entry(ff, font=("Arial", 12), width=13,
                                bg=C["input"], fg=C["text"],
                                bd=0, insertbackground=C["accent"])
        self.to_ent.pack(side=tk.LEFT, ipady=4, padx=(0, 8))
        self.to_ent.insert(0, today_display_str())
        attach_date_mask(self.to_ent)

        ModernButton(ff, text="Filter",
                     command=self._load,
                     color=C["teal"], hover_color=C["blue"],
                     width=80, height=30, radius=8,
                     font=("Arial",10,"bold"),
                     ).pack(side=tk.LEFT, padx=(0,6))

        ModernButton(ff, text="This Month",
                     command=self._set_month,
                     color=C["blue"], hover_color="#154360",
                     width=106, height=30, radius=8,
                     font=("Arial",10,"bold"),
                     ).pack(side=tk.LEFT, padx=(0,6))

        ModernButton(ff, text="Today",
                     command=self._set_today,
                     color=C["purple"], hover_color="#6c3483",
                     width=80, height=30, radius=8,
                     font=("Arial",10,"bold"),
                     ).pack(side=tk.LEFT)

        main = tk.Frame(self, bg=C["bg"])
        main.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))

        list_wrap = tk.Frame(main, bg=C["card"])
        list_wrap.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        list_head = tk.Frame(list_wrap, bg=C["sidebar"], padx=12, pady=6)
        list_head.pack(fill=tk.X)
        tk.Label(list_head, text="Expense Ledger",
                 font=("Arial", 11, "bold"),
                 bg=C["sidebar"], fg=C["text"]).pack(side=tk.LEFT)
        tk.Label(list_head, text="Double click an entry to edit",
                 bg=C["sidebar"], fg=C["muted"],
                 font=("Arial", 9)).pack(side=tk.RIGHT)
        tk.Frame(list_wrap, bg=C["blue"], height=2).pack(fill=tk.X)

        table_area = tk.Frame(list_wrap, bg=C["card"])
        table_area.pack(fill=tk.BOTH, expand=True)

        # Treeview
        cols = ("Date", "Category", "Staff", "Description", "Amount")
        self.tree = ttk.Treeview(table_area, columns=cols,
                                  show="headings", height=12)
        for col, w in zip(cols, [110, 140, 130, 260, 110]):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w)
        apply_treeview_column_alignment(self.tree)
        self.tree.heading("Amount", text="Amount Rs", anchor="e")
        self.tree.column("Amount", width=96, anchor="e")

        vsb = ttk.Scrollbar(table_area, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=(12, 0), pady=12, side=tk.LEFT)
        vsb.pack(side=tk.LEFT, fill=tk.Y, pady=12, padx=(0, 12))
        self.tree.bind("<Double-1>", lambda e: self._edit_selected())
        self.tree.bind("<Button-3>", self._show_expense_context_menu)

        rail = tk.Frame(main, bg=C["card"], padx=14, pady=14, width=260)
        rail.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 0))
        rail.pack_propagate(False)
        tk.Label(rail, text="Actions", bg=C["card"], fg=C["text"],
                 font=("Arial", 11, "bold")).pack(anchor="w")
        tk.Label(rail, text="Choose an expense row and use the action below.",
                 bg=C["card"], fg=C["muted"], justify="left",
                 wraplength=220,
                 font=("Arial", 9)).pack(anchor="w", pady=(6, 14))
        ModernButton(rail, text="Edit Selected",
                     command=self._edit_selected,
                     color=C["blue"], hover_color="#154360",
                     width=210, height=36, radius=8,
                     font=("Arial",10,"bold"),
                     ).pack(anchor="w", pady=(0, 8))
        ModernButton(rail, text="Delete Selected",
                     command=self._delete,
                     color=C["red"], hover_color="#c0392b",
                     width=210, height=36, radius=8,
                     font=("Arial",10,"bold"),
                     ).pack(anchor="w")

        self._load()

    def _build_cards(self, expenses=None):
        try:
            for w in self.cards.winfo_children():
                w.destroy()
            self.cards.grid_columnconfigure(0, weight=1)

            td = today_str()
            mo = date.today().strftime("%Y-%m-01")
            me = today_str()

            today_rev  = get_revenue_for_period(td, td)
            month_rev  = get_revenue_for_period(mo, me)

            if expenses is None:
                expenses = get_expenses()
            today_exp = sum(safe_float(e.get("amount", 0))
                            for e in expenses if e.get("date","")[:10] == td)
            month_exp = sum(safe_float(e.get("amount", 0))
                            for e in expenses
                            if e.get("date","")[:7] == month_str())

            today_cards = [
                ("Today Revenue",  fmt_currency(today_rev),             C["teal"]),
                ("Today Expenses", fmt_currency(today_exp),             C["red"]),
                ("Today Profit",   fmt_currency(today_rev - today_exp), C["green"]),
            ]
            month_cards = [
                ("Month Revenue",  fmt_currency(month_rev),             C["blue"]),
                ("Month Expenses", fmt_currency(month_exp),             C["orange"]),
                ("Month Profit",   fmt_currency(month_rev - month_exp), C["purple"]),
            ]

            def _card(parent, label, value, color, *, big=False):
                padx = 16
                pady = 10 if big else 6
                value_font = ("Arial", 14, "bold") if big else ("Arial", 10, "bold")
                label_font = ("Arial", 10, "bold") if big else ("Arial", 8)
                card = tk.Frame(parent, bg=color, padx=padx, pady=pady, height=60 if big else 48)
                card.pack_propagate(False)
                tk.Label(card, text=value, font=value_font,
                         bg=color, fg="white").pack(anchor="w")
                tk.Label(card, text=label, font=label_font,
                         bg=color, fg="white").pack(anchor="w", pady=(4 if big else 1, 0))
                return card

            today_row = tk.Frame(self.cards, bg=C["bg"])
            today_row.grid(row=0, column=0, sticky="ew", pady=(0, 4))
            for col in range(3):
                today_row.grid_columnconfigure(col, weight=1, uniform="expense_summary")
            for idx, (lbl, val, col) in enumerate(today_cards):
                card = _card(today_row, lbl, val, col, big=True)
                card.grid(row=0, column=idx, sticky="nsew", padx=(0, 6 if idx < 2 else 0))

            month_row = tk.Frame(self.cards, bg=C["bg"])
            month_row.grid(row=1, column=0, sticky="ew", pady=(2, 0))
            for col in range(3):
                month_row.grid_columnconfigure(col, weight=1, uniform="expense_summary")
            for idx, (lbl, val, col) in enumerate(month_cards):
                card = _card(month_row, lbl, val, col, big=False)
                card.grid(row=0, column=idx, sticky="nsew", padx=(0, 6 if idx < 2 else 0))
        except Exception as e:
            app_log(f"[_build_cards] {e}")

    def _on_cat_change(self, *args):
        """Show/hide staff picker based on category."""
        # Using module-level SALARY_CATS
        cat = self.cat_var.get()
        if cat in SALARY_CATS:
            staff_list = self._expense_staff_names(self._staff_var.get().strip())
            self._staff_cb["values"] = staff_list
            if staff_list and not self._staff_var.get().strip():
                self._staff_var.set(staff_list[0])
            self._staff_lbl.pack(side=tk.LEFT, padx=(0,4))
            self._staff_cb.pack(side=tk.LEFT, padx=(0,10))
        else:
            self._staff_lbl.pack_forget()
            self._staff_cb.pack_forget()
            self._staff_var.set("")

    def _add_expense_from_values(self, dt, cat, desc, amt, staff_name=""):
        if self._rbac_denied(): return

        dt = _normalize_expense_date(dt)

        if not amt:
            messagebox.showerror("Error", "Enter amount."); return
        av = safe_float(amt, None)
        if av is None or av <= 0:
            messagebox.showerror("Error", "Invalid amount."); return

        if cat in SALARY_CATS:
            # Auto-fill description if empty
            if not desc and staff_name:
                desc = cat + " - " + staff_name

        try:
            data = get_expenses()
            data.append({
                "date":        dt or today_str(),
                "category":    cat,
                "staff":       staff_name,
                "description": desc,
                "amount":      av,
                "added":       now_str(),
            })
            save_expenses(data)
            self.amt_ent.delete(0, tk.END)
            self.desc_ent.delete(0, tk.END)
            self._load()
            self._build_cards()
        except Exception as e:
            messagebox.showerror("Error", f"Could not save expense: {e}")

    def _add_expense(self):
        self._add_expense_from_values(
            self.date_ent.get().strip(),
            self.cat_var.get(),
            self.desc_ent.get().strip(),
            self.amt_ent.get().strip(),
            self._staff_var.get().strip(),
        )

    def _open_add_popup(self):
        if self._rbac_denied():
            return
        defaults = {
            "date": self.date_ent.get().strip() or today_display_str(),
            "category": self.cat_var.get().strip() or CATEGORIES[0],
            "staff": self._staff_var.get().strip(),
            "description": self.desc_ent.get().strip(),
            "amount": self.amt_ent.get().strip(),
        }
        self._open_expense_popup(mode="add", record=defaults)

    def _show_expense_context_menu(self, event):
        row_id = self.tree.identify_row(event.y)
        if not row_id:
            return "break"
        try:
            self.tree.selection_set(row_id)
            self.tree.focus(row_id)
            values = self.tree.item(row_id, "values")
            if not values:
                return "break"
            self._register_expense_context_menu_callbacks()

            from shared.context_menu.constants import WidgetType
            from shared.context_menu.menu_context_factory import build_context
            from shared.context_menu.renderer import renderer_service
            from shared.context_menu_definitions.expense_context_menu import get_sections

            selected_row = {
                "row_id": row_id,
                "date": values[0] if len(values) > 0 else "",
                "category": values[1] if len(values) > 1 else "",
                "staff": values[2] if len(values) > 2 else "",
                "description": values[3] if len(values) > 3 else "",
                "amount": values[4] if len(values) > 4 else "",
            }
            context = build_context(
                "expenses",
                entity_type="expense",
                entity_id=f"{selected_row['date']}|{selected_row['category']}|{selected_row['amount']}",
                selected_row=selected_row,
                selection_count=1,
                user_role=self.app.current_user.get("role", "") if getattr(self.app, "current_user", None) else "",
                widget_type=WidgetType.TREEVIEW,
                widget_id="expenses_grid",
                screen_x=event.x_root,
                screen_y=event.y_root,
                extra={"has_expense": True},
            )
            menu = renderer_service.build_menu(self, get_sections(), context)
            menu.tk_popup(event.x_root, event.y_root)
            return "break"
        except Exception as exc:
            app_log(f"[expenses context menu] {exc}")
            return "break"

    def _register_expense_context_menu_callbacks(self):
        from shared.context_menu.action_adapter import action_adapter
        from shared.context_menu.clipboard_service import clipboard_service
        from shared.context_menu_definitions.expense_context_menu import ExpenseContextAction

        action_adapter.register(ExpenseContextAction.EDIT, lambda _ctx, _act: self._edit_selected())
        action_adapter.register(
            ExpenseContextAction.COPY_AMOUNT,
            lambda ctx, _act: clipboard_service.copy_text(self, ctx.selected_row.get("amount", "")),
        )
        action_adapter.register(
            ExpenseContextAction.COPY_DESCRIPTION,
            lambda ctx, _act: clipboard_service.copy_text(self, ctx.selected_row.get("description", "")),
        )
        action_adapter.register(
            ExpenseContextAction.COPY_CATEGORY,
            lambda ctx, _act: clipboard_service.copy_text(self, ctx.selected_row.get("category", "")),
        )
        action_adapter.register(ExpenseContextAction.REFRESH, lambda _ctx, _act: self._load())
        action_adapter.register(ExpenseContextAction.DELETE, lambda _ctx, _act: self._delete())

    def _selected_record_ref(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select an expense.")
            return None
        values = self.tree.item(sel[0], "values")
        dt, cat, staff_name, desc = values[0], values[1], values[2], values[3]
        amount_text = str(values[4]).replace(",", "").replace("Rs.", "").replace("₹", "").strip()
        amount = safe_float(amount_text, 0)
        data = get_expenses()
        for idx, e in enumerate(data):
            if (
                e.get("date", "")[:10] == dt
                and e.get("category", "") == cat
                and (e.get("staff", "") or "") == (staff_name or "")
                and e.get("description", "") == desc
                and abs(safe_float(e.get("amount", 0)) - amount) < 0.01
            ):
                return idx, e, data
        messagebox.showerror("Not Found", "Could not locate the selected expense entry.")
        return None

    def _edit_selected(self):
        if self._rbac_denied():
            return
        ref = self._selected_record_ref()
        if not ref:
            return
        idx, record, data = ref

        self._open_expense_popup(mode="edit", record=record, data=data, idx=idx)

    def _open_expense_popup(self, mode="add", record=None, data=None, idx=None):
        record = record or {}
        data = data or get_expenses()

        win = tk.Toplevel(self)
        hide_while_building(win)
        popup_window(win, 700, 560)
        win.title("Edit Expense" if mode == "edit" else "Add Expense")
        win.configure(bg=C["bg"])
        win.transient(self.winfo_toplevel())

        def _close():
            try:
                win.grab_release()
            except Exception:
                pass
            win.destroy()

        self.after_idle(lambda: win.grab_set())
        win.protocol("WM_DELETE_WINDOW", _close)
        win.bind("<Escape>", lambda e: (_close(), "break"))

        head = tk.Frame(win, bg=C["sidebar"], padx=18, pady=10)
        head.pack(fill=tk.X)
        tk.Label(head, text="Edit Expense" if mode == "edit" else "Add Expense",
                 bg=C["sidebar"], fg=C["text"],
                 font=("Arial", 12, "bold")).pack(side=tk.LEFT)
        tk.Frame(win, bg=C["teal"], height=2).pack(fill=tk.X)

        body = tk.Frame(win, bg=C["bg"], padx=18, pady=14)
        body.pack(fill=tk.BOTH, expand=True)

        def _label(text):
            tk.Label(body, text=text, bg=C["bg"], fg=C["muted"],
                     font=("Arial", 11)).pack(anchor="w", pady=(4, 2))

        def _entry(default=""):
            ent = tk.Entry(body, font=("Arial", 11), bg=C["input"], fg=C["text"],
                           bd=0, insertbackground=C["accent"])
            ent.pack(fill=tk.X, ipady=6)
            ent.insert(0, default)
            return ent

        _label("Date (DD-MM-YYYY):")
        raw_date = str(record.get("date", ""))[:10]
        date_ent = _entry(iso_to_display_date(raw_date) if raw_date else today_display_str())
        attach_date_mask(date_ent)

        _label("Category:")
        cat_var = tk.StringVar(value=record.get("category", CATEGORIES[0]))
        cat_cb = ttk.Combobox(body, textvariable=cat_var, values=CATEGORIES, state="readonly", font=("Arial", 11))
        cat_cb.pack(fill=tk.X, ipady=4)

        _label("Linked Staff (if applicable):")
        staff_var = tk.StringVar(value=record.get("staff", ""))
        staff_cb = ttk.Combobox(body, textvariable=staff_var, state="readonly", font=("Arial", 11))
        staff_cb.pack(fill=tk.X, ipady=4)

        def _load_staff_names():
            current_staff = staff_var.get().strip()
            names = self._expense_staff_names(current_staff)
            staff_cb["values"] = names
            if cat_var.get() in SALARY_CATS and names and not staff_var.get().strip():
                staff_var.set(names[0])

        def _sync_staff_visibility(*_):
            if cat_var.get() in SALARY_CATS:
                _load_staff_names()
                staff_cb.config(state="readonly")
            else:
                staff_var.set("")
                staff_cb.config(state="disabled")

        cat_var.trace_add("write", _sync_staff_visibility)
        _sync_staff_visibility()

        _label("Amount Rs:")
        amt_ent = _entry(str(record.get("amount", "")))

        _label("Description:")
        desc_ent = _entry(record.get("description", ""))

        actions = tk.Frame(body, bg=C["bg"])
        actions.pack(fill=tk.X, pady=(16, 0))

        def _collect_form_values():
            raw_date = date_ent.get().strip() or today_display_str()
            new_date = _normalize_expense_date(raw_date)
            try:
                datetime.strptime(new_date, "%Y-%m-%d")
            except Exception:
                messagebox.showerror("Error", "Date must be DD-MM-YYYY format.\nExample: 28-03-2026")
                return None
            new_cat = cat_var.get().strip() or CATEGORIES[0]
            new_amount = safe_float(amt_ent.get().strip(), None)
            if new_amount is None or new_amount <= 0:
                messagebox.showerror("Error", "Enter a valid amount.")
                return None
            new_staff = staff_var.get().strip() if new_cat in SALARY_CATS else ""
            new_desc = desc_ent.get().strip()
            if not new_desc and new_staff and new_cat in SALARY_CATS:
                new_desc = f"{new_cat} - {new_staff}"
            return {
                "date": new_date,
                "category": new_cat,
                "staff": new_staff,
                "description": new_desc,
                "amount": new_amount,
            }

        def _save_edit():
            form_data = _collect_form_values()
            if not form_data:
                return
            updated = dict(record)
            updated.update(form_data)
            data[idx] = updated
            save_expenses(data)
            _close()
            self._load()

        def _add_new_from_popup():
            form_data = _collect_form_values()
            if not form_data:
                return
            self._add_expense_from_values(
                form_data["date"],
                form_data["category"],
                form_data["description"],
                str(form_data["amount"]),
                form_data["staff"],
            )
            _close()

        if mode == "edit":
            ModernButton(actions, text="Save Changes",
                         command=_save_edit,
                         color=C["teal"], hover_color=C["blue"],
                         width=180, height=34, radius=8,
                         font=("Arial", 10, "bold")).pack(side=tk.LEFT)
            ModernButton(actions, text="Add Expense",
                         command=_add_new_from_popup,
                         color=C["accent"], hover_color=C["blue"],
                         width=150, height=34, radius=8,
                         font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(8, 0))
        else:
            ModernButton(actions, text="Add Expense",
                         command=_add_new_from_popup,
                         color=C["teal"], hover_color=C["blue"],
                         width=180, height=34, radius=8,
                         font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        ModernButton(actions, text="Cancel",
                     command=_close,
                     color=C["sidebar"], hover_color=C["blue"],
                     width=120, height=34, radius=8,
                     font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(8, 0))
        reveal_when_ready(win)

    def _set_month(self):
        self.from_ent.delete(0, tk.END)
        self.from_ent.insert(0, iso_to_display_date(date.today().strftime("%Y-%m-01")))
        self.to_ent.delete(0, tk.END)
        self.to_ent.insert(0, today_display_str())
        self._load()

    def _set_today(self):
        self.from_ent.delete(0, tk.END); self.from_ent.insert(0, today_display_str())
        self.to_ent.delete(0, tk.END);   self.to_ent.insert(0, today_display_str())
        self._load()

    def _load(self):
        try:
            for i in self.tree.get_children(): self.tree.delete(i)
            fd = _normalize_expense_date(self.from_ent.get().strip())
            td = _normalize_expense_date(self.to_ent.get().strip())
            expenses = get_expenses()
            for e in reversed(expenses):
                dt = e.get("date","")[:10]
                if fd and dt < fd: continue
                if td and dt > td: continue
                amt = safe_float(e.get("amount",0))
                self.tree.insert("", tk.END, values=(
                    dt,
                    e.get("category",""),
                    e.get("staff",""),
                    e.get("description",""),
                    fmt_currency(amt),
                ))
            self._build_cards(expenses=expenses)
        except Exception as e:
            app_log(f"[expenses _load] {e}")

    def _delete(self):
        if self._rbac_denied(): return
        ref = self._selected_record_ref()
        if not ref:
            return
        idx, _record, data = ref
        if not messagebox.askyesno("Delete","Delete this expense entry?"): return
        try:
            data.pop(idx)
            save_expenses(data)
            self._load()
        except Exception as e:
            messagebox.showerror("Error", f"Could not delete: {e}")

    def _build_salary_summary(self):
        """Show per-staff salary totals for current month."""
        try:
            from datetime import date as _date
            mo = _date.today().strftime("%Y-%m")
            expenses = get_expenses()
            staff_totals = {}
            for e in expenses:
                if (e.get("date","")[:7] == mo
                        and e.get("category","") in SALARY_CATS):
                    sname = e.get("staff","") or e.get("description","") or "Unknown"
                    cat   = e.get("category","Salary")
                    key   = sname + " (" + cat + ")"
                    staff_totals[key] = staff_totals.get(key, 0) + safe_float(e.get("amount",0))
            return staff_totals
        except Exception:
            return {}

    def refresh(self):
        try:
            self._load()
        except Exception as e:
            app_log(f"[expenses refresh] {e}")
