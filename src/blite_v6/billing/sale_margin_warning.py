from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class SaleMarginWarningState:
    should_warn: bool
    title: str = "Below Cost Warning"
    message: str = ""
    effective_bill_total: float = 0.0
    cost_total: float = 0.0
    discount_total: float = 0.0
    offending_items: tuple[dict[str, float | str], ...] = ()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def _product_cost_total(item: Mapping[str, Any]) -> float:
    return max(0.0, _safe_float(item.get("cost_price", item.get("cost", 0.0)))) * max(0.0, _safe_float(item.get("qty", 1.0), 1.0))


def build_sale_margin_warning_state(
    *,
    bill_items: Sequence[Mapping[str, Any]],
    gross_before_discount: Any,
    discount_total: Any,
) -> SaleMarginWarningState:
    gross_before = max(0.0, _safe_float(gross_before_discount))
    discount_value = max(0.0, _safe_float(discount_total))
    if gross_before <= 0:
        return SaleMarginWarningState(False)

    effective_bill_total = max(0.0, gross_before - discount_value)
    if effective_bill_total <= 0:
        return SaleMarginWarningState(False)

    discount_ratio = effective_bill_total / gross_before
    offenders: list[dict[str, float | str]] = []
    total_cost = 0.0

    for item in bill_items:
        if item.get("mode") != "products":
            continue
        sale_total = max(0.0, _safe_float(item.get("price")) * _safe_float(item.get("qty", 1.0), 1.0))
        cost_total = _product_cost_total(item)
        if sale_total <= 0 or cost_total <= 0:
            continue
        effective_sale_total = round(sale_total * discount_ratio, 2)
        total_cost += cost_total
        if effective_sale_total + 0.005 < cost_total:
            offenders.append(
                {
                    "name": str(item.get("name", "Item")).strip() or "Item",
                    "sale": round(effective_sale_total, 2),
                    "cost": round(cost_total, 2),
                }
            )

    if not offenders:
        return SaleMarginWarningState(
            False,
            effective_bill_total=round(effective_bill_total, 2),
            cost_total=round(total_cost, 2),
            discount_total=round(discount_value, 2),
        )

    preview_lines = []
    for offender in offenders[:3]:
        preview_lines.append(
            f"- {offender['name']}: Rs{offender['sale']:.2f} vs cost Rs{offender['cost']:.2f}"
        )
    extra = len(offenders) - len(preview_lines)
    if extra > 0:
        preview_lines.append(f"- {extra} more item(s) also drop below cost")

    message = (
        "One or more products are below cost after the current bill discounts.\n\n"
        + "\n".join(preview_lines)
        + "\n\nContinue anyway?"
    )
    return SaleMarginWarningState(
        True,
        message=message,
        effective_bill_total=round(effective_bill_total, 2),
        cost_total=round(total_cost, 2),
        discount_total=round(discount_value, 2),
        offending_items=tuple(offenders),
    )
