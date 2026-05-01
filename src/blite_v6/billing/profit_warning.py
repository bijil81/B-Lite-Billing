from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class BelowCostWarningState:
    should_warn: bool
    title: str = "Below Cost Warning"
    message: str = ""
    sale_unit_price: float = 0.0
    effective_unit_price: float = 0.0
    cost_unit_price: float = 0.0
    sale_total: float = 0.0
    effective_total: float = 0.0
    cost_total: float = 0.0
    discount_amount: float = 0.0
    discount_ratio: float = 0.0


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def _bill_subtotal(items: Sequence[Mapping[str, Any]]) -> float:
    total = 0.0
    for item in items:
        if item.get("mode") not in {"services", "products"}:
            continue
        total += _safe_float(item.get("price")) * _safe_float(item.get("qty"), 1.0)
    return max(0.0, total)


def build_below_cost_warning_state(
    *,
    bill_items: Sequence[Mapping[str, Any]],
    item_name: str,
    sale_price: Any,
    qty: Any,
    cost_price: Any,
    discount_enabled: bool,
    discount_value: Any,
) -> BelowCostWarningState:
    sale_unit_price = max(0.0, _safe_float(sale_price))
    cost_unit_price = max(0.0, _safe_float(cost_price))
    qty_value = _safe_float(qty, 1.0)
    if qty_value <= 0 or sale_unit_price <= 0 or cost_unit_price <= 0:
        return BelowCostWarningState(False)

    sale_total = round(sale_unit_price * qty_value, 2)
    cost_total = round(cost_unit_price * qty_value, 2)
    if sale_total <= 0 or cost_total <= 0:
        return BelowCostWarningState(False)

    bill_total_before = _bill_subtotal(bill_items)
    bill_total_after = round(bill_total_before + sale_total, 2)
    discount_amount = 0.0
    if discount_enabled and bill_total_after > 0:
        discount_amount = min(bill_total_after, max(0.0, _safe_float(discount_value)))

    discount_ratio = (discount_amount / bill_total_after) if bill_total_after > 0 else 0.0
    effective_total = round(sale_total * (1.0 - discount_ratio), 2)
    effective_unit_price = round(effective_total / qty_value, 2)

    should_warn = effective_total + 0.005 < cost_total
    if not should_warn:
        return BelowCostWarningState(
            False,
            sale_unit_price=sale_unit_price,
            effective_unit_price=effective_unit_price,
            cost_unit_price=cost_unit_price,
            sale_total=sale_total,
            effective_total=effective_total,
            cost_total=cost_total,
            discount_amount=round(discount_amount, 2),
            discount_ratio=round(discount_ratio, 4),
        )

    if discount_amount > 0:
        message = (
            f"{item_name} would sell at Rs{effective_unit_price:.2f}/unit "
            f"after Rs{discount_amount:.2f} bill discount, but cost is Rs{cost_unit_price:.2f}/unit.\n"
            "Continue anyway?"
        )
    else:
        message = (
            f"{item_name} sale price Rs{sale_unit_price:.2f}/unit is below cost "
            f"Rs{cost_unit_price:.2f}/unit.\nContinue anyway?"
        )

    return BelowCostWarningState(
        True,
        message=message,
        sale_unit_price=sale_unit_price,
        effective_unit_price=effective_unit_price,
        cost_unit_price=cost_unit_price,
        sale_total=sale_total,
        effective_total=effective_total,
        cost_total=cost_total,
        discount_amount=round(discount_amount, 2),
        discount_ratio=round(discount_ratio, 4),
    )
