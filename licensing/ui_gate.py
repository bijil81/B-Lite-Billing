import tkinter as tk
import os
import sys
from tkinter import messagebox
from licensing.license_manager import get_license_manager
from branding import get_app_name
from ui_responsive import fit_toplevel, make_toplevel_scrollable
from src.blite_v6.app.window_lifecycle import hide_while_building, reveal_when_ready


def _log_gate(message: str, level: str = "info"):
    try:
        from utils import app_log
        app_log(f"[licensing gate] {message}", level)
    except Exception:
        pass


class ActivationDialog(tk.Toplevel):
    def __init__(self, parent=None, blocking=False):
        super().__init__(parent)
        hide_while_building(self)
        self.title("License Activation")
        self.configure(bg="#101114")
        self.resizable(True, True)
        self.result = False
        self.manager = get_license_manager()
        self.blocking = blocking
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build()
        fit_toplevel(
            self,
            max(560, self.winfo_reqwidth()),
            max(620, self.winfo_reqheight()),
            min_width=520,
            min_height=460,
            resizable=True,
            anchor="center",
        )
        reveal_when_ready(self)
        self.grab_set()
        self.focus_force()
        self.transient(parent)

    def _build(self):
        status = self.manager.current_status()
        body, _canvas, _container = make_toplevel_scrollable(self, bg="#101114")
        wrap = tk.Frame(body, bg="#101114", padx=22, pady=18)
        wrap.pack(fill="both", expand=True)
        tk.Label(wrap, text=f"Activate {get_app_name()}", font=("Arial", 16, "bold"), bg="#101114", fg="white").pack(anchor="w")
        tk.Label(wrap, text="Offline activation only. Key is bound to this device and install.", bg="#101114", fg="#94a3b8").pack(anchor="w", pady=(4, 10))
        self.copy_msg = tk.Label(wrap, text="", bg="#101114", fg="#22c55e", justify="left")
        self._build_copy_field(wrap, "Device ID", status["device_id"], "Device ID copied")
        self._build_copy_field(wrap, "Installation ID", status["install_id"], "Installation ID copied")
        self.copy_msg.pack(anchor="w", pady=(6, 0))
        if status["activation_disabled"]:
            tk.Label(wrap, text="Activation is disabled because tamper protection was triggered.", bg="#101114", fg="#f87171").pack(anchor="w", pady=(8, 0))
        elif not status["activated"]:
            color = "#f59e0b" if status["reminder_required"] else "#fbbf24"
            tk.Label(wrap, text=f"Trial days left: {status['days_left']}", bg="#101114", fg=color, font=("Arial", 11, "bold")).pack(anchor="w", pady=(8, 0))

        tk.Label(wrap, text="Activation Key", bg="#101114", fg="white").pack(anchor="w", pady=(14, 4))
        self.activation_var = tk.StringVar()
        entry = tk.Entry(wrap, textvariable=self.activation_var, show="*", width=40, font=("Consolas", 12))
        entry.pack(fill="x", ipady=5)
        self._bind_entry_shortcuts(entry, allow_paste=True)
        entry.focus_set()

        if status.get("extension_available") and not status["activated"]:
            tk.Label(wrap, text="Trial Extension Key", bg="#101114", fg="white").pack(anchor="w", pady=(12, 4))
            self.extension_var = tk.StringVar()
            extension_entry = tk.Entry(wrap, textvariable=self.extension_var, show="*", width=40, font=("Consolas", 12))
            extension_entry.pack(fill="x", ipady=5)
            self._bind_entry_shortcuts(extension_entry, allow_paste=True)
        else:
            self.extension_var = None

        self.msg = tk.Label(wrap, text="", bg="#101114", fg="#f87171", justify="left", wraplength=500)
        self.msg.pack(anchor="w", pady=(10, 0))

        actions = tk.Frame(wrap, bg="#101114")
        actions.pack(fill="x", pady=(14, 0))
        tk.Button(actions, text="Activate", command=self._activate, bg="#2563eb", fg="white", activebackground="#1d4ed8").pack(side="left")
        if self.extension_var is not None:
            tk.Button(actions, text="Extend Trial", command=self._extend, bg="#16a34a", fg="white", activebackground="#15803d").pack(side="left", padx=(8, 0))
        if not self.blocking:
            tk.Button(actions, text="Close", command=self._on_close).pack(side="right")

    def _build_copy_field(self, parent, label_text, value, success_message):
        tk.Label(parent, text=label_text, bg="#101114", fg="white").pack(anchor="w", pady=(0, 4))
        row = tk.Frame(parent, bg="#101114")
        row.pack(fill="x", pady=(0, 4))
        entry = tk.Entry(
            row,
            width=40,
            font=("Consolas", 11),
            relief="flat",
            bd=1,
            readonlybackground="#1f2937",
            fg="#e2e8f0",
            insertbackground="#e2e8f0",
        )
        entry.insert(0, value)
        entry.configure(state="readonly")
        entry.pack(side="left", fill="x", expand=True, ipady=5)
        self._bind_entry_shortcuts(entry, allow_paste=False)
        tk.Button(
            row,
            text="Copy",
            command=lambda text=value, msg=success_message: self._copy_text(text, msg),
            bg="#334155",
            fg="white",
            activebackground="#475569",
        ).pack(side="left", padx=(8, 0))

    def _bind_entry_shortcuts(self, entry, allow_paste):
        entry.bind("<Control-c>", self._copy_selection, add="+")
        entry.bind("<Control-C>", self._copy_selection, add="+")
        entry.bind("<Double-Button-1>", self._select_all, add="+")
        entry.bind("<Button-3>", lambda event, widget=entry: self._show_context_menu(event, widget, allow_paste), add="+")

    def _copy_selection(self, event=None):
        widget = getattr(event, "widget", None)
        if widget is None:
            return "break"
        try:
            text = widget.selection_get()
        except Exception:
            text = widget.get()
        return self._copy_text(text)

    def _copy_text(self, text, message=None):
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update_idletasks()
        except Exception:
            self.msg.configure(text="Clipboard copy failed. Please copy manually.")
            return "break"
        self.msg.configure(text="")
        if message:
            self._show_copy_message(message)
        return "break"

    def _show_copy_message(self, text):
        self.copy_msg.configure(text=text)
        if hasattr(self, "_copy_after_id") and self._copy_after_id:
            self.after_cancel(self._copy_after_id)
        self._copy_after_id = self.after(1800, lambda: self.copy_msg.configure(text=""))

    def _select_all(self, event=None):
        widget = getattr(event, "widget", None)
        if widget is None:
            return "break"
        widget.focus_set()
        widget.selection_range(0, "end")
        widget.icursor("end")
        return "break"

    def _paste_into_entry(self, widget):
        try:
            pasted = self.clipboard_get()
        except Exception:
            return
        if not pasted:
            return
        try:
            if widget.selection_present():
                start = widget.index("sel.first")
                end = widget.index("sel.last")
                widget.delete(start, end)
                widget.insert(start, pasted)
            else:
                widget.insert(widget.index("insert"), pasted)
        except Exception:
            pass

    def _show_context_menu(self, event, widget, allow_paste):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Copy", command=lambda: self._copy_text(widget.selection_get() if widget.selection_present() else widget.get()))
        menu.add_command(label="Select All", command=lambda: self._select_all_from_widget(widget))
        if allow_paste:
            menu.add_command(label="Paste", command=lambda: self._paste_into_entry(widget))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
        return "break"

    def _select_all_from_widget(self, widget):
        widget.focus_set()
        widget.selection_range(0, "end")
        widget.icursor("end")

    def _activate(self):
        ok, reason = self.manager.apply_activation_key(self.activation_var.get().strip())
        if ok:
            self.result = True
            messagebox.showinfo("Activation", "License activated successfully.")
            self.destroy()
            return
        self.msg.configure(text=self._friendly(reason))

    def _extend(self):
        ok, reason = self.manager.apply_trial_extension_key(self.extension_var.get().strip())
        if ok:
            self.result = True
            messagebox.showinfo("Trial Extended", "Trial extended successfully.")
            self.destroy()
            return
        self.msg.configure(text=self._friendly(reason))

    def _friendly(self, reason):
        mapping = {
            "invalid_key": "Invalid key format.",
            "invalid_checksum": "Key checksum is invalid.",
            "invalid_type": "Unknown key type.",
            "wrong_key_type": "This key is for a different operation.",
            "device_or_install_mismatch": "Key does not belong to this system.",
            "already_extended": "Trial was already extended once.",
            "activation_disabled": "Activation is disabled because tamper protection was triggered.",
        }
        return mapping.get(reason, reason)

    def _on_close(self):
        if self.blocking:
            self.result = False
        self.destroy()


