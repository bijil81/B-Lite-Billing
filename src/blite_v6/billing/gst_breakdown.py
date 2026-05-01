from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .gst_category_rules import resolve_category_gst_rate


def _text(value: object, default: str = "") -> str:
    text = str(value if value is not None else "").strip()
    return text or default


def _float(value: object, default: float = 0.0) -> float:
    try:
        return float(value if value not in (None, "") else default)
    except Exception:
        return default


def _bool(value: object, default: bool = False) -> bool:
    if value in (None, ""):
        return default
    if isinstance(value, str):
        return value.strip().lower() in {"1", "yes", "true", "on", "y"}
    return bool(value)


@dataclass(frozen=True)
class GSTRateSummary:
    rate: float
    taxable_amount: float
    gst_amount: float
    gross_amount: float
    line_count: int


@dataclass(frozen=True)
class GSTComputation:
    gross_before_discount: float
    gross_after_discount: float
    taxable_amount: float
    gst_amount: float
    grand_total: float
    gst_mode: str
    rate_summary: tuple[GSTRateSummary, ...]


def _resolve_item_rate(
    item: Mapping[str, Any],
    *,
    gst_rate: float,
    gst_rate_source: str,
    missing_item_gst_policy: str,
    product_wise_gst_enabled: bool,
    gst_category_rate_map: Mapping[str, Any] | None = None,
) -> tuple[float, str]:
    if not product_wise_gst_enabled or item.get("mode") != "products":
        return gst_rate, "global"

    raw_rate = item.get("gst_rate")
    if raw_rate not in (None, ""):
        try:
            return max(0.0, float(raw_rate)), "item"
        except Exception:
            pass

    if gst_rate_source == "hybrid":
        category_rate = resolve_category_gst_rate(
            item.get("category")
            or item.get("category_name")
            or item.get("category_label"),
            category_rate_map=gst_category_rate_map,
        )
        if category_rate is not None:
            return category_rate, "category"

    policy = _text(missing_item_gst_policy, "global").lower()
    if policy == "zero":
        return 0.0, "missing-zero"
    if policy == "warn":
        return gst_rate, "missing-global-warn"
    if gst_rate_source == "item":
        return gst_rate, "missing-global"
    return gst_rate, "global"


def _resolve_item_inclusive(
    item: Mapping[str, Any],
    *,
    gst_type: str,
    product_wise_gst_enabled: bool,
) -> bool:
    if product_wise_gst_enabled and item.get("mode") == "products" and item.get("price_includes_tax") not in (None, ""):
        return _bool(item.get("price_includes_tax"), True)
    return str(gst_type or "inclusive").strip().lower() != "exclusive"


def build_gst_computation(
    items: Sequence[Mapping[str, Any]],
    *,
    gross_before_discount: float,
    gross_after_discount: float,
    gst_rate: float,
    gst_type: str,
    product_wise_gst_enabled: bool = False,
    gst_rate_source: str = "global",
    missing_item_gst_policy: str = "global",
    gst_category_rate_map: Mapping[str, Any] | None = None,
) -> GSTComputation:
    gross_before_discount = max(0.0, float(gross_before_discount or 0.0))
    gross_after_discount = max(0.0, float(gross_after_discount or 0.0))
    try:
        gst_rate = float(gst_rate)
    except Exception:
        gst_rate = 18.0
    if gross_before_discount <= 0 or gross_after_discount <= 0:
        return GSTComputation(
            gross_before_discount=gross_before_discount,
            gross_after_discount=gross_after_discount,
            taxable_amount=gross_after_discount,
            gst_amount=0.0,
            grand_total=gross_after_discount,
            gst_mode="item" if product_wise_gst_enabled else "global",
            rate_summary=(),
        )

    discount_factor = gross_after_discount / gross_before_discount
    summary: dict[float, dict[str, float | int]] = {}
    grand_total = 0.0
    gst_amount = 0.0

    for item in items:
        display_amount = max(0.0, _float(item.get("price"), 0.0) * _float(item.get("qty"), 1.0))
        discounted_amount = round(display_amount * discount_factor, 2)
        rate, _source = _resolve_item_rate(
            item,
            gst_rate=gst_rate,
            gst_rate_source=gst_rate_source,
            missing_item_gst_policy=missing_item_gst_policy,
            product_wise_gst_enabled=product_wise_gst_enabled,
            gst_category_rate_map=gst_category_rate_map,
        )
        inclusive = _resolve_item_inclusive(
            item,
            gst_type=gst_type,
            product_wise_gst_enabled=product_wise_gst_enabled,
        )

        if rate > 0:
            if inclusive:
                tax_amount = round(discounted_amount - (discounted_amount / (1 + (rate / 100.0))), 2)
                gross_amount = discounted_amount
                taxable_amount = round(gross_amount - tax_amount, 2)
            else:
                taxable_amount = discounted_amount
                tax_amount = round(taxable_amount * rate / 100.0, 2)
                gross_amount = round(taxable_amount + tax_amount, 2)
        else:
            tax_amount = 0.0
            taxable_amount = discounted_amount
            gross_amount = discounted_amount

        gst_amount += tax_amount
        grand_total += gross_amount

        bucket = summary.setdefault(rate, {"taxable": 0.0, "gst": 0.0, "gross": 0.0, "count": 0})
        bucket["taxable"] = float(bucket["taxable"]) + taxable_amount
        bucket["gst"] = float(bucket["gst"]) + tax_amount
        bucket["gross"] = float(bucket["gross"]) + gross_amount
        bucket["count"] = int(bucket["count"]) + 1

    rate_summary = tuple(
        GSTRateSummary(
            rate=rate,
            taxable_amount=round(float(bucket["taxable"]), 2),
            gst_amount=round(float(bucket["gst"]), 2),
            gross_amount=round(float(bucket["gross"]), 2),
            line_count=int(bucket["count"]),
        )
        for rate, bucket in sorted(summary.items(), key=lambda item: item[0])
    )
    taxable_amount = round(grand_total - gst_amount, 2)
    return GSTComputation(
        gross_before_discount=round(gross_before_discount, 2),
        gross_after_discount=round(gross_after_discount, 2),
        taxable_amount=taxable_amount,
        gst_amount=round(gst_amount, 2),
        grand_total=round(grand_total, 2),
        gst_mode="item" if product_wise_gst_enabled else "global",
        rate_summary=rate_summary,
    )
