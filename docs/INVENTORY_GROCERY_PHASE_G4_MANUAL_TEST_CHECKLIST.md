# Inventory/Grocery Phase G4 Manual Test Checklist

Date: 2026-04-30
Project: B-Lite management_Billing_V6.0

## Purpose

Verify loose-unit product billing after the G3 inventory product master and billing catalog bridge changes.

## Source Smoke

1. Run `python main.py`.
2. Open `Billing`.
3. Switch to `Products`.
4. Confirm existing salon/product billing still opens normally.
5. Open `Inventory` if needed and confirm the G3 test products exist:
   - `Test Rice Packet 1kg`
   - `Test Tomato Loose`

## Packet Product Billing

1. Select or search `Test Rice Packet 1kg`.
2. Confirm the quantity label shows pieces/packets, not kg.
3. Enter quantity `2`.
4. Add item to bill.
5. Confirm preview amount is `sale price x 2`.
6. Save only on a test bill/customer.

## Loose Kg Product Billing

1. Select or search `Test Tomato Loose`.
2. Confirm the quantity label/unit hint shows `kg`.
3. Enter quantity `1.24`.
4. Add item to bill.
5. Confirm preview shows a readable quantity such as `1.24 kg`.
6. Confirm amount is `sale price per kg x 1.24`.

## Converted Gram Input

1. Select `Test Tomato Loose` again.
2. Enter quantity `1240g`.
3. Add item to bill.
4. Confirm it merges with, or displays equivalent to, `1.24 kg`.
5. Confirm amount is the same as the `1.24` kg entry.

## Edit Quantity

1. Double-click bill preview or use the edit bill item action.
2. Select the loose item.
3. Change quantity to `500g`.
4. Confirm the bill updates to `0.5 kg`.
5. Confirm packet product quantity editing still works as before.

## Save, Print, PDF, WhatsApp

1. Save the test bill.
2. Confirm inventory stock deducts decimal quantity from the loose item.
3. Generate PDF.
4. Use print fallback if no printer is installed.
5. Trigger WhatsApp/manual send if configured.
6. Confirm product lines keep unit-aware quantity labels in bill output.

## Pass Rule

Pass G4 only if:
- Loose kg/g and L/ml quantity inputs convert correctly.
- Packet products remain simple quantity products.
- Stock deduction preserves decimal quantities.
- Preview, print, PDF, and WhatsApp bill data show clean unit labels.
- Existing salon service billing is unchanged.

Source verification already completed:
- Focused G3/G4 gate on 2026-04-30: 39 passed.
- Compile check passed for billing, inventory, print, and catalog bridge modules.
