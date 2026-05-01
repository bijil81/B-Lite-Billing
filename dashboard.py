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
                        all_rev += val
                        if row[0][:10] == td:
                            td_rev += val
                            td_bills += 1
                            if pi > 0 and len(row) > pi:
                                payment_counts[row[pi]] += val
                        if row[0][:7] == mo:
                            mo_rev += val
                            mo_bills += 1
                        if ir > 0 and len(row) > ir:
                            for seg in row[ir].split("|"):
                                parts = seg.split("~")
                                if len(parts) == 4 and parts[0] == "services":
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
        try:
            appts = load_json(F_APPOINTMENTS, [])
            td = today_str()
            return [a for a in appts if a.get("date", "") == td]
        except Exception as e:
            app_log(f"[_today_appointments] {e}")
            return []
    dependency_key = os.path.getmtime(F_APPOINTMENTS) if os.path.exists(F_APPOINTMENTS) else 0
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
            inv = load_json(F_INVENTORY, {})
            return sum(1 for item in inv.values()
                       if item.get("qty", 0) <= item.get("min_stock", 5))
        except Exception as e:
            app_log(f"[_low_stock_count] {e}")
            return 0
    dependency_key = os.path.getmtime(F_INVENTORY) if os.path.exists(F_INVENTORY) else 0
    return _get_cached_value("low_stock_count", dependency_key, _builder)


