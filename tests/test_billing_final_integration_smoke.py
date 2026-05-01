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


def test_save_report_wrapper_delegates_legacy_core_and_preserves_v5_branch():
    source = BILLING_PATH.read_text(encoding="utf-8")
    save_source = _method_source("_save_report")

    assert "from src.blite_v6.billing.report_persistence import" in source
    assert "SaveLegacyReportDependencies" in save_source
    assert "save_report_legacy_core" in save_source
    assert "use_v5_billing_db" in save_source
    assert "_save_report_v5" in save_source
    assert "F_REPORT" in save_source


def test_billing_frame_still_owns_ui_side_effect_methods_after_final_split():
    for method_name in [
        "_build",
        "_ss_show",
        "_build_suggestion_popup",
        "_edit_item_qty",
        "send_whatsapp",
        "print_bill",
        "_right_click_menu",
    ]:
        assert f"def {method_name}" in _method_source(method_name)
