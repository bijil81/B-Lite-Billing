"""Purchase history and cost lookup helpers."""
from __future__ import annotations

from typing import Any

from db_core.connection import connection_scope
from db_core.query_utils import rows_to_dicts
from db_core.schema_manager import ensure_v5_schema


def _limit(value: Any, default: int = 200) -> int:
    try:
        amount = int(value)
    except Exception:
        amount = default
    return max(1, min(amount, 1000))


def list_purchase_invoices(vendor_id: int | None = None, limit: int = 300) -> list[dict]:
    ensure_v5_schema()
    with connection_scope() as conn:
        sql = """
            SELECT
                i.*,
                v.name AS vendor_name,
                v.phone AS vendor_phone,
                v.gstin AS vendor_gstin,
                COALESCE(
                    (SELECT COUNT(*) FROM v5_purchase_invoice_items ii WHERE ii.purchase_invoice_id = i.id),
                    0
                ) AS item_count
            FROM v5_purchase_invoices i
            LEFT JOIN v5_vendors v ON v.id = i.vendor_id
        """
        params: list[Any] = []
        if vendor_id:
            sql += " WHERE i.vendor_id = ?"
            params.append(int(vendor_id))
        sql += " ORDER BY i.invoice_date DESC, i.id DESC LIMIT ?"
        params.append(_limit(limit))
        return rows_to_dicts(conn.execute(sql, tuple(params)).fetchall())


def list_purchase_items(purchase_invoice_id: int) -> list[dict]:
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


def list_vendor_summary(active_only: bool = True) -> list[dict]:
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
        if active_only:
            sql += " WHERE v.active = 1"
        sql += " GROUP BY v.id ORDER BY v.name"
        return rows_to_dicts(conn.execute(sql).fetchall())


def latest_purchase_cost_for_item(item_name: str) -> dict[str, Any]:
    ensure_v5_schema()
    name = str(item_name or "").strip()
    if not name:
        return {}
    with connection_scope() as conn:
        row = conn.execute(
            """
            SELECT
                ii.item_name,
                ii.cost_price,
                ii.sale_price,
                ii.mrp,
                ii.gst_rate,
                ii.unit,
                i.invoice_no,
                i.invoice_date,
                v.name AS vendor_name
            FROM v5_purchase_invoice_items ii
            JOIN v5_purchase_invoices i ON i.id = ii.purchase_invoice_id
            LEFT JOIN v5_vendors v ON v.id = i.vendor_id
            WHERE lower(ii.item_name) = lower(?)
            ORDER BY i.invoice_date DESC, ii.id DESC
            LIMIT 1
            """,
            (name,),
        ).fetchone()
        if not row:
            return {}
        return dict(row)
