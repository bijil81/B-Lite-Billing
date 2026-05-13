from pathlib import Path

from ui_responsive import _is_dropdown_wheel_target, _wheel_scroll_units


ROOT = Path(__file__).resolve().parents[1]


def test_wheel_delta_normalization_supports_precision_touchpads():
    assert _wheel_scroll_units(120) == -1
    assert _wheel_scroll_units(-120) == 1
    assert _wheel_scroll_units(60) == -1
    assert _wheel_scroll_units(-60) == 1
    assert _wheel_scroll_units(240) == -2
    assert _wheel_scroll_units(0) == 0


class _FakeWidget:
    def __init__(self, widget_class: str, path: str):
        self._widget_class = widget_class
        self._path = path

    def winfo_class(self):
        return self._widget_class

    def __str__(self):
        return self._path


def test_dropdown_mousewheel_targets_do_not_scroll_parent_page():
    assert _is_dropdown_wheel_target(_FakeWidget("TCombobox", ".app.combo"))
    assert _is_dropdown_wheel_target(
        _FakeWidget("Listbox", ".app.combo.popdown.f.l")
    )
    assert not _is_dropdown_wheel_target(_FakeWidget("Listbox", ".app.items"))
    assert not _is_dropdown_wheel_target(_FakeWidget("Frame", ".app.page"))


def test_sidebar_does_not_override_global_mousewheel_bindings():
    source = (ROOT / "main.py").read_text(encoding="utf-8", errors="ignore")
    assert "_bind_mousewheel(sb_canvas, sb_body)" in source
    assert 'bind_all("<MouseWheel>"' not in source
    assert "unbind_all(\"<MouseWheel>\")" not in source


def test_settings_and_billing_use_common_mousewheel_helper():
    settings_source = (ROOT / "salon_settings.py").read_text(encoding="utf-8", errors="ignore")
    billing_sections_source = (
        ROOT / "src" / "blite_v6" / "billing" / "ui_sections.py"
    ).read_text(encoding="utf-8", errors="ignore")
    assert "_bind_mousewheel(c, f)" in settings_source
    assert "_bind_mousewheel(canvas, body)" in billing_sections_source
