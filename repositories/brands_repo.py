"""SQL-only repository for v5 brands."""

from __future__ import annotations

from db_core.connection import connection_scope
from db_core.query_utils import normalize_bool, row_to_dict, rows_to_dicts
from db_core.schema_manager import ensure_v5_schema


class BrandsRepository:
    def list_all(self) -> list[dict]:
        ensure_v5_schema()
        with connection_scope() as conn:
            rows = conn.execute("SELECT * FROM v5_brands ORDER BY name").fetchall()
            return rows_to_dicts(rows)

    def get_by_name(self, name: str) -> dict | None:
        ensure_v5_schema()
        with connection_scope() as conn:
            row = conn.execute(
                "SELECT * FROM v5_brands WHERE lower(name) = lower(?)",
                (name.strip(),),
            ).fetchone()
            return row_to_dict(row)

    def upsert(self, payload: dict) -> int:
        ensure_v5_schema()
        name = str(payload.get("name", "")).strip()
        if not name:
            raise ValueError("Brand name is required")
        with connection_scope() as conn:
            conn.execute(
                """
                INSERT INTO v5_brands(name, code, active, updated_at)
                VALUES(?, ?, ?, datetime('now'))
                ON CONFLICT(name) DO UPDATE SET
                    code = excluded.code,
                    active = excluded.active,
                    updated_at = excluded.updated_at
                """,
                (
                    name,
                    str(payload.get("code", "")).strip(),
                    normalize_bool(payload.get("active", True)),
                ),
            )
            row = conn.execute(
                "SELECT id FROM v5_brands WHERE lower(name) = lower(?)",
                (name,),
            ).fetchone()
            return int(row["id"])
