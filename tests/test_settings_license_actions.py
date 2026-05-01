from __future__ import annotations

from src.blite_v6.settings.license_actions import license_activation_action_view


def test_license_action_prompts_only_when_not_activated():
    view = license_activation_action_view({"activated": False, "activation_disabled": False})

    assert view["enabled"] is True
    assert view["text"] == "Activate / Extend Trial"


def test_license_action_becomes_status_when_activated():
    view = license_activation_action_view({"activated": True, "activation_disabled": False})

    assert view["enabled"] is False
    assert view["text"] == "Activated"


def test_license_action_blocks_when_activation_disabled():
    view = license_activation_action_view({"activated": False, "activation_disabled": True})

    assert view["enabled"] is False
    assert view["text"] == "Activation Disabled"
