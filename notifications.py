"""
notifications.py  -  BOBY'S Salon : Smart notification popup system
Checks birthdays, low stock, today's appointments on app start.
"""
import tkinter as tk
from datetime import date
from utils import (C, load_json, F_CUSTOMERS, F_INVENTORY,
                   F_APPOINTMENTS, today_str)
from ui_theme import ModernButton
from ui_responsive import fit_toplevel, make_scrollable
from branding import get_company_name
from src.blite_v6.app.window_lifecycle import hide_while_building, reveal_when_ready


def get_all_notifications() -> list:
    """Returns notifications filtered by user preferences."""
    from salon_settings import get_settings
    cfg = get_settings()
    show_bday = cfg.get("notif_birthday", True)
    show_stock = cfg.get("notif_low_stock", True)
    show_appts = cfg.get("notif_appointments", True)

    notes = _get_all_raw()
    return [n for n in notes if (
        (n["type"] == "birthday" and show_bday) or
        (n["type"] in ("low_stock", "out_of_stock") and show_stock) or
        (n["type"] == "appointments" and show_appts)
    )]


def _get_all_raw() -> list:
    """Returns list of notification dicts sorted by priority."""
    notes = []

    customers = load_json(F_CUSTOMERS, {})
    today_md = date.today().strftime("-%m-%d")
    for ph, customer in customers.items():
        bd = customer.get("birthday", "")
        if bd and bd.endswith(today_md):
            notes.append({
                "type": "birthday",
                "icon": "Bday",
                "title": "Birthday Today!",
                "message": f"{customer.get('name', '')}  |  Phone {ph}",
                "color": C["gold"],
                "phone": ph,
                "name": customer.get("name", ""),
            })

    inv = load_json(F_INVENTORY, {})
    for name, item in inv.items():
        qty = item.get("qty", 0)
        mins = item.get("min_stock", 5)
        if qty == 0:
            notes.append({
                "type": "out_of_stock",
                "icon": "Out",
                "title": "Out of Stock!",
                "message": f"{name}  (0 {item.get('unit', 'pcs')} remaining)",
                "color": C["red"],
            })
        elif qty <= mins:
            notes.append({
                "type": "low_stock",
                "icon": "Low",
                "title": "Low Stock",
                "message": f"{name}  ({qty} {item.get('unit', 'pcs')} left - min: {mins})",
                "color": C["orange"],
            })

    appts = load_json(F_APPOINTMENTS, [])
    td = today_str()
    today_appts = [a for a in appts
                   if a.get("date", "") == td
                   and a.get("status", "") == "Scheduled"]
    if today_appts:
        notes.append({
            "type": "appointments",
            "icon": "Appt",
            "title": f"{len(today_appts)} Appointment(s) Today",
            "message": "  |  ".join(
                f"{a.get('time', '')} - {a.get('customer', '')}"
                for a in sorted(today_appts, key=lambda x: x.get("time", ""))[:4]
            ),
            "color": C["blue"],
        })

    return notes


class NotificationPopup:
    """Shows a non-blocking notification popup on app start."""

    def __init__(self, parent, notes=None):
        notes = list(notes) if notes is not None else get_all_notifications()
        if not notes:
            return

        win = tk.Toplevel(parent)
        hide_while_building(win)
        win.title("Notifications")
        win.configure(bg=C["bg"])
        win.attributes("-topmost", True)
        fit_toplevel(win, 540, 480,
                     min_width=420, min_height=320,
                     resizable=True, anchor="topright",
                     top_offset=40, right_offset=30)

        hdr = tk.Frame(win, bg=C["card"], pady=10)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text=f"Notifications ({len(notes)})",
                 font=("Arial", 13, "bold"),
                 bg=C["card"], fg=C["text"]).pack(side=tk.LEFT, padx=16)
        ModernButton(hdr, text="Close",
                     command=win.destroy,
                     color=C["red"], hover_color="#c0392b",
                     width=90, height=30, radius=8,
                     font=("Arial", 10, "bold")).pack(side=tk.RIGHT, padx=12)

        body, _canvas, _container = make_scrollable(win, bg=C["bg"])

        for note in notes:
            card = tk.Frame(body, bg=note["color"], padx=14, pady=10)
            card.pack(fill=tk.X, padx=12, pady=5)

            title_row = tk.Frame(card, bg=note["color"])
            title_row.pack(fill=tk.X)
            tk.Label(title_row,
                     text=f"{note['icon']}  {note['title']}",
                     font=("Arial", 11, "bold"),
                     bg=note["color"], fg="white").pack(side=tk.LEFT)

            tk.Label(card, text=note["message"],
                     font=("Arial", 11),
                     bg=note["color"], fg="white",
                     wraplength=460, justify="left").pack(anchor="w", pady=(4, 0))

            if note.get("type") == "birthday" and note.get("phone"):
                ModernButton(card, text="Send Birthday WhatsApp",
                             command=lambda ph=note["phone"], nm=note["name"]: _wa_birthday(ph, nm),
                             color="#25d366", hover_color="#1a9e4a",
                             width=220, height=30, radius=8,
                             font=("Arial", 10, "bold")).pack(anchor="w", pady=(6, 0))

        ModernButton(win, text="Dismiss All",
                     command=win.destroy,
                     color=C["sidebar"], hover_color="#c0392b",
                     width=300, height=36, radius=8,
                     font=("Arial", 11, "bold")).pack(fill=tk.X, padx=12, pady=8)
        reveal_when_ready(win)


def _wa_birthday(phone: str, name: str):
    try:
        import pywhatkit as kit
        salon_name = get_company_name()
        msg = (f"Happy Birthday {name}!\n\n"
               f"Wishing you a beautiful day!\n"
               f"Come visit {salon_name} for a special birthday treat!\n"
               f"\n- Team {salon_name}")
        try:
            from salon_settings import get_settings as _gs
            country_code = _gs().get("country_code", "91")
        except Exception:
            country_code = "91"
        kit.sendwhatmsg_instantly(f"+{country_code}{phone}", msg,
                                  wait_time=25, tab_close=True)
    except Exception as e:
        from tkinter import messagebox
        messagebox.showerror("WhatsApp Error", str(e))
