"""Small SQLite row/query helpers for v5 repositories."""

from __future__ import annotations

import sqlite3
from typing import Any, Iterable


def rows_to_dicts(rows: Iterable[sqlite3.Row]) -> list[dict]:
    return [dict(row) for row in rows]


def row_to_dict(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row else None


def normalize_bool(value: Any) -> int:
    return 1 if bool(value) else 0
