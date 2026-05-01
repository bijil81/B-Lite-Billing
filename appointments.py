"""
appointments.py  —  BOBY'S Salon : Appointment booking + Smart Reminder System

ADDED (no existing functionality changed):
  - get_due_appointment_reminders()  : filter logic with cooldown
  - show_appointment_popup()         : non-blocking per-appointment popup
  - "dont_show" / "last_reminded"    : two new optional fields per appointment
    (read safely with .get() — old data without these fields works fine)
FIXES:
  - Fix R7a: utils validate_phone + validate_date imported and used in _save()
  - Fix R7b: _save() — phone + date + time validation before booking
  - Fix R7c: _stamp_last_reminded() — try/except crash prevention
  - Fix R7d: _update_appointment() — try/except crash prevention
  - Fix R7e: _load() — try/except crash prevention
  - Fix R7f: _set_status() — try/except + error message
  - Fix R7g: _delete() — try/except + error message
  - Fix R7h: _send_reminder() — uses validate_phone from utils (centralized)
  - Fix R7i: refresh() — try/except crash prevention
  - Fix R7j: get_due_appointment_reminders() — try/except crash prevention
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date, timedelta
from utils import (C, load_json, save_json, F_APPOINTMENTS,
                   now_str, today_str, fmt_currency,
                   popup_window, validate_phone, validate_date, app_log)
from date_helpers import (
    attach_date_mask,
    display_to_iso_date,
    iso_to_display_date,
    today_display_str,
    validate_display_date,
)
from ui_responsive import make_scrollable
from ui_theme import apply_treeview_column_alignment, ModernButton, status_badge
from ui_responsive import get_responsive_metrics, scaled_value, fit_toplevel
from branding import get_invoice_branding
from ui_utils import make_searchable_combobox
from icon_system import get_action_icon
from src.blite_v6.app.window_lifecycle import hide_while_building, reveal_when_ready

STATUS_COLORS = {
    "Scheduled": "#2980b9",
    "Completed":  "#27ae60",
    "Cancelled":  "#e74c3c",
    "No Show":    "#e67e22",
}

# Cooldown between repeated reminders for the SAME appointment (seconds)
REMINDER_COOLDOWN_SECONDS = 300   # 5 minutes


# ─────────────────────────────────────────────────────────
#  DATA HELPERS  (unchanged)
# ─────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────
#  REMINDER FILTER
# ─────────────────────────────────────────────────────────

def get_due_appointment_reminders() -> list:
    """
    Return appointments that need a reminder popup right now.

    Rules:
      1. status must be "Scheduled"
      2. dont_show must not be True
      3. appointment datetime must be in the FUTURE (time not yet passed)
      4. If last_reminded is set, at least REMINDER_COOLDOWN_SECONDS must
         have elapsed since the last popup was shown
      5. Only appointments scheduled within the next 24 hours are surfaced
         (avoids cluttering the screen with far-future bookings)

    Returns a list of appointment dicts (references into the loaded list —
    callers should reload from disk before mutating).
    Fix R7j: wrapped in try/except — reminder loop never crashes the app.
    """
    try:
        now = datetime.now()
        due = []

        for appt in get_appointments():
            # ── Gate 1: status ───────────────────────
            if appt.get("status", "Scheduled") != "Scheduled":
                continue

            # ── Gate 2: user dismissed this one ──────
            if appt.get("dont_show", False):
                continue

            # ── Gate 3: parse appointment datetime ───
            raw_date = appt.get("date", "").strip()
            raw_time = appt.get("time", "").strip()
            if not raw_date or not raw_time:
                continue
            try:
                appt_dt = datetime.strptime(
                    f"{raw_date} {raw_time}", "%Y-%m-%d %H:%M")
            except ValueError:
                continue  # malformed date/time — skip silently

            # ── Gate 4: time must not have passed ────
            if appt_dt <= now:
                continue

            # ── Gate 5: only surface within next 24 h ─
            if appt_dt > now + timedelta(hours=24):
                continue

            # ── Gate 6: cooldown check ───────────────
            last_reminded = appt.get("last_reminded", "").strip()
            if last_reminded:
                try:
                    last_dt = datetime.strptime(last_reminded, "%Y-%m-%d %H:%M:%S")
                    elapsed = (now - last_dt).total_seconds()
                    if elapsed < REMINDER_COOLDOWN_SECONDS:
                        continue
                except ValueError:
                    pass  # unparseable timestamp â†’ treat as "never reminded"

            due.append(appt)

        return due
    except Exception as e:
        app_log(f"[get_due_appointment_reminders] {e}")
        return []


# ─────────────────────────────────────────────────────────
#  REMINDER POPUP
# ─────────────────────────────────────────────────────────

def show_appointment_popup(root: tk.Tk, appt: dict):
    """
    Show a non-blocking reminder popup for a single appointment.

    Two actions available:
      ✅" Mark as Done   â†’ sets status = "Completed"
      ✅– Don't Show Again â†’ sets dont_show = True

    In both cases:
      - appointments.json is saved immediately
      - last_reminded is stamped when the popup first appears
    """
    # ── Stamp last_reminded immediately on display ──────
    _stamp_last_reminded(appt)

    customer = appt.get("customer", "Customer")
    service  = appt.get("service",  "—")
    appt_time = appt.get("time",    "—")
    appt_date = appt.get("date",    "—")

    # ── Window ──────────────────────────────────────────
    win = tk.Toplevel(root)
    hide_while_building(win)
    win.title("Appointment Reminder")
    win.configure(bg=C["bg"])
    win.attributes("-topmost", True)

    # Position: top-right corner, stacked if multiple popups
    w, h = 360, 210
    # Offset by a small random-ish amount so stacked popups are readable
    import time as _t
    offset = int(_t.time() * 1000) % 5 * 22   # 0—88 px vertical offset
    fit_toplevel(win, w, h,
                 min_width=320, min_height=180,
                 resizable=True, anchor="topright",
                 top_offset=60 + offset, right_offset=20)

    # ── Header bar ──────────────────────────────────────
    hdr = tk.Frame(win, bg=C["blue"], pady=8)
    hdr.pack(fill=tk.X)
    tk.Label(hdr, text="Appointment Reminder",
             font=("Arial", 11, "bold"),
             bg=C["blue"], fg="white").pack(side=tk.LEFT, padx=14)

    # ── Body ────────────────────────────────────────────
    body = tk.Frame(win, bg=C["card"], padx=18, pady=14)
    body.pack(fill=tk.BOTH, expand=True)

    for label, value in [
        ("Customer", customer),
        ("Service",  service),
        ("Time",     f"{appt_date}  {appt_time}"),
    ]:
        row = tk.Frame(body, bg=C["card"])
        row.pack(fill=tk.X, pady=3)
        tk.Label(row, text=label,
                 font=("Arial", 10),
                 bg=C["card"], fg=C["muted"],
                 width=13, anchor="w").pack(side=tk.LEFT)
        tk.Label(row, text=value,
                 font=("Arial", 11, "bold"),
                 bg=C["card"], fg=C["text"],
                 anchor="w").pack(side=tk.LEFT)

    # ── Buttons ─────────────────────────────────────────
    btn_frame = tk.Frame(win, bg=C["bg"], pady=8)
    btn_frame.pack(fill=tk.X, padx=14)
    compact = get_responsive_metrics(root)["mode"] == "compact"

    def _mark_done():
        _update_appointment(appt, status="Completed")
        win.destroy()

    def _dont_show():
        _update_appointment(appt, dont_show=True)
        win.destroy()

    ModernButton(btn_frame, text="Mark as Done", image=get_action_icon("save"), compound="left",
                 command=_mark_done,
                 color=C["green"], hover_color="#1a7a45",
                 width=scaled_value(152, 140, 118), height=scaled_value(34, 32, 28), radius=8,
                 font=("Arial", 10 if not compact else 9, "bold"),
                 ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

    ModernButton(btn_frame, text="Don't Show Again", image=get_action_icon("clear"), compound="left",
                 command=_dont_show,
                 color=C["orange"], hover_color="#d35400",
                 width=scaled_value(152, 140, 118), height=scaled_value(34, 32, 28), radius=8,
                 font=("Arial", 10 if not compact else 9, "bold"),
                 ).pack(side=tk.LEFT, fill=tk.X, expand=True)

    # Allow simple window-close (X button) without any data change
    win.protocol("WM_DELETE_WINDOW", win.destroy)
    reveal_when_ready(win)


# ─────────────────────────────────────────────────────────
#  INTERNAL HELPERS
# ─────────────────────────────────────────────────────────

def _stamp_last_reminded(appt: dict):
    """Write last_reminded = now into appointments.json for this appointment.
    Fix R7c: try/except — reminder popup never crashes on save failure."""
    try:
        appts = get_appointments()
        for a in appts:
            if (_appt_matches(a, appt)):
                a["last_reminded"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                break
        save_appointments(appts)
    except Exception as e:
        app_log(f"[_stamp_last_reminded] {e}")


def _update_appointment(appt: dict, status: str = None, dont_show: bool = None):
    """
    Reload appointments from disk, find the matching entry, apply changes, save.
    Always reloads from disk to avoid overwriting concurrent changes.
    Fix R7d: try/except — popup action never crashes app.
    """
    try:
        appts = get_appointments()
        for a in appts:
            if _appt_matches(a, appt):
                if status is not None:
                    a["status"] = status
                if dont_show is not None:
                    a["dont_show"] = dont_show
                a["last_reminded"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                break
        save_appointments(appts)
    except Exception as e:
        app_log(f"[_update_appointment] {e}")


def _appt_matches(a: dict, b: dict) -> bool:
    """Identity check: same customer + phone + date + time."""
    return (a.get("customer", "") == b.get("customer", "")
            and a.get("phone",    "") == b.get("phone",    "")
            and a.get("date",     "") == b.get("date",     "")
            and a.get("time",     "") == b.get("time",     ""))


# ─────────────────────────────────────────────────────────
#  APPOINTMENTS FRAME  (all existing code preserved exactly)
# ─────────────────────────────────────────────────────────

class AppointmentsFrame(tk.Frame):

    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self._responsive = get_responsive_metrics(parent.winfo_toplevel())
        self._build()

    def _build(self):
        compact = self._responsive["mode"] == "compact"
        # UI v3 — modern header
        hdr = tk.Frame(self, bg=C["card"], pady=10)
        hdr.pack(fill=tk.X)
        left_f = tk.Frame(hdr, bg=C["card"])
        left_f.pack(side=tk.LEFT, padx=20)
        tk.Label(left_f, text="Appointments",
                 font=("Arial", 15, "bold"),
                 bg=C["card"], fg=C["text"]).pack(anchor="w")
        tk.Label(left_f, text="Appointments",
                 font=("Arial", 10),
                 bg=C["card"], fg=C["muted"]).pack(anchor="w")
        ModernButton(hdr, text="Book Appointment", image=get_action_icon("add"), compound="left",
                     command=self._add_dialog,
                     color=C["teal"], hover_color=C["blue"],
                     width=scaled_value(168, 154, 132), height=scaled_value(34, 32, 28), radius=8,
                     font=("Arial", 10 if not compact else 9, "bold"),
                     ).pack(side=tk.RIGHT, padx=15, pady=6)
        tk.Frame(self, bg=C["teal"], height=2).pack(fill=tk.X)

        # Today's summary
        self.today_f = tk.Frame(self, bg=C["bg"])
        self.today_f.pack(fill=tk.X, padx=15, pady=8)

        # Filter row
        ff = tk.Frame(self, bg=C["bg"], pady=4)
        ff.pack(fill=tk.X, padx=15)

        tk.Label(ff, text="Date:", bg=C["bg"],
                 fg=C["muted"], font=("Arial", 11)).pack(side=tk.LEFT, padx=(0, 4))
        self.date_var = tk.StringVar(value=today_display_str())
        self.date_ent = tk.Entry(ff, textvariable=self.date_var,
                                  font=("Arial", 12), bg=C["input"],
                                  fg=C["text"], bd=0, width=14,
                                  insertbackground=C["accent"])
        self.date_ent.pack(side=tk.LEFT, ipady=5, padx=(0, 8))
        attach_date_mask(self.date_ent)

        for txt, icon_name, cmd in [
            ("Today",     "search", lambda: self._jump(today_str())),
            ("Tomorrow",  "search", lambda: self._jump(
                (date.today() + timedelta(days=1)).strftime("%Y-%m-%d"))),
            ("This Week", "filter", lambda: self._jump(
                date.today().strftime("%Y-%m-%d"), 7)),
            ("All",       "clear", lambda: self._load_all()),
        ]:
            ModernButton(ff, text=txt, image=get_action_icon(icon_name), compound="left", command=cmd,
                         color=C["sidebar"], hover_color=C["blue"],
                         width=scaled_value(78, 72, 62), height=scaled_value(30, 30, 26), radius=8,
                         font=("Arial", 10 if not compact else 9, "bold"),
                         ).pack(side=tk.LEFT, padx=2)

        ModernButton(ff, text="Load", image=get_action_icon("refresh"), compound="left",
                     command=lambda: self._load(self.date_var.get()),
                     color=C["teal"], hover_color=C["blue"],
                     width=scaled_value(84, 76, 64), height=scaled_value(30, 30, 26), radius=8,
                     font=("Arial", 10 if not compact else 9, "bold"),
                     ).pack(side=tk.LEFT, padx=4)

        # Phase 5.6.1 Phase 2: visible result count label
        self._appt_result_label = tk.Label(ff, text="", bg=C["bg"],
                                           fg=C["muted"], font=("Arial", 10))
        self._appt_result_label.pack(side=tk.LEFT, padx=(8, 0))

        # Treeview
        cols = ("Time", "Customer", "Phone", "Service", "Staff", "Status")
        self.tree = ttk.Treeview(self, columns=cols,
                                  show="headings", height=15)
        self._tree_cols = cols
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=scaled_value(120, 104, 88))
        # Apply global header + data alignment (centre/left/right per column type)
        apply_treeview_column_alignment(self.tree)

        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=15, side=tk.LEFT)
        vsb.pack(side=tk.LEFT, fill=tk.Y, pady=(0, 8), padx=(0, 15))
        self.bind("<Configure>", self._resize_tree_columns, add="+")
        self.tree.bind("<Button-3>", self._show_appointment_context_menu, add="+")
        self.tree.bind("<ButtonRelease-3>", self._show_appointment_context_menu, add="+")
        self.tree.bind("<Shift-F10>", self._show_appointment_context_menu, add="+")

        # Action buttons (UI v3)
        bb = tk.Frame(self, bg=C["bg"])
        bb.pack(fill=tk.X, padx=15, pady=(0, 10))
        for txt, icon_name, clr, hclr, cmd in [
            ("Complete",  "save",     C["green"],  "#1a7a45", lambda: self._set_status("Completed")),
            ("Cancel",    "clear",    C["red"],    "#c0392b", lambda: self._set_status("Cancelled")),
            ("No Show",   "filter",   C["orange"], "#d35400", lambda: self._set_status("No Show")),
            ("WA Remind", "whatsapp", "#25d366",  "#1a9e4a", self._send_reminder),
            ("Delete",    "delete",   C["red"],   "#c0392b",  self._delete),
        ]:
            ModernButton(bb, text=txt, image=get_action_icon(icon_name), compound="left", command=cmd,
                         color=clr, hover_color=hclr,
                         width=scaled_value(120, 112, 96), height=scaled_value(36, 34, 30), radius=8,
                         font=("Arial", 10 if not compact else 9, "bold"),
                         ).pack(side=tk.LEFT, padx=3)

        self._load(today_str())

    # ── Navigation helpers ──────────────────────────────

    def _jump(self, dt, days=0):
        self.date_var.set(iso_to_display_date(dt))
        self._load(dt, days)

    def _load_all(self):
        self.date_var.set("")
        self._load("")

    def _load(self, dt="", days=0):
        try:
            self._load_inner(dt, days)
        except Exception as e:
            app_log(f"[appointments _load] {e}")

    def _resize_tree_columns(self, event=None):
        if event is None:
            return
        width = max(540, event.width - 56)
        col_map = {
            "Time": max(70, int(width * 0.10)),
            "Customer": max(120, int(width * 0.20)),
            "Phone": max(96, int(width * 0.15)),
            "Service": max(150, int(width * 0.25)),
            "Staff": max(110, int(width * 0.16)),
        }
        used = sum(col_map.values())
        col_map["Status"] = max(92, width - used)
        for col in self._tree_cols:
            self.tree.column(col, width=col_map[col])

    def _load_inner(self, dt="", days=0):
        dt = display_to_iso_date(dt)
        for i in self.tree.get_children():
            self.tree.delete(i)

        today_count = sched_count = shown_count = 0
        for a in sorted(get_appointments(),
                        key=lambda x: (x.get("date", ""), x.get("time", ""))):
            adate = a.get("date", "")
            if dt:
                if days == 0 and adate != dt:
                    continue
                elif days > 0:
                    end = (datetime.strptime(dt, "%Y-%m-%d")
                           + timedelta(days=days)).strftime("%Y-%m-%d")
                    if not (dt <= adate <= end):
                        continue
            shown_count += 1
            if adate == today_str():
                today_count += 1
                if a.get("status", "") == "Scheduled":
                    sched_count += 1

            self.tree.insert("", tk.END, values=(
                a.get("time",     ""),
                a.get("customer", ""),
                a.get("phone",    ""),
                a.get("service",  ""),
                a.get("staff",    ""),
                a.get("status",   "Scheduled"),
            ))

        # Update result count label
        if hasattr(self, "_appt_result_label"):
            if shown_count == 0 and dt:
                label_text = "No matching appointments"
            elif shown_count == 1:
                label_text = "1 appointment"
            else:
                label_text = f"{shown_count} appointments"
            self._appt_result_label.config(text=label_text)

        # Summary cards (UI v3 — stat_card_v3 style)
        for w in self.today_f.winfo_children():
            w.destroy()
        for lbl, val, col, prefix in [
            ("Today's Appointments", str(today_count), C["blue"],   "Today"),
            ("Pending (Scheduled)",  str(sched_count), C["orange"], "Pending"),
        ]:
            card = tk.Frame(self.today_f, bg=C["card"],
                            padx=16, pady=10, relief="flat")
            card.pack(side=tk.LEFT, padx=(0, 10))
            tk.Label(card, text=f"{prefix}  {val}",
                     font=("Arial", 16, "bold"),
                     bg=C["card"], fg=col).pack(anchor="w")
            tk.Label(card, text=lbl,
                     font=("Arial", 10),
                     bg=C["card"], fg=C["muted"]).pack(anchor="w")
            tk.Frame(card, bg=col, height=3).pack(fill=tk.X, pady=(6, 0))

    # ── Book appointment dialog ─────────────────────────

    def _add_dialog(self):
        win = tk.Toplevel(self)
        hide_while_building(win)
        win.title("Book Appointment")
        popup_window(win, 620, 660)
        fit_toplevel(
            win,
            scaled_value(700, 660, 600),
            scaled_value(720, 680, 600),
            min_width=560,
            min_height=520,
        )
        win.configure(bg=C["bg"])
        win.grab_set()
        win.protocol("WM_DELETE_WINDOW",
                     lambda: (win.grab_release(), win.destroy()))
        compact = self._responsive["mode"] == "compact"

        # Fix combobox dropdown list colors
        win.option_add("*TCombobox*Listbox.background",       C["card"])
        win.option_add("*TCombobox*Listbox.foreground",       C["text"])
        win.option_add("*TCombobox*Listbox.selectBackground", C["teal"])
        win.option_add("*TCombobox*Listbox.selectForeground", "white")
        win.option_add("*TCombobox*Listbox.font",             f"Arial {10 if compact else 11}")

        # UI v3 dialog header
        dh = tk.Frame(win, bg=C["sidebar"], padx=20, pady=10)
        dh.pack(fill=tk.X)
        tk.Label(dh, text="Book Appointment",
                 font=("Arial", 13, "bold"),
                 bg=C["sidebar"], fg=C["text"]).pack(side=tk.LEFT)
        tk.Frame(win, bg=C["teal"], height=2).pack(fill=tk.X)

        f, _canvas, _container = make_scrollable(
            win, bg=C["bg"], padx=30, pady=10)

        entries = {}
        for lbl, key, default in [
            ("Customer Name:",     "customer", ""),
            ("Phone:",             "phone",    ""),
            ("Service:",           "service",  ""),
            ("Date (DD-MM-YYYY):", "date",     today_display_str()),
            ("Time (HH:MM, 24-hour):", "time", "10:00"),
        ]:
            tk.Label(f, text=lbl, bg=C["bg"],
                     fg=C["muted"], font=("Arial", 11 if compact else 12)).pack(anchor="w")
            e = tk.Entry(f, font=("Arial", 10 if compact else 11), bg=C["input"],
                         fg=C["text"], bd=0, insertbackground=C["accent"])
            e.pack(fill=tk.X, ipady=5, pady=(3, 8))
            e.insert(0, default)
            entries[key] = e
            if key == "date":
                attach_date_mask(e)

        suggest = {"win": None, "lb": None, "items": [], "field": None}

        def _load_customer_rows():
            try:
                from customers import get_customers
                all_customers = get_customers()
            except Exception:
                all_customers = {}

            rows = []
            for phone, customer in all_customers.items():
                name = str(customer.get("name", "")).strip()
                phone_s = str(phone).strip()
                if not name and not phone_s:
                    continue
                rows.append({
                    "name": name or "Guest",
                    "phone": phone_s,
                    "name_l": name.lower(),
                    "phone_l": phone_s.lower(),
                })
            return rows

        def _hide_customer_popup():
            try:
                if suggest["win"] and suggest["win"].winfo_exists():
                    suggest["win"].destroy()
            except Exception:
                pass
            suggest["win"] = None
            suggest["lb"] = None
            suggest["items"] = []
            suggest["field"] = None

        def _fill_customer_popup(item):
            name, phone = item
            entries["customer"].delete(0, tk.END)
            entries["customer"].insert(0, name)
            entries["phone"].delete(0, tk.END)
            entries["phone"].insert(0, phone)
            _hide_customer_popup()
            entries["service"].focus_set()

        def _move_customer_popup(delta: int = 1):
            lb = suggest.get("lb")
            if (not lb or lb.size() == 0) and suggest.get("field"):
                _show_customer_popup(suggest["field"])
                lb = suggest.get("lb")
            if not lb or lb.size() == 0:
                return "break"
            sel = lb.curselection()
            idx = sel[0] if sel else 0
            if sel:
                idx = max(0, min(idx + delta, lb.size() - 1))
            lb.selection_clear(0, tk.END)
            lb.selection_set(idx)
            lb.activate(idx)
            lb.see(idx)
            return "break"

        def _commit_customer_popup():
            lb = suggest.get("lb")
            items = suggest.get("items") or []
            if lb and lb.size() > 0:
                sel = lb.curselection()
                idx = sel[0] if sel else 0
                _fill_customer_popup(items[idx])
                return "break"
            if len(items) == 1:
                _fill_customer_popup(items[0])
                return "break"
            return None

        def _match_customer_rows(field: str, query: str):
            query = query.strip().lower()
            if not query:
                return []

            starts = []
            contains = []
            for row in _load_customer_rows():
                if field == "phone":
                    primary = row["phone_l"]
                    secondary = row["name_l"]
                else:
                    primary = row["name_l"]
                    secondary = row["phone_l"]
                if primary.startswith(query) or secondary.startswith(query):
                    starts.append((row["name"], row["phone"]))
                elif query in primary or query in secondary:
                    contains.append((row["name"], row["phone"]))
            return (starts + contains)[:12]

        def _show_customer_popup(field: str):
            query = entries[field].get().strip().lower()
            if not query:
                _hide_customer_popup()
                return

            matches = _match_customer_rows(field, query)
            if not matches:
                _hide_customer_popup()
                return

            _hide_customer_popup()
            anchor = entries[field]
            win2 = tk.Toplevel(win)
            win2.wm_overrideredirect(True)
            win2.configure(bg=C["teal"])
            popup_h = min(28 * len(matches) + 4, 220)
            win2.geometry(
                f"{max(320, anchor.winfo_width())}x{popup_h}+"
                f"{anchor.winfo_rootx()}+{anchor.winfo_rooty() + anchor.winfo_height()}"
            )
            try:
                win2.transient(win.winfo_toplevel())
                win2.lift(win.winfo_toplevel())
            except Exception:
                pass

            lb = tk.Listbox(
                win2,
                font=("Arial", 10 if compact else 11),
                bg=C["card"],
                fg=C["text"],
                selectbackground=C["teal"],
                selectforeground="white",
                bd=0,
                activestyle="none",
                exportselection=False,
            )
            lb.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
            for name, phone in matches:
                lb.insert(tk.END, f"  {name}  |  {phone}")
            lb.selection_set(0)
            lb.activate(0)

            def _click_pick(e=None):
                sel = lb.curselection()
                if not sel:
                    return "break"
                _fill_customer_popup(matches[sel[0]])
                return "break"

            lb.bind("<ButtonRelease-1>", _click_pick)
            lb.bind("<Double-Button-1>", _click_pick)
            lb.bind("<Return>", _click_pick)
            lb.bind("<Up>", lambda e: _move_customer_popup(-1))
            lb.bind("<Down>", lambda e: _move_customer_popup(1))
            lb.bind("<Escape>", lambda e: (_hide_customer_popup(), "break")[-1])

            suggest["win"] = win2
            suggest["lb"] = lb
            suggest["items"] = matches
            suggest["field"] = field

        def _on_customer_key(e, field: str):
            if getattr(e, "keysym", "") in {"Up", "Down", "Return", "Escape"}:
                return
            suggest["field"] = field
            _show_customer_popup(field)

        def _move_for_field(field: str, delta: int):
            suggest["field"] = field
            return _move_customer_popup(delta)

        entries["customer"].bind("<KeyRelease>", lambda e: _on_customer_key(e, "customer"))
        entries["phone"].bind("<KeyRelease>", lambda e: _on_customer_key(e, "phone"))
        entries["customer"].bind("<Down>", lambda e: _move_for_field("customer", 1))
        entries["phone"].bind("<Down>", lambda e: _move_for_field("phone", 1))
        entries["customer"].bind("<Up>", lambda e: _move_for_field("customer", -1))
        entries["phone"].bind("<Up>", lambda e: _move_for_field("phone", -1))
        entries["customer"].bind("<Return>", lambda e: _commit_customer_popup())
        entries["phone"].bind("<Return>", lambda e: _commit_customer_popup())
        entries["customer"].bind("<Escape>", lambda e: (_hide_customer_popup(), "break")[-1])
        entries["phone"].bind("<Escape>", lambda e: (_hide_customer_popup(), "break")[-1])
        entries["customer"].bind("<FocusOut>", lambda e: win.after(200, _hide_customer_popup))
        entries["phone"].bind("<FocusOut>", lambda e: win.after(200, _hide_customer_popup))

        # Staff dropdown
        tk.Label(f, text="Staff:", bg=C["bg"],
                 fg=C["muted"], font=("Arial", 11 if compact else 12)).pack(anchor="w")
        from staff import get_staff
        staff_data  = get_staff()
        staff_names = ([
            v.get("name", k)
            for k, v in staff_data.items()
            if isinstance(v, dict) and v.get("active", True)
        ] or ["—"])
        staff_var = tk.StringVar(value=staff_names[0])
        staff_cb  = ttk.Combobox(f, textvariable=staff_var,
                                  values=staff_names, font=("Arial", 10 if compact else 12),
                                  state="readonly")
        staff_cb.pack(fill=tk.X, pady=(3, 8))
        make_searchable_combobox(staff_cb, staff_names)

        def _save():
            nm   = entries["customer"].get().strip()
            ph   = entries["phone"].get().strip()
            svc  = entries["service"].get().strip()
            dt   = entries["date"].get().strip()
            tm   = entries["time"].get().strip()

            # Fix R7b: input validation
            if not nm:
                messagebox.showerror("Error", "Customer name required.")
                return
            if not validate_phone(ph):
                messagebox.showerror("Error",
                                     "Phone must be exactly 10 digits.")
                return
            if not validate_display_date(dt):
                messagebox.showerror("Error",
                                     "Date must be DD-MM-YYYY format.\n"
                                     "Example: 15-06-2025")
                return
            dt = display_to_iso_date(dt)
            if not tm:
                messagebox.showerror("Error", "Time required (HH:MM).")
                return

            try:
                new_appt = {
                    "customer":      nm,
                    "phone":         ph,
                    "service":       svc,
                    "date":          dt,
                    "time":          tm,
                    "staff":         staff_var.get(),
                    "status":        "Scheduled",
                    "created":       now_str(),
                    "dont_show":     False,
                    "last_reminded": "",
                }
                appts = get_appointments()
                appts.append(new_appt)
                save_appointments(appts)
                win.grab_release()
                win.destroy()
                self._load(self.date_var.get())
                messagebox.showinfo("Booked", "Appointment booked!")
            except Exception as e:
                messagebox.showerror("Error", f"Could not book: {e}")

        ModernButton(f, text="Book Appointment", image=get_action_icon("add"), compound="left",
                     command=_save,
                     color=C["teal"], hover_color=C["blue"],
                     width=scaled_value(400, 340, 280), height=scaled_value(38, 36, 32), radius=8,
                     font=("Arial", 10 if compact else 11, "bold"),
                     ).pack(fill=tk.X, pady=(4, 0))
        reveal_when_ready(win)

    # ── Row selection helper ────────────────────────────

    def _get_selected_idx(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select an appointment.")
            return -1, None
        v     = self.tree.item(sel[0], "values")
        appts = get_appointments()
        for i, a in enumerate(appts):
            if (a.get("time",     "") == v[0]
                    and a.get("customer", "") == v[1]
                    and a.get("phone",    "") == v[2]):
                return i, appts
        return -1, None

    def _show_appointment_context_menu(self, event):
        row_id = self.tree.identify_row(getattr(event, "y", 0))
        if not row_id:
            selection = self.tree.selection()
            row_id = selection[0] if selection else self.tree.focus()
        if not row_id:
            return "break"
        try:
            self.tree.selection_set(row_id)
            self.tree.focus(row_id)
            values = self.tree.item(row_id, "values")
            if not values:
                return "break"
            self._register_appointment_context_menu_callbacks()

            from shared.context_menu.constants import WidgetType
            from shared.context_menu.menu_context_factory import build_context
            from shared.context_menu.renderer import renderer_service
            from shared.context_menu_definitions.appointment_context_menu import get_sections

            selected_row = {
                "row_id": row_id,
                "time": values[0] if len(values) > 0 else "",
                "customer": values[1] if len(values) > 1 else "",
                "phone": values[2] if len(values) > 2 else "",
                "service": values[3] if len(values) > 3 else "",
                "staff": values[4] if len(values) > 4 else "",
                "status": values[5] if len(values) > 5 else "",
            }
            context = build_context(
                "appointments",
                entity_type="appointment",
                entity_id=f"{selected_row['time']}|{selected_row['customer']}|{selected_row['phone']}",
                selected_row=selected_row,
                selection_count=1,
                user_role=self.app.current_user.get("role", "") if getattr(self.app, "current_user", None) else "",
                widget_type=WidgetType.TREEVIEW,
                widget_id="appointments_grid",
                screen_x=event.x_root,
                screen_y=event.y_root,
                extra={"has_appointment": True},
            )
            menu = renderer_service.build_menu(self, get_sections(), context)
            x_root = getattr(event, "x_root", None)
            y_root = getattr(event, "y_root", None)
            if x_root is None or y_root is None:
                x_root = self.tree.winfo_rootx() + 24
                y_root = self.tree.winfo_rooty() + 24
            menu.tk_popup(x_root, y_root)
            menu.grab_release()
            return "break"
        except Exception as exc:
            app_log(f"[appointments context menu] {exc}")
            return "break"

    def _register_appointment_context_menu_callbacks(self):
        from shared.context_menu.action_adapter import action_adapter
        from shared.context_menu.clipboard_service import clipboard_service
        from shared.context_menu_definitions.appointment_context_menu import AppointmentContextAction

        action_adapter.register(
            AppointmentContextAction.MARK_COMPLETED,
            lambda _ctx, _act: self._set_status("Completed"),
        )
        action_adapter.register(
            AppointmentContextAction.MARK_CANCELLED,
            lambda _ctx, _act: self._set_status("Cancelled"),
        )
        action_adapter.register(
            AppointmentContextAction.MARK_NO_SHOW,
            lambda _ctx, _act: self._set_status("No Show"),
        )
        action_adapter.register(AppointmentContextAction.SEND_REMINDER, lambda _ctx, _act: self._send_reminder())
        action_adapter.register(
            AppointmentContextAction.COPY_CUSTOMER,
            lambda ctx, _act: clipboard_service.copy_text(self, ctx.selected_row.get("customer", "")),
        )
        action_adapter.register(
            AppointmentContextAction.COPY_PHONE,
            lambda ctx, _act: clipboard_service.copy_text(self, ctx.selected_row.get("phone", "")),
        )
        action_adapter.register(
            AppointmentContextAction.COPY_SERVICE,
            lambda ctx, _act: clipboard_service.copy_text(self, ctx.selected_row.get("service", "")),
        )
        action_adapter.register(AppointmentContextAction.REFRESH, lambda _ctx, _act: self._load(self.date_var.get()))
        action_adapter.register(AppointmentContextAction.DELETE, lambda _ctx, _act: self._delete())

    # ── Status / delete actions ─────────────────────────

    def _set_status(self, status: str):
        i, appts = self._get_selected_idx()
        if i < 0:
            return
        try:
            appts[i]["status"] = status
            save_appointments(appts)
            self._load(self.date_var.get())
        except Exception as e:
            messagebox.showerror("Error", f"Could not update status: {e}")

    def _delete(self):
        i, appts = self._get_selected_idx()
        if i < 0:
            return
        if messagebox.askyesno("Delete", "Delete this appointment?"):
            try:
                appts.pop(i)
                save_appointments(appts)
                self._load(self.date_var.get())
            except Exception as e:
                messagebox.showerror("Error", f"Could not delete: {e}")

    # ── WhatsApp reminder ───────────────────────────────

    def _send_reminder(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select an appointment.")
            return
        v     = self.tree.item(sel[0], "values")
        appts = get_appointments()
        appt  = next((a for a in appts
                      if a.get("time",     "") == v[0]
                      and a.get("customer", "") == v[1]
                      and a.get("phone",    "") == v[2]), {})
        ph  = appt.get("phone", "").strip()
        nm  = appt.get("customer", "Customer")
        # Fix R7h: centralized phone validation from utils
        if not validate_phone(ph):
            messagebox.showerror("Phone", "Valid 10-digit phone required.")
            return
        try:
            from salon_settings import get_settings
            cfg   = get_settings()
            sname = cfg.get("salon_name", get_invoice_branding().get("salon_name", "B-Lite Management"))
            sph   = cfg.get("phone", "")
        except Exception:
            sname = get_invoice_branding().get("salon_name", "B-Lite Management")
            sph   = ""

        parts = [
            f"Dear {nm},",
            "",
            f"Appointment Reminder — {sname}",
            "",
            f"Date    : {iso_to_display_date(appt.get('date', ''))}",
            f"Time    : {appt.get('time', '')}",
            f"Service : {appt.get('service', '')}",
            "",
            "Please arrive on time.",
        ]
        if sph:
            parts.append(f"Contact : {sph}")
        parts.append("")
        parts.append("Thank you!")
        msg = "\n".join(parts)

        import threading

        def _send():
            try:
                from whatsapp_helper import send_text
                ok  = send_text(ph, msg)
                txt = "Reminder sent!" if ok else "Could not send."
                self.after(0, lambda: messagebox.showinfo("WhatsApp", txt))
            except Exception as ex:
                err = str(ex)
                self.after(0, lambda: messagebox.showerror("Error", err))

        threading.Thread(target=_send, daemon=True).start()

    def refresh(self):
        try:
            self._load(self.date_var.get())
        except Exception as e:
            app_log(f"[appointments refresh] {e}")

# v5 appointment compatibility overrides -------------------------------------
def get_appointments() -> list:
    from services_v5.appointment_service import AppointmentService
    from salon_settings import get_settings
    if bool(get_settings().get("use_v5_appointments_db", False)):
        return AppointmentService().build_legacy_appointments()
    return load_json(F_APPOINTMENTS, [])


def save_appointments(data: list) -> bool:
    from services_v5.appointment_service import AppointmentService
    from salon_settings import get_settings
    if bool(get_settings().get("use_v5_appointments_db", False)):
        AppointmentService().sync_legacy_appointments(data)
        return True
    return save_json(F_APPOINTMENTS, data)
