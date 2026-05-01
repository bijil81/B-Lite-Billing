"""Multi-branch config helpers."""

from __future__ import annotations


def default_multibranch_config() -> dict:
    return {
        "enabled": False,
        "server_url": "",
        "api_key": "",
        "storage": "keyring",
        "shop_id": "",
        "auto_sync": False,
        "sync_interval_minutes": 15,
        "sync_status": "Not Connected",
    }
