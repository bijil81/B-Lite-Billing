"""Chart data builders for ReportsFrame."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any, NamedTuple, Sequence

from src.blite_v6.reports.service_report import parse_service_report_item


class ChartSeries(NamedTuple):
    labels: tuple[str, ...]
    values: tuple[float, ...]


def daily_revenue_series(rows: Sequence[dict[str, Any]], today: date, days: int = 30) -> ChartSeries:
    daily: defaultdict[str, float] = defaultdict(float)
    for row in rows:
        day = str(row.get("date", ""))[:10]
        if day:
            daily[day] += float(row.get("total", 0) or 0)

    day_keys = [(today - timedelta(days=idx)).strftime("%Y-%m-%d") for idx in range(days - 1, -1, -1)]
    return ChartSeries(
        tuple(day[-5:] for day in day_keys),
        tuple(daily[day] for day in day_keys),
    )


def monthly_revenue_series(rows: Sequence[dict[str, Any]], months: int = 12) -> ChartSeries:
    monthly: defaultdict[str, float] = defaultdict(float)
    for row in rows:
        month = str(row.get("date", ""))[:7]
        if month:
            monthly[month] += float(row.get("total", 0) or 0)

    sorted_months = sorted(monthly.items())[-months:]
    return ChartSeries(
        tuple(month for month, _value in sorted_months),
        tuple(value for _month, value in sorted_months),
    )


def payment_revenue_series(rows: Sequence[dict[str, Any]]) -> ChartSeries:
    payments: defaultdict[str, float] = defaultdict(float)
    for row in rows:
        payment = str(row.get("payment", "") or "Unknown")
        payments[payment] += float(row.get("total", 0) or 0)

    return ChartSeries(tuple(payments.keys()), tuple(payments.values()))


def top_services_revenue_series(rows: Sequence[dict[str, Any]], limit: int = 10, label_limit: int = 22) -> ChartSeries:
    service_totals: defaultdict[str, float] = defaultdict(float)
    for row in rows:
        for segment in str(row.get("items_raw", "") or "").split("|"):
            item = parse_service_report_item(segment)
            if item is None or item.mode != "services":
                continue
            service_totals[item.name] += item.price * item.quantity

    top_services = sorted(service_totals.items(), key=lambda item: item[1], reverse=True)[:limit]
    return ChartSeries(
        tuple(name[:label_limit] for name, _value in top_services),
        tuple(value for _name, value in top_services),
    )
