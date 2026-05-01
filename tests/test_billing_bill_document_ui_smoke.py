from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BILLING_PATH = ROOT / "billing.py"


def _method_source(method_name: str) -> str:
    source = BILLING_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(BILLING_PATH))
    lines = source.splitlines()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == method_name:
            return "\n".join(lines[node.lineno - 1:node.end_lineno])
    raise AssertionError(f"Method not found: {method_name}")


def test_bill_document_wrappers_delegate_to_phase7_helpers():
    source = BILLING_PATH.read_text(encoding="utf-8")

    assert "from src.blite_v6.billing.bill_document import" in source
    assert "apply_printer_width" in _method_source("_refresh_bill_inner")
    assert "build_bill_data_kwargs" in _method_source("_refresh_bill_inner")
    assert "build_bill_data_kwargs" in _method_source("_build_bill_data_inner")
    assert "build_pdf_path" in _method_source("_pdf_path")


def test_bill_preview_still_uses_print_engine_and_updates_ui_in_billing_py():
    refresh_source = _method_source("_refresh_bill_inner")

    assert "generate_thermal_text" in refresh_source
    assert "BillData" in refresh_source
    assert "self.txt.delete" in refresh_source
    assert "self.txt.insert" in refresh_source
    assert "self.total_lbl.config" in refresh_source
