"""SQL-only repository for v5 catalog products."""

from __future__ import annotations

from db_core.connection import connection_scope
from db_core.query_utils import normalize_bool, row_to_dict, rows_to_dicts
from db_core.schema_manager import ensure_v5_schema


class ProductsRepository:
    def list_all(self) -> list[dict]:
        ensure_v5_schema()
        with connection_scope() as conn:
            rows = conn.execute(
                """
                SELECT p.*, b.name AS brand_name, c.name AS category_name
                FROM v5_catalog_products p
                LEFT JOIN v5_brands b ON b.id = p.brand_id
                LEFT JOIN v5_product_categories c ON c.id = p.category_id
                ORDER BY coalesce(b.name, ''), p.name
                """
            ).fetchall()
            return rows_to_dicts(rows)

    def upsert(self, payload: dict) -> int:
        ensure_v5_schema()
        name = str(payload.get("name", "")).strip()
        if not name:
            raise ValueError("Product name is required")
        brand_id = payload.get("brand_id")
        category_id = payload.get("category_id")
        with connection_scope() as conn:
            conn.execute(
                """
                INSERT INTO v5_catalog_products(
                    brand_id, category_id, name, base_name, description, active, updated_at
                ) VALUES(?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(brand_id, category_id, name) DO UPDATE SET
                    base_name = excluded.base_name,
                    description = excluded.description,
                    active = excluded.active,
                    updated_at = excluded.updated_at
                """,
                (
                    brand_id,
                    category_id,
                    name,
                    str(payload.get("base_name", name)).strip(),
                    str(payload.get("description", "")).strip(),
                    normalize_bool(payload.get("active", True)),
                ),
            )
            row = conn.execute(
                """
                SELECT id FROM v5_catalog_products
                WHERE coalesce(brand_id, 0) = coalesce(?, 0)
                  AND coalesce(category_id, 0) = coalesce(?, 0)
                  AND name = ?
                """,
                (brand_id, category_id, name),
            ).fetchone()
            return int(row["id"])

    def get_product(self, product_id: int) -> dict | None:
        ensure_v5_schema()
        with connection_scope() as conn:
            row = conn.execute(
                """
                SELECT p.*, b.name AS brand_name, c.name AS category_name
                FROM v5_catalog_products p
                LEFT JOIN v5_brands b ON b.id = p.brand_id
                LEFT JOIN v5_product_categories c ON c.id = p.category_id
                WHERE p.id = ?
                """,
                (product_id,),
            ).fetchone()
            return row_to_dict(row)
