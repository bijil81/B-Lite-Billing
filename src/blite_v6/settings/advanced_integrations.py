from __future__ import annotations

from typing import Mapping


AI_MODELS = ["claude-sonnet-4-5", "claude-haiku-4-5-20251001", "claude-opus-4-6"]
ADVANCED_SAVED_MESSAGE = (
    "Advanced feature settings saved.\n\n"
    "AI visibility updates immediately. Other advanced module tabs refresh when reopened."
)


def whatsapp_validation_message(provider_name: str, secret_present: bool) -> str:
    display_name = str(provider_name or "WhatsApp").strip().title()
    if secret_present:
        return f"{display_name} configuration looks ready."
    return f"{display_name} is selected, but the API secret is missing."


def whatsapp_test_message(provider_name: str) -> str:
    display_name = str(provider_name or "WhatsApp").strip().title()
    return (
        f"{display_name} test-send is scaffolded for V5.6.\n"
        "Save credentials first, then complete provider onboarding before production use."
    )


def build_whatsapp_api_config(
    *,
    enabled: bool,
    provider: str,
    fallback_to_selenium: bool,
    account_id: str,
    sender_id: str,
    secret_saved: bool,
) -> dict:
    return {
        "enabled": bool(enabled),
        "provider": str(provider).strip(),
        "fallback_to_selenium": bool(fallback_to_selenium),
        "account_id": str(account_id).strip(),
        "sender_id": str(sender_id).strip(),
        "api_key": "",
        "storage": "keyring" if secret_saved else "unavailable",
    }


def normalize_sync_interval_minutes(value: object, *, default: int = 15, minimum: int = 5) -> int:
    try:
        minutes = int(str(value).strip() or str(default))
    except Exception:
        minutes = default
    return max(minimum, minutes)


def multibranch_status_view(ok: bool, message: str, shop_id: str, colors: Mapping[str, str]) -> tuple[str, str]:
    if ok and str(shop_id).strip():
        return "Config Ready (manual server validation pending)", colors["green"]
    if ok:
        return "Missing Shop ID", colors["orange"]
    return str(message), colors["red"]


def build_multibranch_config(
    *,
    enabled: bool,
    server_url: str,
    secret_saved: bool,
    shop_id: str,
    auto_sync: bool,
    sync_interval_minutes: object,
    sync_status: str,
) -> dict:
    return {
        "enabled": bool(enabled),
        "server_url": str(server_url).strip(),
        "api_key": "",
        "storage": "keyring" if secret_saved else "unavailable",
        "shop_id": str(shop_id).strip(),
        "auto_sync": bool(auto_sync),
        "sync_interval_minutes": normalize_sync_interval_minutes(sync_interval_minutes),
        "sync_status": str(sync_status).replace("Status: ", "", 1),
    }


def build_advanced_payload(
    current_settings: Mapping,
    *,
    feature_ai_assistant: bool,
    feature_mobile_viewer: bool,
    feature_whatsapp_api: bool,
    feature_multibranch: bool,
    whatsapp_api_config: Mapping,
    multibranch_config: Mapping,
) -> dict:
    cfg = dict(current_settings)
    cfg["feature_ai_assistant"] = bool(feature_ai_assistant)
    cfg["feature_mobile_viewer"] = bool(feature_mobile_viewer)
    cfg["feature_whatsapp_api"] = bool(feature_whatsapp_api)
    cfg["feature_multibranch"] = bool(feature_multibranch)
    cfg["whatsapp_api_config"] = dict(whatsapp_api_config)
    cfg["multibranch_config"] = dict(multibranch_config)
    return cfg


def ai_storage_hint(keyring_available: bool) -> str:
    if keyring_available:
        return "Stored securely using Windows Credential Manager"
    return "Secure keyring not available. API keys cannot be stored until Windows Credential Manager support is available."


def build_ai_config(*, enabled: bool, secure_saved: bool, model: str) -> dict:
    return {
        "enabled": bool(enabled),
        "api_key": "",
        "storage": "keyring" if secure_saved else "unavailable",
        "model": str(model),
    }


def ai_saved_message(secure_saved: bool) -> str:
    if secure_saved:
        return "AI settings saved securely."
    return "AI settings saved, but the API key was not stored because secure credential storage is unavailable."


def ai_status_view(enabled: bool, key: str, colors: Mapping[str, str]) -> tuple[str, str]:
    if not enabled:
        return "AI is DISABLED", colors["muted"]
    if len(key) > 20:
        return "API key set -- AI Ready!", colors["green"]
    if key:
        return "Key looks invalid (too short)", colors["red"]
    return "API key not set", colors["orange"]

