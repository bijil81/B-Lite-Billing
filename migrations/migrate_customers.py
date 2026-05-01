"""Legacy customers -> v5_customers migration."""

from __future__ import annotations

from repositories.customers_repo import CustomersRepository
from utils import F_CUSTOMERS, load_json


def migrate_customers(dry_run: bool = True) -> dict:
    customers = load_json(F_CUSTOMERS, {})
    repo = CustomersRepository()
    migrated = []
    visit_rows = 0
    loyalty_rows = 0
    for phone, customer in customers.items():
        visits = customer.get("visits", []) or []
        visit_rows += len(visits)
        loyalty_rows += (1 if int(customer.get("points", 0) or 0) else 0)
        row = {
            "phone": phone,
            "name": customer.get("name", ""),
            "birthday": customer.get("birthday", ""),
            "vip": bool(customer.get("vip", False)),
            "points_balance": int(customer.get("points", 0) or 0),
        }
        if not dry_run:
            repo.upsert_legacy_customer(**row)
        migrated.append(phone)
    return {
        "source_count": len(customers),
        "migrated": migrated,
        "visit_rows": visit_rows,
        "loyalty_seed_rows": loyalty_rows,
        "dry_run": dry_run,
    }
