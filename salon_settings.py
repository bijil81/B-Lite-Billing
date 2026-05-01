"""
salon_settings.py  -  B-Lite Management Settings
Tabs: Shop Info | Theme | Bill & GST | Print Size | Security | Preferences | Notifications

FIX (critical):
  self._tabs[key] = f was INSIDE the except block and OUTSIDE the for-loop.
  Result: self._tabs was never populated â†’ every _tab_*() call raised KeyError.
  Fix: moved self._tabs[key] = f to INSIDE the for-loop, where it belongs.
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os, sys
from utils import C, hash_pw, app_log
from auth_security import verify_password
from ui_theme import ModernButton
from icon_system import get_section_icon, get_action_icon
from licensing.ui_gate import open_activation_dialog
from licensing.license_manager import get_license_manager
from secure_store import (
    KEYRING_AVAILABLE,
    get_keyring_warning,
    load_ai_api_key,
    store_ai_api_key,
    load_multibranch_api_key,
    load_whatsapp_provider_secret,
    store_multibranch_api_key,
    store_whatsapp_provider_secret,
)
from whatsapp_api.provider_factory import create_provider
from multibranch.sync_manager import MultiBranchSyncManager
from ui_responsive import get_responsive_metrics, scaled_value
from src.blite_v6.settings.bill_gst import (
    bill_gst_saved_message,
    build_bill_gst_payload,
    GST_RATE_SOURCE_LABELS,
    MISSING_ITEM_GST_POLICY_LABELS,
)
from src.blite_v6.settings.core import (
    DEFAULTS,
    F_SETTINGS,
    _invalidate_settings_cache,
    feature_enabled,
    get_current_theme,
    get_settings,
    save_settings,
)
from src.blite_v6.settings.gst_classification_master import (
    CLASSIFICATION_FIELDS,
    CLASSIFICATION_MODES,
    build_gst_classification_payload,
    gst_classification_saved_message,
    normalize_gst_classification_rules,
)
from src.blite_v6.settings.gst_master import normalize_gst_category_rate_map
from src.blite_v6.settings.print_settings import (
    build_print_preview_text,
    build_print_settings_payload,
    print_settings_saved_message,
)
from src.blite_v6.settings.preferences import (
    build_preferences_payload,
    preferences_saved_message,
)
from src.blite_v6.settings.billing_alert_preferences import ALERT_PREF_KEY
from src.blite_v6.settings.license_actions import license_activation_action_view
from src.blite_v6.settings.notifications import (
    build_notifications_payload,
    dismissed_count_label,
    reset_dismissed_payload,
)
from src.blite_v6.settings.advanced_integrations import (
    ADVANCED_SAVED_MESSAGE,
    AI_MODELS,
    ai_saved_message,
    ai_status_view,
    ai_storage_hint,
    build_advanced_payload,
    build_ai_config,
    build_multibranch_config,
    build_whatsapp_api_config,
    multibranch_status_view,
    whatsapp_test_message,
    whatsapp_validation_message,
)
from src.blite_v6.settings.backup_license_about import (
    LICENSE_ACTIVATION_NOTE,
    UPDATE_MANIFEST_HELP_TEXT,
    VC_RUNTIME_HELP_TEXT,
    about_context_data,
    about_contact_rows,
    about_version_rows,
    activity_count_text,
    backup_context_data,
    backup_info_text,
    build_backup_schedule_config,
    build_update_manifest_payload,
    license_context_data,
    license_reminder_text,
    license_status_rows,
    update_available_message,
    vc_runtime_status,
)
from src.blite_v6.settings.security_settings import (
    build_security_payload,
    current_username,
    password_visibility_show_value,
    validate_new_password,
)
from src.blite_v6.settings.startup import setup_windows_startup
from src.blite_v6.settings.tab_specs import (
    advanced_feature_status_items,
    optional_tab_plan,
    settings_tab_defs,
)
from src.blite_v6.settings.themes import LEGACY_THEME_MAP, THEMES, apply_theme


# ─────────────────────────────────────────────────────────────────────────────
class SettingsFrame(tk.Frame):

    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self._responsive = get_responsive_metrics(self.winfo_toplevel())
        self._tabs = {}
        self._tab_loaded = set()
        self._scroll_frames = {}
        self._scroll_meta = {}
        self._tab_builders = {}
        self._print_tab = None
        self._notebook = None
        self._backup_folder_var = None
        self._backup_folder_entry = None
        self._license_status = {}
        self._upd_manifest_entry = None
        self._register_settings_context_menu_callbacks()
        self._build()

    def _settings_tab_defs(self, cfg: dict | None = None):
        return settings_tab_defs(cfg or get_settings())

    def _ensure_tab_frame(self, key: str, label: str | None = None):
        if key in self._tabs:
            return self._tabs[key]
        frame = tk.Frame(self._notebook, bg=C["bg"])
        self._tabs[key] = frame
        return frame

    def _add_notebook_tab(self, key: str, label: str, before=None):
        frame = self._ensure_tab_frame(key, label)
        if str(frame) in self._notebook.tabs():
            return frame
        tab_icon = get_section_icon(key)
        if tab_icon:
            self._tab_icons[key] = tab_icon
            kwargs = {"text": label, "image": tab_icon, "compound": "left"}
        else:
            kwargs = {"text": label}
        if before is not None and str(before) in self._notebook.tabs():
            self._notebook.insert(before, frame, **kwargs)
        else:
            self._notebook.add(frame, **kwargs)
        return frame

    def _sync_optional_tabs(self, cfg: dict | None = None):
        if not self._notebook:
            return
        plan = optional_tab_plan(cfg or get_settings())
        ai_frame = self._tabs.get(plan.ai_key)
        if plan.ai_enabled:
            before_frame = self._tabs.get(plan.insert_before_key)
            self._add_notebook_tab(plan.ai_key, plan.ai_label, before=before_frame)
        elif ai_frame is not None and str(ai_frame) in self._notebook.tabs():
            current_tab = self._notebook.select()
            if current_tab == str(ai_frame):
                advanced_frame = self._tabs.get(plan.fallback_select_key)
                if advanced_frame is not None and str(advanced_frame) in self._notebook.tabs():
                    self._notebook.select(advanced_frame)
            self._notebook.forget(ai_frame)

    def _feature_status_grid(self, parent, items):
        grid = tk.Frame(parent, bg=C["card"])
        grid.pack(fill=tk.X, pady=(0, 8))
        for idx, item in enumerate(items):
            cell = tk.Frame(grid, bg=C["bg"], padx=12, pady=10)
            cell.grid(row=0, column=idx, sticky="nsew", padx=(0, 8 if idx < len(items) - 1 else 0))
            grid.grid_columnconfigure(idx, weight=1, uniform="advanced_features")
            tk.Label(cell, text=item["label"], bg=C["bg"], fg=C["muted"],
                     font=("Arial", 9, "bold")).pack(anchor="w")
            tk.Label(cell, text=item["state"], bg=C["bg"], fg=item["color"],
                     font=("Arial", 12, "bold")).pack(anchor="w", pady=(4, 0))
            tk.Label(cell, text=item["caption"], bg=C["bg"], fg=C["muted"],
                     font=("Arial", 9), justify="left", wraplength=180).pack(anchor="w", pady=(4, 0))
        return grid

    # ── Build ─────────────────────────────────────────────────────────────────
    def _build(self):
        self._responsive = get_responsive_metrics(self.winfo_toplevel())
        title_font = ("Arial", scaled_value(17, 16, 14), "bold")
        subtitle_font = ("Arial", scaled_value(10, 10, 9))
        section_title_font = ("Arial", scaled_value(16, 15, 13), "bold")
        hdr = tk.Frame(self, bg=C["bg"], pady=6)
        hdr.pack(fill=tk.X)
        left_f = tk.Frame(hdr, bg=C["bg"])
        left_f.pack(side=tk.LEFT, padx=20)
        tk.Label(left_f, text="\u2699\ufe0f  Settings",
                 font=title_font,
                 bg=C["bg"], fg=C["text"]).pack(anchor="w")
        tk.Label(left_f, text="Configure shop, theme, print, licensing, and day-to-day preferences",
                 font=subtitle_font,
                 bg=C["bg"], fg=C["muted"]).pack(anchor="w")
        tk.Frame(self, bg=C["teal"], height=2).pack(fill=tk.X)

        top_band = tk.Frame(self, bg=C["bg"])
        top_band.pack(fill=tk.X, padx=15, pady=8)
        intro = tk.Frame(top_band, bg=C["card"], padx=18, pady=12)
        intro.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(intro, text="Settings Workspace",
                 font=section_title_font,
                 bg=C["card"], fg=C["text"]).pack(anchor="w")
        tk.Label(intro, text="Organise look and feel, billing defaults, notifications, and security from one place.",
                 font=subtitle_font, bg=C["card"], fg=C["muted"]).pack(anchor="w", pady=(4, 0))

        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))
        self._notebook = nb
        self._tab_icons = {}

        cfg = get_settings()
        self._tabs = {}
        for key, label in self._settings_tab_defs(cfg):
            self._add_notebook_tab(key, label)

        self._tab_builders = {
            "info": self._tab_info,
            "theme": self._tab_theme,
            "bill": self._tab_bill,
            "sec": self._tab_security,
            "pref": self._tab_prefs,
            "notif": self._tab_notifs,
            "backup": self._tab_backup,
            "advanced": self._tab_advanced,
            "license": self._tab_license,
            "about": self._tab_about,
        }
        self._tab_builders["ai"] = self._tab_ai

        try:
            t_print = tk.Frame(nb, bg=C["bg"])
            print_icon = get_section_icon("print")
            if print_icon:
                self._tab_icons["print"] = print_icon
                nb.add(t_print, text="Print / Bill", image=print_icon, compound="left")
            else:
                nb.add(t_print, text="Print / Bill")
            self._print_tab = t_print
        except Exception as _pe:
            app_log(f"[Print Settings tab] {_pe}")

        nb.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        try:
            nb.select(self._tabs["info"])
            self._ensure_tab("info")
        except Exception as e:
            app_log(f"[Settings initial tab load] {e}")


    def _on_tab_changed(self, e=None):
        if not self._notebook:
            return
        current = self._notebook.select()
        for key, tab in self._tabs.items():
            if str(tab) == current:
                self._ensure_tab(key)
                return
        if self._print_tab is not None and str(self._print_tab) == current:
            self._ensure_print_tab()

    def _ensure_tab(self, key: str):
        if key in self._tab_loaded:
            return
        builder = self._tab_builders.get(key)
        if not builder:
            return
        try:
            builder()
            self._tab_loaded.add(key)
        except Exception as e:
            app_log(f"[Settings tab:{key}] {e}")
            host = self._tabs.get(key)
            if host is not None:
                for w in host.winfo_children():
                    w.destroy()
                err = tk.Frame(host, bg=C["bg"], padx=20, pady=20)
                err.pack(fill=tk.BOTH, expand=True)
                tk.Label(
                    err,
                    text=f"Could not load this settings tab.\n\n{e}",
                    font=("Arial", 11),
                    bg=C["bg"],
                    fg=C["red"],
                    justify="left",
                ).pack(anchor="w")

    def _ensure_print_tab(self):
        if self._print_tab is None or "print" in self._tab_loaded:
            return
        try:
            from print_templates import PrintSettingsPanel
            PrintSettingsPanel(self._print_tab).pack(fill=tk.BOTH, expand=True)
            self._tab_loaded.add("print")
        except Exception as e:
            app_log(f"[Print Settings tab] {e}")
            for w in self._print_tab.winfo_children():
                w.destroy()
            err = tk.Frame(self._print_tab, bg=C["bg"], padx=20, pady=20)
            err.pack(fill=tk.BOTH, expand=True)
            tk.Label(
                err,
                text=f"Could not load Print / Bill settings.\n\n{e}",
                font=("Arial", 11),
                bg=C["bg"],
                fg=C["red"],
                justify="left",
            ).pack(anchor="w")

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _scroll(self, key: str):
        if key in self._scroll_frames:
            return self._scroll_frames[key]
        parent = self._tabs[key]
        shell = tk.Frame(parent, bg=C["bg"])
        shell.pack(fill=tk.BOTH, expand=True)
        content = tk.Frame(shell, bg=C["bg"])
        content.pack(fill=tk.BOTH, expand=True)
        c   = tk.Canvas(content, bg=C["bg"], highlightthickness=0)
        vsb = ttk.Scrollbar(content, orient="vertical", command=c.yview)
        c.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        c.pack(fill=tk.BOTH, expand=True)
        f  = tk.Frame(c, bg=C["bg"], padx=28, pady=12)
        cw = c.create_window((0, 0), window=f, anchor="nw")
        f.bind("<Configure>",
               lambda e: c.configure(scrollregion=c.bbox("all")))
        c.bind("<Configure>",
               lambda e: c.itemconfig(cw, width=e.width))

        def _mw(e):
            c.yview_scroll(int(-1 * (e.delta / 120)), "units")
        c.bind("<Enter>", lambda e: c.bind_all("<MouseWheel>", _mw))
        c.bind("<Leave>", lambda e: c.unbind_all("<MouseWheel>"))
        action_bar = tk.Frame(
            shell,
            bg=C["card"],
            padx=scaled_value(18, 14, 10),
            pady=scaled_value(10, 8, 6),
        )
        action_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=(6, 0))
        self._scroll_frames[key] = f
        self._scroll_meta[key] = {
            "shell": shell,
            "content": content,
            "canvas": c,
            "action_bar": action_bar,
            "body": f,
        }
        return f

    def _lbl(self, p, t: str):
        font_size = scaled_value(11, 10, 9)
        tk.Label(p, text=t, bg=C["bg"], fg=C["muted"],
                 font=("Arial", font_size, "bold")).pack(anchor="w", pady=(10, 3))

    def _ent(self, p, val: str, w=None):
        fill_x = not w
        e = tk.Entry(p, font=("Arial", scaled_value(12, 11, 10)), bg=C["input"],
                     fg=C["text"], bd=0, insertbackground=C["accent"], width=w)
        e.pack(fill=tk.X if fill_x else None, ipady=scaled_value(6, 5, 4), anchor="w")
        e.insert(0, val)
        return e

    def _sec(self, p, t: str, col=None):
        outer = tk.Frame(p, bg=C["card"])
        outer.pack(fill=tk.X, pady=(0, 12))
        hf = tk.Frame(outer, bg=C["sidebar"], padx=scaled_value(12, 10, 8), pady=scaled_value(6, 5, 4))
        hf.pack(fill=tk.X)
        tk.Label(hf, text=t, font=("Arial", scaled_value(11, 10, 9), "bold"),
                 bg=C["sidebar"], fg=col or C["text"]).pack(side=tk.LEFT)
        tk.Frame(outer, bg=col or C["teal"], height=2).pack(fill=tk.X)
        f = tk.Frame(outer, bg=C["bg"], padx=scaled_value(14, 12, 10), pady=scaled_value(10, 8, 6))
        f.pack(fill=tk.X)
        return f

    def _chk(self, p, t: str, v):
        tk.Checkbutton(p, text=t, variable=v,
                       bg=C["bg"], fg=C["text"],
                       selectcolor=C["input"],
                       font=("Arial", scaled_value(11, 10, 9)),
                       cursor="hand2").pack(anchor="w", pady=2)

    def _savebtn(self, p, t: str, cmd, col=None):
        save_icon = get_action_icon("save")
        clean_text = t.split("  ", 1)[-1] if "  " in t else t
        target = p
        for meta in self._scroll_meta.values():
            if meta.get("body") is p:
                target = meta["action_bar"]
                break
        ModernButton(target, text=clean_text, image=save_icon, compound="left", command=cmd,
                     color=col or C["teal"], hover_color=C["blue"],
                     width=scaled_value(220, 190, 170), height=scaled_value(38, 34, 30), radius=8,
                     font=("Arial", scaled_value(11, 10, 9), "bold"),
                     ).pack(anchor="w")

    def _gst_master_current_map(self) -> dict[str, float]:
        tree = getattr(self, "_gst_master_tree", None)
        if tree is None:
            return {}
        raw: dict[str, object] = {}
        for iid in tree.get_children():
            values = tree.item(iid, "values") or ()
            if len(values) < 2:
                continue
            category = str(values[0]).strip()
            rate = values[1]
            if category:
                raw[category] = rate
        return normalize_gst_category_rate_map(raw)

    def _gst_master_set_rows(self, rows: dict[str, float], *, select_category: str | None = None):
        tree = getattr(self, "_gst_master_tree", None)
        if tree is None:
            return
        tree.delete(*tree.get_children())
        normalized = normalize_gst_category_rate_map(rows)
        for category, rate in normalized.items():
            tree.insert("", tk.END, values=(category, f"{rate:g}"))
        if hasattr(self, "_gst_master_status_lbl"):
            self._gst_master_status_lbl.config(text=f"{len(normalized)} category rules")
        if select_category:
            needle = select_category.strip().lower()
            for iid in tree.get_children():
                values = tree.item(iid, "values") or ()
                if values and str(values[0]).strip().lower() == needle:
                    tree.selection_set(iid)
                    tree.see(iid)
                    self._gst_master_fill_selected()
                    break

    def _gst_master_fill_selected(self, e=None):
        tree = getattr(self, "_gst_master_tree", None)
        if tree is None:
            return
        sel = tree.selection()
        if not sel:
            return
        values = tree.item(sel[0], "values") or ()
        if len(values) < 2:
            return
        self._gst_master_name_var.set(str(values[0]))
        self._gst_master_rate_var.set(str(values[1]))

    def _gst_master_clear_inputs(self):
        if hasattr(self, "_gst_master_name_var"):
            self._gst_master_name_var.set("")
        if hasattr(self, "_gst_master_rate_var"):
            self._gst_master_rate_var.set("")

    def _gst_master_upsert_rule(self):
        name = self._gst_master_name_var.get().strip()
        rate_text = self._gst_master_rate_var.get().strip()
        if not name:
            messagebox.showwarning("GST Master", "Enter a category name.")
            return
        try:
            rate = float(rate_text)
        except Exception:
            messagebox.showwarning("GST Master", "Enter a valid GST percentage.")
            return
        if rate < 0:
            messagebox.showwarning("GST Master", "GST percentage cannot be negative.")
            return

        current = self._gst_master_current_map()
        current[name] = round(rate, 2)
        self._gst_master_set_rows(current, select_category=name)
        self._gst_master_clear_inputs()

    def _gst_master_remove_rule(self):
        tree = getattr(self, "_gst_master_tree", None)
        if tree is None:
            return
        sel = tree.selection()
        if not sel:
            messagebox.showinfo("GST Master", "Select a category rule to remove.")
            return
        current = self._gst_master_current_map()
        for iid in sel:
            values = tree.item(iid, "values") or ()
            if not values:
                continue
            current.pop(str(values[0]), None)
        self._gst_master_set_rows(current)
        self._gst_master_clear_inputs()

    def _gst_master_reset_defaults(self):
        if not messagebox.askyesno(
            "GST Master",
            "Restore the default GST category rules?\nAny custom category rates will be replaced.",
        ):
            return
        self._gst_master_set_rows(dict(DEFAULTS.get("gst_category_rate_map", {})))
        self._gst_master_clear_inputs()

    def _gst_classification_current_rules(self) -> list[dict]:
        tree = getattr(self, "_gst_classification_tree", None)
        if tree is None:
            return []
        raw: list[dict[str, object]] = []
        for iid in tree.get_children():
            values = tree.item(iid, "values") or ()
            if len(values) < 4:
                continue
            field = str(values[0]).strip()
            mode = str(values[1]).strip()
            pattern = str(values[2]).strip()
            rate = values[3]
            if field and pattern:
                raw.append({"field": field, "mode": mode, "pattern": pattern, "rate": rate})
        return normalize_gst_classification_rules(raw)

    def _gst_classification_set_rows(self, rows: list[dict], *, select_pattern: str | None = None):
        tree = getattr(self, "_gst_classification_tree", None)
        if tree is None:
            return
        tree.delete(*tree.get_children())
        normalized = normalize_gst_classification_rules(rows)
        for rule in normalized:
            note = rule.get("note", "")
            values = (rule["field"], rule["mode"], rule["pattern"], f"{rule['rate']:g}")
            iid = tree.insert("", tk.END, values=values)
            if note:
                tree.set(iid, "pattern", rule["pattern"])
        if hasattr(self, "_gst_classification_status_lbl"):
            self._gst_classification_status_lbl.config(text=f"{len(normalized)} item rules")
        if select_pattern:
            needle = select_pattern.strip().lower()
            for iid in tree.get_children():
                values = tree.item(iid, "values") or ()
                if len(values) >= 3 and str(values[2]).strip().lower() == needle:
                    tree.selection_set(iid)
                    tree.see(iid)
                    self._gst_classification_fill_selected()
                    break

    def _gst_classification_fill_selected(self, e=None):
        tree = getattr(self, "_gst_classification_tree", None)
        if tree is None:
            return
        sel = tree.selection()
        if not sel:
            return
        values = tree.item(sel[0], "values") or ()
        if len(values) < 4:
            return
        self._gst_classification_field_var.set(str(values[0]))
        self._gst_classification_mode_var.set(str(values[1]))
        self._gst_classification_pattern_var.set(str(values[2]))
        self._gst_classification_rate_var.set(str(values[3]))

    def _gst_classification_clear_inputs(self):
        if hasattr(self, "_gst_classification_field_var"):
            self._gst_classification_field_var.set("name")
        if hasattr(self, "_gst_classification_mode_var"):
            self._gst_classification_mode_var.set("exact")
        if hasattr(self, "_gst_classification_pattern_var"):
            self._gst_classification_pattern_var.set("")
        if hasattr(self, "_gst_classification_rate_var"):
            self._gst_classification_rate_var.set("")

    def _gst_classification_upsert_rule(self):
        field = self._gst_classification_field_var.get().strip()
        mode = self._gst_classification_mode_var.get().strip()
        pattern = self._gst_classification_pattern_var.get().strip()
        rate_text = self._gst_classification_rate_var.get().strip()
        if not pattern:
            messagebox.showwarning("GST Classification", "Enter a product name, keyword, HSN/SAC, or other match text.")
            return
        try:
            rate = float(rate_text)
        except Exception:
            messagebox.showwarning("GST Classification", "Enter a valid GST percentage.")
            return
        if rate < 0:
            messagebox.showwarning("GST Classification", "GST percentage cannot be negative.")
            return
        current = self._gst_classification_current_rules()
        current.append({"field": field, "mode": mode, "pattern": pattern, "rate": round(rate, 2)})
        self._gst_classification_set_rows(current, select_pattern=pattern)
        self._gst_classification_clear_inputs()

    def _gst_classification_remove_rule(self):
        tree = getattr(self, "_gst_classification_tree", None)
        if tree is None:
            return
        sel = tree.selection()
        if not sel:
            messagebox.showinfo("GST Classification", "Select a rule to remove.")
            return
        current = self._gst_classification_current_rules()
        selected_patterns = set()
        for iid in sel:
            values = tree.item(iid, "values") or ()
            if len(values) >= 3:
                selected_patterns.add(str(values[2]).strip().lower())
        filtered = [rule for rule in current if str(rule.get("pattern", "")).strip().lower() not in selected_patterns]
        self._gst_classification_set_rows(filtered)
        self._gst_classification_clear_inputs()

    def _gst_classification_reset_defaults(self):
        if not messagebox.askyesno(
            "GST Classification",
            "Clear all GST classification rules?\nThis returns to category/master fallback only.",
        ):
            return
        self._gst_classification_set_rows([])
        self._gst_classification_clear_inputs()

    def _offer_restart(self, title: str, message: str):
        if messagebox.askyesno(
                title,
                f"{message}\n\nRestart now?\nChoose 'No' to restart later."):
            os.execl(sys.executable, sys.executable, *sys.argv)
        else:
            messagebox.showinfo(
                "Restart Later",
                "Changes are saved. Remaining updates will apply on next restart.")

    # ── Tab 1: Shop Info ──────────────────────────────────────────────────────
    def _tab_info(self):
        from salon_info_tab import render_shop_info_tab

        return render_shop_info_tab(self)

    def _save_info(self):
        cfg = get_settings()
        for k, e in self._ents.items():
            cfg[k] = e.get().strip()
        save_settings(cfg)
        messagebox.showinfo("Saved", "Shop info saved!")

    # ── Tab 2: Theme ───────────────────────────────────────────────────────────
    def _tab_theme(self):
        from theme_tab import render_theme_tab

        return render_theme_tab(self)

    def _browse_logo(self):
        p = filedialog.askopenfilename(
            title="Select Logo",
            filetypes=[("Images", "*.png *.jpg *.jpeg"), ("All", "*.*")])
        if p:
            self._logo_var.set(p)

    def _apply_theme(self):
        key = self._theme_var.get()
        cfg = get_settings()
        cfg["theme"]     = key
        cfg["ui_scale"]  = self._scale_var.get()
        cfg["logo_path"] = self._logo_var.get()
        save_settings(cfg)
        apply_theme(key)
        self._offer_restart(
            "Theme Applied",
            f"Theme saved: {THEMES[key]['name']}\n"
            "Full visual refresh needs a restart.")

    # ── Tab 3: Bill & GST ──────────────────────────────────────────────────────
    def _tab_bill(self):
        cfg = get_settings()
        f   = self._scroll("bill")

        mode_f = self._sec(f, "🏪  Business Billing Mode", C["teal"])
        self._billing_mode = tk.StringVar(value=cfg.get("billing_mode", "mixed"))
        tk.Label(
            mode_f,
            text="Control how items appear in billing, invoices, and printed bills.",
            bg=C["bg"], fg=C["muted"],
            font=("Arial", 10)
        ).pack(anchor="w", pady=(0, 10))

        self._mode_borders = {}

        def _select_mode(val):
            self._billing_mode.set(val)
            for opt, border_frame in self._mode_borders.items():
                border_frame.config(bg=C["teal"] if opt == val else C["card"])

        for value, icon, title, subtitle in [
            ("mixed", "✂", "Salon / Spa", "Services + Products"),
            ("product_only", "🛍", "Retail Store", "Products Only"),
            ("service_only", "🔧", "Service Business", "Services Only"),
        ]:
            row = tk.Frame(mode_f, bg=C["card"], cursor="hand2")
            row.pack(fill=tk.X, pady=4)
            border = tk.Frame(
                row,
                bg=C["teal"] if self._billing_mode.get() == value else C["card"],
                width=3,
                height=52,
            )
            border.pack(side=tk.LEFT, fill=tk.Y)
            self._mode_borders[value] = border

            inner = tk.Frame(row, bg=C["card"], padx=8, pady=8, cursor="hand2")
            inner.pack(side=tk.LEFT, fill=tk.X, expand=True)
            icon_lbl = tk.Label(
                inner, text=icon, font=("Arial", 18),
                bg=C["card"], fg=C["text"], cursor="hand2"
            )
            icon_lbl.pack(side=tk.LEFT, padx=(2, 10))

            txt = tk.Frame(inner, bg=C["card"], cursor="hand2")
            txt.pack(side=tk.LEFT, fill=tk.X, expand=True)
            title_lbl = tk.Label(
                txt, text=title, font=("Arial", 12, "bold"),
                bg=C["card"], fg=C["text"], anchor="w", cursor="hand2"
            )
            title_lbl.pack(anchor="w")
            sub_lbl = tk.Label(
                txt, text=subtitle, font=("Arial", 10),
                bg=C["card"], fg=C["muted"], anchor="w", cursor="hand2"
            )
            sub_lbl.pack(anchor="w", pady=(2, 0))

            for widget in (row, inner, icon_lbl, txt, title_lbl, sub_lbl):
                widget.bind("<Button-1>", lambda _e, v=value: _select_mode(v))

        gst_f = self._sec(f, "\U0001f9fe  GST Settings", C["teal"])
        self._gst_on   = tk.BooleanVar(value=cfg.get("gst_always_on", False))
        self._gst_type = tk.StringVar(value=cfg.get("gst_type", "inclusive"))
        self._chk(gst_f, "Always enable GST on every bill", self._gst_on)
        tk.Label(gst_f, text="GST Type:",
                 bg=C["bg"], fg=C["muted"],
                 font=("Arial", 11, "bold")).pack(anchor="w", pady=(10, 4))
        tf = tk.Frame(gst_f, bg=C["bg"])
        tf.pack(fill=tk.X)
        for val, txt in [
            ("inclusive", "Inclusive — GST inside price (customer pays same)"),
            ("exclusive", "Exclusive — GST added on top (customer pays more)"),
        ]:
            tk.Radiobutton(tf, text=txt, variable=self._gst_type, value=val,
                           bg=C["bg"], fg=C["text"],
                           selectcolor=C["input"],
                           font=("Arial", 11),
                           cursor="hand2").pack(anchor="w", pady=2)

        ex_f = tk.Frame(gst_f, bg=C["card"], padx=12, pady=8)
        ex_f.pack(fill=tk.X, pady=(8, 4))
        tk.Label(ex_f,
                 text="Inclusive: \u20b91000 service \u2192 pay \u20b91000 (GST inside)\n"
                      "Exclusive: \u20b91000 + 18% \u2192 pay \u20b91180",
                 bg=C["card"], fg=C["muted"],
                 font=("Arial", 10), justify="left").pack(anchor="w")

        rr = tk.Frame(gst_f, bg=C["bg"])
        rr.pack(fill=tk.X, pady=(8, 0))
        tk.Label(rr, text="GST Rate %:",
                 bg=C["bg"], fg=C["muted"],
                 font=("Arial", 11, "bold")).pack(side=tk.LEFT, padx=(0, 8))
        self._gst_rate = tk.Entry(rr, font=("Arial", 12),
                                  bg=C["input"], fg=C["lime"],
                                  bd=0, width=8,
                                  insertbackground=C["accent"])
        self._gst_rate.pack(side=tk.LEFT, ipady=5)
        self._gst_rate.insert(0, str(cfg.get("gst_rate", 18.0)))
        tk.Label(rr, text="  (default: 18%)",
                 bg=C["bg"], fg=C["muted"],
                 font=("Arial", 10)).pack(side=tk.LEFT)

        pg_f = tk.Frame(gst_f, bg=C["card"], padx=12, pady=8)
        pg_f.pack(fill=tk.X, pady=(10, 4))
        tk.Label(pg_f, text="Product-wise GST:",
                 bg=C["card"], fg=C["text"],
                 font=("Arial", 11, "bold")).pack(anchor="w")
        self._product_wise_gst = tk.BooleanVar(value=cfg.get("product_wise_gst_enabled", False))
        self._chk(pg_f, "Enable item-wise GST for inventory products", self._product_wise_gst)

        src_row = tk.Frame(pg_f, bg=C["card"])
        src_row.pack(fill=tk.X, pady=(8, 0))
        tk.Label(src_row, text="GST Source:",
                 bg=C["card"], fg=C["muted"],
                 font=("Arial", 11, "bold")).pack(side=tk.LEFT, padx=(0, 8))
        self._gst_rate_source = tk.StringVar(value=cfg.get("gst_rate_source", "global"))
        ttk.Combobox(
            src_row,
            textvariable=self._gst_rate_source,
            values=list(GST_RATE_SOURCE_LABELS.keys()),
            state="readonly",
            width=14,
            font=("Arial", 11),
        ).pack(side=tk.LEFT, ipady=2)
        tk.Label(
            src_row,
            text="global = salon mode, item = grocery mode, hybrid = auto fallback",
            bg=C["card"], fg=C["muted"],
            font=("Arial", 10),
        ).pack(side=tk.LEFT, padx=(10, 0))

        miss_row = tk.Frame(pg_f, bg=C["card"])
        miss_row.pack(fill=tk.X, pady=(8, 0))
        tk.Label(miss_row, text="Missing Item GST:",
                 bg=C["card"], fg=C["muted"],
                 font=("Arial", 11, "bold")).pack(side=tk.LEFT, padx=(0, 8))
        self._missing_item_gst_policy = tk.StringVar(value=cfg.get("missing_item_gst_policy", "global"))
        ttk.Combobox(
            miss_row,
            textvariable=self._missing_item_gst_policy,
            values=list(MISSING_ITEM_GST_POLICY_LABELS.keys()),
            state="readonly",
            width=18,
            font=("Arial", 11),
        ).pack(side=tk.LEFT, ipady=2)

        master_f = self._sec(f, "🏷️  GST Category Master")
        tk.Label(
            master_f,
            text="Edit category-wise tax defaults used by Hybrid / Auto GST mode.",
            bg=C["bg"], fg=C["muted"],
            font=("Arial", 10),
        ).pack(anchor="w", pady=(0, 6))

        self._gst_master_status_lbl = tk.Label(
            master_f,
            text="",
            bg=C["bg"], fg=C["muted"],
            font=("Arial", 10, "bold"),
        )
        self._gst_master_status_lbl.pack(anchor="w", pady=(0, 6))

        tree_wrap = tk.Frame(master_f, bg=C["card"], width=340, height=210)
        tree_wrap.pack(anchor="w", pady=(0, 8))
        tree_wrap.pack_propagate(False)
        self._gst_master_tree = ttk.Treeview(
            tree_wrap,
            columns=("category", "rate"),
            show="headings",
            height=6,
        )
        self._gst_master_tree.heading("category", text="Category")
        self._gst_master_tree.heading("rate", text="GST %")
        self._gst_master_tree.column("category", width=245, anchor="w", stretch=False)
        self._gst_master_tree.column("rate", width=65, anchor="e", stretch=False)
        tree_sb = ttk.Scrollbar(tree_wrap, orient="vertical", command=self._gst_master_tree.yview)
        self._gst_master_tree.configure(yscrollcommand=tree_sb.set)
        self._gst_master_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._gst_master_tree.bind("<<TreeviewSelect>>", self._gst_master_fill_selected)

        edit_row = tk.Frame(master_f, bg=C["card"], width=340)
        edit_row.pack(anchor="w", pady=(2, 0))
        left_edit = tk.Frame(edit_row, bg=C["card"])
        left_edit.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(left_edit, text="Category:", bg=C["card"], fg=C["muted"], font=("Arial", 11, "bold")).pack(anchor="w")
        self._gst_master_name_var = tk.StringVar()
        tk.Entry(
            left_edit,
            textvariable=self._gst_master_name_var,
            font=("Arial", 12),
            bg=C["input"], fg=C["text"],
            bd=0,
            insertbackground=C["accent"],
        ).pack(fill=tk.X, ipady=5, pady=(4, 8))

        tk.Label(left_edit, text="Examples: Grocery, Fruits, Body Care", bg=C["card"], fg=C["muted"], font=("Arial", 10)).pack(anchor="w")

        right_edit = tk.Frame(edit_row, bg=C["card"])
        right_edit.pack(side=tk.LEFT, fill=tk.X, padx=(12, 0))
        tk.Label(right_edit, text="GST %:", bg=C["card"], fg=C["muted"], font=("Arial", 11, "bold")).pack(anchor="w")
        self._gst_master_rate_var = tk.StringVar()
        tk.Entry(
            right_edit,
            textvariable=self._gst_master_rate_var,
            font=("Arial", 12),
            bg=C["input"], fg=C["text"],
            bd=0,
            width=10,
            insertbackground=C["accent"],
        ).pack(anchor="w", ipady=5, pady=(4, 8))

        actions_row = tk.Frame(master_f, bg=C["card"], width=340)
        actions_row.pack(anchor="w", pady=(2, 0))
        ModernButton(
            actions_row,
            text="Add / Update",
            command=self._gst_master_upsert_rule,
            color=C["teal"],
            hover_color=C["blue"],
            width=150,
            height=34,
            radius=8,
            font=("Arial", 10, "bold"),
        ).pack(side=tk.LEFT, padx=(0, 8))
        ModernButton(
            actions_row,
            text="Remove",
            command=self._gst_master_remove_rule,
            color=C["red"],
            hover_color="#c0392b",
            width=120,
            height=34,
            radius=8,
            font=("Arial", 10, "bold"),
        ).pack(side=tk.LEFT, padx=(0, 8))
        ModernButton(
            actions_row,
            text="Reset Defaults",
            command=self._gst_master_reset_defaults,
            color=C["blue"],
            hover_color="#154360",
            width=140,
            height=34,
            radius=8,
            font=("Arial", 10, "bold"),
        ).pack(side=tk.LEFT)
        self._gst_master_set_rows(cfg.get("gst_category_rate_map", {}))

        class_f = self._sec(f, "🏷️  GST Classification Master")
        tk.Label(
            class_f,
            text="Add exact product-name, keyword, HSN/SAC, SKU, or barcode rules before category fallback.",
            bg=C["bg"], fg=C["muted"],
            font=("Arial", 10),
        ).pack(anchor="w", pady=(0, 6))

        self._gst_classification_status_lbl = tk.Label(
            class_f,
            text="",
            bg=C["bg"], fg=C["muted"],
            font=("Arial", 10, "bold"),
        )
        self._gst_classification_status_lbl.pack(anchor="w", pady=(0, 6))

        class_wrap = tk.Frame(class_f, bg=C["card"], width=580, height=210)
        class_wrap.pack(anchor="w", pady=(0, 8))
        class_wrap.pack_propagate(False)
        self._gst_classification_tree = ttk.Treeview(
            class_wrap,
            columns=("field", "mode", "pattern", "rate"),
            show="headings",
            height=6,
        )
        self._gst_classification_tree.heading("field", text="Field")
        self._gst_classification_tree.heading("mode", text="Mode")
        self._gst_classification_tree.heading("pattern", text="Pattern / Value")
        self._gst_classification_tree.heading("rate", text="GST %")
        self._gst_classification_tree.column("field", width=95, anchor="w", stretch=False)
        self._gst_classification_tree.column("mode", width=80, anchor="w", stretch=False)
        self._gst_classification_tree.column("pattern", width=250, anchor="w", stretch=False)
        self._gst_classification_tree.column("rate", width=60, anchor="e", stretch=False)
        class_sb = ttk.Scrollbar(class_wrap, orient="vertical", command=self._gst_classification_tree.yview)
        self._gst_classification_tree.configure(yscrollcommand=class_sb.set)
        self._gst_classification_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        class_sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._gst_classification_tree.bind("<<TreeviewSelect>>", self._gst_classification_fill_selected)

        class_edit_row = tk.Frame(class_f, bg=C["card"], width=580)
        class_edit_row.pack(anchor="w", pady=(2, 0))
        class_left = tk.Frame(class_edit_row, bg=C["card"])
        class_left.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(class_left, text="Field:", bg=C["card"], fg=C["muted"], font=("Arial", 11, "bold")).pack(anchor="w")
        self._gst_classification_field_var = tk.StringVar(value="name")
        ttk.Combobox(
            class_left,
            textvariable=self._gst_classification_field_var,
            values=list(CLASSIFICATION_FIELDS),
            state="readonly",
            font=("Arial", 12),
        ).pack(fill=tk.X, ipady=4, pady=(4, 8))

        tk.Label(class_left, text="Pattern / Value:", bg=C["card"], fg=C["muted"], font=("Arial", 11, "bold")).pack(anchor="w")
        self._gst_classification_pattern_var = tk.StringVar()
        tk.Entry(
            class_left,
            textvariable=self._gst_classification_pattern_var,
            font=("Arial", 12),
            bg=C["input"], fg=C["text"],
            bd=0,
            insertbackground=C["accent"],
        ).pack(fill=tk.X, ipady=5, pady=(4, 8))

        class_right = tk.Frame(class_edit_row, bg=C["card"])
        class_right.pack(side=tk.LEFT, fill=tk.X, padx=(12, 0))
        tk.Label(class_right, text="Mode:", bg=C["card"], fg=C["muted"], font=("Arial", 11, "bold")).pack(anchor="w")
        self._gst_classification_mode_var = tk.StringVar(value="exact")
        ttk.Combobox(
            class_right,
            textvariable=self._gst_classification_mode_var,
            values=list(CLASSIFICATION_MODES),
            state="readonly",
            font=("Arial", 12),
            width=14,
        ).pack(anchor="w", ipady=4, pady=(4, 8))

        tk.Label(class_right, text="GST %:", bg=C["card"], fg=C["muted"], font=("Arial", 11, "bold")).pack(anchor="w")
        self._gst_classification_rate_var = tk.StringVar()
        tk.Entry(
            class_right,
            textvariable=self._gst_classification_rate_var,
            font=("Arial", 12),
            bg=C["input"], fg=C["text"],
            bd=0,
            width=10,
            insertbackground=C["accent"],
        ).pack(anchor="w", ipady=5, pady=(4, 8))

        class_actions = tk.Frame(class_f, bg=C["card"], width=580)
        class_actions.pack(anchor="w", pady=(2, 0))
        ModernButton(
            class_actions,
            text="Add / Update",
            command=self._gst_classification_upsert_rule,
            color=C["teal"],
            hover_color=C["blue"],
            width=150,
            height=34,
            radius=8,
            font=("Arial", 10, "bold"),
        ).pack(side=tk.LEFT, padx=(0, 8))
        ModernButton(
            class_actions,
            text="Remove",
            command=self._gst_classification_remove_rule,
            color=C["red"],
            hover_color="#c0392b",
            width=120,
            height=34,
            radius=8,
            font=("Arial", 10, "bold"),
        ).pack(side=tk.LEFT, padx=(0, 8))
        ModernButton(
            class_actions,
            text="Reset Defaults",
            command=self._gst_classification_reset_defaults,
            color=C["blue"],
            hover_color="#154360",
            width=140,
            height=34,
            radius=8,
            font=("Arial", 10, "bold"),
        ).pack(side=tk.LEFT)
        self._gst_classification_set_rows(cfg.get("gst_classification_rules", []))

        footer_f = self._sec(f, "\U0001f4dd  Bill Footer Message")
        self._footer = tk.Text(footer_f, height=3, font=("Arial", 11),
                               bg=C["input"], fg=C["text"],
                               bd=0, insertbackground=C["accent"])
        self._footer.pack(fill=tk.X)
        self._footer.insert("1.0", cfg.get("bill_footer", ""))

        self._savebtn(f, "\U0001f4be  Save Bill & GST", self._save_bill)

    def _save_bill(self):
        cfg = build_bill_gst_payload(
            get_settings(),
            billing_mode=self._billing_mode.get(),
            gst_always_on=self._gst_on.get(),
            gst_type=self._gst_type.get(),
            gst_rate_text=self._gst_rate.get(),
            product_wise_gst_enabled=self._product_wise_gst.get(),
            gst_rate_source=self._gst_rate_source.get(),
            missing_item_gst_policy=self._missing_item_gst_policy.get(),
            gst_category_rate_map=self._gst_master_current_map(),
            bill_footer=self._footer.get("1.0", tk.END),
        )
        cfg = build_gst_classification_payload(
            cfg,
            gst_classification_rules=self._gst_classification_current_rules(),
        )
        save_settings(cfg)
        messagebox.showinfo("Saved", bill_gst_saved_message(cfg))

    # ── Tab 4: Print Size ──────────────────────────────────────────────────────
    def _tab_print(self):
        cfg = get_settings()
        f   = self._scroll("print")

        tk.Label(f, text="\U0001f5a8\ufe0f  Print Size Settings",
                 bg=C["bg"], fg=C["accent"],
                 font=("Arial", 13, "bold")).pack(anchor="w", pady=(0, 14))

        paper_f = self._sec(f, "\U0001f4dc  Paper / Printer Type")
        tk.Label(paper_f, text="Select your printer paper size:",
                 bg=C["bg"], fg=C["muted"],
                 font=("Arial", 11)).pack(anchor="w", pady=(0, 10))
        self._paper = tk.StringVar(value=cfg.get("paper_size", "80mm"))
        for val, lbl, desc in [
            ("58mm", "58mm", "Small thermal printer  (32 columns)"),
            ("80mm", "80mm", "Standard thermal printer  (48 columns) \u2190 Most common"),
            ("A5",   "A5",   "Half A4 paper  (56 columns)"),
            ("A4",   "A4",   "Full A4 paper  (64 columns)"),
        ]:
            row = tk.Frame(paper_f, bg=C["bg"])
            row.pack(fill=tk.X, pady=3)
            tk.Radiobutton(row, text=lbl,
                           variable=self._paper, value=val,
                           bg=C["bg"], fg=C["text"],
                           selectcolor=C["input"],
                           font=("Arial", 12, "bold"),
                           cursor="hand2",
                           command=self._update_print_preview).pack(
                               side=tk.LEFT, padx=(0, 10))
            tk.Label(row, text=desc,
                     bg=C["bg"], fg=C["muted"],
                     font=("Arial", 10)).pack(side=tk.LEFT)

        font_f = self._sec(f, "\U0001f524  Print Font Size")
        tk.Label(font_f,
                 text="Bill text font size (smaller = more text fits):",
                 bg=C["bg"], fg=C["muted"],
                 font=("Arial", 11)).pack(anchor="w", pady=(0, 8))
        self._pfs = tk.IntVar(value=cfg.get("print_font_size", 9))
        fs_row = tk.Frame(font_f, bg=C["bg"])
        fs_row.pack(fill=tk.X)
        for sz, lbl in [(7, "7pt (tiny)"), (8, "8pt"), (9, "9pt (default)"),
                        (10, "10pt"), (11, "11pt"), (12, "12pt (large)")]:
            tk.Radiobutton(fs_row, text=lbl,
                           variable=self._pfs, value=sz,
                           bg=C["bg"], fg=C["text"],
                           selectcolor=C["input"],
                           font=("Arial", 10),
                           cursor="hand2",
                           command=self._update_print_preview).pack(
                               side=tk.LEFT, padx=(0, 12))

        width_f = self._sec(f, "\u2194  Bill Width (columns)")
        tk.Label(width_f, text="Number of characters per line:",
                 bg=C["bg"], fg=C["muted"],
                 font=("Arial", 11)).pack(anchor="w", pady=(0, 8))
        self._pwc = tk.StringVar(value=str(cfg.get("print_width_chars", 48)))
        wc_row = tk.Frame(width_f, bg=C["bg"])
        wc_row.pack(fill=tk.X)
        for val, lbl in [("32", "32 (58mm)"), ("40", "40"),
                          ("48", "48 (80mm)"), ("56", "56 (A5)"),
                          ("64", "64 (A4)")]:
            tk.Radiobutton(wc_row, text=lbl,
                           variable=self._pwc, value=val,
                           bg=C["bg"], fg=C["text"],
                           selectcolor=C["input"],
                           font=("Arial", 10),
                           cursor="hand2",
                           command=self._update_print_preview).pack(
                               side=tk.LEFT, padx=(0, 12))

        prev_f = self._sec(f, "\U0001f441\ufe0f  Live Bill Preview")
        tk.Label(prev_f,
                 text="Preview updates when you change settings above:",
                 bg=C["bg"], fg=C["muted"],
                 font=("Arial", 10)).pack(anchor="w", pady=(0, 6))
        self._print_prev_txt = tk.Text(
            prev_f, height=10,
            font=("Courier New", cfg.get("print_font_size", 9)),
            bg=C["input"], fg=C["text"],
            bd=0, state="disabled")
        self._print_prev_txt.pack(fill=tk.X)
        self.after(200, self._update_print_preview)

        self._savebtn(f, "\U0001f4be  Save Print Settings", self._save_print)

    def _update_print_preview(self):
        try:
            paper = self._paper.get()
            fs    = self._pfs.get()
            cfg2  = get_settings()
            sample = build_print_preview_text(
                cfg2,
                paper_size=paper,
                font_size=fs,
                width_text=self._pwc.get(),
            )
            widget = getattr(self, "_print_prev_txt", None)
            if widget:
                widget.config(state="normal",
                              font=("Courier New", fs))
                widget.delete("1.0", tk.END)
                widget.insert(tk.END, sample)
                widget.config(state="disabled")
        except Exception:
            pass

    def _save_print(self):
        cfg = build_print_settings_payload(
            get_settings(),
            paper_size=self._paper.get(),
            font_size=self._pfs.get(),
            width_text=self._pwc.get(),
        )
        save_settings(cfg)
        messagebox.showinfo("Saved", print_settings_saved_message(cfg))

    # ── Tab 5: Security ────────────────────────────────────────────────────────
    def _tab_security(self):
        from security_tab import render_security_tab

        return render_security_tab(self)

    def _pw_entry(self, parent, label: str):
        tk.Label(parent, text=label,
                 bg=C["bg"], fg=C["muted"],
                 font=("Arial", 11)).pack(anchor="w")
        e = tk.Entry(parent, show="*", font=("Arial", 12),
                     bg=C["input"], fg=C["text"],
                     bd=0, insertbackground=C["accent"])
        e.pack(fill=tk.X, ipady=6, pady=(4, 8))
        return e

    def _toggle_security_passwords(self):
        show_value = password_visibility_show_value(self._show_security_passwords.get())
        for entry in (self._pw_curr, self._pw_new, self._pw_conf):
            try:
                entry.config(show=show_value)
            except Exception:
                pass

    def _change_pw(self):
        from auth import get_users, _save_users
        curr = self._pw_curr.get().strip()
        newp = self._pw_new.get().strip()
        conf = self._pw_conf.get().strip()
        uname = current_username(getattr(self.app, "current_user", {}))
        users = get_users()
        if uname not in users:
            messagebox.showerror("Error", "Current user account not found.")
            return
        user  = users.get(uname, {})
        if not verify_password(curr, str(user.get("password", "")))[0]:
            messagebox.showerror("Error", "Current password incorrect!")
            return
        valid, error = validate_new_password(newp, conf)
        if not valid:
            messagebox.showerror("Error", error)
            return
        users[uname]["password"] = hash_pw(newp)
        if not _save_users(users):
            messagebox.showerror("Error", "Password could not be saved.")
            return
        for e in (self._pw_curr, self._pw_new, self._pw_conf):
            e.delete(0, tk.END)
        messagebox.showinfo("Done", "Password changed!")

    def _save_security(self):
        cfg = build_security_payload(
            get_settings(),
            auto_logout=self._auto_logout.get(),
            require_pw_bill=self._req_pw_del.get(),
        )
        save_settings(cfg)
        messagebox.showinfo("Saved", "Security settings saved!")

    # ── Tab 6: Preferences ────────────────────────────────────────────────────
    def _tab_prefs(self):
        cfg = get_settings()
        f   = self._scroll("pref")

        bf = self._sec(f, "\U0001f9fe  Billing Defaults")
        tk.Label(bf, text="Default Payment:",
                 bg=C["bg"], fg=C["muted"],
                 font=("Arial", 11)).pack(anchor="w", pady=(0, 6))
        self._def_pay = tk.StringVar(value=cfg.get("default_payment", "Cash"))
        pr = tk.Frame(bf, bg=C["bg"])
        pr.pack(fill=tk.X)
        for pm in ["Cash", "Card", "UPI"]:
            tk.Radiobutton(pr, text=pm, variable=self._def_pay, value=pm,
                           bg=C["bg"], fg=C["text"],
                           selectcolor=C["input"],
                           font=("Arial", 11),
                           cursor="hand2").pack(side=tk.LEFT, padx=(0, 16))
        self._show_pts   = tk.BooleanVar(value=cfg.get("show_points_on_bill", True))
        self._auto_clear = tk.BooleanVar(value=cfg.get("auto_clear_after_print", False))
        self._wa_confirm = tk.BooleanVar(value=cfg.get("show_whatsapp_confirm", True))
        self._show_ai_btn = tk.BooleanVar(value=cfg.get("show_ai_floating_button", True))
        self._enable_anim = tk.BooleanVar(value=cfg.get("enable_animations", True))
        self._show_below_cost_alert = tk.BooleanVar(value=cfg.get(ALERT_PREF_KEY, True))
        self._chk(bf, "Show loyalty points on bill footer", self._show_pts)
        self._chk(bf, "Auto clear bill after Print/Save",   self._auto_clear)
        self._chk(bf, "Ask confirmation before WhatsApp",   self._wa_confirm)
        self._chk(bf, "Show floating AI button",            self._show_ai_btn)
        self._chk(bf, "Enable smooth animations",           self._enable_anim)
        self._chk(bf, "Show below-cost warning banner",     self._show_below_cost_alert)

        self._v5_customers = tk.BooleanVar(value=cfg.get("use_v5_customers_db", False))
        self._v5_appointments = tk.BooleanVar(value=cfg.get("use_v5_appointments_db", False))
        self._v5_reports = tk.BooleanVar(value=cfg.get("use_v5_reports_db", False))
        self._v5_billing = tk.BooleanVar(value=cfg.get("use_v5_billing_db", False))
        self._v5_inventory = tk.BooleanVar(value=cfg.get("use_v5_inventory_db", False))
        self._v5_staff = tk.BooleanVar(value=cfg.get("use_v5_staff_db", False))
        self._v5_product_variants = tk.BooleanVar(value=cfg.get("use_v5_product_variants_db", False))
        if (
            cfg.get("show_database_rollout_controls", False)
            and getattr(getattr(self.app, "current_user", {}), "get", lambda *_: "")("role", "") == "owner"
        ):
            v5f = self._sec(f, "Advanced: Database Rollout")
            tk.Label(v5f,
                     text="Internal owner-only switches for staged v5 migration and rollback.",
                     bg=C["bg"], fg=C["muted"],
                     font=("Arial", 9), justify="left").pack(anchor="w", pady=(0, 8))
            rollout_mode = str(cfg.get("install_mode", "hybrid")).strip() or "hybrid"
            migration_done = "Yes" if cfg.get("migration_completed", False) else "No"
            migration_at = str(cfg.get("migration_completed_at", "")).strip() or "Not completed yet"
            sqlite_primary = "Yes" if cfg.get("sqlite_primary_mode", False) else "No"
            status_box = tk.Frame(v5f, bg=C["card"], padx=10, pady=8)
            status_box.pack(fill=tk.X, pady=(0, 8))
            for line in [
                f"Install Mode: {rollout_mode}",
                f"Migration Completed: {migration_done}",
                f"Migration Completed At: {migration_at}",
                f"SQLite Primary Mode: {sqlite_primary}",
            ]:
                tk.Label(
                    status_box,
                    text=line,
                    bg=C["card"],
                    fg=C["text"],
                    font=("Arial", 10),
                    justify="left",
                    anchor="w",
                ).pack(anchor="w", pady=1)
            self._chk(v5f, "Customers -> v5 SQLite tables", self._v5_customers)
            self._chk(v5f, "Appointments -> v5 SQLite tables", self._v5_appointments)
            self._chk(v5f, "Reports -> v5 SQLite tables", self._v5_reports)
            self._chk(v5f, "Billing -> v5 SQLite tables", self._v5_billing)
            self._chk(v5f, "Inventory -> v5 SQLite tables", self._v5_inventory)
            self._chk(v5f, "Staff -> v5 SQLite tables", self._v5_staff)
            self._chk(v5f, "Product Variants -> v5 SQLite tables", self._v5_product_variants)
            tk.Label(v5f,
                     text="Use these only after migration validation. Turn off a switch to fall back quickly.",
                     bg=C["bg"], fg=C["muted"],
                     font=("Arial", 9), justify="left").pack(anchor="w", pady=(6, 0))

        sf = self._sec(f, "\U0001f4bb  System")
        self._start_win = tk.BooleanVar(value=cfg.get("start_with_windows", False))
        self._chk(sf, "Start with Windows on boot", self._start_win)
        tk.Label(sf, text="* Works on Windows 10/11 (may need admin)",
                 bg=C["bg"], fg=C["muted"],
                 font=("Arial", 9)).pack(anchor="w")

        rf = self._sec(f, "\U0001f4ca  Report Defaults")
        tk.Label(rf, text="Default Period:",
                 bg=C["bg"], fg=C["muted"],
                 font=("Arial", 11)).pack(anchor="w", pady=(0, 4))
        self._def_rep = tk.StringVar(value=cfg.get("default_report_period", "This Month"))
        ttk.Combobox(rf, textvariable=self._def_rep,
                     values=["Today", "This Week", "This Month", "All"],
                     state="readonly", font=("Arial", 11),
                     width=22).pack(anchor="w")

        self._savebtn(f, "\U0001f4be  Save Preferences", self._save_prefs)

    def _save_prefs(self):
        cfg = build_preferences_payload(
            get_settings(),
            default_payment=self._def_pay.get(),
            show_points_on_bill=self._show_pts.get(),
            auto_clear_after_print=self._auto_clear.get(),
            show_whatsapp_confirm=self._wa_confirm.get(),
            show_ai_floating_button=self._show_ai_btn.get(),
            enable_animations=self._enable_anim.get(),
            show_below_cost_alert=self._show_below_cost_alert.get(),
            use_v5_customers_db=self._v5_customers.get(),
            use_v5_appointments_db=self._v5_appointments.get(),
            use_v5_reports_db=self._v5_reports.get(),
            use_v5_billing_db=self._v5_billing.get(),
            use_v5_inventory_db=self._v5_inventory.get(),
            use_v5_staff_db=self._v5_staff.get(),
            use_v5_product_variants_db=self._v5_product_variants.get(),
            start_with_windows=self._start_win.get(),
            default_report_period=self._def_rep.get(),
        )
        save_settings(cfg)
        try:
            if hasattr(self.app, "apply_runtime_preferences"):
                self.app.apply_runtime_preferences()
        except Exception as e:
            app_log(f"[_save_prefs runtime apply] {e}")
        ok  = setup_windows_startup(self._start_win.get())
        msg = preferences_saved_message(start_with_windows=self._start_win.get(), startup_ok=ok)
        messagebox.showinfo("Saved", msg)

    # ── Tab 7: Notifications ──────────────────────────────────────────────────
    def _tab_notifs(self):
        cfg = get_settings()
        f   = self._scroll("notif")

        wf = self._sec(f, "\U0001f514  Show on Startup")
        self._n_bday  = tk.BooleanVar(value=cfg.get("notif_birthday", True))
        self._n_stock = tk.BooleanVar(value=cfg.get("notif_low_stock", True))
        self._n_appts = tk.BooleanVar(value=cfg.get("notif_appointments", True))
        self._chk(wf, "\U0001f382  Birthday notifications",  self._n_bday)
        self._chk(wf, "\u26a0\ufe0f  Low stock alerts",      self._n_stock)
        self._chk(wf, "\U0001f4c5  Appointment reminders",   self._n_appts)

        tf = self._sec(f, "\u23f1\ufe0f  Popup Auto-close Time")
        tk.Label(tf, text="Popup closes automatically after:",
                 bg=C["bg"], fg=C["muted"],
                 font=("Arial", 11)).pack(anchor="w", pady=(0, 8))
        self._popup_time = tk.IntVar(value=cfg.get("notif_popup_time", 5))
        tr = tk.Frame(tf, bg=C["bg"])
        tr.pack(fill=tk.X)
        for val, lbl in [(0, "Manual only"), (3, "3 sec"),
                         (5, "5 sec"), (10, "10 sec"), (30, "30 sec")]:
            tk.Radiobutton(tr, text=lbl,
                           variable=self._popup_time, value=val,
                           bg=C["bg"], fg=C["text"],
                           selectcolor=C["input"],
                           font=("Arial", 10),
                           cursor="hand2").pack(side=tk.LEFT, padx=(0, 12))

        df = self._sec(f, "\U0001f6ab  Don't Show Again \u2014 Reset")
        dismissed = cfg.get("notif_dismissed", [])
        tk.Label(df,
                 text="Some notifications can be dismissed permanently.\n"
                      "Click below to reset all dismissed notifications.",
                 bg=C["bg"], fg=C["muted"],
                 font=("Arial", 10), justify="left").pack(anchor="w", pady=(0, 8))
        ModernButton(df, text="Reset All Dismissed", image=get_action_icon("refresh"), compound="left",
                     command=self._reset_dismissed,
                     color=C["orange"], hover_color="#d35400",
                     width=200, height=34, radius=8,
                     font=("Arial", 10, "bold"),
                     ).pack(anchor="w")
        self._dismissed_lbl = tk.Label(
            df, text=dismissed_count_label(dismissed),
            bg=C["bg"], fg=C["muted"], font=("Arial", 9))
        self._dismissed_lbl.pack(anchor="w", pady=(6, 0))

        self._savebtn(f, "\U0001f4be  Save Notification Settings",
                      self._save_notifs)

    def _reset_dismissed(self):
        cfg = reset_dismissed_payload(get_settings())
        save_settings(cfg)
        self._dismissed_lbl.config(text=dismissed_count_label([]))
        messagebox.showinfo("Reset", "All dismissed notifications reset!")

    def _save_notifs(self):
        cfg = build_notifications_payload(
            get_settings(),
            birthday=self._n_bday.get(),
            low_stock=self._n_stock.get(),
            appointments=self._n_appts.get(),
            popup_time=self._popup_time.get(),
        )
        save_settings(cfg)
        messagebox.showinfo("Saved", "Notification settings saved!")

    def _tab_advanced(self):
        from advanced_tab import render_advanced_tab

        return render_advanced_tab(self)

    def _row_entry(self, parent, label, variable, show=None, help_text=None):
        row = tk.Frame(parent, bg=C["card"])
        row.pack(fill=tk.X, pady=(4, 0))
        tk.Label(row, text=label, bg=C["card"], fg=C["muted"], font=("Arial", 10, "bold"), width=20, anchor="w").pack(side=tk.LEFT)
        entry = tk.Entry(
            row, textvariable=variable, show=show or "",
            font=("Arial", 11), bg=C["input"], fg=C["text"],
            bd=1, relief="solid",
            highlightthickness=1,
            highlightbackground=C.get("border", C["sidebar"]),
            highlightcolor=C["accent"],
            insertbackground=C["accent"]
        )
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6)
        if help_text:
            tk.Label(parent, text=help_text, bg=C["card"], fg=C["muted"],
                     font=("Arial", 9), justify="left").pack(anchor="w", padx=(140, 0), pady=(2, 0))
        return entry

    def _validate_whatsapp_provider(self):
        provider_name = self._wa_provider.get().strip()
        provider = create_provider(provider_name, settings={
            "account_id": self._wa_account_id.get().strip(),
            "sender_id": self._wa_sender_id.get().strip(),
        })
        secret_present = bool((self._wa_api_key.get() or "").strip())
        msg = whatsapp_validation_message(provider.provider_name, secret_present)
        messagebox.showinfo("WhatsApp API Validation", msg)

    def _test_whatsapp_provider(self):
        messagebox.showinfo(
            "WhatsApp API Test",
            whatsapp_test_message(self._wa_provider.get())
        )

    def _test_multibranch_connection(self):
        mgr = MultiBranchSyncManager(config={
            "server_url": self._mb_server_url.get().strip(),
            "api_key": self._mb_api_key.get().strip(),
        })
        ok, message = mgr.test_connection()
        status, color = multibranch_status_view(ok, message, self._mb_shop_id.get(), C)
        self._mb_status_lbl.config(text=f"Status: {status}", fg=color)
        messagebox.showinfo("Multi-Branch Test", self._mb_status_lbl.cget("text"))

    def _save_advanced(self):
        wa_secret = (self._wa_api_key.get() or "").strip()
        wa_saved = store_whatsapp_provider_secret(self._wa_provider.get(), wa_secret)
        secure_warnings = []
        if wa_secret and not wa_saved:
            secure_warnings.append(get_keyring_warning("the WhatsApp API secret"))
        wa_cfg = build_whatsapp_api_config(
            enabled=self._wa_api_enabled.get(),
            provider=self._wa_provider.get(),
            fallback_to_selenium=self._wa_api_fallback.get(),
            account_id=self._wa_account_id.get(),
            sender_id=self._wa_sender_id.get(),
            secret_saved=wa_saved,
        )
        mb_secret = (self._mb_api_key.get() or "").strip()
        mb_saved = store_multibranch_api_key(mb_secret)
        if mb_secret and not mb_saved:
            secure_warnings.append(get_keyring_warning("the Multi-Branch API key"))
        mb_cfg = build_multibranch_config(
            enabled=self._mb_enabled.get(),
            server_url=self._mb_server_url.get(),
            secret_saved=mb_saved,
            shop_id=self._mb_shop_id.get(),
            auto_sync=self._mb_auto_sync.get(),
            sync_interval_minutes=self._mb_interval.get(),
            sync_status=self._mb_status_lbl.cget("text"),
        )
        cfg = build_advanced_payload(
            get_settings(),
            feature_ai_assistant=self._feature_ai.get(),
            feature_mobile_viewer=self._feature_mobile.get(),
            feature_whatsapp_api=self._feature_wa_api.get(),
            feature_multibranch=self._feature_multibranch.get(),
            whatsapp_api_config=wa_cfg,
            multibranch_config=mb_cfg,
        )
        save_settings(cfg)
        self._sync_optional_tabs(cfg)
        try:
            if hasattr(self.app, "apply_runtime_feature_settings"):
                self.app.apply_runtime_feature_settings()
        except Exception as e:
            app_log(f"[_save_advanced runtime apply] {e}")
        if secure_warnings:
            messagebox.showwarning("Saved With Security Warning", ADVANCED_SAVED_MESSAGE + "\n\n" + "\n".join(secure_warnings))
        else:
            messagebox.showinfo("Saved", ADVANCED_SAVED_MESSAGE)

    def _tab_ai(self):
        from ai_settings_tab import render_ai_settings_tab

        return render_ai_settings_tab(self)

    def _save_ai(self):
        """Save AI config to salon_settings.json."""
        try:
            cfg = get_settings()
            raw_key = self._ai_key_var.get().strip()
            secure_saved = store_ai_api_key(raw_key)
            if raw_key and not secure_saved:
                messagebox.showwarning("Secure Storage Required", get_keyring_warning("the AI API key"))
            cfg["ai_config"] = build_ai_config(
                enabled=self._ai_enabled.get(),
                secure_saved=secure_saved,
                model=self._ai_model_var.get(),
            )
            save_settings(cfg)
            try:
                if hasattr(self.app, "apply_runtime_ai_settings"):
                    self.app.apply_runtime_ai_settings()
            except Exception as e:
                app_log(f"[_save_ai runtime apply] {e}")
            self._refresh_ai_status()
            msg = ai_saved_message(secure_saved)
            messagebox.showinfo("Saved", msg)
        except Exception as e:
            messagebox.showerror("Error", f"Could not save AI settings:\n{e}")

    def _refresh_ai_status(self):
        """Update the status label in AI tab."""
        try:
            ai_cfg  = get_settings().get("ai_config", {})
            enabled = ai_cfg.get("enabled", True)
            key     = load_ai_api_key(ai_cfg)
            txt, col = ai_status_view(enabled, key, C)
            self._ai_status_lbl.configure(text=txt, fg=col)
        except Exception:
            pass

    # V5.6.1 Phase 1 — Backup & Activity Log tab
    def _tab_backup(self):
        """Backup scheduling and activity log viewer entry."""
        from scheduled_backup import get_scheduled_config, save_scheduled_config
        from backup_system import get_backup_config, normalize_backup_folder, save_backup_config
        ui_host = self._tabs["backup"]
        if ui_host is None:
            return
        from tkinter import messagebox as _mb

        f = self._scroll("backup")

        # Header
        tk.Label(f, text="Backup & Activity", font=("Arial", 14, "bold"),
                 bg=C["bg"], fg=C["text"]).pack(anchor="w", pady=(0, 4))
        tk.Frame(f, bg=C["teal"], height=2).pack(fill=tk.X, pady=(0, 12))

        # ── Scheduled Backup Section ──
        tk.Label(f, text="Scheduled Backup", font=("Arial", 12, "bold"),
                 bg=C["bg"], fg=C["accent"]).pack(anchor="w", pady=(4, 4))

        sched_cfg = get_scheduled_config()
        base_cfg = get_backup_config()

        enabled_var = tk.BooleanVar(value=sched_cfg.get("enabled", False))
        freq_var = tk.StringVar(value=sched_cfg.get("frequency", "daily"))
        time_var = tk.StringVar(value=sched_cfg.get("time", "02:00"))
        retention_var = tk.StringVar(value=str(sched_cfg.get("retention", 7)))
        weekday_var = tk.StringVar(value=sched_cfg.get("weekday", "monday"))

        row = tk.Frame(f, bg=C["bg"])
        row.pack(fill=tk.X, pady=2)
        tk.Checkbutton(row, text="Enable scheduled backup",
                       variable=enabled_var, bg=C["bg"], fg=C["text"],
                       selectcolor=C["input"], font=("Arial", 10)).pack(anchor="w")

        row = tk.Frame(f, bg=C["bg"])
        row.pack(fill=tk.X, pady=2)
        tk.Label(row, text="Frequency:", bg=C["bg"], fg=C["muted"],
                 font=("Arial", 10)).pack(side="left", padx=(0, 6))
        ttk.Combobox(row, textvariable=freq_var, width=14,
                     values=["daily", "weekly"], state="readonly",
                     font=("Arial", 10)).pack(side="left", padx=(0, 12))

        tk.Label(row, text="Time (HH:MM):", bg=C["bg"], fg=C["muted"],
                 font=("Arial", 10)).pack(side="left", padx=(0, 6))
        tk.Entry(row, textvariable=time_var, width=8, font=("Arial", 10),
                 bg=C["input"], fg=C["text"]).pack(side="left", padx=(0, 12))

        tk.Label(row, text="Retain:", bg=C["bg"], fg=C["muted"],
                 font=("Arial", 10)).pack(side="left", padx=(0, 6))
        ttk.Spinbox(row, from_=1, to=30, textvariable=retention_var,
                    width=4, font=("Arial", 10)).pack(side="left", padx=(0, 12))

        tk.Label(row, text="Day:", bg=C["bg"], fg=C["muted"],
                 font=("Arial", 10)).pack(side="left", padx=(0, 6))
        ttk.Combobox(row, textvariable=weekday_var, width=10,
                     values=["monday", "tuesday", "wednesday", "thursday",
                             "friday", "saturday", "sunday"],
                     state="readonly", font=("Arial", 10)).pack(side="left")

        # Backup folder path
        folder_var = tk.StringVar(value=base_cfg.get("folder", ""))
        self._backup_folder_var = folder_var
        folder_row = tk.Frame(f, bg=C["bg"])
        folder_row.pack(fill=tk.X, pady=(6, 2), anchor="w")
        tk.Label(folder_row, text="Backup folder:", bg=C["bg"], fg=C["muted"],
                 font=("Arial", 10)).pack(side="left")
        self._backup_folder_entry = tk.Entry(
            folder_row,
            textvariable=folder_var,
            width=35,
            font=("Arial", 9),
            bg=C["input"],
            fg=C["text"],
            state="readonly",
        )
        self._backup_folder_entry.pack(side="left", padx=(6, 6))
        self._backup_folder_entry.bind("<Button-3>", self._show_settings_backup_context_menu, add="+")
        self._backup_folder_entry.bind("<Shift-F10>", self._show_settings_backup_context_menu, add="+")

        def _pick_folder():
            from tkinter import filedialog
            d = filedialog.askdirectory()
            if d:
                folder_var.set(d)

        ModernButton(folder_row, text="Browse", command=_pick_folder,
                     color=C["blue"], hover_color="#154360",
                     width=70, height=24, radius=6,
                     font=("Arial", 9)).pack(side="left")

        # Last backup / error info
        info_txt = backup_info_text(sched_cfg)
        tk.Label(f, text=info_txt, bg=C["bg"], fg=C["muted"],
                 font=("Arial", 9), justify="left").pack(anchor="w", pady=(4, 0))

        def _save_sched():
            new_cfg = build_backup_schedule_config(
                enabled=enabled_var.get(),
                frequency=freq_var.get(),
                time=time_var.get(),
                retention=retention_var.get(),
                weekday=weekday_var.get(),
            )
            save_scheduled_config(new_cfg)

            # Update base backup folder
            new_folder = normalize_backup_folder(folder_var.get().strip())
            base_cfg["folder"] = new_folder
            save_backup_config(base_cfg)

            # Restart scheduler to pick up changes
            from scheduled_backup import stop_scheduler as _stop, start_scheduler as _start
            _stop()
            if enabled_var.get():
                _start()

            _mb.showinfo("Saved", "Backup schedule saved!")

        ModernButton(f, text="Save Backup Schedule", command=_save_sched,
                     color=C["teal"], hover_color=C["blue"],
                     width=240, height=34, radius=8,
                     font=("Arial", 10, "bold")).pack(pady=(10, 16))

        # ── Activity Log Section ──
        tk.Frame(f, bg=C["sidebar"], height=1).pack(fill=tk.X, pady=(4, 10))
        tk.Label(f, text="Activity Log", font=("Arial", 12, "bold"),
                 bg=C["bg"], fg=C["accent"]).pack(anchor="w", pady=(0, 4))

        try:
            from activity_log import get_event_count
            count = get_event_count()
        except Exception:
            count = 0

        tk.Label(f, text=activity_count_text(count), bg=C["bg"], fg=C["muted"],
                 font=("Arial", 10)).pack(anchor="w", pady=(0, 8))

        def _open_log_viewer():
            try:
                from activity_log import show_activity_log_viewer
                show_activity_log_viewer(self.winfo_toplevel())
            except Exception as e:
                _mb.showerror("Error", f"Could not open activity log:\n{e}")

        ModernButton(f, text="View Activity Log", command=_open_log_viewer,
                     color=C["blue"], hover_color="#154360",
                     width=200, height=34, radius=8,
                     font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 12))

    def _tab_license(self):
        f = self._tabs["license"]
        for w in f.winfo_children():
            w.destroy()

        mgr = get_license_manager()
        status = mgr.current_status()
        self._license_status = dict(status)

        sec = self._sec(f, "License & Trial", C["purple"])
        rows = license_status_rows(status)
        for label, value in rows:
            row = tk.Frame(sec, bg=C["card"])
            row.pack(fill=tk.X, pady=4)
            tk.Label(row, text=label, bg=C["card"], fg=C["muted"], font=("Arial", 11, "bold")).pack(side=tk.LEFT)
            value_label = tk.Label(row, text=value, bg=C["card"], fg=C["text"], font=("Arial", 11))
            value_label.pack(side=tk.RIGHT)
            if label in {"Device ID", "Install ID"}:
                handler = lambda event, field=label: self._show_settings_license_context_menu(event, field)
                row.bind("<Button-3>", handler, add="+")
                row.bind("<Shift-F10>", handler, add="+")
                value_label.bind("<Button-3>", handler, add="+")
                value_label.bind("<Shift-F10>", handler, add="+")

        note = self._sec(f, "Activation", C["teal"])
        reminder_text = license_reminder_text(status)
        if reminder_text:
            tk.Label(note,
                     text=reminder_text,
                     bg=C["card"], fg=C["orange"], font=("Arial", 11, "bold")).pack(anchor="w", pady=(0, 8))
        tk.Label(note,
                 text=LICENSE_ACTIVATION_NOTE,
                 bg=C["card"], fg=C["text"], justify="left", font=("Arial", 10)).pack(anchor="w")

        btns = tk.Frame(note, bg=C["card"])
        btns.pack(fill=tk.X, pady=(12, 0))
        action_view = license_activation_action_view(status)
        if action_view["enabled"]:
            ModernButton(
                btns,
                text=str(action_view["text"]),
                bg=str(action_view["color"]),
                command=lambda: self._open_license_dialog(),
            ).pack(side=tk.LEFT)
        else:
            tk.Label(
                btns,
                text=f"  {action_view['text']}  ",
                bg=str(action_view["color"]),
                fg="white",
                font=("Arial", 10, "bold"),
                padx=10,
                pady=7,
            ).pack(side=tk.LEFT)
        ModernButton(btns, text="Refresh Status", bg=C["green"], command=self._refresh_license_tab).pack(side=tk.LEFT, padx=8)

    def _tab_about(self):
        f = self._tabs["about"]
        for w in f.winfo_children():
            w.destroy()

        # Version info
        from branding import get_about_contact_info, get_branding_value, get_company_name, get_app_name
        version = get_branding_value("product_version", "5.6")
        app_name = get_app_name()
        company = get_company_name()
        is_frozen = getattr(sys, "frozen", False)

        sec = self._sec(f, "Version", C["purple"])
        ver_rows = about_version_rows(
            app_name=app_name,
            version=version,
            company=company,
            is_frozen=is_frozen,
        )
        for label, value in ver_rows:
            row = tk.Frame(sec, bg=C["card"])
            row.pack(fill=tk.X, pady=4)
            tk.Label(row, text=label, bg=C["card"], fg=C["muted"], font=("Arial", 11, "bold")).pack(side=tk.LEFT)
            tk.Label(row, text=value, bg=C["card"], fg=C["text"], font=("Arial", 11)).pack(side=tk.RIGHT)

        contact_rows = about_contact_rows(get_about_contact_info())
        if contact_rows:
            contact_sec = self._sec(f, "Contact", C["teal"])
            for label, value in contact_rows:
                row = tk.Frame(contact_sec, bg=C["card"])
                row.pack(fill=tk.X, pady=4)
                tk.Label(
                    row,
                    text=label,
                    bg=C["card"],
                    fg=C["muted"],
                    font=("Arial", 11, "bold"),
                ).pack(side=tk.LEFT)
                tk.Label(
                    row,
                    text=value,
                    bg=C["card"],
                    fg=C["text"],
                    font=("Arial", 11),
                    justify="right",
                    wraplength=760,
                ).pack(side=tk.RIGHT)

        # VC++ Runtime check
        vc_sec = self._sec(f, "VC++ Runtime", C["teal"])
        vc_frame = tk.Frame(vc_sec, bg=C["card"])
        vc_frame.pack(fill=tk.X, pady=4)
        vc_label = tk.Label(vc_frame, text="Checking...", bg=C["card"], fg=C["muted"], font=("Arial", 10))
        vc_label.pack(side=tk.LEFT)
        vc_btn = ModernButton(vc_frame, text="Re-check", bg=C["blue"], command=lambda: self._check_vc_runtime(vc_label), width=100, height=28, radius=6, font=("Arial", 9, "bold"))
        vc_btn.pack(side=tk.RIGHT, padx=4)
        self._check_vc_runtime(vc_label)

        tk.Label(vc_sec, text=VC_RUNTIME_HELP_TEXT, bg=C["card"], fg=C["muted"],
                 font=("Arial", 9), justify="left").pack(anchor="w", pady=(4, 0))

        # Update checker
        upd_sec = self._sec(f, "Check for Updates", C["blue"])
        self._upd_status_lbl = tk.Label(upd_sec, text="Click to check for updates.", bg=C["card"], fg=C["muted"], font=("Arial", 10))
        self._upd_status_lbl.pack(anchor="w")
        manifest_row = tk.Frame(upd_sec, bg=C["card"])
        manifest_row.pack(fill=tk.X, pady=(8, 4))
        tk.Label(manifest_row, text="Manifest URL:", bg=C["card"], fg=C["muted"],
                 font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        self._upd_manifest_var = tk.StringVar(value=get_settings().get("update_manifest_url", ""))
        self._upd_manifest_entry = tk.Entry(
            manifest_row,
            textvariable=self._upd_manifest_var,
            bg=C["input"],
            fg=C["text"],
            bd=0,
            insertbackground=C["accent"],
            font=("Arial", 10),
        )
        self._upd_manifest_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 8), ipady=4)
        self._upd_manifest_entry.bind("<Button-3>", self._show_settings_about_context_menu, add="+")
        self._upd_manifest_entry.bind("<Shift-F10>", self._show_settings_about_context_menu, add="+")
        ModernButton(manifest_row, text="Save URL", bg=C["green"], hover_color="#1a7a45",
                     command=self._save_update_manifest_url, width=92, height=28, radius=6,
                     font=("Arial", 9, "bold")).pack(side=tk.RIGHT)
        upd_btn = ModernButton(upd_sec, text="Check Now", bg=C["blue"], hover_color="#154360",
                               command=self._manual_update_check, width=200, height=34, radius=8,
                               font=("Arial", 10, "bold"))
        upd_btn.pack(anchor="w", pady=(8, 0))
        tk.Label(upd_sec,
                 text=UPDATE_MANIFEST_HELP_TEXT,
                 bg=C["card"], fg=C["muted"], font=("Arial", 9), justify="left").pack(anchor="w", pady=(4, 0))

        # Powered by
        tk.Label(f, text="Powered by B-Lite Technologies", bg=C["bg"], fg=C["muted"],
                 font=("Arial", 9, "italic")).pack(side=tk.BOTTOM, pady=(8, 0))

    def _check_vc_runtime(self, label_widget):
        try:
            import ctypes
            # Load the CRT DLL used by many Windows apps
            ctypes.CDLL("vcruntime140.dll")
            text, color = vc_runtime_status(True)
        except Exception:
            text, color = vc_runtime_status(False)
        label_widget.configure(text=text, fg=color)

    def _manual_update_check(self):
        from update_checker import UpdateChecker
        checker = UpdateChecker(settings_getter=get_settings)
        manifest_url = get_settings().get("update_manifest_url", "").strip()
        if not manifest_url:
            self._upd_status_lbl.configure(text="Set a manifest URL first, then try again.", fg="#e67e22")
            messagebox.showinfo("Update Check", "Set a manifest URL in the About tab before checking for updates.")
            return

        self._upd_status_lbl.configure(text="Checking...", fg=C["blue"])

        def show_available(info):
            ver = info.get("version", "?")
            dl = info.get("download_url", "")
            self._upd_status_lbl.configure(text=f"Update available: v{ver}", fg="#27ae60")
            msg, has_download = update_available_message(info)
            if has_download:
                if messagebox.askyesno("Update Available", msg):
                    import webbrowser
                    webbrowser.open(dl)
            else:
                messagebox.showinfo("Update Available", msg)

        def show_none():
            self._upd_status_lbl.configure(text="No updates found.", fg=C["muted"])

        def show_error():
            self._upd_status_lbl.configure(text="Could not check for updates. Verify the manifest URL.", fg="#e67e22")

        def worker():
            info = checker.check_sync()
            if info is None:
                self.after(0, show_error)
            elif checker.is_update_available(info):
                self.after(0, lambda: show_available(info))
            else:
                self.after(0, show_none)

        import threading
        threading.Thread(target=worker, daemon=True).start()

    def _save_update_manifest_url(self):
        cfg = build_update_manifest_payload(get_settings(), self._upd_manifest_var.get())
        save_settings(cfg)
        self._upd_status_lbl.configure(text="Manifest URL saved.", fg="#27ae60")

    def _open_license_dialog(self):
        open_activation_dialog(parent=self, blocking=False)
        self._refresh_license_tab()

    def _refresh_license_tab(self):
        try:
            self._tab_license()
        except Exception as e:
            app_log(f"[license tab refresh] {e}")

    def _popup_context_menu(self, event, menu, fallback_widget=None):
        x_root = getattr(event, "x_root", None)
        y_root = getattr(event, "y_root", None)
        if x_root is None or y_root is None:
            widget = fallback_widget or self
            x_root = widget.winfo_rootx() + 24
            y_root = widget.winfo_rooty() + 24
        menu.tk_popup(x_root, y_root)
        menu.grab_release()
        return "break"

    def _show_settings_backup_context_menu(self, event):
        try:
            from shared.context_menu.constants import WidgetType
            from shared.context_menu.menu_context_factory import build_context
            from shared.context_menu.renderer import renderer_service
            from shared.context_menu_definitions.settings_context_menu import get_backup_sections

            folder_path = self._backup_folder_var.get().strip() if self._backup_folder_var is not None else ""
            context_data = backup_context_data(folder_path)
            context = build_context(
                "settings",
                entity_type=context_data["entity_type"],
                selected_row=context_data["selected_row"],
                selected_text=context_data["selected_text"],
                user_role=self.app.current_user.get("role", "") if getattr(self.app, "current_user", None) else "",
                widget_type=WidgetType.ENTRY,
                widget_id=context_data["widget_id"],
                extra=context_data["extra"],
            )
            menu = renderer_service.build_menu(self, get_backup_sections(), context)
            return self._popup_context_menu(event, menu, self._backup_folder_entry or self)
        except Exception as exc:
            app_log(f"[settings backup context menu] {exc}")
            return "break"

    def _show_settings_license_context_menu(self, event, field_label: str = ""):
        try:
            from shared.context_menu.constants import WidgetType
            from shared.context_menu.menu_context_factory import build_context
            from shared.context_menu.renderer import renderer_service
            from shared.context_menu_definitions.settings_context_menu import get_license_sections

            context_data = license_context_data(self._license_status, field_label)
            context = build_context(
                "settings",
                entity_type=context_data["entity_type"],
                selected_row=context_data["selected_row"],
                selected_text=context_data["selected_text"],
                user_role=self.app.current_user.get("role", "") if getattr(self.app, "current_user", None) else "",
                widget_type=WidgetType.CARD,
                widget_id=context_data["widget_id"],
                extra=context_data["extra"],
            )
            menu = renderer_service.build_menu(self, get_license_sections(), context)
            return self._popup_context_menu(event, menu, self)
        except Exception as exc:
            app_log(f"[settings license context menu] {exc}")
            return "break"

    def _show_settings_about_context_menu(self, event):
        try:
            from shared.context_menu.constants import WidgetType
            from shared.context_menu.menu_context_factory import build_context
            from shared.context_menu.renderer import renderer_service
            from shared.context_menu_definitions.settings_context_menu import get_about_sections

            manifest_url = self._upd_manifest_var.get().strip() if hasattr(self, "_upd_manifest_var") else ""
            context_data = about_context_data(manifest_url)
            context = build_context(
                "settings",
                entity_type=context_data["entity_type"],
                selected_row=context_data["selected_row"],
                selected_text=context_data["selected_text"],
                user_role=self.app.current_user.get("role", "") if getattr(self.app, "current_user", None) else "",
                widget_type=WidgetType.ENTRY,
                widget_id=context_data["widget_id"],
                extra=context_data["extra"],
            )
            menu = renderer_service.build_menu(self, get_about_sections(), context)
            return self._popup_context_menu(event, menu, self._upd_manifest_entry or self)
        except Exception as exc:
            app_log(f"[settings about context menu] {exc}")
            return "break"

    def _register_settings_context_menu_callbacks(self):
        from shared.context_menu.action_adapter import action_adapter
        from shared.context_menu.clipboard_service import clipboard_service
        from shared.context_menu_definitions.settings_context_menu import SettingsContextAction

        action_adapter.register(
            SettingsContextAction.COPY_BACKUP_FOLDER,
            lambda _ctx, _act: clipboard_service.copy_text(self, self._backup_folder_var.get().strip() if self._backup_folder_var is not None else ""),
        )
        action_adapter.register(
            SettingsContextAction.COPY_DEVICE_ID,
            lambda _ctx, _act: clipboard_service.copy_text(self, str(self._license_status.get("device_id", "")).strip()),
        )
        action_adapter.register(
            SettingsContextAction.COPY_INSTALL_ID,
            lambda _ctx, _act: clipboard_service.copy_text(self, str(self._license_status.get("install_id", "")).strip()),
        )
        action_adapter.register(SettingsContextAction.OPEN_LICENSE_DIALOG, lambda _ctx, _act: self._open_license_dialog())
        action_adapter.register(SettingsContextAction.REFRESH_LICENSE, lambda _ctx, _act: self._refresh_license_tab())
        action_adapter.register(
            SettingsContextAction.COPY_MANIFEST_URL,
            lambda _ctx, _act: clipboard_service.copy_text(self, self._upd_manifest_var.get().strip() if hasattr(self, "_upd_manifest_var") else ""),
        )
        action_adapter.register(SettingsContextAction.SAVE_MANIFEST_URL, lambda _ctx, _act: self._save_update_manifest_url())
        action_adapter.register(SettingsContextAction.CHECK_UPDATES, lambda _ctx, _act: self._manual_update_check())

    def refresh(self):
        pass



