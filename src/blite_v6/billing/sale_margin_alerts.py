from __future__ import annotations

from typing import Any

from .sale_margin_warning import SaleMarginWarningState


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def build_sale_margin_alert_text(state: SaleMarginWarningState) -> str:
    if not state.should_warn:
        return ""

    offenders = list(state.offending_items)
    if not offenders:
        return "Below cost after the current discount."

    parts: list[str] = []
    for offender in offenders[:2]:
        name = _safe_text(offender.get("name")) or "Item"
        sale = float(offender.get("sale", 0.0) or 0.0)
        cost = float(offender.get("cost", 0.0) or 0.0)
        parts.append(f"{name}: Rs{sale:.2f} vs cost Rs{cost:.2f}")

    if len(offenders) > 2:
        parts.append(f"+ {len(offenders) - 2} more item(s)")

    prefix = "Below cost after the current discount."
    return f"{prefix} " + " | ".join(parts)
