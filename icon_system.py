import os
import tkinter as tk

from utils import app_log, resource_path

try:
    from PIL import Image, ImageTk
except Exception:  # pragma: no cover - graceful fallback when PIL is unavailable
    Image = None
    ImageTk = None


_ICON_CACHE = {}
_ICON_CACHE_OWNER = None

_NAV_FILE_MAP = {
    "dashboard": "dashboard_20.png",
    "billing": "billing_20.png",
    "customers": "customers_20.png",
    "appointments": "appointments_20.png",
    "membership": "memberships_20.png",
    "offers": "offers_20.png",
    "redeem_codes": "redeem_20.png",
    "cloud_sync": "icons8-cloud-sync-20.png",
    "staff": "staff_20.png",
    "inventory": "inventory_20.png",
    "expenses": "expenses_20.png",
    "whatsapp_bulk": "bulk_whatsapp_20.png",
    "reports": "reports_20.png",
    "closing_report": "closing_report_20.png",
    "ai_assistant": "ai_assistant_20.png",
    "settings": "settings_20.png",
}

_ACTION_FILE_MAP = {
    "alerts": "notification_14.png",
    "help": "help_16.png",
    "admin": "admin_16.png",
    "logout": "logout_16.png",
    "switch_user": "switch_user_16.png",
    "add": "add_14.png",
    "edit": "edit_14.png",
    "delete": "delete_14.png",
    "save": "save_14.png",
    "refresh": "refresh_14.png",
    "print": "print_14.png",
    "pdf": "pdf_14.png",
    "whatsapp": "whatsapp_14.png",
    "backup": "backup_14.png",
    "restore": "restore_14.png",
    "import_json": "import_json_14.png",
    "import_excel": "import_excel_14.png",
    "search": "search_14.png",
    "filter": "filter_14.png",
    "browse": "browse_14.png",
    "clear": "clear_14.png",
}

_SECTION_FILE_MAP = {
    "info": "salon_info_16.png",
    "theme": "theme_16.png",
    "bill": "billing_settings_16.png",
    "sec": "security_16.png",
    "pref": "preferences_16.png",
    "notif": "notifications_16.png",
    "ai": "ai_settings_16.png",
    "print": "print_bill_16.png",
    "folder_sync": "folder_sync_16.png",
    "mobile_viewer": "mobile_viewer_16.png",
    "offline_backup": "offline_backup_16.png",
    "user_management": "user_management_16.png",
    "packages": "packages_16.png",
}


def clear_icon_cache():
    global _ICON_CACHE_OWNER
    _ICON_CACHE.clear()
    _ICON_CACHE_OWNER = None


def _current_root():
    try:
        root = tk._default_root
    except Exception:
        root = None
    if root is None:
        return None
    try:
        if not int(root.winfo_exists()):
            return None
    except Exception:
        return None
    return root


def _current_root_token():
    root = _current_root()
    if root is None:
        return None
    try:
        return str(root.tk)
    except Exception:
        return None


def _ensure_cache_for_current_root():
    global _ICON_CACHE_OWNER
    current_root = _current_root_token()
    if current_root != _ICON_CACHE_OWNER:
        _ICON_CACHE.clear()
        _ICON_CACHE_OWNER = current_root


def _image_exists_for_root(photo, root) -> bool:
    if photo is None or root is None:
        return False
    try:
        image_name = str(photo)
        if not image_name:
            return False
        image_names = root.tk.call("image", "names")
        return image_name in image_names
    except Exception:
        return False


def _load_icon(rel_path: str, size: tuple[int, int] | None = None):
    if Image is None or ImageTk is None:
        return None

    _ensure_cache_for_current_root()
    root = _current_root()
    if root is None:
        return None

    cache_key = (rel_path, size)
    if cache_key in _ICON_CACHE:
        cached_photo = _ICON_CACHE[cache_key]
        if _image_exists_for_root(cached_photo, root):
            return cached_photo
        _ICON_CACHE.pop(cache_key, None)

    abs_path = resource_path(rel_path)
    if not os.path.exists(abs_path):
        return None

    try:
        img = Image.open(abs_path).convert("RGBA")
        if size:
            img = img.resize(size)
        photo = ImageTk.PhotoImage(img, master=root)
        if not _image_exists_for_root(photo, root):
            return None
        _ICON_CACHE[cache_key] = photo
        return photo
    except Exception as exc:
        app_log(f"[icon_system] Failed to load {rel_path}: {exc}", level="warning")
        return None


def get_nav_icon(nav_key: str):
    filename = _NAV_FILE_MAP.get(nav_key)
    if not filename:
        return None
    return _load_icon(os.path.join("assets", "icons", "nav", filename), (20, 20))


def get_action_icon(action_key: str):
    filename = _ACTION_FILE_MAP.get(action_key)
    if not filename:
        return None
    size = (16, 16) if "_16" in filename else (14, 14)
    return _load_icon(os.path.join("assets", "icons", "actions", filename), size)


def get_section_icon(section_key: str):
    filename = _SECTION_FILE_MAP.get(section_key)
    if not filename:
        return None
    return _load_icon(os.path.join("assets", "icons", "sections", filename), (16, 16))
