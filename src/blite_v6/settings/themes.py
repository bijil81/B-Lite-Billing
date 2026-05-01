from __future__ import annotations

from branding import get_branding_value
from utils import C


DEFAULT_THEME_KEY = get_branding_value("default_theme", "modern_dark")


THEMES = {
    "modern_dark": {
        "name": "Modern Dark",
        "bg": "#0D0D0D", "card": "#1A1A1A", "sidebar": "#121821",
        "input": "#262626", "text": "#F5F5F5", "muted": "#A3A3A3",
        "accent": "#10B981", "teal": "#3B82F6", "lime": "#22C55E",
        "gold": "#10B981", "red": "#EF4444", "green": "#22C55E",
        "blue": "#3B82F6", "orange": "#F59E0B", "purple": "#6366F1",
    },
    "modern_light": {
        "name": "Modern Light",
        "bg": "#F9FAFB", "card": "#FFFFFF", "sidebar": "#EAF1FB",
        "input": "#F3F4F6", "text": "#111827", "muted": "#6B7280",
        "accent": "#10B981", "teal": "#2563EB", "lime": "#10B981",
        "gold": "#10B981", "red": "#EF4444", "green": "#10B981",
        "blue": "#2563EB", "orange": "#F59E0B", "purple": "#60A5FA",
    },
    "salon_spa": {
        "name": "Salon Spa Elegant",
        "bg": "#FFF7F7", "card": "#FFE4E6", "sidebar": "#FBCFE8",
        "input": "#FFFFFF", "text": "#3F3F46", "muted": "#71717A",
        "accent": "#F59E0B", "teal": "#EC4899", "lime": "#F472B6",
        "gold": "#F59E0B", "red": "#EF4444", "green": "#22C55E",
        "blue": "#EC4899", "orange": "#F59E0B", "purple": "#F472B6",
    },
    "natural_spa": {
        "name": "Natural Spa",
        "bg": "#F0FDF4", "card": "#DCFCE7", "sidebar": "#BBF7D0",
        "input": "#FFFFFF", "text": "#14532D", "muted": "#4B5563",
        "accent": "#22C55E", "teal": "#16A34A", "lime": "#4ADE80",
        "gold": "#22C55E", "red": "#EF4444", "green": "#22C55E",
        "blue": "#16A34A", "orange": "#F59E0B", "purple": "#4ADE80",
    },
    "premium_salon": {
        "name": "Premium Salon",
        "bg": "#0F0A1F", "card": "#2E294E", "sidebar": "#1E1B2E",
        "input": "#241F3D", "text": "#F3F4F6", "muted": "#A1A1AA",
        "accent": "#F59E0B", "teal": "#8B5CF6", "lime": "#A78BFA",
        "gold": "#F59E0B", "red": "#EF4444", "green": "#22C55E",
        "blue": "#8B5CF6", "orange": "#F59E0B", "purple": "#A78BFA",
    },
}


LEGACY_THEME_MAP = {
    "dark": "modern_dark",
    "deep_dark": "modern_dark",
    "light": "modern_light",
    "rose": "salon_spa",
    "purple": "premium_salon",
    "ocean": "modern_dark",
}


def normalize_theme_key(theme_key: str | None) -> str:
    key = LEGACY_THEME_MAP.get(theme_key, theme_key)
    if key in THEMES:
        return str(key)
    return DEFAULT_THEME_KEY if DEFAULT_THEME_KEY in THEMES else "modern_dark"


def apply_theme(theme_key: str):
    theme = THEMES[normalize_theme_key(theme_key)]
    for key, value in theme.items():
        if key == "name":
            continue
        C[key] = value

