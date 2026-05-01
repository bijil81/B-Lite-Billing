from __future__ import annotations

from src.blite_v6.reports.service_report import (
    build_service_report_rows,
    format_report_quantity,
    paginate_service_report_rows,
    parse_service_report_item,
    product_report_tree_values,
    service_report_tree_values,
)


def money(value):
    return f"Rs{float(value):.2f}"


def test_parse_service_report_item_supports_new_and_legacy_formats():
    new_item = parse_service_report_item("services~Hair Cut~300~2")
    legacy_item = parse_service_report_item("Threading:150")

    assert new_item.mode == "services"
    assert new_item.name == "Hair Cut"
    assert new_item.price == 300
    assert new_item.quantity == 2
    assert legacy_item.mode == "services"
    assert legacy_item.name == "Threading"
    assert legacy_item.price == 150
    assert legacy_item.quantity == 1
    assert parse_service_report_item("bad segment") is None
    assert parse_service_report_item("products~Rice~59.90~not-a-number") is None


def test_build_service_report_rows_aggregates_services_products_and_decimal_quantities():
    rows = [
        {"items_raw": "services~Hair Cut~300~1|products~Serum~200~2"},
        {"items_raw": "services~Hair Cut~300~2|products~Rice~59.90~1.24"},
        {"items_raw": "Threading:150|products~Rice~59.90~0.5"},
    ]

    report = build_service_report_rows(rows)
    services = {row.name: row for row in report.services}
    products = {row.name: row for row in report.products}

    assert services["Hair Cut"].count == 3
    assert services["Hair Cut"].revenue == 900
    assert services["Hair Cut"].avg == 300
    assert services["Threading"].count == 1
    assert products["Serum"].count == 2
    assert products["Serum"].revenue == 400
    assert products["Rice"].count == 1.74
    assert round(products["Rice"].revenue, 2) == 104.23


def test_build_service_report_rows_sorts_services_by_requested_column():
    rows = [
        {"items_raw": "services~A~100~1|services~B~50~5|services~C~500~1"},
    ]

    by_count = build_service_report_rows(rows, sort_col="Count", sort_reverse=True)
    by_name = build_service_report_rows(rows, sort_col="Service", sort_reverse=False)
    by_avg = build_service_report_rows(rows, sort_col="Avg", sort_reverse=True)

    assert [row.name for row in by_count.services] == ["B", "A", "C"]
    assert [row.name for row in by_name.services] == ["A", "B", "C"]
    assert [row.name for row in by_avg.services] == ["C", "A", "B"]


def test_paginate_service_report_rows_clamps_page():
    rows = tuple(range(5))

    first = paginate_service_report_rows(rows, -10, 2)
    last = paginate_service_report_rows(rows, 99, 2)

    assert first.page == 0
    assert first.max_page == 2
    assert first.rows == (0, 1)
    assert last.page == 2
    assert last.rows == (4,)


def test_tree_values_preserve_old_whole_counts_and_decimal_counts():
    report = build_service_report_rows(
        [
            {"items_raw": "services~Hair Cut~300~2|products~Rice~59.90~1.24"},
        ]
    )

    assert service_report_tree_values(report.services[0], money) == (
        "Hair Cut",
        "2",
        "Rs600.00",
        "Rs300.00",
    )
    assert product_report_tree_values(report.products[0], money) == (
        "Rice",
        "1.24",
        "Rs74.28",
    )
    assert format_report_quantity(1.2349) == "1.235"
