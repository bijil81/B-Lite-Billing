from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .core import DEFAULTS, feature_enabled


BASE_SETTINGS_TABS = [
    ("info", "Shop Info"),
    ("theme", "Theme"),
    ("bill", "Bill & GST"),
    ("sec", "Security"),
    ("pref", "Preferences"),
    ("notif", "Notifications"),
    ("backup", "Backup"),
    ("advanced", "Advanced Features"),
    ("license", "Licensing"),
    ("about", "About"),
]

AI_TAB_DEF = ("ai", "AI Assistant")
AI_INSERT_BEFORE_KEY = "advanced"
REQUIRED_SIDEBAR_KEYS = ("dashboard", "billing", "settings")
OPTIONAL_SIDEBAR_MODULES = [
    ("customers", "Customers"),
    ("appointments", "Appointments"),
    ("membership", "Memberships"),
    ("offers", "Offers"),
    ("redeem_codes", "Redeem"),
    ("cloud_sync", "Cloud Sync"),
    ("staff", "Staff"),
    ("inventory", "Inventory"),
    ("expenses", "Expenses"),
    ("whatsapp_bulk", "Bulk WhatsApp"),
    ("reports", "Reports"),
    ("closing_report", "Closing Report"),
]


@dataclass(frozen=True)
class OptionalTabPlan:
    ai_enabled: bool
    ai_key: str = "ai"
    ai_label: str = "AI Assistant"
    insert_before_key: str = AI_INSERT_BEFORE_KEY
    fallback_select_key: str = AI_INSERT_BEFORE_KEY


def settings_tab_defs(settings: Mapping | None = None) -> list[tuple[str, str]]:
    cfg = settings or DEFAULTS
    tabs = list(BASE_SETTINGS_TABS)
    if feature_enabled("ai_assistant", dict(cfg)):
        before_index = next(
            (idx for idx, (key, _label) in enumerate(tabs) if key == AI_INSERT_BEFORE_KEY),
            len(tabs),
        )
        tabs.insert(before_index, AI_TAB_DEF)
    return tabs


def optional_tab_plan(settings: Mapping | None = None) -> OptionalTabPlan:
    cfg = settings or DEFAULTS
    return OptionalTabPlan(ai_enabled=feature_enabled("ai_assistant", dict(cfg)))


def optional_sidebar_module_defs() -> list[tuple[str, str]]:
    return list(OPTIONAL_SIDEBAR_MODULES)


def sidebar_module_enabled(settings: Mapping | None, key: str) -> bool:
    if key in REQUIRED_SIDEBAR_KEYS:
        return True
    if key == "ai_assistant":
        return feature_enabled("ai_assistant", dict(settings or DEFAULTS))
    cfg = dict(settings or DEFAULTS)
    raw = cfg.get("sidebar_module_visibility", {})
    visibility = dict(raw) if isinstance(raw, Mapping) else {}
    return bool(visibility.get(key, True))


def advanced_feature_status_items(
    *,
    ai_enabled: bool,
    mobile_enabled: bool,
    whatsapp_api_enabled: bool,
    multibranch_enabled: bool,
    colors: Mapping[str, str],
) -> list[dict[str, str]]:
    muted = colors["muted"]
    green = colors["green"]
    gold = colors["gold"]
    premium_ready = whatsapp_api_enabled or multibranch_enabled
    return [
        {
            "label": "AI Assistant",
            "state": "ON" if ai_enabled else "OFF",
            "caption": "Sidebar tab and floating AI tools.",
            "color": green if ai_enabled else muted,
        },
        {
            "label": "Mobile Viewer",
            "state": "ON" if mobile_enabled else "OFF",
            "caption": "Optional tab inside Cloud Sync only.",
            "color": green if mobile_enabled else muted,
        },
        {
            "label": "Premium APIs",
            "state": "READY" if premium_ready else "OFF",
            "caption": "Customer-funded optional integrations.",
            "color": gold if premium_ready else muted,
        },
    ]
