"""Legacy expenses -> v5 expenses migration."""

from __future__ import annotations

from db_core.connection import connection_scope
from db_core.schema_manager import ensure_v5_schema
from expenses import get_expenses


def migrate_expenses(dry_run: bool = True) -> dict:
    ensure_v5_schema()
    expenses = get_expenses()
    migrated = []
    skipped = []
    for index, expense in enumerate(expenses, start=1):
        ref = f"expense-{index}"
        expense_date = expense.get("date", "")
        category = expense.get("category", "")
        staff_name = expense.get("staff", "")
        description = expense.get("description", "")
        amount = float(expense.get("amount", 0.0) or 0.0)
        payment_method = expense.get("payment", expense.get("payment_method", ""))
        if not dry_run:
            with connection_scope() as conn:
                existing = conn.execute(
                    """
                    SELECT id FROM v5_expenses
                    WHERE expense_date = ? AND category = ? AND staff_name = ?
                      AND description = ? AND amount = ? AND payment_method = ?
                    LIMIT 1
                    """,
                    (expense_date, category, staff_name, description, amount, payment_method),
                ).fetchone()
                if existing:
                    skipped.append(ref)
                    continue
                conn.execute(
                    """
                    INSERT INTO v5_expenses(expense_date, category, staff_name, description, amount, payment_method)
                    VALUES(?, ?, ?, ?, ?, ?)
                    """,
                    (expense_date, category, staff_name, description, amount, payment_method),
                )
        migrated.append(ref)
    return {
        "source_count": len(expenses),
        "migrated": migrated,
        "skipped": skipped,
        "dry_run": dry_run,
    }