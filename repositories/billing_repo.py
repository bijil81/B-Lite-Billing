"""SQL-only repository for v5 billing tables."""

from __future__ import annotations

from typing import List

from db_core.connection import connection_scope
from db_core.query_utils import row_to_dict, rows_to_dicts
from db_core.schema_manager import ensure_v5_schema


class BillingRepository:
    def create_invoice(self, conn, payload: dict) -> int:
        cursor = conn.execute(
            """
            INSERT INTO v5_invoices(
                invoice_no, invoice_date, customer_phone, customer_name,
                gross_total, discount_total, tax_total, net_total,
                loyalty_earned, loyalty_redeemed, redeem_code, notes, created_by
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.get("invoice_no"),
                payload.get("invoice_date"),
                payload.get("customer_phone", ""),
                payload.get("customer_name", ""),
                float(payload.get("gross_total", 0.0) or 0.0),
                float(payload.get("discount_total", 0.0) or 0.0),
                float(payload.get("tax_total", 0.0) or 0.0),
                float(payload.get("net_total", 0.0) or 0.0),
                int(payload.get("loyalty_earned", 0) or 0),
                int(payload.get("loyalty_redeemed", 0) or 0),
                payload.get("redeem_code", ""),
                payload.get("notes", ""),
                payload.get("created_by", ""),
            ),
        )
        return int(cursor.lastrowid)

    def get_invoice_by_no(self, invoice_no: str) -> dict | None:
        ensure_v5_schema()
        with connection_scope() as conn:
            row = conn.execute(
                "SELECT * FROM v5_invoices WHERE invoice_no = ?",
                (invoice_no,),
            ).fetchone()
            return row_to_dict(row)

    def add_invoice_item(self, conn, invoice_id: int, item: dict) -> int:
        cursor = conn.execute(
            """
            INSERT INTO v5_invoice_items(
                invoice_id, item_name, item_type, staff_name, qty, unit_price,
                line_total, discount_amount, inventory_item_name
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                invoice_id,
                item.get("item_name", item.get("name", "")),
                item.get("item_type", "service"),
                item.get("staff_name", item.get("staff", "")),
                float(item.get("qty", 1.0) or 1.0),
                float(item.get("unit_price", item.get("price", 0.0)) or 0.0),
                float(item.get("line_total", item.get("total", 0.0)) or 0.0),
                float(item.get("discount_amount", 0.0) or 0.0),
                item.get("inventory_item_name", ""),
            ),
        )
        return int(cursor.lastrowid)

    def add_payment(self, conn, invoice_id: int, payment: dict) -> None:
        conn.execute(
            """
            INSERT INTO v5_payments(invoice_id, payment_method, amount, reference_no)
            VALUES(?, ?, ?, ?)
            """,
            (
                invoice_id,
                payment.get("payment_method", payment.get("method", "Cash")),
                float(payment.get("amount", 0.0) or 0.0),
                payment.get("reference_no", ""),
            ),
        )

    def list_invoices(self, from_date: str = "", to_date: str = "") -> List[dict]:
        ensure_v5_schema()
        with connection_scope() as conn:
            if from_date and to_date:
                rows = conn.execute(
                    "SELECT * FROM v5_invoices WHERE invoice_date BETWEEN ? AND ? ORDER BY invoice_date, invoice_no",
                    (from_date, to_date),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM v5_invoices ORDER BY invoice_date, invoice_no"
                ).fetchall()
            return rows_to_dicts(rows)
