"""
dashboard.py  –  BOBY'S Salon : Dashboard — home screen with live stats
FIXES:
  - Fix R5g–R5m: try/except crash prevention (all preserved)
UI v3.0:
  - Modern SaaS stat cards with icon + accent bottom line
  - Rounded ModernButton for Refresh + WhatsApp buttons
  - Section headers with divider lines
  - Payment & Top Services panels — card style
  - Appointments treeview in a modern card container
  - Birthday cards — modern row with pill badge
  - All existing colors/theme/logic unchanged
"""
import tkinter as tk
from tkinter import ttk
from datetime import datetime, date, timedelta
import csv, os
import time
from collections import defaultdict
from utils import (C, safe_float, fmt_currency, F_REPORT,
                   today_str, month_str, load_json,
                   F_APPOINTMENTS, F_CUSTOMERS, F_INVENTORY,
                   popup_window, app_log)
from ui_theme import ModernButton, stat_card_v3, status_badge
from ui_responsive import get_responsive_metrics, scaled_value, fit_toplevel
from branding import get_company_name
from src.blite_v6.app.window_lifecycle import hide_while_building, reveal_when_ready

_DASHBOARD_CACHE = {}


def _get_cached_value(cache_key, dependency_key, builder, ttl_seconds=2.0):
    now = time.time()
    cached = _DASHBOARD_CACHE.get(cache_key)
    if cached and cached["dependency"] == dependency_key and (now - cached["time"]) <= ttl_seconds:
        return cached["value"]
    value = builder()
    _DASHBOARD_CACHE[cache_key] = {
        "dependency": dependency_key,
        "time": now,
        "value": value,
    }
    return value


def _today_stats():
    def _builder():
        td = today_str()
        mo = date.today().strftime("%Y-%m")
        td_rev = mo_rev = all_rev = 0.0
        td_bills = mo_bills = 0
        payment_counts = defaultdict(float)
        top_services = defaultdict(float)

        if os.path.exists(F_REPORT):
            try:
                with open(F_REPORT, "r", encoding="utf-8") as f:
                    r = csv.reader(f)
                    hdr = next(r, None)
                    ti = 5 if (hdr and len(hdr) >= 6) else 3
                    pi = 4 if (hdr and len(hdr) >= 6) else -1
                    ir = 6 if (hdr and len(hdr) >= 7) else -1
                    for row in r:
                        if not row or len(row) <= ti:
                            continue
                        val = safe_float(row[ti])
                        due_clearance = 0.0
                        if ir > 0 and len(row) > ir:
                            for seg in row[ir].split("|"):
                                parts = seg.split("~")
                                if len(parts) >= 4 and (
                                    parts[0] == "due_clearance"
                                    or parts[1].strip().lower() == "previous due clearance"
                                ):
                                    try:
                                        due_clearance += float(parts[2]) * float(parts[3])
                                    except Exception:
                                        pass
                        sale_val = max(0.0, val - due_clearance)
                        all_rev += sale_val
                        if row[0][:10] == td:
                            td_rev += sale_val
                            td_bills += 1
                            if pi > 0 and len(row) > pi:
                                payment_counts[row[pi]] += sale_val
                        if row[0][:7] == mo:
                            mo_rev += sale_val
                            mo_bills += 1
                        if ir > 0 and len(row) > ir:
                            for seg in row[ir].split("|"):
                                parts = seg.split("~")
                                if len(parts) >= 4 and parts[0] == "services" and parts[1].strip().lower() != "previous due clearance":
                                    try:
                                        top_services[parts[1]] += float(parts[2]) * int(parts[3])
                                    except Exception:
                                        pass
            except Exception as e:
                app_log(f"[_today_stats] {e}")

        return {
            "td_rev": td_rev,
            "mo_rev": mo_rev,
            "all_rev": all_rev,
            "td_bills": td_bills,
            "mo_bills": mo_bills,
            "payment": dict(payment_counts),
            "top_svc": sorted(top_services.items(), key=lambda x: x[1], reverse=True)[:5],
        }

    dependency_key = os.path.getmtime(F_REPORT) if os.path.exists(F_REPORT) else 0
    return _get_cached_value("today_stats", dependency_key, _builder)


