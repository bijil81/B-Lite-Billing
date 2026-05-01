# Inventory/Grocery Phase G6 Manual Test Checklist

Date: 2026-04-30

## Scope

G6C adds preview-first product import apply.

Supported:
- Choose CSV, XLSX, or JSON.
- Review/adjust column mapping.
- Preview create/update/skip/error rows.
- Import valid create/update rows.
- Save inventory.
- Sync billing product catalog.
- Write import batch log.

## Source Smoke

1. Run `main.py`.
2. Open Inventory.
3. Click `Import`.
4. Choose a `.csv`, `.xlsx`, or `.json` product file. A ready sample exists at `docs/manual_test_samples/g6c_product_import_sample.csv`.
5. Confirm the file path appears.
6. Confirm required mappings are auto-filled when headers are recognizable:
   - Product Name
   - Category
   - Sale Price
7. Adjust mapping dropdowns manually if needed.
8. Click `Preview`.
9. Confirm preview grid shows row number, action, item, category, price, and issues.
10. Confirm duplicate barcode/SKU rows show errors.
11. Confirm below-cost rows show warning or error depending on policy.
12. Click `Import Valid Rows`.
13. Confirm success summary shows created/updated/skipped/error counts and a batch id.
14. Confirm imported products appear in Inventory grid with stock, category, unit, cost, sale price, GST, and barcode/SKU where supplied.
15. Open Billing -> Products.
16. Confirm imported product category appears.
17. Search imported item by name and barcode/SKU.
18. Add imported item to bill.
19. Confirm price/unit metadata loads and live preview updates.
20. Restart source app and confirm imported products still appear in Inventory and Billing search.

## Duplicate/Update Smoke

1. Import a row with a barcode/SKU that already exists.
2. Set Existing Items to `skip`; preview should show skip and import should not change the item.
3. Set Existing Items to `update`; preview should show update and import should update the existing item.
4. Set Existing Items to `error`; preview should show error and import should skip that row.

## Deferred

- Undo imported batch.
- Import batch log viewer/restore UI.
