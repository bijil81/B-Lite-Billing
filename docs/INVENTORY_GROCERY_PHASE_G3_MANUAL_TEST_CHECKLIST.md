# Inventory/Grocery Phase G3 Manual Test Checklist

Date: 2026-04-30
Project: B-Lite management_Billing_V6.0

## Purpose

Verify the Inventory Product Master UI changes without disturbing the existing salon/spa billing workflow.

## Source Smoke

1. Run `python main.py`.
2. Open `Inventory`.
3. Click `Add Item`.
4. Confirm the window opens centered and is usable.
5. Confirm these fields are visible:
   - Category
   - Brand
   - Base Product
   - Item Name
   - Bill Label
   - SKU
   - MRP
   - GST Rate
   - HSN/SAC
   - Unit
   - Sale Unit / Price Basis
   - Base Unit
   - Quantity
   - Min Stock Alert
   - Cost per Unit
   - Sale Price
   - Barcode
   - Price includes tax
   - Allow decimal quantity
   - Weighed / loose item

## Packet Product

1. Add a normal packet product:
   - Category: `Grocery`
   - Item Name: `Test Rice Packet 1kg`
   - Unit: `pcs`
   - Quantity: `10`
   - Cost: `55`
   - Sale Price: `62`
   - MRP: `65`
   - GST Rate: `5`
   - HSN/SAC: `1006`
2. Save.
3. Confirm it appears in Inventory.
4. Open it again using Edit.
5. Confirm sale price, barcode/SKU, GST, and MRP are preserved.

## Loose Product

1. Add a loose product:
   - Category: `Vegetables`
   - Item Name: `Test Tomato Loose`
   - Unit: `kg`
   - Quantity: `10.5`
   - Min Stock Alert: `2.5`
   - Cost: `32.25`
   - Sale Price: `45.50`
2. Confirm decimal quantity and weighed/loose flags are enabled.
3. Save.
4. Confirm Inventory grid shows decimal stock cleanly.

## New Category

1. Add item with a new typed category that is not already in the list.
2. Save.
3. Reopen Add Item and confirm the category is available from the category dropdown/list.

## Dialog Fit And Scroll

1. Open `Inventory` -> `Add Item`.
2. Confirm the Save/Cancel footer is visible without manually resizing the window.
3. Use mouse-wheel scrolling while the pointer is over text fields and combo boxes.
4. Confirm the form scrolls and lower fields remain reachable.
5. Resize the dialog smaller and larger; confirm the footer stays visible.

## Billing Catalog Bridge

Restart the source app or leave and reopen the Billing page before this check, so the
product category/search cache reloads from the latest Inventory save.

1. Add or edit an inventory-only grocery item such as `Test Rice Packet 1kg`.
2. Add or edit an inventory-only loose item such as `Test Tomato Loose`.
3. Open `Billing` -> `Products`.
4. Confirm the new categories, for example `Grocery` and `Vegetables`, appear in the category selector.
5. Search `rice` and confirm `Test Rice Packet 1kg` appears.
6. Search `toma` and confirm `Test Tomato Loose` appears.
7. Select the item and confirm price/unit metadata loads before adding to bill.
8. Confirm inventory-only items still appear when the v5 product-variant SQLite switch is off.

## Below-Cost Warning

1. Add item with Cost `100` and Sale Price `80`.
2. Confirm below-cost warning appears.
3. Click `No` first and confirm item is not saved.
4. Repeat and click `Yes`; confirm item saves.

## Duplicate Barcode

1. Edit or add another item using an already existing barcode.
2. Confirm duplicate barcode warning appears.
3. Click `No`; confirm item is not saved with duplicate barcode.

## Billing Compatibility

1. Open Billing.
2. Add an existing service bill and confirm no behavior changed.
3. Switch to Products.
4. Add packet product and confirm price/quantity flow works.
5. Add the new product and confirm bill preview updates.
6. Save and PDF one bill.
7. WhatsApp can remain manual if driver/session is not ready.

## Pass Rule

Pass G3 only if:
- Add/Edit Inventory works.
- Existing product list loads.
- Existing billing service/product paths still work.
- Below-cost warning requires explicit continue.
- No crash occurs while saving or editing product master fields.

Source verification already completed:
- Focused G3 tests on 2026-04-30: 24 passed.
- Compile check on changed G3 modules passed.
- Earlier compatibility/full test gates remain recorded in the phase reports; rerun full gate before final release build.
