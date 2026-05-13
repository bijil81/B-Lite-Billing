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
from ui_responsive import (
    make_toplevel_scrollable,
    make_toplevel_scrollable_with_footer,
    get_responsive_metrics,
    scaled_value,
    fit_toplevel,
)
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
        except Exception as log_err:
            print(f"[auto_mark_attendance] {e} (logging also failed: {log_err})")



# ─────────────────────────────────────────
#  USER HELPERS
# ─────────────────────────────────────────
def get_users() -> dict:
    from adapters.auth_adapter import use_v5_users_db, get_users_legacy_map_v5
    if use_v5_users_db():
        return get_users_legacy_map_v5()
    
    users = load_json(F_USERS, {})
    if isinstance(users, dict):
        return users
    app_log(f"[auth] invalid users store type: {type(users).__name__}")
    return {}

def _save_users(u: dict) -> bool:
    from adapters.auth_adapter import use_v5_users_db, save_users_legacy_map_v5
    if use_v5_users_db():
        save_users_legacy_map_v5(u)
        return True
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
        except Exception as e:
            app_log(f"[show_first_run_setup] Failed to save last_user setting: {e}")

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
            except Exception as e:
                app_log(f"[LoginWindow._close_window] after_cancel failed: {e}")
            self._lockout_after_id = None
        self.logged_in_user = None
        try:
            self.win.quit()
        except Exception as e:
            app_log(f"[LoginWindow._close_window] win.quit() failed: {e}")
        try:
            self.win.destroy()
        except Exception as e:
            app_log(f"[LoginWindow._close_window] win.destroy() failed: {e}")


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
        except Exception as e:
            app_log(f"[LoginWindow._build] Logo load failed, using text fallback: {e}")
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
        except Exception as e:
            app_log(f"[LoginWindow._build] trace_add for show_password failed: {e}")

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
        except Exception as e:
            app_log(f"[LoginWindow._apply_login_password_visibility] {e}")


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
            except Exception as e:
                app_log(f"[LoginWindow._schedule_lockout_refresh] after_cancel failed: {e}")

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
            except Exception as e:
                app_log(f"[LoginWindow._refresh_lockout_state] after_cancel failed: {e}")

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
            except Exception as e:
                app_log(f"[LoginWindow._login] Failed to save last_user setting: {e}")

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
            except Exception as e:
                app_log(f"[LoginWindow._login] activity log (login_success) failed: {e}")


            self.logged_in_user = user
            try:
                self.win.quit()
            except Exception as e:
                app_log(f"[LoginWindow._login] win.quit() failed: {e}")
            try:
                self.win.destroy()
            except Exception as e:
                app_log(f"[LoginWindow._login] win.destroy() failed: {e}")

        else:
            # BUG FIX (2026-05-10): register_login_failure() was called TWICE —
            # once silently on line 762 and again on line 777 to get the message.
            # This double-counted every failure so lockout triggered after ~3
            # wrong passwords instead of the configured 5.
            # Fix: call once, capture the returned message, reuse it for feedback.
            _failure_msg = register_login_failure(u)

            # V5.6.1 Phase 1 — Activity log
            try:
                from activity_log import log_event
                log_event(
                    "login_failed",
                    entity="auth",
                    entity_id=u,
                    details={"reason": "invalid_credentials"},
                )
            except Exception as e:
                app_log(f"[LoginWindow._login] activity log (login_failed) failed: {e}")

            self._set_login_feedback(_failure_msg)
            self._refresh_lockout_state()
            self._apply_login_password_visibility()
            self.p_ent.focus_set()


