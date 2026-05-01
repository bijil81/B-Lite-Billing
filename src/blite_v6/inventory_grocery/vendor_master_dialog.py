"""Vendor master dialog for purchase workflow."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from ui_theme import ModernButton
from utils import C, fmt_currency, popup_window, app_log
from src.blite_v6.app.window_lifecycle import hide_while_building, reveal_when_ready
from src.blite_v6.inventory_grocery.vendor_service import VendorService


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def open_vendor_master_dialog(parent, *, on_change=None, vendor_id: int | None = None):
    svc = VendorService()
    win = tk.Toplevel(parent)
    hide_while_building(win)
    win.title("Vendor Master")
    popup_window(win, 1240, 780)
    win.configure(bg=C["bg"])
    try:
        win.minsize(1120, 680)
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
    tk.Label(hdr, text="Vendor Master", bg=C["sidebar"], fg=C["text"], font=("Arial", 14, "bold")).pack(anchor="w")
    tk.Label(
        hdr,
        text="Add, edit, deactivate vendors and review recent purchase totals.",
        bg=C["sidebar"],
        fg=C["muted"],
        font=("Arial", 10),
    ).pack(anchor="w", pady=(2, 0))

    from ui_responsive import make_scrollable
    body, canvas, inner = make_scrollable(win, bg=C["bg"], padx=16, pady=12)

    def _scroll(event):
        try:
            step = -1 if int(getattr(event, "delta", 0) or 0) > 0 else 1
            canvas.yview_scroll(step, "units")
            return "break"
        except Exception:
            return None

    def _bind_scroll(widget):
        try:
            widget.bind("<MouseWheel>", _scroll, add="+")
        except Exception:
            pass

    top = tk.Frame(body, bg=C["bg"])
    top.pack(fill=tk.X)
    left = tk.Frame(top, bg=C["bg"])
    left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    right = tk.Frame(top, bg=C["bg"], width=360)
    right.pack(side=tk.LEFT, fill=tk.Y, padx=(12, 0))
    right.pack_propagate(False)

    filter_row = tk.Frame(left, bg=C["bg"])
    filter_row.pack(fill=tk.X, pady=(0, 8))
    tk.Label(filter_row, text="Search:", bg=C["bg"], fg=C["muted"], font=("Arial", 10)).pack(side=tk.LEFT)
    search_var = tk.StringVar()
    search_ent = tk.Entry(filter_row, textvariable=search_var, bg=C["input"], fg=C["text"], bd=0, font=("Arial", 11))
    search_ent.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0), ipady=4)
    _bind_scroll(search_ent)

    show_inactive = tk.BooleanVar(value=False)
    tk.Checkbutton(
        filter_row,
        text="Show inactive",
        variable=show_inactive,
        bg=C["bg"],
        fg=C["text"],
        selectcolor=C["input"],
        activebackground=C["bg"],
        activeforeground=C["text"],
        command=lambda: _refresh(),
    ).pack(side=tk.LEFT, padx=(10, 0))

    columns = ("Vendor", "Phone", "GSTIN", "Opening", "Purchases", "Last Purchase", "Active")
    tree_wrap = tk.Frame(left, bg=C["bg"])
    tree_wrap.pack(fill=tk.BOTH, expand=True)
    tree = ttk.Treeview(tree_wrap, columns=columns, show="headings", height=14)
    for col in columns:
        tree.heading(col, text=col)
    tree.column("Vendor", width=190, minwidth=120)
    tree.column("Phone", width=110, minwidth=80)
    tree.column("GSTIN", width=150, minwidth=100)
    tree.column("Opening", width=80, minwidth=70, anchor="e")
    tree.column("Purchases", width=80, minwidth=70, anchor="e")
    tree.column("Last Purchase", width=110, minwidth=90)
    tree.column("Active", width=70, minwidth=50, anchor="center")
    tree.pack(fill=tk.BOTH, expand=True)
    tree_scroll = ttk.Scrollbar(tree_wrap, orient="vertical", command=tree.yview)
    tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    tree.configure(yscrollcommand=tree_scroll.set)

    form = tk.Frame(right, bg=C["card"], padx=14, pady=14)
    form.pack(fill=tk.BOTH, expand=True)
    tk.Label(form, text="Vendor Details", bg=C["card"], fg=C["text"], font=("Arial", 12, "bold")).pack(anchor="w")

    vendor_state = {
        "vendor_id": 0,
    }

    def _field(label: str, default: str = ""):
        row = tk.Frame(form, bg=C["card"])
        row.pack(fill=tk.X, pady=4)
        tk.Label(row, text=label, bg=C["card"], fg=C["muted"], font=("Arial", 10)).pack(anchor="w")
        ent = tk.Entry(row, bg=C["input"], fg=C["text"], bd=0, font=("Arial", 11))
        ent.pack(fill=tk.X, ipady=4)
        ent.insert(0, default)
        _bind_scroll(ent)
        return ent

    name_ent = _field("Name")
    phone_ent = _field("Phone")
    gstin_ent = _field("GSTIN")
    addr_ent = _field("Address")
    ob_ent = _field("Opening Balance", "0")

    active_var = tk.BooleanVar(value=True)
    tk.Checkbutton(
        form,
        text="Active",
        variable=active_var,
        bg=C["card"],
        fg=C["text"],
        selectcolor=C["input"],
        activebackground=C["card"],
        activeforeground=C["text"],
    ).pack(anchor="w", pady=(8, 0))

    summary_lbl = tk.Label(form, text="", bg=C["card"], fg=C["muted"], justify="left", wraplength=420)
    summary_lbl.pack(fill=tk.X, pady=(12, 0))

    btns = tk.Frame(form, bg=C["card"])
    btns.pack(fill=tk.X, pady=(14, 0))

    def _clear():
        vendor_state["vendor_id"] = 0
        for widget, value in (
            (name_ent, ""),
            (phone_ent, ""),
            (gstin_ent, ""),
            (addr_ent, ""),
            (ob_ent, "0"),
        ):
            widget.delete(0, tk.END)
            widget.insert(0, value)
        active_var.set(True)
        summary_lbl.config(text="")

    def _row_from_tree(item_id: str) -> dict:
        values = tree.item(item_id, "values")
        if not values:
            return {}
        return {
            "name": values[0],
            "phone": values[1],
            "gstin": values[2],
            "opening_balance": values[3],
            "purchase_count": values[4],
            "last_purchase_date": values[5],
            "active": values[6],
        }

    def _select(event=None):
        sel = tree.selection()
        if not sel:
            return
        try:
            source = _current_rows.get(sel[0], {})
            vendor_state["vendor_id"] = int(source.get("id") or 0)
            name_ent.delete(0, tk.END)
            name_ent.insert(0, source.get("name", ""))
            phone_ent.delete(0, tk.END)
            phone_ent.insert(0, source.get("phone", ""))
            gstin_ent.delete(0, tk.END)
            gstin_ent.insert(0, source.get("gstin", ""))
            addr_ent.delete(0, tk.END)
            addr_ent.insert(0, source.get("address", ""))
            ob_ent.delete(0, tk.END)
            ob_ent.insert(0, f"{_safe_float(source.get('opening_balance', 0.0)):.2f}".rstrip("0").rstrip("."))
            active_var.set(bool(int(source.get("active", 1) or 0)))
            summary_lbl.config(
                text=(
                    f"Purchases: {source.get('purchase_count', 0)}\n"
                    f"Total spent: {fmt_currency(source.get('total_purchase', 0))}\n"
                    f"Last invoice: {source.get('last_invoice_no', '')} ({source.get('last_purchase_date', '')})"
                )
            )
        except Exception as exc:
            app_log(f"[vendor select] {exc}")

    tree.bind("<<TreeviewSelect>>", _select)
    tree.bind("<Double-1>", _select)

    _current_rows: dict[str, dict] = {}

    def _refresh():
        for row_id in tree.get_children():
            tree.delete(row_id)
        _current_rows.clear()
        q = search_var.get().strip().lower()
        try:
            rows = svc.list_vendors(active_only=not show_inactive.get())
        except Exception as exc:
            app_log(f"[vendor master refresh] {exc}")
            rows = []
        for row in rows:
            name = str(row.get("name", "")).strip()
            if q and q not in name.lower() and q not in str(row.get("phone", "")).lower() and q not in str(row.get("gstin", "")).lower():
                continue
            item_id = tree.insert(
                "",
                tk.END,
                values=(
                    name,
                    row.get("phone", ""),
                    row.get("gstin", ""),
                    fmt_currency(row.get("opening_balance", 0)),
                    int(row.get("purchase_count", 0) or 0),
                    row.get("last_purchase_date", ""),
                    "Yes" if int(row.get("active", 1) or 0) else "No",
                ),
            )
            _current_rows[item_id] = row

    def _save():
        payload = {
            "vendor_id": vendor_state["vendor_id"],
            "name": name_ent.get(),
            "phone": phone_ent.get(),
            "gstin": gstin_ent.get(),
            "address": addr_ent.get(),
            "opening_balance": ob_ent.get(),
            "active": active_var.get(),
        }
        try:
            result = svc.save_vendor(payload)
        except Exception as exc:
            messagebox.showerror("Vendor Error", f"Could not save vendor:\n{exc}")
            return
        vendor_state["vendor_id"] = int(result.get("vendor_id") or 0)
        _refresh()
        if callable(on_change):
            try:
                on_change()
            except Exception:
                pass
        messagebox.showinfo("Saved", f"Vendor saved: {result.get('vendor_name', '')}")

    def _deactivate():
        sel = tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select a vendor first.")
            return
        row = _current_rows.get(sel[0], {})
        vendor_id = int(row.get("id") or 0)
        if not vendor_id:
            return
        if not messagebox.askyesno("Deactivate", f"Deactivate '{row.get('name', '')}'?"):
            return
        try:
            svc.deactivate_vendor(vendor_id)
        except Exception as exc:
            messagebox.showerror("Vendor Error", f"Could not deactivate vendor:\n{exc}")
            return
        if callable(on_change):
            try:
                on_change()
            except Exception:
                pass
        _refresh()

    def _open_history():
        sel = tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select a vendor first.")
            return
        row = _current_rows.get(sel[0], {})
        from src.blite_v6.inventory_grocery.purchase_history_dialog import open_purchase_history_dialog

        open_purchase_history_dialog(parent, vendor_id=int(row.get("id") or 0), vendor_name=str(row.get("name") or ""))

    ModernButton(btns, text="Save / Update", command=_save, color=C["teal"], hover_color=C["blue"], width=150, height=34, radius=8, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 6))
    ModernButton(btns, text="Deactivate", command=_deactivate, color=C["red"], hover_color="#c0392b", width=120, height=34, radius=8, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 6))
    ModernButton(btns, text="History", command=_open_history, color=C["purple"], hover_color="#6c3483", width=100, height=34, radius=8, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 6))
    ModernButton(btns, text="Clear", command=_clear, color=C["sidebar"], hover_color=C["blue"], width=90, height=34, radius=8, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 6))
    ModernButton(btns, text="Close", command=_close, color=C["sidebar"], hover_color=C["blue"], width=90, height=34, radius=8, font=("Arial", 10, "bold")).pack(side=tk.LEFT)

    search_var.trace_add("write", lambda *_: _refresh())
    _refresh()
    if vendor_id:
        for item_id, row in _current_rows.items():
            if int(row.get("id") or 0) == int(vendor_id):
                tree.selection_set(item_id)
                tree.focus(item_id)
                tree.see(item_id)
                _select()
                break
    win.after(0, lambda: _bind_scroll(win))
    reveal_when_ready(win)
