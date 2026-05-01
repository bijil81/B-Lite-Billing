# Inventory/Grocery Phase G1 Manual Test Checklist

Date: 2026-04-30

## Scope

Phase G1 is pure domain helper code only.

Added:
- `src/blite_v6/inventory_grocery/product_units.py`
- `src/blite_v6/inventory_grocery/product_validation.py`

No UI wiring was added.
No database migration was added.
No billing total, stock deduction, print, PDF, WhatsApp, or report logic was changed.

## Automated Gate

Passed:
- `python -m py_compile src\blite_v6\inventory_grocery\product_units.py src\blite_v6\inventory_grocery\product_validation.py`
- `python -m pytest -q tests\test_inventory_grocery_product_units.py tests\test_inventory_grocery_product_validation.py`
- Result: 10 passed.
- Compatibility smoke:
  - `python -m pytest -q tests\test_inventory_grocery_product_units.py tests\test_inventory_grocery_product_validation.py tests\test_billing_cart_operations.py tests\test_billing_product_unit_metadata.py tests\test_inventory_loose_quantity.py tests\test_loose_quantity_printing.py tests\test_schema_constraint_migration.py`
  - Result: 28 passed.
- Full source test folder:
  - `python -m pytest -q tests`
  - Result: 289 passed.

## Manual Smoke

Because G1 has no visible UI change, manual smoke should confirm existing behavior only:

- Run `main.py`.
- Open Billing.
- Add a normal service bill.
- Add a normal packet product bill.
- Confirm quantity, total, Save/PDF/Print/WhatsApp behavior is unchanged.
- Open Inventory.
- Confirm existing Add/Edit item dialog opens.
- Confirm no new grocery fields are visible yet.
- Open Settings and confirm license still shows activated.

Manual result:
- Passed by user screenshot review on 2026-04-30.
- Billing service flow opened and saved/PDF/print fallback behaved as expected.
- Billing product flow with discount/GST/points showed expected total and saved/PDF path.
- WhatsApp manual send flow opened in browser and message content was visible.
- Inventory list, Add Item dialog, and context menu opened.
- Licensing showed Activated/Lifetime.
- No unexpected G1 grocery UI fields appeared.

## Pass Condition

- App opens normally.
- Existing salon/spa billing still works.
- Existing inventory screen opens.
- No new visible controls appear from G1.

Status: passed.

## Next Phase

Phase G2 should be additive schema extension only if we are ready to touch database shape.
If we want visible Inventory UI fields first, split it into a new safe phase after a schema review.
