from __future__ import annotations

from src.blite_v6.reports.retail_summary import (
    build_closing_retail_summary,
    build_gst_summary,
    build_product_sales_summary,
    build_service_sales_summary,
    format_quantity,
    parse_report_line,
)


def test_parse_report_line_supports_legacy_and_future_rich_product_segments():
    legacy = parse_report_line("Threading:150")
    grocery = parse_report_line("products~Tomato Loose~45.50~1.236~kg~0~32.25~Vegetables")

    assert legacy.mode == "services"
    assert legacy.name == "Threading"
    assert legacy.revenue == 150
    assert grocery.mode == "products"
    assert grocery.name == "Tomato Loose"
    assert grocery.quantity == 1.236
    assert grocery.unit == "kg"
    assert grocery.gst_rate == 0
    assert grocery.cost_price == 32.25
    assert grocery.category == "Vegetables"
    assert round(grocery.profit, 2) == 16.38


def test_product_and_service_summaries_preserve_decimal_grocery_quantities():
    rows = [
        {"items_raw": "services~Hair Cut~300~1|products~Rice 1kg~62~2"},
        {"items_raw": "products~Tomato Loose~45.50~1.24~kg~0~32.25~Vegetables"},
        {"items_raw": "Threading:150"},
    ]

    services = {row.name: row for row in build_service_sales_summary(rows)}
    products = {row.name: row for row in build_product_sales_summary(rows)}

    assert services["Hair Cut"].quantity == 1
    assert services["Threading"].revenue == 150
    assert products["Rice 1kg"].quantity == 2
    assert products["Rice 1kg"].revenue == 124
    assert products["Tomato Loose"].quantity == 1.24
    assert products["Tomato Loose"].unit == "kg"
    assert products["Tomato Loose"].revenue == 56.42
    assert products["Tomato Loose"].profit == 16.43


def test_gst_summary_aggregates_saved_rate_breakdowns_and_db_tax_fallback():
    rows = [
        {
            "gst_breakdown": [
                {"rate": 5, "taxable_amount": 100, "gst_amount": 5, "gross_amount": 105, "line_count": 1},
                {"rate": 18, "taxable_amount": 200, "gst_amount": 36, "gross_amount": 236, "line_count": 2},
            ]
        },
        {
            "gst_breakdown": "[{'rate': 5, 'taxable_amount': 50, 'gst_amount': 2.5, 'gross_amount': 52.5}]"
        },
        {"total": 118, "gst_amount": 18, "taxable_amount": 100},
    ]

    summary = build_gst_summary(rows)
    by_rate = {row.rate: row for row in summary}

    assert by_rate[5].taxable_amount == 150
    assert by_rate[5].gst_amount == 7.5
    assert by_rate[5].line_count == 2
    assert by_rate[18].gst_amount == 36
    assert by_rate[-1].taxable_amount == 100
    assert by_rate[-1].gst_amount == 18


def test_gst_summary_falls_back_to_rich_saved_line_metadata():
    rows = [
        {"items_raw": "products~Banana Loose~38~1.5~kg~0~28~Fruits"},
        {"items_raw": "products~Oil 1L~160~1~pcs~5~120~Grocery"},
    ]

    summary = build_gst_summary(rows)
    by_rate = {row.rate: row for row in summary}

    assert by_rate[0].taxable_amount == 57
    assert by_rate[0].gst_amount == 0
    assert by_rate[5].gross_amount == 160
    assert by_rate[5].taxable_amount == 152.38
    assert by_rate[5].gst_amount == 7.62


def test_closing_retail_summary_combines_bills_expenses_products_services_and_gst():
    rows = [
        {
            "total": 417,
            "discount": 40,
            "items_raw": "services~Aroma Oil~800~0.5|products~Banana Loose~38~1.5~kg~0~28~Fruits",
            "gst_breakdown": [{"rate": 0, "taxable_amount": 57, "gst_amount": 0, "gross_amount": 57}],
        },
        {
            "total": 145,
            "discount": 0,
            "items_raw": "products~Sunflower Oil 1L~145~1~pcs~5~120~Grocery",
            "gst_breakdown": [{"rate": 5, "taxable_amount": 138.1, "gst_amount": 6.9, "gross_amount": 145}],
        },
    ]
    expenses = [{"amount": 100}]

    summary = build_closing_retail_summary(rows, expenses)

    assert summary.bill_count == 2
    assert summary.gross_sales == 602
    assert summary.revenue == 562
    assert summary.discount == 40
    assert summary.expenses == 100
    assert summary.net_profit == 462
    assert summary.service_revenue == 400
    assert summary.product_revenue == 202
    assert summary.product_quantity == 2.5
    assert summary.gst_total == 6.9
    assert summary.top_products[0].name == "Sunflower Oil 1L"
    assert summary.top_services[0].name == "Aroma Oil"


def test_format_quantity_keeps_closing_pdf_labels_clean():
    assert format_quantity(1.0) == "1"
    assert format_quantity(1.236) == "1.236"
    assert format_quantity(1.2) == "1.2"
