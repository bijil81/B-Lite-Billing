from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping

from .gst_breakdown import GSTRateSummary, GSTComputation, build_gst_computation
from ..settings.core import get_settings


OfferCalculator = Callable[[Any, Iterable[Mapping[str, Any]], float], float]
RedeemCalculator = Callable[[Any, float], float]


@dataclass(frozen=True)
class BillingTotals:
    service_subtotal: float
    product_subtotal: float
    total: float
    discount: float
    membership_discount: float
    points_discount: float
    offer_discount: float
    redeem_discount: float
    grand_total: float
    gst_amount: float
    taxable_amount: float = 0.0
    gst_mode: str = "global"
    gst_breakdown: tuple[GSTRateSummary, ...] = ()
    points_customer_missing: bool = False

    def as_legacy_tuple(self) -> tuple[float, float, float, float, float, float, float, float, float, float]:
        return (
            self.service_subtotal,
            self.product_subtotal,
            self.total,
            self.discount,
            self.membership_discount,
            self.points_discount,
            self.offer_discount,
            self.redeem_discount,
            self.grand_total,
            self.gst_amount,
        )


def calculate_billing_totals(
    *,
    items: list[Mapping[str, Any]],
    discount_enabled: bool = False,
    discount_value: float = 0.0,
    membership_disc_pct: float = 0.0,
    use_points: bool = False,
    customer_points: int | None = None,
    applied_offer: Any = None,
    applied_redeem_code: Any = None,
    apply_offer_fn: OfferCalculator | None = None,
    calc_redeem_discount_fn: RedeemCalculator | None = None,
    gst_enabled: bool = False,
    gst_rate: float = 18.0,
    gst_type: str = "inclusive",
    product_wise_gst_enabled: bool = False,
    gst_rate_source: str = "global",
    missing_item_gst_policy: str = "global",
    gst_category_rate_map: Mapping[str, Any] | None = None,
) -> BillingTotals:
    """Calculate billing totals with the same ordering as V5.6 BillingFrame._calc_totals."""
    service_items = [item for item in items if item["mode"] == "services"]
    product_items = [item for item in items if item["mode"] == "products"]
    service_subtotal = sum(item["price"] * item["qty"] for item in service_items)
    product_subtotal = sum(item["price"] * item["qty"] for item in product_items)
    total = service_subtotal + product_subtotal

    discount = 0.0
    if discount_enabled:
        discount = min(total, max(0.0, discount_value))

    membership_discount = 0.0
    if membership_disc_pct > 0:
        membership_discount = round(service_subtotal * membership_disc_pct / 100, 2)
        membership_discount = max(0.0, min(membership_discount, max(0.0, total - discount)))

    points_discount = 0.0
    points_customer_missing = False
    if use_points:
        if customer_points is None:
            points_customer_missing = True
        else:
            remaining_for_points = max(0.0, total - discount - membership_discount)
            points_discount = float(min(int(customer_points), int(remaining_for_points)))

    offer_discount = 0.0
    if applied_offer and apply_offer_fn:
        offer_discount = apply_offer_fn(
            applied_offer,
            items,
            max(0.0, total - discount - membership_discount - points_discount),
        )
        offer_discount = max(0.0, offer_discount)

    redeem_discount = 0.0
    if applied_redeem_code and calc_redeem_discount_fn:
        redeem_discount = calc_redeem_discount_fn(
            applied_redeem_code,
            max(0.0, total - discount - membership_discount - points_discount - offer_discount),
        )
        redeem_discount = max(0.0, redeem_discount)

    grand_total = max(
        0.0,
        total - discount - membership_discount - points_discount - offer_discount - redeem_discount,
    )
    gst_amount = 0.0
    taxable_amount = grand_total
    gst_mode = "item" if product_wise_gst_enabled else "global"
    gst_breakdown: tuple[GSTRateSummary, ...] = ()
    if gst_enabled and grand_total > 0:
        gst_source = str(gst_rate_source or "global").strip().lower()
        if not product_wise_gst_enabled and gst_source == "global":
            try:
                rate = float(gst_rate) / 100
            except Exception:
                rate = 18.0 / 100
            if str(gst_type or "inclusive").strip().lower() == "inclusive":
                gst_amount = grand_total - (grand_total / (1 + rate))
            else:
                gst_amount = grand_total * rate
                grand_total = grand_total + gst_amount
            taxable_amount = round(grand_total - gst_amount, 2)
            gst_breakdown = (
                GSTRateSummary(
                    rate=round(rate * 100, 2),
                    taxable_amount=round(grand_total - gst_amount, 2),
                    gst_amount=round(gst_amount, 2),
                    gross_amount=round(grand_total, 2),
                    line_count=len(items),
                ),
            )
        else:
            try:
                settings_category_map = gst_category_rate_map
                if settings_category_map is None:
                    settings_category_map = get_settings().get("gst_category_rate_map", {})
                computation: GSTComputation = build_gst_computation(
                    items,
                    gross_before_discount=total,
                    gross_after_discount=grand_total,
                    gst_rate=gst_rate,
                    gst_type=gst_type,
                    product_wise_gst_enabled=product_wise_gst_enabled,
                    gst_rate_source=gst_rate_source,
                    missing_item_gst_policy=missing_item_gst_policy,
                    gst_category_rate_map=settings_category_map,
                )
                gst_amount = computation.gst_amount
                grand_total = computation.grand_total
                taxable_amount = computation.taxable_amount
                gst_mode = computation.gst_mode
                gst_breakdown = computation.rate_summary
            except Exception:
                try:
                    rate = float(gst_rate) / 100
                except Exception:
                    rate = 18.0 / 100
                if gst_type == "inclusive":
                    gst_amount = grand_total - (grand_total / (1 + rate))
                else:
                    gst_amount = grand_total * rate
                    grand_total = grand_total + gst_amount
                taxable_amount = round(grand_total - gst_amount, 2)

    return BillingTotals(
        service_subtotal=service_subtotal,
        product_subtotal=product_subtotal,
        total=total,
        discount=discount,
        membership_discount=membership_discount,
        points_discount=points_discount,
        offer_discount=offer_discount,
        redeem_discount=redeem_discount,
        grand_total=grand_total,
        gst_amount=gst_amount,
        taxable_amount=taxable_amount,
        gst_mode=gst_mode,
        gst_breakdown=gst_breakdown,
        points_customer_missing=points_customer_missing,
    )
