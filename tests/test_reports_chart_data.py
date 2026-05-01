from __future__ import annotations

from datetime import date

from src.blite_v6.reports.chart_data import (
    daily_revenue_series,
    monthly_revenue_series,
    payment_revenue_series,
    top_services_revenue_series,
)


def test_daily_revenue_series_fills_missing_days_and_keeps_last_30_order():
    rows = [
        {"date": "2026-04-29 10:00", "total": 100},
        {"date": "2026-04-28 10:00", "total": 50},
        {"date": "2026-04-29 11:00", "total": "25.5"},
    ]

    series = daily_revenue_series(rows, date(2026, 4, 29), days=3)

    assert series.labels == ("04-27", "04-28", "04-29")
    assert series.values == (0, 50.0, 125.5)


def test_monthly_revenue_series_keeps_latest_twelve_months():
    rows = [
        {"date": f"2025-{month:02d}-01", "total": month}
        for month in range(1, 13)
    ] + [{"date": "2026-01-01", "total": 100}]

    series = monthly_revenue_series(rows, months=12)

    assert series.labels[0] == "2025-02"
    assert series.labels[-1] == "2026-01"
    assert series.values[-1] == 100


def test_payment_revenue_series_groups_by_payment_method():
    rows = [
        {"payment": "Cash", "total": 100},
        {"payment": "UPI", "total": 50},
        {"payment": "Cash", "total": "25.5"},
        {"payment": "", "total": 10},
    ]

    series = payment_revenue_series(rows)

    assert series.labels == ("Cash", "UPI", "Unknown")
    assert series.values == (125.5, 50.0, 10.0)


def test_top_services_revenue_series_uses_decimal_quantities_and_limits_labels():
    rows = [
        {"items_raw": "services~Hair Cut~300~1|products~Serum~200~2"},
        {"items_raw": "services~Very Long Service Name For Label~100~1.5|services~Hair Cut~300~1"},
        {"items_raw": "Threading:150"},
    ]

    series = top_services_revenue_series(rows, limit=2, label_limit=10)

    assert series.labels == ("Hair Cut", "Very Long ")
    assert series.values == (600.0, 150.0)
