"""SQL-only repository for v5 product variants."""

from __future__ import annotations

from db_core.connection import connection_scope
from db_core.query_utils import normalize_bool, row_to_dict, rows_to_dicts
from db_core.schema_manager import ensure_v5_schema


_GROCERY_VARIANT_DEFAULTS = {
    "sale_unit": "pcs",
    "base_unit": "pcs",
    "unit_multiplier": 1.0,
    "allow_decimal_qty": 0,
    "mrp": 0.0,
    "gst_rate": 0.0,
    "cess_rate": 0.0,
    "hsn_sac": "",
    "price_includes_tax": 1,
    "is_weighed": 0,
}

_GROCERY_MOVEMENT_DEFAULTS = {
    "qty_unit": "",
    "unit_cost": 0.0,
    "supplier_name": "",
    "purchase_ref": "",
    "batch_no": "",
    "expiry_date": "",
}


def _table_columns(conn, table: str) -> set[str]:
    return {str(row["name"]) for row in conn.execute(f"PRAGMA table_info({table})")}


class ProductVariantsRepository:
    def list_all(self, active_only: bool = True) -> list[dict]:
        ensure_v5_schema()
        sql = """
            SELECT
                v.*,
                p.name AS product_name,
                p.base_name AS product_base_name,
                b.name AS brand_name,
                c.name AS category_name
            FROM v5_product_variants v
            JOIN v5_catalog_products p ON p.id = v.product_id
            LEFT JOIN v5_brands b ON b.id = p.brand_id
            LEFT JOIN v5_product_categories c ON c.id = p.category_id
        """
        params = ()
        if active_only:
            sql += " WHERE v.active = 1 AND p.active = 1"
        sql += " ORDER BY coalesce(b.name, ''), p.name, v.pack_label"
        with connection_scope() as conn:
            rows = conn.execute(sql, params).fetchall()
            return rows_to_dicts(rows)

    def search_sellable(self, query: str, limit: int = 20) -> list[dict]:
        ensure_v5_schema()
        q = f"%{query.strip().lower()}%"
        with connection_scope() as conn:
            rows = conn.execute(
                """
                SELECT
                    v.*,
                    p.name AS product_name,
                    p.base_name AS product_base_name,
                    b.name AS brand_name,
                    c.name AS category_name
                FROM v5_product_variants v
                JOIN v5_catalog_products p ON p.id = v.product_id
                LEFT JOIN v5_brands b ON b.id = p.brand_id
                LEFT JOIN v5_product_categories c ON c.id = p.category_id
                WHERE v.active = 1
                  AND (
                    lower(coalesce(b.name, '')) LIKE ? OR
                    lower(p.name) LIKE ? OR
                    lower(coalesce(v.variant_name, '')) LIKE ? OR
                    lower(coalesce(v.pack_label, '')) LIKE ? OR
                    lower(coalesce(v.bill_label, '')) LIKE ? OR
                    lower(coalesce(v.sku, '')) LIKE ? OR
                    lower(coalesce(v.barcode, '')) LIKE ?
                  )
                ORDER BY coalesce(b.name, ''), p.name, v.pack_label
                LIMIT ?
                """,
                (q, q, q, q, q, q, q, int(limit)),
            ).fetchall()
            return rows_to_dicts(rows)

    def get_variant(self, variant_id: int) -> dict | None:
        ensure_v5_schema()
        with connection_scope() as conn:
            row = conn.execute(
                "SELECT * FROM v5_product_variants WHERE id = ?",
                (variant_id,),
            ).fetchone()
            return row_to_dict(row)

    def upsert_variant(self, payload: dict) -> int:
        ensure_v5_schema()
        product_id = int(payload.get("product_id") or 0)
        pack_label = str(payload.get("pack_label", "")).strip()
        if not product_id:
            raise ValueError("Variant product_id is required")
        if not pack_label:
            raise ValueError("Variant pack_label is required")
        sku = str(payload.get("sku", "")).strip()
        barcode = str(payload.get("barcode", "")).strip()
        with connection_scope() as conn:
            table_columns = _table_columns(conn, "v5_product_variants")
            base_values = {
                "product_id": product_id,
                "variant_name": str(payload.get("variant_name", "")).strip(),
                "unit_value": float(payload.get("unit_value", 0.0) or 0.0),
                "unit_type": str(payload.get("unit_type", "pcs")).strip() or "pcs",
                "pack_label": pack_label,
                "bill_label": str(payload.get("bill_label", "")).strip(),
                "sku": sku,
                "barcode": barcode,
                "sale_price": float(payload.get("sale_price", 0.0) or 0.0),
                "cost_price": float(payload.get("cost_price", 0.0) or 0.0),
                "stock_qty": float(payload.get("stock_qty", 0.0) or 0.0),
                "reorder_level": float(payload.get("reorder_level", 0.0) or 0.0),
                "active": normalize_bool(payload.get("active", True)),
            }
            for key, default in _GROCERY_VARIANT_DEFAULTS.items():
                if key in table_columns:
                    value = payload.get(key, default)
                    if key in {"sale_unit", "base_unit", "hsn_sac"}:
                        value = str(value or default).strip()
                    elif key in {"allow_decimal_qty", "price_includes_tax", "is_weighed"}:
                        value = normalize_bool(value)
                    else:
                        value = float(value or default)
                    base_values[key] = value

            columns = list(base_values)
            placeholders = ", ".join(["?"] * len(columns))
            insert_columns = ", ".join(columns)
            update_columns = [
                column for column in columns
                if column not in {"product_id", "pack_label"}
            ]
            update_sql = ",\n                    ".join(
                [f"{column} = excluded.{column}" for column in update_columns]
                + ["updated_at = excluded.updated_at"]
            )
            conn.execute(
                f"""
                INSERT INTO v5_product_variants(
                    {insert_columns}, updated_at
                ) VALUES({placeholders}, datetime('now'))
                ON CONFLICT(product_id, pack_label) DO UPDATE SET
                    {update_sql}
                """,
                tuple(base_values[column] for column in columns),
            )
            row = conn.execute(
                "SELECT id FROM v5_product_variants WHERE product_id = ? AND pack_label = ?",
                (product_id, pack_label),
            ).fetchone()
            return int(row["id"])

    def add_stock_movement(self, payload: dict) -> None:
        ensure_v5_schema()
        variant_id = int(payload.get("variant_id") or 0)
        if not variant_id:
            raise ValueError("variant_id is required")
        qty_delta = float(payload.get("qty_delta", 0.0) or 0.0)
        with connection_scope() as conn:
            conn.execute(
                "UPDATE v5_product_variants SET stock_qty = stock_qty + ?, updated_at = datetime('now') WHERE id = ?",
                (qty_delta, variant_id),
            )
            movement_values = {
                "variant_id": variant_id,
                "movement_type": str(payload.get("movement_type", "adjustment")).strip() or "adjustment",
                "qty_delta": qty_delta,
                "reference_type": str(payload.get("reference_type", "")).strip(),
                "reference_id": str(payload.get("reference_id", "")).strip(),
                "note": str(payload.get("note", "")).strip(),
            }
            table_columns = _table_columns(conn, "v5_product_variant_movements")
            for key, default in _GROCERY_MOVEMENT_DEFAULTS.items():
                if key not in table_columns:
                    continue
                value = payload.get(key, default)
                if key == "unit_cost":
                    value = float(value or default)
                else:
                    value = str(value or default).strip()
                movement_values[key] = value
            columns = list(movement_values)
            placeholders = ", ".join(["?"] * len(columns))
            conn.execute(
                f"""
                INSERT INTO v5_product_variant_movements(
                    {", ".join(columns)}
                ) VALUES({placeholders})
                """,
                tuple(movement_values[column] for column in columns),
            )

    def deactivate_variant(self, variant_id: int) -> None:
        ensure_v5_schema()
        with connection_scope() as conn:
            conn.execute(
                "UPDATE v5_product_variants SET active = 0, updated_at = datetime('now') WHERE id = ?",
                (int(variant_id),),
            )
