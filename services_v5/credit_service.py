"""Credit system helpers — Phase 6.

Extracted from billing_service.py to keep financial logic in a focused module.
Per ENGINEERING_RULES: new financial logic must live in a focused service/helper.

Public API:
    validate_payment_amounts(amount_paid, net_total, due_clearance_amount=0.0) -> None  (raises ValueError)
    compute_new_due(current_due, unpaid_amount, due_clearance_amount) -> float
    check_credit_limit(new_due, credit_limit, unpaid_amount) -> str | None
    is_customer_blacklisted(conn, customer_phone) -> bool
"""

from __future__ import annotations

from utils import app_log


# ---------------------------------------------------------------------------
# Pure financial calculations
# ---------------------------------------------------------------------------

def validate_payment_amounts(
    amount_paid: float,
    net_total: float,
    due_clearance_amount: float = 0.0,
) -> None:
    """Raise ValueError if payment amounts are out of safe bounds.

    Guards against:
    - Negative paid amounts (data corruption / bad UI input)
    - Overpayment beyond net_total + any due_clearance being settled

    BUG FIX (2026-05-10): Previously this function only compared amount_paid
    against net_total. When a customer pays more than the current invoice to
    clear an old outstanding due (due_clearance_amount > 0), amount_paid
    legitimately exceeds net_total — the old code raised ValueError and blocked
    a valid transaction. Now we compute the effective ceiling including
    due_clearance_amount before raising.
    """
    if amount_paid < 0:
        raise ValueError(f"Invalid payment: amount_paid ({amount_paid:.2f}) cannot be negative.")
    effective_ceiling = round(float(net_total) + float(due_clearance_amount or 0.0), 2)
    if round(amount_paid, 2) > effective_ceiling + 0.01:  # 1 paise tolerance
        raise ValueError(
            f"Payment ({amount_paid:.2f}) exceeds invoice total "
            f"({net_total:.2f}) plus due clearance ({due_clearance_amount:.2f})."
        )


def compute_new_due(
    current_due: float,
    unpaid_amount: float,
    due_clearance_amount: float,
) -> float:
    """Return the customer's new outstanding due after this transaction.

    Uses round() to prevent floating-point drift accumulation across invoices.
    Always non-negative.
    """
    raw = current_due + unpaid_amount - due_clearance_amount
    return max(0.0, round(raw, 2))


def check_credit_limit(
    new_due: float,
    credit_limit: float,
    unpaid_amount: float,
) -> str | None:
    """Enforce credit limit rules.

    Returns:
        None            — all clear
        "warning" str   — approaching limit (80 %)
    Raises:
        ValueError      — limit exceeded (blocks save)
    """
    if credit_limit <= 0 or unpaid_amount <= 0:
        return None
    new_due_rounded = round(new_due, 2)
    if new_due_rounded > round(credit_limit, 2):
        raise ValueError(
            f"Credit limit exceeded "
            f"(due would be ₹{new_due_rounded:,.2f}, limit is ₹{credit_limit:,.2f})."
        )
    if new_due_rounded > round(credit_limit * 0.8, 2):
        return "Customer nearing credit limit"
    return None


# ---------------------------------------------------------------------------
# DB-backed helpers
# ---------------------------------------------------------------------------

def is_customer_blacklisted(conn, customer_phone: str) -> bool:
    """Return True if the customer is marked blacklisted in v5_customers."""
    if not customer_phone or customer_phone == "0000000000":
        return False
    try:
        row = conn.execute(
            "SELECT COALESCE(is_blacklisted, 0) AS bl FROM v5_customers WHERE legacy_phone = ?",
            (customer_phone,),
        ).fetchone()
        return bool(row and row["bl"])
    except Exception as exc:
        app_log(f"[credit_service.is_customer_blacklisted] {exc}")
        return False


def get_customer_credit_data(conn, customer_phone: str) -> dict | None:
    """Fetch credit-relevant fields for a customer. Returns None for guests."""
    if not customer_phone or customer_phone == "0000000000":
        return None
    try:
        row = conn.execute(
            """SELECT id,
                      COALESCE(credit_limit, 0.0) AS credit_limit,
                      COALESCE(current_due, 0.0)  AS current_due,
                      COALESCE(is_blacklisted, 0)  AS is_blacklisted
               FROM v5_customers WHERE legacy_phone = ?""",
            (customer_phone,),
        ).fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "credit_limit": float(row["credit_limit"]),
            "current_due": float(row["current_due"]),
            "is_blacklisted": bool(row["is_blacklisted"]),
        }
    except Exception as exc:
        app_log(f"[credit_service.get_customer_credit_data] {exc}")
        return None


def update_customer_due(conn, customer_id: int, new_due: float) -> None:
    """Write the computed new_due to v5_customers with integrity guard."""
    safe_due = max(0.0, round(new_due, 2))
    conn.execute(
        "UPDATE v5_customers SET current_due = ?, updated_at = datetime('now') WHERE id = ?",
        (safe_due, customer_id),
    )
    app_log(f"[credit_service] customer id={customer_id} due updated to {safe_due:.2f}")
