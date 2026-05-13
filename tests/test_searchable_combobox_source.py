from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_searchable_combobox_dropdown_arrow_shows_full_list():
    source = (ROOT / "ui_utils.py").read_text(encoding="utf-8", errors="ignore")
    assert "def _show_all_values" in source
    assert 'combo.bind("<Button-1>", _on_button_click, add="+")' in source
    assert 'combo.bind("<F4>", _show_all_values, add="+")' in source
    assert 'combo.bind("<Alt-Down>", _show_all_values, add="+")' in source
    assert "combo.configure(postcommand=_on_postcommand)" in source
    assert "_searchable_show_all_next" in source
