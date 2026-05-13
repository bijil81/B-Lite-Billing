"""Compatibility adapter for gradual expenses migration to v5 services."""

from __future__ import annotations

from salon_settings import get_settings
from services_v5.expenses_service import ExpensesService
from db import db_transaction

_expenses_service = ExpensesService()

def use_v5_expenses_db() -> bool:
    return bool(get_settings().get("use_v5_expenses_db", False))

def get_expenses_legacy_map_v5() -> list:
    """Returns expenses in legacy format: list of dicts"""
    return _expenses_service.list_expenses()

def save_expenses_legacy_map_v5(data: list) -> None:
    """Receives legacy format list and saves via ExpensesService transaction."""
    with db_transaction():
        # During legacy sync, we replace all active to avoid duplication,
        # but in v5 mode, we should append or rely on DB ID.
        _expenses_service.replace_all(data)
