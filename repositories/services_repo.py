"""SQL-only repository for v5 service master data."""

from __future__ import annotations

from typing import Iterable

from db_core.connection import connection_scope
from db_core.query_utils import normalize_bool, row_to_dict, rows_to_dicts
from db_core.schema_manager import ensure_v5_schema


class ServicesRepository:
    def list_services(self, *, active_only: bool = True) -> list[dict]:
        ensure_v5_schema()
        sql = "SELECT * FROM v5_services"
        if active_only:
            sql += " WHERE COALESCE(active, 1) = 1"
        sql += " ORDER BY category, legacy_name"
        with connection_scope() as conn:
            return rows_to_dicts(conn.execute(sql).fetchall())

    def get_service(self, legacy_name: str) -> dict | None:
        ensure_v5_schema()
        with connection_scope() as conn:
            row = conn.execute(
                "SELECT * FROM v5_services WHERE legacy_name = ?",
                (legacy_name,),
            ).fetchone()
            return row_to_dict(row)

    def upsert_service(self, payload: dict) -> None:
        ensure_v5_schema()
        with connection_scope() as conn:
            conn.execute(
                """
                INSERT INTO v5_services(
                    legacy_name, category, price, active, updated_at
                ) VALUES(?, ?, ?, ?, datetime('now'))
                ON CONFLICT(legacy_name) DO UPDATE SET
                    category = excluded.category,
                    price = excluded.price,
                    active = excluded.active,
                    updated_at = excluded.updated_at
                """,
                (
                    str(payload.get("legacy_name", "")).strip(),
                    str(payload.get("category", "")).strip(),
                    float(payload.get("price", 0.0) or 0.0),
                    normalize_bool(payload.get("active", True)),
                ),
            )

    def deactivate_service(self, legacy_name: str) -> None:
        ensure_v5_schema()
        with connection_scope() as conn:
            conn.execute(
                """
                UPDATE v5_services
                SET active = 0, updated_at = datetime('now')
                WHERE legacy_name = ?
                """,
                (legacy_name,),
            )

    def deactivate_missing(self, keep_names: Iterable[str]) -> None:
        ensure_v5_schema()
        names = [str(name).strip() for name in keep_names if str(name).strip()]
        with connection_scope() as conn:
            if names:
                placeholders = ",".join("?" for _ in names)
                conn.execute(
                    f"""
                    UPDATE v5_services
                    SET active = 0, updated_at = datetime('now')
                    WHERE legacy_name NOT IN ({placeholders})
                    """,
                    tuple(names),
                )
            else:
                conn.execute(
                    """
                    UPDATE v5_services
                    SET active = 0, updated_at = datetime('now')
                    """
                )
