"""Retail/grocery sales summaries for reports and daily closing."""
from __future__ import annotations

import ast
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence


@dataclass(frozen=True)
class ReportLine:
    mode: str
    name: str
    unit_price: float
    quantity: float
    unit: str = ""
    gst_rate: float | None = None
    cost_price: float | None = None
    category: str = ""

    @property
    def revenue(self) -> float:
        return round(self.unit_price * self.quantity, 2)

    @property
    def cost_total(self) -> float:
        if self.cost_price is None:
            return 0.0
        return round(self.cost_price * self.quantity, 2)

    @property
    def profit(self) -> float:
        if self.cost_price is None:
            return 0.0
        return round(self.revenue - self.cost_total, 2)


@dataclass(frozen=True)
class SalesSummaryRow:
    name: str
    quantity: float
    revenue: float
    unit: str = ""
    cost: float = 0.0
    profit: float = 0.0


@dataclass(frozen=True)
class GstSummaryRow:
    rate: float
    taxable_amount: float
    gst_amount: float
    gross_amount: float
    line_count: int


@dataclass(frozen=True)
class ClosingRetailSummary:
    bill_count: int
    gross_sales: float
    revenue: float
    discount: float
    expenses: float
    net_profit: float
    service_revenue: float
    product_revenue: float
    product_quantity: float
    gst_total: float
    top_services: tuple[SalesSummaryRow, ...]
    top_products: tuple[SalesSummaryRow, ...]
    gst_rows: tuple[GstSummaryRow, ...]


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def format_quantity(value: float) -> str:
    numeric = float(value or 0.0)
    if numeric.is_integer():
        return str(int(numeric))
    return f"{numeric:.3f}".rstrip("0").rstrip(".")


def parse_report_line(segment: Any) -> ReportLine | None:
    text = str(segment or "").strip()
    if not text:
        return None

    parts = [part.strip() for part in text.split("~")]
    if len(parts) >= 4:
        name = parts[1]
        qty = safe_float(parts[3], -1.0)
        if not name or qty <= 0:
            return None
        gst_rate = safe_float(parts[5], None) if len(parts) > 5 and parts[5] != "" else None
        cost_price = safe_float(parts[6], None) if len(parts) > 6 and parts[6] != "" else None
        return ReportLine(
            mode=(parts[0] or "services").lower(),
            name=name,
            unit_price=safe_float(parts[2]),
            quantity=qty,
            unit=parts[4] if len(parts) > 4 else "",
            gst_rate=gst_rate,
            cost_price=cost_price,
            category=parts[7] if len(parts) > 7 else "",
        )

    if ":" in text:
        name, price_text = text.rsplit(":", 1)
        name = name.strip()
        if not name:
            return None
        return ReportLine(
            mode="services",
            name=name,
            unit_price=safe_float(price_text),
            quantity=1.0,
        )

    return None


def iter_report_lines(rows: Sequence[Mapping[str, Any]]) -> Iterable[ReportLine]:
    for row in rows:
        for segment in str(row.get("items_raw", "") or "").split("|"):
            line = parse_report_line(segment)
            if line is not None:
                yield line


def _build_sales_rows(lines: Iterable[ReportLine]) -> tuple[SalesSummaryRow, ...]:
    buckets: dict[str, dict[str, Any]] = {}
    for line in lines:
        bucket = buckets.setdefault(
            line.name,
            {"quantity": 0.0, "revenue": 0.0, "cost": 0.0, "profit": 0.0, "unit": line.unit},
        )
        bucket["quantity"] += line.quantity
        bucket["revenue"] += line.revenue
        bucket["cost"] += line.cost_total
        bucket["profit"] += line.profit
        if not bucket["unit"] and line.unit:
            bucket["unit"] = line.unit

    rows = [
        SalesSummaryRow(
            name=name,
            quantity=round(data["quantity"], 3),
            revenue=round(data["revenue"], 2),
            unit=str(data["unit"] or ""),
            cost=round(data["cost"], 2),
            profit=round(data["profit"], 2),
        )
        for name, data in buckets.items()
    ]
    rows.sort(key=lambda row: row.revenue, reverse=True)
    return tuple(rows)


def build_service_sales_summary(rows: Sequence[Mapping[str, Any]]) -> tuple[SalesSummaryRow, ...]:
    return _build_sales_rows(line for line in iter_report_lines(rows) if line.mode == "services")


def build_product_sales_summary(rows: Sequence[Mapping[str, Any]]) -> tuple[SalesSummaryRow, ...]:
    return _build_sales_rows(line for line in iter_report_lines(rows) if line.mode != "services")


