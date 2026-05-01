"""
utils.py  –  BOBY'S Salon : Shared helpers, theme, data paths
FIXES:
  - apply_ttk_style: use tkinter._default_root instead of style.master (Bug 8)
  - All constants, paths, and helpers in one place
  - Fix R6a: Centralized logging system — app_log() writes to app_debug.log
  - Fix R6b: load_json() — logs corrupt file path + auto-backup before fail
  - Fix R6c: save_json() — logs save failures with path details
  - Fix R6d: build_item_codes() — logs errors via app_log
  - Fix R6e: search_items() — generator-based filtering for performance
  - Fix R6f: validate_phone() — centralized 10-digit regex validation
  - Fix R6g: validate_date() — centralized YYYY-MM-DD format validation
  - Fix M2a: load_json() — SQLite primary via db.db_load(), JSON fallback kept
  - Fix M2b: save_json() — SQLite primary via db.db_save(), JSON backup kept
  - Fix M2c: _apply_combobox_option_add() stub added (missing function guard)
"""
import os, sys, json, shutil, hashlib, re, logging, threading
from datetime import datetime
from auth_security import hash_password
from branding import get_appdata_dir_name, get_redeem_prefix, get_runtime_app_slug


def resource_path(rel: str) -> str:
    try:    base = sys._MEIPASS          # type: ignore
    except: base = os.path.abspath(".")
    return os.path.join(base, rel)


def _init_dirs() -> str:
    base = os.getenv("APPDATA") or os.path.expanduser("~")
    root = os.path.join(base, get_appdata_dir_name())
    for sub in ["", "Bills", "Backups", "Trash"]:
        path = os.path.join(root, sub) if sub else root
        if os.path.isdir(path):
            continue
        if os.path.exists(path):
            raise RuntimeError(f"Required data directory path is not a folder: {path}")
        try:
            os.makedirs(path, exist_ok=True)
        except FileExistsError:
            if os.path.isdir(path):
                continue
            raise RuntimeError(f"Required data directory path is not a folder: {path}") from None
    return root


DATA_DIR  = _init_dirs()
BILLS_DIR = os.path.join(DATA_DIR, "Bills")
TRASH_DIR = os.path.join(DATA_DIR, "Trash")

F_SERVICES    = os.path.join(DATA_DIR, "services_db.json")
F_CUSTOMERS   = os.path.join(DATA_DIR, "customers.json")
F_EXPENSES    = os.path.join(DATA_DIR, "expenses.json")
F_APPOINTMENTS= os.path.join(DATA_DIR, "appointments.json")
F_STAFF       = os.path.join(DATA_DIR, "staff.json")
F_INVENTORY   = os.path.join(DATA_DIR, "inventory.json")
F_USERS       = os.path.join(DATA_DIR, "users.json")
F_OFFERS      = os.path.join(DATA_DIR, "offers.json")
F_REDEEM      = os.path.join(DATA_DIR, "redeem_codes.json")
F_MEMBERSHIPS = os.path.join(DATA_DIR, "memberships.json")
F_SETTINGS    = os.path.join(DATA_DIR, "salon_settings.json")
F_REPORT      = os.path.join(DATA_DIR, "sales_report.csv")
F_INVOICE     = os.path.join(DATA_DIR, "invoice_counter.json")
F_LOG         = os.path.join(DATA_DIR, "app_debug.log")

_INVOICE_LOCK = threading.Lock()


# ─────────────────────────────────────────────────────────
#  CENTRALIZED LOGGING  (Fix R6a)
# ─────────────────────────────────────────────────────────

