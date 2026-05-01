from __future__ import annotations

import os

from branding import (
    get_branding_logo_path,
    get_branding_value,
    get_company_name,
    get_invoice_footer,
)
from ..billing.gst_category_rules import DEFAULT_GST_CATEGORY_RATE_MAP
from .gst_classification_master import normalize_gst_classification_rules
from .gst_master import normalize_gst_category_rate_map
from multibranch.sync_config import default_multibranch_config
from utils import DATA_DIR, load_json, save_json
from whatsapp_api.api_settings import default_api_settings

from .themes import DEFAULT_THEME_KEY, LEGACY_THEME_MAP


F_SETTINGS = os.path.join(DATA_DIR, "salon_settings.json")


DEFAULTS = {
    "salon_name":             get_company_name(),
    "address":                get_branding_value("invoice_address", ""),
    "phone":                  "",
    "gst_no":                 "",
    "bill_footer":            get_invoice_footer(),
    "logo_path":              get_branding_logo_path("main"),
    "currency":               "\u20b9",
    "ui_scale":               1.0,
    "gst_always_on":          False,
    "gst_type":               "inclusive",
    "gst_rate":               18.0,
    "product_wise_gst_enabled": False,
    "gst_rate_source":        "global",
    "missing_item_gst_policy": "global",
    "gst_category_rate_map":  dict(DEFAULT_GST_CATEGORY_RATE_MAP),
    "gst_classification_rules": [],
    "theme":                  DEFAULT_THEME_KEY,
    "default_payment":        "Cash",
    "billing_mode":           "mixed",
    "auto_clear_after_print": False,
    "show_points_on_bill":    True,
    "show_whatsapp_confirm":  True,
    "show_ai_floating_button": True,
    "enable_animations":      True,
    "show_below_cost_alert":  True,
    "use_v5_customers_db":    False,
    "use_v5_appointments_db": False,
    "use_v5_reports_db":      False,
    "use_v5_billing_db":      False,
    "use_v5_inventory_db":    False,
    "use_v5_staff_db":        False,
    "use_v5_product_variants_db": False,
    "show_database_rollout_controls": False,
    "migration_completed":    False,
    "migration_completed_at": "",
    "sqlite_primary_mode":    False,
    "install_mode":           "hybrid",
    "notif_birthday":         True,
    "notif_low_stock":        True,
    "notif_appointments":     True,
    "notif_popup_time":       5,
    "notif_dismissed":        [],
    "update_manifest_url":    "",
    "default_report_period":  "This Month",
    "auto_logout":            False,
    "session_timeout_minutes": 30,
    "require_pw_bill":        False,
    "start_with_windows":     False,
    "last_user":              "admin",
    "country_code":           "91",
    "paper_size":             "58mm",
    "print_font_size":        7,
    "print_margin":           2,
    "print_width_chars":      32,
    "feature_ai_assistant":   True,
    "feature_mobile_viewer":  False,
    "feature_whatsapp_api":   False,
    "feature_multibranch":    False,
    "licensing_enforcement_enabled": False,
    "ai_config": {
        "enabled": True,
        "api_key": "",
        "storage": "keyring",
        "model": "claude-sonnet-4-5",
    },
    "whatsapp_api_config": default_api_settings(),
    "multibranch_config": default_multibranch_config(),
}


_SETTINGS_CACHE: dict = {}


def _invalidate_settings_cache():
    """Clear cached settings. Call after save_settings modifies the file."""
    global _SETTINGS_CACHE
    _SETTINGS_CACHE = {}


def get_settings() -> dict:
    try:
        mtime = os.path.getmtime(F_SETTINGS)
    except OSError:
        mtime = 0

    cached = _SETTINGS_CACHE
    if cached.get("mtime") == mtime and "merged" in cached:
        return cached["merged"]

    data = load_json(F_SETTINGS, {})
    merged = {**DEFAULTS, **data}
    for key in ("ai_config", "whatsapp_api_config", "multibranch_config"):
        merged[key] = {**DEFAULTS.get(key, {}), **data.get(key, {})}
    merged["gst_category_rate_map"] = normalize_gst_category_rate_map(
        merged.get("gst_category_rate_map"),
        fallback=DEFAULTS.get("gst_category_rate_map", {}),
    )
    merged["gst_classification_rules"] = normalize_gst_classification_rules(
        merged.get("gst_classification_rules"),
        fallback=DEFAULTS.get("gst_classification_rules", []),
    )
    merged["theme"] = LEGACY_THEME_MAP.get(
        merged.get("theme"),
        merged.get("theme", DEFAULTS["theme"]),
    )

    cached["mtime"] = mtime
    cached["merged"] = merged
    return merged


def save_settings(data: dict) -> bool:
    result = save_json(F_SETTINGS, data)
    if result:
        _invalidate_settings_cache()
    return result


def get_current_theme() -> str:
    return get_settings().get("theme", DEFAULTS["theme"])


def feature_enabled(feature_name: str, settings: dict | None = None) -> bool:
    cfg = settings or get_settings()
    key = f"feature_{feature_name}".strip().lower()
    return bool(cfg.get(key, DEFAULTS.get(key, False)))