def _parse_gst_entries(raw: Any) -> list[Mapping[str, Any]]:
    if not raw:
        return []
    if isinstance(raw, (list, tuple)):
        return [entry for entry in raw if isinstance(entry, Mapping)]
    if isinstance(raw, str):
        try:
            parsed = ast.literal_eval(raw)
        except (SyntaxError, ValueError):
            return []
        if isinstance(parsed, (list, tuple)):
            return [entry for entry in parsed if isinstance(entry, Mapping)]
    return []


def build_gst_summary(rows: Sequence[Mapping[str, Any]]) -> tuple[GstSummaryRow, ...]:
    buckets: defaultdict[float, dict[str, float | int]] = defaultdict(
        lambda: {"taxable": 0.0, "gst": 0.0, "gross": 0.0, "count": 0}
    )
    unknown_taxable = 0.0
    unknown_gst = 0.0
    unknown_gross = 0.0

    for row in rows:
        entries = _parse_gst_entries(row.get("gst_breakdown"))
        if entries:
            for entry in entries:
                rate = safe_float(entry.get("rate"))
                bucket = buckets[rate]
                taxable = safe_float(entry.get("taxable_amount", entry.get("taxable")))
                gst = safe_float(entry.get("gst_amount", entry.get("gst")))
                gross = safe_float(entry.get("gross_amount", entry.get("gross")), taxable + gst)
                bucket["taxable"] = float(bucket["taxable"]) + taxable
                bucket["gst"] = float(bucket["gst"]) + gst
                bucket["gross"] = float(bucket["gross"]) + gross
                bucket["count"] = int(bucket["count"]) + int(safe_float(entry.get("line_count"), 1))
            continue

        gst_amount = safe_float(row.get("gst_amount", row.get("tax_total")))
        if gst_amount > 0:
            taxable = safe_float(row.get("taxable_amount"), safe_float(row.get("total")) - gst_amount)
            unknown_taxable += taxable
            unknown_gst += gst_amount
            unknown_gross += taxable + gst_amount
            continue

        for line in iter_report_lines((row,)):
            if line.gst_rate is None:
                continue
            rate = safe_float(line.gst_rate)
            gross = line.revenue
            if rate > 0:
                taxable = round(gross / (1 + (rate / 100)), 2)
                gst = round(gross - taxable, 2)
            else:
                taxable = gross
                gst = 0.0
            bucket = buckets[rate]
            bucket["taxable"] = float(bucket["taxable"]) + taxable
            bucket["gst"] = float(bucket["gst"]) + gst
            bucket["gross"] = float(bucket["gross"]) + gross
            bucket["count"] = int(bucket["count"]) + 1

    result = [
        GstSummaryRow(
            rate=rate,
            taxable_amount=round(float(data["taxable"]), 2),
            gst_amount=round(float(data["gst"]), 2),
            gross_amount=round(float(data["gross"]), 2),
            line_count=int(data["count"]),
        )
        for rate, data in buckets.items()
    ]
    if unknown_gst > 0:
        result.append(
            GstSummaryRow(
                rate=-1.0,
                taxable_amount=round(unknown_taxable, 2),
                gst_amount=round(unknown_gst, 2),
                gross_amount=round(unknown_gross, 2),
                line_count=0,
            )
        )
    result.sort(key=lambda row: row.rate)
    return tuple(result)


def build_closing_retail_summary(
    rows: Sequence[Mapping[str, Any]],
    expenses: Sequence[Mapping[str, Any]] | None = None,
) -> ClosingRetailSummary:
    total_revenue = round(sum(safe_float(row.get("total")) for row in rows), 2)
    total_discount = round(sum(safe_float(row.get("discount")) for row in rows), 2)
    total_expenses = round(sum(safe_float(row.get("amount")) for row in (expenses or ())), 2)
    service_rows = build_service_sales_summary(rows)
    product_rows = build_product_sales_summary(rows)
    gst_rows = build_gst_summary(rows)
    service_revenue = round(sum(row.revenue for row in service_rows), 2)
    product_revenue = round(sum(row.revenue for row in product_rows), 2)
    line_sales = round(service_revenue + product_revenue, 2)
    gross_sales = line_sales if line_sales > 0 else round(total_revenue + total_discount, 2)
    product_quantity = round(sum(row.quantity for row in product_rows), 3)
    gst_total = round(sum(row.gst_amount for row in gst_rows), 2)

    return ClosingRetailSummary(
        bill_count=len(rows),
        gross_sales=gross_sales,
        revenue=total_revenue,
        discount=total_discount,
        expenses=total_expenses,
        net_profit=round(total_revenue - total_expenses, 2),
        service_revenue=service_revenue,
        product_revenue=product_revenue,
        product_quantity=product_quantity,
        gst_total=gst_total,
        top_services=tuple(service_rows[:8]),
        top_products=tuple(product_rows[:8]),
        gst_rows=gst_rows,
    )
