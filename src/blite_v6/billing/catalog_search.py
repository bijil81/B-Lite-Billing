from __future__ import annotations

import difflib
import re
from typing import Any, Mapping, Sequence


CatalogItem = tuple[str, str, str, float]
CatalogItemLike = Mapping[str, Any] | Sequence[Any]

_CODE_LIKE_RE = re.compile(r"^[A-Za-z]{1,5}[-_]?\d")


def _price_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def normalize_catalog_item(item: CatalogItemLike) -> CatalogItem:
    if isinstance(item, Mapping):
        code = item.get("code") or item.get("sku") or item.get("barcode") or item.get("id") or item.get("name")
        name = item.get("name") or item.get("display_name") or item.get("bill_label") or item.get("product_name")
        category = item.get("category") or item.get("category_name") or ""
        price = _price_or_none(
            item.get("price")
            if item.get("price") not in (None, "")
            else item.get("sale_price", item.get("selling_price", item.get("cost", 0.0)))
        )
        if not name or price is None:
            raise ValueError("catalog mapping must contain a name and numeric price")
        return (str(code or name), str(name), str(category), price)

    if len(item) < 3:
        raise ValueError("catalog item must contain at least 3 values")

    price_at_3 = _price_or_none(item[3]) if len(item) >= 4 else None
    if price_at_3 is not None:
        code, name, category = item[:3]
        return (str(code), str(name), str(category), price_at_3)

    price_at_2 = _price_or_none(item[2])
    if price_at_2 is not None:
        first, second = item[:2]
        if _CODE_LIKE_RE.match(str(first).strip()):
            code, name, category = first, second, ""
        else:
            name, category = first, second
            code = name
        return (str(code), str(name), str(category), price_at_2)

    raise ValueError("catalog item price must be numeric")


def data_for_mode(mode: str, services_data: Mapping[str, Any], products_data: Mapping[str, Any]) -> Mapping[str, Any]:
    return services_data if mode == "services" else products_data


def should_use_variant_products(mode: str, variant_db_enabled: bool) -> bool:
    return mode == "products" and bool(variant_db_enabled)


def category_values_for_mode(mode: str, data: Mapping[str, Any], product_categories: Sequence[str] | None = None) -> list[str]:
    if mode == "products" and product_categories is not None:
        return ["All"] + list(product_categories)
    return ["All"] + list(data.keys())


def build_category_matches(codes: Mapping[str, Mapping[str, Any]], mode: str, category: str = "All") -> list[CatalogItem]:
    mode_type = "service" if mode == "services" else "product"
    matches: list[CatalogItem] = []
    for code, item in codes.items():
        if item["type"] != mode_type:
            continue
        if category != "All" and item["category"] != category:
            continue
        matches.append((code, item["name"], item["category"], item["price"]))
    matches.sort(key=lambda item: item[1])
    return matches


def smart_search(query: str, items: Sequence[CatalogItem]) -> list[CatalogItem]:
    query = query.strip().lower()
    if not query:
        normalized = []
        for item in items:
            try:
                normalized.append(normalize_catalog_item(item))
            except Exception:
                continue
        return normalized

    results: list[tuple[int, CatalogItem]] = []
    for item in items:
        try:
            code, name, _category, _price = normalize_catalog_item(item)
        except Exception:
            continue
        name_l = name.lower()
        code_l = code.lower()
        score = 0

        if name_l.startswith(query) or code_l.startswith(query):
            score += 100
        elif query in name_l or query in code_l:
            score += 60

        ratio = difflib.SequenceMatcher(None, query, name_l).ratio()
        if ratio > 0.6:
            score += int(ratio * 50)

        if score > 0:
            results.append((score, normalize_catalog_item(item)))

    if not results:
        return []

    results.sort(key=lambda result: result[0], reverse=True)
    return [item for _score, item in results]


def find_exact_match(query: str, items: Sequence[CatalogItem]) -> CatalogItem | None:
    query = query.strip().lower()
    if not query:
        return None
    for item in items:
        try:
            code, name, category, price = normalize_catalog_item(item)
        except Exception:
            continue
        if name.lower() == query or code.lower() == query:
            return (code, name, category, price)
    return None


def variant_selection_for_item(code: str, variant_meta: Mapping[str, Mapping[str, Any]], use_variants: bool) -> dict[str, Any] | None:
    if not use_variants:
        return None
    return dict(variant_meta.get(code, {}) or {})


def format_search_result_label(code: str, name: str, price: float) -> str:
    return f"  {code}  {name}  -  Rs{price:.0f}"
