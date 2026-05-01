from __future__ import annotations

from datetime import date

from src.blite_v6.reports.grocery_report_view import resolve_period_range


def test_resolve_period_range_supports_day_week_and_month():
    today = date(2026, 5, 1)

    assert resolve_period_range("day", today).from_date == "2026-05-01"
    assert resolve_period_range("day", today).to_date == "2026-05-01"
    assert resolve_period_range("week", today).from_date == "2026-04-27"
    assert resolve_period_range("week", today).to_date == "2026-05-01"
    assert resolve_period_range("month", today).from_date == "2026-05-01"
    assert resolve_period_range("month", today).to_date == "2026-05-01"


def test_resolve_period_range_defaults_to_month_for_unknown_period():
    resolved = resolve_period_range("unknown", date(2026, 5, 18))

    assert resolved.label == "Custom"
    assert resolved.from_date == "2026-05-01"
    assert resolved.to_date == "2026-05-18"
