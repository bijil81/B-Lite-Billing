"""
membership.py  –  BOBY'S Salon : Membership & Packages
FIXES:
  - Bug 21: get_customer_membership() now persists expired status
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, timedelta
import os
from utils import (C, load_json, safe_float,
                   now_str, today_str, DATA_DIR, F_CUSTOMERS)
from date_helpers import iso_to_display_date
from ui_theme import apply_treeview_column_alignment, ModernButton, ensure_segoe_ttk_font
from ui_utils import make_searchable_combobox
from ui_responsive import make_scrollable
from services_v5.membership_service import MembershipService
from services_v5.customer_service import CustomerService
from src.blite_v6.app.window_lifecycle import hide_while_building, reveal_when_ready

F_MEMBERSHIPS   = os.path.join(DATA_DIR, "memberships.json")
F_PKG_TEMPLATES = os.path.join(DATA_DIR, "pkg_templates.json")

DEFAULT_TEMPLATES = [
    {"name": "Silver Package (1 Month)",    "price": 1500, "duration_days": 30,
     "discount_pct": 10, "wallet": 0,    "description": "10% off all services for 1 month", "active": True},
    {"name": "Gold Package (3 Months)",     "price": 4000, "duration_days": 90,
     "discount_pct": 15, "wallet": 0,    "description": "15% off all services for 3 months", "active": True},
    {"name": "Platinum Package (6 Months)", "price": 7000, "duration_days": 180,
     "discount_pct": 20, "wallet": 0,    "description": "20% off all services for 6 months", "active": True},
    {"name": "Diamond Package (1 Year)",    "price": 12000,"duration_days": 365,
     "discount_pct": 25, "wallet": 0,    "description": "25% off all services for 1 full year", "active": True},
    {"name": "Prepaid Wallet Rs2000",       "price": 2000, "duration_days": 365,
     "discount_pct": 0,  "wallet": 2200, "description": "Pay Rs2000 get Rs2200 wallet balance", "active": True},
    {"name": "Prepaid Wallet Rs5000",       "price": 5000, "duration_days": 365,
     "discount_pct": 0,  "wallet": 5750, "description": "Pay Rs5000 get Rs5750 wallet balance", "active": True},
    {"name": "VIP Annual Package",          "price": 15000,"duration_days": 365,
     "discount_pct": 30, "wallet": 1000, "description": "30% off + Rs1000 wallet - full year VIP", "active": True},
]

_MEMBERSHIP_SERVICE = MembershipService()
_CUSTOMER_SERVICE = CustomerService()


def get_pkg_templates() -> list:
    templates = _MEMBERSHIP_SERVICE.get_templates()
    if templates:
        return templates
    data = load_json(F_PKG_TEMPLATES, None)
    if not data:
        return DEFAULT_TEMPLATES
    return data


def save_pkg_templates(data: list) -> bool:
    _MEMBERSHIP_SERVICE.save_all_plans(data)
    return True


def get_memberships() -> dict:
    memberships = _MEMBERSHIP_SERVICE.get_all()
    if memberships:
        return memberships
    return load_json(F_MEMBERSHIPS, {})


def save_memberships(data: dict) -> bool:
    _MEMBERSHIP_SERVICE.save_all(data)
    return True


def get_customer_membership(phone: str):
    membership = _MEMBERSHIP_SERVICE.get_customer_membership(phone)
    if not membership:
        legacy = load_json(F_MEMBERSHIPS, {}).get(phone)
        membership = legacy
    if not membership:
        return None
    if membership.get("expiry", "") < today_str() and membership.get("status") != "Expired":
        membership = {**membership, "status": "Expired"}
        _MEMBERSHIP_SERVICE.save_customer_membership(
            {
                "customer_phone": phone,
                "customer_name": membership.get("customer_name", membership.get("name", "")),
                "plan_name": membership.get("package_name", membership.get("package", "")),
                "discount_pct": membership.get("discount_pct", 0.0),
                "wallet_balance": membership.get("wallet_balance", 0.0),
                "start_date": membership.get("start", ""),
                "expiry_date": membership.get("expiry", ""),
                "status": membership.get("status", "Expired"),
                "price_paid": membership.get("price_paid", 0.0),
                "payment_method": membership.get("payment", ""),
            }
        )
    return membership


def get_wallet_balance(phone: str) -> float:
    membership = get_customer_membership(phone)
    return safe_float((membership or {}).get("wallet_balance", 0))


def deduct_wallet(phone: str, amount: float) -> float:
    """Deduct from a membership wallet.

    H12 FIX: Block wallet deduction for expired/cancelled memberships.
    Previously this function did not check the membership status,
    allowing expired membership wallets to be used.
    """
    membership = get_customer_membership(phone)
    if not membership:
        return 0.0
    # Block deductions on non-active memberships
    status = membership.get("status", "Expired")
    if status != "Active":
        from utils import app_log
        app_log(f"[deduct_wallet] BLOCKED: {phone} membership status={status}")
        return 0.0
    balance = safe_float(membership.get("wallet_balance", 0))
    deduct = min(balance, amount)
    if deduct > 0:
        _MEMBERSHIP_SERVICE.adjust_wallet(phone, -deduct)
    return deduct


def _fmt_rs(value: float) -> str:
    return f"Rs{safe_float(value):,.2f}"

class MembershipFrame(tk.Frame):

    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self._build()

    def _build(self):
        ensure_segoe_ttk_font()
        hdr = tk.Frame(self, bg=C["card"], pady=10)
        hdr.pack(fill=tk.X)
        left_f = tk.Frame(hdr, bg=C["card"])
        left_f.pack(side=tk.LEFT, padx=20)
        tk.Label(left_f, text="Membership & Packages",
                 font=("Segoe UI", 15, "bold"),
                 bg=C["card"], fg=C["text"]).pack(anchor="w")
        tk.Label(left_f, text="Manage members, packages & wallet",
                 font=("Segoe UI", 10), bg=C["card"], fg=C["muted"]).pack(anchor="w")
        ModernButton(hdr, text="New Membership",
                     command=self._assign_dialog,
                     color=C["teal"], hover_color=C["blue"],
                     width=162, height=34, radius=8,
                     font=("Segoe UI", 10, "bold"),
                     ).pack(side=tk.RIGHT, padx=15, pady=6)
        tk.Frame(self, bg=C["teal"], height=2).pack(fill=tk.X)

        tab_bar = tk.Frame(self, bg=C["bg"])
        tab_bar.pack(fill=tk.X, padx=15, pady=(6, 0))

        self._mem_btn_frame = tk.Frame(tab_bar, bg=C["bg"])
        self._mem_btn_frame.pack(side=tk.RIGHT)
        for txt, clr, hclr, cmd in [
            ("Renew",      C["teal"],   C["blue"],   self._renew),
            ("Cancel",     C["orange"], "#d35400",   self._cancel_mem),
            ("Add Wallet", C["purple"], "#6c3483",   self._add_wallet),
            ("Delete",     C["red"],    "#c0392b",   self._delete_mem),
        ]:
            ModernButton(self._mem_btn_frame, text=txt, command=cmd,
                         color=clr, hover_color=hclr,
                         width=120, height=32, radius=8,
                         font=("Segoe UI", 10, "bold"),
                         ).pack(side=tk.LEFT, padx=(0, 4))

        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True, padx=15, pady=(4, 10))

        t1 = tk.Frame(nb, bg=C["bg"])
        t2 = tk.Frame(nb, bg=C["bg"])
        t3 = tk.Frame(nb, bg=C["bg"])

        nb.add(t1, text="Active Members")
        nb.add(t2, text="Package Templates")
        nb.add(t3, text="Wallet Top-up")

        def _on_tab(e):
            idx = nb.index(nb.select())
            if idx == 0:
                self._mem_btn_frame.pack(side=tk.RIGHT)
            else:
                self._mem_btn_frame.pack_forget()
        nb.bind("<<NotebookTabChanged>>", _on_tab)

        self._build_members_tab(t1)
        self._build_templates_tab(t2)
        self._build_wallet_tab(t3)

    # ── Active Members ─────────────────────────────
    def _build_members_tab(self, parent):
        cols = ("Customer", "Phone", "Package", "Discount%",
                "Wallet", "Expiry", "Status")
        self.mem_tree = ttk.Treeview(parent, columns=cols,
                                     show="headings", height=14)
        widths = [140, 110, 180, 90, 100, 110, 90]
        for col, w in zip(cols, widths):
            self.mem_tree.heading(col, text=col)
            self.mem_tree.column(col, width=w)

        apply_treeview_column_alignment(self.mem_tree)

        vsb = ttk.Scrollbar(parent, orient="vertical",
                            command=self.mem_tree.yview)
        self.mem_tree.configure(yscrollcommand=vsb.set)
        self.mem_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        vsb.pack(side=tk.LEFT, fill=tk.Y)
        self.mem_tree.bind("<Button-3>", self._show_membership_context_menu, add="+")
        self.mem_tree.bind("<ButtonRelease-3>", self._show_membership_context_menu, add="+")
        self.mem_tree.bind("<Shift-F10>", self._show_membership_context_menu, add="+")

        self._load_members()

    def _load_members(self):
        for i in self.mem_tree.get_children():
            self.mem_tree.delete(i)
        for ph, m in get_memberships().items():
            # Auto-update expired status
            if m.get("expiry", "") < today_str() and m.get("status") == "Active":
                m["status"] = "Expired"
            self.mem_tree.insert("", tk.END, values=(
                m.get("customer_name", ""),
                ph,
                m.get("package_name", ""),
                f"{m.get('discount_pct', 0)}%",
                _fmt_rs(m.get("wallet_balance", 0)),
                iso_to_display_date(m.get("expiry", "")),
                m.get("status", "Active"),
            ))

    def _assign_dialog(self):
        from utils import popup_window
        win = tk.Toplevel(self)
        hide_while_building(win)
        win.title("Assign Membership")
        popup_window(win, 560, 540)
        win.configure(bg=C["bg"])
        win.minsize(520, 460)
        win.resizable(True, True)
        win.grab_set()
        win.protocol("WM_DELETE_WINDOW",
                     lambda: (win.grab_release(), win.destroy()))

        tk.Label(win, text="Assign Membership Package",
                 font=("Segoe UI", 13, "bold"),
                 bg=C["bg"], fg=C["text"]).pack(pady=(15, 10))

        f, _canvas, _container = make_scrollable(
            win, bg=C["bg"], padx=30, pady=10)

        customers_map = _CUSTOMER_SERVICE.build_legacy_customer_map()
        customer_choices = []
        for phone, customer in customers_map.items():
            name = str(customer.get("name", "")).strip()
            if phone:
                customer_choices.append(f"{name} - {phone}" if name else phone)
        customer_choices.sort(key=str.lower)

        tk.Label(f, text="Customer:", bg=C["bg"],
                 fg=C["muted"], font=("Segoe UI", 12)).pack(anchor="w")
        customer_var = tk.StringVar()
        customer_cb = ttk.Combobox(
            f,
            textvariable=customer_var,
            values=customer_choices,
            state="normal",
            font=("Segoe UI", 10),
        )
        customer_cb.pack(fill=tk.X, pady=(3, 8))
        make_searchable_combobox(customer_cb, customer_choices)

        entries = {}
        for lbl, key, default in [
            ("Customer Name:", "name", ""),
            ("Phone:",         "phone", ""),
        ]:
            tk.Label(f, text=lbl, bg=C["bg"],
                     fg=C["muted"], font=("Segoe UI", 12)).pack(anchor="w")
            e = tk.Entry(f, font=("Segoe UI", 12), bg=C["input"],
                         fg=C["text"], bd=0, insertbackground=C["accent"])
            e.pack(fill=tk.X, ipady=6, pady=(3, 8))
            e.insert(0, default)
            entries[key] = e

        def _apply_customer_choice(event=None):
            selected = customer_var.get().strip()
            if not selected:
                return
            if " - " in selected:
                selected_name, selected_phone = selected.rsplit(" - ", 1)
            else:
                selected_name, selected_phone = "", selected
            customer = customers_map.get(selected_phone, {})
            entries["name"].delete(0, tk.END)
            entries["name"].insert(0, customer.get("name", selected_name))
            entries["phone"].delete(0, tk.END)
            entries["phone"].insert(0, selected_phone)

        customer_cb.bind("<<ComboboxSelected>>", _apply_customer_choice)

        tk.Label(f, text="Package:", bg=C["bg"],
                 fg=C["muted"], font=("Segoe UI", 12)).pack(anchor="w")
        templates = get_pkg_templates()
        pkg_names = [t["name"] for t in templates]
        pkg_var   = tk.StringVar(value=pkg_names[0] if pkg_names else "")
        pkg_cb    = ttk.Combobox(f, textvariable=pkg_var,
                                  values=pkg_names,
                                  state="readonly", font=("Segoe UI", 10))
        pkg_cb.pack(fill=tk.X, pady=(3, 8))

        tk.Label(f, text="Payment Method:", bg=C["bg"],
                 fg=C["muted"], font=("Segoe UI", 12)).pack(anchor="w")
        pay_var = tk.StringVar(value="Cash")
        pay_cb  = ttk.Combobox(f, textvariable=pay_var,
                                values=["Cash", "Card", "UPI"],
                                state="readonly", font=("Segoe UI", 10))
        pay_cb.pack(fill=tk.X, pady=(3, 8))

        def _save():
            nm  = entries["name"].get().strip()
            ph  = entries["phone"].get().strip()
            pkg = pkg_var.get()
            if not nm or not ph or not pkg:
                messagebox.showerror("Error", "Fill all fields.")
                return
            tmpl = next((t for t in templates if t["name"] == pkg), None)
            if not tmpl:
                messagebox.showerror("Error", "Invalid package.")
                return

            exp = (date.today() + timedelta(days=tmpl["duration_days"])).strftime("%Y-%m-%d")
            memberships = get_memberships()
            memberships[ph] = {
                "customer_name": nm,
                "package_name":  pkg,
                "discount_pct":  tmpl["discount_pct"],
                "wallet_balance": tmpl.get("wallet", 0),
                "start":         today_str(),
                "expiry":        exp,
                "status":        "Active",
                "price_paid":    tmpl["price"],
                "payment":       pay_var.get(),
                "created":       now_str(),
            }
            save_memberships(memberships)
            win.grab_release()
            win.destroy()
            self._load_members()
            messagebox.showinfo("Done",
                                f"{pkg} assigned to {nm}\nExpiry: {exp}")

        ModernButton(f, text="Assign Package",
                     command=_save,
                     color=C["teal"], hover_color=C["blue"],
                     width=380, height=40, radius=8,
                     font=("Segoe UI", 11, "bold"),
                     ).pack(fill=tk.X, pady=(8, 0))
        reveal_when_ready(win)

    def _get_selected_phone(self):
        sel = self.mem_tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select a membership.")
            return None
        return self.mem_tree.item(sel[0], "values")[1]

    def _show_membership_context_menu(self, event):
        row_id = self.mem_tree.identify_row(getattr(event, "y", 0))
        if not row_id:
            selection = self.mem_tree.selection()
            row_id = selection[0] if selection else self.mem_tree.focus()
        if not row_id:
            return "break"
        try:
            self.mem_tree.selection_set(row_id)
            self.mem_tree.focus(row_id)
            values = self.mem_tree.item(row_id, "values")
            if not values:
                return "break"
            self._register_membership_context_menu_callbacks()

            from shared.context_menu.constants import WidgetType
            from shared.context_menu.menu_context_factory import build_context
            from shared.context_menu.renderer import renderer_service
            from shared.context_menu_definitions.membership_context_menu import get_sections

            selected_row = {
                "row_id": row_id,
                "customer": values[0] if len(values) > 0 else "",
                "phone": values[1] if len(values) > 1 else "",
                "package": values[2] if len(values) > 2 else "",
                "discount": values[3] if len(values) > 3 else "",
                "wallet": values[4] if len(values) > 4 else "",
                "expiry": values[5] if len(values) > 5 else "",
                "status": values[6] if len(values) > 6 else "",
            }
            context = build_context(
                "membership",
                entity_type="membership",
                entity_id=selected_row["phone"],
                selected_row=selected_row,
                selection_count=1,
                user_role=self.app.current_user.get("role", "") if getattr(self.app, "current_user", None) else "",
                widget_type=WidgetType.TREEVIEW,
                widget_id="membership_active_grid",
                screen_x=event.x_root,
                screen_y=event.y_root,
                extra={"has_membership": True},
            )
            menu = renderer_service.build_menu(self, get_sections(), context)
            x_root = getattr(event, "x_root", None)
            y_root = getattr(event, "y_root", None)
            if x_root is None or y_root is None:
                x_root = self.mem_tree.winfo_rootx() + 24
                y_root = self.mem_tree.winfo_rooty() + 24
            menu.tk_popup(x_root, y_root)
            menu.grab_release()
            return "break"
        except Exception as exc:
            app_log(f"[membership context menu] {exc}")
            return "break"

    def _register_membership_context_menu_callbacks(self):
        from shared.context_menu.action_adapter import action_adapter
        from shared.context_menu.clipboard_service import clipboard_service
        from shared.context_menu_definitions.membership_context_menu import MembershipContextAction

        action_adapter.register(MembershipContextAction.RENEW, lambda _ctx, _act: self._renew())
        action_adapter.register(MembershipContextAction.CANCEL, lambda _ctx, _act: self._cancel_mem())
        action_adapter.register(MembershipContextAction.ADD_WALLET, lambda _ctx, _act: self._add_wallet())
        action_adapter.register(
            MembershipContextAction.COPY_CUSTOMER,
            lambda ctx, _act: clipboard_service.copy_text(self, ctx.selected_row.get("customer", "")),
        )
        action_adapter.register(
            MembershipContextAction.COPY_PHONE,
            lambda ctx, _act: clipboard_service.copy_text(self, ctx.selected_row.get("phone", "")),
        )
        action_adapter.register(
            MembershipContextAction.COPY_PACKAGE,
            lambda ctx, _act: clipboard_service.copy_text(self, ctx.selected_row.get("package", "")),
        )
        action_adapter.register(
            MembershipContextAction.COPY_WALLET,
            lambda ctx, _act: clipboard_service.copy_text(self, ctx.selected_row.get("wallet", "")),
        )
        action_adapter.register(MembershipContextAction.REFRESH, lambda _ctx, _act: self._load_members())
        action_adapter.register(MembershipContextAction.DELETE, lambda _ctx, _act: self._delete_mem())

    def _renew(self):
        ph = self._get_selected_phone()
        if not ph: return
        memberships = get_memberships()
        m  = memberships.get(ph)
        if not m: return
        templates = get_pkg_templates()
        tmpl = next((t for t in templates
                     if t["name"] == m.get("package_name")), None)
        if not tmpl:
            messagebox.showerror("Error", "Package template not found.")
            return
        exp = (date.today() + timedelta(
            days=tmpl["duration_days"])).strftime("%Y-%m-%d")
        m["expiry"] = exp
        m["status"] = "Active"
        m["wallet_balance"] = safe_float(m.get("wallet_balance", 0)) + \
                               tmpl.get("wallet", 0)
        memberships[ph] = m
        save_memberships(memberships)
        self._load_members()
        messagebox.showinfo("Renewed", f"Membership renewed until {exp}")

    def _cancel_mem(self):
        ph = self._get_selected_phone()
        if not ph: return
        if messagebox.askyesno("Cancel", "Cancel this membership?"):
            memberships = get_memberships()
            if ph in memberships:
                memberships[ph]["status"] = "Cancelled"
                save_memberships(memberships)
                self._load_members()

    def _delete_mem(self):
        """Permanently delete a membership record with warning."""
        ph = self._get_selected_phone()
        if not ph: return
        memberships = get_memberships()
        m = memberships.get(ph, {})
        cust_name = m.get("name", ph)
        pkg_name  = m.get("package", "")
        status    = m.get("status", "")

        # Warning message with full details
        warn_msg = (
            "PERMANENT DELETE - Cannot be undone!\n\n"
            f"Customer : {cust_name}\n"
            f"Phone    : {ph}\n"
            f"Package  : {pkg_name}\n"
            f"Status   : {status}\n\n"
            "Only this membership entry will be removed.\n"
            "Customer record, wallet & visit history are safe.\n\n"
            "Are you sure you want to delete?"
        )
        if messagebox.askyesno("Delete Membership", warn_msg,
                                icon="warning"):
            try:
                memberships.pop(ph, None)
                save_memberships(memberships)
                self._load_members()
                messagebox.showinfo("Deleted",
                                    f"Membership for '{cust_name}' deleted.")
            except Exception as e:
                messagebox.showerror("Error", f"Could not delete: {e}")

    def _add_wallet(self):
        ph = self._get_selected_phone()
        if not ph: return
        import tkinter.simpledialog as sd
        amt = sd.askfloat("Add Wallet",
                          "Amount to add (Rs):",
                          minvalue=1, maxvalue=100000)
        if amt:
            memberships = get_memberships()
            m = memberships.get(ph, {})
            m["wallet_balance"] = safe_float(
                m.get("wallet_balance", 0)) + amt
            memberships[ph] = m
            save_memberships(memberships)
            self._load_members()
            messagebox.showinfo("Done", f"Rs{amt:.0f} added to wallet.")

    # ── Package Templates ──────────────────────────
    def _build_templates_tab(self, parent):
        hdr = tk.Frame(parent, bg=C["bg"], pady=8)
        hdr.pack(fill=tk.X, padx=15)
        tk.Label(hdr, text="Manage Package Templates",
                 font=("Segoe UI", 12, "bold"),
                 bg=C["bg"], fg=C["text"]).pack(side=tk.LEFT)
        ModernButton(hdr, text="Add Template",
                     command=self._add_template,
                     color=C["teal"], hover_color=C["blue"],
                     width=138, height=32, radius=8,
                     font=("Segoe UI", 10, "bold"),
                     ).pack(side=tk.RIGHT)

        cols = ("Name", "Price", "Days", "Disc%", "Wallet", "Description")
        self.tmpl_tree = ttk.Treeview(parent, columns=cols,
                                      show="headings", height=12)
        widths = [180, 80, 60, 60, 80, 300]
        for col, w in zip(cols, widths):
            self.tmpl_tree.heading(col, text=col)
            self.tmpl_tree.column(col, width=w)

        apply_treeview_column_alignment(self.tmpl_tree)
        vsb = ttk.Scrollbar(parent, orient="vertical",
                            command=self.tmpl_tree.yview)
        self.tmpl_tree.configure(yscrollcommand=vsb.set)
        self.tmpl_tree.pack(fill=tk.BOTH, expand=True,
                            padx=15, side=tk.LEFT)
        vsb.pack(side=tk.LEFT, fill=tk.Y, pady=(0, 10), padx=(0, 15))

        bb = tk.Frame(parent, bg=C["bg"])
        bb.pack(fill=tk.X, padx=15, side=tk.BOTTOM, pady=8)
        ModernButton(bb, text="Delete Template",
                     command=self._del_template,
                     color=C["red"], hover_color="#c0392b",
                     width=160, height=36, radius=8,
                     font=("Segoe UI", 10, "bold"),
                     ).pack(side=tk.LEFT)
        self._load_templates()

    def _load_templates(self):
        for i in self.tmpl_tree.get_children():
            self.tmpl_tree.delete(i)
        for t in get_pkg_templates():
            self.tmpl_tree.insert("", tk.END, values=(
                t["name"], f"Rs{t['price']}", t["duration_days"],
                f"{t['discount_pct']}%", _fmt_rs(t.get("wallet", 0)),
                t.get("description", ""),
            ))

    def _add_template(self):
        from utils import popup_window
        win = tk.Toplevel(self)
        hide_while_building(win)
        win.title("Add Package Template")
        popup_window(win, 500, 420)
        win.configure(bg=C["bg"])
        win.minsize(460, 380)
        win.resizable(True, True)
        win.grab_set()
        win.protocol("WM_DELETE_WINDOW",
                     lambda: (win.grab_release(), win.destroy()))

        tk.Label(win, text="Add Package Template",
                 font=("Segoe UI", 13, "bold"),
                 bg=C["bg"], fg=C["text"]).pack(pady=(15, 10))

        f, _canvas, _container = make_scrollable(
            win, bg=C["bg"], padx=30, pady=10)

        entries = {}
        for lbl, key, default in [
            ("Package Name:", "name",         ""),
            ("Price (Rs):",    "price",        ""),
            ("Duration (days):", "duration",  "30"),
            ("Discount %:",   "discount_pct", "0"),
            ("Wallet (Rs):",   "wallet",       "0"),
            ("Description:",  "description",  ""),
        ]:
            tk.Label(f, text=lbl, bg=C["bg"],
                     fg=C["muted"], font=("Segoe UI", 12)).pack(anchor="w")
            e = tk.Entry(f, font=("Segoe UI", 12), bg=C["input"],
                         fg=C["text"], bd=0, insertbackground=C["accent"])
            e.pack(fill=tk.X, ipady=5, pady=(3, 6))
            e.insert(0, default)
            entries[key] = e

        def _save():
            try:
                t = {
                    "name":         entries["name"].get().strip(),
                    "price":        float(entries["price"].get()),
                    "duration_days":int(entries["duration"].get()),
                    "discount_pct": float(entries["discount_pct"].get()),
                    "wallet":       float(entries["wallet"].get()),
                    "description":  entries["description"].get().strip(),
                }
            except ValueError:
                messagebox.showerror("Error", "Check numeric fields.")
                return
            if not t["name"]:
                messagebox.showerror("Error", "Name required.")
                return
            templates = get_pkg_templates()
            templates.append(t)
            save_pkg_templates(templates)
            win.grab_release()
            win.destroy()
            self._load_templates()

        ModernButton(f, text="Save Template",
                     command=_save,
                     color=C["teal"], hover_color=C["blue"],
                     width=380, height=38, radius=8,
                     font=("Segoe UI", 11, "bold"),
                     ).pack(fill=tk.X, pady=(8, 0))
        reveal_when_ready(win)

    def _del_template(self):
        sel = self.tmpl_tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select a template.")
            return
        name = self.tmpl_tree.item(sel[0], "values")[0]
        if messagebox.askyesno("Delete", f"Delete '{name}'?"):
            templates = [t for t in get_pkg_templates()
                         if t["name"] != name]
            save_pkg_templates(templates)
            self._load_templates()

    # ── Wallet Top-up ──────────────────────────────
    def _build_wallet_tab(self, parent):
        f = tk.Frame(parent, bg=C["bg"], padx=30, pady=20)
        f.pack(fill=tk.BOTH, expand=True)

        tk.Label(f, text="Wallet Top-up",
                 font=("Segoe UI", 13, "bold"),
                 bg=C["bg"], fg=C["text"]).pack(anchor="w", pady=(0, 15))

        entries = {}
        for lbl, key in [("Phone:", "phone"), ("Amount (Rs):", "amount")]:
            tk.Label(f, text=lbl, bg=C["bg"],
                     fg=C["muted"], font=("Segoe UI", 12)).pack(anchor="w")
            e = tk.Entry(f, font=("Segoe UI", 12), bg=C["input"],
                         fg=C["text"], bd=0, insertbackground=C["accent"])
            e.pack(fill=tk.X, ipady=6, pady=(3, 10))
            entries[key] = e

        self.wallet_info = tk.Label(f, text="",
                                    bg=C["bg"], fg=C["gold"],
                                    font=("Segoe UI", 11))
        self.wallet_info.pack(anchor="w")

        def _lookup(*a):
            ph = entries["phone"].get().strip()
            m  = get_customer_membership(ph)
            if m:
                bal = safe_float(m.get("wallet_balance", 0))
                self.wallet_info.config(
                    text=f"Current wallet: {_fmt_rs(bal)}"
                         f"  |  {m.get('package_name', '')}"
                         f"  |  {m.get('status', '')}")
            else:
                self.wallet_info.config(text="No membership found.")

        entries["phone"].bind("<FocusOut>", _lookup)

        def _topup():
            ph  = entries["phone"].get().strip()
            try:
                amt = float(entries["amount"].get())
            except ValueError:
                messagebox.showerror("Error", "Enter valid amount.")
                return
            if amt <= 0:
                messagebox.showerror("Error", "Amount must be > 0.")
                return
            memberships = get_memberships()
            m = memberships.get(ph)
            if not m:
                messagebox.showerror("Error", "No membership found.")
                return
            m["wallet_balance"] = safe_float(
                m.get("wallet_balance", 0)) + amt
            memberships[ph] = m
            save_memberships(memberships)
            _lookup()
            messagebox.showinfo("Done", f"Rs{amt:.0f} added to wallet.")

        ModernButton(f, text="Top-up Wallet",
                     command=_topup,
                     color=C["teal"], hover_color=C["blue"],
                     width=380, height=40, radius=8,
                     font=("Segoe UI", 11, "bold"),
                     ).pack(fill=tk.X, pady=15)

    def refresh(self):
        self._load_members()


