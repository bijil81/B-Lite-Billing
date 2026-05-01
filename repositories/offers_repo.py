"""SQL-only repository for offers and redeem codes."""

from __future__ import annotations

from db_core.connection import connection_scope
from db_core.query_utils import normalize_bool, rows_to_dicts
from db_core.schema_manager import ensure_v5_schema


class OffersRepository:
    def list_offers(self) -> list[dict]:
        ensure_v5_schema()
        with connection_scope() as conn:
            rows = conn.execute("SELECT * FROM v5_offers ORDER BY legacy_name").fetchall()
            return rows_to_dicts(rows)

    def upsert_offer(self, payload: dict) -> None:
        ensure_v5_schema()
        with connection_scope() as conn:
            conn.execute(
                """
                INSERT INTO v5_offers(
                    legacy_name, offer_type, value, service_name, coupon_code,
                    min_bill, valid_from, valid_to, active, notes, updated_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(legacy_name) DO UPDATE SET
                    offer_type = excluded.offer_type,
                    value = excluded.value,
                    service_name = excluded.service_name,
                    coupon_code = excluded.coupon_code,
                    min_bill = excluded.min_bill,
                    valid_from = excluded.valid_from,
                    valid_to = excluded.valid_to,
                    active = excluded.active,
                    notes = excluded.notes,
                    updated_at = excluded.updated_at
                """,
                (
                    payload.get("legacy_name"),
                    payload.get("offer_type", "percentage"),
                    float(payload.get("value", 0.0) or 0.0),
                    payload.get("service_name", ""),
                    payload.get("coupon_code", ""),
                    float(payload.get("min_bill", 0.0) or 0.0),
                    payload.get("valid_from", ""),
                    payload.get("valid_to", ""),
                    normalize_bool(payload.get("active", True)),
                    payload.get("notes", ""),
                ),
            )

    def upsert_redeem_code(self, payload: dict) -> None:
        ensure_v5_schema()
        with connection_scope() as conn:
            conn.execute(
                """
                INSERT INTO v5_redeem_codes(
                    code, customer_phone, customer_name, discount_type,
                    discount_value, min_bill, active, used, used_invoice,
                    valid_until, updated_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(code) DO UPDATE SET
                    customer_phone = excluded.customer_phone,
                    customer_name = excluded.customer_name,
                    discount_type = excluded.discount_type,
                    discount_value = excluded.discount_value,
                    min_bill = excluded.min_bill,
                    active = excluded.active,
                    used = excluded.used,
                    used_invoice = excluded.used_invoice,
                    valid_until = excluded.valid_until,
                    updated_at = excluded.updated_at
                """,
                (
                    payload.get("code"),
                    payload.get("customer_phone", ""),
                    payload.get("customer_name", ""),
                    payload.get("discount_type", "flat"),
                    float(payload.get("discount_value", 0.0) or 0.0),
                    float(payload.get("min_bill", 0.0) or 0.0),
                    normalize_bool(payload.get("active", True)),
                    normalize_bool(payload.get("used", False)),
                    payload.get("used_invoice", ""),
                    payload.get("valid_until", ""),
                ),
            )

    def delete_offer(self, legacy_name: str) -> None:
        ensure_v5_schema()
        with connection_scope() as conn:
            conn.execute("DELETE FROM v5_offers WHERE legacy_name = ?", (legacy_name,))
