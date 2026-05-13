from __future__ import annotations

import copy

from src.blite_v6.inventory_grocery import category_master


def _patch_catalog(monkeypatch, initial):
    state = copy.deepcopy(initial)

    def fake_load_json(_path, default=None):
        return copy.deepcopy(state if state is not None else default)

    def fake_save_json(_path, data):
        state.clear()
        state.update(copy.deepcopy(data))
        return True

    monkeypatch.setattr(category_master, "load_json", fake_load_json)
    monkeypatch.setattr(category_master, "save_json", fake_save_json)
    return state


def test_category_master_persists_empty_product_category(monkeypatch):
    state = _patch_catalog(monkeypatch, {"Services": {}, "Products": {}})

    saved = category_master.ensure_catalog_category("Products", "  test   category ")

    assert saved == "Test Category"
    assert category_master.list_catalog_categories("Products") == ["Test Category"]
    assert state["Products"]["Test Category"] == {}


def test_category_master_is_case_insensitive_for_duplicates(monkeypatch):
    state = _patch_catalog(monkeypatch, {"Services": {}, "Products": {"Body Care": {}}})

    saved = category_master.ensure_catalog_category("Products", "body care")

    assert saved == "Body Care"
    assert list(state["Products"].keys()) == ["Body Care"]
