"""SQL-only repository for reporting queries."""

from __future__ import annotations

from db_core.connection import connection_scope
from db_core.query_utils import rows_to_dicts
from db_core.schema_manager import ensure_v5_schema


class ReportsRepository:
    def sales_summary(self, from_date: str, to_date: str) -> dict:
        ensure_v5_schema()
        with connection_scope() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS invoice_count,
                       COALESCE(SUM(net_total), 0) AS net_total,
                       COALESCE(SUM(discount_total), 0) AS discount_total,
                       COALESCE(SUM(tax_total), 0) AS tax_total
                FROM v5_invoices
                WHERE invoice_date BETWEEN ? AND ?
                  AND COALESCE(is_deleted, 0) = 0
                """,
                (from_date, to_date),
            ).fetchone()
            expense_row = conn.execute(
                """
                SELECT COALESCE(SUM(amount), 0) AS expense_total
                FROM v5_expenses
                WHERE expense_date BETWEEN ? AND ?
                """,
                (from_date, to_date),
            ).fetchone()
            return {
                "invoice_count": row["invoice_count"],
                "net_total": row["net_total"],
                "discount_total": row["discount_total"],
                "tax_total": row["tax_total"],
                "expense_total": expense_row["expense_total"],
            }

    def payment_breakdown(self, from_date: str, to_date: str) -> list[dict]:
        ensure_v5_schema()
        with connection_scope() as conn:
            rows = conn.execute(
                """
                SELECT p.payment_method, COALESCE(SUM(p.amount), 0) AS amount_total
                FROM v5_payments p
                JOIN v5_invoices i ON i.id = p.invoice_id
                WHERE i.invoice_date BETWEEN ? AND ?
                  AND COALESCE(i.is_deleted, 0) = 0
                GROUP BY p.payment_method
                ORDER BY amount_total DESC, p.payment_method
                """,
                (from_date, to_date),
            ).fetchall()
            return rows_to_dicts(rows)

    def top_services(self, from_date: str, to_date: str) -> list[dict]:
        ensure_v5_schema()
        with connection_scope() as conn:
            rows = conn.execute(
                """
                SELECT item_name, COUNT(*) AS row_count, COALESCE(SUM(line_total), 0) AS revenue
                FROM v5_invoice_items ii
                JOIN v5_invoices i ON i.id = ii.invoice_id
                WHERE i.invoice_date BETWEEN ? AND ?
                  AND COALESCE(i.is_deleted, 0) = 0
                GROUP BY item_name
                ORDER BY revenue DESC, row_count DESC, item_name
                """,
                (from_date, to_date),
            ).fetchall()
            return rows_to_dicts(rows)

    def report_rows(self, from_date: str = "", to_date: str = "", search: str = "") -> list[dict]:
        ensure_v5_schema()
        search_like = f"%{search.lower()}%" if search else ""
        with connection_scope() as conn:
            query = """
                SELECT i.invoice_date AS date,
                       COALESCE(substr(i.invoice_date, 12, 5), '') AS time,
                       i.invoice_no AS invoice,
                       i.customer_name AS name,
                       i.customer_phone AS phone,
                       COALESCE(i.created_by, '') AS created_by,
                       COALESCE((SELECT p.payment_method
                                 FROM v5_payments p
                                 WHERE p.invoice_id = i.id
                                 ORDER BY p.id LIMIT 1), '') AS payment,
                       i.net_total AS total,
                       i.discount_total AS discount,
                       i.tax_total AS gst_amount,
                       MAX(0, i.net_total - i.tax_total) AS taxable_amount,
                       COALESCE((SELECT GROUP_CONCAT(
                                    ii.item_type || '~' || ii.item_name || '~' || printf('%.2f', ii.unit_price) || '~' || printf('%.2f', ii.qty),
                                    '|'
                                )
                                FROM v5_invoice_items ii
                                WHERE ii.invoice_id = i.id), '') AS items_raw
                FROM v5_invoices i
                WHERE 1 = 1
                  AND COALESCE(i.is_deleted, 0) = 0
            """
            params: list[object] = []
            if from_date:
                query += " AND i.invoice_date >= ?"
                params.append(from_date)
            if to_date:
                query += " AND i.invoice_date <= ?"
                params.append(to_date)
            if search_like:
                query += " AND (LOWER(i.customer_name) LIKE ? OR i.customer_phone LIKE ?)"
                params.extend([search_like, f"%{search}%"])
            query += " ORDER BY i.invoice_date DESC, i.invoice_no DESC"
            rows = conn.execute(query, tuple(params)).fetchall()
            return rows_to_dicts(rows)
