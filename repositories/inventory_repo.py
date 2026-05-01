"""SQL-only repository for v5 inventory data."""

from __future__ import annotations

from typing import List

from db_core.connection import connection_scope
from db_core.query_utils import normalize_bool, row_to_dict, rows_to_dicts
from db_core.schema_manager import ensure_v5_schema


class InventoryRepository:
    def list_items(self) -> List[dict]:
        ensure_v5_schema()
        with connection_scope() as conn:
            rows = conn.execute("SELECT * FROM v5_inventory_items ORDER BY legacy_name").fetchall()
            return rows_to_dicts(rows)

    def get_item(self, legacy_name: str) -> dict | None:
        ensure_v5_schema()
        with connection_scope() as conn:
            row = conn.execute(
                "SELECT * FROM v5_inventory_items WHERE legacy_name = ?",
                (legacy_name,),
            ).fetchone()
            return row_to_dict(row)

    def update_quantity(self, legacy_name: str, current_qty: float) -> None:
        ensure_v5_schema()
        with connection_scope() as conn:
            before = conn.total_changes
            conn.execute(
                """
                UPDATE v5_inventory_items
                SET current_qty = ?, updated_at = datetime('now')
                WHERE legacy_name = ?
                """,
                (float(current_qty or 0.0), legacy_name),
            )
            if conn.total_changes == before:
                raise ValueError(f"Inventory item not found: {legacy_name}")

    def upsert_item(self, payload: dict) -> None:
        ensure_v5_schema()
        with connection_scope() as conn:
            conn.execute(
                """
                INSERT INTO v5_inventory_items(
                    legacy_name, category, brand, unit, current_qty, min_qty,
                    cost_price, sale_price, active, updated_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(legacy_name) DO UPDATE SET
                    category = excluded.category,
                    brand = excluded.brand,
                    unit = excluded.unit,
                    current_qty = excluded.current_qty,
                    min_qty = excluded.min_qty,
                    cost_price = excluded.cost_price,
                    sale_price = excluded.sale_price,
                    active = excluded.active,
                    updated_at = excluded.updated_at
                """,
                (
                    payload.get("legacy_name"),
                    payload.get("category", ""),
                    payload.get("brand", ""),
                    payload.get("unit", "pcs"),
                    float(payload.get("current_qty", 0.0) or 0.0),
                    float(payload.get("min_qty", 0.0) or 0.0),
                    float(payload.get("cost_price", 0.0) or 0.0),
                    float(payload.get("sale_price", 0.0) or 0.0),
                    normalize_bool(payload.get("active", True)),
                ),
            )

    def add_movement(self, payload: dict) -> None:
        ensure_v5_schema()
        with connection_scope() as conn:
            item_row = conn.execute(
                "SELECT id FROM v5_inventory_items WHERE legacy_name = ?",
                (payload.get("legacy_name"),),
            ).fetchone()
            if not item_row:
                raise ValueError(f"Inventory item not found: {payload.get('legacy_name')}")
            conn.execute(
                """
                INSERT INTO v5_inventory_movements(
                    item_id, movement_type, qty_delta, reference_type, reference_id, note
                ) VALUES(?, ?, ?, ?, ?, ?)
                """,
                (
                    item_row["id"],
                    payload.get("movement_type", "adjustment"),
                    float(payload.get("qty_delta", 0.0) or 0.0),
                    payload.get("reference_type", ""),
                    payload.get("reference_id", ""),
                    payload.get("note", ""),
                ),
            )

    def deactivate_item(self, legacy_name: str) -> None:
        ensure_v5_schema()
        with connection_scope() as conn:
            conn.execute(
                """
                UPDATE v5_inventory_items
                SET active = 0, updated_at = datetime('now')
                WHERE legacy_name = ?
                """,
                (legacy_name,),
            )

    def list_deleted_items(self) -> List[dict]:
        ensure_v5_schema()
        with connection_scope() as conn:
            # Try soft-delete column first
            try:
                rows = conn.execute(
                    """
                    SELECT legacy_name, category, legacy_name as name,
                           is_deleted, deleted_at, deleted_by
                    FROM v5_inventory_items
                    WHERE is_deleted = 1
                    ORDER BY deleted_at DESC
                    """
                ).fetchall()
                return rows_to_dicts(rows)
            except Exception:
                # Column doesn't exist yet
                return []
