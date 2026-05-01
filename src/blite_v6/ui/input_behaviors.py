"""Reusable Tkinter input behaviors.

Keep field-level behavior here so large screen modules do not grow when
small input polish is added.
"""
from __future__ import annotations

import tkinter as tk

from date_helpers import attach_date_mask, iso_to_display_date


def first_letter_caps(text: str) -> str:
    """Capitalize the first letter of each typed word without lowercasing codes."""
    result: list[str] = []
    capitalize_next = True
    for char in text:
        if char.isalpha() and capitalize_next:
            result.append(char.upper())
            capitalize_next = False
            continue
        result.append(char)
        if char in {" ", "-", ".", "'", "/"}:
            capitalize_next = True
        elif char.isalnum():
            capitalize_next = False
    return "".join(result)


def attach_first_letter_caps(entry: tk.Entry) -> tk.Entry:
    """Auto-capitalize name-like text fields while preserving cursor position."""
    def _apply(_event=None):
        current = entry.get()
        formatted = first_letter_caps(current)
        if formatted == current:
            return
        try:
            cursor = entry.index(tk.INSERT)
        except Exception:
            cursor = len(formatted)
        entry.delete(0, tk.END)
        entry.insert(0, formatted)
        entry.icursor(min(cursor, len(formatted)))

    entry.bind("<KeyRelease>", _apply, add="+")
    entry.bind("<FocusOut>", _apply, add="+")
    return entry


def attach_display_date_mask(entry: tk.Entry) -> tk.Entry:
    """Attach the app-standard DD-MM-YYYY typing mask."""
    return attach_date_mask(entry)


def date_for_display(stored_date: str) -> str:
    """Convert stored ISO dates to display format, leaving unknown values alone."""
    return iso_to_display_date(stored_date)
