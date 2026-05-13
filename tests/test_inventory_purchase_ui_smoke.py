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
    assert "_is_dropdown_wheel_target" in source
    assert "_bind_purchase_scroll(vendor_cb)" in source
    assert "_bind_purchase_scroll(item_cb)" in source
    assert "item_names = _purchase_item_names(inv)" in source
    assert "item_categories = purchase_item_categories" in source
    assert "item_category_cb = ttk.Combobox" in source
    assert 'text="+ Category"' in source
    assert 'text="+ New Product"' in source
    assert "def _category_filtered_item_names" in source
    assert "item_category_cb.bind(\"<<ComboboxSelected>>\", _on_item_category_change)" in source
    assert "def _add_purchase_category" in source
    assert "def _open_purchase_new_product" in source
    assert "ensure_catalog_category(\"Products\", category)" in source
    assert "list_catalog_categories(\"Products\")" in source
    assert "self._item_form(" in source
    assert "on_saved=_on_product_saved" in source
    assert "smart_title_name(entries[\"name\"].get())" in (ROOT / "inventory.py").read_text(encoding="utf-8")
    assert "item_search_row = tk.Frame" in source
    assert "item_cb = tk.Entry" in source
    assert "item_popup = tk.Toplevel(win)" in source
    assert "item_popup.overrideredirect(True)" in source
    assert "item_list = tk.Listbox" in source
    assert "def _matching_purchase_items" in source
    assert "def _toggle_item_results" in source
    assert "item_arrow_btn = tk.Button" in source
    assert "item_popup.geometry" in source
    assert "item_popup.deiconify()" in source
    assert "item_list_wrap.pack_forget" not in source
    assert "item_cb.bind(\"<KeyRelease>\", _refresh_item_list" in source
    assert "item_cb.bind(\"<Return>\", _select_first_item" in source
    assert "item_list.bind(\"<ButtonRelease-1>\", _select_item_from_list" in source
    assert "_bind_purchase_scroll(notes)" in source
    assert "purchase_lines = []" in source
    assert 'text="Add Line"' in source
    assert 'text="Remove Selected"' in source


def test_purchase_item_names_include_zero_stock_products_but_skip_inactive_rows():
    from inventory import _purchase_item_names

    inv = {
        "Aloe Gel": {"qty": 0, "inactive": False},
        "Deleted Item": {"qty": 0, "is_deleted": True},
        "Inactive Item": {"qty": 10, "inactive": True},
        "Body Wash": {"qty": 5},
        " ": {"qty": 1},
    }

    assert _purchase_item_names(inv) == ["Aloe Gel", "Body Wash"]


def test_purchase_selector_helpers_support_category_quick_add_and_filtering():
    from src.blite_v6.inventory_grocery.purchase_item_selector import (
        category_exists,
        filter_purchase_items,
        normalize_category_name,
        purchase_item_categories,
    )

    inv = {
        "Aloe Gel": {"category": "Skin Care"},
        "Body Wash": {"category": "Body Care"},
        "Body Mist": {"category": "Body Care"},
    }
    names = ["Aloe Gel", "Body Mist", "Body Wash"]

    categories = purchase_item_categories(inv, names, extra=["Salon Use"])
    assert categories == ["All", "Body Care", "Salon Use", "Skin Care"]
    assert normalize_category_name("  Body   Care ") == "Body Care"
    assert category_exists("body care", categories)
    assert filter_purchase_items(
        names,
        "body",
        category="Body Care",
        item_category=lambda name: inv[name]["category"],
    ) == ["Body Mist", "Body Wash"]
