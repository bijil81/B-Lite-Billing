"""Runtime UI text sanitizer for Tkinter/ttk widgets.

This patches common widget constructors and text-bearing methods so mojibake
is normalized before it reaches the screen.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

_PATCHED = False
_SUSPECT_TOKENS = (
    "Ãƒ",
    "Ã‚",
    "Ã°",
    "Ã¢",
    "â€”",
    "â€“",
    "â€™",
    "â€œ",
    "â€",
    "â†’",
    "â€¢",
    "âœ…",
    "Ã¢â€ž",
    "Ã…",
    "Â¤",
    "Å¸",
    "Â",
)


def _suspicious_score(text: str) -> int:
    return sum(text.count(token) for token in _SUSPECT_TOKENS)


def _best_candidate(original: str, best: str, best_score: int, candidate: str):
    cand_score = _suspicious_score(candidate)
    if cand_score < best_score:
        return candidate, cand_score
    if cand_score == best_score and candidate != original and len(candidate) <= len(best):
        return candidate, cand_score
    return best, best_score


def sanitize_ui_text(value: Any) -> Any:
    if not isinstance(value, str) or not value:
        return value

    original = value
    best = original
    best_score = _suspicious_score(original)

    trial = original
    for _ in range(3):
        try:
            candidate = trial.encode("latin-1").decode("utf-8")
        except Exception:
            break
        best, best_score = _best_candidate(original, best, best_score, candidate)
        if candidate != best:
            break
        trial = candidate

    for encoding in ("cp1252", "latin-1"):
        try:
            candidate = original.encode(encoding).decode("utf-8")
        except Exception:
            continue
        best, best_score = _best_candidate(original, best, best_score, candidate)

    direct_replacements = {
        "â€”": "-",
        "â€“": "-",
        "â€™": "'",
        "â€˜": "'",
        "â€œ": '"',
        "â€": '"',
        "â€¦": "...",
        "â€¢": "-",
        "â†’": "->",
        "â„¢": "TM",
        "â‚¹": "Rs",
    }
    for old, new in direct_replacements.items():
        best = best.replace(old, new)

    normalized_replacements = {
        "\u2014": "-",
        "\u2013": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2026": "...",
        "\u2022": "-",
        "\u2192": "->",
        "\u21a9": "Undo",
        "\u00b7": "-",
        "\u20b9": "Rs",
    }
    for old, new in normalized_replacements.items():
        best = best.replace(old, new)

    return best


def _sanitize_text_kw(kwargs: dict[str, Any]) -> dict[str, Any]:
    if "text" in kwargs:
        kwargs["text"] = sanitize_ui_text(kwargs["text"])
    if "label" in kwargs:
        kwargs["label"] = sanitize_ui_text(kwargs["label"])
    if "values" in kwargs and isinstance(kwargs["values"], (list, tuple)):
        kwargs["values"] = type(kwargs["values"])(sanitize_ui_text(v) for v in kwargs["values"])
    if "detail" in kwargs:
        kwargs["detail"] = sanitize_ui_text(kwargs["detail"])
    return kwargs


def _sanitize_text_args(args: tuple[Any, ...]) -> tuple[Any, ...]:
    return tuple(sanitize_ui_text(arg) for arg in args)


def _wrap_widget_init(cls: type[Any]) -> None:
    orig_init = cls.__init__

    def patched_init(self, *args, **kwargs):
        kwargs = _sanitize_text_kw(dict(kwargs))
        orig_init(self, *args, **kwargs)

    cls.__init__ = patched_init

    if hasattr(cls, "configure"):
        orig_configure = cls.configure

        def patched_configure(self, cnf=None, **kwargs):
            kwargs = _sanitize_text_kw(dict(kwargs))
            return orig_configure(self, cnf, **kwargs)

        cls.configure = patched_configure
        cls.config = patched_configure


def _wrap_messagebox(fn):
    def patched(title=None, message=None, *args, **kwargs):
        if title is not None:
            title = sanitize_ui_text(title)
        if message is not None:
            message = sanitize_ui_text(message)
        kwargs = _sanitize_text_kw(dict(kwargs))
        return fn(title, message, *args, **kwargs)

    return patched


def install_ui_text_patch() -> None:
    global _PATCHED
    if _PATCHED:
        return
    _PATCHED = True

    for cls in (
        tk.Label,
        tk.Button,
        tk.Checkbutton,
        tk.Radiobutton,
        tk.Menubutton,
        ttk.Label,
        ttk.Button,
        ttk.Checkbutton,
        ttk.Radiobutton,
        ttk.Menubutton,
        ttk.LabelFrame,
    ):
        _wrap_widget_init(cls)

    orig_title = tk.Toplevel.title

    def patched_title(self, string: str | None = None):
        if string is None:
            return orig_title(self)
        return orig_title(self, sanitize_ui_text(string))

    tk.Toplevel.title = patched_title
    tk.Tk.title = patched_title

    orig_listbox_insert = tk.Listbox.insert

    def patched_listbox_insert(self, index, *elements):
        return orig_listbox_insert(self, index, *(sanitize_ui_text(el) for el in elements))

    tk.Listbox.insert = patched_listbox_insert

    orig_text_insert = tk.Text.insert

    def patched_text_insert(self, index, chars, *args):
        return orig_text_insert(self, index, sanitize_ui_text(chars), *_sanitize_text_args(args))

    tk.Text.insert = patched_text_insert

    orig_entry_insert = tk.Entry.insert

    def patched_entry_insert(self, index, string):
        return orig_entry_insert(self, index, sanitize_ui_text(string))

    tk.Entry.insert = patched_entry_insert

    orig_menu_add_command = tk.Menu.add_command
    orig_menu_add_checkbutton = tk.Menu.add_checkbutton
    orig_menu_add_radiobutton = tk.Menu.add_radiobutton
    orig_menu_entryconfigure = tk.Menu.entryconfigure

    def patched_add_command(self, *args, **kwargs):
        return orig_menu_add_command(self, *args, **_sanitize_text_kw(dict(kwargs)))

    def patched_add_checkbutton(self, *args, **kwargs):
        return orig_menu_add_checkbutton(self, *args, **_sanitize_text_kw(dict(kwargs)))

    def patched_add_radiobutton(self, *args, **kwargs):
        return orig_menu_add_radiobutton(self, *args, **_sanitize_text_kw(dict(kwargs)))

    def patched_entryconfigure(self, index, cnf=None, **kwargs):
        return orig_menu_entryconfigure(self, index, cnf, **_sanitize_text_kw(dict(kwargs)))

    tk.Menu.add_command = patched_add_command
    tk.Menu.add_checkbutton = patched_add_checkbutton
    tk.Menu.add_radiobutton = patched_add_radiobutton
    tk.Menu.entryconfigure = patched_entryconfigure
    tk.Menu.entryconfig = patched_entryconfigure

    orig_notebook_add = ttk.Notebook.add

    def patched_notebook_add(self, child, **kw):
        kw = _sanitize_text_kw(dict(kw))
        return orig_notebook_add(self, child, **kw)

    ttk.Notebook.add = patched_notebook_add

    orig_tree_heading = ttk.Treeview.heading

    def patched_tree_heading(self, column, option=None, **kw):
        kw = _sanitize_text_kw(dict(kw))
        return orig_tree_heading(self, column, option, **kw)

    ttk.Treeview.heading = patched_tree_heading

    orig_tree_insert = ttk.Treeview.insert
    orig_tree_item = ttk.Treeview.item

    def patched_tree_insert(self, parent, index, iid=None, **kw):
        kw = _sanitize_text_kw(dict(kw))
        return orig_tree_insert(self, parent, index, iid=iid, **kw)

    def patched_tree_item(self, item, option=None, **kw):
        kw = _sanitize_text_kw(dict(kw))
        return orig_tree_item(self, item, option, **kw)

    ttk.Treeview.insert = patched_tree_insert
    ttk.Treeview.item = patched_tree_item

    orig_combobox_init = ttk.Combobox.__init__

    def patched_combobox_init(self, *args, **kwargs):
        kwargs = _sanitize_text_kw(dict(kwargs))
        orig_combobox_init(self, *args, **kwargs)

    ttk.Combobox.__init__ = patched_combobox_init

    orig_combobox_setitem = ttk.Combobox.__setitem__

    def patched_combobox_setitem(self, key, value):
        if key == "values" and isinstance(value, (list, tuple)):
            value = type(value)(sanitize_ui_text(v) for v in value)
        return orig_combobox_setitem(self, key, value)

    ttk.Combobox.__setitem__ = patched_combobox_setitem

    for fn_name in (
        "showinfo",
        "showwarning",
        "showerror",
        "askquestion",
        "askokcancel",
        "askyesno",
        "askyesnocancel",
        "askretrycancel",
    ):
        original = getattr(messagebox, fn_name, None)
        if original is not None:
            setattr(messagebox, fn_name, _wrap_messagebox(original))
