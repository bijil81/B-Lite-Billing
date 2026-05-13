from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADMIN_PATH = ROOT / "admin.py"


def _method_source(method_name: str) -> str:
    source = ADMIN_PATH.read_text(encoding="utf-8", errors="ignore")
    tree = ast.parse(source, filename=str(ADMIN_PATH))
    lines = source.splitlines()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == method_name:
            return "\n".join(lines[node.lineno - 1:node.end_lineno])
    raise AssertionError(f"Method not found: {method_name}")


def test_admin_category_actions_are_placed_with_their_related_fields():
    source = _method_source("_build_tab")
    build_source = _method_source("_build")

    assert 'text="Delete Category"' in source
    assert 'text="Add Category"' in source
    assert 'messagebox.askyesno(' in source
    assert '"Delete Category"' in source
    assert "This cannot be undone." in source
    assert 'c == "All"' in source
    assert "self._admin_header_actions" in build_source
    assert "self._catalog_header_actions[label.lower()] = delete_selected_btn" in source
    assert ').grid(row=1, column=3' in source
    assert "primary_actions = tk.Frame" in source
    assert "utility_actions = tk.Frame" in source
    assert "utility_actions.pack(side=tk.RIGHT)" in source
    assert "height=11 if product_mode else 13" in source
    assert 'text="Add"' not in source
    assert 'text="Delete Selected"' not in source


def test_admin_new_category_and_item_names_use_smart_capitalization():
    source = _method_source("_build_tab")

    assert "nm = smart_title_name(new_cat.get())" in source
    assert "cat   = smart_title_name(cat_var.get())" in source
    assert "nm    = smart_title_name(name_e.get())" in source
    assert "existing).strip().lower() == nm.lower()" in source


