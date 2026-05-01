"""Helpers for optional WhatsApp API provider settings."""

from __future__ import annotations


def default_api_settings() -> dict:
    return {
        "enabled": False,
        "provider": "meta",
        "fallback_to_selenium": True,
        "account_id": "",
        "sender_id": "",
        "api_key": "",
        "storage": "keyring",
    }
