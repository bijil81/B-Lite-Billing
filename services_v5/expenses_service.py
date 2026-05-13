"""Workflow layer for expenses."""

from __future__ import annotations

from repositories.expenses_repo import ExpensesRepository


class ExpensesService:
    def __init__(self, repo: ExpensesRepository | None = None):
        self.repo = repo or ExpensesRepository()

    def list_expenses(self) -> list[dict]:
        return [self._to_legacy_expense(row) for row in self.repo.list_all()]

    def add_expense(self, payload: dict) -> None:
        self.repo.insert(
            {
                "expense_date": payload.get("date", ""),
                "category": payload.get("category", ""),
                "staff_name": payload.get("staff", ""),
                "description": payload.get("description", ""),
                "amount": float(payload.get("amount", 0.0) or 0.0),
                "payment_method": payload.get("payment", ""),
            }
        )

    def replace_all(self, expenses: list[dict]) -> None:
        self.repo.delete_all()
        for e in expenses:
            self.add_expense(e)

    def soft_delete(self, expense_id: int) -> None:
        self.repo.soft_delete(expense_id)

    @staticmethod
    def _to_legacy_expense(row: dict) -> dict:
        return {
            "id": row.get("id", 0),  # Expose ID for deletion
            "date": row.get("expense_date", ""),
            "category": row.get("category", ""),
            "staff": row.get("staff_name", ""),
            "description": row.get("description", ""),
            "amount": float(row.get("amount", 0.0) or 0.0),
            "payment": row.get("payment_method", ""),
            "created": row.get("created_at", ""),
        }
