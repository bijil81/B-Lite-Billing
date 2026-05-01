# Inventory/Grocery Phase G2 Manual Test Checklist

Date: 2026-04-30

## Scope

Phase G2 is a database schema foundation only.

No visible billing or inventory UI behavior is expected to change in this phase.

## Source Smoke

Run `main.py`, then check:

- App opens without license/startup crash.
- Billing page opens.
- Inventory page opens.
- Inventory Add Item dialog opens and closes.
- Existing stock grid rows still show quantity, unit, cost, and value.
- Settings > Licensing still shows Activated/Lifetime on an activated machine.
- Billing service bill Save/PDF still works.
- Billing product bill Save/PDF still works.

## Developer Schema Smoke

Run these from the V6 project folder:

```powershell
python -m pytest -q tests\test_inventory_grocery_schema_migration.py tests\test_schema_constraint_migration.py
python -m pytest -q tests
```

Expected:

- G2 dry-run reports missing grocery columns/tables without altering the DB.
- G2 apply creates a DB backup before ALTER/CREATE.
- Existing rows keep sale price, cost price, and stock values.
- Invalid negative financial/stock rows are reported, not silently fixed.
- Constraint rebuild preserves new grocery columns.

## Important Notes

- Existing production DB migration is not auto-applied by UI in this phase.
- Future Inventory/Grocery phases can call the dry-run first, show the report, then apply only after backup confirmation.
- Do not delete wrapper files after this phase.
