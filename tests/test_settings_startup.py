from __future__ import annotations

import types

from src.blite_v6.settings import startup


def test_build_startup_command_quotes_executable_and_main_script():
    assert startup.build_startup_command(
        executable=r"C:\Python312\python.exe",
        main_script=r"G:\App Folder\main.py",
    ) == '"C:\\Python312\\python.exe" "G:\\App Folder\\main.py"'


def test_default_main_script_path_points_to_project_root():
    assert startup.default_main_script_path().endswith("B-Lite management_Billing_V6.0\\main.py")


def test_setup_windows_startup_enable_writes_run_value(monkeypatch):
    calls = []

    fake_winreg = types.SimpleNamespace(
        HKEY_CURRENT_USER="HKCU",
        KEY_SET_VALUE="SET",
        REG_SZ="SZ",
        OpenKey=lambda root, path, reserved, access: calls.append(("open", root, path, reserved, access)) or "key",
        SetValueEx=lambda key, name, reserved, reg_type, value: calls.append(
            ("set", key, name, reserved, reg_type, value)
        ),
        DeleteValue=lambda key, name: calls.append(("delete", key, name)),
        CloseKey=lambda key: calls.append(("close", key)),
    )
    monkeypatch.setitem(__import__("sys").modules, "winreg", fake_winreg)
    monkeypatch.setattr(startup, "get_runtime_app_slug", lambda: "BLiteTest")
    monkeypatch.setattr(startup, "build_startup_command", lambda: '"python" "main.py"')

    assert startup.setup_windows_startup(True) is True
    assert ("open", "HKCU", startup.RUN_KEY_PATH, 0, "SET") in calls
    assert ("set", "key", "BLiteTest", 0, "SZ", '"python" "main.py"') in calls
    assert ("close", "key") in calls


def test_setup_windows_startup_disable_deletes_run_value(monkeypatch):
    calls = []

    fake_winreg = types.SimpleNamespace(
        HKEY_CURRENT_USER="HKCU",
        KEY_SET_VALUE="SET",
        REG_SZ="SZ",
        OpenKey=lambda *_args: "key",
        SetValueEx=lambda *_args: calls.append(("set",)),
        DeleteValue=lambda key, name: calls.append(("delete", key, name)),
        CloseKey=lambda key: calls.append(("close", key)),
    )
    monkeypatch.setitem(__import__("sys").modules, "winreg", fake_winreg)
    monkeypatch.setattr(startup, "get_runtime_app_slug", lambda: "BLiteTest")

    assert startup.setup_windows_startup(False) is True
    assert calls == [("delete", "key", "BLiteTest"), ("close", "key")]


def test_setup_windows_startup_disable_ignores_missing_value(monkeypatch):
    calls = []

    def missing_delete(_key, _name):
        raise FileNotFoundError()

    fake_winreg = types.SimpleNamespace(
        HKEY_CURRENT_USER="HKCU",
        KEY_SET_VALUE="SET",
        REG_SZ="SZ",
        OpenKey=lambda *_args: "key",
        SetValueEx=lambda *_args: calls.append(("set",)),
        DeleteValue=missing_delete,
        CloseKey=lambda key: calls.append(("close", key)),
    )
    monkeypatch.setitem(__import__("sys").modules, "winreg", fake_winreg)

    assert startup.setup_windows_startup(False) is True
    assert calls == [("close", "key")]


def test_salon_settings_startup_public_api_stays_compatible():
    import salon_settings

    assert salon_settings.setup_windows_startup is startup.setup_windows_startup

