"""Lightweight category-master helpers backed by the legacy catalog file."""

from __future__ import annotations

from typing import Literal

from src.blite_v6.text_normalization import smart_title_name
from utils import F_SERVICES, load_json, save_json


CatalogSection = Literal["Products", "Services"]


def _catalog_data() -> dict:
    data = load_json(F_SERVICES, {})
    if not isinstance(data, dict):
        data = {}
    if "Services" not in data or not isinstance(data.get("Services"), dict):
        data["Services"] = {}
    if "Products" not in data or not isinstance(data.get("Products"), dict):
        data["Products"] = {}
    return data


def list_catalog_categories(section: CatalogSection = "Products") -> list[str]:
    data = _catalog_data()
    categories = [smart_title_name(name) for name in data.get(section, {}).keys()]
    return sorted({name for name in categories if name}, key=str.lower)


def ensure_catalog_category(section: CatalogSection, category: object) -> str:
    """Persist an empty category if it does not exist and return its normalized name."""
    name = smart_title_name(category)
    if not name:
        return ""
    data = _catalog_data()
    bucket = data.setdefault(section, {})
    existing = next(
        (key for key in bucket.keys() if str(key).strip().lower() == name.lower()),
        None,
    )
    if existing is None:
        bucket[name] = {}
        save_json(F_SERVICES, data)
        return name
    normalized_existing = smart_title_name(existing)
    if existing != normalized_existing:
        bucket[normalized_existing] = bucket.pop(existing)
        save_json(F_SERVICES, data)
    return normalized_existing
