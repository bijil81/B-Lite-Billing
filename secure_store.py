"""
secure_store.py - secure local credential helpers.
"""
from __future__ import annotations
from branding import get_secure_store_prefix

try:
    import keyring  # type: ignore
    KEYRING_AVAILABLE = True
except Exception:
    keyring = None
    KEYRING_AVAILABLE = False

_PREFIX = get_secure_store_prefix()
AI_SERVICE_NAME = f"{_PREFIX}_AI"
AI_ACCOUNT_NAME = "ai_api_key"
WHATSAPP_SERVICE_NAME = f"{_PREFIX}_WhatsApp"
MULTIBRANCH_SERVICE_NAME = f"{_PREFIX}_MultiBranch"


def _coerce_ai_cfg(settings_or_ai_cfg=None):
    if isinstance(settings_or_ai_cfg, dict):
        if isinstance(settings_or_ai_cfg.get("ai_config"), dict):
            return settings_or_ai_cfg.get("ai_config", {})
        return settings_or_ai_cfg
    return {}


def get_keyring_warning(context: str = "secure credential storage") -> str:
    return (
        f"Windows Credential Manager is unavailable, so {context} cannot be saved securely on this device."
    )


def store_ai_api_key(api_key: str) -> bool:
    api_key = (api_key or "").strip()
    if not KEYRING_AVAILABLE:
        return False
    try:
        keyring.set_password(AI_SERVICE_NAME, AI_ACCOUNT_NAME, api_key)
        return True
    except Exception:
        return False


def load_ai_api_key(settings_or_ai_cfg=None) -> str:
    if KEYRING_AVAILABLE:
        try:
            stored = keyring.get_password(AI_SERVICE_NAME, AI_ACCOUNT_NAME)
            if stored:
                return stored.strip()
        except Exception:
            pass
    return ""


def clear_ai_api_key() -> bool:
    if not KEYRING_AVAILABLE:
        return False
    try:
        keyring.delete_password(AI_SERVICE_NAME, AI_ACCOUNT_NAME)
        return True
    except Exception:
        return False


def store_secret(service_name: str, account_name: str, value: str) -> bool:
    value = (value or "").strip()
    if not KEYRING_AVAILABLE:
        return False
    try:
        keyring.set_password(service_name, account_name, value)
        return True
    except Exception:
        return False


def load_secret(service_name: str, account_name: str, fallback: str = "") -> str:
    if KEYRING_AVAILABLE:
        try:
            stored = keyring.get_password(service_name, account_name)
            if stored:
                return stored.strip()
        except Exception:
            pass
    return ""


def clear_secret(service_name: str, account_name: str) -> bool:
    if not KEYRING_AVAILABLE:
        return False
    try:
        keyring.delete_password(service_name, account_name)
        return True
    except Exception:
        return False


def store_whatsapp_provider_secret(provider_name: str, secret_value: str) -> bool:
    provider = (provider_name or "meta").strip().lower()
    return store_secret(WHATSAPP_SERVICE_NAME, provider, secret_value)


def load_whatsapp_provider_secret(provider_name: str, fallback: str = "") -> str:
    provider = (provider_name or "meta").strip().lower()
    return load_secret(WHATSAPP_SERVICE_NAME, provider, fallback=fallback)


def clear_whatsapp_provider_secret(provider_name: str) -> bool:
    provider = (provider_name or "meta").strip().lower()
    return clear_secret(WHATSAPP_SERVICE_NAME, provider)


def store_multibranch_api_key(secret_value: str) -> bool:
    return store_secret(MULTIBRANCH_SERVICE_NAME, "api_key", secret_value)


def load_multibranch_api_key(fallback: str = "") -> str:
    return load_secret(MULTIBRANCH_SERVICE_NAME, "api_key", fallback=fallback)


def clear_multibranch_api_key() -> bool:
    return clear_secret(MULTIBRANCH_SERVICE_NAME, "api_key")
