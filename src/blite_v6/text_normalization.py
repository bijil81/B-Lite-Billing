"""Shared display-name normalization helpers."""

from __future__ import annotations

import re


_LOWERCASE_TOKENS = {"g", "kg", "ml", "l", "pcs", "pc", "ltr", "m", "cm", "mm"}


def normalize_spaces(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _capitalize_segment(segment: str) -> str:
    if not segment:
        return segment
    lower = segment.lower()
    if lower in _LOWERCASE_TOKENS:
        return lower
    if any(ch.isdigit() for ch in segment):
        return segment
    if segment.isupper() and len(segment) <= 5:
        return segment
    return segment[:1].upper() + segment[1:].lower()


def _capitalize_token(token: str) -> str:
    # Preserve separators while title-casing the text around them.
    parts = re.split(r"([/&+._-])", token)
    return "".join(_capitalize_segment(part) if idx % 2 == 0 else part for idx, part in enumerate(parts))


def smart_title_name(value: object) -> str:
    """Capitalize user-facing names without corrupting units/codes."""
    text = normalize_spaces(value)
    if not text:
        return ""
    return " ".join(_capitalize_token(token) for token in text.split(" "))
