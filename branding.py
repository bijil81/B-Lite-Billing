import json
import os
import re
import sys
from pathlib import Path


DEFAULT_BRANDING = {
    "app_name": "B-Lite Management",
    "company_name": "B-Lite Technologies",
    "publisher_name": "B-Lite Technologies",
    "short_name": "B-Lite",
    "window_title": "B-Lite Management",
    "login_title": "Welcome to B-Lite Management",
    "sidebar_title": "B-Lite",
    "dashboard_title": "B-Lite Dashboard",
    "invoice_company_name": "B-Lite Management",
    "invoice_header": "B-Lite Management",
    "invoice_footer": "Thank you for visiting",
    "invoice_phone": "",
    "invoice_email": "",
    "invoice_address": "",
    "website": "",
    "support_phone": "",
    "support_email": "",
    "contact_name": "",
    "contact_phone": "",
    "contact_whatsapp": "",
    "contact_email": "",
    "contact_website": "",
    "contact_address": "",
    "contact_note": "",
    "logo_path": "logo.png",
    "sidebar_logo_path": "logo.png",
    "invoice_logo_path": "logo.png",
    "app_icon_path": "icon.ico",
    "installer_icon_path": "icon.ico",
    "splash_logo_path": "logo.png",
    "primary_color": "#6C63FF",
    "accent_color": "#FFB347",
    "default_theme": "modern_dark",
    "currency_symbol": "\u20b9",
    "business_type": "Salon",
    "tagline": "Professional Billing and Management",
    "powered_by": "Powered by B-Lite Technologies",
    "redeem_prefix": "BLITE",
    "product_version": "5.6",
    "exe_name": "BLiteManagement",
    "dist_name": "BLiteManagement",
    "install_dir_name": "BLiteManagement",
    "installer_name": "BLiteManagement_Setup_v5.6.exe",
}

LEGACY_FALLBACKS = {
    "logo_path": "logo.png",
    "sidebar_logo_path": "logo.png",
    "invoice_logo_path": "logo.png",
    "app_icon_path": "icon.ico",
    "installer_icon_path": "icon.ico",
    "splash_logo_path": "loading_logo.gif",
}


def _project_root() -> Path:
    return Path(__file__).resolve().parent


def _asset_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", _project_root()))


def _config_candidates():
    root = _project_root()
    asset = _asset_root()
    return [
        root / "assets" / "branding" / "branding_config.json",
        asset / "assets" / "branding" / "branding_config.json",
    ]


def _load_config() -> dict:
    for path in _config_candidates():
        if not path.exists():
            continue
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                return data
        except Exception:
            continue
    return {}


_BRANDING_CACHE = None


def get_branding(force_reload: bool = False) -> dict:
    global _BRANDING_CACHE
    if _BRANDING_CACHE is None or force_reload:
        merged = DEFAULT_BRANDING.copy()
        merged.update(_load_config())
        _BRANDING_CACHE = merged
    return dict(_BRANDING_CACHE)


def get_branding_value(key: str, default=None):
    return get_branding().get(key, default)


def _candidate_paths(rel: str):
    p = Path(rel)
    if p.is_absolute():
        return [p]
    return [_project_root() / rel, _asset_root() / rel]


def _shared_asset_candidates(config_key: str):
    shared = {
        "logo_path": [
            "assets/branding/logo/logo.png",
            "assets/branding/logo/company_logo.png",
        ],
        "sidebar_logo_path": [
            "assets/branding/logo/logo.png",
            "assets/branding/logo/company_logo.png",
            "assets/branding/logo/sidebar_logo.png",
        ],
        "invoice_logo_path": [
            "assets/branding/logo/logo.png",
            "assets/branding/logo/company_logo.png",
            "assets/branding/logo/invoice_logo.png",
        ],
        "splash_logo_path": [
            "assets/branding/logo/logo.png",
            "assets/branding/logo/loading_logo.gif",
            "assets/branding/logo/company_logo.png",
        ],
        "app_icon_path": [
            "assets/branding/icon/icon.ico",
            "assets/branding/icon/app.ico",
        ],
        "installer_icon_path": [
            "assets/branding/icon/icon.ico",
            "assets/branding/icon/installer.ico",
            "assets/branding/icon/app.ico",
        ],
    }
    out = []
    for rel in shared.get(config_key, []):
        out.extend(_candidate_paths(rel))
    return out


def _extension_fallback_candidates(config_key: str):
    root = _project_root()
    asset = _asset_root()
    if "icon" in config_key:
        dirs = [root / "assets" / "branding" / "icon", asset / "assets" / "branding" / "icon"]
        exts = {".ico"}
    else:
        dirs = [root / "assets" / "branding" / "logo", asset / "assets" / "branding" / "logo"]
        exts = {".png", ".gif", ".jpg", ".jpeg", ".webp"}
    out = []
    seen = set()
    for base in dirs:
        if not base.exists():
            continue
        for path in sorted(base.iterdir()):
            if not path.is_file() or path.suffix.lower() not in exts:
                continue
            key = str(path)
            if key in seen:
                continue
            seen.add(key)
            out.append(path)
    return out


def resolve_branding_asset(config_key: str, fallback_key: str | None = None) -> str:
    cfg = get_branding()
    rel = cfg.get(config_key, DEFAULT_BRANDING.get(config_key, ""))
    candidates = _candidate_paths(rel)
    candidates.extend(_shared_asset_candidates(config_key))
    candidates.extend(_extension_fallback_candidates(config_key))
    if fallback_key:
        candidates.extend(_candidate_paths(LEGACY_FALLBACKS.get(fallback_key, "")))
    else:
        candidates.extend(_candidate_paths(LEGACY_FALLBACKS.get(config_key, "")))
    for candidate in candidates:
        if candidate and str(candidate) and candidate.exists():
            return str(candidate)
    return str(candidates[-1]) if candidates else rel


