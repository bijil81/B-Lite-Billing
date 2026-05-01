from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from ..billing.gst_category_rules import DEFAULT_GST_CATEGORY_RATE_MAP, normalize_category_label


def _text(value: object, default: str = "") -> str:
    text = str(value if value is not None else "").strip()
    return text or default


def _float_rate(value: object, default: float | None = None) -> float | None:
    try:
        rate = float(str(value).strip())
    except Exception:
        return default
    if rate < 0:
        return default
    return rate


def normalize_gst_category_rate_map(
    raw: Mapping[str, Any] | Iterable[Mapping[str, Any]] | None,
    *,
    fallback: Mapping[str, Any] | None = None,
) -> dict[str, float]:
    merged: dict[str, float] = {}
    source = fallback or DEFAULT_GST_CATEGORY_RATE_MAP

    if source:
        for category, rate in source.items():
            name = _text(category)
            rate_value = _float_rate(rate, 0.0)
            if name and rate_value is not None:
                merged[name] = rate_value

    if raw is None:
        return _sorted_case_insensitive_map(merged)

    if isinstance(raw, Mapping):
        items = raw.items()
    else:
        items = []
        for entry in raw:
            if not isinstance(entry, Mapping):
                continue
            items.append((entry.get("category") or entry.get("name") or entry.get("label"), entry.get("rate")))

    for category, rate in items:
        name = _text(category)
        rate_value = _float_rate(rate, None)
        if not name or rate_value is None:
            continue
        merged[name] = rate_value

    return _sorted_case_insensitive_map(merged)


def _sorted_case_insensitive_map(data: Mapping[str, float]) -> dict[str, float]:
    ordered: dict[str, float] = {}
    index_by_norm: dict[str, str] = {}
    for category, rate in data.items():
        normalized = normalize_category_label(category)
        if not normalized:
            continue
        previous = index_by_norm.get(normalized)
        if previous and previous in ordered:
            ordered.pop(previous, None)
        ordered[category] = round(float(rate), 2)
        index_by_norm[normalized] = category
    return dict(sorted(ordered.items(), key=lambda item: normalize_category_label(item[0])))


def gst_category_rate_rows(settings: Mapping[str, Any] | None) -> list[tuple[str, float]]:
    cfg = settings or {}
    raw = cfg.get("gst_category_rate_map") if isinstance(cfg, Mapping) else None
    normalized = normalize_gst_category_rate_map(raw)
    return list(normalized.items())


def build_gst_master_payload(
    current_settings: Mapping[str, Any],
    *,
    gst_category_rate_map: Mapping[str, Any] | Iterable[Mapping[str, Any]] | None,
) -> dict:
    cfg = dict(current_settings)
    cfg["gst_category_rate_map"] = normalize_gst_category_rate_map(
        gst_category_rate_map,
        fallback=current_settings.get("gst_category_rate_map") if isinstance(current_settings, Mapping) else None,
    )
    return cfg


def gst_master_saved_message(settings: Mapping[str, Any]) -> str:
    rows = gst_category_rate_rows(settings)
    if not rows:
        return "GST master saved!\nNo category rules configured."
    preview = ", ".join(f"{name}={rate:g}%" for name, rate in rows[:4])
    if len(rows) > 4:
        preview += f", +{len(rows) - 4} more"
    return f"GST master saved!\nCategories: {len(rows)}\n{preview}"
