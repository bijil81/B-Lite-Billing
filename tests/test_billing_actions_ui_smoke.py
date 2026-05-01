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


def test_pdf_print_wrappers_delegate_to_phase8_helpers():
    source = BILLING_PATH.read_text(encoding="utf-8")

    assert "from src.blite_v6.billing.billing_actions import" in source
    assert "has_bill_items" in _method_source("manual_save")
    assert "save_report_args_from_totals" in _method_source("manual_save")
    assert "bill_saved_message" in _method_source("manual_save")
    assert "save_error_message" in _method_source("manual_save")
    assert "pdf_saved_message" in _method_source("save_pdf")
    assert "pdf_error_message" in _method_source("save_pdf")
    assert "printed_message" in _method_source("print_bill")
    assert "print_error_message" in _method_source("print_bill")
    assert "should_auto_clear_after_print" in _method_source("_auto_clear_after_print_or_save")
    assert "_auto_clear_after_print_or_save" in _method_source("manual_save")
    assert "_auto_clear_after_print_or_save" in _method_source("save_pdf")
    assert "_auto_clear_after_print_or_save" in _method_source("print_bill")


def test_whatsapp_wrappers_delegate_to_phase8_helpers():
    source = BILLING_PATH.read_text(encoding="utf-8")

    assert "from src.blite_v6.billing.whatsapp_actions import" in source
    assert "invalid_phone_message" in _method_source("send_whatsapp")
    assert "whatsapp_status_view" in _method_source("send_whatsapp")
    assert "whatsapp_send_success_message" in _method_source("send_whatsapp")
    assert "extract_whatsapp_error" in _method_source("send_whatsapp")
    assert "whatsapp_send_error_message" in _method_source("send_whatsapp")
    assert "whatsapp_exception_message" in _method_source("send_whatsapp")
    assert "whatsapp_session_result" in _method_source("_check_wa_status_billing")
    assert "whatsapp_status_view" in _method_source("_check_wa_status_billing")
