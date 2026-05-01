"""
main.py  Ã¢â‚¬â€œ  BOBY'S Beauty Salon Management System  v8
FIXES (all preserved):
  - Bug 16, Issue A, Bug 11, M3aÃ¢â‚¬â€œM3g stability fixes
UI v3.0:
  - Sidebar nav items Ã¢â‚¬â€ rounded hover pill, active accent strip wider
  - Sidebar logo section Ã¢â‚¬â€ subtle bottom border separator
  - User info section Ã¢â‚¬â€ avatar circle + role badge pill
  - Logout button Ã¢â‚¬â€ ModernButton rounded red
  - Top bar Ã¢â‚¬â€ page title breadcrumb style + Today revenue pill
  - Admin + Bell buttons Ã¢â‚¬â€ ModernButton rounded
  - Nav active state Ã¢â‚¬â€ brighter accent strip (4px), bg highlight
"""
import tkinter as tk
from tkinter import messagebox, ttk
import os, sys
import time
import ctypes
import importlib
import subprocess
import traceback

from ui_text import install_ui_text_patch
install_ui_text_patch()

from utils import (C, resource_path, init_services_db,
                   fmt_currency, F_REPORT, today_str, safe_float,
                   app_log)
from auth import LoginWindow
from migration_state import initialize_runtime_migration_state
from backup_system import maybe_prompt_restore
from ui_theme import ModernButton
from help_system import show_context_help
from icon_system import get_nav_icon, get_action_icon, clear_icon_cache
from licensing.ui_gate import ensure_startup_access
from secure_store import load_ai_api_key
from branding import (
    get_branding_icon_path,
    get_branding_logo_path,
    get_short_name,
    get_sidebar_title,
    get_window_title,
)
from ui_responsive import get_responsive_metrics, initialize_responsive
from ui_theme import refresh_fonts
# Ã¢â€â‚¬Ã¢â€â‚¬ AI Assistant (optional Ã¢â‚¬â€ works without if not installed) Ã¢â€â‚¬Ã¢â€â‚¬
try:
    from ai_assistant.controllers.ai_controller import AIController
    from ai_assistant.ui.ai_chat_window import AIChatWindow, AIChatFrame
    AI_AVAILABLE = True
except Exception:
    AI_AVAILABLE = False


def _enable_windows_dpi_awareness():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def _relaunch_current_app():
    try:
        if getattr(sys, "frozen", False):
            target = sys.executable
            if target:
                subprocess.Popen([target], close_fds=True)
                return True
        main_file = os.path.abspath(__file__)
        python_exe = sys.executable or "python"
        subprocess.Popen([python_exe, main_file], close_fds=True)
        return True
    except Exception as e:
        try:
            app_log(f"[relaunch] {e}")
        except Exception:
            pass
        return False


def _log_exception(prefix: str, exc_type=None, exc_value=None, exc_tb=None) -> None:
    try:
        if exc_type is None or exc_value is None or exc_tb is None:
            exc_type, exc_value, exc_tb = sys.exc_info()
        if exc_type is None or exc_value is None or exc_tb is None:
            app_log(f"{prefix}: unknown exception")
            return
        details = "".join(traceback.format_exception(exc_type, exc_value, exc_tb)).strip()
        app_log(f"{prefix}\n{details}")
    except Exception:
        pass


def _show_fatal_error_dialog(title: str, message: str) -> None:
    temp_root = None
    try:
        parent = getattr(tk, "_default_root", None)
        if parent is None:
            temp_root = tk.Tk()
            temp_root.withdraw()
            parent = temp_root
        messagebox.showerror(title, message, parent=parent)
    except Exception:
        pass
    finally:
        if temp_root is not None:
            try:
                temp_root.destroy()
            except Exception:
                pass


def _install_global_exception_hooks() -> None:
    if getattr(_install_global_exception_hooks, "_installed", False):
        return

    def _tk_callback_exception(self, exc_type, exc_value, exc_tb):
        _log_exception("[tk] unhandled callback exception", exc_type, exc_value, exc_tb)
        _show_fatal_error_dialog(
            "Unexpected Error",
            "The app hit an unexpected error.\n\n"
            "Please close and reopen the app.\n"
            "If the issue repeats, check app_debug.log.",
        )

    def _sys_excepthook(exc_type, exc_value, exc_tb):
        _log_exception("[startup] unhandled exception", exc_type, exc_value, exc_tb)
        _show_fatal_error_dialog(
            "Startup Error",
            "The app could not start correctly.\n\n"
            "Please restart the app.\n"
            "If the issue repeats, check app_debug.log.",
        )

    tk.Tk.report_callback_exception = _tk_callback_exception
    tk.Toplevel.report_callback_exception = _tk_callback_exception
    sys.excepthook = _sys_excepthook
    _install_global_exception_hooks._installed = True


def _run_startup_step(label: str, func):
    try:
        app_log(f"[startup] {label} started", "info")
        result = func()
        app_log(f"[startup] {label} completed", "info")
        return result
    except SystemExit:
        raise
    except Exception:
        _log_exception(f"[startup] {label} failed")
        raise


