from __future__ import annotations

from src.blite_v6.reports.report_view import (
    build_report_summary,
    max_report_page,
    paginate_report_rows,
    report_result_message,
    report_tree_values,
)


def test_build_report_summary_calculates_today_month_total_and_average():
    rows = [
        {"date": "2026-04-29 09:00", "total": 100.0},
        {"date": "2026-04-28 09:00", "total": "50.5"},
        {"date": "2026-03-01 09:00", "total": 25.0},
    ]

    summary = build_report_summary(rows, "2026-04-29", "2026-04")

    assert summary.today_total == 100.0
    assert summary.month_total == 150.5
    assert summary.filtered_total == 175.5
    assert summary.count == 3
    assert summary.average == 58.5


def test_paginate_report_rows_clamps_page_and_slices_rows():
    rows = [{"invoice": f"INV-{idx}"} for idx in range(5)]

    first = paginate_report_rows(rows, 0, 2)
    last = paginate_report_rows(rows, 99, 2)

    assert first.page == 0
    assert first.max_page == 2
    assert [row["invoice"] for row in first.rows] == ["INV-0", "INV-1"]
    assert last.page == 2
    assert [row["invoice"] for row in last.rows] == ["INV-4"]


def test_max_report_page_handles_empty_and_invalid_page_size():
    assert max_report_page(0, 80) == 0
    assert max_report_page(10, 0) == 0
    assert max_report_page(81, 80) == 1


def test_report_tree_values_formats_legacy_report_row_for_treeview():
    row = {
        "date": "2026-04-29 10:45:00",
        "invoice": "INV-10",
        "name": "Anu",
        "phone": "9999999999",
        "payment": "UPI",
        "discount": 5,
        "total": 120.5,
    }

    values = report_tree_values(
        row,
        display_date=lambda value: "29-04-2026" if value == "2026-04-29" else value,
        currency=lambda value: f"Rs{float(value):.2f}",
    )

    assert values == (
        "29-04-2026",
        "10:45",
        "INV-10",
        "Anu",
        "9999999999",
        "UPI",
        "Rs5.00",
        "Rs120.50",
    )


def test_report_result_message_matches_existing_ui_copy():
    assert report_result_message(0, 80, "anu") == "No invoices found"
    assert report_result_message(1, 80, "anu") == "1 matching invoice"
    assert report_result_message(5, 80, "anu") == "5 matching invoices"
    assert report_result_message(81, 80, "") == "Showing 80 of 81 invoices"