def _today_appointments():
    def _builder():
        merged = []
        seen = set()
        td = today_str()

        def _add(row):
            key = (
                str(row.get("date", "")),
                str(row.get("time", "")),
                str(row.get("customer", "")),
                str(row.get("phone", "")),
                str(row.get("service", "")),
            )
            if key in seen:
                return
            seen.add(key)
            merged.append(row)

        try:
            appts = load_json(F_APPOINTMENTS, [])
            for a in appts:
                if a.get("date", "") == td:
                    _add(dict(a))
        except Exception as e:
            app_log(f"[_today_appointments json] {e}")

        try:
            from booking_calendar import list_bookings, _time_display
            for b in list_bookings(td):
                status = str(b.get("status", "")).strip().lower()
                if status in {"cancelled", "no_show"}:
                    continue
                start = str(b.get("start_time", "")).strip()
                end = str(b.get("end_time", "")).strip()
                time_text = _time_display(start)
                if end:
                    time_text = f"{time_text} - {_time_display(end)}"
                _add({
                    "date": td,
                    "time": time_text,
                    "customer": b.get("customer_name", ""),
                    "phone": b.get("phone", ""),
                    "service": b.get("service", ""),
                    "staff": b.get("staff", ""),
                    "status": "Scheduled" if status == "booked" else status.title(),
                })
        except Exception as e:
            app_log(f"[_today_appointments bookings] {e}")
        return merged

    dependency_parts = []
    for path in (F_APPOINTMENTS,):
        try:
            dependency_parts.append(os.path.getmtime(path) if os.path.exists(path) else 0)
        except Exception:
            dependency_parts.append(0)
    try:
        from db import DB_PATH
        dependency_parts.append(os.path.getmtime(DB_PATH) if os.path.exists(DB_PATH) else 0)
    except Exception:
        dependency_parts.append(time.time())
    dependency_key = tuple(dependency_parts)
    return _get_cached_value("today_appointments", dependency_key, _builder)


def _birthday_today():
    def _builder():
        try:
            customers = load_json(F_CUSTOMERS, {})
            today_md = date.today().strftime("-%m-%d")
            return [c for c in customers.values()
                    if c.get("birthday", "").endswith(today_md)]
        except Exception as e:
            app_log(f"[_birthday_today] {e}")
            return []
    dependency_key = os.path.getmtime(F_CUSTOMERS) if os.path.exists(F_CUSTOMERS) else 0
    return _get_cached_value("birthday_today", dependency_key, _builder)


def _low_stock_count():
    def _builder():
        try:
            from inventory import get_inventory
            inv = get_inventory()
            return sum(
                1 for item in inv.values()
                if safe_float(item.get("qty", 0), 0) <= safe_float(item.get("min_stock", 5), 5)
            )
        except Exception as e:
            app_log(f"[_low_stock_count] {e}")
            return 0
    try:
        from db import DB_PATH
        dependency_key = os.path.getmtime(DB_PATH) if os.path.exists(DB_PATH) else time.time()
    except Exception:
        dependency_key = time.time()
    return _get_cached_value("low_stock_count", dependency_key, _builder)


