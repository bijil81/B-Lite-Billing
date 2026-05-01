"""Workflow layer for v5 reports."""

from __future__ import annotations

from repositories.reports_repo import ReportsRepository


class ReportService:
    def __init__(self, repo: ReportsRepository | None = None):
        self.repo = repo or ReportsRepository()

    def sales_summary(self, from_date: str, to_date: str) -> dict:
        data = self.repo.sales_summary(from_date, to_date)
        data["profit_estimate"] = float(data.get("net_total", 0.0) or 0.0) - float(data.get("expense_total", 0.0) or 0.0)
        return data

    def payment_breakdown(self, from_date: str, to_date: str) -> list[dict]:
        return self.repo.payment_breakdown(from_date, to_date)

    def top_services(self, from_date: str, to_date: str) -> list[dict]:
        return self.repo.top_services(from_date, to_date)

    def report_rows(self, from_date: str = "", to_date: str = "", search: str = "") -> list[dict]:
        return self.repo.report_rows(from_date, to_date, search)