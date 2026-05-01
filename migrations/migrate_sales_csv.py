"""Legacy sales_report.csv -> v5 invoices migration."""

from __future__ import annotations

import csv
import os

from db_core.schema_manager import ensure_v5_schema
from repositories.billing_repo import BillingRepository
from utils import F_REPORT


def migrate_sales_csv(dry_run: bool = True) -> dict:
    ensure_v5_schema()
    if not os.path.exists(F_REPORT):
        return {"source_count": 0, "migrated": [], "skipped": [], "dry_run": dry_run}
    repo = BillingRepository()
    migrated = []
    skipped = []
    with open(F_REPORT, 'r', encoding='utf-8') as handle:
        reader = csv.reader(handle)
        header = next(reader, None)
        total_idx = 5 if header and len(header) >= 6 else 3
        invoice_idx = 1 if header and len(header) >= 2 else 0
        customer_idx = 2 if header and len(header) >= 3 else 0
        for row in reader:
            if not row:
                continue
            raw_date = row[0][:10]
            invoice_no = row[invoice_idx] if len(row) > invoice_idx else f"CSV-{len(migrated) + len(skipped) + 1}"
            customer_name = row[customer_idx] if len(row) > customer_idx else ""
            net_total = float(row[total_idx] or 0) if len(row) > total_idx else 0.0
            if not dry_run and repo.get_invoice_by_no(invoice_no):
                skipped.append(invoice_no)
                continue
            migrated.append(invoice_no)
            if not dry_run:
                from db_core.transaction import transaction_scope
                with transaction_scope() as conn:
                    invoice_id = repo.create_invoice(conn, {
                        "invoice_no": invoice_no,
                        "invoice_date": raw_date,
                        "customer_phone": "",
                        "customer_name": customer_name,
                        "gross_total": net_total,
                        "discount_total": 0.0,
                        "tax_total": 0.0,
                        "net_total": net_total,
                        "loyalty_earned": 0,
                        "loyalty_redeemed": 0,
                        "redeem_code": "",
                        "notes": "Imported from legacy sales_report.csv",
                        "created_by": "migration",
                    })
                    repo.add_invoice_item(conn, invoice_id, {
                        "item_name": "Legacy CSV Sale",
                        "item_type": "service",
                        "staff_name": "",
                        "qty": 1,
                        "unit_price": net_total,
                        "line_total": net_total,
                        "discount_amount": 0.0,
                        "inventory_item_name": "",
                    })
                    repo.add_payment(conn, invoice_id, {
                        "payment_method": "Legacy",
                        "amount": net_total,
                        "reference_no": "sales_report.csv",
                    })
    return {
        "source_count": len(migrated) + len(skipped),
        "migrated": migrated,
        "skipped": skipped,
        "dry_run": dry_run,
    }
