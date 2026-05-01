"""SQL-only repository for v5 vendor purchase data."""

from __future__ import annotations

from db_core.connection import connection_scope
from db_core.query_utils import normalize_bool, row_to_dict, rows_to_dicts
from db_core.schema_manager import ensure_v5_schema


def _table_columns(conn, table: str) -> set[str]:
    return {str(row["name"]) for row in conn.execute(f"PRAGMA table_info({table})")}


class PurchaseRepository:
    def list_vendors(self, active_only: bool = True) -> list[dict]:
        ensure_v5_schema()
        sql = "SELECT * FROM v5_vendors"
        if active_only:
            sql += " WHERE active = 1"
        sql += " ORDER BY name"
        with connection_scope() as conn:
            return rows_to_dicts(conn.execute(sql).fetchall())

    def get_vendor_by_name(self, name: str) -> dict | None:
        ensure_v5_schema()
        with connection_scope() as conn:
            row = conn.execute(
                "SELECT * FROM v5_vendors WHERE lower(name) = lower(?)",
                (str(name or "").strip(),),
            ).fetchone()
            return row_to_dict(row)

    def get_vendor_by_id(self, vendor_id: int) -> dict | None:
        ensure_v5_schema()
        with connection_scope() as conn:
            row = conn.execute(
                "SELECT * FROM v5_vendors WHERE id = ?",
                (int(vendor_id),),
            ).fetchone()
            return row_to_dict(row)

    def upsert_vendor(self, conn, payload: dict) -> int:
        columns = _table_columns(conn, "v5_vendors")
        values = {
            "name": str(payload.get("name", "")).strip(),
            "phone": str(payload.get("phone", "")).strip(),
            "gstin": str(payload.get("gstin", "")).strip(),
            "address": str(payload.get("address", "")).strip(),
            "active": normalize_bool(payload.get("active", True)),
        }
        if "opening_balance" in columns:
            values["opening_balance"] = float(payload.get("opening_balance", 0.0) or 0.0)
        insert_columns = list(values)
        placeholders = ", ".join(["?"] * len(insert_columns))
        update_columns = [column for column in insert_columns if column != "name"]
        update_sql = ",\n                    ".join(
            [f"{column} = excluded.{column}" for column in update_columns]
            + ["updated_at = excluded.updated_at"]
        )
        conn.execute(
            f"""
            INSERT INTO v5_vendors({", ".join(insert_columns)}, updated_at)
            VALUES({placeholders}, datetime('now'))
            ON CONFLICT(name) DO UPDATE SET
                {update_sql}
            """,
            tuple(values[column] for column in insert_columns),
        )
        row = conn.execute(
            "SELECT id FROM v5_vendors WHERE lower(name) = lower(?)",
            (values["name"],),
        ).fetchone()
        return int(row["id"])

    def save_vendor(self, conn, payload: dict) -> int:
        vendor_id = int(payload.get("vendor_id") or 0)
        columns = _table_columns(conn, "v5_vendors")
        values = {
            "name": str(payload.get("name", "")).strip(),
            "phone": str(payload.get("phone", "")).strip(),
            "gstin": str(payload.get("gstin", "")).strip(),
            "address": str(payload.get("address", "")).strip(),
            "active": normalize_bool(payload.get("active", True)),
        }
        if "opening_balance" in columns:
            values["opening_balance"] = float(payload.get("opening_balance", 0.0) or 0.0)
        if vendor_id > 0:
            set_clause = ", ".join(f"{key} = ?" for key in values)
            conn.execute(
                f"""
                UPDATE v5_vendors
                SET {set_clause}, updated_at = datetime('now')
                WHERE id = ?
                """,
                tuple(values[key] for key in values) + (vendor_id,),
            )
            return vendor_id
        return self.upsert_vendor(conn, values)

    def deactivate_vendor(self, vendor_id: int) -> None:
        ensure_v5_schema()
        with connection_scope() as conn:
            conn.execute(
                "UPDATE v5_vendors SET active = 0, updated_at = datetime('now') WHERE id = ?",
                (int(vendor_id),),
            )

    def list_vendor_purchase_summary(self, active_only: bool = True) -> list[dict]:
        ensure_v5_schema()
        with connection_scope() as conn:
            sql = """
                SELECT
                    v.id,
                    v.name,
                    v.phone,
                    v.gstin,
                    v.address,
                    v.opening_balance,
                    v.active,
                    COUNT(i.id) AS purchase_count,
                    COALESCE(SUM(i.net_total), 0) AS total_purchase,
                    COALESCE(MAX(i.invoice_date), '') AS last_purchase_date,
                    COALESCE(MAX(i.invoice_no), '') AS last_invoice_no
                FROM v5_vendors v
                LEFT JOIN v5_purchase_invoices i ON i.vendor_id = v.id
            """
            params: tuple = ()
            if active_only:
                sql += " WHERE v.active = 1"
            sql += " GROUP BY v.id ORDER BY v.name"
            rows = conn.execute(sql, params).fetchall()
            return rows_to_dicts(rows)

    def list_vendor_purchase_invoices(self, vendor_id: int | None = None) -> list[dict]:
        ensure_v5_schema()
        with connection_scope() as conn:
            sql = """
                SELECT i.*, v.name AS vendor_name, v.phone AS vendor_phone, v.gstin AS vendor_gstin,
                       COALESCE((SELECT COUNT(*) FROM v5_purchase_invoice_items ii WHERE ii.purchase_invoice_id = i.id), 0) AS item_count
                FROM v5_purchase_invoices i
                LEFT JOIN v5_vendors v ON v.id = i.vendor_id
            """
            params: tuple = ()
            if vendor_id:
                sql += " WHERE i.vendor_id = ?"
                params = (int(vendor_id),)
            sql += " ORDER BY i.invoice_date DESC, i.id DESC"
            rows = conn.execute(sql, params).fetchall()
            return rows_to_dicts(rows)

    def list_vendor_purchase_items(self, purchase_invoice_id: int) -> list[dict]:
        return self.list_purchase_items(purchase_invoice_id)

    def create_purchase_invoice(self, conn, payload: dict) -> int:
        cursor = conn.execute(
            """
            INSERT INTO v5_purchase_invoices(
                vendor_id, invoice_no, invoice_date, gross_total, tax_total, net_total, notes, updated_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            (
                int(payload.get("vendor_id") or 0) or None,
                payload.get("invoice_no", ""),
                payload.get("invoice_date", ""),
                float(payload.get("gross_total", 0.0) or 0.0),
                float(payload.get("tax_total", 0.0) or 0.0),
                float(payload.get("net_total", 0.0) or 0.0),
                payload.get("notes", ""),
            ),
        )
        return int(cursor.lastrowid)

    def add_purchase_item(self, conn, purchase_invoice_id: int, item: dict) -> int:
        cursor = conn.execute(
            """
            INSERT INTO v5_purchase_invoice_items(
                purchase_invoice_id, variant_id, item_name, qty, unit, cost_price,
                sale_price, mrp, gst_rate, hsn_sac, batch_no, expiry_date
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(purchase_invoice_id),
                int(item.get("variant_id") or 0) or None,
                item.get("item_name", ""),
                float(item.get("qty", 0.0) or 0.0),
                item.get("unit", "pcs"),
                float(item.get("cost_price", 0.0) or 0.0),
                float(item.get("sale_price", 0.0) or 0.0),
                float(item.get("mrp", 0.0) or 0.0),
                float(item.get("gst_rate", 0.0) or 0.0),
                item.get("hsn_sac", ""),
                item.get("batch_no", ""),
                item.get("expiry_date", ""),
            ),
        )
        return int(cursor.lastrowid)

    def list_purchase_invoices(self) -> list[dict]:
        ensure_v5_schema()
        with connection_scope() as conn:
            rows = conn.execute(
                """
                SELECT i.*, v.name AS vendor_name,
                       COALESCE((SELECT COUNT(*) FROM v5_purchase_invoice_items ii WHERE ii.purchase_invoice_id = i.id), 0) AS item_count
                FROM v5_purchase_invoices i
                LEFT JOIN v5_vendors v ON v.id = i.vendor_id
                ORDER BY i.invoice_date DESC, i.id DESC
                """
            ).fetchall()
            return rows_to_dicts(rows)

    def list_purchase_items(self, purchase_invoice_id: int) -> list[dict]:
        ensure_v5_schema()
        with connection_scope() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM v5_purchase_invoice_items
                WHERE purchase_invoice_id = ?
                ORDER BY id
                """,
                (int(purchase_invoice_id),),
            ).fetchall()
            return rows_to_dicts(rows)