def _resolve_dialog_parent(parent=None):
    if parent is not None:
        return parent, None
    root = getattr(tk, "_default_root", None)
    try:
        if root is not None and int(root.winfo_exists()):
            return root, None
    except Exception:
        pass
    temp_root = tk.Tk()
    hide_while_building(temp_root)
    return temp_root, temp_root


def _call_messagebox(kind: str, title: str, message: str, parent=None):
    dialog_parent, owned_root = _resolve_dialog_parent(parent)
    try:
        fn = getattr(messagebox, kind)
        return fn(title, message, parent=dialog_parent)
    finally:
        if owned_root is not None:
            try:
                owned_root.destroy()
            except Exception:
                pass


def open_activation_dialog(parent=None, blocking=False):
    dialog_parent, owned_root = _resolve_dialog_parent(parent)
    try:
        _log_gate(f"opening activation dialog (blocking={blocking})", "info")
        dlg = ActivationDialog(parent=dialog_parent, blocking=blocking)
        dlg.wait_window()
        _log_gate(f"activation dialog closed result={dlg.result}", "info")
        return dlg.result
    finally:
        if owned_root is not None:
            try:
                owned_root.destroy()
            except Exception:
                pass


def _source_license_bypass_enabled() -> bool:
    if getattr(sys, "frozen", False):
        return False
    if os.environ.get("BLITE_V6_FORCE_LICENSE", "0") == "1":
        return False
    try:
        from salon_settings import get_settings
        return not bool(get_settings().get("licensing_enforcement_enabled", False))
    except Exception:
        return True


