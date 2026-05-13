"""
void_invoice_dialog.py  —  B-Lite Billing v6
Secure UI dialog for voiding an invoice.

Safety features:
  - User must type "VOID" (exact, uppercase) to enable the Confirm button.
  - Reason field is mandatory.
  - Shows full bill preview before confirmation.
  - Calls invoice_void_service.void_invoice() atomically.
"""

import tkinter as tk
from tkinter import messagebox
from utils import C, fmt_currency, app_log


def open_void_dialog(root: tk.Misc, app=None) -> None:
    """
    Open the Void Invoice dialog.

    Args:
        root: Parent Tkinter widget (or root window).
        app:  Application instance (used to retrieve current_user).
    """
    current_user = "admin"
    if app and hasattr(app, "current_user") and isinstance(app.current_user, dict):
        current_user = app.current_user.get("username", "admin")

    dlg = _VoidInvoiceDialog(root, current_user=current_user)
    dlg.grab_set()
    root.wait_window(dlg)


class _VoidInvoiceDialog(tk.Toplevel):
    """Internal dialog window — do not instantiate directly, use open_void_dialog()."""

    def __init__(self, parent: tk.Misc, current_user: str = "admin"):
        super().__init__(parent)
        self._user      = current_user
        self._preview   = None   # dict from get_invoice_preview()

        self.title("Void Invoice  |  B-Lite Billing")
        self.resizable(False, False)
        self.configure(bg=C["bg"])

        # Center dialog
        self.update_idletasks()
        w, h = 560, 580
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w)//2}+{(sh - h)//2}")

        self._build()

    # ─── Build UI ────────────────────────────────────────────────

    def _build(self):
        # Header
        hdr = tk.Frame(self, bg="#c0392b", padx=18, pady=12)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="⊘  Void Invoice",
                 font=("Segoe UI", 14, "bold"),
                 bg="#c0392b", fg="white").pack(side=tk.LEFT)
        tk.Label(hdr, text="This action is permanent and logged.",
                 font=("Segoe UI", 10),
                 bg="#c0392b", fg="#f5b7b1").pack(side=tk.RIGHT, padx=4)

        body = tk.Frame(self, bg=C["bg"], padx=18, pady=14)
        body.pack(fill=tk.BOTH, expand=True)

        # ── Invoice lookup ──────────────────────────────────────
        lookup_card = tk.Frame(body, bg=C["card"], padx=14, pady=12)
        lookup_card.pack(fill=tk.X, pady=(0, 10))

        tk.Label(lookup_card, text="Invoice Number",
                 font=("Segoe UI", 10, "bold"),
                 bg=C["card"], fg=C["muted"]).pack(anchor="w")

        row_lookup = tk.Frame(lookup_card, bg=C["card"])
        row_lookup.pack(fill=tk.X, pady=(4, 0))

        self._inv_var = tk.StringVar()
        inv_entry = tk.Entry(row_lookup, textvariable=self._inv_var,
                             font=("Segoe UI", 12), bg=C["input"],
                             fg=C["text"], bd=0, insertbackground=C["text"],
                             width=28)
        inv_entry.pack(side=tk.LEFT, ipady=6, padx=(0, 8))
        inv_entry.focus_set()
        inv_entry.bind("<Return>", lambda e: self._fetch_preview())

        self._lookup_btn = tk.Button(row_lookup, text="Look Up",
                                     font=("Segoe UI", 10, "bold"),
                                     bg=C["blue"], fg="white",
                                     relief=tk.FLAT, padx=12, pady=6,
                                     cursor="hand2",
                                     command=self._fetch_preview)
        self._lookup_btn.pack(side=tk.LEFT)

        # ── Preview area ────────────────────────────────────────
        prev_frame = tk.Frame(body, bg=C["card"], padx=14, pady=10)
        prev_frame.pack(fill=tk.X, pady=(0, 10))
        tk.Label(prev_frame, text="Invoice Preview",
                 font=("Segoe UI", 10, "bold"),
                 bg=C["card"], fg=C["muted"]).pack(anchor="w")

        self._preview_text = tk.Text(prev_frame, height=9,
                                     font=("Courier New", 10),
                                     bg="#f8f9fa", fg="#2d3436",
                                     bd=0, padx=8, pady=6,
                                     state="disabled", wrap="none")
        self._preview_text.pack(fill=tk.X, pady=(4, 0))
        self._set_preview_text("Enter an invoice number above and click Look Up.")

        # ── Reason ─────────────────────────────────────────────
        reason_card = tk.Frame(body, bg=C["card"], padx=14, pady=10)
        reason_card.pack(fill=tk.X, pady=(0, 10))
        tk.Label(reason_card, text="Void Reason  (mandatory)",
                 font=("Segoe UI", 10, "bold"),
                 bg=C["card"], fg=C["muted"]).pack(anchor="w")
        self._reason_var = tk.StringVar()
        self._reason_var.trace_add("write", lambda *_: self._update_confirm_state())
        tk.Entry(reason_card, textvariable=self._reason_var,
                 font=("Segoe UI", 11), bg=C["input"],
                 fg=C["text"], bd=0, insertbackground=C["text"],
                 width=52).pack(fill=tk.X, ipady=6, pady=(4, 0))

        # ── Safety confirmation ─────────────────────────────────
        safety_card = tk.Frame(body, bg="#fef9e7", padx=14, pady=10,
                               highlightthickness=1,
                               highlightbackground="#f39c12")
        safety_card.pack(fill=tk.X, pady=(0, 12))
        tk.Label(safety_card,
                 text='⚠  Type  VOID  below (exactly) to enable the confirm button.',
                 font=("Segoe UI", 10, "bold"),
                 bg="#fef9e7", fg="#b7950b").pack(anchor="w")
        self._confirm_var = tk.StringVar()
        self._confirm_var.trace_add("write", lambda *_: self._update_confirm_state())
        tk.Entry(safety_card, textvariable=self._confirm_var,
                 font=("Segoe UI", 12, "bold"), bg="white",
                 fg="#c0392b", bd=1, relief=tk.SOLID, width=12,
                 insertbackground="#c0392b").pack(anchor="w", ipady=5, pady=(5, 0))

        # ── Action buttons ──────────────────────────────────────
        btn_row = tk.Frame(body, bg=C["bg"])
        btn_row.pack(fill=tk.X)

        tk.Button(btn_row, text="Cancel",
                  font=("Segoe UI", 10), bg=C["card"],
                  fg=C["muted"], relief=tk.FLAT, padx=16, pady=8,
                  cursor="hand2", command=self.destroy).pack(side=tk.RIGHT, padx=(6, 0))

        self._confirm_btn = tk.Button(btn_row, text="✔  Confirm VOID",
                                      font=("Segoe UI", 10, "bold"),
                                      bg="#7f8c8d", fg="white",
                                      relief=tk.FLAT, padx=16, pady=8,
                                      cursor="hand2", state="disabled",
                                      command=self._execute_void)
        self._confirm_btn.pack(side=tk.RIGHT)

    # ─── Logic ───────────────────────────────────────────────────

    def _set_preview_text(self, text: str):
        self._preview_text.config(state="normal")
        self._preview_text.delete("1.0", tk.END)
        self._preview_text.insert(tk.END, text)
        self._preview_text.config(state="disabled")

    def _fetch_preview(self):
        inv = self._inv_var.get().strip()
        if not inv:
            messagebox.showwarning("Missing", "Please enter an invoice number.", parent=self)
            return
        try:
            from src.blite_v6.billing.invoice_void_service import get_invoice_preview, VoidError
            data = get_invoice_preview(inv)
            self._preview = data
            self._set_preview_text(self._format_preview(data))
        except Exception as e:
            self._preview = None
            self._set_preview_text(f"⚠  {e}")
        self._update_confirm_state()

    def _format_preview(self, d: dict) -> str:
        lines = [
            f"Invoice  : {d['invoice']}",
            f"Date     : {d['date']}",
            f"Customer : {d['customer']}  (Ph: {d['phone']})",
            f"Payment  : {d['payment']}",
            f"Discount : {fmt_currency(d['discount'])}",
            f"Total    : {fmt_currency(d['total'])}",
        ]
        if d.get("is_voided"):
            lines.append("")
            lines.append(f"⚠  Already VOID  (by {d['void_by']} on {d['void_at']})")
            lines.append(f"   Reason: {d['void_reason']}")
        elif d.get("items"):
            lines.append("")
            lines.append("Items:")
            for item in d["items"][:8]:
                name = item.get("name", "?")
                qty  = item.get("qty", "")
                price= item.get("price", "")
                lines.append(f"  • {name}  x{qty}  @ {price}")
        return "\n".join(lines)

    def _update_confirm_state(self):
        typed   = self._confirm_var.get()
        reason  = self._reason_var.get().strip()
        valid   = (
            self._preview is not None
            and not self._preview.get("is_voided")
            and typed == "VOID"
            and reason != ""
        )
        self._confirm_btn.config(
            state="normal" if valid else "disabled",
            bg="#c0392b" if valid else "#7f8c8d",
        )

    def _execute_void(self):
        inv    = self._inv_var.get().strip()
        reason = self._reason_var.get().strip()
        if not messagebox.askyesno(
            "Final Confirmation",
            f"Permanently VOID invoice  {inv}?\n\n"
            f"Reason: {reason}\n\n"
            "This action is audited and cannot be undone from the UI.",
            parent=self
        ):
            return

        try:
            from src.blite_v6.billing.invoice_void_service import void_invoice, VoidError
            result = void_invoice(inv, reason, self._user)
            messagebox.showinfo(
                "Invoice Voided",
                f"✔  Invoice {result['invoice']} has been voided.\n"
                f"Customer : {result['customer']}\n"
                f"Total    : {fmt_currency(result['total'])}\n"
                f"Products with stock restored: {result['items_restored']}",
                parent=self
            )
            self.destroy()
        except Exception as e:
            app_log(f"[void_dialog] Error: {e}")
            messagebox.showerror("Void Failed", str(e), parent=self)
