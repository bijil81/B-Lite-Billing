"""v5 customer service."""

from __future__ import annotations

from repositories.customers_repo import CustomersRepository
from validators.customer_validator import validate_customer_payload
from db import db_transaction
import datetime
import random


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
                "current_due": float(customer.get("current_due", 0.0) or 0.0),
                "credit_limit": float(customer.get("credit_limit", 0.0) or 0.0),
                "is_blacklisted": bool(customer.get("is_blacklisted", 0)),
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
            credit_limit=clean.get("credit_limit"),
            is_blacklisted=clean.get("is_blacklisted"),
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

    def settle_customer_due(
        self,
        phone: str,
        amount_paid: float,
        payment_method: str,
        handled_by: str = ""
    ) -> dict:
        """Securely deducts due amount and logs a settlement payment record."""
        if amount_paid <= 0:
            raise ValueError("Settlement amount must be greater than zero.")
        
        phone = self._normalize_phone(phone)
        customer = self.get_customer_by_phone(phone)
        if not customer:
            raise ValueError("Customer not found.")
            
        current_due = float(customer.get("current_due", 0.0) or 0.0)
        if amount_paid > current_due:
            raise ValueError(f"Cannot overpay. Current due is {current_due}.")
            
        # Generate receipt no: SET-YYYYMMDD-RND4
        date_str = datetime.datetime.now().strftime("%Y%m%d")
        rnd_suffix = f"{random.randint(1000, 9999)}"
        receipt_no = f"SET-{date_str}-{rnd_suffix}"
        
        with db_transaction() as conn:
            # Update customer due atomically to prevent TOCTOU race conditions
            conn.execute(
                "UPDATE v5_customers SET current_due = MAX(0.0, ROUND(current_due - ?, 2)) WHERE legacy_phone = ?",
                (amount_paid, phone)
            )
            
            # Fetch the actual new due after atomic deduction
            row = conn.execute("SELECT current_due, credit_limit, is_blacklisted FROM v5_customers WHERE legacy_phone = ?", (phone,)).fetchone()
            actual_new_due = float(row["current_due"]) if row else 0.0
            limit = float(row["credit_limit"]) if row else 1000.0
            
            # Auto-remove blacklist if due falls below credit limit
            if actual_new_due <= limit and row and row["is_blacklisted"]:
                conn.execute("UPDATE v5_customers SET is_blacklisted = 0 WHERE legacy_phone = ?", (phone,))
            
            # Record settlement
            conn.execute(
                "INSERT INTO v5_due_settlements "
                "(customer_phone, amount_paid, payment_method, receipt_no, handled_by) "
                "VALUES (?, ?, ?, ?, ?)",
                (phone, amount_paid, payment_method, receipt_no, handled_by)
            )
            
            # Record audit log
            import json
            payload = json.dumps({
                "amount": amount_paid,
                "mode": payment_method,
                "receipt": receipt_no,
                "prev_due_approx": current_due, # Memory snapshot at time of UI interaction
                "new_due": actual_new_due # Guaranteed accurate DB value
            })
            conn.execute(
                "INSERT INTO v5_audit_log (actor, action, entity_type, entity_id, payload) "
                "VALUES (?, ?, ?, ?, ?)",
                (handled_by, "due_settlement", "customer", phone, payload)
            )
            
        self._invalidate_customer_cache(phone)
        
        return {
            "success": True,
            "receipt_no": receipt_no,
            "previous_due": actual_new_due + amount_paid,
            "amount_paid": amount_paid,
            "new_due": actual_new_due,
            "payment_method": payment_method,
            "customer_name": customer.get("name", "Unknown"),
            "customer_phone": phone,
            "handled_by": handled_by,
            "date": datetime.datetime.now().strftime("%d-%m-%Y %I:%M %p")
        }

