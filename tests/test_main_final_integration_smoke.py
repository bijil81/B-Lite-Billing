from __future__ import annotations

import importlib

from src.blite_v6.app.app_specs import build_module_specs, build_nav_entries


def test_main_import_and_public_billing_entrypoint_are_available():
    main = importlib.import_module("main")
    billing = importlib.import_module("billing")

    assert hasattr(main, "SalonApp")
    assert hasattr(billing, "BillingFrame")
    assert main.SalonApp.NAV[1][2] == "billing"


def test_main_split_helper_modules_import_without_gui_startup():
    for module_name in [
        "src.blite_v6.app.app_specs",
        "src.blite_v6.app.startup_runtime",
        "src.blite_v6.app.runtime_features",
        "src.blite_v6.app.app_shell",
        "src.blite_v6.app.shell_sections",
        "src.blite_v6.app.navigation",
        "src.blite_v6.app.startup_ui",
        "src.blite_v6.app.session_security",
        "src.blite_v6.app.app_events",
        "theme_tab",
        "salon_info_tab",
        "print_engine",
        "print_utils",
        "adapters.staff_adapter",
        "adapters.report_adapter",
    ]:
        assert importlib.import_module(module_name)


def test_navigation_specs_cover_all_non_special_main_pages():
    nav_keys = {entry[2] for entry in build_nav_entries()}
    module_keys = set(build_module_specs())

    assert "billing" in module_keys
    assert "settings" in module_keys
    assert "ai_assistant" in nav_keys
    assert "ai_assistant" not in module_keys
    assert (nav_keys - {"ai_assistant"}) <= module_keys


def test_license_gate_runs_after_authentication_not_before_login():
    source = open("main.py", encoding="utf-8").read()
    login_loop = source.index("def _start_login")
    post_login_gate = source.index('"post-login licensing gate"')
    login_startup_loop = source.index('"login/startup loop"')

    assert login_loop < post_login_gate < login_startup_loop
    assert '"licensing gate", ensure_startup_access' not in source
