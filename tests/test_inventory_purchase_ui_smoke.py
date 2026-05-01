from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = ROOT / "inventory.py"


def _method_source(method_name: str) -> str:
    source = INVENTORY_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(INVENTORY_PATH))
    lines = source.splitlines()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == method_name:
            return "\n".join(lines[node.lineno - 1:node.end_lineno])
    raise AssertionError(f"Method not found: {method_name}")


def test_purchase_dialog_uses_pinned_footer_and_scrollable_body():
    source = _method_source("_purchase_dialog")

    assert "popup_window(win, 900, 780)" in source
    assert "win.minsize(760, 640)" in source
    assert "win.resizable(True, True)" in source
    assert "actions.pack(fill=tk.X, side=tk.BOTTOM)" in source
    assert "make_scrollable(win" in source
    assert "_bind_purchase_scroll(vendor_cb)" in source
    assert "_bind_purchase_scroll(item_cb)" in source
    assert "_bind_purchase_scroll(notes)" in source
