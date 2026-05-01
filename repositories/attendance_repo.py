"""SQL-only repository for v5 attendance sessions."""

from __future__ import annotations

from typing import List

from db_core.connection import connection_scope
from db_core.query_utils import rows_to_dicts
from db_core.schema_manager import ensure_v5_schema


class AttendanceRepository:
    def list_all(self) -> List[dict]:
        ensure_v5_schema()
        with connection_scope() as conn:
            rows = conn.execute(
                "SELECT * FROM v5_attendance_sessions ORDER BY staff_name, attendance_date, in_time"
            ).fetchall()
            return rows_to_dicts(rows)

    def list_by_date(self, attendance_date: str) -> List[dict]:
        ensure_v5_schema()
        with connection_scope() as conn:
            rows = conn.execute(
                "SELECT * FROM v5_attendance_sessions WHERE attendance_date = ? ORDER BY staff_name, in_time",
                (attendance_date,),
            ).fetchall()
            return rows_to_dicts(rows)

    def replace_staff_sessions(self, staff_name: str, sessions: list[dict]) -> None:
        ensure_v5_schema()
        with connection_scope() as conn:
            conn.execute("DELETE FROM v5_attendance_sessions WHERE staff_name = ?", (staff_name,))
            for payload in sessions:
                conn.execute(
                    """
                    INSERT INTO v5_attendance_sessions(
                        staff_name, attendance_date, status, in_time, out_time, source
                    ) VALUES(?, ?, ?, ?, ?, ?)
                    """,
                    (
                        staff_name,
                        payload.get("attendance_date", ""),
                        payload.get("status", "Present"),
                        payload.get("in_time", ""),
                        payload.get("out_time", ""),
                        payload.get("source", "migration"),
                    ),
                )

    def add_session(self, payload: dict) -> None:
        ensure_v5_schema()
        with connection_scope() as conn:
            conn.execute(
                """
                INSERT INTO v5_attendance_sessions(
                    staff_name, attendance_date, status, in_time, out_time, source
                ) VALUES(?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.get("staff_name", ""),
                    payload.get("attendance_date", ""),
                    payload.get("status", "Present"),
                    payload.get("in_time", ""),
                    payload.get("out_time", ""),
                    payload.get("source", "migration"),
                ),
            )