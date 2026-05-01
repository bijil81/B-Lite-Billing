from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence


SafeTextFn = Callable[[Any], str]


def _default_safe_text(value: Any) -> str:
    return str(value or "")


def discount_toggle_state(enabled: bool, current_value: str | None) -> dict[str, Any]:
    if enabled:
        return {
            "entry_state": "normal",
            "value": (current_value or "").strip() or "0",
            "focus_discount": True,
        }
    return {
        "entry_state": "disabled",
        "value": "0",
        "focus_discount": False,
    }


def format_offer_option(offer: Mapping[str, Any], safe_text_fn: SafeTextFn = _default_safe_text) -> str:
    try:
        offer_type = offer.get("type", "percentage")
        offer_value = int(offer.get("value", 0))
        offer_name = safe_text_fn(offer.get("name", "Offer")) or "Offer"
        value_text = f"{offer_value}%" if offer_type != "flat" else f"Rs{offer_value}"
        return f"{offer_name} ({str(offer_type).replace('_', ' ')} - {value_text})"
    except Exception:
        return safe_text_fn(offer.get("name", "Offer")) or "Offer"


def build_offer_options(offers: Sequence[Mapping[str, Any]], safe_text_fn: SafeTextFn = _default_safe_text) -> list[str]:
    return ["No Offer"] + [format_offer_option(offer, safe_text_fn) for offer in offers]


def select_offer_state(
    selected_text: str,
    offers: Sequence[Mapping[str, Any]],
    option_values: Sequence[str],
    safe_text_fn: SafeTextFn = _default_safe_text,
) -> dict[str, Any]:
    if selected_text == "No Offer":
        return {"applied_offer": None, "info_text": "", "clear_coupon": True}

    idx = list(option_values).index(selected_text) - 1
    if 0 <= idx < len(offers):
        offer = offers[idx]
        info_text = safe_text_fn(offer.get("description", "Offer applied")) or "Offer applied"
        return {"applied_offer": offer, "info_text": info_text, "clear_coupon": True}
    return {"applied_offer": None, "info_text": "", "clear_coupon": True}


def normalize_coupon_code(raw_code: str | None) -> str:
    return (raw_code or "").strip().upper()


def coupon_success_text(code: str, offer: Mapping[str, Any], safe_text_fn: SafeTextFn = _default_safe_text) -> str:
    return f"Coupon '{code}' applied! - {safe_text_fn(offer.get('name', ''))}"


def coupon_invalid_text(code: str) -> str:
    return f"Coupon '{code}' is invalid or expired."


def coupon_apply_state(code: str, offer: Mapping[str, Any] | None, safe_text_fn: SafeTextFn = _default_safe_text) -> dict[str, Any]:
    if offer:
        return {
            "valid": True,
            "applied_offer": offer,
            "offer_var": "No Offer",
            "info_text": coupon_success_text(code, offer, safe_text_fn),
            "error_text": "",
        }
    return {
        "valid": False,
        "applied_offer": None,
        "offer_var": None,
        "info_text": "",
        "error_text": coupon_invalid_text(code),
    }


def clear_offer_state() -> dict[str, Any]:
    return {
        "applied_offer": None,
        "applied_redeem_code": None,
        "offer_var": "No Offer",
        "info_text": "",
    }


def format_redeem_value(value: Any, discount_type: str) -> str:
    numeric_value = float(value or 0)
    return f"Rs{numeric_value:.0f}" if discount_type == "flat" else f"{numeric_value:.0f}%"


def redeem_apply_state(code: str, valid: bool, info: Mapping[str, Any] | str) -> dict[str, Any]:
    if valid:
        value = info.get("value", 0) if isinstance(info, Mapping) else 0
        discount_type = info.get("discount_type", "flat") if isinstance(info, Mapping) else "flat"
        value_text = format_redeem_value(value, discount_type)
        return {
            "valid": True,
            "applied_redeem_code": code,
            "info_text": f"Redeem '{code}' - {value_text} discount! (valid)",
            "error_text": "",
        }
    return {
        "valid": False,
        "applied_redeem_code": None,
        "info_text": "",
        "error_text": info,
    }


def should_clear_offer_info_after_redeem_clear(applied_offer: Mapping[str, Any] | None) -> bool:
    return not bool(applied_offer)