class DashboardFrame(tk.Frame):

    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self._responsive = get_responsive_metrics(parent.winfo_toplevel())
        self._dashboard_signature = None
        self._chart_manager = None
        self._canvas = None
        self._scrollbar = None
        self._body = None
        self._mw_bound_widgets = set()
        self._built = False
        self._build_scheduled = False
        self._show_bootstrap_placeholder()
        self._schedule_build()

    def _show_bootstrap_placeholder(self):
        for w in self.winfo_children():
            try:
                w.destroy()
            except Exception:
                pass
        holder = tk.Frame(self, bg=C["bg"])
        holder.pack(fill=tk.BOTH, expand=True)
        tk.Label(
            holder,
            text="Loading Dashboard...",
            font=("Segoe UI", 11, "bold"),
            bg=C["bg"],
            fg=C["muted"],
        ).pack(expand=True)

    def _schedule_build(self):
        if self._build_scheduled or self._built:
            return
        self._build_scheduled = True
        self.after(1, self._build_deferred)

    def _build_deferred(self):
        self._build_scheduled = False
        if not self.winfo_exists() or self._built:
            return
        self._build()
        self._built = True

    def _build(self):
        """Build/rebuild the full dashboard shell with the current theme from C[]."""
        self._mw_bound_widgets.clear()
        # Destroy ALL existing children so theme colors are fully applied fresh
        for w in self.winfo_children():
            try:
                w.destroy()
            except Exception:
                pass
        self.configure(bg=C["bg"])

        self._responsive = get_responsive_metrics(self.winfo_toplevel())
        compact = self._responsive["mode"] == "compact"

        # ── Header ──────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=C["card"], pady=10)
        hdr.pack(fill=tk.X)

        left_f = tk.Frame(hdr, bg=C["card"])
        left_f.pack(side=tk.LEFT, padx=20)
        tk.Label(left_f, text="📈  Dashboard",
                 font=("Segoe UI", 14, "bold"),
                 bg=C["card"], fg=C["text"]).pack(anchor="w")
        tk.Label(left_f, text="Live shop overview",
                 font=("Segoe UI", 10),
                 bg=C["card"], fg=C["muted"]).pack(anchor="w")

        self.time_lbl = tk.Label(hdr, text="",
                                  font=("Segoe UI", 10),
                                  bg=C["card"], fg=C["muted"])
        self.time_lbl.pack(side=tk.RIGHT, padx=(0, 20))
        self._tick()

        ModernButton(hdr, text="🔄  Refresh",
                     command=self.refresh,
                     color=C["teal"], hover_color=C["blue"],
                     width=scaled_value(120, 112, 96),
                     height=scaled_value(34, 32, 28), radius=8,
                     font=("Segoe UI", 10 if compact else 9, "bold"),
                     ).pack(side=tk.RIGHT, padx=(0, 10), pady=6)

        # Accent divider — uses theme accent color
        tk.Frame(self, bg=C["teal"], height=2).pack(fill=tk.X)

        # ── Scrollable canvas ────────────────────────────────────────
        canvas = tk.Canvas(self, bg=C["bg"], highlightthickness=0)
        vsb    = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(fill=tk.BOTH, expand=True)

        self._body = tk.Frame(canvas, bg=C["bg"])
        self._win  = canvas.create_window((0, 0), window=self._body, anchor="nw")
        self._body.bind("<Configure>",
                         lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(self._win, width=e.width))

        self._canvas = canvas
        self._scrollbar = vsb
        self._tree_resize_jobs = {}

        self._populate()
        self._install_scroll_bindings()

    def _wheel_units(self, event) -> int:
        try:
            num = getattr(event, "num", None)
            if num == 4:
                return -1
            if num == 5:
                return 1
            delta = int(getattr(event, "delta", 0))
            if delta == 0:
                return 0
            units = int(-delta / 120)
            if units == 0:
                units = -1 if delta > 0 else 1
            return units
        except Exception:
            return 0

    def _on_dashboard_mousewheel(self, event):
        try:
            if not self.winfo_exists():
                return
            if getattr(self.app, "current_page_key", "") != "dashboard":
                return
            if not getattr(self, "_canvas", None) or not getattr(self, "_scrollbar", None):
                return
            if self._scrollbar.get() == (0.0, 1.0):
                return
            units = self._wheel_units(event)
            if units == 0:
                return
            self._canvas.yview_scroll(units, "units")
        except Exception:
            pass

    def _bind_mousewheel_recursive(self, widget):
        wid = str(widget)
        already_bound = wid in self._mw_bound_widgets
        try:
            if not already_bound:
                widget.bind("<MouseWheel>", self._on_dashboard_mousewheel, add="+")
                widget.bind("<Button-4>", self._on_dashboard_mousewheel, add="+")
                widget.bind("<Button-5>", self._on_dashboard_mousewheel, add="+")
                self._mw_bound_widgets.add(wid)
        except Exception:
            pass
        try:
            for child in widget.winfo_children():
                self._bind_mousewheel_recursive(child)
        except Exception:
            pass

    def _install_scroll_bindings(self):
        try:
            self._bind_mousewheel_recursive(self)
        except Exception:
            pass

    def _tick(self):
        now = datetime.now().strftime("%A, %d %B %Y   %I:%M %p")
        self.time_lbl.config(text=now)
        self.after(30000, self._tick)

    def _populate(self):
        """Show loading screen, then build dashboard content in background thread."""
        # Show loading overlay immediately
        self._show_loading()
        # Build data + charts in background to avoid UI freeze
        import threading
        t = threading.Thread(target=self._populate_bg, daemon=True)
        t.start()

    def _show_loading(self):
        """Render a centered loading indicator over the body canvas."""
        try:
            for w in self._body.winfo_children():
                w.destroy()
        except Exception:
            pass
        loading_f = tk.Frame(self._body, bg=C["bg"])
        loading_f.pack(fill=tk.BOTH, expand=True, pady=60)

        # Spinner text (rotating braille dots)
        self._spinner_chars = ["⣹", "⢺", "⢷", "⣯", "⣟", "⢿", "⣻", "⣽"]
        self._spinner_idx = 0
        self._spinner_lbl = tk.Label(loading_f, text=self._spinner_chars[0],
                                      font=("Segoe UI", 48), bg=C["bg"],
                                      fg=C.get("teal", "#3B82F6"))
        self._spinner_lbl.pack(pady=(0, 12))

        tk.Label(loading_f, text="Loading Dashboard...", font=("Segoe UI", 14),
                 bg=C["bg"], fg=C.get("muted", "#9ca3af")).pack()
        tk.Label(loading_f, text="Fetching live data & charts", font=("Segoe UI", 10),
                 bg=C["bg"], fg=C.get("muted", "#9ca3af")).pack(pady=(4, 0))

        self._spinner_running = True
        self._animate_spinner()
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        self._install_scroll_bindings()

    def _animate_spinner(self):
        if not getattr(self, "_spinner_running", False):
            return
        try:
            self._spinner_idx = (self._spinner_idx + 1) % len(self._spinner_chars)
            self._spinner_lbl.config(text=self._spinner_chars[self._spinner_idx])
            self._spinner_job = self.after(80, self._animate_spinner)
        except Exception:
            pass

    def _stop_spinner(self):
        self._spinner_running = False
        if getattr(self, "_spinner_job", None):
            try:
                self.after_cancel(self._spinner_job)
            except Exception:
                pass

    def _populate_bg(self):
        """Run heavy data fetch in background, then schedule UI build on main thread."""
        try:
            # Pre-fetch all data outside main thread
            stats = _today_stats()
            appts = _today_appointments()
            bdays = _birthday_today()
            low   = _low_stock_count()
            # Schedule UI rendering back on main thread
            self.after(0, lambda: self._populate_inner(stats, appts, bdays, low))
        except Exception as e:
            app_log(f"[_populate_bg] {e}")
            self.after(0, lambda: self._stop_spinner())

    def _populate_inner(self, stats=None, appts=None, bdays=None, low=None):
        # Stop spinner animation
        self._stop_spinner()

        # Safely destroy old graphical instance if it exists to prevent memory leaks
        if getattr(self, "_chart_manager", None):
            self._chart_manager.safe_destroy_all()
        try:
            from dashboard_analytics import DashboardChartManager
            self._chart_manager = DashboardChartManager()
        except ImportError:
            self._chart_manager = None

        # Clear existing widgets
        for widget in self._body.winfo_children():
            widget.destroy()

        compact = self._responsive["mode"] == "compact"
        # Use pre-fetched data or fetch now
        if stats is None: stats = _today_stats()
        if appts is None: appts = _today_appointments()
        if bdays is None: bdays = _birthday_today()
        if low   is None: low   = _low_stock_count()

        signature = (
            stats.get("td_rev"),
            stats.get("td_bills"),
            stats.get("mo_rev"),
            stats.get("mo_bills"),
            stats.get("all_rev"),
            tuple(sorted(stats.get("payment", {}).items())),
            tuple(stats.get("top_svc", [])),
            tuple(tuple(sorted(a.items())) for a in appts),
            tuple(tuple(sorted(c.items())) for c in bdays),
            low,
            compact,
        )
        self._dashboard_signature = signature

        pad = dict(padx=16, pady=12)

        def _make_card_row(parent, card_data, is_clickable=True, title=None):
            outer = tk.Frame(parent, bg=C["bg"])
            outer.pack(fill=tk.X, **pad)
            
            if title:
                hdr = tk.Frame(outer, bg=C["bg"])
                hdr.pack(fill=tk.X, pady=(0, 8))
                tk.Label(hdr, text=title, font=("Segoe UI", 12),
                         bg=C["bg"], fg=C["muted"]).pack(side=tk.LEFT)

            row_frame = tk.Frame(outer, bg=C["bg"])
            row_frame.pack(fill=tk.X)

            for item in card_data:
                if len(item) == 5:
                    lbl, val, icon, col, cmd = item
                    card = self._stat_card(row_frame, lbl, val, accent_color=col, click_cmd=cmd, icon=icon)
                else:
                    lbl, val, icon, col = item
                    card = self._stat_card(row_frame, lbl, val, accent_color=col, icon=icon)
                card.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)

            return row_frame

        # ── Row 1 : Revenue cards ───
        cards1 = [
            ("Today Revenue",    fmt_currency(stats["td_rev"]),  "💰", C.get("teal", "#3b82f6"), lambda: self._show_bills("today")),
            ("Today Bills",      str(stats["td_bills"]),         "🧾", C.get("blue", "#22c55e"), lambda: self._show_bills("today")),
            ("Month Revenue",    fmt_currency(stats["mo_rev"]),  "📅", C.get("purple", "#a855f7"), lambda: self._show_bills("month")),
            ("Month Bills",      str(stats["mo_bills"]),         "📊", C.get("orange", "#f59e0b"), lambda: self._show_bills("month")),
            ("All Time Revenue", fmt_currency(stats["all_rev"]), "🏆", C.get("teal", "#3b82f6"), lambda: self._show_bills("all")),
        ]
        _make_card_row(self._body, cards1, is_clickable=True, title="Revenue Overview")

        # ── Row 2 : Alerts ───
        pending = sum(1 for a in appts if a.get("status") == "Scheduled")
        alert_data = [
            ("Today Appts",     str(len(appts)), "📅", C.get("blue", "#3b82f6") if appts else C["sidebar"]),
            ("Birthdays Today", str(len(bdays)), "🎂", C.get("accent", "#a855f7") if bdays else C["sidebar"]),
            ("Low Stock Items", str(low),        "⚠️", C.get("red", "#ef4444") if low   else C["sidebar"]),
            ("Pending Appts",   str(pending),    "🕐", C.get("orange", "#f59e0b")),
        ]
        _make_card_row(self._body, alert_data, is_clickable=False, title="Quick Stats")

        # ── Row 3 : MAIN CONTENT AREA (70/30 Split) ───
        if self._chart_manager:
            r3_outer = tk.Frame(self._body, bg=C["bg"])
            r3_outer.pack(fill=tk.X, padx=16, pady=(0, 12))
            r3_outer.columnconfigure(0, weight=7)
            r3_outer.columnconfigure(1, weight=3)
            r3_outer.rowconfigure(0, weight=1)

            # Left: Line chart card with title bar
            left_card = tk.Frame(r3_outer, bg=C["card"], relief="flat")
            left_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
            left_card.rowconfigure(1, weight=1)
            left_card.columnconfigure(0, weight=1)

            left_title_bar = tk.Frame(left_card, bg=C["card"], padx=14, pady=8)
            left_title_bar.grid(row=0, column=0, sticky="ew")
            tk.Label(left_title_bar, text="7-Day Revenue Trend", font=("Segoe UI", 12, "bold"),
                     bg=C["card"], fg=C["text"]).pack(side=tk.LEFT)
            period_lbl = tk.Label(left_title_bar, text="Last 7 Days", font=("Segoe UI", 9),
                                  bg=C["sidebar"], fg=C["muted"], padx=8, pady=3)
            period_lbl.pack(side=tk.RIGHT)

            left_chart_f = tk.Frame(left_card, bg=C["card"])
            left_chart_f.grid(row=1, column=0, sticky="nsew")
            left_chart_f.rowconfigure(0, weight=1)
            left_chart_f.columnconfigure(0, weight=1)
            self._chart_manager.render_cashflow_chart(left_chart_f)

            # Right: Two stacked chart cards
            right_col = tk.Frame(r3_outer, bg=C["bg"])
            right_col.grid(row=0, column=1, sticky="nsew")
            right_col.columnconfigure(0, weight=1)
            right_col.rowconfigure(0, weight=1)
            right_col.rowconfigure(1, weight=1)

            top_right_card = tk.Frame(right_col, bg=C["card"], relief="flat")
            top_right_card.grid(row=0, column=0, sticky="nsew", pady=(0, 6))
            top_right_card.rowconfigure(1, weight=1)
            top_right_card.columnconfigure(0, weight=1)
            top_right_title = tk.Frame(top_right_card, bg=C["card"], padx=14, pady=6)
            top_right_title.grid(row=0, column=0, sticky="ew")
            tk.Label(top_right_title, text="Top 5 Services (All Time)", font=("Segoe UI", 11, "bold"),
                     bg=C["card"], fg=C["text"]).pack(side=tk.LEFT)
            top_chart_f = tk.Frame(top_right_card, bg=C["card"])
            top_chart_f.grid(row=1, column=0, sticky="nsew")
            top_chart_f.rowconfigure(0, weight=1)
            top_chart_f.columnconfigure(0, weight=1)
            self._chart_manager.render_top_items_chart(top_chart_f)

            bot_right_card = tk.Frame(right_col, bg=C["card"], relief="flat")
            bot_right_card.grid(row=1, column=0, sticky="nsew", pady=(6, 0))
            bot_right_card.rowconfigure(1, weight=1)
            bot_right_card.columnconfigure(0, weight=1)
            bot_right_title = tk.Frame(bot_right_card, bg=C["card"], padx=14, pady=6)
            bot_right_title.grid(row=0, column=0, sticky="ew")
            tk.Label(bot_right_title, text="Revenue by Payment Mode", font=("Segoe UI", 11, "bold"),
                     bg=C["card"], fg=C["text"]).pack(side=tk.LEFT)
            bot_chart_f = tk.Frame(bot_right_card, bg=C["card"])
            bot_chart_f.grid(row=1, column=0, sticky="nsew")
            bot_chart_f.rowconfigure(0, weight=1)
            bot_chart_f.columnconfigure(0, weight=1)
            self._chart_manager.render_payment_methods_chart(bot_chart_f)

        # ── Row 4 : BOTTOM SECTION (3 columns) ───
        r4_bottom = tk.Frame(self._body, bg=C["bg"])
        r4_bottom.pack(fill=tk.X, **pad)
        r4_bottom.columnconfigure(0, weight=1, uniform="bottom_cols")
        r4_bottom.columnconfigure(1, weight=1, uniform="bottom_cols")
        r4_bottom.columnconfigure(2, weight=1, uniform="bottom_cols")
        r4_bottom.rowconfigure(0, weight=1)

        # Col 0: Today Payments
        pm_outer = tk.Frame(r4_bottom, bg=C["card"], relief="flat")
        pm_outer.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        pm_hdr_f = tk.Frame(pm_outer, bg=C["card"], padx=14, pady=12)
        pm_hdr_f.pack(fill=tk.X)
        pm_icon = tk.Label(pm_hdr_f, text="💳", font=("Segoe UI Emoji", 14), bg=C["card"], fg=C["lime"])
        pm_icon.pack(side=tk.LEFT, padx=(0, 6))
        tk.Label(pm_hdr_f, text="Today's Payments", font=("Segoe UI", 12, "bold"),
                 bg=C["card"], fg=C["text"]).pack(side=tk.LEFT)
        tk.Frame(pm_outer, bg=C["sidebar"], height=1).pack(fill=tk.X, padx=14)
        pm_f = tk.Frame(pm_outer, bg=C["card"], padx=14, pady=12)
        pm_f.pack(fill=tk.BOTH, expand=True)

        pm = stats.get("payment", {})
        if pm:
            total_pm = 0
            for method, amt in pm.items():
                row = tk.Frame(pm_f, bg=C["card"])
                row.pack(fill=tk.X, pady=4)
                tk.Label(row, text=method, bg=C["card"], fg=C["muted"],
                         font=("Segoe UI", 11), width=7 if compact else 8,
                         anchor="w").pack(side=tk.LEFT)
                tk.Label(row, text=fmt_currency(amt), bg=C["card"], fg=C["text"],
                         font=("Segoe UI", 12, "bold")).pack(side=tk.RIGHT)
                total_pm += amt
            tk.Frame(pm_f, bg=C["sidebar"], height=1).pack(fill=tk.X, pady=(8, 4))
            total_row = tk.Frame(pm_f, bg=C["card"])
            total_row.pack(fill=tk.X)
            tk.Label(total_row, text="Total Payments", bg=C["card"], fg=C["muted"],
                     font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT)
            tk.Label(total_row, text=fmt_currency(total_pm), bg=C["card"], fg=C["text"],
                     font=("Segoe UI", 13, "bold")).pack(side=tk.RIGHT)
        else:
            tk.Label(pm_f, text="No bills today", bg=C["card"], fg=C["muted"],
                     font=("Segoe UI", 11)).pack()

        # Col 1: Top Services List
        ts_outer = tk.Frame(r4_bottom, bg=C["card"], relief="flat")
        ts_outer.grid(row=0, column=1, sticky="nsew", padx=(6, 6))
        ts_hdr_f = tk.Frame(ts_outer, bg=C["card"], padx=14, pady=12)
        ts_hdr_f.pack(fill=tk.X)
        ts_icon = tk.Label(ts_hdr_f, text="🏆", font=("Segoe UI Emoji", 14), bg=C["card"], fg=C["gold"])
        ts_icon.pack(side=tk.LEFT, padx=(0, 6))
        tk.Label(ts_hdr_f, text="Top 5 Services (All Time)", font=("Segoe UI", 12, "bold"),
                 bg=C["card"], fg=C["text"]).pack(side=tk.LEFT)
        tk.Frame(ts_outer, bg=C["sidebar"], height=1).pack(fill=tk.X, padx=14)
        ts_f = tk.Frame(ts_outer, bg=C["card"], padx=14, pady=12)
        ts_f.pack(fill=tk.BOTH, expand=True)

        top_svc = stats.get("top_svc", [])
        if top_svc:
            total_qty = 0
            for i, (svc, amt) in enumerate(top_svc):
                row = tk.Frame(ts_f, bg=C["card"])
                row.pack(fill=tk.X, pady=4)
                rank_colors = [C["gold"], C["muted"], C["muted"], C["muted"], C["muted"]]
                tk.Label(row, text=f"{i+1}", bg=C["card"], fg=rank_colors[i],
                         font=("Segoe UI", 12, "bold"), width=2, anchor="w").pack(side=tk.LEFT)
                tk.Label(row, text=svc[:22 if compact else 26], bg=C["card"], fg=C["text"],
                         font=("Segoe UI", 11), anchor="w").pack(side=tk.LEFT, padx=(4, 0), fill=tk.X, expand=True)
                qty_val = int(float(amt))
                pill = tk.Label(row, text=str(qty_val), bg=C["sidebar"], fg=C["lime"],
                                font=("Segoe UI", 10, "bold"), padx=8, pady=2)
                pill.pack(side=tk.RIGHT)
                total_qty += qty_val
            tk.Frame(ts_f, bg=C["sidebar"], height=1).pack(fill=tk.X, pady=(10, 6))
            total_row = tk.Frame(ts_f, bg=C["card"])
            total_row.pack(fill=tk.X)
            tk.Label(total_row, text="Total Sold", bg=C["card"], fg=C["muted"],
                     font=("Segoe UI", 11)).pack(side=tk.LEFT)
            tk.Label(total_row, text=str(total_qty), bg=C["card"], fg=C["lime"],
                     font=("Segoe UI", 14, "bold")).pack(side=tk.RIGHT)
        else:
            tk.Label(ts_f, text="No data yet", bg=C["card"], fg=C["muted"], font=("Segoe UI", 11)).pack()

        # Col 2: Today Appointments
        appt_outer = tk.Frame(r4_bottom, bg=C["card"], relief="flat")
        appt_outer.grid(row=0, column=2, sticky="nsew", padx=(6, 0))
        appt_hdr_f = tk.Frame(appt_outer, bg=C["card"], padx=14, pady=12)
        appt_hdr_f.pack(fill=tk.X)
        ap_icon = tk.Label(appt_hdr_f, text="📅", font=("Segoe UI Emoji", 14), bg=C["card"], fg=C["blue"])
        ap_icon.pack(side=tk.LEFT, padx=(0, 6))
        tk.Label(appt_hdr_f, text="Today's Appointments", font=("Segoe UI", 12, "bold"),
                 bg=C["card"], fg=C["text"]).pack(side=tk.LEFT)
        status_badge(appt_hdr_f, f"{len(appts)} scheduled").pack(side=tk.RIGHT)
        tk.Frame(appt_outer, bg=C["sidebar"], height=1).pack(fill=tk.X, padx=14)

        if appts:
            af = tk.Frame(appt_outer, bg=C["card"], padx=14, pady=10)
            af.pack(fill=tk.BOTH, expand=True)
            cols = ("Time", "Customer", "Service")
            tree = ttk.Treeview(af, columns=cols, show="headings", height=min(5, len(appts)))
            for col in cols:
                tree.heading(col, text=col)
                tree.column(col, width=scaled_value(80, 70, 60))
            for a in sorted(appts, key=lambda x: x.get("time","")):
                tree.insert("", tk.END, values=(
                    a.get("time",""), a.get("customer",""), a.get("service","")
                ))
            tree.pack(fill=tk.BOTH, expand=True)
            af.bind("<Configure>", lambda e, tree=tree: self._schedule_tree_resize("appt_mini", tree, e.width), add="+")
        else:
            no_appt_f = tk.Frame(appt_outer, bg=C["card"])
            no_appt_f.pack(fill=tk.BOTH, expand=True, pady=20)
            tk.Label(no_appt_f, text="📅", font=("Segoe UI Emoji", 36), bg=C["card"], fg=C["sidebar"]).pack(pady=(10, 6))
            tk.Label(no_appt_f, text="No appointments scheduled today",
                     bg=C["card"], fg=C["muted"], font=("Segoe UI", 11)).pack()
            tk.Label(no_appt_f, text="You're all caught up!",
                     bg=C["card"], fg=C["blue"], font=("Segoe UI", 10)).pack(pady=(4, 0))

        def _update_scroll():
            try:
                self._canvas.configure(scrollregion=self._canvas.bbox("all"))
                self._install_scroll_bindings()
            except Exception:
                pass
        self.after(200, _update_scroll)

    def _stat_card(self, parent, label, value, accent_color=None, click_cmd=None, icon=""):
        """SaaS-style KPI card: icon box left, label + value content right."""
        bg = C["card"]
        card = tk.Frame(parent, bg=bg, relief="flat", height=100)
        card.pack_propagate(False)

        # LEFT: colored accent line
        if accent_color:
            tk.Frame(card, bg=accent_color, width=3).pack(side=tk.LEFT, fill=tk.Y)

        # LEFT: colored square icon box (fixed 68px wide)
        if icon:
            icon_box_color = accent_color or C.get("teal", "#3b82f6")
            icon_box = tk.Frame(card, bg=C["sidebar"], width=68)
            icon_box.pack(side=tk.LEFT, fill=tk.Y)
            icon_box.pack_propagate(False)
            icon_lbl = tk.Label(icon_box, text=icon,
                                font=("Segoe UI Emoji", 20),
                                bg=C["sidebar"], fg=icon_box_color)
            icon_lbl.pack(fill=tk.BOTH, expand=True)
        else:
            icon_lbl = None
            icon_box = None

        # RIGHT: content area
        content = tk.Frame(card, bg=bg)
        content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(14, 12), pady=12)

        lbl_w = tk.Label(content, text=label.upper(),
                         font=("Segoe UI", 9), bg=bg, fg=C["muted"], anchor="w")
        lbl_w.pack(fill=tk.X)

        val_w = tk.Label(content, text=value,
                         font=("Segoe UI", 20, "bold"), bg=bg, fg=C["text"], anchor="w")
        val_w.pack(fill=tk.X, pady=(2, 0))

        if click_cmd:
            hover_bg = C.get("input", "#1a2332")
            all_w = [card, content, lbl_w, val_w]
            if icon_box: all_w.append(icon_box)
            if icon_lbl: all_w.append(icon_lbl)

            def _enter(e):
                card.configure(bg=hover_bg)
                content.configure(bg=hover_bg)
                lbl_w.configure(bg=hover_bg)
                val_w.configure(bg=hover_bg)
            def _leave(e):
                card.configure(bg=bg)
                content.configure(bg=bg)
                lbl_w.configure(bg=bg)
                val_w.configure(bg=bg)

            for w in all_w:
                w.bind("<Button-1>", lambda e, c=click_cmd: c())
                w.bind("<Enter>", _enter)
                w.bind("<Leave>", _leave)
                w.configure(cursor="hand2")
        return card

    def _wa_birthday(self, phone, name):
        if not phone: return
        try:
            import pywhatkit as kit
            salon_name = get_company_name()
            msg = (f"Happy Birthday {name}!\n\n"
                   f"Wishing you a wonderful day!\n"
                   f"Visit {salon_name} for a special birthday treat!\n"
                   f"\n- Team {salon_name}")
            kit.sendwhatmsg_instantly(f"+91{phone}", msg,
                                       wait_time=25, tab_close=True)
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Error", str(e))

    def _show_bills(self, period: str = "today"):
        """Popup showing bill list for selected period."""
        import csv, os
        from utils import F_REPORT, safe_float, fmt_currency, today_str
        from datetime import date

        td = today_str()
        mo = date.today().strftime("%Y-%m")

        win = tk.Toplevel(self)
        hide_while_building(win)
        win.title("📋  Bills")
        popup_window(win, 900, 560)
        fit_toplevel(
            win,
            scaled_value(980, 900, 780),
            scaled_value(620, 580, 500),
            min_width=720,
            min_height=420,
        )
        win.configure(bg=C["bg"])
        win.grab_set()
        win.protocol("WM_DELETE_WINDOW", lambda: (win.grab_release(), win.destroy()))

        title_map = {"today": "Today's Bills",
                     "month": "This Month's Bills",
                     "all":   "All Bills"}
        # v3 popup header
        hdr_f = tk.Frame(win, bg=C["sidebar"], padx=16, pady=10)
        hdr_f.pack(fill=tk.X)
        tk.Label(hdr_f, text=f"📋  {title_map.get(period,'Bills')}",
                 font=("Arial", 13, "bold"),
                 bg=C["sidebar"], fg=C["text"]).pack(side=tk.LEFT)
        tk.Frame(win, bg=C["teal"], height=2).pack(fill=tk.X)

        cols = ("Date","Invoice","Customer","Phone","Payment","Total")
        tree = ttk.Treeview(win, columns=cols, show="headings", height=16)
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=scaled_value(118, 104, 90))

        vsb = ttk.Scrollbar(win, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(fill=tk.BOTH, expand=True, padx=15, side=tk.LEFT)
        vsb.pack(side=tk.LEFT, fill=tk.Y, pady=(0,8))
        win.bind("<Configure>", lambda e, tree=tree: self._schedule_tree_resize("bills", tree, max(0, e.width - 60)), add="+")

        total = count = 0
        if os.path.exists(F_REPORT):
            try:
                with open(F_REPORT,"r",encoding="utf-8") as f:
                    r   = csv.reader(f)
                    hdr = next(r, None)
                    ti  = 5 if (hdr and len(hdr)>=6) else 3
                    for row in r:
                        if not row or len(row)<=ti: continue
                        dt = row[0][:10]
                        if period=="today" and dt!=td: continue
                        if period=="month" and row[0][:7]!=mo: continue
                        tv = safe_float(row[ti])
                        total += tv; count += 1
                        inv = row[1] if len(row)>1 else "---"
                        nm  = row[2] if len(row)>2 else ""
                        ph  = row[3] if len(row)>3 else ""
                        pm  = row[4] if len(row)>4 else ""
                        tree.insert("", tk.END, values=(
                            row[0], inv, nm, ph, pm, fmt_currency(tv)))
            except Exception as e:
                app_log(f"[_show_bills] {e}")

        tk.Label(win,
                 text=f"Total: {fmt_currency(total)}  |  Bills: {count}",
                 font=("Arial",11,"bold"),
                 bg=C["bg"], fg=C["lime"]).pack(pady=6)
        reveal_when_ready(win)

    def refresh(self):
        """Full refresh: rebuild shell (picks up new theme) + reload data."""
        if not self._built:
            self._schedule_build()
            return
        try:
            self._dashboard_signature = None  # force full repopulate
            self._build()  # rebuild header + canvas with current C[] theme colors
            self._built = True
        except Exception as e:
            app_log(f"[dashboard refresh] {e}")

    def _schedule_tree_resize(self, key, tree, width):
        job = self._tree_resize_jobs.get(key)
        if job:
            try:
                self.after_cancel(job)
            except Exception:
                pass
        self._tree_resize_jobs[key] = self.after(60, lambda: self._resize_tree_columns(key, tree, width))

    def _resize_tree_columns(self, key, tree, width):
        width = max(520, width)
        if key == "appt":
            col_map = {
                "Time": max(72, int(width * 0.10)),
                "Customer": max(120, int(width * 0.18)),
                "Phone": max(96, int(width * 0.15)),
                "Service": max(150, int(width * 0.26)),
                "Staff": max(110, int(width * 0.16)),
            }
            used = sum(col_map.values())
            col_map["Status"] = max(90, width - used - 24)
        elif key == "appt_mini":
            width = max(300, width)
            col_map = {
                "Time": max(60, int(width * 0.2)),
                "Customer": max(100, int(width * 0.4)),
            }
            used = sum(col_map.values())
            col_map["Service"] = max(100, width - used - 24)
        else:
            col_map = {
                "Date": max(108, int(width * 0.18)),
                "Invoice": max(84, int(width * 0.12)),
                "Customer": max(128, int(width * 0.22)),
                "Phone": max(96, int(width * 0.16)),
                "Payment": max(84, int(width * 0.12)),
            }
            used = sum(col_map.values())
            col_map["Total"] = max(92, width - used - 24)
        for col, val in col_map.items():
            try:
                tree.column(col, width=val)
            except Exception:
                pass
