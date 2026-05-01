"""SQL-only repository for v5 staff master data."""

from __future__ import annotations

from typing import List

from db_core.connection import connection_scope
from db_core.query_utils import normalize_bool, row_to_dict, rows_to_dicts
from db_core.schema_manager import ensure_v5_schema


class StaffRepository:
    def list_all(self) -> List[dict]:
        ensure_v5_schema()
        with connection_scope() as conn:
            rows = conn.execute("SELECT * FROM v5_staff ORDER BY display_name").fetchall()
            return rows_to_dicts(rows)

    def get_by_name(self, legacy_name: str) -> dict | None:
        ensure_v5_schema()
        with connection_scope() as conn:
            row = conn.execute(
                "SELECT * FROM v5_staff WHERE legacy_name = ?",
                (legacy_name,),
            ).fetchone()
            return row_to_dict(row)

    def upsert_legacy_staff(self, payload: dict) -> None:
        ensure_v5_schema()
        with connection_scope() as conn:
            conn.execute(
                """
                INSERT INTO v5_staff(
                    legacy_name, display_name, role_name, phone, commission_pct,
                    salary, active, photo_path, notes, updated_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(legacy_name) DO UPDATE SET
                    display_name = excluded.display_name,
                    role_name = excluded.role_name,
                    phone = excluded.phone,
                    commission_pct = excluded.commission_pct,
                    salary = excluded.salary,
                    active = excluded.active,
                    photo_path = excluded.photo_path,
                    notes = excluded.notes,
                    updated_at = excluded.updated_at
                """,
                (
                    payload.get("legacy_name"),
                    payload.get("display_name", payload.get("legacy_name", "")),
                    payload.get("role_name", "staff"),
                    payload.get("phone", ""),
                    float(payload.get("commission_pct", 0.0) or 0.0),
                    float(payload.get("salary", 0.0) or 0.0),
                    normalize_bool(payload.get("active", True)),
                    payload.get("photo_path", ""),
                    payload.get("notes", ""),
                ),
            )