def get_app_name() -> str:
    return get_branding_value("app_name", DEFAULT_BRANDING["app_name"])


def get_company_name() -> str:
    return get_branding_value("company_name", DEFAULT_BRANDING["company_name"])


def get_short_name() -> str:
    return get_branding_value("short_name", DEFAULT_BRANDING["short_name"])


def get_window_title(include_version: bool = False) -> str:
    title = get_branding_value("window_title", DEFAULT_BRANDING["window_title"])
    version = str(get_branding_value("product_version", DEFAULT_BRANDING["product_version"])).strip()
    if include_version and version:
        return f"{title} v{version}"
    return title


def get_login_title() -> str:
    return get_branding_value("login_title", DEFAULT_BRANDING["login_title"])


def get_sidebar_title() -> str:
    return get_branding_value("sidebar_title", DEFAULT_BRANDING["sidebar_title"])


def get_invoice_header() -> str:
    return get_branding_value("invoice_header", DEFAULT_BRANDING["invoice_header"])


def get_invoice_company_name() -> str:
    return get_branding_value("invoice_company_name", DEFAULT_BRANDING["invoice_company_name"])


def get_invoice_footer() -> str:
    return get_branding_value("invoice_footer", DEFAULT_BRANDING["invoice_footer"])


def get_branding_logo_path(kind: str = "main") -> str:
    mapping = {
        "main": "logo_path",
        "sidebar": "sidebar_logo_path",
        "invoice": "invoice_logo_path",
        "splash": "splash_logo_path",
    }
    key = mapping.get(kind, "logo_path")
    return resolve_branding_asset(key, key)


def get_branding_icon_path(kind: str = "app") -> str:
    key = "installer_icon_path" if kind == "installer" else "app_icon_path"
    return resolve_branding_asset(key, key)


def get_invoice_branding() -> dict:
    cfg = get_branding()
    return {
        "salon_name": cfg.get("invoice_company_name") or cfg.get("invoice_header") or get_company_name(),
        "header": cfg.get("invoice_header") or get_company_name(),
        "footer": cfg.get("invoice_footer") or DEFAULT_BRANDING["invoice_footer"],
        "phone": cfg.get("invoice_phone", ""),
        "email": cfg.get("invoice_email", ""),
        "address": cfg.get("invoice_address", ""),
        "website": cfg.get("website", ""),
        "logo_path": get_branding_logo_path("invoice"),
    }


def get_about_contact_info() -> dict:
    cfg = get_branding()
    return {
        "name": cfg.get("contact_name", ""),
        "phone": cfg.get("contact_phone") or cfg.get("support_phone", ""),
        "whatsapp": cfg.get("contact_whatsapp", ""),
        "email": cfg.get("contact_email") or cfg.get("support_email", ""),
        "website": cfg.get("contact_website") or cfg.get("website", ""),
        "address": cfg.get("contact_address", ""),
        "note": cfg.get("contact_note", ""),
    }


def get_tagline() -> str:
    return get_branding_value("tagline", DEFAULT_BRANDING["tagline"])


def get_redeem_prefix() -> str:
    raw = str(get_branding_value("redeem_prefix", "") or "").strip()
    if raw:
        return _slugify(raw.upper(), "BLITE")[:8]
    return _slugify(get_short_name().upper(), "BLITE")[:8]


def get_backup_folder_name() -> str:
    short_name = _slugify(get_short_name(), "BLite")
    return f"{short_name}_OfflineBackup"


def get_runtime_app_slug() -> str:
    cfg = get_branding()
    return _slugify(
        cfg.get("install_dir_name")
        or cfg.get("exe_name")
        or cfg.get("short_name")
        or cfg.get("app_name"),
        "BLiteManagement",
    )


def get_appdata_dir_name() -> str:
    return f"{get_runtime_app_slug()}_Data"


def get_programdata_dir_name() -> str:
    return get_runtime_app_slug()


def get_secure_store_prefix() -> str:
    return get_runtime_app_slug()


def _slugify(value: str, fallback: str) -> str:
    text = re.sub(r"[^A-Za-z0-9]+", "", str(value or "").strip())
    return text or fallback


def get_build_branding() -> dict:
    cfg = get_branding()
    version = str(cfg.get("product_version", DEFAULT_BRANDING["product_version"])).strip() or DEFAULT_BRANDING["product_version"]
    app_name = str(cfg.get("app_name", DEFAULT_BRANDING["app_name"])).strip() or DEFAULT_BRANDING["app_name"]
    company = str(cfg.get("publisher_name", cfg.get("company_name", DEFAULT_BRANDING["publisher_name"]))).strip() or DEFAULT_BRANDING["publisher_name"]
    exe_name = _slugify(cfg.get("exe_name", app_name), "BLiteManagement")
    dist_name = _slugify(cfg.get("dist_name", exe_name), exe_name)
    install_dir_name = _slugify(cfg.get("install_dir_name", app_name), dist_name)
    installer_name = str(cfg.get("installer_name", f"{dist_name}_Setup_v{version}.exe")).strip() or f"{dist_name}_Setup_v{version}.exe"
    return {
        "app_name": app_name,
        "app_version": version,
        "publisher_name": company,
        "exe_name": exe_name,
        "exe_file": f"{exe_name}.exe",
        "dist_name": dist_name,
        "install_dir_name": install_dir_name,
        "installer_name": installer_name,
        "app_icon": get_branding_icon_path("app"),
        "installer_icon": get_branding_icon_path("installer"),
    }
