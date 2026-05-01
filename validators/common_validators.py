"""Shared validation helpers for v5 services."""

from __future__ import annotations


def require_text(value: object, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field_name} is required")
    return text


def require_non_negative(value: object, field_name: str) -> float:
    number = float(value or 0)
    if number < 0:
        raise ValueError(f"{field_name} cannot be negative")
    return number
