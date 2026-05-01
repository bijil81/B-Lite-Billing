from __future__ import annotations

from src.blite_v6.settings.advanced_integrations import (
    ADVANCED_SAVED_MESSAGE,
    AI_MODELS,
    ai_saved_message,
    ai_status_view,
    ai_storage_hint,
    build_advanced_payload,
    build_ai_config,
    build_multibranch_config,
    build_whatsapp_api_config,
    multibranch_status_view,
    normalize_sync_interval_minutes,
    whatsapp_test_message,
    whatsapp_validation_message,
)


COLORS = {
    "green": "green",
    "orange": "orange",
    "red": "red",
    "muted": "muted",
}


def test_whatsapp_messages_and_config_never_persist_secret():
    assert whatsapp_validation_message("meta", True) == "Meta configuration looks ready."
    assert whatsapp_validation_message("twilio", False) == "Twilio is selected, but the API secret is missing."
    assert "Gupshup test-send is scaffolded" in whatsapp_test_message("gupshup")

    cfg = build_whatsapp_api_config(
        enabled=True,
        provider=" meta ",
        fallback_to_selenium=False,
        account_id=" acct ",
        sender_id=" phone ",
        secret_saved=True,
    )

    assert cfg == {
        "enabled": True,
        "provider": "meta",
        "fallback_to_selenium": False,
        "account_id": "acct",
        "sender_id": "phone",
        "api_key": "",
        "storage": "keyring",
    }


def test_multibranch_config_and_status_boundaries():
    assert normalize_sync_interval_minutes("1") == 5
    assert normalize_sync_interval_minutes("bad") == 15
    assert normalize_sync_interval_minutes("30") == 30
    assert multibranch_status_view(True, "ok", "shop-1", COLORS) == (
        "Config Ready (manual server validation pending)",
        "green",
    )
    assert multibranch_status_view(True, "ok", "", COLORS) == ("Missing Shop ID", "orange")
    assert multibranch_status_view(False, "Network failed", "shop-1", COLORS) == ("Network failed", "red")

    cfg = build_multibranch_config(
        enabled=True,
        server_url=" https://sync.example.com ",
        secret_saved=False,
        shop_id=" branch-kochi ",
        auto_sync=True,
        sync_interval_minutes="2",
        sync_status="Status: Ready",
    )

    assert cfg["enabled"] is True
    assert cfg["server_url"] == "https://sync.example.com"
    assert cfg["api_key"] == ""
    assert cfg["storage"] == "unavailable"
    assert cfg["shop_id"] == "branch-kochi"
    assert cfg["auto_sync"] is True
    assert cfg["sync_interval_minutes"] == 5
    assert cfg["sync_status"] == "Ready"


def test_advanced_payload_preserves_settings_and_feature_flags():
    current = {"salon_name": "Demo", "unknown": "keep"}
    wa_cfg = {"enabled": True, "api_key": "", "storage": "keyring"}
    mb_cfg = {"enabled": False, "api_key": "", "storage": "unavailable"}

    result = build_advanced_payload(
        current,
        feature_ai_assistant=True,
        feature_mobile_viewer=False,
        feature_whatsapp_api=True,
        feature_multibranch=False,
        whatsapp_api_config=wa_cfg,
        multibranch_config=mb_cfg,
    )

    assert result["salon_name"] == "Demo"
    assert result["unknown"] == "keep"
    assert result["feature_ai_assistant"] is True
    assert result["feature_mobile_viewer"] is False
    assert result["feature_whatsapp_api"] is True
    assert result["feature_multibranch"] is False
    assert result["whatsapp_api_config"] == wa_cfg
    assert result["multibranch_config"] == mb_cfg
    assert current == {"salon_name": "Demo", "unknown": "keep"}
    assert ADVANCED_SAVED_MESSAGE.startswith("Advanced feature settings saved.")


def test_ai_config_status_messages_and_models():
    assert "claude-sonnet-4-5" in AI_MODELS
    assert ai_storage_hint(True) == "Stored securely using Windows Credential Manager"
    assert "Secure keyring not available" in ai_storage_hint(False)
    assert ai_saved_message(True) == "AI settings saved securely."
    assert "API key was not stored" in ai_saved_message(False)

    cfg = build_ai_config(enabled=True, secure_saved=True, model="claude-sonnet-4-5")
    assert cfg == {
        "enabled": True,
        "api_key": "",
        "storage": "keyring",
        "model": "claude-sonnet-4-5",
    }
    assert ai_status_view(False, "", COLORS) == ("AI is DISABLED", "muted")
    assert ai_status_view(True, "x" * 21, COLORS) == ("API key set -- AI Ready!", "green")
    assert ai_status_view(True, "short", COLORS) == ("Key looks invalid (too short)", "red")
    assert ai_status_view(True, "", COLORS) == ("API key not set", "orange")


def test_salon_settings_imports_phase6_helpers():
    import salon_settings
    from src.blite_v6.settings import advanced_integrations

    assert salon_settings.build_advanced_payload is advanced_integrations.build_advanced_payload
    assert salon_settings.build_ai_config is advanced_integrations.build_ai_config
    assert salon_settings.build_whatsapp_api_config is advanced_integrations.build_whatsapp_api_config
    assert salon_settings.build_multibranch_config is advanced_integrations.build_multibranch_config