class DashboardFrame(tk.Frame):

    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self._responsive = get_responsive_metrics(parent.winfo_toplevel())
        self._dashboard_signature = None
        self._build()

    def _build(self):
        self._responsive = get_responsive_metrics(self.winfo_toplevel())
        compact = self._responsive["mode"] == "compact"
        # ── Header (UI v3.0) ─────────────────────────
        hdr = tk.Frame(self, bg=C["card"], pady=10)
        hdr.pack(fill=tk.X)

        # Left — icon + title + subtitle
        left_f = tk.Frame(hdr, bg=C["card"])
        left_f.pack(side=tk.LEFT, padx=20)
        tk.Label(left_f, text="📈  Dashboard",
                 font=("Arial", 15, "bold"),
                 bg=C["card"], fg=C["text"]).pack(anchor="w")
        tk.Label(left_f, text="Live shop overview",
                 font=("Arial", 10),
                 bg=C["card"], fg=C["muted"]).pack(anchor="w")

        # Right — clock + refresh button
        self.time_lbl = tk.Label(hdr, text="",
                                  font=("Arial", 11),
                                  bg=C["card"], fg=C["muted"])
        self.time_lbl.pack(side=tk.RIGHT, padx=(0, 20))
        self._tick()

        ModernButton(hdr, text="🔄  Refresh",
                     command=self.refresh,
                     color=C["teal"], hover_color=C["blue"],
                     width=scaled_value(120, 112, 96), height=scaled_value(34, 32, 28), radius=8,
                     font=("Arial", 10 if compact else 9, "bold"),
                     ).pack(side=tk.RIGHT, padx=(0, 10), pady=6)

        # Thin accent divider under header
        tk.Frame(self, bg=C["teal"], height=2).pack(fill=tk.X)

        # Scrollable canvas
        canvas = tk.Canvas(self, bg=C["bg"], highlightthickness=0)
        vsb    = ttk.Scrollbar(self, orient="vertical",
                                command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(fill=tk.BOTH, expand=True)

        self._body = tk.Frame(canvas, bg=C["bg"])
        self._win  = canvas.create_window((0, 0), window=self._body,
                                           anchor="nw")
        self._body.bind("<Configure>",
                         lambda e: canvas.configure(
                             scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(
                        self._win, width=e.width))
        self._canvas = canvas
        self._tree_resize_jobs = {}

        self._populate()

    def _tick(self):
        now = datetime.now().strftime("%A, %d %B %Y   %I:%M %p")
        self.time_lbl.config(text=now)
        self.after(30000, self._tick)

    def _populate(self):
        try:
            self._populate_inner()
        except Exception as e:
            app_log(f"[_populate] {e}")

    def _populate_inner(self):
        stats = _today_stats()
        appts = _today_appointments()
        bdays = _birthday_today()
        low   = _low_stock_count()
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
        )
        if self._dashboard_signature == signature and self._body.winfo_children():
            return
        self._dashboard_signature = signature

        for w in self._body.winfo_children():
            w.destroy()

        pad = dict(padx=16, pady=6)

        # Phase 3 FIX: stat card rows use a scrollable canvas to prevent
        # overflow/clipping on narrow windows. Cards wrap naturally
        # when the window is resized.

        def _make_card_row(parent, card_data, is_clickable=True):
            """Create a horizontally-scrollable row of stat cards.

            V5.6.1 Regression Fix:
            - Hide horizontal scrollbar when content fits
            - Only show scrollbar when width is actually too small
            - Prevent empty canvas/placeholder from occupying height
            """
            outer = tk.Frame(parent, bg=C["bg"])
            outer.pack(fill=tk.X, **pad)

            # Canvas for horizontal scroll
            canvas = tk.Canvas(outer, bg=C["bg"], highlightthickness=0, bd=0)
            hsb = ttk.Scrollbar(outer, orient="horizontal", command=canvas.xview)
            canvas.configure(xscrollcommand=hsb.set)

            inner = tk.Frame(canvas, bg=C["bg"])
            canvas_win = canvas.create_window((0, 0), window=inner, anchor="nw")

            def _sync(event=None):
                canvas.configure(scrollregion=canvas.bbox("all"))
                # V5.6.1: hide scrollbar when content fits
                inner_w = event.width
                canvas_w = canvas.winfo_width()
                if inner_w <= canvas_w + 2:
                    canvas.itemconfigure(canvas_win, width=canvas_w)
                    hsb.pack_forget()
                else:
                    hsb.pack(side=tk.BOTTOM, fill=tk.X, expand=False)
            inner.bind("<Configure>", _sync)

            def _fit_width(event):
                canvas.itemconfigure(canvas_win, width=event.width)
                # V5.6.1: re-check scrollbar visibility on resize
                if inner.winfo_reqwidth() <= event.width + 2:
                    hsb.pack_forget()
                else:
                    hsb.pack(side=tk.BOTTOM, fill=tk.X)
            canvas.bind("<Configure>", _fit_width)

            def _mousewheel(e):
                try:
                    canvas.xview_scroll(int(-1 * (e.delta / 120)), "units")
                except Exception:
                    pass
            canvas.bind_all("<Shift-MouseWheel>", _mousewheel)

            canvas.pack(side=tk.TOP, fill=tk.X, expand=True)
            # hsb starts hidden — shown by _sync if needed

            for item in card_data:
                if len(item) == 5:
                    lbl, val, icon, col, cmd = item
                    card = stat_card_v3(inner, lbl, val, icon=icon, color=col)
                    if is_clickable:
                        card.configure(cursor="hand2")
                        card.bind("<Button-1>", lambda e, c=cmd: c())
                else:
                    lbl, val, icon, col = item
                    card = stat_card_v3(inner, lbl, val, icon=icon, color=col)
                card.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)

            return inner

        # ── Row 1 : Revenue cards ─────────────────
        cards1 = [
            ("Today Revenue",    fmt_currency(stats["td_rev"]),  "💰", C["teal"],   lambda: self._show_bills("today")),
            ("Today Bills",      str(stats["td_bills"]),         "🧾", C["blue"],   lambda: self._show_bills("today")),
            ("Month Revenue",    fmt_currency(stats["mo_rev"]),  "📅", C["purple"], lambda: self._show_bills("month")),
            ("Month Bills",      str(stats["mo_bills"]),         "📊", C["orange"], lambda: self._show_bills("month")),
            ("All Time Revenue", fmt_currency(stats["all_rev"]), "🏆", C["teal"],   lambda: self._show_bills("all")),
        ]
        _make_card_row(self._body, cards1, is_clickable=True)

        # ── Row 2 : Alerts ───────────────────────
        pending = sum(1 for a in appts if a.get("status") == "Scheduled")
        alert_data = [
            ("Today Appts",    str(len(appts)), "📅",
             C["blue"]   if appts else C["sidebar"]),
            ("Birthdays Today", str(len(bdays)), "🎂",
             C["accent"] if bdays else C["sidebar"]),
            ("Low Stock Items", str(low),        "⚠️",
             C["red"]    if low   else C["sidebar"]),
            ("Pending Appts",  str(pending),    "🕐", C["orange"]),
        ]
        _make_card_row(self._body, alert_data, is_clickable=False)

        # ── Row 3 : Payment + Top Services ───────
        r3 = tk.Frame(self._body, bg=C["bg"])
        r3.pack(fill=tk.X, **pad)

        # Payment breakdown — v3 card
        pm_outer = tk.Frame(r3, bg=C["card"], padx=0, pady=0,
                             relief="flat")
        pm_outer.pack(side=tk.LEFT, fill=tk.BOTH, expand=True,
                      padx=(0, 10))
        # Card header
        pm_hdr = tk.Frame(pm_outer, bg=C["sidebar"], padx=14, pady=8)
        pm_hdr.pack(fill=tk.X)
        tk.Label(pm_hdr, text="💳  Today Payments",
                 font=("Arial", 11, "bold"),
                 bg=C["sidebar"], fg=C["text"]).pack(side=tk.LEFT)
        tk.Frame(pm_outer, bg=C["teal"], height=2).pack(fill=tk.X)
        pm_f = tk.Frame(pm_outer, bg=C["card"], padx=14, pady=10)
        pm_f.pack(fill=tk.BOTH, expand=True)

        pm = stats["payment"]
        if pm:
            for method, amt in pm.items():
                row = tk.Frame(pm_f, bg=C["card"])
                row.pack(fill=tk.X, pady=3)
                tk.Label(row, text=method,
                         bg=C["card"], fg=C["muted"],
                         font=("Arial", 12 if not compact else 10), width=7 if compact else 8,
                         anchor="w").pack(side=tk.LEFT)
                tk.Label(row, text=fmt_currency(amt),
                         bg=C["card"], fg=C["lime"],
                         font=("Arial", 11, "bold")).pack(side=tk.RIGHT)
        else:
            tk.Label(pm_f, text="No bills today",
                     bg=C["card"], fg=C["muted"],
                     font=("Arial", 12)).pack()

        # Top services — v3 card
        ts_outer = tk.Frame(r3, bg=C["card"], relief="flat")
        ts_outer.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ts_hdr = tk.Frame(ts_outer, bg=C["sidebar"], padx=14, pady=8)
        ts_hdr.pack(fill=tk.X)
        tk.Label(ts_hdr, text="🏆  Top 5 Services (All Time)",
                 font=("Arial", 11, "bold"),
                 bg=C["sidebar"], fg=C["text"]).pack(side=tk.LEFT)
        tk.Frame(ts_outer, bg=C["purple"], height=2).pack(fill=tk.X)
        ts_f = tk.Frame(ts_outer, bg=C["card"], padx=14, pady=10)
        ts_f.pack(fill=tk.BOTH, expand=True)

        if stats["top_svc"]:
            max_val = stats["top_svc"][0][1] if stats["top_svc"] else 1
            for i, (svc, amt) in enumerate(stats["top_svc"]):
                row = tk.Frame(ts_f, bg=C["card"])
                row.pack(fill=tk.X, pady=3)
                rank_col = [C["gold"], C["muted"], C["muted"],
                             C["muted"], C["muted"]][i]
                tk.Label(row, text=f"#{i+1}",
                         bg=C["card"], fg=rank_col,
                         font=("Arial", 11, "bold"),
                         width=3).pack(side=tk.LEFT)
                tk.Label(row, text=svc[:24 if compact else 28],
                         bg=C["card"], fg=C["text"],
                         font=("Arial", 11 if not compact else 9),
                         anchor="w", width=22 if compact else 28).pack(side=tk.LEFT, padx=4)
                # mini bar
                bar_w = max(4, int(scaled_value(80, 68, 54) * amt / max_val))
                tk.Frame(row, bg=C["teal"],
                         width=bar_w, height=scaled_value(12, 12, 10)).pack(side=tk.LEFT)
                tk.Label(row, text=fmt_currency(amt),
                         bg=C["card"], fg=C["muted"],
                         font=("Arial", 10)).pack(side=tk.RIGHT)
        else:
            tk.Label(ts_f, text="No data yet",
                     bg=C["card"], fg=C["muted"],
                     font=("Arial", 12)).pack()

        # ── Row 4 : Today appointments (UI v3) ───
        appt_outer = tk.Frame(self._body, bg=C["card"])
        appt_outer.pack(fill=tk.X, **pad)

        # Card header
        appt_hdr = tk.Frame(appt_outer, bg=C["sidebar"], padx=14, pady=8)
        appt_hdr.pack(fill=tk.X)
        tk.Label(appt_hdr, text="📅  Today's Appointments",
                 font=("Arial", 11, "bold"),
                 bg=C["sidebar"], fg=C["text"]).pack(side=tk.LEFT)
        status_badge(appt_hdr, f"{len(appts)} scheduled").pack(
            side=tk.RIGHT, padx=4)
        tk.Frame(appt_outer, bg=C["blue"], height=2).pack(fill=tk.X)

        if appts:
            af = tk.Frame(appt_outer, bg=C["card"], padx=14, pady=10)
            af.pack(fill=tk.BOTH, expand=True)

            cols = ("Time", "Customer", "Phone", "Service", "Staff", "Status")
            tree = ttk.Treeview(af, columns=cols,
                                 show="headings", height=min(5, len(appts)))
            for col in cols:
                tree.heading(col, text=col)
                tree.column(col, width=scaled_value(120, 104, 88))
            for a in sorted(appts, key=lambda x: x.get("time","")):
                tree.insert("", tk.END, values=(
                    a.get("time",""), a.get("customer",""),
                    a.get("phone",""), a.get("service",""),
                    a.get("staff",""),  a.get("status",""),
                ))
            tree.pack(fill=tk.X)
            af.bind("<Configure>", lambda e, tree=tree: self._schedule_tree_resize("appt", tree, e.width), add="+")
        else:
            tk.Label(appt_outer, text="No appointments scheduled today",
                     bg=C["card"], fg=C["muted"],
                     font=("Arial", 10),
                     padx=14, pady=16).pack()

        # ── Row 5 : Birthdays (UI v3) ────────────
        if bdays:
            bd_outer = tk.Frame(self._body, bg=C["card"])
            bd_outer.pack(fill=tk.X, **pad)

            bd_hdr = tk.Frame(bd_outer, bg=C["sidebar"], padx=14, pady=8)
            bd_hdr.pack(fill=tk.X)
            tk.Label(bd_hdr, text="🎂  Birthdays Today!",
                     font=("Arial", 11, "bold"),
                     bg=C["sidebar"], fg=C["gold"]).pack(side=tk.LEFT)
            tk.Frame(bd_outer, bg=C["accent"], height=2).pack(fill=tk.X)

            bf2 = tk.Frame(bd_outer, bg=C["card"], padx=14, pady=10)
            bf2.pack(fill=tk.BOTH, expand=True)

            for c in bdays:
                row = tk.Frame(bf2, bg=C["card"])
                row.pack(fill=tk.X, pady=4)
                tk.Label(row,
                         text=f"🎂  {c.get('name','')}  |  📞 {c.get('phone','')}",
                         bg=C["card"], fg=C["gold"],
                         font=("Arial", 11, "bold")).pack(side=tk.LEFT)
                ModernButton(row, text="💬 WhatsApp",
                             command=lambda ph=c.get("phone",""),
                             nm=c.get("name",""): self._wa_birthday(ph, nm),
                             color="#25d366", hover_color="#16a34a",
                             width=scaled_value(120, 112, 96), height=scaled_value(30, 30, 26), radius=8,
                             font=("Arial", 10 if not compact else 9, "bold"),
                             ).pack(side=tk.RIGHT)

    def _stat_card(self, parent, label, value, color, click_cmd=None):
        card = tk.Frame(parent, bg=color, padx=18, pady=14,
                        cursor="hand2" if click_cmd else "")
        tk.Label(card, text=value,
                 font=("Arial", 16, "bold"),
                 bg=color, fg="white",
                 cursor="hand2" if click_cmd else "").pack()
        tk.Label(card, text=label,
                 font=("Arial", 10),
                 bg=color, fg="white",
                 cursor="hand2" if click_cmd else "").pack()
        if click_cmd:
            card.bind("<Button-1>", lambda e: click_cmd())
            for child in card.winfo_children():
                child.bind("<Button-1>", lambda e: click_cmd())
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
        try:
            self._populate()
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
