from __future__ import annotations

from src.blite_v6.reports.export_actions import (
    build_export_ui_result,
    collect_report_filters,
    run_customer_ledger_export,
    run_date_export,
    run_search_export,
    selected_customer_from_row,
)


def test_collect_report_filters_normalizes_values():
    filters = collect_report_filters(" 2026-04-01 ", " 2026-04-29 ", "  anu ")

    assert filters.from_d == "2026-04-01"
    assert filters.to_d == "2026-04-29"
    assert filters.search == "anu"


def test_build_export_ui_result_for_success_and_empty_result():
    success = build_export_ui_result("C:/tmp/sales.xlsx", "Excel saved", "No data")
    empty = build_export_ui_result(None, "Excel saved", "No data")

    assert success.success is True
    assert success.title == "Exported"
    assert success.message == "Excel saved:\nC:/tmp/sales.xlsx"
    assert success.should_open is True
    assert success.path == "C:/tmp/sales.xlsx"
    assert empty.success is False
    assert empty.title == "Export Info"
    assert empty.message == "No data"
    assert empty.should_open is False


def test_build_export_ui_result_respects_open_after_flag():
    result = build_export_ui_result("C:/tmp/sales.pdf", "PDF saved", "No data", open_after=False)

    assert result.success is True
    assert result.should_open is False


def test_selected_customer_from_row_trims_phone_and_name():
    phone, name = selected_customer_from_row({"phone": " 9999999999 ", "name": " Anu "})

    assert phone == "9999999999"
    assert name == "Anu"
    assert selected_customer_from_row(None) == ("", "")


def test_run_search_export_passes_date_and_search_filters():
    calls = []
    filters = collect_report_filters("2026-04-01", "2026-04-29", "body")

    def exporter(from_d, to_d, search):
        calls.append((from_d, to_d, search))
        return "sales.xlsx"

    result = run_search_export(exporter, filters, "Excel saved", "No data")

    assert calls == [("2026-04-01", "2026-04-29", "body")]
    assert result.path == "sales.xlsx"
    assert result.success_prefix == "Excel saved"
    assert result.empty_message == "No data"


def test_run_date_export_passes_only_date_filters():
    calls = []
    filters = collect_report_filters("2026-04-01", "2026-04-29", "ignored")

    def exporter(from_d, to_d):
        calls.append((from_d, to_d))
        return "gst.xlsx"

    result = run_date_export(exporter, filters, "GST summary saved", "No data")

    assert calls == [("2026-04-01", "2026-04-29")]
    assert result.path == "gst.xlsx"
    assert result.success_prefix == "GST summary saved"


def test_run_customer_ledger_export_uses_selected_customer_label():
    calls = []
    filters = collect_report_filters("2026-04-01", "2026-04-29", "")

    def exporter(phone, from_d, to_d):
        calls.append((phone, from_d, to_d))
        return "customer-ledger.xlsx"

    result = run_customer_ledger_export(
        exporter,
        filters,
        "9999999999",
        "Anu",
        "No ledger",
    )

    assert calls == [("9999999999", "2026-04-01", "2026-04-29")]
    assert result.path == "customer-ledger.xlsx"
    assert result.success_prefix == "Customer ledger saved for Anu"
    assert result.empty_message == "No ledger"