def _setup_logger() -> logging.Logger:
    """Configure rotating file logger. Silent on failure."""
    logger = logging.getLogger(get_runtime_app_slug())
    if logger.handlers:
        return logger   # already configured
    try:
        from logging.handlers import RotatingFileHandler
        handler = RotatingFileHandler(
            F_LOG,
            maxBytes   = 1 * 1024 * 1024,  # 1 MB max
            backupCount= 2,                  # keep 2 old logs
            encoding   = "utf-8",
        )
        handler.setFormatter(logging.Formatter(
            "%(asctime)s  [%(levelname)s]  %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)
    except Exception:
        pass
    return logger

_logger = _setup_logger()


def app_log(msg: str, level: str = "error") -> None:
    """
    Write a message to app_debug.log.
    level: "debug" | "info" | "warning" | "error"
    Usage:  app_log(f"[module] {e}")
    Silent — never raises, never blocks the UI.
    """
    try:
        fn = getattr(_logger, level.lower(), _logger.error)
        fn(msg)
    except Exception:
        pass


C = {
    "bg":      "#1a1a2e",
    "card":    "#16213e",
    "sidebar": "#0f3460",
    "input":   "#2d2d44",
    "accent":  "#ff79c6",
    "teal":    "#16a085",
    "blue":    "#2980b9",
    "purple":  "#8e44ad",
    "red":     "#e94560",
    "green":   "#27ae60",
    "lime":    "#50fa7b",
    "orange":  "#e67e22",
    "gold":    "#f39c12",
    "text":    "#e8e8e8",
    "muted":   "#94a3b8",
    "white":   "#ffffff",
    "dark2":   "#2c2c54",
}


def _normalize_json_payload(path: str, data, default):
    if default is None:
        return data
    try:
        expected_type = type(default)
        if isinstance(default, (dict, list)) and not isinstance(data, expected_type):
            app_log(
                f"[load_json] Type mismatch for {path}: expected "
                f"{expected_type.__name__}, got {type(data).__name__}. Using default.",
                "warning",
            )
            return default
    except Exception:
        pass
    return data


def load_json(path: str, default=None):
    """
    Fix M2a: SQLite primary, JSON fallback — transparent dual-mode.
    1. Try db.db_load() → reads from SQLite kv_store (fast)
    2. If db unavailable, read JSON file directly (original behaviour)
    3. Log + auto-backup corrupt JSON files (Fix R6b preserved)
    """
    if default is None:
        default = {}
    # ── SQLite primary (M2a) ──────────────────────────────
    try:
        from db import db_load
        return _normalize_json_payload(path, db_load(path, default), default)
    except ImportError:
        pass   # db.py not available — fall through to JSON
    except Exception as e:
        app_log(f"[load_json] db_load error for {path}: {e}")
    # ── JSON fallback (original R6b behaviour) ────────────
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return _normalize_json_payload(path, json.load(f), default)
    except json.JSONDecodeError as e:
        app_log(f"[load_json] Corrupt JSON at {path}: {e}")
        try:
            backup = path + ".corrupt"
            shutil.copy2(path, backup)
            app_log(f"[load_json] Corrupt file backed up to {backup}")
        except Exception:
            pass
    except Exception as e:
        app_log(f"[load_json] Error reading {path}: {e}")
    return default


def save_json(path: str, data) -> bool:
    """
    Fix M2b: SQLite primary + JSON backup — transparent dual-mode.
    1. Try db.db_save() → writes SQLite kv_store + JSON backup atomically
    2. If db unavailable, write JSON file directly (original behaviour)
    Fix R6c: logs save failures with path details (preserved).
    """
    # ── SQLite primary (M2b) ──────────────────────────────
    try:
        from db import db_save
        return db_save(path, data)
    except ImportError:
        pass   # db.py not available — fall through to JSON
    except Exception as e:
        app_log(f"[save_json] db_save error for {path}: {e}")
    # ── JSON fallback (original R6c behaviour) ────────────
    try:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        if os.path.exists(path):
            os.replace(tmp, path)
        else:
            os.rename(tmp, path)
        return True
    except Exception as e:
        app_log(f"[save_json] Failed to save {path}: {e}")
        try:
            if os.path.exists(path + ".tmp"):
                os.remove(path + ".tmp")
        except Exception:
            pass
        return False


def safe_float(v, default=0.0):
    try:   return float(v)
    except: return default


def safe_int(v, default=0):
    try:   return int(v)
    except: return default


def sanitize_filename(name: str) -> str:
    s = "".join(c for c in name.strip()
                if c.isalnum() or c in " _-").strip()
    return s or "Guest"


def center_window(win, w: int, h: int):
    """Center window on screen, fitting within screen bounds."""
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    w  = min(w, sw - 40)
    h  = min(h, sh - 80)
    x  = (sw // 2) - (w // 2)
    y  = max(30, (sh // 2) - (h // 2))
    win.geometry(f"{w}x{h}+{x}+{y}")


def popup_window(win, w: int, h: int, title: str = "",
                 resizable: bool = True):
    try:
        owner = win.master.winfo_toplevel() if getattr(win, "master", None) else None
        if owner and owner != win:
            win.transient(owner)
    except Exception:
        pass
    try:
        from ui_responsive import fit_toplevel
        fit_toplevel(win, w, h,
                     min_width=420, min_height=320,
                     resizable=resizable, anchor="center")
        if title:
            win.title(title)
        return
    except Exception:
        pass
    """
    Smart popup: scales to screen, centers, sets sensible min size.
    Always fits within screen — no more tiny fixed-size popups.
    """
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()

    # Scale requested size to screen (90% max usable area)
    max_w = int(sw * 0.90)
    max_h = int(sh * 0.88)

    # If requested is bigger than screen → shrink
    w = min(w, max_w)
    h = min(h, max_h)

    # If screen is small (laptop) → scale down proportionally
    if sw < 1366 or sh < 768:
        scale = min(sw / 1366, sh / 768)
        w = max(int(w * scale), 420)
        h = max(int(h * scale), 320)
        w = min(w, max_w)
        h = min(h, max_h)

    # Center on screen
    x = (sw - w) // 2
    y = max(30, (sh - h) // 2)

    win.geometry(f"{w}x{h}+{x}+{y}")
    win.minsize(min(w, 420), min(h, 320))

    if resizable:
        win.resizable(True, True)
    if title:
        win.title(title)


def hash_pw(pw: str) -> str:
    try:
        return hash_password(pw)
    except Exception:
        return hashlib.sha256(pw.encode()).hexdigest()


def next_invoice() -> str:
    """
    Professional date-based invoice numbers.
    Format: INV-YYYYMM-NNNNN  (counter resets each month)
    """
    try:
        with _INVOICE_LOCK:
            now     = datetime.now()
            ym      = now.strftime("%Y%m")
            data    = load_json(F_INVOICE, {"last": 0, "month": ""})
            last_mo = data.get("month", "")
            num     = int(data.get("last", 0)) + 1
            if last_mo != ym:
                num = 1
            save_json(F_INVOICE, {"last": num, "month": ym})
            return f"INV-{ym}-{num:05d}"
    except Exception as e:
        app_log(f"[next_invoice] {e}")
        return f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}"


def init_services_db():
    """Copy bundled services_db.json on first run."""
    if not os.path.exists(F_SERVICES):
        for src in [resource_path("services_db.json"),
                    os.path.join(os.path.dirname(
                        os.path.abspath(__file__)), "services_db.json")]:
            if os.path.exists(src):
                try:
                    shutil.copy(src, F_SERVICES)
                except Exception as e:
                    app_log(f"[init_services_db] {e}")
                break


def fmt_currency(v) -> str:
    return f"\u20b9{safe_float(v):,.2f}"


def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def month_str() -> str:
    return datetime.now().strftime("%Y-%m")


def attendance_get_day_record(att_list, date_str: str):
    """Return the attendance record for a given day, if present."""
    for rec in att_list or []:
        if isinstance(rec, dict) and rec.get("date", "") == date_str:
            return rec
    return None


def attendance_get_sessions(day_rec: dict) -> list:
    """
    Backward-compatible session reader.
    Supports both:
    - legacy: in_time/out_time
    - new: sessions=[{in_time, out_time}, ...]
    """
    if not isinstance(day_rec, dict):
        return []

    sessions = day_rec.get("sessions", [])
    if isinstance(sessions, list) and sessions:
        cleaned = []
        for sess in sessions:
            if not isinstance(sess, dict):
                continue
            cleaned.append({
                "in_time": str(sess.get("in_time", "") or ""),
                "out_time": str(sess.get("out_time", "") or ""),
            })
        if cleaned:
            return cleaned

    in_time = str(day_rec.get("in_time", "") or "")
    out_time = str(day_rec.get("out_time", "") or "")
    if in_time or out_time:
        return [{"in_time": in_time, "out_time": out_time}]
    return []


def attendance_sync_legacy_fields(day_rec: dict) -> dict:
    """
    Keep legacy in_time/out_time fields in sync with the sessions model.
    This preserves old UI/report code while allowing gradual rollout.
    """
    if not isinstance(day_rec, dict):
        return {}

    sessions = attendance_get_sessions(day_rec)
    if sessions:
        day_rec["sessions"] = sessions
        day_rec["in_time"] = sessions[0].get("in_time", "")
        last_out = ""
        for sess in sessions:
            if sess.get("out_time"):
                last_out = sess.get("out_time", "")
        day_rec["out_time"] = last_out
    else:
        day_rec["sessions"] = []
        day_rec["in_time"] = str(day_rec.get("in_time", "") or "")
        day_rec["out_time"] = str(day_rec.get("out_time", "") or "")
    return day_rec


def attendance_latest_session(day_rec: dict):
    sessions = attendance_get_sessions(day_rec)
    return sessions[-1] if sessions else None


def attendance_open_session(day_rec: dict):
    for sess in reversed(attendance_get_sessions(day_rec)):
        if sess.get("in_time") and not sess.get("out_time"):
            return sess
    return None


def init_sample_data():
    """Initialize sample/default data on first run."""
    import json as _json
    from datetime import date, timedelta

    if not os.path.exists(F_SERVICES):
        for src_path in [
            resource_path("services_db.json"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "services_db.json"),
        ]:
            if os.path.exists(src_path):
                try:
                    shutil.copy2(src_path, F_SERVICES)
                except Exception as e:
                    app_log(f"[init_sample_data services copy] {e}")
                break

    if not os.path.exists(F_INVENTORY):
        try:
            db_path = F_SERVICES if os.path.exists(F_SERVICES) else \
                os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "services_db.json")
            if os.path.exists(db_path):
                with open(db_path, "r", encoding="utf-8") as f:
                    db = _json.load(f)
                inventory = {}
                for cat, items in db.get("Products", {}).items():
                    for iname, price in items.items():
                        sell = float(price)
                        inventory[iname] = {
                            "category":   cat,
                            "qty":        10,
                            "unit":       "pcs",
                            "min_stock":  3,
                            "cost":       round(sell * 0.6, 2),
                            "sell_price": sell,
                            "updated":    date.today().strftime("%Y-%m-%d"),
                        }
                if inventory:
                    save_json(F_INVENTORY, inventory)
        except Exception:
            pass

    if not os.path.exists(F_OFFERS):
        today = date.today()
        yr    = date(today.year, 12, 31).strftime("%Y-%m-%d")
        td    = today.strftime("%Y-%m-%d")
        nowt  = today.strftime("%Y-%m-%d %H:%M")
        save_json(F_OFFERS, [
            {"name": "Welcome Discount", "type": "percentage", "value": 10.0,
             "service_name": "", "coupon_code": "WELCOME10",
             "valid_from": td, "valid_to": yr,
             "description": "10% off for new customers", "active": True, "created": nowt},
            {"name": "Flat Rs.100 Off", "type": "flat", "value": 100.0,
             "service_name": "", "coupon_code": "SAVE100",
             "valid_from": td, "valid_to": yr,
             "description": "Rs.100 off on any bill", "active": True, "created": nowt},
            {"name": "Birthday Month 25%", "type": "percentage", "value": 25.0,
             "service_name": "", "coupon_code": "BDAY25",
             "valid_from": td, "valid_to": yr,
             "description": "25% off in birthday month", "active": True, "created": nowt},
        ])

    F_PKG = os.path.join(DATA_DIR, "pkg_templates.json")
    if not os.path.exists(F_PKG):
        save_json(F_PKG, [
            {"name": "Silver Package (1 Month)",    "price": 1500,
             "duration_days": 30,  "discount_pct": 10, "wallet": 0,
             "description": "10% off all services for 1 month"},
            {"name": "Gold Package (3 Months)",     "price": 4000,
             "duration_days": 90,  "discount_pct": 15, "wallet": 0,
             "description": "15% off all services for 3 months"},
            {"name": "Platinum Package (6 Months)", "price": 7000,
             "duration_days": 180, "discount_pct": 20, "wallet": 0,
             "description": "20% off all services for 6 months"},
            {"name": "Diamond Package (1 Year)",    "price": 12000,
             "duration_days": 365, "discount_pct": 25, "wallet": 0,
             "description": "25% off all services for 1 full year"},
            {"name": "Prepaid Wallet Rs.2000",      "price": 2000,
             "duration_days": 365, "discount_pct": 0,  "wallet": 2200,
             "description": "Pay Rs.2000 get Rs.2200 wallet balance"},
            {"name": "VIP Annual Package",          "price": 15000,
             "duration_days": 365, "discount_pct": 30, "wallet": 1000,
             "description": "30% off + Rs.1000 wallet - full year VIP"},
        ])

    if not os.path.exists(F_REDEEM):
        today = date.today()
        exp1y = (today + timedelta(days=365)).strftime("%Y-%m-%d")
        nowt  = today.strftime("%Y-%m-%d %H:%M")
        redeem_prefix = get_redeem_prefix()
        save_json(F_REDEEM, {
            f"{redeem_prefix}-GIFT1": {
                "discount_type": "flat", "value": 200.0, "phone": "",
                "name": "Gift Code", "expiry": exp1y,
                "note": "Gift voucher Rs.200 off", "used": False,
                "used_on": "", "used_invoice": "", "created": nowt,
            },
            f"{redeem_prefix}-VIP01": {
                "discount_type": "percentage", "value": 20.0, "phone": "",
                "name": "VIP Code", "expiry": exp1y,
                "note": "VIP 20% off", "used": False,
                "used_on": "", "used_invoice": "", "created": nowt,
            },
        })


# ─────────────────────────────────────────────────────────
#  COMBOBOX DARK MODE HELPER  (Fix M2c)
# ─────────────────────────────────────────────────────────

def _apply_combobox_option_add(root) -> None:
    """
    Apply dark-mode colours to all Combobox dropdown lists.
    Called from apply_ttk_style() — safe to call multiple times.
    Fix M2c: was referenced but never defined, causing silent AttributeError.
    """
    try:
        root.option_add("*TCombobox*Listbox.background",       C["card"])
        root.option_add("*TCombobox*Listbox.foreground",       C["text"])
        root.option_add("*TCombobox*Listbox.selectBackground", C["teal"])
        root.option_add("*TCombobox*Listbox.selectForeground", "white")
        root.option_add("*TCombobox*Listbox.font",             "Arial 11")
    except Exception as e:
        app_log(f"[_apply_combobox_option_add] {e}")


# ─────────────────────────────────────────────────────────
#  GLOBAL TTK STYLE — call once at app start
# ─────────────────────────────────────────────────────────

def apply_ttk_style(ui_scale: float = 1.0):
    """
    Apply global ttk styles.
    FIX (Bug 8): uses tkinter._default_root instead of style.master
    which can be None on some Tk versions.
    """
    try:
        import tkinter as _tk
        from tkinter import ttk
        style = ttk.Style()

        tab_font_size = max(10, int(12 * ui_scale))
        tab_pad_x     = max(8,  int(12 * ui_scale))
        tab_pad_y     = max(5,  int(7  * ui_scale))

        style.configure("TNotebook", background=C["bg"], borderwidth=0)
        style.configure("TNotebook.Tab",
                        font=("Arial", tab_font_size, "bold"),
                        padding=[tab_pad_x, tab_pad_y],
                        background=C["sidebar"],
                        foreground=C["muted"])
        style.map("TNotebook.Tab",
                  background=[("selected", C["bg"]),
                               ("active",   C["card"])],
                  foreground=[("selected", C["accent"]),
                               ("active",   C["text"])])

        style.configure("Vertical.TScrollbar",
                        background=C["sidebar"],
                        troughcolor=C["bg"],
                        borderwidth=0,
                        arrowcolor=C["muted"])

        tv_font_size = max(10, int(11 * ui_scale))
        tv_row_h     = max(22, int(26 * ui_scale))
        style.configure("Treeview",
                        background=C["card"],
                        foreground=C["text"],
                        fieldbackground=C["card"],
                        rowheight=tv_row_h,
                        font=("Arial", tv_font_size))
        style.configure("Treeview.Heading",
                        background=C["sidebar"],
                        foreground=C["accent"],
                        font=("Arial", tv_font_size, "bold"))
        style.map("Treeview",
                  background=[("selected", C["teal"])],
                  foreground=[("selected", "white")])

        # FIX (Bug 8): use _default_root, not style.master
        try:
            _root = _tk._default_root
            if _root is not None:
                _apply_combobox_option_add(_root)
        except Exception:
            pass

    except Exception as e:
        app_log(f"[apply_ttk_style] {e}")



# ─────────────────────────────────────────────────────────
#  ITEM CODE SYSTEM
# ─────────────────────────────────────────────────────────

_SVC_PREFIXES = {
    "Treatments":          "T",
    "Waxing":              "W",
    "Head Massage":        "HM",
    "Rica Wax (Flavor)":   "RW",
    "Rica Brazilian":      "RB",
    "Bridal":              "BR",
    "Nail Art":            "NA",
    "Threading":           "TH",
    "Hair Ironing":        "HI",
    "De Tan":              "DT",
    "Bleaching":           "BL",
    "Clean Up":            "CU",
    "Hair Cut":            "HC",
    "Hair Colouring":      "HCL",
    "Hair Spa":            "HS",
    "Pedicure & Manicure": "PM",
    "Facial":              "F",
}

_PRD_PREFIXES = {
    "Hair Care":                        "PC",
    "Hair Styling Tools & Accessories": "PT",
    "Skin Care":                        "PS",
    "Body Care":                        "PB",
    "Waxing Products":                  "PW",
    "Threading & Bleach":               "PTB",
    "Facial Kits & Professional":       "PF",
    "Makeup":                           "PMK",
    "Nail Products":                    "PN",
    "Manicure & Pedicure":              "PMP",
    "Salon Consumables":                "PSC",
}

_ITEM_CODE_CACHE = {}
_CODE_BUILT      = False


def build_item_codes(force=False):
    """Build code→item mapping from services_db.json. Cached after first call."""
    global _ITEM_CODE_CACHE, _CODE_BUILT
    if _CODE_BUILT and not force:
        return _ITEM_CODE_CACHE

    _ITEM_CODE_CACHE.clear()
    try:
        db = load_json(F_SERVICES, {})

        for cat, items in db.get("Services", {}).items():
            prefix = _SVC_PREFIXES.get(cat, cat[:2].upper())
            for i, (name, price) in enumerate(items.items(), 1):
                code = f"{prefix}{i:03d}"
                _ITEM_CODE_CACHE[code] = {
                    "code":     code,
                    "name":     name,
                    "category": cat,
                    "price":    float(price),
                    "type":     "service",
                }

        for cat, items in db.get("Products", {}).items():
            prefix = _PRD_PREFIXES.get(cat, "P" + cat[:2].upper())
            for i, (name, price) in enumerate(items.items(), 1):
                code = f"{prefix}{i:03d}"
                _ITEM_CODE_CACHE[code] = {
                    "code":     code,
                    "name":     name,
                    "category": cat,
                    "price":    float(price),
                    "type":     "product",
                }
    except Exception as e:
        app_log(f"[build_item_codes] {e}")

    _CODE_BUILT = True
    return _ITEM_CODE_CACHE


def search_items(query: str, mode: str = "all", limit: int = 14) -> list:
    """
    Smart search — matches name, code, category.
    mode: "all" | "services" | "products"
    Returns [] for empty query (use build_item_codes() for show-all).
    Fix R6e: generator-based filtering — no intermediate list for large datasets.
    """
    codes = build_item_codes()
    q     = query.strip().lower()
    if not q:
        return []

    def _score(code: str, item: dict) -> int:
        code_l = code.lower()
        name_l = item["name"].lower()
        cat_l  = item["category"].lower()
        if   code_l == q:              return 100
        elif code_l.startswith(q):     return 90
        elif name_l == q:              return 80
        elif name_l.startswith(q):     return 70
        elif q in code_l:              return 60
        elif q in name_l:              return 50
        elif q in cat_l:               return 30
        return 0

    # Generator: filter + score without building full list first
    scored = (
        ({**item, "score": s})
        for code, item in codes.items()
        if (mode == "all" or item["type"] == ("service" if mode == "services" else "product"))
        for s in (_score(code, item),)
        if s > 0
    )

    results = sorted(scored, key=lambda x: (-x["score"], x["name"]))
    return results[:limit]


def open_file_cross_platform(path: str):
    """Open a file with the default application. Windows + Linux + Mac safe."""
    import subprocess
    try:
        if sys.platform == "win32":
            os.startfile(path)          # type: ignore
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as e:
        app_log(f"[open_file] {e}")


def open_print_text_fallback(text: str, filename: str = "bill_print_preview.txt") -> str:
    """Create a printable text fallback and ask the OS default print handler to print it."""
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", filename).strip("._")
    if not safe_name:
        safe_name = "bill_print_preview.txt"
    if not safe_name.lower().endswith(".txt"):
        safe_name += ".txt"
    path = os.path.join(DATA_DIR, safe_name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text or "")
    try:
        if sys.platform == "win32":
            os.startfile(path, "print")  # type: ignore[attr-defined]
            return path
    except Exception as e:
        app_log(f"[open_print_text_fallback] shell print failed: {e}", "warning")
    open_file_cross_platform(path)
    return path


# ─────────────────────────────────────────────────────────
#  INPUT VALIDATORS  (Fix R6f, R6g)
# ─────────────────────────────────────────────────────────

_RE_PHONE = re.compile(r"^\d{10}$")
_RE_DATE  = re.compile(r"^\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])$")
_RE_DATE_DMY = re.compile(r"^(?:0[1-9]|[12]\d|3[01])-(?:0[1-9]|1[0-2])-\d{4}$")


def validate_phone(phone: str) -> bool:
    """Return True if phone is exactly 10 digits. Fix R6f."""
    return bool(_RE_PHONE.match(phone.strip()))


def validate_date(date_str: str) -> bool:
    """Return True if date_str matches YYYY-MM-DD format. Fix R6g."""
    if not _RE_DATE.match(date_str.strip()):
        return False
    try:
        from datetime import date
        date.fromisoformat(date_str.strip())
        return True
    except ValueError:
        return False  # e.g. 2024-02-30 — invalid day for month
