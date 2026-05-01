"""v5 users repository."""

from __future__ import annotations

from typing import Dict, List, Optional

from db_core.connection import connection_scope
from db_core.query_utils import normalize_bool, row_to_dict, rows_to_dicts
from db_core.schema_manager import ensure_v5_schema


class UsersRepository:
    def list_all(self) -> List[dict]:
        ensure_v5_schema()
        with connection_scope() as conn:
            rows = conn.execute("""
                SELECT username, password_hash, role, display_name, active
                FROM v5_app_users
                ORDER BY username
            """).fetchall()
            return rows_to_dicts(rows)

    def get_by_username(self, username: str) -> Optional[dict]:
        ensure_v5_schema()
        with connection_scope() as conn:
            row = conn.execute("""
                SELECT username, password_hash, role, display_name, active
                FROM v5_app_users
                WHERE username = ?
            """, (username,)).fetchone()
            return row_to_dict(row)

    def upsert(self, user: Dict[str, object]) -> None:
        ensure_v5_schema()
        with connection_scope() as conn:
            conn.execute("""
                INSERT INTO v5_app_users(
                    username, password_hash, role, display_name, active, updated_at
                )
                VALUES(?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(username) DO UPDATE SET
                    password_hash = excluded.password_hash,
                    role = excluded.role,
                    display_name = excluded.display_name,
                    active = excluded.active,
                    updated_at = excluded.updated_at
            """, (
                str(user.get("username", "")).strip().lower(),
                str(user.get("password_hash", "")),
                str(user.get("role", "staff")),
                str(user.get("display_name", "")),
                normalize_bool(user.get("active", True)),
            ))
