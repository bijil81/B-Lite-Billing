"""Pure helpers for the Purchase Bill item selector."""

from __future__ import annotations

from typing import Callable, Iterable, Mapping

from src.blite_v6.text_normalization import smart_title_name


def purchase_item_names(inv: Mapping[str, Mapping]) -> list[str]:
    """Return active product names available for purchase entry, including zero-stock rows."""
    names: list[str] = []
    for name, item in (inv or {}).items():
        text = str(name or "").strip()
        if not text:
            continue
        row = item or {}
        if bool(row.get("inactive", False)) or bool(row.get("is_deleted", False)):
            continue
        names.append(text)
    return sorted(set(names), key=str.lower)


def purchase_item_categories(
    inv: Mapping[str, Mapping],
    names: Iterable[str],
    extra: Iterable[str] | None = None,
) -> list[str]:
    """Build category filter values for the purchase selector."""
    allowed = {str(name or "").strip() for name in names if str(name or "").strip()}
    categories = {
        str((item or {}).get("category", "") or "").strip()
        for name, item in (inv or {}).items()
        if str(name or "").strip() in allowed
    }
    categories.update(str(value or "").strip() for value in (extra or []))
    clean = sorted({value for value in categories if value}, key=str.lower)
    return ["All"] + clean


def normalize_category_name(value: object) -> str:
    """Normalize user-created category names without changing their meaning."""
    return smart_title_name(value)


def category_exists(category: str, categories: Iterable[str]) -> bool:
    target = normalize_category_name(category).lower()
    return bool(target) and any(
        normalize_category_name(existing).lower() == target
        for existing in categories
        if normalize_category_name(existing) != "All"
    )


def filter_purchase_items(
    names: Iterable[str],
    query: str,
    *,
    category: str = "All",
    item_category: Callable[[str], str] | None = None,
    limit: int = 60,
) -> list[str]:
    """Filter product names by category and typed search text."""
    source = [str(name or "").strip() for name in names if str(name or "").strip()]
    category = normalize_category_name(category)
    if category and category != "All" and item_category is not None:
        source = [name for name in source if normalize_category_name(item_category(name)) == category]

    text = str(query or "").strip().lower()
    if not text:
        return source[:limit]

    starts = [name for name in source if name.lower().startswith(text)]
    contains = [name for name in source if text in name.lower() and name not in starts]
    return (starts + contains)[:limit]
