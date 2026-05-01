from __future__ import annotations

from src.blite_v6.billing.customer_suggestions import (
    clamp_suggestion_index,
    find_customer_suggestions,
    format_customer_suggestion_label,
    get_customer_suggestion_stats,
)


def _customers(count: int = 10):
    return {
        f"99999999{i:02d}": {
            "name": f"Anu {i}",
            "points": i,
            "visits": [{} for _ in range(i % 3)],
        }
        for i in range(count)
    }


def test_find_customer_suggestions_by_name_is_case_insensitive_and_limited():
    matches = find_customer_suggestions(_customers(10), "name", "ANU", limit=8)

    assert len(matches) == 8
    assert matches[0] == ("Anu 0", "9999999900")
    assert matches[-1] == ("Anu 7", "9999999907")


def test_find_customer_suggestions_by_phone_matches_substring():
    matches = find_customer_suggestions(_customers(10), "phone", "9903", limit=8)

    assert matches == [("Anu 3", "9999999903")]


def test_find_customer_suggestions_returns_empty_for_blank_query_or_zero_limit():
    customers = _customers(2)

    assert find_customer_suggestions(customers, "name", "") == []
    assert find_customer_suggestions(customers, "name", "anu", limit=0) == []


def test_suggestion_stats_and_label_match_legacy_popup_format():
    customer = {"points": "12", "visits": [{}, {}, {}]}
    stats = get_customer_suggestion_stats(customer)

    assert stats == {"points": 12, "visits": 3}
    assert format_customer_suggestion_label("Anu", "9999999999", **stats) == (
        "  Anu  |  9999999999  |  3v  |  12pts"
    )


def test_suggestion_index_clamps_to_visible_range():
    assert clamp_suggestion_index(-10, 4) == 0
    assert clamp_suggestion_index(2, 4) == 2
    assert clamp_suggestion_index(99, 4) == 3
    assert clamp_suggestion_index(99, 0) == 0
