"""v5 customers repository."""

from __future__ import annotations

from typing import List, Optional

from db_core.connection import connection_scope
from db_core.query_utils import normalize_bool, row_to_dict, rows_to_dicts
from db_core.schema_manager import ensure_v5_schema


class CustomersRepository:
    def list_all(self) -> List[dict]:
        ensure_v5_schema()
        with connection_scope() as conn:
            rows = conn.execute("""
                SELECT id, legacy_phone, name, birthday, vip, points_balance,
                       created_at, updated_at
                FROM v5_customers
                WHERE COALESCE(is_deleted, 0) = 0
                ORDER BY name, legacy_phone
            """).fetchall()
            return rows_to_dicts(rows)

    def get_by_phone(self, phone: str) -> Optional[dict]:
        ensure_v5_schema()
        with connection_scope() as conn:
            row = conn.execute("""
                SELECT id, legacy_phone, name, birthday, vip, points_balance,
                       created_at, updated_at
                FROM v5_customers
                WHERE legacy_phone = ? AND COALESCE(is_deleted, 0) = 0
            """, (phone,)).fetchone()
            return row_to_dict(row)

    def list_visits(self, phone: str) -> List[dict]:
        ensure_v5_schema()
        with connection_scope() as conn:
            row = conn.execute("SELECT id FROM v5_customers WHERE legacy_phone = ?", (phone,)).fetchone()
            if not row:
                return []
            visits = conn.execute(
                "SELECT visit_date, invoice_no, amount, note FROM v5_customer_visits WHERE customer_id = ? ORDER BY visit_date",
                (row["id"],),
            ).fetchall()
            return rows_to_dicts(visits)

    def add_visit(self, phone: str, invoice_no: str, amount: float, note: str = "") -> None:
        ensure_v5_schema()
        with connection_scope() as conn:
            customer = conn.execute("SELECT id FROM v5_customers WHERE legacy_phone = ?", (phone,)).fetchone()
            if not customer:
                return
            conn.execute(
                "INSERT INTO v5_customer_visits(customer_id, visit_date, note, amount, invoice_no) VALUES(?, datetime('now'), ?, ?, ?)",
                (customer["id"], note, float(amount), invoice_no),
            )

    def add_loyalty_entry(self, phone: str, points_delta: int, txn_type: str, reference_id: str = "", note: str = "") -> None:
        ensure_v5_schema()
        with connection_scope() as conn:
            customer = conn.execute("SELECT id FROM v5_customers WHERE legacy_phone = ?", (phone,)).fetchone()
            if not customer:
                return
            conn.execute(
                "UPDATE v5_customers SET points_balance = COALESCE(points_balance, 0) + ?, updated_at = datetime('now') WHERE id = ?",
                (int(points_delta), customer["id"]),
            )
            conn.execute(
                "INSERT INTO v5_loyalty_ledger(customer_id, txn_type, points_delta, reference_type, reference_id, note) VALUES(?, ?, ?, 'customer', ?, ?)",
                (customer["id"], txn_type, int(points_delta), reference_id, note),
            )

    def set_vip(self, phone: str, vip: bool) -> None:
        ensure_v5_schema()
        with connection_scope() as conn:
            conn.execute(
                "UPDATE v5_customers SET vip = ?, updated_at = datetime('now') WHERE legacy_phone = ?",
                (normalize_bool(vip), phone),
            )

    def set_points_balance(self, phone: str, points_balance: int) -> None:
        ensure_v5_schema()
        with connection_scope() as conn:
            conn.execute(
                "UPDATE v5_customers SET points_balance = ?, updated_at = datetime('now') WHERE legacy_phone = ?",
                (int(points_balance), phone),
            )

    def delete_by_phone(self, phone: str) -> None:
        ensure_v5_schema()
        with connection_scope() as conn:
            conn.execute("DELETE FROM v5_customers WHERE legacy_phone = ?", (phone,))

    def upsert_legacy_customer(
        self,
        phone: str,
        name: str,
        birthday: str = "",
        vip: bool = False,
        points_balance: int = 0,
    ) -> None:
        ensure_v5_schema()
        with connection_scope() as conn:
            conn.execute("""
                INSERT INTO v5_customers(
                    legacy_phone, name, birthday, vip, points_balance, updated_at
                )
                VALUES(?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(legacy_phone) DO UPDATE SET
                    name = excluded.name,
                    birthday = excluded.birthday,
                    vip = excluded.vip,
                    points_balance = excluded.points_balance,
                    updated_at = excluded.updated_at
            """, (
                phone,
                name,
                birthday,
                normalize_bool(vip),
                int(points_balance),
            ))