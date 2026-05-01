from __future__ import annotations

from src.blite_v6.settings import core, themes
from utils import C


def test_get_settings_merges_defaults_nested_config_and_legacy_theme(monkeypatch):
    core._invalidate_settings_cache()
    monkeypatch.setattr(core.os.path, "getmtime", lambda _path: 123)
    monkeypatch.setattr(
        core,
        "load_json",
        lambda _path, _default: {
            "theme": "dark",
            "salon_name": "Demo Shop",
            "unknown_custom_key": "keep-me",
            "ai_config": {"model": "custom-model"},
            "whatsapp_api_config": {"provider": "manual"},
        },
    )

    cfg = core.get_settings()

    assert cfg["salon_name"] == "Demo Shop"
    assert cfg["gst_rate"] == core.DEFAULTS["gst_rate"]
    assert cfg["unknown_custom_key"] == "keep-me"
    assert cfg["ai_config"]["model"] == "custom-model"
    assert cfg["ai_config"]["storage"] == core.DEFAULTS["ai_config"]["storage"]
    assert cfg["whatsapp_api_config"]["provider"] == "manual"
    assert cfg["theme"] == "modern_dark"


def test_get_settings_uses_mtime_cache(monkeypatch):
    core._invalidate_settings_cache()
    calls = {"count": 0}

    def fake_load(_path, _default):
        calls["count"] += 1
        return {"salon_name": f"Shop {calls['count']}"}

    monkeypatch.setattr(core.os.path, "getmtime", lambda _path: 55)
    monkeypatch.setattr(core, "load_json", fake_load)

    first = core.get_settings()
    second = core.get_settings()

    assert first is second
    assert second["salon_name"] == "Shop 1"
    assert calls["count"] == 1


def test_save_settings_invalidates_cache_on_success(monkeypatch):
    core._SETTINGS_CACHE = {"mtime": 1, "merged": {"salon_name": "cached"}}
    saved = []

    monkeypatch.setattr(core, "save_json", lambda path, data: saved.append((path, data)) or True)

    assert core.save_settings({"salon_name": "Fresh"}) is True
    assert saved == [(core.F_SETTINGS, {"salon_name": "Fresh"})]
    assert core._SETTINGS_CACHE == {}


def test_feature_enabled_uses_explicit_config_or_default():
    assert core.feature_enabled("ai_assistant", {"feature_ai_assistant": False}) is False
    assert core.feature_enabled("ai_assistant", {}) is True
    assert core.feature_enabled("mobile_viewer", {}) is False


def test_apply_theme_accepts_legacy_keys_and_invalid_falls_back():
    original = dict(C)
    try:
        themes.apply_theme("purple")
        assert C["bg"] == themes.THEMES["premium_salon"]["bg"]
        assert C["accent"] == themes.THEMES["premium_salon"]["accent"]

        themes.apply_theme("missing-theme")
        fallback = themes.THEMES[themes.normalize_theme_key("missing-theme")]
        assert C["bg"] == fallback["bg"]
    finally:
        C.clear()
        C.update(original)


def test_salon_settings_public_api_stays_compatible():
    import salon_settings

    assert salon_settings.DEFAULTS is core.DEFAULTS
    assert salon_settings.THEMES is themes.THEMES
    assert salon_settings.LEGACY_THEME_MAP is themes.LEGACY_THEME_MAP
    assert salon_settings.get_settings is core.get_settings
    assert salon_settings.save_settings is core.save_settings
    assert salon_settings.apply_theme is themes.apply_theme

