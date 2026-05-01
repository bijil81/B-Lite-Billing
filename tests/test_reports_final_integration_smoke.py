from __future__ import annotations

import ast
import importlib
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_PY = PROJECT_ROOT / "reports.py"


def _imports_from(module: ast.Module, source_module: str) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(module):
        if isinstance(node, ast.ImportFrom) and node.module == source_module:
            names.update(alias.name for alias in node.names)
    return names


def test_reports_public_shell_remains_importable():
    reports = importlib.import_module("reports")

    assert hasattr(reports, "ReportsFrame")
    assert hasattr(reports, "_read_report")


def test_all_split_report_modules_remain_importable():
    modules = [
        "src.blite_v6.reports.bill_text",
        "src.blite_v6.reports.saved_bills",
        "src.blite_v6.reports.report_view",
        "src.blite_v6.reports.export_actions",
        "src.blite_v6.reports.service_report",
        "src.blite_v6.reports.retail_summary",
        "src.blite_v6.reports.delete_restore",
        "src.blite_v6.reports.chart_data",
        "src.blite_v6.reports.grocery_report_view",
    ]

    for module_name in modules:
        assert importlib.import_module(module_name)


def test_reports_py_still_wires_each_extracted_responsibility():
    source = REPORTS_PY.read_text(encoding="utf-8")

    expected_symbols = [
        "_build_bill_text",
        "list_saved_bill_files",
        "build_report_summary",
        "run_search_export",
        "build_service_report_rows",
        "build_report_sales_context_row",
        "daily_revenue_series",
        "GroceryReportPanel",
    ]

    for symbol in expected_symbols:
        assert symbol in source


def test_reports_py_import_surface_stays_shrunk():
    tree = ast.parse(REPORTS_PY.read_text(encoding="utf-8"))

    utils_imports = _imports_from(tree, "utils")
    reports_export_imports = _imports_from(tree, "reports_export")
    top_level_imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }

    assert "safe_float" not in utils_imports
    assert "DATA_DIR" not in utils_imports
    assert "F_REPORT" not in utils_imports
    assert "export_report_excel_or_csv" not in reports_export_imports
    assert "csv" not in top_level_imports
