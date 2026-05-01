from __future__ import annotations


def test_source_main_py_smoke_defers_unfinished_license_gate(monkeypatch):
    from licensing import ui_gate
    import salon_settings

    monkeypatch.setattr(ui_gate.sys, "frozen", False, raising=False)
    monkeypatch.delenv("BLITE_V6_FORCE_LICENSE", raising=False)
    monkeypatch.setattr(salon_settings, "get_settings", lambda: {"licensing_enforcement_enabled": False})
    monkeypatch.setattr(
        ui_gate,
        "get_license_manager",
        lambda: (_ for _ in ()).throw(AssertionError("license manager should not be called")),
    )

    assert ui_gate.ensure_startup_access() is True
