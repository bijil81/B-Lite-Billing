"""SQL-only repository for expenses."""

from __future__ import annotations

from db_core.connection import connection_scope
from db_core.query_utils import rows_to_dicts
from db_core.schema_manager import ensure_v5_schema


class ExpensesRepository:
    def list_all(self) -> list[dict]:
        ensure_v5_schema()
        with connection_scope() as conn:
            rows = conn.execute("SELECT * FROM v5_expenses WHERE is_deleted = 0 ORDER BY expense_date DESC, id DESC").fetchall()
            return rows_to_dicts(rows)

    def insert(self, payload: dict) -> None:
        ensure_v5_schema()
        with connection_scope() as conn:
            conn.execute(
                """
                INSERT INTO v5_expenses(
                    expense_date, category, staff_name, description, amount, payment_method
                ) VALUES(?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.get("expense_date", ""),
                    payload.get("category", ""),
                    payload.get("staff_name", ""),
                    payload.get("description", ""),
                    float(payload.get("amount", 0.0) or 0.0),
                    payload.get("payment_method", ""),
                ),
            )

    def soft_delete(self, expense_id: int) -> None:
        ensure_v5_schema()
        with connection_scope() as conn:
            conn.execute(
                "UPDATE v5_expenses SET is_deleted = 1, deleted_at = datetime('now') WHERE id = ?",
                (expense_id,)
            )

    def delete_all(self) -> None:
        """For full sync replacement only!"""
        ensure_v5_schema()
        with connection_scope() as conn:
            conn.execute("DELETE FROM v5_expenses")
