"""Workflow layer for membership plans and customer memberships."""

from __future__ import annotations

from repositories.memberships_repo import MembershipsRepository


class MembershipService:
    def __init__(self, repo: MembershipsRepository | None = None):
        self.repo = repo or MembershipsRepository()

    def list_plans(self) -> list[dict]:
        return self.repo.list_plans()

    def list_customer_memberships(self) -> list[dict]:
        return self.repo.list_customer_memberships()

    def get_all(self) -> dict:
        result = {}
        for row in self.repo.list_customer_memberships():
            result[row.get("customer_phone", "")] = self._to_legacy_membership(row)
        return result

    def get_customer_membership(self, customer_phone: str) -> dict | None:
        row = self.repo.get_customer_membership(customer_phone)
        return self._to_legacy_membership(row) if row else None

    def get_templates(self) -> list[dict]:
        return [
            {
                "name": row.get("plan_name", ""),
                "price": float(row.get("price", 0.0) or 0.0),
                "duration_days": int(row.get("duration_days", 0) or 0),
                "discount_pct": float(row.get("discount_pct", 0.0) or 0.0),
                "wallet": float(row.get("wallet_amount", 0.0) or 0.0),
                "description": row.get("description", ""),
                "active": bool(row.get("active", 1)),
            }
            for row in self.repo.list_plans()
            if bool(row.get("active", 1))
        ]

    def save_plan(self, payload: dict) -> None:
        self.repo.upsert_plan(payload)

    def save_all_plans(self, templates: list[dict]) -> None:
        existing_names = {row.get("plan_name", "") for row in self.repo.list_plans()}
        incoming_names = {
            str(template.get("name", "")).strip()
            for template in templates
            if str(template.get("name", "")).strip()
        }
        for template in templates:
            self.repo.upsert_plan(
                {
                    "plan_name": template.get("name", ""),
                    "duration_days": template.get("duration_days", 0),
                    "discount_pct": template.get("discount_pct", 0.0),
                    "wallet_amount": template.get("wallet", 0.0),
                    "price": template.get("price", 0.0),
                    "description": template.get("description", ""),
                    "active": template.get("active", True),
                }
            )
        for stale_name in existing_names - incoming_names:
            if stale_name:
                self.repo.delete_plan(stale_name)

    def save_customer_membership(self, payload: dict) -> None:
        self.repo.upsert_customer_membership(payload)

    def save_all(self, data: dict) -> None:
        existing_phones = {row.get("customer_phone", "") for row in self.repo.list_customer_memberships()}
        incoming_phones = {phone for phone in data.keys() if str(phone).strip()}
        for phone, membership in data.items():
            self.repo.upsert_customer_membership(
                {
                    "customer_phone": phone,
                    "customer_name": membership.get("customer_name", membership.get("name", "")),
                    "plan_name": membership.get("package_name", membership.get("package", "")),
                    "discount_pct": membership.get("discount_pct", 0.0),
                    "wallet_balance": membership.get("wallet_balance", 0.0),
                    "start_date": membership.get("start", ""),
                    "expiry_date": membership.get("expiry", ""),
                    "status": membership.get("status", "Active"),
                    "price_paid": membership.get("price_paid", 0.0),
                    "payment_method": membership.get("payment", ""),
                }
            )
        for stale_phone in existing_phones - incoming_phones:
            if stale_phone:
                self.repo.delete_customer_membership(stale_phone)

    def add_transaction(self, payload: dict) -> None:
        self.repo.add_transaction(payload)

    def delete_customer_membership(self, customer_phone: str) -> None:
        self.repo.delete_customer_membership(customer_phone)

    def adjust_wallet(self, customer_phone: str, amount_delta: float) -> float:
        membership = self.get_customer_membership(customer_phone)
        if not membership:
            return 0.0
        new_balance = max(0.0, float(membership.get("wallet_balance", 0.0) or 0.0) + float(amount_delta or 0.0))
        self.repo.upsert_customer_membership(
            {
                "customer_phone": customer_phone,
                "customer_name": membership.get("customer_name", ""),
                "plan_name": membership.get("package_name", ""),
                "discount_pct": membership.get("discount_pct", 0.0),
                "wallet_balance": new_balance,
                "start_date": membership.get("start", ""),
                "expiry_date": membership.get("expiry", ""),
                "status": membership.get("status", "Active"),
                "price_paid": membership.get("price_paid", 0.0),
                "payment_method": membership.get("payment", ""),
            }
        )
        self.repo.add_transaction(
            {
                "customer_phone": customer_phone,
                "txn_type": "wallet_adjustment",
                "amount": amount_delta,
                "note": "Wallet updated",
                "reference_id": "",
            }
        )
        return new_balance

    @staticmethod
    def _to_legacy_membership(row: dict) -> dict:
        return {
            "customer_name": row.get("customer_name", ""),
            "name": row.get("customer_name", ""),
            "package_name": row.get("plan_name", ""),
            "package": row.get("plan_name", ""),
            "discount_pct": float(row.get("discount_pct", 0.0) or 0.0),
            "wallet_balance": float(row.get("wallet_balance", 0.0) or 0.0),
            "start": row.get("start_date", ""),
            "expiry": row.get("expiry_date", ""),
            "status": row.get("status", "Active"),
            "price_paid": float(row.get("price_paid", 0.0) or 0.0),
            "payment": row.get("payment_method", ""),
            "created": row.get("created_at", ""),
        }
