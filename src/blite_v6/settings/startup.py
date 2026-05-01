from __future__ import annotations

import os
import sys
from pathlib import Path

from branding import get_runtime_app_slug
from utils import app_log


RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"


def default_main_script_path() -> str:
    """Return the V6 project-root main.py path from this extracted module."""
    project_root = Path(__file__).resolve().parents[3]
    return str(project_root / "main.py")


def build_startup_command(executable: str | None = None, main_script: str | None = None) -> str:
    exe = executable or sys.executable
    script = main_script or default_main_script_path()
    return f'"{exe}" "{os.path.abspath(script)}"'


def setup_windows_startup(enable: bool) -> bool:
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            RUN_KEY_PATH,
            0,
            winreg.KEY_SET_VALUE,
        )
        run_value_name = get_runtime_app_slug()
        if enable:
            winreg.SetValueEx(
                key,
                run_value_name,
                0,
                winreg.REG_SZ,
                build_startup_command(),
            )
        else:
            try:
                winreg.DeleteValue(key, run_value_name)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except Exception as exc:
        app_log(f"[Startup] {exc}")
        return False

