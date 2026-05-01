"""Legacy memberships and package templates -> v5 memberships migration."""

from __future__ import annotations

from membership import get_memberships, get_pkg_templates
from repositories.memberships_repo import MembershipsRepository


def migrate_memberships(dry_run: bool = True) -> dict:
    repo = MembershipsRepository()
    templates = get_pkg_templates()
    memberships = get_memberships()
    plan_names = []
    member_phones = []
    for template in templates:
        plan_names.append(template.get("name", ""))
        if not dry_run:
            repo.upsert_plan({
                "plan_name": template.get("name", ""),
                "duration_days": template.get("duration_days", 0),
                "discount_pct": template.get("discount_pct", 0.0),
                "wallet_amount": template.get("wallet", 0.0),
                "price": template.get("price", 0.0),
                "description": template.get("description", ""),
                "active": True,
            })
    for phone, membership in memberships.items():
        member_phones.append(phone)
        if not dry_run:
            repo.upsert_customer_membership({
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
            })
            repo.add_transaction({
                "customer_phone": phone,
                "txn_type": "migration_seed",
                "amount": membership.get("price_paid", 0.0),
                "note": "Imported legacy membership",
                "reference_id": membership.get("created", ""),
            })
    return {
        "plan_count": len(plan_names),
        "membership_count": len(member_phones),
        "plans": plan_names,
        "memberships": member_phones,
        "dry_run": dry_run,
    }
