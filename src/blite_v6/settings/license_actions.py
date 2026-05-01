from __future__ import annotations

from typing import Mapping


def license_activation_action_view(status: Mapping) -> dict[str, object]:
    if status.get("activation_disabled"):
        return {
            "text": "Activation Disabled",
            "enabled": False,
            "color": "#ef4444",
        }
    if status.get("activated"):
        return {
            "text": "Activated",
            "enabled": False,
            "color": "#16a34a",
        }
    return {
        "text": "Activate / Extend Trial",
        "enabled": True,
        "color": "#2563eb",
    }
