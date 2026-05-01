import calendar
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta

from utils import C, app_log
from ui_theme import ModernButton
from ui_responsive import get_responsive_metrics, scaled_value, fit_toplevel
from icon_system import get_action_icon
from db import get_db
from src.blite_v6.app.window_lifecycle import hide_while_building, reveal_when_ready


STATUS_COLORS = {
    "booked": "#2563eb",
    "completed": "#16a34a",
    "cancelled": "#dc2626",
    "no_show": "#6b7280",
}

TIME_OPTIONS = []
for hour in range(9, 21):
    TIME_OPTIONS.append(f"{hour:02d}:00")
    TIME_OPTIONS.append(f"{hour:02d}:30")
TIME_OPTIONS.append("21:00")


def _color(name, fallback):
    return C.get(name, fallback)


def _parse_date_any(value):
    value = str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d-%m-%y"):
        try:
            return datetime.strptime(value, fmt)
        except Exception:
            pass
    raise ValueError("Date must be in DD-MM-YYYY or YYYY-MM-DD format.")


def _to_storage_date(value):
    return _parse_date_any(value).strftime("%Y-%m-%d")


def _to_display_date(value):
    return _parse_date_any(value).strftime("%d-%m-%Y")


def _ensure_bookings_table():
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL DEFAULT '',
            phone TEXT NOT NULL DEFAULT '',
            service TEXT NOT NULL DEFAULT '',
            staff TEXT NOT NULL DEFAULT '',
            date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'booked',
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_bookings_date ON bookings(date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_bookings_staff_date ON bookings(staff, date)")
    conn.commit()


def _parse_minutes(value):
    try:
        dt = datetime.strptime(value.strip(), "%H:%M")
    except Exception as exc:
        raise ValueError("Time must be in HH:MM format.") from exc
    return dt.hour * 60 + dt.minute


def _validate_date(value):
    try:
        return _to_storage_date(value.strip())
    except Exception as exc:
        raise ValueError("Date must be in DD-MM-YYYY or YYYY-MM-DD format.") from exc


def _slot_label(total_minutes):
    return datetime(2000, 1, 1) + timedelta(minutes=total_minutes)


def _now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _friendly_day(date_value):
    try:
        return _parse_date_any(date_value).strftime("%a, %d %b %Y")
    except Exception:
        return date_value


def _staff_lane_label(name, col_width, total_staff):
    name = str(name or "").strip()
    if not name:
        return "Staff"
    parts = [p for p in name.split() if p]
    if total_staff >= 6 or col_width < 150:
        if len(parts) >= 2:
            return "".join(p[0].upper() for p in parts[:2])
        return name[:2].upper()
    if len(parts) >= 1:
        short = parts[0]
    else:
        short = name
    return short if len(short) <= 10 else f"{short[:9]}."


def _center_toplevel(window, parent, width=None, height=None):
    window.update_idletasks()
    if width is None:
        width = max(window.winfo_reqwidth(), window.winfo_width())
    if height is None:
        height = max(window.winfo_reqheight(), window.winfo_height())
    fit_toplevel(window, width, height, min_width=min(420, width), min_height=min(320, height))


def _place_popup_below(window, anchor_widget, min_width=280):
    window.update_idletasks()
    anchor_widget.update_idletasks()
    width = max(min_width, window.winfo_reqwidth())
    height = max(window.winfo_reqheight(), window.winfo_height())
    x = anchor_widget.winfo_rootx()
    y = anchor_widget.winfo_rooty() + anchor_widget.winfo_height() + 6
    sw = window.winfo_screenwidth()
    sh = window.winfo_screenheight()
    width = min(width, max(280, sw - 40))
    height = min(height, max(220, sh - 80))
    x = min(x, max(20, sw - width - 20))
    y = min(y, max(20, sh - height - 20))
    window.geometry(f"{width}x{height}+{x}+{y}")


def _sync_customer_record(phone, customer_name):
    phone = str(phone or "").strip()
    customer_name = str(customer_name or "").strip()
    if not phone or not customer_name:
        return
    try:
        from adapters.customer_adapter import use_v5_customers_db
        if use_v5_customers_db():
            from services_v5.customer_service import CustomerService
            svc = CustomerService()
            existing = svc.get_customer_by_phone(phone) or {}
            svc.save_customer({
                "phone": phone,
                "name": customer_name,
                "birthday": existing.get("birthday", ""),
                "vip": bool(existing.get("vip", 0)),
                "points_balance": int(existing.get("points_balance", 0) or 0),
            })
            return
    except Exception:
        pass
    try:
        from customers import add_or_update_customer
        add_or_update_customer(phone, customer_name)
    except Exception:
        pass


def list_staff_names():
    _ensure_bookings_table()
    conn = get_db()
    names = []
    try:
        rows = conn.execute(
            "SELECT name FROM staff WHERE COALESCE(active, 1) = 1 ORDER BY name"
        ).fetchall()
        names = [str(row["name"]).strip() for row in rows if str(row["name"]).strip()]
    except Exception:
        names = []
    if not names:
        try:
            from staff import get_staff
            names = [str(name).strip() for name in get_staff().keys() if str(name).strip()]
        except Exception:
            names = []
    if not names:
        try:
            rows = conn.execute(
                "SELECT DISTINCT staff FROM bookings WHERE TRIM(COALESCE(staff, '')) <> '' ORDER BY staff"
            ).fetchall()
            names = [str(row["staff"]).strip() for row in rows if str(row["staff"]).strip()]
        except Exception:
            names = []
    if not names:
        names = ["General"]
    return names


def list_customer_suggestions(query="", limit=12):
    query = str(query or "").strip().lower()
    try:
        from customers import get_customers
        customers = get_customers() or {}
    except Exception:
        customers = {}
    results = []
    for phone, customer in customers.items():
        phone_text = str(phone or "").strip()
        name_text = str((customer or {}).get("name", "")).strip()
        hay = f"{name_text} {phone_text}".lower()
        if query and query not in hay:
            continue
        if not phone_text and not name_text:
            continue
        results.append({
            "phone": phone_text,
            "name": name_text or phone_text,
        })
    results.sort(key=lambda item: (item["name"].lower(), item["phone"]))
    return results[:limit]


def list_bookings(date_value):
    _ensure_bookings_table()
    conn = get_db()
    rows = conn.execute(
        """
        SELECT id, customer_name, phone, service, staff, date, start_time, end_time,
               status, notes, created_at
        FROM bookings
        WHERE date = ?
        ORDER BY start_time, staff, customer_name
        """,
        (date_value,),
    ).fetchall()
    return [dict(row) for row in rows]


def _has_overlap(conn, date_value, staff, start_time, end_time, exclude_id=None):
    start_minutes = _parse_minutes(start_time)
    end_minutes = _parse_minutes(end_time)
    if end_minutes <= start_minutes:
        raise ValueError("End time must be after start time.")
    rows = conn.execute(
        """
        SELECT id, start_time, end_time, status
        FROM bookings
        WHERE date = ? AND staff = ?
        """,
        (date_value, staff.strip()),
    ).fetchall()
    for row in rows:
        row_id = int(row["id"])
        if exclude_id and row_id == int(exclude_id):
            continue
        if str(row["status"]).strip().lower() in {"cancelled", "no_show"}:
            continue
        other_start = _parse_minutes(row["start_time"])
        other_end = _parse_minutes(row["end_time"])
        if start_minutes < other_end and end_minutes > other_start:
            return True
    return False


def save_booking(payload, booking_id=None):
    _ensure_bookings_table()
    customer_name = str(payload.get("customer_name", "")).strip()
    phone = str(payload.get("phone", "")).strip()
    service = str(payload.get("service", "")).strip()
    staff = str(payload.get("staff", "")).strip()
    date_value = _validate_date(str(payload.get("date", "")).strip())
    start_time = str(payload.get("start_time", "")).strip()
    end_time = str(payload.get("end_time", "")).strip()
    status = str(payload.get("status", "booked")).strip().lower() or "booked"
    notes = str(payload.get("notes", "")).strip()

    if not customer_name or not phone or not service or not staff:
        raise ValueError("Customer, phone, service, and staff are required.")
    if status not in STATUS_COLORS:
        raise ValueError("Invalid booking status.")
    _parse_minutes(start_time)
    _parse_minutes(end_time)

    conn = get_db()
    if _has_overlap(conn, date_value, staff, start_time, end_time, exclude_id=booking_id):
        raise ValueError("Booking overlaps with an existing slot for this staff member.")

    if booking_id:
        conn.execute(
            """
            UPDATE bookings
            SET customer_name = ?, phone = ?, service = ?, staff = ?, date = ?,
                start_time = ?, end_time = ?, status = ?, notes = ?
            WHERE id = ?
            """,
            (
                customer_name,
                phone,
                service,
                staff,
                date_value,
                start_time,
                end_time,
                status,
                notes,
                int(booking_id),
            ),
        )
    else:
        conn.execute(
            """
            INSERT INTO bookings (
                customer_name, phone, service, staff, date,
                start_time, end_time, status, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                customer_name,
                phone,
                service,
                staff,
                date_value,
                start_time,
                end_time,
                status,
                notes,
                _now_text(),
            ),
        )
    conn.commit()
    _sync_customer_record(phone, customer_name)


def delete_booking(booking_id):
    _ensure_bookings_table()
    conn = get_db()
    conn.execute("DELETE FROM bookings WHERE id = ?", (int(booking_id),))
    conn.commit()


class BookingModal(tk.Toplevel):
    def __init__(self, parent, booking, staff_names, on_save, on_delete, on_convert, on_reminder):
        super().__init__(parent)
        hide_while_building(self)
        self._responsive = get_responsive_metrics(parent.winfo_toplevel())
        self.booking = dict(booking or {})
        self._on_save = on_save
        self._on_delete = on_delete
        self._on_convert = on_convert
        self._on_reminder = on_reminder
        self.title("Booking Details")
        self.configure(bg=_color("bg", "#111827"))
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        self.resizable(False, False)
        compact = self._responsive["mode"] == "compact"
        btn_h = self._responsive["btn_h"]
        action_w = scaled_value(140, 128, 112)

        self.customer_var = tk.StringVar(value=self.booking.get("customer_name", ""))
        self.phone_var = tk.StringVar(value=self.booking.get("phone", ""))
        self.service_var = tk.StringVar(value=self.booking.get("service", ""))
        self.staff_var = tk.StringVar(value=self.booking.get("staff", staff_names[0] if staff_names else "General"))
        self.date_var = tk.StringVar(value=_to_display_date(self.booking.get("date", datetime.now().strftime("%Y-%m-%d"))))
        self.start_var = tk.StringVar(value=self.booking.get("start_time", "09:00"))
        self.end_var = tk.StringVar(value=self.booking.get("end_time", "09:30"))
        self.status_var = tk.StringVar(value=self.booking.get("status", "booked"))
        self.customer_matches = []

        outer = tk.Frame(self, bg=_color("bg", "#111827"), padx=18, pady=16)
        outer.pack(fill=tk.BOTH, expand=True)

        title_row = tk.Frame(outer, bg=_color("bg", "#111827"))
        title_row.pack(fill=tk.X, pady=(0, 10))
        tk.Label(title_row, text="Shop Booking", bg=_color("bg", "#111827"), fg=_color("text", "#f8fafc"), font=("Arial", 16, "bold")).pack(side=tk.LEFT)

        form = tk.Frame(outer, bg=_color("card", "#1f2937"), padx=14, pady=14)
        form.pack(fill=tk.BOTH, expand=True)

        tk.Label(form, text="Customer Name", bg=_color("card", "#1f2937"), fg=_color("muted", "#94a3b8"), font=("Arial", 10, "bold")).pack(anchor="w", pady=(8, 4))
        self.customer_name_entry = tk.Entry(form, textvariable=self.customer_var, font=("Arial", 11), bg=_color("input", "#111827"), fg=_color("text", "#f8fafc"), insertbackground=_color("accent", "#8b5cf6"), bd=0)
        self.customer_name_entry.pack(fill=tk.X, ipady=6)
        tk.Label(form, text="Phone", bg=_color("card", "#1f2937"), fg=_color("muted", "#94a3b8"), font=("Arial", 10, "bold")).pack(anchor="w", pady=(8, 4))
        self.phone_entry = tk.Entry(form, textvariable=self.phone_var, font=("Arial", 11), bg=_color("input", "#111827"), fg=_color("text", "#f8fafc"), insertbackground=_color("accent", "#8b5cf6"), bd=0)
        self.phone_entry.pack(fill=tk.X, ipady=6)
        self.customer_hint = tk.Label(form, text="Type saved customer name or phone to filter matches.", bg=_color("card", "#1f2937"), fg=_color("muted", "#94a3b8"), font=("Arial", 8))
        self.customer_hint.pack(anchor="w", pady=(4, 3))
        self.customer_suggestions = tk.Listbox(form, height=4 if not compact else 3, font=("Arial", scaled_value(10, 10, 9)), bg=_color("input", "#111827"), fg=_color("text", "#f8fafc"), highlightthickness=1, highlightbackground=_color("muted", "#334155"), selectbackground=_color("accent", "#8b5cf6"), selectforeground="white", bd=0)
        self.customer_suggestions.pack(fill=tk.X, pady=(0, 8))
        self.customer_suggestions.pack_forget()
        self.customer_name_entry.bind("<KeyRelease>", lambda e: self._refresh_customer_suggestions())
        self.phone_entry.bind("<KeyRelease>", lambda e: self._refresh_customer_suggestions())
        self.customer_suggestions.bind("<<ListboxSelect>>", self._apply_customer_suggestion)
        self.customer_suggestions.bind("<Double-Button-1>", self._apply_customer_suggestion)
        self._field(form, "Service", tk.Entry(form, textvariable=self.service_var, font=("Arial", 11), bg=_color("input", "#111827"), fg=_color("text", "#f8fafc"), insertbackground=_color("accent", "#8b5cf6"), bd=0))

        staff_box = ttk.Combobox(form, textvariable=self.staff_var, values=staff_names, state="readonly", font=("Arial", 11))
        self._field(form, "Staff", staff_box)
        date_row = tk.Frame(form, bg=_color("card", "#1f2937"))
        date_entry = tk.Entry(date_row, textvariable=self.date_var, font=("Arial", 11), bg=_color("input", "#111827"), fg=_color("text", "#f8fafc"), insertbackground=_color("accent", "#8b5cf6"), bd=0)
        date_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6)
        self.date_pick_button = ModernButton(date_row, text="Pick", command=self._pick_date, color=_color("sidebar", "#334155"), hover_color=_color("muted", "#64748b"), width=scaled_value(78, 70, 62), height=btn_h, radius=8, font=("Arial", scaled_value(9, 9, 8), "bold"))
        self.date_pick_button.pack(side=tk.LEFT, padx=(8, 0))
        self._field(form, "Date (DD-MM-YYYY)", date_row, packed=True)

        time_row = tk.Frame(form, bg=_color("card", "#1f2937"))
        tk.Label(time_row, text="Start Time", bg=_color("card", "#1f2937"), fg=_color("muted", "#94a3b8"), font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Combobox(time_row, textvariable=self.start_var, values=TIME_OPTIONS[:-1], state="readonly", width=scaled_value(10, 9, 8), font=("Arial", scaled_value(11, 10, 9))).pack(side=tk.LEFT)
        tk.Label(time_row, text="End Time", bg=_color("card", "#1f2937"), fg=_color("muted", "#94a3b8"), font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(14, 8))
        ttk.Combobox(time_row, textvariable=self.end_var, values=TIME_OPTIONS[1:], state="readonly", width=scaled_value(10, 9, 8), font=("Arial", scaled_value(11, 10, 9))).pack(side=tk.LEFT)
        self._field(form, "Time Slot", time_row, packed=True)

        status_box = ttk.Combobox(form, textvariable=self.status_var, values=list(STATUS_COLORS.keys()), state="readonly", font=("Arial", 11))
        self._field(form, "Status", status_box)

        tk.Label(form, text="Notes", bg=_color("card", "#1f2937"), fg=_color("muted", "#94a3b8"), font=("Arial", 10, "bold")).pack(anchor="w", pady=(8, 4))
        self.notes_text = tk.Text(form, height=4 if not compact else 3, font=("Arial", scaled_value(10, 10, 9)), bg=_color("input", "#111827"), fg=_color("text", "#f8fafc"), insertbackground=_color("accent", "#8b5cf6"), bd=0)
        self.notes_text.pack(fill=tk.X)
        self.notes_text.insert("1.0", self.booking.get("notes", ""))

        action_row = tk.Frame(outer, bg=_color("bg", "#111827"))
        action_row.pack(fill=tk.X, pady=(12, 0))

        ModernButton(action_row, text="Save Booking", image=get_action_icon("save"), compound="left", command=self._save, color=_color("green", "#16a34a"), hover_color="#15803d", width=action_w, height=scaled_value(36, 34, 30), radius=10, font=("Arial", scaled_value(10, 10, 9), "bold")).pack(side=tk.LEFT)
        ModernButton(action_row, text="Convert to Bill", image=get_action_icon("billing"), compound="left", command=self._convert, color=_color("teal", "#0891b2"), hover_color=_color("blue", "#2563eb"), width=action_w, height=scaled_value(36, 34, 30), radius=10, font=("Arial", scaled_value(10, 10, 9), "bold")).pack(side=tk.LEFT, padx=(8, 0))
        ModernButton(action_row, text="Reminder", image=get_action_icon("whatsapp"), compound="left", command=self._send_reminder, color="#25d366", hover_color="#1a9e4a", width=scaled_value(120, 112, 96), height=scaled_value(36, 34, 30), radius=10, font=("Arial", scaled_value(10, 10, 9), "bold")).pack(side=tk.LEFT, padx=(8, 0))
        if self.booking.get("id"):
            ModernButton(action_row, text="Delete", image=get_action_icon("clear"), compound="left", command=self._delete, color=_color("red", "#dc2626"), hover_color="#b91c1c", width=scaled_value(110, 102, 88), height=scaled_value(36, 34, 30), radius=10, font=("Arial", scaled_value(10, 10, 9), "bold")).pack(side=tk.LEFT, padx=(8, 0))
        ModernButton(action_row, text="Close", command=self.destroy, color=_color("sidebar", "#334155"), hover_color=_color("muted", "#64748b"), width=scaled_value(108, 100, 88), height=scaled_value(36, 34, 30), radius=10, font=("Arial", scaled_value(10, 10, 9), "bold")).pack(side=tk.RIGHT)
        self._refresh_customer_suggestions()
        self.update_idletasks()
        fit_toplevel(
            self,
            min(max(scaled_value(860, 780, 700), self.winfo_reqwidth()), int(self.winfo_screenwidth() * 0.86)),
            min(max(scaled_value(620, 580, 520), self.winfo_reqheight()), int(self.winfo_screenheight() * 0.84)),
            min_width=680,
            min_height=500,
        )
        reveal_when_ready(self)

    def _field(self, parent, label, widget, packed=False):
        tk.Label(parent, text=label, bg=_color("card", "#1f2937"), fg=_color("muted", "#94a3b8"), font=("Arial", 10, "bold")).pack(anchor="w", pady=(8, 4))
        if packed:
            widget.pack(fill=tk.X)
        else:
            widget.pack(fill=tk.X, ipady=6)

    def _payload(self):
        return {
            "customer_name": self.customer_var.get().strip(),
            "phone": self.phone_var.get().strip(),
            "service": self.service_var.get().strip(),
            "staff": self.staff_var.get().strip(),
            "date": _to_storage_date(self.date_var.get().strip()),
            "start_time": self.start_var.get().strip(),
            "end_time": self.end_var.get().strip(),
            "status": self.status_var.get().strip(),
            "notes": self.notes_text.get("1.0", tk.END).strip(),
        }

    def _pick_date(self):
        DatePickerPopup(self, self.date_var, anchor_widget=self.date_pick_button)

    def _refresh_customer_suggestions(self):
        query = (self.customer_var.get().strip() or self.phone_var.get().strip()).lower()
        matches = list_customer_suggestions(query)
        self.customer_matches = matches
        self.customer_suggestions.delete(0, tk.END)
        if not matches or (len(matches) == 1 and matches[0]["name"] == self.customer_var.get().strip() and matches[0]["phone"] == self.phone_var.get().strip()):
            self.customer_suggestions.pack_forget()
            return
        for item in matches:
            self.customer_suggestions.insert(tk.END, f"{item['name']}  •  {item['phone']}")
        self.customer_suggestions.pack(fill=tk.X, pady=(0, 8))

    def _apply_customer_suggestion(self, event=None):
        selection = self.customer_suggestions.curselection()
        if not selection:
            return
        item = self.customer_matches[selection[0]]
        self.customer_var.set(item["name"])
        self.phone_var.set(item["phone"])
        self.customer_suggestions.pack_forget()

    def _save(self):
        try:
            self._on_save(self._payload(), self.booking.get("id"))
            self.destroy()
        except Exception as exc:
            messagebox.showerror("Booking", str(exc), parent=self)

    def _delete(self):
        if not self.booking.get("id"):
            return
        if not messagebox.askyesno("Delete Booking", "Delete this booking?", parent=self):
            return
        try:
            self._on_delete(self.booking["id"])
            self.destroy()
        except Exception as exc:
            messagebox.showerror("Booking", str(exc), parent=self)

    def _convert(self):
        try:
            self._on_convert({**self.booking, **self._payload()})
        except Exception as exc:
            messagebox.showerror("Convert to Bill", str(exc), parent=self)

    def _send_reminder(self):
        try:
            self._on_reminder({**self.booking, **self._payload()})
        except Exception as exc:
            messagebox.showerror("Reminder", str(exc), parent=self)


class DatePickerPopup(tk.Toplevel):
    def __init__(self, parent, target_var, anchor_widget=None):
        super().__init__(parent)
        hide_while_building(self)
        self._responsive = get_responsive_metrics(parent.winfo_toplevel())
        self.target_var = target_var
        self.anchor_widget = anchor_widget
        self.configure(bg=_color("bg", "#111827"))
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        try:
            current = _parse_date_any(target_var.get().strip())
        except Exception:
            current = datetime.now()
        self.current_month = current.replace(day=1)
        self.title("Pick Date")
        self.resizable(False, False)
        self.body = tk.Frame(self, bg=_color("card", "#1f2937"), padx=12, pady=12)
        self.body.pack(fill=tk.BOTH, expand=True)
        self._render()
        self.update_idletasks()
        if self.anchor_widget is not None:
            _place_popup_below(self, self.anchor_widget, min_width=scaled_value(320, 300, 280))
        else:
            _center_toplevel(self, parent.winfo_toplevel(), width=max(scaled_value(360, 330, 300), self.winfo_reqwidth()), height=max(scaled_value(300, 280, 250), self.winfo_reqheight()))
        reveal_when_ready(self)

    def _render(self):
        for child in self.body.winfo_children():
            child.destroy()
        top = tk.Frame(self.body, bg=_color("card", "#1f2937"))
        top.pack(fill=tk.X, pady=(0, 8))
        ModernButton(top, text="<", command=lambda: self._move_month(-1), color=_color("sidebar", "#334155"), hover_color=_color("muted", "#64748b"), width=scaled_value(40, 38, 34), height=scaled_value(28, 28, 24), radius=8, font=("Arial", scaled_value(10, 10, 9), "bold")).pack(side=tk.LEFT)
        tk.Label(top, text=self.current_month.strftime("%B %Y"), bg=_color("card", "#1f2937"), fg=_color("text", "#f8fafc"), font=("Arial", scaled_value(12, 11, 10), "bold")).pack(side=tk.LEFT, expand=True)
        ModernButton(top, text=">", command=lambda: self._move_month(1), color=_color("sidebar", "#334155"), hover_color=_color("muted", "#64748b"), width=scaled_value(40, 38, 34), height=scaled_value(28, 28, 24), radius=8, font=("Arial", scaled_value(10, 10, 9), "bold")).pack(side=tk.RIGHT)

        grid = tk.Frame(self.body, bg=_color("card", "#1f2937"))
        grid.pack()
        for idx, day in enumerate(("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")):
            tk.Label(grid, text=day, width=4, bg=_color("card", "#1f2937"), fg=_color("muted", "#94a3b8"), font=("Arial", scaled_value(9, 9, 8), "bold")).grid(row=0, column=idx, padx=2, pady=2)

        month_days = calendar.monthcalendar(self.current_month.year, self.current_month.month)
        today_text = datetime.now().strftime("%d-%m-%Y")
        for row_idx, week in enumerate(month_days, start=1):
            for col_idx, day_no in enumerate(week):
                if day_no == 0:
                    tk.Label(grid, text="", width=4, bg=_color("card", "#1f2937")).grid(row=row_idx, column=col_idx, padx=2, pady=2)
                    continue
                date_obj = self.current_month.replace(day=day_no)
                date_text = date_obj.strftime("%d-%m-%Y")
                is_today = date_text == today_text
                color = _color("accent", "#8b5cf6") if is_today else _color("input", "#111827")
                ModernButton(grid, text=str(day_no), command=lambda value=date_text: self._pick(value), color=color, hover_color=_color("blue", "#2563eb"), width=scaled_value(36, 34, 30), height=scaled_value(28, 28, 24), radius=8, font=("Arial", scaled_value(9, 9, 8), "bold")).grid(row=row_idx, column=col_idx, padx=2, pady=2)

    def _move_month(self, delta):
        year = self.current_month.year + ((self.current_month.month - 1 + delta) // 12)
        month = ((self.current_month.month - 1 + delta) % 12) + 1
        self.current_month = self.current_month.replace(year=year, month=month, day=1)
        self._render()

    def _pick(self, date_text):
        self.target_var.set(date_text)
        self.destroy()


class BookingCalendarFrame(tk.Frame):
    TIME_COL_W = 90
    STAFF_COL_W = 230
    HEADER_H = 64
    SLOT_H = 56
    START_HOUR = 9
    END_HOUR = 21

    def __init__(self, parent, app):
        super().__init__(parent, bg=_color("bg", "#111827"))
        self.app = app
        self._responsive = get_responsive_metrics(parent.winfo_toplevel())
        self.selected_date = tk.StringVar(value=datetime.now().strftime("%d-%m-%Y"))
        self.staff_filter_var = tk.StringVar(value="All Staff")
        self.search_var = tk.StringVar(value="")
        self.staff_names = list_staff_names()
        self.bookings = []
        self.filtered_bookings = []
        self.visible_staff_names = list(self.staff_names)
        self.selected_booking_id = None
        self.canvas = None
        self.day_card_wrap = None
        self.list_inner = None
        self.detail_labels = {}
        self.detail_notes = None
        self.detail_status_chip = None
        self.metric_labels = {}
        self.timeline_title = None
        self._build()
        self.reload()

    def _build(self):
        self._responsive = get_responsive_metrics(self.winfo_toplevel())
        self._build_header()
        self._build_week_strip()
        self._build_main_shell()

    def _build_header(self):
        compact = self._responsive["mode"] == "compact"
        header = tk.Frame(self, bg=_color("bg", "#111827"), padx=16, pady=12)
        header.pack(fill=tk.X)

        title_wrap = tk.Frame(header, bg=_color("bg", "#111827"))
        title_wrap.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(title_wrap, text="Shop Booking Calendar", bg=_color("bg", "#111827"), fg=_color("text", "#f8fafc"), font=("Arial", scaled_value(18, 16, 14), "bold")).pack(anchor="w")
        tk.Label(title_wrap, text="Date-wise schedule with staff columns, booking details, and quick billing handoff.", bg=_color("bg", "#111827"), fg=_color("muted", "#94a3b8"), font=("Arial", scaled_value(10, 10, 9))).pack(anchor="w", pady=(4, 0))

        actions = tk.Frame(header, bg=_color("bg", "#111827"))
        actions.pack(side=tk.RIGHT)
        ModernButton(actions, text="Prev", command=lambda: self._shift_day(-1), color=_color("sidebar", "#334155"), hover_color=_color("muted", "#64748b"), width=scaled_value(82, 74, 64), height=scaled_value(34, 32, 28), radius=10, font=("Arial", scaled_value(10, 10, 9), "bold")).pack(side=tk.LEFT)
        self.date_entry = tk.Entry(actions, textvariable=self.selected_date, width=11 if compact else 12, font=("Arial", scaled_value(11, 10, 9), "bold"), bg=_color("input", "#0f172a"), fg=_color("text", "#f8fafc"), insertbackground=_color("accent", "#8b5cf6"), bd=0, justify="center")
        self.date_entry.pack(side=tk.LEFT, padx=8, ipady=7)
        self.header_pick_button = ModernButton(actions, text="Pick", command=lambda: DatePickerPopup(self, self.selected_date, anchor_widget=self.header_pick_button), color=_color("sidebar", "#334155"), hover_color=_color("muted", "#64748b"), width=scaled_value(74, 68, 60), height=scaled_value(34, 32, 28), radius=10, font=("Arial", scaled_value(10, 10, 9), "bold"))
        self.header_pick_button.pack(side=tk.LEFT)
        ModernButton(actions, text="Load", command=self.reload, color=_color("purple", _color("accent", "#8b5cf6")), hover_color=_color("blue", "#2563eb"), width=scaled_value(82, 74, 64), height=scaled_value(34, 32, 28), radius=10, font=("Arial", scaled_value(10, 10, 9), "bold")).pack(side=tk.LEFT)
        ModernButton(actions, text="Today", command=self._go_today, color=_color("teal", "#0891b2"), hover_color=_color("blue", "#2563eb"), width=scaled_value(88, 78, 68), height=scaled_value(34, 32, 28), radius=10, font=("Arial", scaled_value(10, 10, 9), "bold")).pack(side=tk.LEFT, padx=(8, 0))
        ModernButton(actions, text="Next", command=lambda: self._shift_day(1), color=_color("sidebar", "#334155"), hover_color=_color("muted", "#64748b"), width=scaled_value(82, 74, 64), height=scaled_value(34, 32, 28), radius=10, font=("Arial", scaled_value(10, 10, 9), "bold")).pack(side=tk.LEFT, padx=(8, 0))

    def _build_week_strip(self):
        compact = self._responsive["mode"] == "compact"
        strip_shell = tk.Frame(self, bg=_color("bg", "#111827"), padx=16, pady=0)
        strip_shell.pack(fill=tk.X)

        strip_card = tk.Frame(strip_shell, bg=_color("card", "#1f2937"), padx=10, pady=10, highlightthickness=1, highlightbackground=_color("muted", "#334155"))
        strip_card.pack(fill=tk.X, pady=(0, 8))
        tk.Label(strip_card, text="Quick Date Switch", bg=_color("card", "#1f2937"), fg=_color("text", "#f8fafc"), font=("Arial", 11, "bold")).pack(anchor="w")
        tk.Label(strip_card, text="Use the week strip, pick a date, or type DD-MM-YYYY.", bg=_color("card", "#1f2937"), fg=_color("muted", "#94a3b8"), font=("Arial", 9)).pack(anchor="w", pady=(2, 8))
        self.day_card_wrap = tk.Frame(strip_card, bg=_color("card", "#1f2937"))
        self.day_card_wrap.pack(fill=tk.X)

        filter_row = tk.Frame(strip_card, bg=_color("card", "#1f2937"))
        filter_row.pack(fill=tk.X, pady=(10, 0))
        tk.Label(filter_row, text="Staff", bg=_color("card", "#1f2937"), fg=_color("muted", "#94a3b8"), font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        self.staff_filter_box = ttk.Combobox(filter_row, textvariable=self.staff_filter_var, state="readonly", width=16 if compact else 18, font=("Arial", scaled_value(10, 10, 9)))
        self.staff_filter_box.pack(side=tk.LEFT, padx=(8, 14))
        self.staff_filter_box.bind("<<ComboboxSelected>>", lambda e: self._apply_filters())
        tk.Label(filter_row, text="Search", bg=_color("card", "#1f2937"), fg=_color("muted", "#94a3b8"), font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        search_entry = tk.Entry(filter_row, textvariable=self.search_var, font=("Arial", scaled_value(10, 10, 9)), bg=_color("input", "#111827"), fg=_color("text", "#f8fafc"), insertbackground=_color("accent", "#8b5cf6"), bd=0)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 8), ipady=6)
        search_entry.bind("<KeyRelease>", lambda e: self._apply_filters())
        ModernButton(filter_row, text="Clear", command=self._clear_filters, color=_color("sidebar", "#334155"), hover_color=_color("muted", "#64748b"), width=scaled_value(74, 68, 60), height=scaled_value(30, 30, 26), radius=8, font=("Arial", scaled_value(9, 9, 8), "bold")).pack(side=tk.LEFT)

    def _build_main_shell(self):
        shell = tk.PanedWindow(self, bg=_color("bg", "#111827"), sashwidth=8, sashrelief=tk.FLAT, bd=0, orient=tk.HORIZONTAL)
        shell.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 14))

        self.sidebar = tk.Frame(shell, bg=_color("bg", "#111827"))
        self.scheduler = tk.Frame(shell, bg=_color("bg", "#111827"))
        shell.add(self.sidebar, minsize=scaled_value(320, 280, 240), width=scaled_value(400, 340, 280))
        shell.add(self.scheduler, minsize=scaled_value(720, 620, 520))

        self._build_sidebar()
        self._build_scheduler()

    def _build_sidebar(self):
        metrics = tk.Frame(self.sidebar, bg=_color("card", "#1f2937"), padx=12, pady=8, highlightthickness=1, highlightbackground=_color("muted", "#334155"))
        metrics.pack(fill=tk.X, pady=(0, 8))
        tk.Label(metrics, text="Day Overview", bg=_color("card", "#1f2937"), fg=_color("text", "#f8fafc"), font=("Arial", 12, "bold")).pack(anchor="w")
        tk.Label(metrics, text="Quick summary for the selected day.", bg=_color("card", "#1f2937"), fg=_color("muted", "#94a3b8"), font=("Arial", 9)).pack(anchor="w", pady=(2, 8))

        metric_grid = tk.Frame(metrics, bg=_color("card", "#1f2937"))
        metric_grid.pack(fill=tk.X)
        for idx, title in enumerate(("Bookings", "Staff", "Booked", "Done")):
            card = tk.Frame(metric_grid, bg=_color("input", "#111827"), padx=10, pady=5, highlightthickness=1, highlightbackground=_color("muted", "#334155"))
            row, col = divmod(idx, 2)
            card.grid(row=row, column=col, sticky="nsew", padx=4, pady=4)
            metric_grid.grid_columnconfigure(col, weight=1)
            tk.Label(card, text=title, bg=_color("input", "#111827"), fg=_color("muted", "#94a3b8"), font=("Arial", 9)).pack(anchor="w")
            value = tk.Label(card, text="0", bg=_color("input", "#111827"), fg=_color("text", "#f8fafc"), font=("Arial", 15, "bold"))
            value.pack(anchor="w", pady=(2, 0))
            self.metric_labels[title] = value

        day_list_card = tk.Frame(self.sidebar, bg=_color("card", "#1f2937"), padx=12, pady=8, highlightthickness=1, highlightbackground=_color("muted", "#334155"))
        day_list_card.pack(fill=tk.BOTH, expand=True)
        header_row = tk.Frame(day_list_card, bg=_color("card", "#1f2937"))
        header_row.pack(fill=tk.X)
        tk.Label(header_row, text="Bookings For Selected Date", bg=_color("card", "#1f2937"), fg=_color("text", "#f8fafc"), font=("Arial", 11, "bold")).pack(side=tk.LEFT)
        self.day_list_count = tk.Label(header_row, text="0", bg=_color("sidebar", "#334155"), fg="white", font=("Arial", 8, "bold"), padx=7, pady=2)
        self.day_list_count.pack(side=tk.RIGHT)
        tk.Label(day_list_card, text="Single click for details, double click to edit.", bg=_color("card", "#1f2937"), fg=_color("muted", "#94a3b8"), font=("Arial", 8)).pack(anchor="w", pady=(2, 6))

        list_wrap = tk.Frame(day_list_card, bg=_color("card", "#1f2937"))
        list_wrap.pack(fill=tk.BOTH, expand=True)
        list_canvas = tk.Canvas(list_wrap, bg=_color("card", "#1f2937"), highlightthickness=0)
        list_scroll = ttk.Scrollbar(list_wrap, orient="vertical", command=list_canvas.yview)
        list_canvas.configure(yscrollcommand=list_scroll.set)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        list_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.list_inner = tk.Frame(list_canvas, bg=_color("card", "#1f2937"))
        list_canvas.create_window((0, 0), window=self.list_inner, anchor="nw")
        self.list_inner.bind("<Configure>", lambda e: list_canvas.configure(scrollregion=list_canvas.bbox("all")))

    def _build_detail_panel(self, parent):
        compact = self._responsive["mode"] == "compact"
        detail_shell = tk.Frame(parent, bg=_color("card", "#1f2937"), padx=12, pady=12, highlightthickness=1, highlightbackground=_color("muted", "#334155"))
        detail_shell.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        detail_shell.configure(width=scaled_value(340, 300, 250))
        detail_shell.pack_propagate(False)

        top = tk.Frame(detail_shell, bg=_color("card", "#1f2937"))
        top.pack(fill=tk.X)
        tk.Label(top, text="Selected Booking", bg=_color("card", "#1f2937"), fg=_color("text", "#f8fafc"), font=("Arial", 12, "bold")).pack(side=tk.LEFT)
        self.detail_status_chip = tk.Label(top, text="No selection", bg=_color("sidebar", "#334155"), fg="white", font=("Arial", 9, "bold"), padx=10, pady=4)
        self.detail_status_chip.pack(side=tk.RIGHT)
        tk.Label(detail_shell, text="Click a booking in the timeline or list to inspect it.", bg=_color("card", "#1f2937"), fg=_color("muted", "#94a3b8"), font=("Arial", scaled_value(9, 9, 8)), wraplength=scaled_value(310, 270, 220), justify="left").pack(anchor="w", pady=(4, 10))

        meta = tk.Frame(detail_shell, bg=_color("card", "#1f2937"))
        meta.pack(fill=tk.X, pady=(0, 4))
        for label in ("Customer", "Phone", "Service", "Staff", "Date", "Time", "Created"):
            row = tk.Frame(meta, bg=_color("card", "#1f2937"))
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=label, width=9 if compact else 10, anchor="w", bg=_color("card", "#1f2937"), fg=_color("muted", "#94a3b8"), font=("Arial", scaled_value(9, 9, 8), "bold")).pack(side=tk.LEFT)
            value = tk.Label(row, text="--", anchor="w", bg=_color("card", "#1f2937"), fg=_color("text", "#f8fafc"), font=("Arial", scaled_value(9, 9, 8)))
            value.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.detail_labels[label] = value

        tk.Label(detail_shell, text="Notes", bg=_color("card", "#1f2937"), fg=_color("muted", "#94a3b8"), font=("Arial", scaled_value(9, 9, 8), "bold")).pack(anchor="w", pady=(6, 3))
        self.detail_notes = tk.Label(detail_shell, text="Select a booking to see customer notes.", justify="left", wraplength=scaled_value(300, 260, 210), anchor="nw", bg=_color("input", "#111827"), fg=_color("text", "#f8fafc"), font=("Arial", scaled_value(9, 9, 8)), padx=10, pady=8, height=4 if compact else 5)
        self.detail_notes.pack(fill=tk.X)

        action_row = tk.Frame(detail_shell, bg=_color("card", "#1f2937"))
        action_row.pack(fill=tk.X, pady=(10, 0))
        ModernButton(action_row, text="Edit", command=self._edit_selected, color=_color("accent", "#8b5cf6"), hover_color=_color("blue", "#2563eb"), width=scaled_value(84, 78, 70), height=scaled_value(32, 30, 28), radius=10, font=("Arial", scaled_value(9, 9, 8), "bold")).pack(side=tk.LEFT)
        ModernButton(action_row, text="Delete", command=self._delete_selected, color=_color("red", "#dc2626"), hover_color="#b91c1c", width=scaled_value(84, 78, 70), height=scaled_value(32, 30, 28), radius=10, font=("Arial", scaled_value(9, 9, 8), "bold")).pack(side=tk.LEFT, padx=(6, 0))
        ModernButton(action_row, text="Convert", command=self._convert_selected, color=_color("green", "#16a34a"), hover_color="#15803d", width=scaled_value(96, 88, 78), height=scaled_value(32, 30, 28), radius=10, font=("Arial", scaled_value(9, 9, 8), "bold")).pack(side=tk.RIGHT)

    def _build_scheduler(self):
        card = tk.Frame(self.scheduler, bg=_color("card", "#1f2937"), padx=12, pady=12, highlightthickness=1, highlightbackground=_color("muted", "#334155"))
        card.pack(fill=tk.BOTH, expand=True)

        top = tk.Frame(card, bg=_color("card", "#1f2937"))
        top.pack(fill=tk.X, pady=(0, 8))
        self.timeline_title = tk.Label(top, text="Day Timeline", bg=_color("card", "#1f2937"), fg=_color("text", "#f8fafc"), font=("Arial", 12, "bold"))
        self.timeline_title.pack(side=tk.LEFT)
        top_actions = tk.Frame(top, bg=_color("card", "#1f2937"))
        top_actions.pack(side=tk.RIGHT)
        tk.Label(top_actions, text="Click empty slot to create. Click booking to inspect. Double click to edit.", bg=_color("card", "#1f2937"), fg=_color("muted", "#94a3b8"), font=("Arial", scaled_value(9, 9, 8))).pack(side=tk.LEFT, padx=(0, 10))
        ModernButton(top_actions, text="Quick Booking", image=get_action_icon("add"), compound="left", command=self._new_booking, color=_color("accent", "#8b5cf6"), hover_color=_color("blue", "#2563eb"), width=scaled_value(140, 128, 108), height=scaled_value(32, 30, 28), radius=10, font=("Arial", scaled_value(9, 9, 8), "bold")).pack(side=tk.LEFT)

        legend = tk.Frame(card, bg=_color("card", "#1f2937"))
        legend.pack(fill=tk.X, pady=(0, 8))
        for key, label in (("booked", "Booked"), ("completed", "Completed"), ("cancelled", "Cancelled"), ("no_show", "No Show")):
            chip = tk.Frame(legend, bg=_color("card", "#1f2937"))
            chip.pack(side=tk.LEFT, padx=(0, 14))
            dot = tk.Canvas(chip, width=12, height=12, bg=_color("card", "#1f2937"), highlightthickness=0)
            dot.pack(side=tk.LEFT)
            dot.create_oval(2, 2, 10, 10, fill=STATUS_COLORS[key], outline="")
            tk.Label(chip, text=label, bg=_color("card", "#1f2937"), fg=_color("muted", "#94a3b8"), font=("Arial", 10)).pack(side=tk.LEFT, padx=(6, 0))

        content = tk.Frame(card, bg=_color("card", "#1f2937"))
        content.pack(fill=tk.BOTH, expand=True)

        timeline_shell = tk.Frame(content, bg=_color("card", "#1f2937"))
        timeline_shell.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._build_detail_panel(content)

        canvas_wrap = tk.Frame(timeline_shell, bg=_color("card", "#1f2937"))
        canvas_wrap.pack(fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(canvas_wrap, bg=_color("surface", _color("bg", "#111827")), highlightthickness=0)
        yscroll = ttk.Scrollbar(canvas_wrap, orient="vertical", command=self.canvas.yview)
        xscroll = ttk.Scrollbar(timeline_shell, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        xscroll.pack(fill=tk.X)
        self.canvas.bind("<Button-1>", self._on_canvas_single_click)
        self.canvas.bind("<Double-1>", self._on_canvas_double_click)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Shift-MouseWheel>", self._on_shift_mousewheel)
        self.canvas.bind("<Configure>", lambda e: self.after_idle(self._draw_calendar))

    def refresh(self):
        self.reload()

    def _go_today(self):
        self.selected_date.set(datetime.now().strftime("%d-%m-%Y"))
        self.reload()

    def _shift_day(self, delta):
        try:
            current = _parse_date_any(self.selected_date.get().strip())
        except Exception:
            current = datetime.now()
        self.selected_date.set((current + timedelta(days=delta)).strftime("%d-%m-%Y"))
        self.reload()

    def _new_booking(self):
        self._open_modal({
            "date": _to_storage_date(self.selected_date.get().strip()),
            "staff": self.visible_staff_names[0] if self.visible_staff_names else (self.staff_names[0] if self.staff_names else "General"),
            "start_time": "09:00",
            "end_time": "09:30",
            "status": "booked",
        })

    def reload(self):
        try:
            self.staff_names = list_staff_names()
            date_value = _validate_date(self.selected_date.get().strip())
            self.selected_date.set(_to_display_date(date_value))
            self.bookings = list_bookings(date_value)
            self.staff_filter_box.configure(values=["All Staff"] + self.staff_names)
            if self.staff_filter_var.get() not in (["All Staff"] + self.staff_names):
                self.staff_filter_var.set("All Staff")
            self._apply_filters()
        except Exception as exc:
            app_log(f"[BookingCalendar.reload] {exc}")
            messagebox.showerror("Booking Calendar", str(exc))

    def _apply_filters(self):
        query = self.search_var.get().strip().lower()
        selected_staff = self.staff_filter_var.get().strip()
        visible = []
        for booking in self.bookings:
            if selected_staff and selected_staff != "All Staff" and booking["staff"] != selected_staff:
                continue
            hay = " ".join([
                str(booking.get("customer_name", "")),
                str(booking.get("phone", "")),
                str(booking.get("service", "")),
                str(booking.get("notes", "")),
                str(booking.get("staff", "")),
            ]).lower()
            if query and query not in hay:
                continue
            visible.append(booking)
        self.filtered_bookings = visible
        self.visible_staff_names = [selected_staff] if selected_staff and selected_staff != "All Staff" else list(self.staff_names)
        if not self.visible_staff_names:
            self.visible_staff_names = list(self.staff_names) or ["General"]
        if self.selected_booking_id is not None and not any(int(item["id"]) == int(self.selected_booking_id) for item in self.filtered_bookings):
            self.selected_booking_id = None
        if self.selected_booking_id is None and self.filtered_bookings:
            self.selected_booking_id = int(self.filtered_bookings[0]["id"])
        self._populate_week_strip()
        self._refresh_metrics()
        self._populate_day_list()
        self._refresh_selected_details()
        self._draw_calendar()

    def _clear_filters(self):
        self.staff_filter_var.set("All Staff")
        self.search_var.set("")
        self._apply_filters()

    def _populate_week_strip(self):
        for child in self.day_card_wrap.winfo_children():
            child.destroy()

        current = _parse_date_any(self.selected_date.get().strip())
        start = current - timedelta(days=3)
        for offset in range(7):
            day = start + timedelta(days=offset)
            value = day.strftime("%d-%m-%Y")
            is_selected = value == self.selected_date.get().strip()
            card_bg = _color("accent", "#8b5cf6") if is_selected else _color("input", "#111827")
            fg = "white" if is_selected else _color("text", "#f8fafc")
            muted = "#e9d5ff" if is_selected else _color("muted", "#94a3b8")
            card = tk.Frame(self.day_card_wrap, bg=card_bg, padx=8, pady=8, highlightthickness=1, highlightbackground=_color("muted", "#334155"), cursor="hand2")
            card.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=2)
            for text, font, text_fg in ((day.strftime("%a"), ("Arial", 9, "bold"), muted), (day.strftime("%d"), ("Arial", 16, "bold"), fg), (day.strftime("%b"), ("Arial", 9), muted)):
                item = tk.Label(card, text=text, bg=card_bg, fg=text_fg, font=font)
                item.pack()
                item.bind("<Button-1>", lambda e, selected=value: self._set_date(selected))
            card.bind("<Button-1>", lambda e, selected=value: self._set_date(selected))

    def _set_date(self, date_value):
        self.selected_date.set(date_value)
        self.reload()

    def _refresh_metrics(self):
        counts = {"Bookings": len(self.filtered_bookings), "Staff": len(self.visible_staff_names), "Booked": 0, "Done": 0}
        for booking in self.filtered_bookings:
            status = str(booking.get("status", "")).strip().lower()
            if status == "booked":
                counts["Booked"] += 1
            if status == "completed":
                counts["Done"] += 1
        for key, label in self.metric_labels.items():
            label.configure(text=str(counts.get(key, 0)))
        self.timeline_title.configure(text=f"Day Timeline - {_friendly_day(self.selected_date.get().strip())}")

    def _populate_day_list(self):
        for child in self.list_inner.winfo_children():
            child.destroy()
        self.day_list_count.configure(text=str(len(self.filtered_bookings)))

        if not self.filtered_bookings:
            empty = tk.Label(self.list_inner, text="No bookings for this date.\nClick an empty slot or use Quick Booking.", bg=_color("card", "#1f2937"), fg=_color("muted", "#94a3b8"), font=("Arial", 10), justify="center", pady=20)
            empty.pack(fill=tk.X)
            return

        for booking in self.filtered_bookings:
            is_selected = int(booking["id"]) == int(self.selected_booking_id) if self.selected_booking_id is not None else False
            bg = _color("sidebar", "#334155") if is_selected else _color("input", "#111827")
            frame = tk.Frame(self.list_inner, bg=bg, padx=10, pady=8, highlightthickness=1, highlightbackground=_color("muted", "#334155"), cursor="hand2")
            frame.pack(fill=tk.X, pady=4)

            top = tk.Frame(frame, bg=bg)
            top.pack(fill=tk.X)
            tk.Label(top, text=booking["customer_name"], bg=bg, fg=_color("text", "#f8fafc"), font=("Arial", 10, "bold")).pack(side=tk.LEFT)
            tk.Label(top, text=booking["status"].replace("_", " ").title(), bg=STATUS_COLORS.get(booking["status"], _color("sidebar", "#334155")), fg="white", font=("Arial", 8, "bold"), padx=8, pady=2).pack(side=tk.RIGHT)

            tk.Label(frame, text=f"{booking['start_time']} - {booking['end_time']}  |  {booking['staff']}", bg=bg, fg=_color("muted", "#94a3b8"), font=("Arial", 9)).pack(anchor="w", pady=(4, 0))
            tk.Label(frame, text=f"{booking['service']}  |  {booking['phone']}", bg=bg, fg=_color("muted", "#94a3b8"), font=("Arial", 9)).pack(anchor="w", pady=(2, 0))

            frame.bind("<Button-1>", lambda e, booking_id=booking["id"]: self._select_booking(booking_id))
            frame.bind("<Double-1>", lambda e, booking_id=booking["id"]: self._edit_booking(booking_id))
            for child in frame.winfo_children():
                child.bind("<Button-1>", lambda e, booking_id=booking["id"]: self._select_booking(booking_id))
                child.bind("<Double-1>", lambda e, booking_id=booking["id"]: self._edit_booking(booking_id))

    def _refresh_selected_details(self):
        booking = self._find_booking(self.selected_booking_id) if self.selected_booking_id is not None else None
        if not booking:
            for label in self.detail_labels.values():
                label.configure(text="--")
            self.detail_notes.configure(text="Select a booking to see customer notes.")
            self.detail_status_chip.configure(text="No selection", bg=_color("sidebar", "#334155"))
            return

        self.detail_labels["Customer"].configure(text=booking["customer_name"])
        self.detail_labels["Phone"].configure(text=booking["phone"])
        self.detail_labels["Service"].configure(text=booking["service"])
        self.detail_labels["Staff"].configure(text=booking["staff"])
        self.detail_labels["Date"].configure(text=_friendly_day(booking["date"]))
        self.detail_labels["Time"].configure(text=f"{booking['start_time']} - {booking['end_time']}")
        self.detail_labels["Created"].configure(text=str(booking.get("created_at", "--")))
        self.detail_notes.configure(text=booking.get("notes") or "No customer notes for this booking.")
        self.detail_status_chip.configure(text=booking["status"].replace("_", " ").title(), bg=STATUS_COLORS.get(booking["status"], _color("sidebar", "#334155")))

    def _draw_calendar(self):
        canvas = self.canvas
        canvas.delete("all")
        total_slots = (self.END_HOUR - self.START_HOUR) * 2
        visible_staff = self.visible_staff_names or self.staff_names or ["General"]
        canvas.update_idletasks()
        available_width = max(canvas.winfo_width() - self.TIME_COL_W - 24, 0)
        dynamic_col_w = max(self.STAFF_COL_W, int(available_width / max(1, len(visible_staff)))) if available_width else self.STAFF_COL_W
        width = self.TIME_COL_W + len(visible_staff) * dynamic_col_w
        height = self.HEADER_H + total_slots * self.SLOT_H
        border_color = _color("border", _color("muted", "#334155"))
        header_fill = _color("card", "#1f2937")
        surface_fill = _color("surface", _color("bg", "#111827"))
        alt_fill = _color("bg", "#111827")
        canvas.config(scrollregion=(0, 0, width, height))

        canvas.create_rectangle(0, 0, width, self.HEADER_H, fill=header_fill, outline=border_color)
        canvas.create_text(18, self.HEADER_H / 2, text="Time", fill=_color("text", "#f8fafc"), font=("Arial", 12, "bold"), anchor="w")

        for index, staff in enumerate(visible_staff):
            x0 = self.TIME_COL_W + index * dynamic_col_w
            x1 = x0 + dynamic_col_w
            canvas.create_rectangle(x0, 0, x1, self.HEADER_H, fill=header_fill, outline=border_color)
            header_text = _staff_lane_label(staff, dynamic_col_w, len(visible_staff))
            canvas.create_text(x0 + 14, self.HEADER_H / 2, text=header_text, fill=_color("text", "#f8fafc"), font=("Arial", 11, "bold"), anchor="w")

        for slot_index in range(total_slots):
            minute_total = self.START_HOUR * 60 + slot_index * 30
            y0 = self.HEADER_H + slot_index * self.SLOT_H
            y1 = y0 + self.SLOT_H
            label = _slot_label(minute_total).strftime("%I:%M %p").lstrip("0")
            canvas.create_rectangle(0, y0, self.TIME_COL_W, y1, fill=header_fill, outline=border_color)
            canvas.create_text(12, y0 + self.SLOT_H / 2, text=label, fill=_color("muted", "#94a3b8"), font=("Arial", 9), anchor="w")
            for index in range(len(visible_staff)):
                x0 = self.TIME_COL_W + index * dynamic_col_w
                x1 = x0 + dynamic_col_w
                fill = surface_fill if slot_index % 2 == 0 else alt_fill
                canvas.create_rectangle(x0, y0, x1, y1, fill=fill, outline=border_color, tags=("slot", f"slot:{index}:{slot_index}"))

        today_line_y = None
        today_line_x1 = None
        try:
            if _to_storage_date(self.selected_date.get().strip()) == datetime.now().strftime("%Y-%m-%d"):
                now = datetime.now()
                mins = now.hour * 60 + now.minute
                if self.START_HOUR * 60 <= mins <= self.END_HOUR * 60:
                    today_line_y = self.HEADER_H + ((mins - self.START_HOUR * 60) / 30.0) * self.SLOT_H
                    today_line_x1 = self.TIME_COL_W + len(visible_staff) * dynamic_col_w
        except Exception:
            today_line_y = None

        for booking in self.filtered_bookings:
            try:
                staff_index = visible_staff.index(booking["staff"])
            except ValueError:
                continue
            start_minutes = _parse_minutes(booking["start_time"])
            end_minutes = _parse_minutes(booking["end_time"])
            slot_offset = (start_minutes - self.START_HOUR * 60) / 30
            slot_span = max(1, (end_minutes - start_minutes) / 30)
            x0 = self.TIME_COL_W + staff_index * dynamic_col_w + 8
            x1 = x0 + dynamic_col_w - 16
            y0 = self.HEADER_H + slot_offset * self.SLOT_H + 6
            y1 = y0 + slot_span * self.SLOT_H - 12
            fill = STATUS_COLORS.get(str(booking["status"]).strip().lower(), STATUS_COLORS["booked"])
            outline = "white" if self.selected_booking_id is not None and int(booking["id"]) == int(self.selected_booking_id) else ""
            tag = f"booking:{booking['id']}"
            canvas.create_rectangle(x0, y0, x1, y1, fill=fill, outline=outline, width=2 if outline else 0, tags=(tag, "booking"))
            summary_lines = [booking["customer_name"]]
            if slot_span >= 2:
                summary_lines.append(f"{booking['start_time']} - {booking['end_time']}")
            else:
                summary_lines.append(booking["service"])
            if slot_span >= 3:
                summary_lines.append(booking["service"])
            center_y = (y0 + y1) / 2
            line_gap = 14
            start_y = center_y - ((len(summary_lines) - 1) * line_gap / 2)
            for idx, line in enumerate(summary_lines):
                font = ("Arial", 10, "bold") if idx == 0 else ("Arial", 9)
                text_fill = "white" if idx == 0 else "#e5e7eb"
                canvas.create_text(x0 + 10, start_y + idx * line_gap, text=line, fill=text_fill, font=font, anchor="w", tags=(tag, "booking"))

        if today_line_y is not None and today_line_x1 is not None:
            marker_x0 = max(self.TIME_COL_W + 8, today_line_x1 - 76)
            marker_x1 = today_line_x1 - 10
            canvas.create_line(marker_x0, today_line_y, marker_x1, today_line_y, fill="#f59e0b", width=1)
            canvas.create_oval(marker_x1 - 4, today_line_y - 4, marker_x1 + 4, today_line_y + 4, fill="#f59e0b", outline="")
            canvas.create_text(marker_x1 - 10, today_line_y - 10, text="Now", fill="#f59e0b", font=("Arial", 8, "bold"), anchor="e")

    def _slot_payload_from_coords(self, x, y):
        visible_staff = self.visible_staff_names or self.staff_names or ["General"]
        if y <= self.HEADER_H or x <= self.TIME_COL_W:
            return None
        available_width = max(self.canvas.winfo_width() - self.TIME_COL_W - 24, 0)
        dynamic_col_w = max(self.STAFF_COL_W, int(available_width / max(1, len(visible_staff)))) if available_width else self.STAFF_COL_W
        staff_index = int((x - self.TIME_COL_W) // dynamic_col_w)
        if staff_index < 0 or staff_index >= len(visible_staff):
            return None
        slot_index = int((y - self.HEADER_H) // self.SLOT_H)
        minute_total = self.START_HOUR * 60 + slot_index * 30
        if minute_total < self.START_HOUR * 60 or minute_total >= self.END_HOUR * 60:
            return None
        start_time = _slot_label(minute_total).strftime("%H:%M")
        end_time = (_slot_label(minute_total) + timedelta(minutes=30)).strftime("%H:%M")
        return {
            "date": _to_storage_date(self.selected_date.get().strip()),
            "staff": visible_staff[staff_index],
            "start_time": start_time,
            "end_time": end_time,
            "status": "booked",
        }

    def _booking_id_from_event(self, event):
        tags = self.canvas.gettags("current")
        for tag in tags:
            if tag.startswith("booking:"):
                try:
                    return int(tag.split(":", 1)[1])
                except Exception:
                    return None
        return None

    def _on_canvas_single_click(self, event):
        booking_id = self._booking_id_from_event(event)
        if booking_id is not None:
            self._select_booking(booking_id)
            return
        payload = self._slot_payload_from_coords(self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
        if payload:
            self._open_modal(payload)

    def _on_canvas_double_click(self, event):
        booking_id = self._booking_id_from_event(event)
        if booking_id is not None:
            self._edit_booking(booking_id)

    def _find_booking(self, booking_id):
        if booking_id is None:
            return None
        for booking in self.filtered_bookings or self.bookings:
            if int(booking["id"]) == int(booking_id):
                return dict(booking)
        return None

    def _select_booking(self, booking_id):
        self.selected_booking_id = int(booking_id)
        self._populate_day_list()
        self._refresh_selected_details()
        self._draw_calendar()

    def _edit_booking(self, booking_id):
        booking = self._find_booking(booking_id)
        if booking:
            self.selected_booking_id = int(booking_id)
            self._refresh_selected_details()
            self._open_modal(booking)

    def _edit_selected(self):
        if self.selected_booking_id is None:
            messagebox.showinfo("Booking", "Select a booking first.", parent=self)
            return
        self._edit_booking(self.selected_booking_id)

    def _delete_selected(self):
        if self.selected_booking_id is None:
            messagebox.showinfo("Booking", "Select a booking first.", parent=self)
            return
        if not messagebox.askyesno("Delete Booking", "Delete this booking?", parent=self):
            return
        self._delete_booking(self.selected_booking_id)

    def _convert_selected(self):
        booking = self._find_booking(self.selected_booking_id)
        if not booking:
            messagebox.showinfo("Booking", "Select a booking first.", parent=self)
            return
        self._convert_to_bill(booking)

    def _open_modal(self, booking):
        BookingModal(self, booking, self.staff_names, self._save_booking, self._delete_booking, self._convert_to_bill, self._send_booking_reminder)

    def _save_booking(self, payload, booking_id=None):
        save_booking(payload, booking_id=booking_id)
        if booking_id:
            self.selected_booking_id = int(booking_id)
        else:
            latest = list_bookings(payload["date"])
            for booking in reversed(latest):
                if booking["customer_name"] == payload["customer_name"] and booking["phone"] == payload["phone"] and booking["staff"] == payload["staff"] and booking["start_time"] == payload["start_time"]:
                    self.selected_booking_id = int(booking["id"])
                    break
        self.reload()

    def _delete_booking(self, booking_id):
        delete_booking(booking_id)
        if self.selected_booking_id is not None and int(self.selected_booking_id) == int(booking_id):
            self.selected_booking_id = None
        self.reload()

    def _convert_to_bill(self, booking):
        try:
            if hasattr(self.app, "_ensure_frame"):
                self.app._ensure_frame("billing")
            self.app.switch_to("billing")
            def _do_prefill():
                billing = getattr(self.app, "billing_frame", None)
                if billing and hasattr(billing, "prefill_from_booking"):
                    billing.prefill_from_booking(booking)
                else:
                    messagebox.showwarning("Billing", "Billing module is not ready yet. Open Billing once and try again.", parent=self)
            self.after(120, _do_prefill)
        except Exception as exc:
            raise RuntimeError(f"Could not open Billing: {exc}") from exc

    def _send_booking_reminder(self, booking):
        try:
            if hasattr(self.app, "_ensure_frame"):
                self.app._ensure_frame("whatsapp_bulk")
            self.app.switch_to("whatsapp_bulk")
            def _prefill():
                frame = self.app.frames.get("whatsapp_bulk")
                if frame and hasattr(frame, "prefill_booking_reminder"):
                    frame.prefill_booking_reminder(booking)
                else:
                    messagebox.showinfo("Reminder", "WhatsApp module is open. Select the customer and send a reminder.", parent=self)
            self.after(120, _prefill)
        except Exception as exc:
            raise RuntimeError(f"Could not open WhatsApp: {exc}") from exc

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_shift_mousewheel(self, event):
        self.canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")
