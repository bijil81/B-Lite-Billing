from __future__ import annotations


BILLING_LEFT_RATIO = 0.52


def billing_left_width(total_width: int, min_left: int, min_preview: int) -> int:
    """Return the billing composer width while preserving small-screen guards."""
    if total_width <= 0:
        return min_left
    max_left = max(min_left, total_width - min_preview)
    target_left = int(total_width * BILLING_LEFT_RATIO)
    return max(min_left, min(max_left, target_left))
