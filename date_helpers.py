"""Shared DD-MM-YYYY helpers for user-facing date fields."""
from __future__ import annotations

from datetime import datetime


def validate_display_date(date_str: str) -> bool:
    raw = str(date_str or "").strip()
    try:
        datetime.strptime(raw, "%d-%m-%Y")
        return True
    except ValueError:
        return False


def iso_to_display_date(date_str: str) -> str:
    raw = str(date_str or "").strip()
    if not raw:
        return ""
    try:
        return datetime.strptime(raw, "%Y-%m-%d").strftime("%d-%m-%Y")
    except ValueError:
        return raw


def display_to_iso_date(date_str: str) -> str:
    raw = str(date_str or "").strip()
    if not raw:
        return ""
    try:
        return datetime.strptime(raw, "%d-%m-%Y").strftime("%Y-%m-%d")
    except ValueError:
        return raw


def today_display_str() -> str:
    return datetime.now().strftime("%d-%m-%Y")


def attach_date_mask(entry):
    """Auto-format a Tk entry as DD-MM-YYYY while typing digits."""

    def _format_from_digits(_event=None):
        raw = entry.get()
        digits = "".join(ch for ch in raw if ch.isdigit())[:8]
        if len(digits) <= 2:
            formatted = digits
        elif len(digits) <= 4:
            formatted = f"{digits[:2]}-{digits[2:]}"
        else:
            formatted = f"{digits[:2]}-{digits[2:4]}-{digits[4:]}"
        if raw != formatted:
            entry.delete(0, "end")
            entry.insert(0, formatted)

    entry.bind("<KeyRelease>", _format_from_digits, add="+")
    entry.bind("<FocusOut>", _format_from_digits, add="+")
    return entry
