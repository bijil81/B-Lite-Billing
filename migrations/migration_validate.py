"""Validation helpers for additive v5 migrations."""

from __future__ import annotations

import csv
import os

from appointments import get_appointments
from auth import get_users
from expenses import get_expenses
from inventory import get_inventory
from membership import get_memberships, get_pkg_templates
from offers import get_offers
from redeem_codes import get_codes
from repositories.appointments_repo import AppointmentsRepository
from repositories.billing_repo import BillingRepository
from repositories.customers_repo import CustomersRepository
from repositories.inventory_repo import InventoryRepository
from repositories.memberships_repo import MembershipsRepository
from repositories.offers_repo import OffersRepository
from repositories.product_variants_repo import ProductVariantsRepository
from repositories.staff_repo import StaffRepository
from repositories.users_repo import UsersRepository
from staff import get_staff
from utils import F_CUSTOMERS, F_REPORT, load_json


def validate_users_migration() -> dict:
    source = get_users()
    target = UsersRepository().list_all()
    return {"source_count": len(source), "target_count": len(target), "counts_match": len(source) == len(target)}


def validate_customers_migration() -> dict:
    source = load_json(F_CUSTOMERS, {})
    target = CustomersRepository().list_all()
    target_phones = {str(row.get("legacy_phone", "")).strip() for row in target}
    missing = sorted(phone for phone in source.keys() if str(phone).strip() not in target_phones)
    return {
        "source_count": len(source),
        "target_count": len(target),
        "missing_phones": missing,
        "counts_match": len(missing) == 0,
    }


def validate_staff_migration() -> dict:
    source = get_staff()
    target = StaffRepository().list_all()
    return {"source_count": len(source), "target_count": len(target), "counts_match": len(source) == len(target)}


def validate_appointments_migration() -> dict:
    source = get_appointments()
    target = AppointmentsRepository().list_all()
    return {"source_count": len(source), "target_count": len(target), "counts_match": len(source) == len(target)}


def validate_inventory_migration() -> dict:
    source = get_inventory()
    target = InventoryRepository().list_items()
    return {"source_count": len(source), "target_count": len(target), "counts_match": len(source) == len(target)}


def validate_product_variants_migration() -> dict:
    source = get_inventory()
    target = ProductVariantsRepository().list_all(active_only=False)
    target_labels = {
        str(row.get("bill_label", "")).strip() or str(row.get("display_name", "")).strip()
        for row in target
    }
    missing = sorted(name for name in source.keys() if str(name).strip() not in target_labels)
    return {
        "source_count": len(source),
        "target_count": len(target),
        "missing_items": missing,
        "counts_match": len(missing) == 0,
    }


def validate_expenses_migration() -> dict:
    source = get_expenses()
    from db_core.connection import connection_scope
    from db_core.schema_manager import ensure_v5_schema
    ensure_v5_schema()
    matched = 0
    with connection_scope() as conn:
        for expense in source:
            row = conn.execute(
                """
                SELECT id FROM v5_expenses
                WHERE expense_date = ? AND category = ? AND staff_name = ?
                  AND description = ? AND amount = ? AND payment_method = ?
                LIMIT 1
                """,
                (
                    expense.get("date", ""),
                    expense.get("category", ""),
                    expense.get("staff", ""),
                    expense.get("description", ""),
                    float(expense.get("amount", 0.0) or 0.0),
                    expense.get("payment", expense.get("payment_method", "")),
                ),
            ).fetchone()
            if row:
                matched += 1
    return {"source_count": len(source), "matched_count": matched, "counts_match": len(source) == matched}


def validate_memberships_migration() -> dict:
    source_plans = get_pkg_templates()
    source_memberships = get_memberships()
    repo = MembershipsRepository()
    target_plans = repo.list_plans()
    target_memberships = repo.list_customer_memberships()
    return {
        "plan_source_count": len(source_plans),
        "plan_target_count": len(target_plans),
        "membership_source_count": len(source_memberships),
        "membership_target_count": len(target_memberships),
        "counts_match": len(source_memberships) == len(target_memberships),
    }


def validate_offers_migration() -> dict:
    offer_count = len(get_offers())
    code_count = len(get_codes())
    repo = OffersRepository()
    target_offers = repo.list_offers()
    return {
        "offer_source_count": offer_count,
        "offer_target_count": len(target_offers),
        "code_source_count": code_count,
        "counts_match": offer_count == len(target_offers),
    }


def validate_sales_csv_migration() -> dict:
    source_invoice_nos: set[str] = set()
    if os.path.exists(F_REPORT):
        with open(F_REPORT, 'r', encoding='utf-8') as handle:
            reader = csv.reader(handle)
            header = next(reader, None)
            invoice_idx = 1 if header and len(header) >= 2 else 0
            for row in reader:
                if not row:
                    continue
                invoice_no = row[invoice_idx] if len(row) > invoice_idx else ""
                if invoice_no:
                    source_invoice_nos.add(invoice_no)
    target_invoice_nos = {
        str(row.get("invoice_no", "")).strip()
        for row in BillingRepository().list_invoices()
        if str(row.get("invoice_no", "")).strip()
    }
    missing = sorted(no for no in source_invoice_nos if no and no not in target_invoice_nos)
    return {
        "source_unique_count": len(source_invoice_nos),
        "target_imported_count": len(target_invoice_nos),
        "missing_invoice_nos": missing,
        "counts_match": len(missing) == 0,
    }


def validate_all() -> dict:
    return {
        "users": validate_users_migration(),
        "customers": validate_customers_migration(),
        "staff": validate_staff_migration(),
        "appointments": validate_appointments_migration(),
        "inventory": validate_inventory_migration(),
        "product_variants": validate_product_variants_migration(),
        "expenses": validate_expenses_migration(),
        "memberships": validate_memberships_migration(),
        "offers": validate_offers_migration(),
        "sales_csv": validate_sales_csv_migration(),
    }
