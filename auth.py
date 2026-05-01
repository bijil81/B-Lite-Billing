"""
auth.py  —  BOBY'S Salon : Login window + user management
"""
import json
import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys
import time
from utils import (C, center_window, load_json, save_json,
                   hash_pw, F_USERS, resource_path,
                   popup_window, app_log,
                   today_str, now_str,
                   attendance_get_day_record,
                   attendance_get_sessions,
                   attendance_sync_legacy_fields,
                   attendance_open_session)
from auth_security import verify_password
from ui_theme import ModernButton
from ui_responsive import make_toplevel_scrollable, get_responsive_metrics, scaled_value, fit_toplevel
from icon_system import get_action_icon
from src.blite_v6.app.window_lifecycle import hide_while_building, reveal_when_ready
from branding import (
    get_branding_icon_path,
    get_branding_logo_path,
    get_login_title,
    get_short_name,
    get_tagline,
    get_window_title,
)
from db import get_db

_LOGIN_FAILED_ATTEMPTS = {}
_LOGIN_MAX_ATTEMPTS = 5
_LOGIN_WINDOW_SECONDS = 10 * 60
_LOGIN_LOCKOUT_SECONDS = 15 * 60


def _ensure_login_lockout_table():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS auth_lockouts (
            username TEXT PRIMARY KEY,
            attempts_json TEXT NOT NULL DEFAULT '[]',
            locked_until REAL NOT NULL DEFAULT 0,
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    return conn


def _read_login_lock_entry(username: str) -> dict:
    key = username.lower().strip()
    if not key:
        return {"attempts": [], "locked_until": 0.0}
    try:
        conn = _ensure_login_lockout_table()
        row = conn.execute(
            "SELECT attempts_json, locked_until FROM auth_lockouts WHERE username = ?",
            (key,),
        ).fetchone()
        if not row:
            return {"attempts": [], "locked_until": 0.0}
        try:
            attempts = [float(ts) for ts in json.loads(row["attempts_json"] or "[]")]
        except Exception:
            attempts = []
        return {
            "attempts": attempts,
            "locked_until": float(row["locked_until"] or 0.0),
        }
    except Exception as e:
        app_log(f"[auth lockout read] {e}")
        return _LOGIN_FAILED_ATTEMPTS.get(key, {"attempts": [], "locked_until": 0.0})


def _write_login_lock_entry(username: str, attempts: list[float], locked_until: float):
    key = username.lower().strip()
    clean = {"attempts": attempts, "locked_until": locked_until}
    _LOGIN_FAILED_ATTEMPTS[key] = clean
    try:
        conn = _ensure_login_lockout_table()
        if attempts or locked_until:
            conn.execute(
                """
                INSERT INTO auth_lockouts(username, attempts_json, locked_until, updated_at)
                VALUES(?, ?, ?, datetime('now'))
                ON CONFLICT(username) DO UPDATE SET
                    attempts_json = excluded.attempts_json,
                    locked_until = excluded.locked_until,
                    updated_at = excluded.updated_at
                """,
                (key, json.dumps(attempts), float(locked_until or 0.0)),
            )
        else:
            conn.execute("DELETE FROM auth_lockouts WHERE username = ?", (key,))
            _LOGIN_FAILED_ATTEMPTS.pop(key, None)
        conn.commit()
    except Exception as e:
        app_log(f"[auth lockout write] {e}")


def _prune_login_failures(username: str):
    key = username.lower().strip()
    entry = _read_login_lock_entry(key)
    now = time.time()
    attempts = [ts for ts in entry.get("attempts", []) if now - ts <= _LOGIN_WINDOW_SECONDS]
    locked_until = float(entry.get("locked_until", 0.0) or 0.0)
    if locked_until and locked_until <= now:
        locked_until = 0.0
    _write_login_lock_entry(key, attempts, locked_until)
    return {"attempts": attempts, "locked_until": locked_until}


def get_login_lock_message(username: str) -> str | None:
    entry = _prune_login_failures(username)
    locked_until = entry.get("locked_until", 0.0)
    if not locked_until:
        return None
    remaining = max(1, int((locked_until - time.time()) // 60) + 1)
    return f"Too many failed attempts. Try again in about {remaining} minute(s)."


def get_login_feedback_state(username: str) -> dict:
    entry = _prune_login_failures(username)
    attempts = list(entry.get("attempts", []))
    locked_until = float(entry.get("locked_until", 0.0) or 0.0)
    locked = bool(locked_until and locked_until > time.time())
    return {
        "attempt_count": len(attempts),
        "remaining_attempts": max(0, _LOGIN_MAX_ATTEMPTS - len(attempts)),
        "locked_until": locked_until,
        "locked": locked,
        "lock_message": get_login_lock_message(username) if locked else None,
    }


def register_login_failure(username: str) -> str:
    key = username.lower().strip()
    entry = _prune_login_failures(key)
    attempts = entry.get("attempts", [])
    attempts.append(time.time())
    if len(attempts) >= _LOGIN_MAX_ATTEMPTS:
        _write_login_lock_entry(key, attempts, time.time() + _LOGIN_LOCKOUT_SECONDS)
        return get_login_lock_message(key) or "Too many failed attempts."
    _write_login_lock_entry(key, attempts, 0.0)
    remaining = max(0, _LOGIN_MAX_ATTEMPTS - len(attempts))
    return f"Invalid username or password. {remaining} attempt(s) left before temporary lock."


def clear_login_failures(username: str):
    _write_login_lock_entry(username, [], 0.0)

# ─────────────────────────────────────────
#  AUTO ATTENDANCE HELPER
# ─────────────────────────────────────────
def auto_mark_attendance(username: str, event: str):
    """
    Called on login/logout to auto-record attendance.
    event = 'login'  â†’ marks Present + opens a session if none is open
    event = 'logout' â†’ closes the current open session
    Staff is matched by username (login name) or display name.
    """
    try:
        from staff import get_staff, save_staff
        staff = get_staff()
        td    = today_str()
        now   = now_str()        # "YYYY-MM-DD HH:MM:SS"
        time_only = now[11:16]   # "HH:MM"

        # Match staff by username or name (case-insensitive)
        target_key = None
        for key, s in staff.items():
            if (key.lower() == username.lower() or
                    s.get("name", "").lower() == username.lower()):
                target_key = key
                break

        if not target_key:
            return  # Not a staff member — owner/admin only, skip

        s = staff[target_key]
        att_list = s.get("attendance", [])

        if event == "login":
            existing = attendance_get_day_record(att_list, td)
            if existing:
                existing["status"] = "Present"
                existing = attendance_sync_legacy_fields(existing)
                if not attendance_open_session(existing):
                    sessions = attendance_get_sessions(existing)
                    sessions.append({
                        "in_time": time_only,
                        "out_time": "",
                    })
                    existing["sessions"] = sessions
                    attendance_sync_legacy_fields(existing)
            else:
                new_day = {
                    "date":     td,
                    "status":   "Present",
                    "sessions": [{
                        "in_time": time_only,
                        "out_time": "",
                    }],
                }
                att_list.append(attendance_sync_legacy_fields(new_day))
            s["attendance"] = att_list
            staff[target_key] = s
            save_staff(staff)

        elif event == "logout":
            existing = attendance_get_day_record(att_list, td)
            if existing and existing.get("status") == "Present":
                existing = attendance_sync_legacy_fields(existing)
                open_session = attendance_open_session(existing)
                if not open_session:
                    return
                open_session["out_time"] = time_only
                attendance_sync_legacy_fields(existing)
                s["attendance"] = att_list
                staff[target_key] = s
                save_staff(staff)

    except Exception as e:
        try:
            from utils import app_log
            app_log(f"[auto_mark_attendance] {e}")
        except Exception:
            pass


# ─────────────────────────────────────────
#  USER HELPERS
# ─────────────────────────────────────────
def get_users() -> dict:
    users = load_json(F_USERS, {})
    if isinstance(users, dict):
        return users
    app_log(f"[auth] invalid users store type: {type(users).__name__}")
    return {}

def _save_users(u: dict) -> bool:
    return save_json(F_USERS, u)


def _users_store_exists() -> bool:
    if os.path.exists(F_USERS):
        return True
    try:
        row = get_db().execute(
            "SELECT 1 FROM kv_store WHERE key = ? LIMIT 1",
            ("users",),
        ).fetchone()
        return bool(row)
    except Exception as e:
        app_log(f"[auth] users store probe failed: {e}")
        return False

def init_default_admin():
    """Create default owner account on first launch.

    C2 FIX: Instead of a well-known password (admin/admin123),
    generate a random password and force the user to set their own
    on the first login via the first-run wizard in main.py.
    The random password is stored so the admin user exists,
    but it is never displayed or used again.
    """
    import secrets, string
    u = get_users()
    if not u and not _users_store_exists():
        # Generate a strong random password that won't be shown to anyone
        random_pwd = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
        u["admin"] = {
            "password": hash_pw(random_pwd),
            "role":     "owner",
            "name":     "Admin",
            "active":   True,
        }
        if not _save_users(u):
            app_log("[auth] default admin bootstrap save failed")


def is_first_run() -> bool:
    """Check if no users exist yet (fresh install with no setup completed)."""
    users = get_users()
    if users:
        return False
    first_run = not _users_store_exists()
    if not first_run:
        app_log("[auth] users store exists but resolved empty; skipping first-run wizard", "warning")
    return first_run


def show_first_run_setup():
    """C2 FIX: First-run wizard forces the user to set up their owner account.

    This replaces the well-known admin/admin123 default credentials.
    On first launch, the user must provide an owner name and password
    (minimum 8 characters) before they can access the system.
    """
    import secrets, string
    from tkinter.simpledialog import askstring

    win = tk.Tk()
    hide_while_building(win)
    win.title("Welcome - First Time Setup")
    win.resizable(False, False)
    win.configure(bg=C["bg"])
    center_window(win, 480, 420)

    try:
        win.iconbitmap(get_branding_icon_path("app"))
    except Exception:
        pass

    tk.Label(win, text="Welcome to " + get_short_name(),
             font=("Arial", 18, "bold"), bg=C["bg"],
             fg=C["accent"]).pack(pady=(30, 8))
    tk.Label(win, text="Let's set up your owner account",
             font=("Arial", 12), bg=C["bg"],
             fg=C["muted"]).pack(pady=(0, 24))

    form = tk.Frame(win, bg=C["bg"], padx=40)
    form.pack(fill=tk.BOTH, expand=True)

    tk.Label(form, text="Owner Name", font=("Arial", 12, "bold"),
             bg=C["bg"], fg=C["text"]).pack(anchor="w")
    name_var = tk.StringVar(value="Admin")
    name_ent = tk.Entry(form, textvariable=name_var,
                        font=("Arial", 12), bg=C["input"], fg=C["text"],
                        bd=0, insertbackground=C["accent"])
    name_ent.pack(fill=tk.X, ipady=8, pady=(4, 14))

    tk.Label(form, text="Username", font=("Arial", 12, "bold"),
             bg=C["bg"], fg=C["text"]).pack(anchor="w")
    user_var = tk.StringVar(value="admin")
    user_ent = tk.Entry(form, textvariable=user_var,
                        font=("Arial", 12), bg=C["input"], fg=C["text"],
                        bd=0, insertbackground=C["accent"])
    user_ent.pack(fill=tk.X, ipady=8, pady=(4, 14))

    tk.Label(form, text="Password (minimum 8 characters)",
             font=("Arial", 12, "bold"), bg=C["bg"], fg=C["text"]).pack(anchor="w")
    pw_var = tk.StringVar()
    pw_ent = tk.Entry(form, textvariable=pw_var, font=("Arial", 12),
                      show="*", bg=C["input"], fg=C["text"],
                      bd=0, insertbackground=C["accent"])
    pw_ent.pack(fill=tk.X, ipady=8, pady=(4, 14))
    pw_ent.focus_set()

    tk.Label(form, text="Tip: Use a strong, memorable password.",
             font=("Arial", 10), bg=C["bg"], fg=C["muted"]).pack(anchor="w")

    error_lbl = tk.Label(form, text="", font=("Arial", 10),
                         bg=C["bg"], fg="red")
    error_lbl.pack(anchor="w", pady=(8, 0))

    result = {"user": None}

    def _setup():
        name = name_var.get().strip() or "Admin"
        username = user_var.get().strip().lower()
        if not username:
            error_lbl.config(text="Username is required.")
            return
        if len(username) < 3:
            error_lbl.config(text="Username must be at least 3 characters.")
            return
        pw = pw_var.get()
        if len(pw) < 8:
            error_lbl.config(text="Password must be at least 8 characters.")
            return
        # Create the user
        u = get_users()
        if username in u:
            error_lbl.config(text="That username already exists.")
            return
        u[username] = {
            "password": hash_pw(pw),
            "role":     "owner",
            "name":     name,
            "active":   True,
        }
        if not _save_users(u):
            error_lbl.config(text="Owner account could not be saved. Check app storage.")
            app_log(f"[auth] first-run owner save failed for {username}")
            return
        result["user"] = {
            "username": username,
            "role":     "owner",
            "name":     name,
        }
        try:
            from salon_settings import get_settings, save_settings
            cfg = get_settings()
            cfg["last_user"] = username
            save_settings(cfg)
        except Exception:
            pass
        messagebox.showinfo("Setup Complete",
            f"Owner account '{username}' created.\n\n"
            f"You can now add staff/users from the Admin panel after login.")
        win.quit()
        win.destroy()

    ModernButton(form, text="Create Account & Continue",
                 command=_setup,
                 width=scaled_value(360, 320, 280), height=scaled_value(44, 40, 34),
                 radius=10,
                 font=("Arial", scaled_value(13, 12, 10), "bold"),
                 ).pack(fill=tk.X, pady=(20, 0))

    win.bind("<Return>", lambda e: _setup())
    reveal_when_ready(win)
    win.mainloop()
    return result["user"]

def verify_login(username: str, password: str):
    key = username.lower().strip()
    users = get_users()
    u = users.get(key)
    if u and u.get("active", True):
        is_valid, should_upgrade = verify_password(password, str(u.get("password", "")))
        if is_valid:
            if should_upgrade:
                try:
                    users[key]["password"] = hash_pw(password)
                    if not _save_users(users):
                        app_log(f"[verify_login] password upgrade save failed for {key}")
                except Exception as e:
                    app_log(f"[verify_login] password upgrade failed for {key}: {e}")
            return {**u, "username": key}
    return None


# ─────────────────────────────────────────
#  LOGIN WINDOW
# ─────────────────────────────────────────
class LoginWindow:
    def __init__(self, on_success=None):
        self.on_success = on_success
        self.logged_in_user = None
        self._responsive = get_responsive_metrics()
        self._login_enabled = True
        self._lockout_after_id = None
        init_default_admin()

        self.win = tk.Tk()
        hide_while_building(self.win)
        self.win.title(get_window_title())
        self.win.resizable(False, False)
        self.win.configure(bg=C["bg"])
        self.win.protocol("WM_DELETE_WINDOW", self._close_window)
        center_window(self.win, 440, 540)

        try:
            self.win.iconbitmap(get_branding_icon_path("app"))
        except Exception as e:
            app_log(f"[login icon] {e}")

        self._build()
        reveal_when_ready(self.win)
        self.win.mainloop()
        if self.logged_in_user and callable(self.on_success):
            self.on_success(self.logged_in_user)

    def _close_window(self):
        if self._lockout_after_id:
            try:
                self.win.after_cancel(self._lockout_after_id)
            except Exception:
                pass
            self._lockout_after_id = None
        self.logged_in_user = None
        try:
            self.win.quit()
        except Exception:
            pass
        try:
            self.win.destroy()
        except Exception:
            pass

    def _build(self):
        # Top brand
        top = tk.Frame(self.win, bg=C["sidebar"], pady=25)
        top.pack(fill=tk.X)

        try:
            from PIL import Image, ImageTk
            img  = Image.open(get_branding_logo_path("main")).convert("RGBA")
            bbox = img.getbbox()
            if bbox: img = img.crop(bbox)
            h = 70; w = int(img.size[0] * h / img.size[1])
            self._logo = ImageTk.PhotoImage(img.resize((w, h)))
            tk.Label(top, image=self._logo, bg=C["sidebar"]).pack()
        except Exception:
            tk.Label(top, text=get_short_name().upper(),
                     font=("Arial", 22, "bold"),
                     bg=C["sidebar"], fg=C["accent"]).pack()
            tk.Label(top, text=get_tagline(),
                     font=("Arial", 12), bg=C["sidebar"],
                     fg=C["muted"]).pack()

        # Form
        f = tk.Frame(self.win, bg=C["bg"], padx=40)
        f.pack(fill=tk.BOTH, expand=True, pady=20)

        tk.Label(f, text=get_login_title(),
                 font=("Arial", 16, "bold"),
                 bg=C["bg"], fg=C["text"]).pack(pady=(8, 3))
        tk.Label(f, text="Sign in to your account",
                 font=("Arial", 12), bg=C["bg"],
                 fg=C["muted"]).pack(pady=(0, 18))

        # Get user list + last user
        from salon_settings import get_settings
        cfg         = get_settings()
        last_user   = cfg.get("last_user", "admin")
        all_users   = list(get_users().keys())
        if not all_users: all_users = ["admin"]

        # Username dropdown
        tk.Label(f, text="Username", font=("Arial", 12, "bold"),
                 bg=C["bg"], fg=C["muted"]).pack(anchor="w")
        self.u_var = tk.StringVar(value=last_user)
        self.u_ent = ttk.Combobox(f, textvariable=self.u_var,
                                    values=all_users,
                                    font=("Arial", 12), state="normal")
        self.u_ent.pack(fill=tk.X, ipady=6, pady=(4, 14))
        # Select last user
        if last_user in all_users:
            self.u_ent.set(last_user)

        # Password
        tk.Label(f, text="Password", font=("Arial", 12, "bold"),
                 bg=C["bg"], fg=C["muted"]).pack(anchor="w")
        self.p_ent = tk.Entry(f, font=("Arial", 12), show="*",
                               bg=C["input"], fg=C["text"],
                               bd=0, insertbackground=C["accent"])
        self.p_ent.pack(fill=tk.X, ipady=8, pady=(4, 12))

        # Show password + Remember me row
        opt_row = tk.Frame(f, bg=C["bg"])
        opt_row.pack(fill=tk.X, pady=(0, 14))
        self._show_login_password = tk.BooleanVar(value=False)
        try:
            self._show_login_password.trace_add("write", self._on_toggle_login_password)
        except Exception:
            pass
        self._show_login_password_cb = tk.Checkbutton(
            opt_row,
            text="Show Password",
            variable=self._show_login_password,
            command=self._toggle_login_password,
            bg=C["bg"], fg=C["muted"],
            selectcolor=C["input"],
            font=("Arial", 11),
        )
        self._show_login_password_cb.pack(side=tk.LEFT)
        self._show_login_password_cb.bind(
            "<ButtonRelease-1>",
            lambda _e: self.win.after_idle(self._apply_login_password_visibility),
            add="+",
        )

        self.err = tk.Label(
            f,
            text="",
            font=("Arial", 11),
            bg=C["bg"],
            fg=C["red"],
            anchor="w",
            justify="left",
            wraplength=scaled_value(360, 320, 280),
        )
        self.err.pack(fill=tk.X, pady=(0, 8))

        self._login_btn = ModernButton(
            f,
            text="Login",
            command=self._login,
            color=C["accent"],
            hover_color=C["purple"],
            width=scaled_value(360, 320, 280),
            height=scaled_value(44, 40, 34),
            radius=10,
            font=("Arial", scaled_value(13, 12, 10), "bold"),
        )
        self._login_btn.pack(fill=tk.X)

        # C2 FIX: Remove hardcoded credential display. First-run users
        # are guided through a setup wizard on initial launch.
        tk.Label(f, text="Contact your administrator if you don't have credentials.",
                 font=("Arial", 9), bg=C["bg"],
                 fg=C["muted"]).pack(pady=(10, 0))

        self.u_var.trace_add("write", self._on_login_identity_change)
        self.win.bind("<Return>", lambda e: self._login())
        self.p_ent.focus_set()
        self._refresh_lockout_state()

    def _apply_login_password_visibility(self):
        try:
            self.p_ent.configure(show="" if self._show_login_password.get() else "*")
            self.p_ent.configure(fg=C["text"], insertbackground=C["accent"])
            self.p_ent.update_idletasks()
        except Exception:
            pass

    def _toggle_login_password(self):
        self._apply_login_password_visibility()

    def _on_toggle_login_password(self, *_args):
        self._apply_login_password_visibility()

    def _set_login_feedback(self, text: str = "", color: str | None = None):
        if not hasattr(self, "err"):
            return
        self.err.config(text=text, fg=color or C["red"])

    def _set_login_enabled(self, enabled: bool):
        if not hasattr(self, "_login_btn"):
            self._login_enabled = enabled
            return
        self._login_enabled = enabled
        if enabled:
            self._login_btn._cmd = self._login
            self._login_btn.set_text("Login")
            self._login_btn.set_color(C["accent"], C["purple"])
            self._login_btn.configure(cursor="hand2")
            self._login_btn._lbl.configure(cursor="hand2")
            return

        self._login_btn._cmd = None
        self._login_btn.set_text("Locked")
        self._login_btn.set_color(C["sidebar"], C["sidebar"])
        self._login_btn.configure(cursor="arrow")
        self._login_btn._lbl.configure(cursor="arrow")

    def _schedule_lockout_refresh(self):
        if self._lockout_after_id:
            try:
                self.win.after_cancel(self._lockout_after_id)
            except Exception:
                pass
        self._lockout_after_id = self.win.after(1000, self._refresh_lockout_state)

    def _refresh_lockout_state(self, *_args):
        if not hasattr(self, "u_var"):
            return
        username = self.u_var.get().strip()
        if not username:
            self._set_login_enabled(True)
            self._lockout_after_id = None
            return

        state = get_login_feedback_state(username)
        if state["locked"]:
            self._set_login_feedback(state["lock_message"] or "Too many failed attempts.")
            self._set_login_enabled(False)
            self._schedule_lockout_refresh()
            return

        self._set_login_enabled(True)
        if self._lockout_after_id:
            try:
                self.win.after_cancel(self._lockout_after_id)
            except Exception:
                pass
            self._lockout_after_id = None
        if hasattr(self, "err") and "Too many failed attempts" in self.err.cget("text"):
            self._set_login_feedback("")

    def _on_login_identity_change(self, *_args):
        if hasattr(self, "err") and self.err.cget("text") and "Invalid username or password" in self.err.cget("text"):
            self._set_login_feedback("")
        self._refresh_lockout_state()

    def _login(self):
        if not self._login_enabled:
            self._refresh_lockout_state()
            return
        u = self.u_var.get().strip()
        p = self.p_ent.get().strip()
        if not u or not p:
            self._set_login_feedback("Enter username and password")
            return
        lock_msg = get_login_lock_message(u)
        if lock_msg:
            self._set_login_feedback(lock_msg)
            self._set_login_enabled(False)
            self._schedule_lockout_refresh()
            self._apply_login_password_visibility()
            self.p_ent.focus_set()
            return
        user = verify_login(u, p)
        if user:
            clear_login_failures(u)
            self._set_login_feedback("")
            self._set_login_enabled(True)
            # Save last user
            try:
                from salon_settings import get_settings, save_settings
                cfg = get_settings()
                cfg["last_user"] = u
                save_settings(cfg)
            except Exception:
                pass
            # Auto-mark attendance: Present + In Time on login
            auto_mark_attendance(u, "login")

            # V5.6.1 Phase 1 — Activity log
            try:
                from activity_log import log_event
                log_event(
                    "login_success",
                    entity="auth",
                    entity_id=u,
                    user=u,
                )
            except Exception:
                pass

            self.logged_in_user = user
            try:
                self.win.quit()
            except Exception:
                pass
            try:
                self.win.destroy()
            except Exception:
                pass
        else:
            register_login_failure(u)

            # V5.6.1 Phase 1 — Activity log
            try:
                from activity_log import log_event
                log_event(
                    "login_failed",
                    entity="auth",
                    entity_id=u,
                    details={"reason": "invalid_credentials"},
                )
            except Exception:
                pass

            self._set_login_feedback(register_login_failure(u))
            self._refresh_lockout_state()
            self._apply_login_password_visibility()
            self.p_ent.focus_set()


# ─────────────────────────────────────────
#  USER MANAGEMENT  (called from admin panel)
# ─────────────────────────────────────────
class UserManagerWindow:
    def __init__(self, parent, current_user: dict):
        self.current_user = current_user
        self._show_user_password = tk.BooleanVar(value=False)
        self._responsive = get_responsive_metrics(parent.winfo_toplevel())

        win = tk.Toplevel(parent)
        hide_while_building(win)
        win.title("User Management")
        popup_window(win, 960, 620)
        fit_toplevel(
            win,
            scaled_value(1080, 980, 860),
            scaled_value(700, 640, 560),
            min_width=760,
            min_height=460,
        )
        win.configure(bg=C["bg"])
        win.grab_set()
        win.protocol("WM_DELETE_WINDOW",
                     lambda: (win.grab_release(), win.destroy()))

        dh = tk.Frame(win, bg=C["sidebar"], padx=16, pady=10)
        dh.pack(fill=tk.X)
        tk.Label(dh, text="User Management",
                 font=("Arial", 13, "bold"),
                 bg=C["sidebar"], fg=C["text"]).pack(side=tk.LEFT)
        tk.Frame(win, bg=C["teal"], height=2).pack(fill=tk.X)

        body, _canvas, _container = make_toplevel_scrollable(
            win, bg=C["bg"], padx=15, pady=10
        )

        cols = ("Username", "Name", "Role", "Status")
        self.tree = ttk.Treeview(body, columns=cols, show="headings", height=10)
        self._tree_cols = cols
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=scaled_value(140, 126, 110))
        self.tree.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        body.bind("<Configure>", self._resize_user_columns, add="+")

        # Form
        frm = tk.Frame(body, bg=C["card"], padx=15, pady=10)
        frm.pack(fill=tk.X, pady=(0, 5))

        for col in range(4):
            frm.grid_columnconfigure(col, weight=1)
        self.ents = {}
        self.ents["user"] = tk.Entry(
            frm, font=("Arial", 12), bg=C["input"], fg=C["text"], bd=0)
        self.ents["name"] = tk.Entry(
            frm, font=("Arial", 12), bg=C["input"], fg=C["text"], bd=0)
        self.ents["pass"] = tk.Entry(
            frm, font=("Arial", 12), bg=C["input"], fg=C["text"], bd=0, show="*")
        self.role_var = tk.StringVar(value="staff")
        role_cb = ttk.Combobox(
            frm, textvariable=self.role_var,
            values=["owner", "manager", "receptionist", "staff"],
            state="readonly")
        field_specs = [
            ("Username:", self.ents["user"], 0, 0),
            ("Display Name:", self.ents["name"], 0, 2),
            ("Password:", self.ents["pass"], 1, 0),
            ("Role:", role_cb, 1, 2),
        ]
        for lbl, widget, row, col in field_specs:
            tk.Label(frm, text=lbl, bg=C["card"], fg=C["muted"],
                     font=("Arial", 11)).grid(
                         row=row, column=col, padx=(8, 6), pady=6, sticky="w")
            widget.grid(row=row, column=col + 1, padx=(0, 8), pady=6,
                        ipady=3, sticky="ew")
        tk.Checkbutton(
            frm,
            text="Show Password",
            variable=self._show_user_password,
            command=lambda: self.ents["pass"].config(
                show="" if self._show_user_password.get() else "*"
            ),
            bg=C["card"],
            fg=C["muted"],
            selectcolor=C["input"],
            font=("Arial", 10),
        ).grid(row=2, column=1, padx=(0, 8), pady=(0, 4), sticky="w")

        # Buttons
        bb = tk.Frame(body, bg=C["bg"])
        bb.pack(fill=tk.X, pady=(0, 10))

        for txt, clr, hclr, cmd in [
            ("Add User",   C["teal"],   C["blue"],   self._add),
            ("Reset Pass", C["blue"],   "#154360",   self._reset_pass),
            ("Deactivate", C["orange"], "#d35400",   self._deactivate),
            ("Delete",     C["red"],    "#c0392b",   self._delete),
        ]:
            ModernButton(bb, text=txt, command=cmd,
                         color=clr, hover_color=hclr,
                         width=scaled_value(126, 118, 96), height=scaled_value(34, 32, 28), radius=8,
                         font=("Arial",scaled_value(10, 10, 9),"bold"),
                         ).pack(side=tk.LEFT, padx=3)

        self._load()
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        reveal_when_ready(win)

    def _resize_user_columns(self, event=None):
        if event is None:
            return
        width = max(520, event.width - 40)
        col_map = {
            "Username": max(120, int(width * 0.24)),
            "Name": max(140, int(width * 0.32)),
            "Role": max(110, int(width * 0.20)),
        }
        used = sum(col_map.values())
        col_map["Status"] = max(88, width - used)
        for col in self._tree_cols:
            self.tree.column(col, width=col_map[col])

    def _can_manage_users(self) -> bool:
        return str(self.current_user.get("role", "staff")).strip().lower() == "owner"

    def _deny_users(self) -> bool:
        if self._can_manage_users():
            return False
        messagebox.showerror("Access Denied",
                             "User management is restricted to Owner only.")
        return True

    def _load(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        for uname, u in get_users().items():
            status = "Active" if u.get("active", True) else "Inactive"
            self.tree.insert("", tk.END, values=(uname, u.get("name",""), u.get("role",""), status))

    def _clear_form(self):
        for key in ("user", "name", "pass"):
            self.ents[key].delete(0, tk.END)
        self.role_var.set("staff")
        self._show_user_password.set(False)
        self.ents["pass"].config(show="*")
        for item in self.tree.selection():
            self.tree.selection_remove(item)
        self.ents["user"].focus_set()

    def _on_select(self, e=None):
        sel = self.tree.selection()
        if not sel: return
        v = self.tree.item(sel[0], "values")
        self.ents["user"].delete(0, tk.END); self.ents["user"].insert(0, v[0])
        self.ents["name"].delete(0, tk.END); self.ents["name"].insert(0, v[1])
        self.role_var.set(v[2])

    def _add(self):
        if self._deny_users(): return
        u  = self.ents["user"].get().strip().lower()
        nm = self.ents["name"].get().strip()
        pw = self.ents["pass"].get().strip()
        rl = self.role_var.get()
        if not u or not nm or not pw:
            messagebox.showerror("Error", "Fill all fields."); return
        users = get_users()
        if u in users:
            messagebox.showerror("Error", "Username already exists."); return
        users[u] = {"password": hash_pw(pw), "role": rl, "name": nm, "active": True}
        if not _save_users(users):
            messagebox.showerror("Error", "User could not be saved."); return
        self._sync_staff_record(u, nm, rl, active=True)
        self._load()
        self._clear_form()
        messagebox.showinfo("Done", f"User '{u}' created!")

    def _reset_pass(self):
        if self._deny_users(): return
        sel = self.tree.selection()
        if not sel: messagebox.showerror("Error","Select a user."); return
        uname = self.tree.item(sel[0], "values")[0]
        pw    = self.ents["pass"].get().strip()
        if len(pw) < 8:
            messagebox.showerror("Error","Enter new password (min 8 chars)."); return
        if not messagebox.askyesno("Confirm Reset", f"Reset password for '{uname}'?"):
            return
        users = get_users()
        if uname in users:
            users[uname]["password"] = hash_pw(pw)
            if not _save_users(users):
                messagebox.showerror("Error", "Password could not be saved."); return
            messagebox.showinfo("Done", f"Password reset for '{uname}'.")

    def _deactivate(self):
        if self._deny_users(): return
        sel = self.tree.selection()
        if not sel: return
        uname = self.tree.item(sel[0], "values")[0]
        if uname == self.current_user.get("username"):
            messagebox.showerror("Error","Cannot deactivate yourself."); return
        users = get_users()
        if uname in users:
            users[uname]["active"] = not users[uname].get("active", True)
            _save_users(users)
            self._sync_staff_active(uname, users[uname].get("name", ""), users[uname].get("active", True))
            self._load()

    def _delete(self):
        if self._deny_users(): return
        sel = self.tree.selection()
        if not sel: return
        uname = self.tree.item(sel[0], "values")[0]
        if uname == self.current_user.get("username"):
            messagebox.showerror("Error","Cannot delete yourself."); return
        if messagebox.askyesno("Delete", f"Delete user '{uname}'?"):
            users = get_users()
            removed = users.get(uname, {})
            users.pop(uname, None)
            _save_users(users)
            self._remove_staff_record(uname, removed.get("name", ""))
            self._load()

    def _sync_staff_record(self, username: str, display_name: str, role: str, active: bool = True):
        role_key = str(role or "").strip().lower()
        if role_key not in {"staff", "manager", "receptionist"}:
            return
        try:
            from staff import get_staff, save_staff
            staff_data = get_staff()
            existing_key = None
            for key, rec in staff_data.items():
                if key.strip().lower() == display_name.strip().lower():
                    existing_key = key
                    break
            staff_key = existing_key or display_name
            current = staff_data.get(staff_key, {})
            staff_data[staff_key] = {
                "role": current.get("role") or role.title(),
                "phone": current.get("phone", ""),
                "commission_pct": current.get("commission_pct", 0),
                "salary": current.get("salary", 0),
                "join_date": current.get("join_date") or today_str(),
                "active": active,
                "attendance": current.get("attendance", []),
                "sales": current.get("sales", []),
                "username": username,
            }
            save_staff(staff_data)
        except Exception as e:
            app_log(f"[user->staff sync add] {e}")

    def _sync_staff_active(self, username: str, display_name: str, active: bool):
        try:
            from staff import get_staff, save_staff
            staff_data = get_staff()
            for key, rec in staff_data.items():
                if key.strip().lower() == display_name.strip().lower() or str(rec.get("username", "")).strip().lower() == username.strip().lower():
                    rec["active"] = active
                    rec["username"] = username
                    staff_data[key] = rec
                    save_staff(staff_data)
                    return
        except Exception as e:
            app_log(f"[user->staff sync active] {e}")

    def _remove_staff_record(self, username: str, display_name: str):
        try:
            from staff import get_staff, save_staff
            staff_data = get_staff()
            remove_key = None
            for key, rec in staff_data.items():
                if key.strip().lower() == display_name.strip().lower() or str(rec.get("username", "")).strip().lower() == username.strip().lower():
                    remove_key = key
                    break
            if remove_key:
                staff_data.pop(remove_key, None)
                save_staff(staff_data)
        except Exception as e:
            app_log(f"[user->staff sync delete] {e}")
