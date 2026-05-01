"""SQL-only repository for v5 appointments."""

from __future__ import annotations

from typing import List

from db_core.connection import connection_scope
from db_core.query_utils import normalize_bool, row_to_dict, rows_to_dicts
from db_core.schema_manager import ensure_v5_schema


class AppointmentsRepository:
    def list_all(self) -> List[dict]:
        ensure_v5_schema()
        with connection_scope() as conn:
            rows = conn.execute(
                "SELECT * FROM v5_appointments ORDER BY appointment_date, appointment_time"
            ).fetchall()
            return rows_to_dicts(rows)

    def list_by_date_range(self, from_date: str, to_date: str) -> List[dict]:
        ensure_v5_schema()
        with connection_scope() as conn:
            rows = conn.execute(
                """
                SELECT * FROM v5_appointments
                WHERE appointment_date BETWEEN ? AND ?
                ORDER BY appointment_date, appointment_time
                """,
                (from_date, to_date),
            ).fetchall()
            return rows_to_dicts(rows)

    def get_by_legacy_key(self, legacy_key: str) -> dict | None:
        ensure_v5_schema()
        with connection_scope() as conn:
            row = conn.execute(
                "SELECT * FROM v5_appointments WHERE legacy_key = ?",
                (legacy_key,),
            ).fetchone()
            return row_to_dict(row)

    def upsert_legacy_appointment(self, payload: dict) -> None:
        ensure_v5_schema()
        with connection_scope() as conn:
            conn.execute(
                """
                INSERT INTO v5_appointments(
                    legacy_key, customer_name, phone, service_name, staff_name,
                    appointment_date, appointment_time, status, dont_show,
                    last_reminded, notes, updated_at
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(legacy_key) DO UPDATE SET
                    customer_name = excluded.customer_name,
                    phone = excluded.phone,
                    service_name = excluded.service_name,
                    staff_name = excluded.staff_name,
                    appointment_date = excluded.appointment_date,
                    appointment_time = excluded.appointment_time,
                    status = excluded.status,
                    dont_show = excluded.dont_show,
                    last_reminded = excluded.last_reminded,
                    notes = excluded.notes,
                    updated_at = excluded.updated_at
                """,
                (
                    payload.get("legacy_key"),
                    payload.get("customer_name", ""),
                    payload.get("phone", ""),
                    payload.get("service_name", ""),
                    payload.get("staff_name", ""),
                    payload.get("appointment_date", ""),
                    payload.get("appointment_time", ""),
                    payload.get("status", "Scheduled"),
                    normalize_bool(payload.get("dont_show", False)),
                    payload.get("last_reminded", ""),
                    payload.get("notes", ""),
                ),
            )
