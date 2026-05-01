from __future__ import annotations

from typing import Any, Mapping


DEFAULT_GST_CATEGORY_RATE_MAP: dict[str, float] = {
    "fruits": 0.0,
    "fresh fruits": 0.0,
    "vegetables": 0.0,
    "fresh vegetables": 0.0,
    "salad": 0.0,
    "groceries": 5.0,
    "grocery": 5.0,
    "staples": 5.0,
    "cereals": 5.0,
    "grains": 5.0,
    "pulses": 5.0,
    "spices": 5.0,
    "edible oil": 5.0,
    "oil": 5.0,
    "dairy": 5.0,
    "hair care": 18.0,
    "body care": 18.0,
    "skin care": 18.0,
    "makeup": 18.0,
    "cosmetics": 18.0,
    "salon": 18.0,
    "beauty": 18.0,
    "tools": 18.0,
}


def _text(value: object, default: str = "") -> str:
    text = str(value if value is not None else "").strip()
    return text or default


def normalize_category_label(value: object) -> str:
    text = _text(value)
    if not text:
        return ""
    return " ".join(text.replace("_", " ").replace("/", " ").split()).lower()


def _float_rate(value: object) -> float | None:
    try:
        rate = float(value)
    except Exception:
        return None
    return max(0.0, rate)


def resolve_category_gst_rate(
    category: object,
    *,
    category_rate_map: Mapping[str, Any] | None = None,
) -> float | None:
    normalized = normalize_category_label(category)
    if not normalized:
        return None

    # Exact match first.
    if category_rate_map:
        for key, value in category_rate_map.items():
            if normalize_category_label(key) == normalized:
                rate = _float_rate(value)
                if rate is not None:
                    return rate

    for key, value in DEFAULT_GST_CATEGORY_RATE_MAP.items():
        if normalize_category_label(key) == normalized:
            rate = _float_rate(value)
            if rate is not None:
                return rate

    # Fall back to a simple containment match for broad labels such as
    # "Body Care / Cosmetics" or "Fresh Vegetables".
    merged: dict[str, Any] = dict(DEFAULT_GST_CATEGORY_RATE_MAP)
    if category_rate_map:
        merged.update(category_rate_map)

    for key, value in merged.items():
        key_norm = normalize_category_label(key)
        if key_norm and (key_norm in normalized or normalized in key_norm):
            rate = _float_rate(value)
            if rate is not None:
                return rate

    return None
