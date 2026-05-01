from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import tkinter as tk
import traceback
from tkinter import messagebox
from typing import Callable, TypeVar

from utils import app_log

T = TypeVar("T")


def _enable_windows_dpi_awareness() -> None:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def _current_entry_file() -> str:
    main_module = sys.modules.get("__main__")
    main_file = getattr(main_module, "__file__", None)
    if main_file:
        return os.path.abspath(main_file)
    return os.path.abspath(__file__)


def _relaunch_current_app(main_file: str | None = None) -> bool:
    try:
        if getattr(sys, "frozen", False):
            target = sys.executable
            if target:
                subprocess.Popen([target], close_fds=True)
                return True
        target_file = os.path.abspath(main_file) if main_file else _current_entry_file()
        python_exe = sys.executable or "python"
        subprocess.Popen([python_exe, target_file], close_fds=True)
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


def _run_startup_step(label: str, func: Callable[[], T]) -> T:
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