def ensure_startup_access():
    try:
        if _source_license_bypass_enabled():
            _log_gate("source/manual smoke mode: licensing enforcement deferred", "warning")
            return True
        manager = get_license_manager()
        manager.register_startup()
        status = manager.current_status()
        _log_gate(
            "status "
            f"activated={status.get('activated')} "
            f"expired={status.get('expired')} "
            f"days_left={status.get('days_left')} "
            f"date_tamper={status.get('date_tamper_detected')} "
            f"code_tamper={status.get('code_tamper_detected')}",
            "info",
        )
        if status["date_tamper_detected"]:
            _call_messagebox("showerror", "License Error", "System date rollback detected. App is blocked.")
            return False
        if status["code_tamper_detected"]:
            _call_messagebox("showerror", "License Error", "Critical files were modified. Activation is disabled.")
            return False
        if status["activated"]:
            return True
        if status["expired"]:
            _log_gate("trial/license expired, forcing activation dialog", "warning")
            return open_activation_dialog(blocking=True)
        if status["reminder_required"]:
            should_open = _call_messagebox(
                "askyesno",
                "Trial Reminder",
                f"Trial ends in {status['days_left']} day(s). Open activation now?",
            )
            if should_open:
                open_activation_dialog(blocking=False)
        return True
    except Exception as exc:
        _log_gate(f"startup access failure: {exc}", "error")
        try:
            return open_activation_dialog(blocking=True)
        except Exception as dlg_exc:
            _log_gate(f"activation fallback failed: {dlg_exc}", "error")
            _call_messagebox(
                "showerror",
                "License Error",
                "The app could not complete the license check.\n\nPlease restart the app.",
            )
            return False
