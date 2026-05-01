# Inventory/Grocery Phase G5 Manual Test Checklist

Date: 2026-04-30

## Scope

G5 adds the backend purchase/vendor foundation and a first-pass Inventory purchase-entry popup. The first UI pass records one stock item per purchase bill; multi-line purchase bills and reversal/delete are still deferred.

## Source Smoke

1. Run `main.py`.
2. Open Inventory and confirm existing stock grid loads.
3. Select an item and click `Purchase Bill`.
4. Confirm the popup opens without needing manual resize and the Save/Cancel footer is visible.
5. Confirm mouse-wheel scroll works over entry fields, vendor/item comboboxes, and notes.
6. Choose an existing vendor or type a new vendor.
7. Enter purchase invoice number/date, qty, cost price, sale price, MRP, GST, batch, and expiry if available.
8. Save purchase and confirm a success message with gross/GST/net totals.
9. Confirm Inventory stock increased by the purchased quantity.
10. Open Billing -> Products and confirm G3/G4 product search still works.
11. Add an existing loose item to a bill and confirm decimal quantity still calculates correctly.

## Backend Expectations

- Vendor save/upsert supports name, phone, GSTIN, address, opening balance, active.
- Duplicate vendor name updates the existing vendor instead of creating a duplicate.
- Purchase invoice save stores vendor, invoice number/date, items, cost, sale price, MRP, GST, batch, expiry.
- Purchase invoice save increases stock through positive movement rows.
- Matching legacy inventory rows and v5 product variants stay in sync for stock quantity.

## Deferred Manual Smoke

- Multi-line purchase bill entry.
- Purchase invoice edit/reversal.
- Vendor payable/balance reporting.
