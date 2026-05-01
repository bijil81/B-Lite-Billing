from __future__ import annotations

from typing import Any, Mapping

from ..settings.gst_classification_master import resolve_gst_classification_rate
from ..billing.gst_category_rules import normalize_category_label, resolve_category_gst_rate


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


def resolve_inventory_gst_rate(
    product: Mapping[str, Any] | object,
    *,
    settings: Mapping[str, Any] | None = None,
) -> float | None:
    """
    Resolve a practical inventory GST rate.

    Exact product classification rules win first. If no classification rule
    exists, category master rules win next. If no category rule exists and a
    category is present, the shop-wide GST rate is used as fallback.
    """
    cfg = dict(settings or {})
    if isinstance(product, Mapping):
        classification_rate = resolve_gst_classification_rate(
            product,
            rules=cfg.get("gst_classification_rules"),
        )
        if classification_rate is not None:
            return classification_rate
        category_text = _text(product.get("category"))
    else:
        category_text = _text(product)

    if not normalize_category_label(category_text):
        return None

    rate = resolve_category_gst_rate(
        category_text,
        category_rate_map=cfg.get("gst_category_rate_map"),
    )
    if rate is not None:
        return rate
    return _float_rate(cfg.get("gst_rate", 18.0), 18.0)


def autofill_inventory_gst_rate(
    raw: Mapping[str, Any],
    *,
    settings: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Return a copy of raw inventory form data with gst_rate filled when blank.
    Explicit user-entered GST values are preserved.
    """
    data = dict(raw)
    if data.get("gst_rate_touched"):
        return data

    current_rate = _text(data.get("gst_rate"))
    initial_fields = {
        "name": _text(data.get("initial_name")),
        "base_product": _text(data.get("initial_base_product")),
        "category": _text(data.get("initial_category")),
        "hsn_sac": _text(data.get("initial_hsn_sac")),
        "sku": _text(data.get("initial_sku")),
        "barcode": _text(data.get("initial_barcode")),
    }
    has_initial_context = any(initial_fields.values()) or _text(data.get("initial_gst_rate"))

    if current_rate and not has_initial_context:
        return data

    current_fields = {
        "name": _text(data.get("name")),
        "base_product": _text(data.get("base_product")),
        "category": _text(data.get("category")),
        "hsn_sac": _text(data.get("hsn_sac")),
        "sku": _text(data.get("sku")),
        "barcode": _text(data.get("barcode")),
    }
    classification_changed = any(
        normalize_category_label(current_fields[key]) != normalize_category_label(initial_fields.get(key, ""))
        for key in ("name", "base_product", "category")
    ) or any(
        _text(current_fields[key]).strip() != _text(initial_fields.get(key, "")).strip()
        for key in ("hsn_sac", "sku", "barcode")
    )

    if current_rate and has_initial_context and not classification_changed:
        initial_rate = _text(data.get("initial_gst_rate"))
        if initial_rate:
            data["gst_rate"] = initial_rate
        return data

    resolved = resolve_inventory_gst_rate(data, settings=settings)
    if resolved is None:
        if current_rate:
            return data
        initial_rate = _text(data.get("initial_gst_rate"))
        if initial_rate:
            data["gst_rate"] = initial_rate
        return data

    data["gst_rate"] = f"{resolved:g}"
    return data