class SalonApp:
    # Reminder loop interval in milliseconds (5 minutes)
    _REMINDER_INTERVAL_MS = 300_000

    def _user_role(self) -> str:
        return str(self.current_user.get("role", "staff")).strip().lower() or "staff"

    def _has_access(self, nav_entry) -> bool:
        if not nav_entry:
            return False
        allowed = nav_entry[3]
        if isinstance(allowed, bool):
            return (not allowed) or self._user_role() == "owner"
        return self._user_role() in [str(r).strip().lower() for r in allowed]

    # Final v4.1 role matrix.
    NAV = [
        ("\U0001F4C8", "Dashboard",      "dashboard",      ["owner", "manager", "receptionist"]),
        ("\U0001F9FE", "Billing",        "billing",        ["owner", "manager", "receptionist", "staff"]),
        ("\U0001F465", "Customers",      "customers",      ["owner", "manager", "receptionist", "staff"]),
        ("\U0001F4C5", "Appointments",   "appointments",   ["owner", "manager", "receptionist", "staff"]),
        ("\U0001F381", "Memberships",    "membership",     ["owner", "manager", "receptionist"]),
        ("\U0001F3F7\uFE0F", "Offers",   "offers",         ["owner", "manager"]),
        ("\U0001F39F\uFE0F", "Redeem",   "redeem_codes",   ["owner", "manager", "receptionist"]),
        ("\u2601\uFE0F", "Cloud Sync",   "cloud_sync",     ["owner"]),
        ("\U0001F469\u200D\U0001F4BC", "Staff", "staff",   ["owner", "manager"]),
        ("\U0001F4E6", "Inventory",      "inventory",      ["owner", "manager"]),
        ("\U0001F4B0", "Expenses",       "expenses",       ["owner", "manager"]),
        ("\U0001F48C", "Bulk WhatsApp",  "whatsapp_bulk",  ["owner", "manager", "receptionist"]),
        ("\U0001F4CA", "Reports",        "reports",        ["owner", "manager"]),
        ("\U0001F4C5", "Closing Report", "closing_report", ["owner", "manager"]),
        ("\U0001F916", "AI Assistant",   "ai_assistant",   ["owner", "manager", "receptionist", "staff"]),
        ("\u2699",     "Settings",       "settings",       ["owner"]),
    ]

    ACTION_ROLES = {
        "admin_panel":       ["owner"],
        "manage_users":      ["owner"],
        "manage_staff":      ["owner", "manager"],
        "manage_inventory":  ["owner", "manager"],
        "manage_expenses":   ["owner", "manager"],
        "manage_offers":     ["owner", "manager"],
        "manage_cloud_sync": ["owner"],
        "delete_bill":       ["owner", "manager"],
    }

    def has_permission(self, permission: str) -> bool:
        allowed = self.ACTION_ROLES.get(permission, [])
        if not allowed:
            return False
        return self._user_role() in [str(r).strip().lower() for r in allowed]

    def require_permission(self, permission: str, label: str = "This action") -> bool:
        if self.has_permission(permission):
            return True
        messagebox.showerror("Access Denied",
                             f"{label} is restricted for your role.")
        return False

    def _first_allowed_nav_key(self):
        for entry in self.NAV:
            if self._has_access(entry):
                return entry[2]
        return None

    def _destroy_ai_floating_widgets(self):
        for attr in ("_ai_window", "_ai_chat"):
            widget = getattr(self, attr, None)
            if not widget:
                continue
            try:
                if hasattr(widget, "hide"):
                    widget.hide()
            except Exception:
                pass
            try:
                btn = getattr(widget, "_float_btn", None)
                if btn and btn.winfo_exists():
                    btn.destroy()
            except Exception:
                pass
            setattr(self, attr, None)

    def _refresh_ai_floating_button(self):
        self._destroy_ai_floating_widgets()
        if not (AI_AVAILABLE and self.ai_ctrl and self._feature_enabled("ai_assistant")):
            return
        try:
            from salon_settings import get_settings as _gs
            if not _gs().get("show_ai_floating_button", True):
                return
            self._ai_chat = AIChatWindow(
                self.root, self.ai_ctrl, app_ref=self)
        except Exception as _ae:
            app_log(f"[AI float btn] {_ae}")

    def _show_startup_splash(self):
        self._startup_splash_started = time.perf_counter()
        splash = tk.Toplevel(self.root)
        splash.overrideredirect(True)
        splash.configure(bg="black")
        try:
            splash.attributes("-topmost", True)
        except Exception:
            pass

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        splash.geometry(f"{sw}x{sh}+0+0")

        holder = tk.Frame(splash, bg="black")
        holder.pack(fill=tk.BOTH, expand=True)
        center = tk.Frame(holder, bg="black")
        center.place(relx=0.5, rely=0.5, anchor="center")

        self._startup_media_frames = []
        self._startup_media_label = None
        self._startup_logo_img = None

        try:
            from PIL import Image, ImageTk, ImageSequence
            gif_path = get_branding_logo_path("splash")
            if os.path.exists(gif_path):
                gif = Image.open(gif_path)
                target_w = sw
                target_h = sh
                max_frames = 12
                step = max(1, getattr(gif, "n_frames", 1) // max_frames)
                for idx, frame in enumerate(ImageSequence.Iterator(gif)):
                    if idx % step != 0:
                        continue
                    fr = frame.convert("RGBA")
                    self._startup_media_frames.append(
                        ImageTk.PhotoImage(fr.resize((target_w, target_h))))
                    if len(self._startup_media_frames) >= max_frames:
                        break
                if self._startup_media_frames:
                    media = tk.Label(
                        holder,
                        image=self._startup_media_frames[0],
                        bg="black",
                        bd=0
                    )
                    media.place(x=0, y=0, relwidth=1, relheight=1)
                    media.image = self._startup_media_frames[0]
                    self._startup_media_label = media
            if self._startup_media_label is None:
                img = Image.open(get_branding_logo_path("main")).convert("RGBA")
                bb = img.getbbox()
                if bb:
                    img = img.crop(bb)
                w = min(360, img.size[0])
                h = max(1, int(img.size[1] * w / max(1, img.size[0])))
                self._startup_logo_img = ImageTk.PhotoImage(img.resize((w, h)))
                tk.Label(center, image=self._startup_logo_img,
                         bg="black", bd=0).pack(pady=(0, 16))
        except Exception:
            tk.Label(center, text=get_short_name(),
                     bg="black", fg=C["accent"],
                     font=("Arial", 26, "bold")).pack(pady=(0, 12))

        self._startup_status_label = tk.Label(
            center,
            text="Loading.",
            bg="black",
            fg="#d7d7d7",
            font=("Arial", 14, "bold")
        )
        self._startup_status_label.pack()
        tk.Label(
            center,
            text="Preparing your workspace",
            bg="black",
            fg="#9aa4b2",
            font=("Arial", 10)
        ).pack(pady=(6, 0))

        self._startup_splash = splash
        self._startup_placeholder = splash
        self._startup_placeholder_label = self._startup_status_label
        if self._startup_media_label is not None:
            self.root.after(50, self._play_startup_media)
        self.root.after(30, self._animate_loading_placeholder)
        self.root.after(40, self._animate_loading_text)

    def _finish_startup_splash(self):
        if self._animations_enabled():
            min_duration = 2.2
            remaining = min_duration - (time.perf_counter() - getattr(self, "_startup_splash_started", 0.0))
            if remaining > 0:
                self.root.after(max(1, int(remaining * 1000)), self._finish_startup_splash)
                return
        splash = getattr(self, "_startup_splash", None)
        if splash is not None:
            try:
                splash.destroy()
            except Exception:
                pass
        self._startup_splash = None

    def _animations_enabled(self) -> bool:
        try:
            from salon_settings import get_settings as _gs
            return bool(_gs().get("enable_animations", True))
        except Exception:
            return True

    def _animate_loading_placeholder(self):
        if not self._animations_enabled():
            return
        label = getattr(self, "_startup_placeholder_label", None)
        placeholder = getattr(self, "_startup_placeholder", None)
        if not label or not placeholder:
            return
        try:
            if not (label.winfo_exists() and placeholder.winfo_exists()):
                return
        except Exception:
            return
        try:
            from ui_theme import anim
            label.configure(fg=C["muted"])
            anim.color(label, C["muted"], C["text"], prop="fg", dur=170)
            self.root.after(220, lambda: self._animate_loading_placeholder())
        except Exception:
            pass

    def _animate_loading_text(self, step=0):
        placeholder = getattr(self, "_startup_placeholder", None)
        label = getattr(self, "_startup_placeholder_label", None)
        if not placeholder or not label:
            return
        try:
            if not (placeholder.winfo_exists() and label.winfo_exists()):
                return
        except Exception:
            return
        dots = "." * ((step % 3) + 1)
        try:
            label.configure(text=f"Loading{dots}")
        except Exception:
            return
        self.root.after(320, lambda s=step + 1: self._animate_loading_text(s))

    def _play_startup_media(self, index=0):
        placeholder = getattr(self, "_startup_placeholder", None)
        label = getattr(self, "_startup_media_label", None)
        frames = getattr(self, "_startup_media_frames", None)
        if not placeholder or not label or not frames:
            return
        try:
            if not (placeholder.winfo_exists() and label.winfo_exists()):
                return
        except Exception:
            return
        try:
            frame = frames[index % len(frames)]
            label.configure(image=frame)
            label.image = frame
        except Exception:
            return
        self.root.after(70, lambda i=index + 1: self._play_startup_media(i))

    def _animate_startup_logo(self, step=0):
        if not self._animations_enabled():
            return
        placeholder = getattr(self, "_startup_placeholder", None)
        label = getattr(self, "_startup_logo_label", None)
        base_img = getattr(self, "_startup_logo_base", None)
        if not placeholder or not label or base_img is None:
            return
        try:
            if not (placeholder.winfo_exists() and label.winfo_exists()):
                return
        except Exception:
            return
        try:
            from PIL import ImageTk
            scales = [0.88, 0.94, 1.00, 1.06, 1.12, 1.06, 1.00, 0.94]
            scale = scales[step % len(scales)]
            w = max(1, int(base_img.size[0] * scale))
            h = max(1, int(base_img.size[1] * scale))
            img = ImageTk.PhotoImage(base_img.resize((w, h)))
            label.configure(image=img)
            label.image = img
            self._startup_logo_img = img
        except Exception:
            return
        self.root.after(110, lambda s=step + 1: self._animate_startup_logo(s))

    def _animate_page_reveal(self):
        if not self._animations_enabled():
            return
        try:
            from ui_theme import anim
            self.page_title.configure(fg=C["muted"])
            anim.color(self.page_title, C["muted"], C["text"], prop="fg", dur=140)
            self.today_lbl.configure(bg=C["blue"])
            anim.color(self.today_lbl, C["blue"], C["teal"], prop="bg", dur=150)
        except Exception:
            pass

    def apply_runtime_preferences(self):
        if not self._animations_enabled():
            try:
                self.page_title.configure(fg=C["text"])
                self.today_lbl.configure(bg=C["teal"])
            except Exception:
                pass
        self._refresh_ai_floating_button()

    def apply_runtime_ai_settings(self):
        try:
            from salon_settings import get_settings as _gs
            ai_cfg = _gs().get("ai_config", {})
            if self.ai_ctrl:
                self.ai_ctrl.set_api_key(load_ai_api_key(ai_cfg))
                self.ai_ctrl.toggle_ai(ai_cfg.get("enabled", True))
        except Exception as _ae:
            app_log(f"[apply_runtime_ai_settings] {_ae}")
        self._refresh_ai_floating_button()

    def _feature_enabled(self, feature_name: str) -> bool:
        try:
            from salon_settings import feature_enabled as _feature_enabled
            return _feature_enabled(feature_name)
        except Exception:
            return False

    def _set_nav_row_visibility(self, key: str, visible: bool):
        row = self._nav_rows.get(key)
        if row is None:
            return
        if visible:
            if row.winfo_manager() == "pack":
                return
            before_widget = None
            seen = False
            for _, _, nav_key, allowed_roles in self.NAV:
                if nav_key == key:
                    seen = True
                    continue
                if not seen:
                    continue
                if not self._has_access(("", "", nav_key, allowed_roles)):
                    continue
                candidate = self._nav_rows.get(nav_key)
                if candidate is not None and candidate.winfo_manager() == "pack":
                    before_widget = candidate
                    break
            pack_kwargs = {"fill": tk.X, "pady": 1}
            if before_widget is not None:
                row.pack(before=before_widget, **pack_kwargs)
            else:
                row.pack(**pack_kwargs)
        else:
            if row.winfo_manager() == "pack":
                row.pack_forget()

    def _apply_sidebar_feature_visibility(self):
        self._set_nav_row_visibility("ai_assistant", self._feature_enabled("ai_assistant"))

    def apply_runtime_feature_settings(self):
        try:
            if self._feature_enabled("ai_assistant") and AI_AVAILABLE and not self.ai_ctrl:
                try:
                    from salon_settings import get_settings as _gs
                    _ai_cfg = _gs().get("ai_config", {})
                    self.ai_ctrl = AIController(
                        app_ref=self,
                        api_key=load_ai_api_key(_ai_cfg))
                    self.ai_ctrl.toggle_ai(_ai_cfg.get("enabled", True))
                except Exception as _aie:
                    app_log(f"[apply_runtime_feature_settings ai init] {_aie}")
            if self._feature_enabled("ai_assistant"):
                stale = self.frames.pop("ai_assistant", None)
                try:
                    if stale and stale.winfo_exists():
                        stale.destroy()
                except Exception:
                    pass
                self.module_classes.pop("ai_assistant", None)
            self._apply_sidebar_feature_visibility()
            self._refresh_ai_floating_button()
            if not self._feature_enabled("ai_assistant"):
                self._destroy_ai_floating_widgets()
                if self.current_page_key == "ai_assistant":
                    fallback = self._first_allowed_nav_key() or "dashboard"
                    if fallback != "ai_assistant":
                        self.switch_to(fallback)
        except Exception as _fe:
            app_log(f"[apply_runtime_feature_settings] {_fe}")

    def _restart_to_login(self):
        self._restart_login_requested = True
        try:
            self._cancel_root_after_callbacks()
        except Exception:
            pass
        try:
            from ui_theme import anim
            anim.stop()
        except Exception:
            pass
        try:
            clear_icon_cache()
        except Exception:
            pass
        try:
            self._destroy_ai_floating_widgets()
        except Exception:
            pass
        try:
            self.root.withdraw()
            self.root.update_idletasks()
            self.root.update()
        except Exception:
            pass
        try:
            self.root.quit()
        except Exception:
            pass

    def _shutdown_app(self):
        self._restart_login_requested = False
        try:
            self._cancel_root_after_callbacks()
        except Exception:
            pass
        # V5.6.1 Phase 1 — Stop scheduled backup on shutdown
        try:
            from scheduled_backup import stop_scheduler
            stop_scheduler()
        except Exception:
            pass
        try:
            from ui_theme import anim
            anim.stop()
        except Exception:
            pass
        try:
            clear_icon_cache()
        except Exception:
            pass
        try:
            self._destroy_ai_floating_widgets()
        except Exception:
            pass
        try:
            self.root.withdraw()
            self.root.update_idletasks()
            self.root.update()
        except Exception:
            pass
        try:
            self.root.quit()
        except Exception:
            pass

    def _cancel_root_after_callbacks(self):
        try:
            info = self.root.tk.call("after", "info")
        except Exception:
            return
        if isinstance(info, str):
            ids = [info] if info else []
        else:
            ids = list(info)
        for after_id in ids:
            try:
                self.root.after_cancel(after_id)
            except Exception:
                pass

    def __init__(self, user: dict):
        self.current_user  = user
        self._admin_panel  = None   # Bug 11: track open admin panel
        self._restart_login_requested = False

        _enable_windows_dpi_awareness()
        self.root = tk.Tk()
        try:
            clear_icon_cache()
        except Exception:
            pass
        try:
            self.root.protocol("WM_DELETE_WINDOW", self._shutdown_app)
        except Exception:
            pass
        self.root.withdraw()
        try:
            dpi = self.root.winfo_fpixels("1i")
            self.root.tk.call("tk", "scaling", dpi / 72)
        except Exception:
            pass
        self._responsive = initialize_responsive(self.root)
        # Phase 3 FIX: Recompute font constants from responsive metrics
        refresh_fonts()
        self.root.title(get_window_title(include_version=True))
        self.root.configure(bg=C["bg"])
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{sw}x{sh}+0+0")
        self.root.state("zoomed")
        self.root.minsize(960, 600)
        try:
            self.root.iconbitmap(get_branding_icon_path("app"))
        except Exception:
            pass
        self._show_startup_placeholder(self.root)
        self.root.update_idletasks()
        self.root.deiconify()

        # Phase 3 FIX: respond to live window resize by refreshing
        # the active module so it can adapt layout metrics.
        self._resize_debounce_ms = 150
        self._resize_after_id = None
        self.root.bind("<Configure>", self._on_window_resize, add="+")

        # Apply theme colors + global ttk dark styling BEFORE widgets are built
        try:
            from ui_theme import apply_global_ttk_dark_theme
            from salon_settings import get_settings, apply_theme
            _cfg = get_settings()
            apply_theme(_cfg.get("theme", "dark"))
            apply_global_ttk_dark_theme(self.root)
            self.root.update_idletasks()
        except Exception:
            pass
        # Start animation engine after root is ready
        from ui_theme import anim
        anim.init(self.root)

        # AI controller (initialised before _build so tab frame can use it)
        self.ai_ctrl = None
        if AI_AVAILABLE and self._feature_enabled("ai_assistant"):
            try:
                from salon_settings import get_settings as _gs
                _ai_cfg = _gs().get("ai_config", {})
                self.ai_ctrl = AIController(
                    app_ref=self,
                    api_key=load_ai_api_key(_ai_cfg))
                self.ai_ctrl.toggle_ai(_ai_cfg.get("enabled", True))
            except Exception as _ae:
                app_log(f"[AI init] {_ae}")

        self.frames    = {}
        self.module_specs = {}
        self.module_classes = {}
        self.current_page_key = None
        self._nav_btns = {}
        self._nav_strips = {}
        self._nav_rows = {}
        self._build()
        self._install_context_menu_shortcuts()
        self._setup_session_security()
        self.root.update_idletasks()
        self.root.bind("<Map>", self._on_root_map, add="+")
        self._ai_window = None
        self._ai_chat = None

        # Ã¢â€â‚¬Ã¢â€â‚¬ Floating AI button Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
        self.root.after(80, self._refresh_ai_floating_button)
        first_key = self._first_allowed_nav_key() or "dashboard"
        self.switch_to(first_key)

        # AI floating chat button (bottom-right)

        # Startup notifications (existing)
        self.root.after(1500, lambda: self._show_notifications(manual=False))
        self.root.after(900, lambda: maybe_prompt_restore(self.root))

        # Smart appointment reminder loop Ã¢â‚¬â€ starts 2 s after UI is ready,
        # then repeats every 5 minutes automatically via self.after()
        self.root.after(2000, self._check_appointment_reminders)

        self.root.mainloop()
        try:
            if int(self.root.winfo_exists()):
                self.root.destroy()
        except Exception:
            pass

    def _install_context_menu_shortcuts(self):
        try:
            from shared.context_menu.shortcut_service import shortcut_service
            shortcut_service.install(self.root, app_ref=self, enabled=True)
        except Exception as e:
            app_log(f"[context_menu shortcuts] {e}")

    def _setup_session_security(self):
        self._last_activity_ts = time.monotonic()
        self.root.bind_all("<Any-KeyPress>", self._note_activity, add="+")
        self.root.bind_all("<Any-ButtonPress>", self._note_activity, add="+")
        self.root.after(60_000, self._check_session_timeout)

    def _note_activity(self, _event=None):
        self._last_activity_ts = time.monotonic()

    def _session_timeout_minutes(self) -> int:
        try:
            from salon_settings import get_settings as _gs
            cfg = _gs()
            return max(5, int(cfg.get("session_timeout_minutes", 30) or 30))
        except Exception:
            return 30

    def _check_session_timeout(self):
        if not getattr(self, "root", None):
            return
        try:
            if not int(self.root.winfo_exists()):
                return
        except Exception:
            return
        try:
            from salon_settings import get_settings as _gs
            cfg = _gs()
            if bool(cfg.get("auto_logout", False)):
                idle_limit = self._session_timeout_minutes() * 60
                idle_for = time.monotonic() - getattr(self, "_last_activity_ts", time.monotonic())
                if idle_for >= idle_limit:
                    self.root.after(0, self._logout_due_to_inactivity)
                    return
        except Exception as _se:
            app_log(f"[session_timeout] {_se}")
        try:
            self.root.after(60_000, self._check_session_timeout)
        except Exception:
            return

    def _logout_due_to_inactivity(self):
        try:
            messagebox.showwarning("Session Timeout", "Logged out due to inactivity.")
        except Exception:
            pass
        try:
            from auth import auto_mark_attendance
            username = self.current_user.get("username", "")
            if username:
                auto_mark_attendance(username, "logout")
        except Exception:
            pass
        self._restart_to_login()

    # Ã¢â€â‚¬Ã¢â€â‚¬ BUILD Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
    def _build(self):
        is_owner = self._user_role() == "owner"

        try:
            from salon_settings import get_settings
            _sc = get_settings()
            _ui = float(_sc.get("ui_scale", 1.0))
            _responsive = get_responsive_metrics(self.root)
            _compact = _responsive["mode"] == "compact"
            _sb_w = max(150, int(_responsive["sidebar_w"] * _ui))
        except Exception:
            _ui   = 1.0
            _responsive = {"mode": "medium", "sidebar_w": 190, "padding": 8}
            _compact = False
            _sb_w = 180

        nav_font_sz = max(9, int((_responsive["font_sz"] + 1) * _ui))
        nav_padx    = max(8, int((_responsive["padding"] + 6) * _ui))
        nav_pady    = max(4, int((_responsive["padding"] + (0 if _compact else 2)) * _ui))
        sidebar_btn_h = max(28, int((_responsive["btn_h"] + (-2 if _compact else 0)) * _ui))
        user_btn_w = max(124, _sb_w - 24)
        self._nav_font_sz = nav_font_sz
        self._sidebar_width = _sb_w

        # Ã¢â€â‚¬Ã¢â€â‚¬ SIDEBAR Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
        sb = tk.Frame(self.root, bg=C["sidebar"], width=_sb_w)
        sb.pack(side=tk.LEFT, fill=tk.Y)
        sb.pack_propagate(False)
        self.sidebar = sb

        sb_canvas = tk.Canvas(
            sb,
            bg=C["sidebar"],
            highlightthickness=0,
            bd=0,
            width=_sb_w,
        )
        sb_scroll = ttk.Scrollbar(sb, orient="vertical", command=sb_canvas.yview)
        sb_canvas.configure(yscrollcommand=sb_scroll.set)
        sb_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        sb_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb_body = tk.Frame(sb_canvas, bg=C["sidebar"])
        sb_window = sb_canvas.create_window((0, 0), window=sb_body, anchor="nw", width=_sb_w)
        sb_body.bind("<Configure>", lambda e: sb_canvas.configure(scrollregion=sb_canvas.bbox("all")))
        sb_canvas.bind("<Configure>", lambda e: sb_canvas.itemconfigure(sb_window, width=e.width))

        def _sb_mousewheel(event):
            try:
                sb_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except Exception:
                pass

        sb_canvas.bind("<Enter>", lambda e: sb_canvas.bind_all("<MouseWheel>", _sb_mousewheel))
        sb_canvas.bind("<Leave>", lambda e: sb_canvas.unbind_all("<MouseWheel>"))
        self._sidebar_canvas = sb_canvas
        self._sidebar_window = sb_window
        self._sidebar_body = sb_body

        logo_f = tk.Frame(sb_body, bg=C["sidebar"], pady=(12 if _compact else 16))
        logo_f.pack(fill=tk.X)
        try:
            from PIL import Image, ImageTk
            img = Image.open(get_branding_logo_path("sidebar")).convert("RGBA")
            bb  = img.getbbox()
            if bb: img = img.crop(bb)
            logo_w = min(148 if not _compact else 122, _sb_w - 20)
            logo_h = int(img.size[1] * logo_w / img.size[0])
            self._logo = ImageTk.PhotoImage(img.resize((logo_w, logo_h)))
            tk.Label(logo_f, image=self._logo,
                     bg=C["sidebar"]).pack(padx=10)
        except Exception:
            tk.Label(logo_f, text=get_sidebar_title().upper(),
                     font=("Arial", 12 if _compact else 13, "bold"),
                     bg=C["sidebar"], fg=C["accent"]).pack(pady=4)

        # UI v3 Ã¢â‚¬â€ accent separator under logo
        tk.Frame(sb_body, bg=C["accent"], height=1).pack(
            fill=tk.X, padx=16, pady=(0, 8))

        # Ã¢â€â‚¬Ã¢â€â‚¬ NAV ITEMS (UI v3 Ã¢â‚¬â€ rounded hover pill) Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
        self._page_icons = {}
        self._action_icons = {}
        nav_host = tk.Frame(sb_body, bg=C["sidebar"])
        nav_host.pack(fill=tk.X)

        for _, label, key, allowed_roles in self.NAV:
            if not self._has_access(("", label, key, allowed_roles)):
                continue

            row = tk.Frame(nav_host, bg=C["sidebar"])
            row.pack(fill=tk.X, pady=1)

            # Active accent strip Ã¢â‚¬â€ 4px wide (v3: slightly thicker)
            strip = tk.Frame(row, bg=C["sidebar"], width=4)
            strip.pack(side=tk.LEFT, fill=tk.Y)

            nav_icon = get_nav_icon(key)
            if nav_icon:
                self._page_icons[key] = nav_icon

            btn = tk.Button(
                row,
                text=f" {label}",
                image=nav_icon,
                compound="left",
                command=lambda k=key: self.switch_to(k),
                bg=C["sidebar"], fg=C["muted"],
                font=("Arial", nav_font_sz), bd=0,
                anchor="w",
                padx=nav_padx, pady=nav_pady,
                cursor="hand2",
                activebackground=C["bg"],
                activeforeground=C["text"],
                relief="flat")
            btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
            btn.image = nav_icon

            def _on_enter(e, b=btn, s=strip, r=row):
                if b.cget("bg") != C["bg"]:
                    # v3: hover Ã¢â‚¬â€ subtle bg tint + muted strip
                    b.configure(fg=C["text"])
                    s.configure(bg=C["teal"])
                    r.configure(bg=C["sidebar"])

            def _on_leave(e, b=btn, s=strip, r=row):
                if b.cget("bg") != C["bg"]:
                    b.configure(fg=C["muted"])
                    s.configure(bg=C["sidebar"])
                    r.configure(bg=C["sidebar"])

            btn.bind("<Enter>", _on_enter)
            btn.bind("<Leave>", _on_leave)

            self._nav_btns[key]   = btn
            self._nav_strips[key] = strip
            self._nav_rows[key] = row

            if key == "ai_assistant" and not self._feature_enabled("ai_assistant"):
                row.pack_forget()

        tk.Frame(sb_body, bg=C["sidebar"], height=max(8, nav_pady)).pack(fill=tk.X)
        tk.Frame(sb_body, bg=C["sidebar"], height=1).pack(
            fill=tk.X, padx=16, pady=(0, 6))

        # UI v3 Ã¢â‚¬â€ user section separator
        tk.Frame(sb_body, bg=C["sidebar"], height=1).pack(
            fill=tk.X, padx=16, pady=(0, 0))
        tk.Frame(sb_body, bg=C["accent"], height=1).pack(
            fill=tk.X, padx=16, pady=(0, 6))

        ub = tk.Frame(sb_body, bg=C["sidebar"], pady=(8 if _compact else 10))
        ub.pack(fill=tk.X)

        ua = tk.Frame(ub, bg=C["sidebar"])
        ua.pack(fill=tk.X, padx=14, pady=(0, 8))

        # Avatar circle (initial letter)
        uname = self.current_user.get("name", "U")
        avatar_lbl = tk.Label(ua,
                 text=uname[0].upper() if uname else "U",
                 font=("Arial", 13, "bold"),
                 bg=C["teal"], fg="white",
                 width=2, relief="flat")
        avatar_lbl.pack(side=tk.LEFT)

        ui = tk.Frame(ua, bg=C["sidebar"])
        ui.pack(side=tk.LEFT, padx=(8, 0))

        tk.Label(ui,
                 text=uname,
                 font=("Arial", 11, "bold"),
                 bg=C["sidebar"], fg=C["text"],
                 anchor="w").pack(anchor="w")

        # Role pill badge (v3)
        role     = self.current_user.get("role", "staff").upper()
        role_col = C["accent"] if role == "OWNER" else C["blue"]
        tk.Label(ui,
                 text=f"  {role}  ",
                 font=("Arial", 8, "bold"),
                 bg=role_col, fg="white",
                 relief="flat").pack(anchor="w", pady=(2, 0))

        # Logout Ã¢â‚¬â€ ModernButton rounded (v3)
        logout_icon = get_action_icon("logout")
        if logout_icon:
            self._action_icons["logout"] = logout_icon

        btn_logout = ModernButton(
                 ub,
                 text="Logout",
                 image=logout_icon,
                 compound="left",
                 command=self._logout,
                 color=C["red"],
                 hover_color="#c0392b",
                 width=user_btn_w,
                 height=sidebar_btn_h,
                 radius=8,
                 font=("Arial", max(9, nav_font_sz - 1), "bold")
                 )

        btn_logout.pack(padx=12, pady=(0, 4))
        btn_logout.pack_configure(pady=(0, 8))

        # Ã¢â€â‚¬Ã¢â€â‚¬ TOP BAR (UI v3) Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
        tb = tk.Frame(self.root, bg=C["card"], pady=6)
        tb.pack(side=tk.TOP, fill=tk.X)
        self.top_bar = tb

        # Left Ã¢â‚¬â€ breadcrumb style page title
        title_f = tk.Frame(tb, bg=C["card"])
        title_f.pack(side=tk.LEFT, padx=20)
        tk.Label(title_f, text=get_sidebar_title(),
                 font=("Arial", 10),
                 bg=C["card"], fg=C["muted"]).pack(side=tk.LEFT)
        tk.Label(title_f, text="  /  ",
                 font=("Arial", 10),
                 bg=C["card"], fg=C["sidebar"]).pack(side=tk.LEFT)
        self.page_icon = tk.Label(
            title_f,
            bg=C["card"],
            bd=0
        )
        self.page_icon.pack(side=tk.LEFT, padx=(0, 6))
        self.page_title = tk.Label(
            title_f, text="",
            font=("Arial", 12, "bold"),
            bg=C["card"], fg=C["text"])
        self.page_title.pack(side=tk.LEFT)

        # Right Ã¢â‚¬â€ Today revenue pill
        self.today_lbl = tk.Label(
            tb, text="",
            font=("Arial", 10, "bold"),
            bg=C["teal"], fg="white",
            padx=12, pady=4, relief="flat")
        self.today_lbl.pack(side=tk.RIGHT, padx=(0, 14))
        self._refresh_today()

        # Admin button (owner only) Ã¢â‚¬â€ ModernButton v3
        is_owner = self.current_user.get("role") == "owner"
        if is_owner:
            admin_icon = get_action_icon("admin")
            if admin_icon:
                self._action_icons["admin"] = admin_icon
            ModernButton(tb, text="Admin",
                         image=admin_icon,
                         compound="left",
                         command=self._open_admin,
                         color=C["red"], hover_color="#c0392b",
                         width=100, height=30, radius=8,
                         font=("Arial", 10, "bold"),
                         ).pack(side=tk.RIGHT, padx=(0, 6), pady=5)

        help_icon = get_action_icon("help")
        if help_icon:
            self._action_icons["help"] = help_icon
        ModernButton(tb, text="Help",
                     image=help_icon,
                     compound="left",
                     command=self._show_context_help,
                     color=C["blue"], hover_color="#154360",
                     width=90, height=30, radius=8,
                     font=("Arial", 10, "bold"),
                     ).pack(side=tk.RIGHT, padx=(0, 6), pady=5)

        # Bell Ã¢â‚¬â€ notification button
        alerts_icon = get_action_icon("alerts")
        if alerts_icon:
            self._action_icons["alerts"] = alerts_icon
        btn_bell = ModernButton(
            tb, text="Notifications",
            image=alerts_icon,
            compound="left",
            command=self._show_notifications,
            color="#D4A017", hover_color="#C58F00",
            width=160, height=30, radius=8,
            font=("Arial", 10, "bold"),
        )
        btn_bell.pack(side=tk.RIGHT, padx=(0, 4), pady=5)
        self.btn_notifications = btn_bell
        self._update_notification_button()

        # Thin accent line under top bar
        tk.Frame(self.root, bg=C["sidebar"], height=1).pack(
            side=tk.TOP, fill=tk.X)

        # Ã¢â€â‚¬Ã¢â€â‚¬ SIDEBAR DRAG DIVIDER Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
        sb_divider = tk.Frame(
            self.root, bg=C["sidebar"], width=4,
            cursor="sb_h_double_arrow")
        sb_divider.pack(side=tk.LEFT, fill=tk.Y)

        def _sb_drag(e):
            min_sidebar = max(140, _responsive["sidebar_w"] - 30)
            max_sidebar = max(260, _responsive["sidebar_w"] + 80)
            new_w = max(min_sidebar, min(max_sidebar, e.x_root - self.root.winfo_rootx()))
            sb.configure(width=new_w)
            try:
                sb_canvas.configure(width=new_w)
                sb_canvas.itemconfigure(sb_window, width=new_w)
            except Exception:
                pass

        sb_divider.bind("<B1-Motion>", _sb_drag)
        sb_divider.bind("<Enter>",
                        lambda e: sb_divider.configure(bg=C["accent"]))
        sb_divider.bind("<Leave>",
                        lambda e: sb_divider.configure(bg=C["sidebar"]))

        # Ã¢â€â‚¬Ã¢â€â‚¬ CONTENT AREA Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
        self.content = tk.Frame(self.root, bg=C["bg"])
        self.content.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self._init_modules()

    def _init_modules(self):
        module_specs = {
            "dashboard":      ("dashboard", "DashboardFrame"),
            "billing":        ("billing", "BillingFrame"),
            "customers":      ("customers", "CustomersFrame"),
            "appointments":   ("booking_calendar", "BookingCalendarFrame"),
            "membership":     ("membership", "MembershipFrame"),
            "offers":         ("offers", "OffersFrame"),
            "redeem_codes":   ("redeem_codes", "RedeemCodesFrame"),
            "cloud_sync":     ("cloud_sync", "CloudSyncFrame"),
            "staff":          ("staff", "StaffFrame"),
            "inventory":      ("inventory", "InventoryFrame"),
            "expenses":       ("expenses", "ExpensesFrame"),
            "whatsapp_bulk":  ("whatsapp_bulk", "WhatsAppBulkFrame"),
            "reports":        ("reports", "ReportsFrame"),
            "accounting":     ("accounting", "AccountingFrame"),
            "closing_report": ("closing_report", "ClosingReportFrame"),
            "settings":       ("salon_settings", "SettingsFrame"),
        }
        self.module_specs = module_specs
        self.module_classes = {}
        self.billing_frame = None

    # Ã¢â€â‚¬Ã¢â€â‚¬ NAVIGATION Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
    def _show_startup_placeholder(self, parent=None):
        parent = parent or self.content
        placeholder = tk.Frame(parent, bg=C["bg"])
        center = tk.Frame(placeholder, bg=C["bg"])
        center.pack(expand=True)
        self._startup_media_frames = []
        self._startup_media_label = None
        self._startup_logo_img = None
        self._startup_logo_label = None
        self._startup_logo_base = None

        try:
            from PIL import Image, ImageTk
            img = Image.open(get_branding_logo_path("main")).convert("RGBA")
            bb = img.getbbox()
            if bb:
                img = img.crop(bb)
            screen_w = max(1, self.root.winfo_screenwidth())
            screen_h = max(1, self.root.winfo_screenheight())
            target_w = max(260, int(screen_w * 0.24))
            target_h_cap = max(140, int(screen_h * 0.20))
            w = min(target_w, img.size[0], 480)
            h = max(1, int(img.size[1] * w / max(1, img.size[0])))
            if h > target_h_cap:
                h = target_h_cap
                w = max(1, int(img.size[0] * h / max(1, img.size[1])))
            self._startup_logo_base = img.resize((w, h))
            self._startup_logo_img = ImageTk.PhotoImage(self._startup_logo_base)
            logo_lbl = tk.Label(
                center,
                image=self._startup_logo_img,
                bg=C["bg"],
                bd=0
            )
            logo_lbl.pack(pady=(0, 14))
            logo_lbl.image = self._startup_logo_img
            self._startup_logo_label = logo_lbl
            self.root.after(60, self._animate_startup_logo)
        except Exception:
            tk.Label(
                center,
                text=get_short_name(),
                bg=C["bg"],
                fg=C["accent"],
                font=("Arial", 24, "bold")
            ).pack(pady=(0, 10))

        label = tk.Label(
            center,
            text="Loading.",
            bg=C["bg"],
            fg=C["muted"],
            font=("Arial", 14, "bold")
        )
        label.pack()
        tk.Label(
            center,
            text="Preparing your workspace",
            bg=C["bg"],
            fg=C["muted"],
            font=("Arial", 10)
        ).pack(pady=(6, 0))
        placeholder.place(x=0, y=0, relwidth=1, relheight=1)
        self._startup_placeholder = placeholder
        self._startup_placeholder_label = label
        self.root.after(30, self._animate_loading_placeholder)
        self.root.after(40, self._animate_loading_text)

    def _on_root_map(self, event=None):
        if getattr(event, "widget", None) is not self.root:
            return
        if not self.root.winfo_ismapped():
            return
        self.root.after_idle(self._restore_visible_page)

    def _on_window_resize(self, event=None):
        """Phase 3 FIX: debounced window resize handler."""
        if event is None or getattr(event, "widget", None) is self.root:
            if self._resize_after_id is not None:
                try:
                    self.root.after_cancel(self._resize_after_id)
                except Exception:
                    pass
            self._resize_after_id = self.root.after(
                self._resize_debounce_ms, self._handle_resize)

    def _handle_resize(self):
        """Called after debounce when window is resized."""
        self._resize_after_id = None
        try:
            from ui_responsive import initialize_responsive
            initialize_responsive(self.root)
            refresh_fonts()
            key = self.current_page_key
            if key:
                frame = self.frames.get(key)
                if frame and hasattr(frame, "refresh"):
                    frame.refresh()
        except Exception:
            pass

    def _restore_visible_page(self):
        key = self.current_page_key
        if not key:
            return
        frame = self.frames.get(key)
        if not frame:
            return
        try:
            frame.place(x=0, y=0, relwidth=1, relheight=1)
            frame.lift()
            self.root.update_idletasks()
        except Exception:
            pass

    def _ensure_frame(self, key: str):
        if key in self.frames:
            return self.frames[key]
        try:
            t0 = time.perf_counter()
            Cls = self.module_classes.get(key)
            if Cls is None:
                if key == "ai_assistant":
                    if not self._feature_enabled("ai_assistant"):
                        return None
                    if AI_AVAILABLE and not self.ai_ctrl:
                        try:
                            from salon_settings import get_settings as _gs
                            _ai_cfg = _gs().get("ai_config", {})
                            self.ai_ctrl = AIController(
                                app_ref=self,
                                api_key=load_ai_api_key(_ai_cfg))
                            self.ai_ctrl.toggle_ai(_ai_cfg.get("enabled", True))
                        except Exception as _aie:
                            app_log(f"[_ensure_frame ai init] {_aie}")
                    if self.ai_ctrl and AI_AVAILABLE:
                        from ai_assistant.ui.ai_chat_window import AIChatFrame
                        _ctrl = self.ai_ctrl

                        class _AITab(AIChatFrame):
                            def __init__(self_w, parent, app_ref=None):
                                super().__init__(parent, _ctrl)

                        Cls = _AITab
                    else:
                        placeholder = tk.Frame(self.content, bg=C["bg"])
                        tk.Label(
                            placeholder,
                            text="AI Assistant is enabled, but the runtime is not ready.\nOpen Settings and save the AI section once, then try again.",
                            bg=C["bg"], fg=C["orange"],
                            font=("Arial", 11), justify="center").pack(expand=True)
                        placeholder.place(x=0, y=0, relwidth=1, relheight=1)
                        self.frames[key] = placeholder
                        return placeholder
                else:
                    spec = self.module_specs.get(key)
                    if spec is None:
                        return None
                    module_name, class_name = spec
                    try:
                        mod = importlib.import_module(module_name)
                        Cls = getattr(mod, class_name)
                    except Exception as _ie:
                        app_log(f"[_ensure_frame import {module_name}] {_ie}")
                        raise
                self.module_classes[key] = Cls

            f = Cls(self.content, self)
            f.place(x=0, y=0, relwidth=1, relheight=1)
            self.frames[key] = f
            if key == "billing":
                self.billing_frame = f
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            app_log(f"[_ensure_frame {key}] loaded in {elapsed_ms}ms")
            return f
        except Exception as e:
            placeholder = tk.Frame(self.content, bg=C["bg"])
            tk.Label(
                placeholder,
                text=f"Module '{key}' failed to load:\n{e}",
                bg=C["bg"], fg=C["red"],
                font=("Arial", 11)).pack(expand=True)
            placeholder.place(x=0, y=0, relwidth=1, relheight=1)
            self.frames[key] = placeholder
            app_log(f"[Module Error] {key}: {e}")
            return placeholder

    def switch_to(self, key: str):
        entry = next((e for e in self.NAV if e[2] == key), None)
        if entry and not self._has_access(entry):
            messagebox.showerror(
                "Access Denied",
                f"{entry[1]} access is restricted for your role.")
            return
        frame = self._ensure_frame(key)
        if frame is None:
            return

        placeholder = getattr(self, "_startup_placeholder", None)
        if placeholder is not None:
            try:
                if placeholder.winfo_exists():
                    placeholder.destroy()
            except Exception:
                pass
            self._startup_placeholder = None
            self._startup_placeholder_label = None
            self._startup_media_label = None
            self._startup_media_frames = []

        for frame_key, other in self.frames.items():
            try:
                if frame_key == key:
                    other.place(x=0, y=0, relwidth=1, relheight=1)
                else:
                    other.place_forget()
            except Exception:
                pass

        frame.lift()
        self.current_page_key = key
        self._animate_page_reveal()

        for k, btn in self._nav_btns.items():
            active = (k == key)
            # UI v3 Ã¢â‚¬â€ active: accent bg tint + bold + 4px accent strip
            btn.config(
                bg     = C["bg"]     if active else C["sidebar"],
                fg     = C["accent"] if active else C["muted"],
                font   = ("Arial", getattr(self, "_nav_font_sz", 11), "bold" if active else "normal"),
                relief = "flat")
            if k in self._nav_strips:
                self._nav_strips[k].configure(
                    bg    = C["accent"] if active else C["sidebar"],
                    width = 4)

        if entry:
            page_icon = self._page_icons.get(key)
            self.page_title.config(text=entry[1])
            self.page_icon.config(image=page_icon)
            self.page_icon.image = page_icon

        try:
            if hasattr(frame, "refresh"):
                frame.refresh()
        except Exception:
            pass

        self._refresh_today()

    # Ã¢â€â‚¬Ã¢â€â‚¬ EVENTS Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
    def on_bill_saved(self):
        try:
            inventory_frame = self.frames.get("inventory")
            if inventory_frame is not None:
                inventory_frame._force_next_refresh = True
        except Exception:
            pass
        self._refresh_today(force=True)

    def _refresh_today(self, force: bool = False):
        try:
            now_ts = time.monotonic()
            last_ts = getattr(self, "_today_refresh_last_ts", 0.0)
            if not force and last_ts and (now_ts - last_ts) < 30:
                return
            self._today_refresh_last_ts = now_ts
            td  = today_str()
            tot = 0.0
            if os.path.exists(F_REPORT):
                # Phase 3 FIX: use cached report source instead of raw CSV read
                from reports_data import read_report_rows
                rows = read_report_rows(td, td)
                for r in rows:
                    tot += safe_float(r.get("total", 0))
            self.today_lbl.config(text=f"Today: {fmt_currency(tot)}")
        except Exception as e:
            app_log(f"[_refresh_today] {e}")  # Fix M3f

    def _notification_count(self) -> int:
        try:
            from notifications import get_all_notifications
            return len(get_all_notifications())
        except Exception:
            return 0

    def _update_notification_button(self):
        btn = getattr(self, "btn_notifications", None)
        if not btn:
            return
        count = self._notification_count()
        label = "Notifications"
        if count > 0:
            label = f"Notifications ({count})"
        try:
            btn.set_text(label)
            if count > 0:
                btn.set_color("#D4A017", "#C58F00")
            else:
                btn.set_color("#D4A017", "#C58F00")
        except Exception:
            pass

    def _show_notifications(self, manual: bool = True):
        try:
            from notifications import NotificationPopup, get_all_notifications
            notes = get_all_notifications()
            if not notes:
                if manual:
                    messagebox.showinfo("Notifications", "No new notifications.")
                self._update_notification_button()
                return
            NotificationPopup(self.root, notes=notes)
            self._update_notification_button()
        except Exception as e:
            app_log(f"[_show_notifications] {e}")  # Fix M3d

    def _show_context_help(self):
        try:
            show_context_help(self.root, self.current_page_key or "dashboard")
        except Exception as e:
            app_log(f"[_show_context_help] {e}")

    # Ã¢â€â‚¬Ã¢â€â‚¬ SMART APPOINTMENT REMINDER LOOP Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
    def _check_appointment_reminders(self):
        """
        Called once 2 s after startup, then rescheduled every 5 minutes.

        Logic:
          1. Ask appointments.py for reminders that are currently due.
          2. Show one non-blocking popup per due appointment.
          3. Reschedule itself for the next cycle regardless of outcome.

        All error handling is defensive Ã¢â‚¬â€ a crash here must NEVER bring
        down the rest of the application.
        """
        if not getattr(self, "root", None):
            return
        try:
            if not int(self.root.winfo_exists()):
                return
        except Exception:
            return
        try:
            from appointments import (get_due_appointment_reminders,
                                      show_appointment_popup)
            due = get_due_appointment_reminders()
            for appt in due:
                # Small stagger between popups so they don't all appear
                # on the exact same pixel (100 ms offset per popup)
                delay = due.index(appt) * 100
                try:
                    self.root.after(
                        delay,
                        lambda a=appt: show_appointment_popup(self.root, a)
                    )
                except Exception:
                    return
        except Exception as exc:
            # Log but never crash Ã¢â‚¬â€ the reminder loop is non-critical
            app_log(f"[_check_appointment_reminders] {exc}")  # Fix M3e

        # Always reschedule Ã¢â‚¬â€ loop runs forever while the app is open
        try:
            self.root.after(self._REMINDER_INTERVAL_MS,
                            self._check_appointment_reminders)
        except Exception:
            return

    def _open_admin(self):
        """
        Bug 11 fix: prevent duplicate admin panel windows.
        Bug 12 fix: pass current_user to AdminPanel.
        """
        if not self.require_permission("admin_panel", "Admin Panel"):
            return
        if self._admin_panel is not None:
            try:
                self._admin_panel.win.lift()
                self._admin_panel.win.focus_set()
                return
            except Exception:
                self._admin_panel = None

        from admin import AdminPanel

        def _on_admin_close():
            self._admin_panel = None
            if self.billing_frame:
                try:
                    self.billing_frame.reload_services()
                except Exception:
                    pass

        self._admin_panel = AdminPanel(
            self.root,
            on_close=_on_admin_close,
            current_user=self.current_user,
        )

    def _mark_current_user_logout_attendance(self):
        try:
            from auth import auto_mark_attendance
            username = self.current_user.get("username", "")
            if username:
                auto_mark_attendance(username, "logout")
        except Exception:
            pass

    def _logout(self):
        if messagebox.askyesno("Logout", "Logout?"):
            # V5.6.1 Phase 1 — Activity log
            try:
                from activity_log import log_event
                user = self.current_user.get("username", "")
                log_event(
                    "logout",
                    entity="auth",
                    entity_id=user,
                    user=user,
                )
            except Exception:
                pass
            self._mark_current_user_logout_attendance()
            _relaunch_current_app()
            self._shutdown_app()

    def _switch_user(self):
        self._logout()


# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
def _start_login():
    while True:
        try:
            clear_icon_cache()
        except Exception:
            pass
        app_log("[startup] login window launch", "info")
        login = LoginWindow()
        user = getattr(login, "logged_in_user", None)
        if not user:
            app_log("[startup] login cancelled by user", "info")
            sys.exit(0)
        try:
            clear_icon_cache()
        except Exception:
            pass
        app_log(f"[startup] launching main app for user={user.get('username', '')}", "info")
        app = SalonApp(user)
        if not getattr(app, "_restart_login_requested", False):
            app_log("[startup] main app session completed", "info")
            break
        app_log("[startup] restart-login requested", "info")


if __name__ == "__main__":
    _install_global_exception_hooks()
    app_log("[startup] app entry", "info")

    # Apply saved theme FIRST
    try:
        from salon_settings import get_settings, apply_theme
        _cfg         = get_settings()
        _saved_theme = _cfg.get("theme", "dark")
        apply_theme(_saved_theme)
    except Exception as _te:
        app_log(f"[Theme] Could not apply: {_te}")

    init_services_db()

    # Fix M3a + M3g: initialise SQLite DB + auto-migrate JSON on first run
    try:
        from db import ensure_migrated
        ensure_migrated()
    except Exception as _dbe:
        app_log(f"[startup] db ensure_migrated failed: {_dbe}")

    try:
        from migrations.migration_runner import bootstrap_v5_foundation
        bootstrap_v5_foundation()
    except Exception as _v5e:
        app_log(f"[startup] v5 foundation bootstrap failed: {_v5e}")

    try:
        initialize_runtime_migration_state()
    except Exception as _mse:
        app_log(f"[startup] migration state init failed: {_mse}")

    # V5.6.1 Phase 1 — Start scheduled backup thread
    try:
        from scheduled_backup import start_scheduler
        start_scheduler()
    except Exception as _sb:
        app_log(f"[startup] scheduled backup start failed: {_sb}")

    try:
        from utils import init_sample_data
        init_sample_data()
    except Exception:
        pass

    try:
        licensing_ok = _run_startup_step("licensing gate", ensure_startup_access)
    except Exception:
        _log_exception("[startup] licensing gate failure")
        _show_fatal_error_dialog(
            "License Check Error",
            "The app could not complete the license check.\n\n"
            "Please restart the app.\n"
            "If the issue repeats, check app_debug.log.",
        )
        sys.exit(1)
    if not licensing_ok:
        app_log("[startup] blocked by licensing gate", "warning")
        sys.exit(0)

    # C2 FIX: First-run wizard replaces hardcoded admin/admin123.
    # On a fresh install with no users, show the setup dialog.
    try:
        from auth import is_first_run, show_first_run_setup
        if is_first_run():
            app_log("[startup] First-run setup wizard launched.")
            first_user = _run_startup_step("first-run setup", show_first_run_setup)
            if first_user is None:
                # User closed the wizard without setup -- exit gracefully
                app_log("[startup] User cancelled first-run setup.")
                sys.exit(0)
            # If first-run succeeded, use that user directly
            try:
                clear_icon_cache()
            except Exception:
                pass
            app = _run_startup_step(
                "first-run app launch",
                lambda: SalonApp(first_user),
            )
            if not getattr(app, "_restart_login_requested", False):
                pass  # proceed normally
            sys.exit(0)
    except Exception as _fre:
        app_log(f"[startup] First-run setup failed: {_fre}, falling back to login.")

    try:
        _run_startup_step("login/startup loop", _start_login)
    except SystemExit:
        raise
    except Exception:
        _log_exception("[startup] fatal startup failure")
        _show_fatal_error_dialog(
            "Startup Error",
            "The app could not finish startup.\n\n"
            "Please restart the app.\n"
            "If the issue repeats, check app_debug.log.",
        )
        sys.exit(1)
