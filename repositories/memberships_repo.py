"""SQL-only repository for memberships and plans."""

from __future__ import annotations

from db_core.connection import connection_scope
from db_core.query_utils import normalize_bool, rows_to_dicts
from db_core.schema_manager import ensure_v5_schema


class MembershipsRepository:
    def list_plans(self) -> list[dict]:
        ensure_v5_schema()
        with connection_scope() as conn:
            rows = conn.execute("SELECT * FROM v5_membership_plans ORDER BY plan_name").fetchall()
            return rows_to_dicts(rows)

    def list_customer_memberships(self) -> list[dict]:
        ensure_v5_schema()
        with connection_scope() as conn:
            rows = conn.execute(
                "SELECT * FROM v5_customer_memberships ORDER BY customer_name, customer_phone"
            ).fetchall()
            return rows_to_dicts(rows)

    def get_customer_membership(self, customer_phone: str) -> dict | None:
        ensure_v5_schema()
        with connection_scope() as conn:
            row = conn.execute(
                "SELECT * FROM v5_customer_memberships WHERE customer_phone = ?",
                (customer_phone,),
            ).fetchone()
            return dict(row) if row else None

    def upsert_plan(self, payload: dict) -> None:
        ensure_v5_schema()
        with connection_scope() as conn:
            conn.execute(
                """
                INSERT INTO v5_membership_plans(
                    plan_name, duration_days, discount_pct, wallet_amount,
                    price, description, active, updated_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(plan_name) DO UPDATE SET
                    duration_days = excluded.duration_days,
                    discount_pct = excluded.discount_pct,
                    wallet_amount = excluded.wallet_amount,
                    price = excluded.price,
                    description = excluded.description,
                    active = excluded.active,
                    updated_at = excluded.updated_at
                """,
                (
                    payload.get("plan_name"),
                    int(payload.get("duration_days", 0) or 0),
                    float(payload.get("discount_pct", 0.0) or 0.0),
                    float(payload.get("wallet_amount", 0.0) or 0.0),
                    float(payload.get("price", 0.0) or 0.0),
                    payload.get("description", ""),
                    normalize_bool(payload.get("active", True)),
                ),
            )

    def upsert_customer_membership(self, payload: dict) -> None:
        ensure_v5_schema()
        with connection_scope() as conn:
            existing = conn.execute(
                "SELECT id FROM v5_customer_memberships WHERE customer_phone = ?",
                (payload.get("customer_phone"),),
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE v5_customer_memberships
                    SET customer_name = ?, plan_name = ?, discount_pct = ?, wallet_balance = ?,
                        start_date = ?, expiry_date = ?, status = ?, price_paid = ?,
                        payment_method = ?, updated_at = datetime('now')
                    WHERE customer_phone = ?
                    """,
                    (
                        payload.get("customer_name", ""),
                        payload.get("plan_name", ""),
                        float(payload.get("discount_pct", 0.0) or 0.0),
                        float(payload.get("wallet_balance", 0.0) or 0.0),
                        payload.get("start_date", ""),
                        payload.get("expiry_date", ""),
                        payload.get("status", "Active"),
                        float(payload.get("price_paid", 0.0) or 0.0),
                        payload.get("payment_method", ""),
                        payload.get("customer_phone"),
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO v5_customer_memberships(
                        customer_phone, customer_name, plan_name, discount_pct,
                        wallet_balance, start_date, expiry_date, status,
                        price_paid, payment_method
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        payload.get("customer_phone"),
                        payload.get("customer_name", ""),
                        payload.get("plan_name", ""),
                        float(payload.get("discount_pct", 0.0) or 0.0),
                        float(payload.get("wallet_balance", 0.0) or 0.0),
                        payload.get("start_date", ""),
                        payload.get("expiry_date", ""),
                        payload.get("status", "Active"),
                        float(payload.get("price_paid", 0.0) or 0.0),
                        payload.get("payment_method", ""),
                    ),
                )

    def add_transaction(self, payload: dict) -> None:
        ensure_v5_schema()
        with connection_scope() as conn:
            membership = conn.execute(
                "SELECT id FROM v5_customer_memberships WHERE customer_phone = ?",
                (payload.get("customer_phone"),),
            ).fetchone()
            conn.execute(
                """
                INSERT INTO v5_membership_transactions(
                    customer_membership_id, customer_phone, txn_type, amount, note, reference_id
                ) VALUES(?, ?, ?, ?, ?, ?)
                """,
                (
                    membership["id"] if membership else None,
                    payload.get("customer_phone"),
                    payload.get("txn_type", "migration"),
                    float(payload.get("amount", 0.0) or 0.0),
                    payload.get("note", ""),
                    payload.get("reference_id", ""),
                ),
            )

    def delete_plan(self, plan_name: str) -> None:
        ensure_v5_schema()
        with connection_scope() as conn:
            conn.execute("DELETE FROM v5_membership_plans WHERE plan_name = ?", (plan_name,))

    def delete_customer_membership(self, customer_phone: str) -> None:
        ensure_v5_schema()
        with connection_scope() as conn:
            conn.execute("DELETE FROM v5_customer_memberships WHERE customer_phone = ?", (customer_phone,))