# ─────────────────────────────────────────
#  USER MANAGEMENT  (called from admin panel)
# ─────────────────────────────────────────
class UserManagerWindow:
    def __init__(self, parent, current_user: dict, on_users_changed=None):
        self.current_user = current_user
        self.on_users_changed = on_users_changed
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

        body, footer, _canvas, _container = make_toplevel_scrollable_with_footer(
            win, bg=C["bg"], padx=15, pady=10
        )

        cols = ("Username", "Name", "Role", "Status")
        self.tree = ttk.Treeview(body, columns=cols, show="headings", height=14)
        self._tree_cols = cols
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=scaled_value(140, 126, 110))
        self.tree.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        body.bind("<Configure>", self._resize_user_columns, add="+")

        # Buttons
        bb = tk.Frame(footer, bg=C["bg"])
        bb.pack(fill=tk.X)

        self._add_user_btn = ModernButton(
            bb, text="Add User", command=self._add,
            color=C["teal"], hover_color=C["blue"],
            width=scaled_value(126, 118, 96), height=scaled_value(34, 32, 28), radius=8,
            font=("Arial",scaled_value(10, 10, 9),"bold"),
        )
        self._add_user_btn.pack(side=tk.LEFT, padx=3)
        self._reset_pass_btn = ModernButton(
            bb, text="Reset Pass", command=self._reset_pass,
            color=C["blue"], hover_color="#154360",
            width=scaled_value(126, 118, 96), height=scaled_value(34, 32, 28), radius=8,
            font=("Arial",scaled_value(10, 10, 9),"bold"),
        )
        self._reset_pass_btn.pack(side=tk.LEFT, padx=3)
        self._user_active_btn = ModernButton(
            bb, text="Deactivate", command=self._deactivate,
            color=C["orange"], hover_color="#d35400",
            width=scaled_value(126, 118, 96), height=scaled_value(34, 32, 28), radius=8,
            font=("Arial",scaled_value(10, 10, 9),"bold"),
        )
        self._user_active_btn.pack(side=tk.LEFT, padx=3)
        self._delete_user_btn = ModernButton(
            bb, text="Delete", command=self._delete,
            color=C["red"], hover_color="#c0392b",
            width=scaled_value(126, 118, 96), height=scaled_value(34, 32, 28), radius=8,
            font=("Arial",scaled_value(10, 10, 9),"bold"),
        )
        self._delete_user_btn.pack(side=tk.LEFT, padx=3)

        self._load()
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self._update_user_action_buttons()
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

    def _notify_users_changed(self):
        try:
            if callable(self.on_users_changed):
                self.on_users_changed()
        except Exception as e:
            app_log(f"[UserManagerWindow._notify_users_changed] {e}")

    def _clear_form(self):
        for item in self.tree.selection():
            self.tree.selection_remove(item)

    def _on_select(self, e=None):
        self._update_user_action_buttons()

    def _update_user_action_buttons(self):
        try:
            if not hasattr(self, "_user_active_btn"):
                return
            sel = self.tree.selection()
            if not sel:
                self._user_active_btn.set_text("Deactivate")
                self._user_active_btn.set_color(C["orange"], "#d35400")
                return
            values = self.tree.item(sel[0], "values")
            status = str(values[3] if len(values) > 3 else "").strip().lower()
            if status == "inactive":
                self._user_active_btn.set_text("Activate")
                self._user_active_btn.set_color(C["green"], C["teal"])
            else:
                self._user_active_btn.set_text("Deactivate")
                self._user_active_btn.set_color(C["orange"], "#d35400")
        except Exception as e:
            app_log(f"[UserManagerWindow._update_user_action_buttons] {e}")

    def _add(self):
        if self._deny_users(): return
        self._open_add_user_dialog()

    def _open_add_user_dialog(self):
        win = tk.Toplevel(self.tree.winfo_toplevel())
        hide_while_building(win)
        win.title("Add User")
        popup_window(win, 600, 430)
        win.configure(bg=C["bg"])
        win.grab_set()
        win.protocol("WM_DELETE_WINDOW", lambda: (win.grab_release(), win.destroy()))

        dh = tk.Frame(win, bg=C["sidebar"], padx=16, pady=10)
        dh.pack(fill=tk.X)
        tk.Label(dh, text="Add New User", font=("Arial", 13, "bold"),
                 bg=C["sidebar"], fg=C["text"]).pack(side=tk.LEFT)
        tk.Frame(win, bg=C["teal"], height=2).pack(fill=tk.X)

        frm = tk.Frame(win, bg=C["card"], padx=18, pady=14)
        frm.pack(fill=tk.BOTH, expand=True, padx=14, pady=14)
        frm.grid_columnconfigure(1, weight=1)

        entries = {}
        entries["user"] = tk.Entry(frm, font=("Arial", 12), bg=C["input"], fg=C["text"], bd=0)
        entries["name"] = tk.Entry(frm, font=("Arial", 12), bg=C["input"], fg=C["text"], bd=0)
        entries["pass"] = tk.Entry(frm, font=("Arial", 12), bg=C["input"], fg=C["text"], bd=0, show="*")
        entries["confirm"] = tk.Entry(frm, font=("Arial", 12), bg=C["input"], fg=C["text"], bd=0, show="*")
        role_var = tk.StringVar(value="staff")
        role_cb = ttk.Combobox(
            frm, textvariable=role_var,
            values=["owner", "manager", "receptionist", "staff"],
            state="readonly",
        )

        for row, (label, widget) in enumerate([
            ("Username:", entries["user"]),
            ("Display Name:", entries["name"]),
            ("Password:", entries["pass"]),
            ("Confirm Password:", entries["confirm"]),
            ("Role:", role_cb),
        ]):
            tk.Label(frm, text=label, bg=C["card"], fg=C["muted"],
                     font=("Arial", 11)).grid(row=row, column=0, padx=(0, 10), pady=7, sticky="w")
            widget.grid(row=row, column=1, padx=(0, 0), pady=5, ipady=4, sticky="ew")

        show_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            frm,
            text="Show Password",
            variable=show_var,
            command=lambda: [
                entries["pass"].config(show="" if show_var.get() else "*"),
                entries["confirm"].config(show="" if show_var.get() else "*"),
            ],
            bg=C["card"],
            fg=C["muted"],
            selectcolor=C["input"],
            font=("Arial", 10),
        ).grid(row=5, column=1, pady=(0, 4), sticky="w")

        btn_row = tk.Frame(frm, bg=C["card"])
        btn_row.grid(row=6, column=0, columnspan=2, sticky="e", pady=(12, 0))

        def _save():
            u = entries["user"].get().strip().lower()
            nm = entries["name"].get().strip()
            pw = entries["pass"].get().strip()
            confirm_pw = entries["confirm"].get().strip()
            rl = role_var.get()
            if pw != confirm_pw:
                messagebox.showerror("Error", "Password and Confirm Password do not match.", parent=win)
                return
            if self._create_user(u, nm, pw, rl, parent=win):
                win.grab_release()
                win.destroy()

        ModernButton(btn_row, text="Save", command=_save,
                     color=C["teal"], hover_color=C["blue"],
                     width=110, height=34, radius=8,
                     font=("Arial", 10, "bold")).pack(side=tk.RIGHT, padx=(6, 0))
        ModernButton(btn_row, text="Cancel", command=lambda: (win.grab_release(), win.destroy()),
                     color=C["sidebar"], hover_color=C["blue"],
                     width=100, height=34, radius=8,
                     font=("Arial", 10, "bold")).pack(side=tk.RIGHT)

        entries["user"].focus_set()
        reveal_when_ready(win)

    def _create_user(self, u: str, nm: str, pw: str, rl: str, parent=None) -> bool:
        if not u or not nm or not pw:
            messagebox.showerror("Error", "Fill all fields.", parent=parent); return False
        users = get_users()
        if u in users:
            messagebox.showerror("Error", "Username already exists.", parent=parent); return False
        users[u] = {"password": hash_pw(pw), "role": rl, "name": nm, "active": True}
        if not _save_users(users):
            messagebox.showerror("Error", "User could not be saved.", parent=parent); return False
        self._sync_staff_record(u, nm, rl, active=True)
        self._load()
        self._notify_users_changed()
        self._clear_form()
        messagebox.showinfo("Done", f"User '{u}' created!", parent=parent)
        return True

    def _reset_pass(self):
        if self._deny_users(): return
        sel = self.tree.selection()
        if not sel: messagebox.showerror("Error","Select a user."); return
        uname = self.tree.item(sel[0], "values")[0]
        win = tk.Toplevel(self.tree.winfo_toplevel())
        hide_while_building(win)
        win.title("Reset Password")
        popup_window(win, 500, 310)
        win.configure(bg=C["bg"])
        win.grab_set()
        win.protocol("WM_DELETE_WINDOW", lambda: (win.grab_release(), win.destroy()))

        dh = tk.Frame(win, bg=C["sidebar"], padx=16, pady=10)
        dh.pack(fill=tk.X)
        tk.Label(dh, text=f"Reset Password: {uname}", font=("Arial", 12, "bold"),
                 bg=C["sidebar"], fg=C["text"]).pack(side=tk.LEFT)
        tk.Frame(win, bg=C["teal"], height=2).pack(fill=tk.X)

        frm = tk.Frame(win, bg=C["card"], padx=18, pady=16)
        frm.pack(fill=tk.BOTH, expand=True, padx=14, pady=14)
        frm.grid_columnconfigure(1, weight=1)

        tk.Label(frm, text="New Password:", bg=C["card"], fg=C["muted"],
                 font=("Arial", 11)).grid(row=0, column=0, padx=(0, 10), pady=7, sticky="w")
        pass_entry = tk.Entry(frm, font=("Arial", 12), bg=C["input"], fg=C["text"], bd=0, show="*")
        pass_entry.grid(row=0, column=1, pady=7, ipady=4, sticky="ew")
        tk.Label(frm, text="Confirm Password:", bg=C["card"], fg=C["muted"],
                 font=("Arial", 11)).grid(row=1, column=0, padx=(0, 10), pady=7, sticky="w")
        confirm_entry = tk.Entry(frm, font=("Arial", 12), bg=C["input"], fg=C["text"], bd=0, show="*")
        confirm_entry.grid(row=1, column=1, pady=7, ipady=4, sticky="ew")
        show_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            frm,
            text="Show Password",
            variable=show_var,
            command=lambda: [
                pass_entry.config(show="" if show_var.get() else "*"),
                confirm_entry.config(show="" if show_var.get() else "*"),
            ],
            bg=C["card"],
            fg=C["muted"],
            selectcolor=C["input"],
            font=("Arial", 10),
        ).grid(row=2, column=1, sticky="w")

        btn_row = tk.Frame(frm, bg=C["card"])
        btn_row.grid(row=3, column=0, columnspan=2, sticky="e", pady=(18, 0))

        def _save():
            pw = pass_entry.get().strip()
            confirm_pw = confirm_entry.get().strip()
            if len(pw) < 8:
                messagebox.showerror("Error","Enter new password (min 8 chars).", parent=win); return
            if pw != confirm_pw:
                messagebox.showerror("Error", "Password and Confirm Password do not match.", parent=win); return
            if not messagebox.askyesno("Confirm Reset", f"Reset password for '{uname}'?", parent=win):
                return
            users = get_users()
            if uname in users:
                users[uname]["password"] = hash_pw(pw)
                if not _save_users(users):
                    messagebox.showerror("Error", "Password could not be saved.", parent=win); return
                win.grab_release()
                win.destroy()
                messagebox.showinfo("Done", f"Password reset for '{uname}'.")

        ModernButton(btn_row, text="Save", command=_save,
                     color=C["blue"], hover_color="#154360",
                     width=110, height=34, radius=8,
                     font=("Arial", 10, "bold")).pack(side=tk.RIGHT, padx=(6, 0))
        ModernButton(btn_row, text="Cancel", command=lambda: (win.grab_release(), win.destroy()),
                     color=C["sidebar"], hover_color=C["blue"],
                     width=100, height=34, radius=8,
                     font=("Arial", 10, "bold")).pack(side=tk.RIGHT)
        pass_entry.focus_set()
        reveal_when_ready(win)

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
            self._select_user_row(uname)
            self._update_user_action_buttons()
            self._notify_users_changed()

    def _select_user_row(self, username: str):
        username = str(username or "").strip().lower()
        if not username:
            return
        for item_id in self.tree.get_children():
            values = self.tree.item(item_id, "values")
            if values and str(values[0]).strip().lower() == username:
                self.tree.selection_set(item_id)
                self.tree.focus(item_id)
                self.tree.see(item_id)
                return

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
            deleted = False
            try:
                from adapters.auth_adapter import use_v5_users_db, delete_user_v5
                if use_v5_users_db():
                    delete_user_v5(uname)
                    deleted = True
            except Exception as e:
                app_log(f"[user delete v5] {e}")
            if not deleted:
                users.pop(uname, None)
                _save_users(users)
            self._remove_staff_record(uname, removed.get("name", ""))
            self._load()
            self._clear_form()
            self._update_user_action_buttons()
            self._notify_users_changed()

    def _sync_staff_record(self, username: str, display_name: str, role: str, active: bool = True):
        role_key = str(role or "").strip().lower()
        if role_key not in {"staff", "manager", "receptionist"}:
            return
        try:
            from staff import get_staff, save_staff
            staff_data = get_staff()
            users = get_users()
            existing_key = None
            username_norm = username.strip().lower()
            display_norm = display_name.strip().lower()
            duplicate_display = sum(
                1 for uname, urec in users.items()
                if str(uname).strip().lower() != username_norm
                and str(urec.get("name", "")).strip().lower() == display_norm
            ) > 0
            for key, rec in staff_data.items():
                if str(rec.get("username", "")).strip().lower() == username_norm:
                    existing_key = key
                    break
            if existing_key is None:
                for key, rec in staff_data.items():
                    rec_username = str(rec.get("username", "")).strip().lower()
                    can_claim_legacy_name = (
                        not rec_username
                        and (not duplicate_display or username_norm == display_norm)
                    )
                    if key.strip().lower() == display_norm and (rec_username == username_norm or can_claim_legacy_name):
                        existing_key = key
                        break
            staff_key = existing_key or display_name
            if not existing_key and staff_key in staff_data:
                staff_key = f"{display_name} ({username})"
            current = staff_data.get(staff_key, {})
            staff_data[staff_key] = {
                "role": role.title(),
                "phone": current.get("phone", ""),
                "commission_pct": current.get("commission_pct", 0),
                "salary": current.get("salary", 0),
                "join_date": current.get("join_date") or today_str(),
                "active": active,
                "inactive": not bool(active),
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
            users = get_users()
            username_norm = username.strip().lower()
            display_norm = display_name.strip().lower()
            duplicate_display = sum(
                1 for uname, urec in users.items()
                if str(uname).strip().lower() != username_norm
                and str(urec.get("name", "")).strip().lower() == display_norm
            ) > 0
            matched_key = None
            for key, rec in staff_data.items():
                if str(rec.get("username", "")).strip().lower() == username_norm:
                    matched_key = key
                    break
            if matched_key is None:
                for key, rec in staff_data.items():
                    rec_username = str(rec.get("username", "")).strip().lower()
                    can_claim_legacy_name = (
                        not rec_username
                        and (not duplicate_display or username_norm == display_norm)
                    )
                    if key.strip().lower() == display_norm and (rec_username == username_norm or can_claim_legacy_name):
                        matched_key = key
                        break
            if matched_key:
                rec = staff_data.get(matched_key, {})
                rec["active"] = active
                rec["inactive"] = not bool(active)
                rec["username"] = username
                staff_data[matched_key] = rec
                save_staff(staff_data)
                return
        except Exception as e:
            app_log(f"[user->staff sync active] {e}")

    def _remove_staff_record(self, username: str, display_name: str):
        try:
            from staff import get_staff, save_staff
            staff_data = get_staff()
            users = get_users()
            remove_key = None
            username_norm = username.strip().lower()
            display_norm = display_name.strip().lower()
            duplicate_display = sum(
                1 for uname, urec in users.items()
                if str(uname).strip().lower() != username_norm
                and str(urec.get("name", "")).strip().lower() == display_norm
            ) > 0
            for key, rec in staff_data.items():
                if str(rec.get("username", "")).strip().lower() == username_norm:
                    remove_key = key
                    break
            if remove_key is None:
                for key, rec in staff_data.items():
                    rec_username = str(rec.get("username", "")).strip().lower()
                    can_claim_legacy_name = (
                        not rec_username
                        and (not duplicate_display or username_norm == display_norm)
                    )
                    if key.strip().lower() == display_norm and (rec_username == username_norm or can_claim_legacy_name):
                        remove_key = key
                        break
            if remove_key:
                staff_data.pop(remove_key, None)
                save_staff(staff_data)
        except Exception as e:
            app_log(f"[user->staff sync delete] {e}")
