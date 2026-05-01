"""v5 migration entry helpers and CLI runner."""

from __future__ import annotations

import argparse
import json

from db_core.schema_manager import ensure_v5_schema
from migration_state import mark_migration_completed
from migrations.migrate_appointments import migrate_appointments
from migrations.migrate_customers import migrate_customers
from migrations.migrate_expenses import migrate_expenses
from migrations.migrate_inventory import migrate_inventory
from migrations.migrate_memberships import migrate_memberships
from migrations.migrate_offers import migrate_offers
from migrations.migrate_product_variants import migrate_product_variants
from migrations.migrate_sales_csv import migrate_sales_csv
from migrations.migrate_staff import migrate_staff
from migrations.migrate_users import migrate_users
from migrations.migration_validate import validate_all


MIGRATION_STEPS = [
    ("users", migrate_users),
    ("customers", migrate_customers),
    ("staff", migrate_staff),
    ("appointments", migrate_appointments),
    ("inventory", migrate_inventory),
    ("product_variants", migrate_product_variants),
    ("expenses", migrate_expenses),
    ("sales_csv", migrate_sales_csv),
    ("memberships", migrate_memberships),
    ("offers", migrate_offers),
]


def bootstrap_v5_foundation() -> dict:
    ensure_v5_schema()
    return {
        "ok": True,
        "message": "v5 relational foundation ready"
    }


def run_foundation_dry_run() -> dict:
    ensure_v5_schema()
    results = {}
    for name, fn in MIGRATION_STEPS:
        results[name] = fn(dry_run=True)
    return {"ok": True, "results": results}


def run_all_migrations(dry_run: bool = True) -> dict:
    ensure_v5_schema()
    results = {}
    for name, fn in MIGRATION_STEPS:
        results[name] = fn(dry_run=dry_run)
    return {
        "ok": True,
        "dry_run": dry_run,
        "results": results,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run v5 relational migration steps.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Run actual migration writes. Default is dry-run.",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Run validation after migration/dry-run summary.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON only.",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    bootstrap = bootstrap_v5_foundation()
    migration = run_all_migrations(dry_run=not args.apply)
    payload: dict = {
        "bootstrap": bootstrap,
        "migration": migration,
    }
    if args.validate:
        payload["validation"] = validate_all()
        if args.apply:
            all_ok = all(bool(result.get("counts_match", False)) for result in payload["validation"].values())
            payload["migration"]["migration_completed_marked"] = mark_migration_completed() if all_ok else False
    elif args.apply:
        payload["migration"]["migration_completed_marked"] = False

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    print("=== v5 Migration Runner ===")
    print(bootstrap.get("message", ""))
    print(f"Mode: {'APPLY' if args.apply else 'DRY RUN'}")
    print()
    for name, result in migration.get("results", {}).items():
        source_count = result.get("source_count")
        migrated_count = len(result.get("migrated", [])) if isinstance(result.get("migrated"), list) else None
        line = f"- {name}:"
        if source_count is not None:
            line += f" source={source_count}"
        if migrated_count is not None:
            line += f" migrated={migrated_count}"
        extras = []
        for key in (
            "attendance_rows",
            "visit_rows",
            "loyalty_seed_rows",
            "plan_count",
            "membership_count",
            "offer_count",
            "code_count",
        ):
            if key in result:
                extras.append(f"{key}={result[key]}")
        if extras:
            line += " " + " ".join(extras)
        print(line)

    if args.validate:
        print()
        print("=== Validation ===")
        for name, result in payload["validation"].items():
            counts_match = result.get("counts_match")
            print(f"- {name}: counts_match={counts_match} details={result}")
        if args.apply:
            print()
            print(f"Migration Completed Marked: {payload['migration'].get('migration_completed_marked', False)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
