from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = ROOT / "inventory.py"
IMPORT_DIALOG_PATH = ROOT / "src" / "blite_v6" / "inventory_grocery" / "product_import_dialog.py"


def _method_source(method_name: str) -> str:
    source = INVENTORY_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(INVENTORY_PATH))
    lines = source.splitlines()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == method_name:
            return "\n".join(lines[node.lineno - 1:node.end_lineno])
    raise AssertionError(f"Method not found: {method_name}")


def test_import_dialog_has_preview_first_apply_with_mapping_grid():
    inventory_source = INVENTORY_PATH.read_text(encoding="utf-8")
    source = IMPORT_DIALOG_PATH.read_text(encoding="utf-8")
    method = _method_source("_import_dialog")

    assert "open_product_import_preview_dialog" in inventory_source
    assert "filedialog" not in inventory_source
    assert "from tkinter import filedialog, messagebox, ttk" in source
    assert "parse_import_file" in source
    assert "default_column_mapping" in source
    assert "build_import_preview" in source
    assert "apply_import_preview" in source
    assert "filedialog.askopenfilename" in source
    assert "Column Mapping" in source
    assert "Preview before import" in source
    assert "Import Valid Rows" in source
    assert "file_row.grid_columnconfigure(1, weight=1)" in source
    assert "row = idx // 2" in source
    assert "browse_button.grid" in source
    assert "messagebox.showinfo(\"Import Completed\", message)" in source
    assert "_close()" in source
    assert "duplicate_policy" in source
    assert "below_cost_policy" in source
    assert "preview_tree = ttk.Treeview" in source
    assert "get_inventory_fn()" in source
    assert "save_inventory_fn=save_inventory" in method
    assert "refresh_inventory_fn=self._load" in method
    assert "service.save" not in source


def test_inventory_exposes_import_preview_actions():
    source = _method_source("_build")

    assert 'ModernButton(hdr, text="Import"' in source
    assert "command=self._import_dialog" in source
    assert '"Import Preview"' in source
