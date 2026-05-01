"""Export wrapper helpers for ReportsFrame."""
from __future__ import annotations

from typing import Any, Callable, NamedTuple


class ReportFilters(NamedTuple):
    from_d: str
    to_d: str
    search: str


class ExportCallResult(NamedTuple):
    path: str | None
    success_prefix: str
    empty_message: str


class ExportUiResult(NamedTuple):
    success: bool
    title: str
    message: str
    should_open: bool
    path: str | None


def collect_report_filters(from_d: Any = "", to_d: Any = "", search: Any = "") -> ReportFilters:
    return ReportFilters(
        str(from_d or "").strip(),
        str(to_d or "").strip(),
        str(search or "").strip(),
    )


def build_export_ui_result(
    path: str | None,
    success_prefix: str,
    empty_message: str,
    *,
    open_after: bool = True,
) -> ExportUiResult:
    if path:
        return ExportUiResult(
            success=True,
            title="Exported",
            message=f"{success_prefix}:\n{path}",
            should_open=open_after,
            path=path,
        )
    return ExportUiResult(
        success=False,
        title="Export Info",
        message=empty_message,
        should_open=False,
        path=None,
    )


def selected_customer_from_row(row: dict[str, Any] | None) -> tuple[str, str]:
    row = row or {}
    return str(row.get("phone", "")).strip(), str(row.get("name", "")).strip()


def customer_ledger_success_label(phone: str, name: str) -> str:
    return f"Customer ledger saved for {name or phone}" if (phone or name) else "Customer ledger saved"


def run_search_export(
    exporter: Callable[[str, str, str], str | None],
    filters: ReportFilters,
    success_prefix: str,
    empty_message: str,
) -> ExportCallResult:
    return ExportCallResult(
        exporter(filters.from_d, filters.to_d, filters.search),
        success_prefix,
        empty_message,
    )


def run_date_export(
    exporter: Callable[[str, str], str | None],
    filters: ReportFilters,
    success_prefix: str,
    empty_message: str,
) -> ExportCallResult:
    return ExportCallResult(
        exporter(filters.from_d, filters.to_d),
        success_prefix,
        empty_message,
    )


def run_customer_ledger_export(
    exporter: Callable[[str, str, str], str | None],
    filters: ReportFilters,
    phone: str,
    name: str,
    empty_message: str,
) -> ExportCallResult:
    return ExportCallResult(
        exporter(phone, filters.from_d, filters.to_d),
        customer_ledger_success_label(phone, name),
        empty_message,
    )
