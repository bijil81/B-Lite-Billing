"""Shop metadata helpers for multi-branch mode."""

from __future__ import annotations


def normalize_shop_id(shop_id: str) -> str:
    return (shop_id or "").strip().lower().replace(" ", "_")
