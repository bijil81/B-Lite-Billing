"""Pure report list view-model helpers for ReportsFrame."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class ReportSummary:
    today_total: float
    month_total: float
    filtered_total: float
    count: int
    average: float


@dataclass(frozen=True)
class ReportPage:
    rows: list[dict[str, Any]]
    total: int
    page: int
    max_page: int
    start: int
    end: int


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def build_report_summary(rows: list[dict[str, Any]], today_iso: str, month_iso: str) -> ReportSummary:
    today_total = 0.0
    month_total = 0.0
    filtered_total = 0.0

    for row in rows:
        date_text = str(row.get("date", ""))
        total = _safe_float(row.get("total"))
        filtered_total += total
        if date_text[:10] == today_iso:
            today_total += total
        if date_text[:7] == month_iso:
            month_total += total

    count = len(rows)
    average = filtered_total / count if count else 0.0
    return ReportSummary(
        today_total=today_total,
        month_total=month_total,
        filtered_total=filtered_total,
        count=count,
        average=average,
    )


def max_report_page(total: int, page_size: int) -> int:
    if total <= 0 or page_size <= 0:
        return 0
    return max(0, (total - 1) // page_size)


def paginate_report_rows(rows: list[dict[str, Any]], page: int, page_size: int) -> ReportPage:
    total = len(rows)
    max_page = max_report_page(total, page_size)
    current_page = min(max(0, page), max_page)
    if page_size <= 0:
        return ReportPage(rows=list(rows), total=total, page=0, max_page=0, start=0, end=total)
    start = current_page * page_size
    end = start + page_size
    return ReportPage(
        rows=list(rows[start:end]),
        total=total,
        page=current_page,
        max_page=max_page,
        start=start,
        end=end,
    )


def report_tree_values(
    row: dict[str, Any],
    *,
    display_date: Callable[[str], str],
    currency: Callable[[Any], str],
) -> tuple[str, str, str, str, str, str, str, str]:
    raw_date = str(row.get("date", ""))
    date_prefix = raw_date[:10]
    try:
        date_value = display_date(date_prefix) if date_prefix else raw_date
    except Exception:
        date_value = raw_date

    return (
        date_value,
        str(row.get("time", raw_date[11:16])),
        str(row.get("invoice", "")),
        str(row.get("name", "")),
        str(row.get("phone", "")),
        str(row.get("payment", "")),
        currency(row.get("discount", 0.0)),
        currency(row.get("total", 0.0)),
    )


def report_result_message(total: int, page_size: int, search: str) -> str:
    shown = min(total, page_size) if total > 0 and page_size > 0 else 0
    search = (search or "").strip()
    if total == 0 and search:
        return "No invoices found"
    if search:
        return f"{shown} matching invoice{'s' if shown != 1 else ''}"
    return f"Showing {shown} of {total} invoice{'s' if total != 1 else ''}"
