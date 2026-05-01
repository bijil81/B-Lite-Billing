from __future__ import annotations

from typing import Mapping

from .gst_master import normalize_gst_category_rate_map


BILLING_MODE_LABELS = {
    "mixed": "Salon/Spa",
    "product_only": "Retail Store",
    "service_only": "Service Business",
}

GST_RATE_SOURCE_LABELS = {
    "global": "Global GST",
    "item": "Item-wise GST",
    "hybrid": "Hybrid / Auto",
}

MISSING_ITEM_GST_POLICY_LABELS = {
    "global": "Use global GST rate",
    "zero": "Use 0% and warn",
    "warn": "Use global GST and warn",
}


def parse_gst_rate(rate_text: str, default: float = 18.0) -> float:
    try:
        return float(str(rate_text).strip() or str(default))
    except Exception:
        return default


def build_bill_gst_payload(
    current_settings: Mapping,
    *,
    billing_mode: str,
    gst_always_on: bool,
    gst_type: str,
    gst_rate_text: str,
    product_wise_gst_enabled: bool,
    gst_rate_source: str,
    missing_item_gst_policy: str,
    gst_category_rate_map: Mapping | None = None,
    bill_footer: str,
) -> dict:
    cfg = dict(current_settings)
    cfg["billing_mode"] = billing_mode
    cfg["gst_always_on"] = bool(gst_always_on)
    cfg["gst_type"] = gst_type
    cfg["gst_rate"] = parse_gst_rate(gst_rate_text)
    cfg["product_wise_gst_enabled"] = bool(product_wise_gst_enabled)
    cfg["gst_rate_source"] = str(gst_rate_source).strip() or "global"
    cfg["missing_item_gst_policy"] = str(missing_item_gst_policy).strip() or "global"
    if gst_category_rate_map is not None:
        cfg["gst_category_rate_map"] = normalize_gst_category_rate_map(
            gst_category_rate_map,
            fallback=current_settings.get("gst_category_rate_map"),
        )
    cfg["bill_footer"] = str(bill_footer).strip()
    return cfg


def bill_gst_saved_message(settings: Mapping) -> str:
    gst_state = "Always ON" if settings.get("gst_always_on") else "Manual"
    mode_name = BILLING_MODE_LABELS.get(settings.get("billing_mode"), "Salon/Spa")
    gst_type = str(settings.get("gst_type", "inclusive")).title()
    gst_rate = settings.get("gst_rate", 18.0)
    rate_source = GST_RATE_SOURCE_LABELS.get(settings.get("gst_rate_source"), "Global GST")
    item_mode = "Item GST ON" if settings.get("product_wise_gst_enabled") else "Item GST OFF"
    master_count = len(settings.get("gst_category_rate_map", {}) or {})
    classification_count = len(settings.get("gst_classification_rules", {}) or {})
    return (
        f"Saved!\nMode: {mode_name}\nGST: {gst_state} | {gst_type} | {gst_rate}%\n"
        f"Tax Mode: {rate_source} | {item_mode}\n"
        f"GST Master: {master_count} category rules\n"
        f"GST Classification: {classification_count} item rules"
    )
