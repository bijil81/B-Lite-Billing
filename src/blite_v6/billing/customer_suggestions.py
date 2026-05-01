from __future__ import annotations

from typing import Any, Mapping


CustomerSuggestion = tuple[str, str]


def find_customer_suggestions(
    customers: Mapping[str, Mapping[str, Any]],
    field: str,
    query: str | None,
    limit: int = 8,
) -> list[CustomerSuggestion]:
    clean_query = (query or "").strip().lower()
    if not clean_query or limit <= 0:
        return []

    matches: list[CustomerSuggestion] = []
    for phone, customer in customers.items():
        name = customer.get("name", "")
        if field == "name":
            if clean_query in name.lower():
                matches.append((name, phone))
        else:
            if clean_query in phone:
                matches.append((customer.get("name", ""), phone))
        if len(matches) >= limit:
            break
    return matches


def get_customer_suggestion_stats(customer: Mapping[str, Any] | None) -> dict[str, int]:
    customer = customer or {}
    return {
        "points": int(customer.get("points", 0) or 0),
        "visits": len(customer.get("visits", []) or []),
    }


def format_customer_suggestion_label(customer_name: str, phone: str, points: int = 0, visits: int = 0) -> str:
    return f"  {customer_name}  |  {phone}  |  {visits}v  |  {points}pts"


def clamp_suggestion_index(index: int, size: int) -> int:
    if size <= 0:
        return 0
    return max(0, min(index, size - 1))
