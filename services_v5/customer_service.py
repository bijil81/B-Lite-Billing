"""v5 customer service."""

from __future__ import annotations

from repositories.customers_repo import CustomersRepository
from validators.customer_validator import validate_customer_payload


class CustomerService:
    def __init__(self, repo: CustomersRepository | None = None):
        self.repo = repo or CustomersRepository()
        self._customers_cache: list[dict] | None = None
        self._customer_by_phone_cache: dict[str, dict | None] = {}
        self._history_cache: dict[str, list[dict]] = {}
        self._legacy_map_cache: dict | None = None

    def _normalize_phone(self, phone: str) -> str:
        return str(phone or "").strip()

    def _invalidate_customer_cache(self, phone: str = "") -> None:
        normalized = self._normalize_phone(phone)
        self._customers_cache = None
        self._legacy_map_cache = None
        if normalized:
            self._customer_by_phone_cache.pop(normalized, None)
            self._history_cache.pop(normalized, None)
        else:
            self._customer_by_phone_cache.clear()
            self._history_cache.clear()

    def list_customers(self):
        if self._customers_cache is None:
            self._customers_cache = self.repo.list_all()
        return [dict(row) for row in self._customers_cache]

    def get_customer_by_phone(self, phone: str):
        normalized = self._normalize_phone(phone)
        if not normalized:
            return None
        if normalized not in self._customer_by_phone_cache:
            self._customer_by_phone_cache[normalized] = self.repo.get_by_phone(normalized)
        customer = self._customer_by_phone_cache.get(normalized)
        return dict(customer) if customer else None

    def get_customer_history(self, phone: str) -> list[dict]:
        normalized = self._normalize_phone(phone)
        if not normalized:
            return []
        if normalized not in self._history_cache:
            self._history_cache[normalized] = self.repo.list_visits(normalized)
        return [dict(row) for row in self._history_cache.get(normalized, [])]

    def build_legacy_customer_map(self) -> dict:
        if self._legacy_map_cache is not None:
            return {
                phone: {**payload, "visits": [dict(visit) for visit in payload.get("visits", [])]}
                for phone, payload in self._legacy_map_cache.items()
            }

        result = {}
        for customer in self.list_customers():
            phone = customer.get("legacy_phone", "")
            history = self.get_customer_history(phone)
            visits = []
            for row in history:
                visits.append({
                    "date": row.get("visit_date", ""),
                    "invoice": row.get("invoice_no", ""),
                    "items": [],
                    "total": float(row.get("amount", 0.0) or 0.0),
                    "payment": "",
                    "note": row.get("note", ""),
                })
            result[phone] = {
                "name": customer.get("name", ""),
                "phone": phone,
                "birthday": customer.get("birthday", ""),
                "vip": bool(customer.get("vip", 0)),
                "points": int(customer.get("points_balance", 0) or 0),
                "visits": visits,
                "created": customer.get("created_at", ""),
            }
        # Filter out soft-deleted customers
        try:
            from db_core.connection import connection_scope
            from db_core.schema_manager import ensure_v5_schema
            ensure_v5_schema()
            with connection_scope() as conn:
                rows = conn.execute(
                    "SELECT legacy_phone FROM v5_customers WHERE COALESCE(is_deleted, 0) = 1"
                ).fetchall()
                deleted_phones = {str(r["legacy_phone"]).strip() for r in rows}
                result = {ph: data for ph, data in result.items() if ph not in deleted_phones}
        except Exception:
            pass
        self._legacy_map_cache = {
            phone: {**payload, "visits": [dict(visit) for visit in payload.get("visits", [])]}
            for phone, payload in result.items()
        }
        return result

    def save_customer(self, payload: dict) -> None:
        clean = validate_customer_payload(payload)
        self.repo.upsert_legacy_customer(
            phone=clean["phone"],
            name=clean["name"],
            birthday=clean["birthday"],
            vip=clean["vip"],
            points_balance=clean["points_balance"],
        )
        self._invalidate_customer_cache(clean["phone"])

    def record_visit(self, phone: str, invoice_no: str, amount: float, payment: str = "") -> int:
        if not phone:
            return 0
        points_earned = int(float(amount or 0.0) // 100)
        self.repo.add_visit(phone, invoice_no, amount, payment)
        if points_earned:
            self.repo.add_loyalty_entry(phone, points_earned, "earn", invoice_no, "Legacy billing visit")
        self._invalidate_customer_cache(phone)
        return points_earned

    def redeem_points(self, phone: str, points: int) -> float:
        customer = self.repo.get_by_phone(phone)
        if not customer:
            return 0.0
        available = int(customer.get("points_balance", 0) or 0)
        use = min(int(points or 0), available)
        if use > 0:
            self.repo.add_loyalty_entry(phone, -use, "redeem", "", "Legacy billing redeem")
            self._invalidate_customer_cache(phone)
        return float(use)

    def set_vip(self, phone: str, vip: bool) -> None:
        self.repo.set_vip(phone, vip)
        self._invalidate_customer_cache(phone)

    def set_points_balance(self, phone: str, points_balance: int) -> None:
        self.repo.set_points_balance(phone, points_balance)
        self._invalidate_customer_cache(phone)

    def delete_customer(self, phone: str) -> None:
        self.repo.delete_by_phone(phone)
        self._invalidate_customer_cache(phone)

    def save_legacy_customer(
        self,
        phone: str,
        name: str,
        birthday: str = "",
        vip: bool = False,
        points_balance: int = 0,
    ) -> None:
        self.save_customer(
            {
                "phone": phone,
                "name": name,
                "birthday": birthday,
                "vip": vip,
                "points_balance": points_balance,
            }
        )
