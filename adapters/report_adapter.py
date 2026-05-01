"""Compatibility adapter for read-side reporting via v5 service layer."""

from __future__ import annotations

from salon_settings import get_settings
from services_v5.report_service import ReportService


_service = ReportService()


def use_v5_reports_db() -> bool:
    return bool(get_settings().get("use_v5_reports_db", False))


def get_sales_summary_v5(from_date: str, to_date: str) -> dict:
    return _service.sales_summary(from_date, to_date)


def get_payment_breakdown_v5(from_date: str, to_date: str) -> list[dict]:
    return _service.payment_breakdown(from_date, to_date)


def get_report_rows_v5(from_date: str = "", to_date: str = "", search: str = "") -> list[dict]:
    return _service.report_rows(from_date, to_date, search)