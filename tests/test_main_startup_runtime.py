from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from src.blite_v6.app import startup_runtime


def test_run_startup_step_logs_start_and_completion(monkeypatch):
    logs = []
    monkeypatch.setattr(startup_runtime, "app_log", lambda *args: logs.append(args))

    result = startup_runtime._run_startup_step("sample", lambda: "ok")

    assert result == "ok"
    assert logs == [
        ("[startup] sample started", "info"),
        ("[startup] sample completed", "info"),
    ]


def test_run_startup_step_logs_and_reraises_failure(monkeypatch):
    logs = []
    monkeypatch.setattr(startup_runtime, "app_log", lambda *args: logs.append(args))

    with pytest.raises(ValueError):
        startup_runtime._run_startup_step("sample", lambda: (_ for _ in ()).throw(ValueError("bad")))

    assert any("[startup] sample failed" in entry[0] for entry in logs)
    assert any("ValueError: bad" in entry[0] for entry in logs)


def test_run_startup_step_preserves_system_exit(monkeypatch):
    logs = []
    monkeypatch.setattr(startup_runtime, "app_log", lambda *args: logs.append(args))

    with pytest.raises(SystemExit):
        startup_runtime._run_startup_step("sample", lambda: (_ for _ in ()).throw(SystemExit(2)))

    assert logs == [("[startup] sample started", "info")]


def test_relaunch_current_app_uses_explicit_main_file(monkeypatch):
    popen_calls = []
    monkeypatch.setattr(startup_runtime.sys, "frozen", False, raising=False)
    monkeypatch.setattr(startup_runtime.sys, "executable", "python-test")
    monkeypatch.setattr(
        startup_runtime.subprocess,
        "Popen",
        lambda args, close_fds: popen_calls.append((args, close_fds)),
    )

    assert startup_runtime._relaunch_current_app("G:\\app\\main.py") is True
    assert popen_calls == [(["python-test", "G:\\app\\main.py"], True)]


def test_relaunch_current_app_uses_main_module_file(monkeypatch):
    popen_calls = []
    fake_main = SimpleNamespace(__file__="G:\\app\\main.py")
    monkeypatch.setitem(sys.modules, "__main__", fake_main)
    monkeypatch.setattr(startup_runtime.sys, "frozen", False, raising=False)
    monkeypatch.setattr(startup_runtime.sys, "executable", "python-test")
    monkeypatch.setattr(
        startup_runtime.subprocess,
        "Popen",
        lambda args, close_fds: popen_calls.append((args, close_fds)),
    )

    assert startup_runtime._relaunch_current_app() is True
    assert popen_calls == [(["python-test", "G:\\app\\main.py"], True)]
