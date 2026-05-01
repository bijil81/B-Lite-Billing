"""v5 settings repository."""

from __future__ import annotations

from typing import Optional

from db_core.connection import connection_scope
from db_core.schema_manager import ensure_v5_schema


class SettingsRepository:
    def get(self, key: str) -> Optional[str]:
        ensure_v5_schema()
        with connection_scope() as conn:
            row = conn.execute(
                "SELECT value FROM v5_app_settings WHERE key = ?",
                (key,)
            ).fetchone()
            return row["value"] if row else None

    def set(self, key: str, value: str) -> None:
        ensure_v5_schema()
        with connection_scope() as conn:
            conn.execute("""
                INSERT INTO v5_app_settings(key, value, updated_at)
                VALUES(?, ?, datetime('now'))
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
            """, (key, value))

    def get_bool(self, key: str, default: bool = False) -> bool:
        value = self.get(key)
        if value is None:
            return default
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    def set_bool(self, key: str, value: bool) -> None:
        self.set(key, "1" if value else "0")
