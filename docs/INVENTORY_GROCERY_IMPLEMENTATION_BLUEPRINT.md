# Inventory / Grocery Implementation Blueprint

Date: 2026-04-30
Project: B-Lite management_Billing_V6.0

## Goal

Add supermarket, grocery, and universal retail support without destabilizing the current salon/spa billing flow.

Primary target:
- Product master supports packet items and loose-unit items.
- Billing supports decimal/converted quantity such as `1.24 kg` or `1240g`.
- Inventory supports cost price, sale price, stock quantity, reorder level, item GST, HSN/SAC, barcode/SKU, and clean bulk import.
- Future purchase/vendor workflows can update stock and cost safely.

Non-goal for the first implementation pass:
- Do not rewrite the whole app.
- Do not delete the current large wrapper files.
- Do not silently change existing customer/product/sales data.
- Do not force grocery UI on salon-only users.

## Current State

Already present:
- Billing unit visibility helper has been added for products.
- Loose quantity billing, parser, stock deduction, and printing tests exist.
- V5 product variant SQLite foundation exists.
- Inventory has category, brand, base product, item name, bill label, unit, pack size, stock, reorder level, cost, sale price preservation, and barcode.
- Inventory add/edit dialog exposes sale price, MRP, GST rate, HSN/SAC, SKU, sale/base unit, tax-inclusive, decimal quantity, and weighed/loose controls.
- Inventory-only products are bridged into Billing product categories/search without overwriting legacy products.
- Product variant constraints exist for non-negative sale price, cost price, stock quantity, and reorder level.

Important gaps:
- Category is still mostly row-derived, not a true category master workflow.
- No full vendor master.
- No purchase invoice module.
- No item-wise GST calculation in billing; billing still uses one global GST rate.
- Bulk import exists in limited form, but not as a safe clean-install import wizard with preview and row validation.
- Below-cost sale warning is not applied everywhere.

## Split Closure Decision

The previous broad split work can be treated as **functionally complete**, but not as a reason to delete wrapper files.

Keep these top-level files as compatibility wrappers until full manual smoke is passed from source and installed EXE:
- `billing.py`
- `main.py`
- `reports.py`
- `salon_settings.py`

Do not delete them. Current callers and app entry points still import them.

Shrink strategy:
- No more broad shrink before grocery work.
- Only remove dead/unreachable code when a focused test/manual smoke proves the replacement path.
- New grocery/retail logic must live in new focused modules under `src/blite_v6/inventory_grocery/`.
- Existing large files may receive only small wiring edits, imports, or compatibility calls.

## Feature Flags

Recommended new settings:
- `retail_grocery_enabled`: false by default for salon/spa safety.
- `show_product_unit_controls`: true when product billing is enabled, but advanced grocery hints can follow `retail_grocery_enabled`.
- `product_wise_gst_enabled`: false until Phase G7 is complete.
- `gst_rate_source`: `global` for salon/service mode, `item` for retail mode, `hybrid` for mixed mode.
- `missing_item_gst_policy`: default to global GST rate, with an optional warning in retail mode when product GST is blank.
- `below_cost_warning_enabled`: true once Phase G8 is complete.
- `ship_sample_catalog`: true for demo builds, false for clean production installs when desired.

## Phase Plan

### Phase G0 - Safety Baseline and Close Split Gate

Status: completed.

Scope:
- Record current split status.
- Confirm wrappers are retained.
- Run focused tests for billing unit visibility, loose quantity, reports, settings licensing display, and startup if available.
- Update QA blueprint with grocery phase order.

Acceptance:
- No behavior change.
- Existing app opens from source.
- Existing EXE license status remains valid after reopen.
- Blueprint is documented.

### Phase G1 - Pure Product/Unit Domain Helpers

Status: completed in source and manual smoke passed on 2026-04-30.

Scope:
- Add new module: `src/blite_v6/inventory_grocery/product_units.py`.
- Add new module: `src/blite_v6/inventory_grocery/product_validation.py`.
- Define supported units: `pcs`, `kg`, `g`, `L`, `ml`, `meter`, `custom`.
- Define price basis conversion:
  - per `kg`: accepts kg or g input.
  - per `L`: accepts L or ml input.
  - per `pcs`: integer/decimal policy is explicit.
- Validate:
  - non-negative sale price, cost price, stock, reorder.
  - sale price below cost warning payload, not silent rewrite.
  - GST rate range.
  - barcode/SKU normalization.

Risk:
- Low, because this phase is pure helper logic only.

Tests:
- Unit conversion.
- Decimal quantity parsing.
- Invalid price/stock/GST rejection.
- Sale below cost returns a warning decision object.

Implemented:
- `src/blite_v6/inventory_grocery/product_units.py`
- `src/blite_v6/inventory_grocery/product_validation.py`
- `tests/test_inventory_grocery_product_units.py`
- `tests/test_inventory_grocery_product_validation.py`

Verification:
- `python -m py_compile src\blite_v6\inventory_grocery\product_units.py src\blite_v6\inventory_grocery\product_validation.py`
- `python -m pytest -q tests\test_inventory_grocery_product_units.py tests\test_inventory_grocery_product_validation.py`
- Result: 10 passed.
- Compatibility smoke:
  - `python -m pytest -q tests\test_inventory_grocery_product_units.py tests\test_inventory_grocery_product_validation.py tests\test_billing_cart_operations.py tests\test_billing_product_unit_metadata.py tests\test_inventory_loose_quantity.py tests\test_loose_quantity_printing.py tests\test_schema_constraint_migration.py`
  - Result: 28 passed.
- Full source test folder:
  - `python -m pytest -q tests`
  - Result: 289 passed.
- Manual smoke:
  - Passed by user screenshot review.
  - Existing Billing, Inventory, Licensing, PDF/print fallback, and WhatsApp manual flow remained usable.

### Phase G2 - Additive SQLite Schema Extension

Status: completed in source on 2026-04-30.

Scope:
- Extend product variant metadata without data loss.
- Add dry-run and backup-first migration for any new columns/tables.
- Candidate new fields:
  - `gst_rate`
  - `hsn_sac`
  - `mrp`
  - `price_basis`
  - `tax_inclusive`
  - `default_vendor_id`
  - `expiry_tracking_enabled`
- Candidate new tables:
  - `v5_vendors`
  - `v5_purchase_invoices`
  - `v5_purchase_invoice_items`

Rules:
- Additive migration only.
- Existing rows get safe defaults.
- Do not auto-run production data migration until a staging dry-run passes.
- Do not silently fix invalid stock/financial data.

Risk:
- Medium, because it touches database schema.

Tests:
- Fresh DB creates new schema.
- Existing DB dry-run reports actions.
- Backup-first apply creates a backup.
- Invalid existing data is reported clearly and is not rewritten by this additive migration.

Implemented:
- `src/blite_v6/inventory_grocery/schema_migration.py`
- Additive fields on `v5_product_variants`:
  - `sale_unit`
  - `base_unit`
  - `unit_multiplier`
  - `allow_decimal_qty`
  - `mrp`
  - `gst_rate`
  - `cess_rate`
  - `hsn_sac`
  - `price_includes_tax`
  - `is_weighed`
- Additive fields on `v5_product_variant_movements`:
  - `qty_unit`
  - `unit_cost`
  - `supplier_name`
  - `purchase_ref`
  - `batch_no`
  - `expiry_date`
- Additive tables:
  - `v5_vendors`
  - `v5_purchase_invoices`
  - `v5_purchase_invoice_items`

Safety notes:
- Existing DB apply is backup-first.
- Dry-run does not alter schema.
- Existing sale price, cost price, stock, and reorder values are not rewritten.
- Invalid negative financial/stock rows are reported as warnings and left untouched by this additive migration.
- Existing CHECK-constraint rebuild now preserves grocery columns.

Verification:
- `python -m py_compile src\blite_v6\inventory_grocery\schema_migration.py db_core\constraint_migration.py`
- `python -m pytest -q tests\test_inventory_grocery_schema_migration.py tests\test_schema_constraint_migration.py`
- Result: 9 passed.

Manual checklist:
- `docs/INVENTORY_GROCERY_PHASE_G2_MANUAL_TEST_CHECKLIST.md`

### Phase G3 - Inventory Product Master UI

Status: completed in source on 2026-04-30; manual smoke pending when user is ready.

Scope:
- Keep `InventoryFrame` as wrapper.
- New UI helper module for product form sections.
- Add visible fields:
  - sale price
  - cost price
  - MRP
  - sell unit
  - price basis
  - GST rate
  - HSN/SAC
  - SKU/barcode
  - opening stock
  - reorder level
- Category combo should allow controlled new category creation.
- Grocery-specific controls show only when `retail_grocery_enabled` is on, or product mode is active.

Rules:
- Existing salon inventory path must still work.
- If sale price is lower than cost price, show warning and require explicit continue.

Risk:
- Medium, because it changes Inventory UI.

Tests:
- Add packet product.
- Add loose product.
- Edit product preserves existing barcode and price.
- Category create path.
- Below-cost warning appears.

Implemented:
- `src/blite_v6/inventory_grocery/product_form.py`
- Inventory Add/Edit dialog now exposes:
  - editable category combo for controlled new category creation
  - SKU
  - sale price
  - MRP
  - GST rate
  - HSN/SAC
  - sale unit / price basis
  - base unit
  - tax-inclusive flag
  - decimal quantity flag
  - weighed/loose item flag
- Existing cost, stock, reorder, barcode, bill label, brand, base product, and pack-size fields remain.
- Product save path now builds a validated grocery-aware payload before writing legacy inventory and v5 product-variant data.
- Sale price below cost shows an explicit warning and requires the user to continue.
- Repository writes optional grocery columns only when the migrated DB has them, so existing DBs do not crash before G2 migration is applied.

Verification:
- `python -m py_compile inventory.py repositories\product_variants_repo.py services_v5\inventory_service.py services_v5\product_catalog_service.py src\blite_v6\inventory_grocery\product_form.py`
- `python -m pytest -q tests\test_inventory_grocery_product_form.py tests\test_inventory_grocery_product_validation.py tests\test_inventory_grocery_schema_migration.py`
- Result: 16 passed.
- Compatibility gate:
  - `python -m pytest -q tests\test_inventory_grocery_product_form.py tests\test_inventory_grocery_product_validation.py tests\test_inventory_grocery_schema_migration.py tests\test_inventory_grocery_product_units.py tests\test_inventory_loose_quantity.py tests\test_billing_product_unit_metadata.py`
  - Result: 23 passed.
- Full source gate:
  - `python -m pytest -q tests`
  - Result: 300 passed.

Manual checklist:
- `docs/INVENTORY_GROCERY_PHASE_G3_MANUAL_TEST_CHECKLIST.md`

### Phase G4 - Billing Quantity/Unit Workflow For Loose Items

Status: completed in source on 2026-04-30; manual smoke pending when user is ready.

Scope:
- Billing product selection reads unit and price basis.
- Quantity entry accepts:
  - `1.24`
  - `1.24kg`
  - `1240g`
  - `500ml`
- Cart stores display quantity and base quantity safely.
- Stock deduction uses base unit consistently.
- Print/PDF/WhatsApp show readable line labels such as `1.24 kg x Rs60/kg`.

Rules:
- Service billing must remain unchanged.
- Packet products must remain simple.
- Decimal math must be deterministic and rounded only at display/money boundaries.

Risk:
- High, because it touches money, stock, and bill output.

Tests:
- Product bill with kg item.
- Product bill with g input converted to kg price.
- Product bill with ml input converted to L price.
- Packet product remains same.
- Save/PDF/Print/WhatsApp line labels.
- Stock deduction decimal precision.

Implemented:
- Product selection stores unit metadata on cart items.
- Quantity parser accepts decimal base units and converted shorthand such as `1240g` and `500ml`.
- Unit-aware quantity labels are used in bill preview, edit quantity, print, PDF, and WhatsApp bill data.
- Decimal stock deduction is preserved for inventory sale deduction.
- Packet/pieces products remain on the existing simple quantity path.

Verification:
- `python -m py_compile billing.py inventory.py print_engine.py print_utils.py adapters\product_catalog_adapter.py src\blite_v6\billing\cart_operations.py src\blite_v6\billing\ui_sections.py src\blite_v6\billing\bill_document.py src\blite_v6\billing\catalog_search.py`
- `python -m pytest -q -p no:cacheprovider tests\test_inventory_billing_bridge.py tests\test_inventory_grocery_product_form.py tests\test_inventory_grocery_product_units.py tests\test_billing_product_unit_metadata.py tests\test_billing_catalog_search.py tests\test_inventory_loose_quantity.py tests\test_loose_quantity_printing.py tests\test_billing_cart_operations.py tests\test_billing_unit_visibility.py`
- Result: 39 passed.

Manual checklist:
- `docs/INVENTORY_GROCERY_PHASE_G4_MANUAL_TEST_CHECKLIST.md`

### Phase G5 - Inventory Purchase/Vendor/Purchase Bill Foundation

Status: backend foundation and first Inventory purchase-entry popup completed in source on 2026-04-30; manual smoke pending.

Scope:
- Add vendor/supplier master in new modules.
- Fields:
  - name
  - phone
  - GSTIN
  - address
  - opening balance
  - active/inactive

Risk:
- Medium.

Tests:
- Add/edit/deactivate vendor.
- Duplicate vendor handling.
- GSTIN optional validation.

Scope:
- Add purchase invoice entry.
- Purchase item fields:
  - vendor
  - purchase invoice no
  - date
  - product/variant
  - qty
  - unit
  - cost
  - MRP
  - sale price
  - item GST rate
  - batch no
  - expiry date optional
- Purchase increases stock through movement records.
- Direct stock correction remains separate.

Risk:
- High, because it introduces accounting-like stock movement.

Tests:
- Purchase increases stock.
- Purchase with decimal qty.
- Purchase below/above existing cost updates according to selected policy.
- Purchase deletion/reversal is explicit and auditable.

Implemented:
- `src/blite_v6/inventory_grocery/purchase_validation.py`
- `src/blite_v6/inventory_grocery/purchase_form.py`
- `repositories/purchase_repo.py`
- `services_v5/purchase_service.py`
- Additive `opening_balance` support for `v5_vendors`.
- Purchase invoice save creates/uses vendor records, stores purchase header/items, increases product variant stock, increases matching legacy inventory stock, and writes positive purchase movement records.
- Inventory screen now has a first-pass `Purchase Bill` popup for a selected/typed item, existing/new vendor, invoice date/no, qty/unit, cost, sale price, MRP, GST, HSN/SAC, batch, expiry, and notes.

Deferred:
- Purchase invoice reversal/delete workflow.
- Vendor balance/payment ledger.
- Multi-line purchase invoice UI. The first UI pass records one stock item per purchase bill.

Verification:
- `python -m py_compile repositories\purchase_repo.py services_v5\purchase_service.py src\blite_v6\inventory_grocery\purchase_validation.py db_core\schema_manager.py src\blite_v6\inventory_grocery\schema_migration.py`
- `python -m pytest -q -p no:cacheprovider tests\test_inventory_purchase_foundation.py tests\test_inventory_grocery_schema_migration.py`
- Result: 10 passed.
- UI wiring follow-up:
  - `python -m py_compile inventory.py src\blite_v6\inventory_grocery\purchase_form.py src\blite_v6\inventory_grocery\purchase_validation.py repositories\purchase_repo.py services_v5\purchase_service.py`
  - `python -m pytest -q -p no:cacheprovider tests\test_inventory_grocery_purchase_form.py tests\test_inventory_purchase_foundation.py tests\test_inventory_grocery_schema_migration.py`
  - Result: 12 passed.

### Phase G6 - Bulk Product Import Wizard

Status: G6A/G6B/G6C completed in source on 2026-04-30; source-mode manual smoke pending.

Scope:
- New module for import parsing and preview.
- Supported formats:
  - Excel `.xlsx`
  - JSON
  - CSV if simple and safe
- Required columns:
  - product name
  - category
  - sale price
- Optional columns:
  - brand
  - variant/pack size
  - unit
  - price basis
  - barcode/SKU
  - cost price
  - MRP
  - opening stock
  - reorder level
  - GST rate
  - HSN/SAC
  - tax inclusive/exclusive

Rules:
- Preview before import.
- Show created, updated, skipped, errored.
- Duplicate barcode/SKU must not be silently overwritten.
- Below-cost rows must be warned, skipped, or explicitly approved.

Risk:
- Medium.

Tests:
- Empty file.
- Valid import into clean DB.
- Duplicate barcode.
- Missing required columns.
- Sale below cost row.

G6A implemented:
- `src/blite_v6/inventory_grocery/product_import.py`
- CSV, JSON, and XLSX row parsing.
- Supplier-style header auto-mapping, including headers discovered across uneven rows.
- Preview-only result model with:
  - `create`
  - `update`
  - `skip`
  - `error`
- Existing item matching by barcode first, then SKU, then exact item name.
- Duplicate barcode/SKU/name detection inside the import file.
- Below-cost handling as warning by default, or error/allow by policy.
- No inventory/catalog writes in G6A.

G6A verification:
- `python -m py_compile src\blite_v6\inventory_grocery\product_import.py`
- `python -m pytest -q -p no:cacheprovider tests\test_inventory_grocery_product_import.py tests\test_inventory_grocery_product_form.py tests\test_inventory_grocery_product_validation.py`
- Result: 19 passed.

G6B implemented:
- Inventory import popup with file picker.
- Supports `.csv`, `.xlsx`, and `.json` selection through the G6A parser.
- Column mapping review for required and common optional fields.
- Existing-item policy selector: skip/update/error.
- Below-cost policy selector: warn/error/allow.
- Preview grid with row number, action, item, category, price, and issue text.
- Manual checklist: `docs/INVENTORY_GROCERY_PHASE_G6_MANUAL_TEST_CHECKLIST.md`

G6B verification:
- `python -m py_compile inventory.py src\blite_v6\inventory_grocery\product_import.py`
- `python -m pytest -q -p no:cacheprovider tests\test_inventory_import_ui_smoke.py tests\test_inventory_grocery_product_import.py tests\test_inventory_grocery_product_form.py tests\test_inventory_grocery_product_validation.py`
- Result: 21 passed.

G6C implemented:
- `src/blite_v6/inventory_grocery/product_import_apply.py`
- Preview-first `Import Valid Rows` action.
- Applies only `create` and `update` rows.
- Leaves `skip` and `error` rows untouched.
- Update rows match existing items by barcode, SKU, or exact name.
- If an update changes the product name, the old inventory key is removed so duplicate rows are not created.
- Inventory is saved once per import batch.
- Product catalog sync runs after inventory save so Billing product search/categories can see imported products.
- Batch log is appended to `inventory_import_batches.json`.
- Dialog refreshes Inventory after import.

G6C verification:
- `python -m py_compile inventory.py src\blite_v6\inventory_grocery\product_import.py src\blite_v6\inventory_grocery\product_import_apply.py src\blite_v6\inventory_grocery\product_import_dialog.py`
- `python -m pytest -q -p no:cacheprovider tests\test_inventory_grocery_product_import_apply.py tests\test_inventory_import_ui_smoke.py tests\test_inventory_grocery_product_import.py`
- Result: 17 passed.

### Phase G7 - Product-wise GST

Scope:
- Add item GST profile to billing without breaking the existing salon/spa GST setting.
- Settings design:
  - Existing `GST Rate %` remains the default/global service GST rate for salon/spa and legacy bills.
  - Add a GST calculation mode instead of replacing the old field:
    - `Global GST`: every taxable item uses Settings GST rate. This is the current salon/spa behavior.
    - `Item-wise GST`: products use Inventory/Product Master GST rate; services use Settings GST rate unless service-specific GST is added later.
    - `Hybrid/Auto`: Retail Store mode defaults products to item-wise GST, Salon/Spa mode defaults to global GST, mixed mode uses item GST when available and falls back to global GST.
  - Add missing-product-GST policy:
    - fallback to global GST rate,
    - fallback to 0%,
    - or warn/block before billing. Recommended default for retail is fallback + warning, not silent 0%.
  - Keep `GST Type` inclusive/exclusive as a bill-level default, but allow each product to respect `price_includes_tax` from Inventory when item-wise GST is enabled.
- Billing GST mode:
  - global GST remains default for existing installs and salon/spa users.
  - item-wise GST is enabled only when feature flag/settings mode allows it.
- Bill data stores item tax rate and tax amount.
- Bill preview, print, PDF, WhatsApp, reports, and exports show tax grouped by GST rate, for example `GST 5%`, `GST 12%`, `GST 18%`, plus total tax.
- Purchase invoice GST should use the same item GST fields so purchase cost and sale billing do not drift.

Risk:
- High, because it affects totals and compliance.

Tests:
- Mixed GST rates in one bill.
- Inclusive item GST.
- Exclusive item GST.
- Retail mode product-wise GST with fallback to Settings GST when item GST is blank.
- Salon/Spa mode keeps current global GST behavior.
- Mixed service + grocery bill uses service/global GST and product/item GST safely.
- Print/PDF/WhatsApp tax summary groups by GST rate.
- Discount base before/after GST according to current business rule.
- Reports totals match billing totals.

### Phase G8 - Below-cost Guard Everywhere

Scope:
- Enforce warning/confirmation in:
  - product master save
  - bulk import
  - purchase entry
  - billing manual price override
- Record override reason in activity log when possible.

Risk:
- Medium.

Tests:
- Warning appears.
- Cancel blocks save/sale.
- Continue saves/sells and records audit note.

### Phase G9 - Dashboard Graphical Interface

Scope:
- Add an optional graphical dashboard preference after core inventory/billing flows are stable.
- Keep existing dashboard behavior available.
- Avoid making dashboard changes part of billing, stock, GST, or purchase phases.

Risk:
- Medium, because it affects the main visible landing area.

Tests:
- Existing dashboard opens.
- New dashboard preference toggles cleanly.
- No startup/navigation regression.

Current status:
- Pending. This is still useful before production handoff, but it should remain optional until the core grocery billing/report flows pass final audit.

### Phase G10 - Reports / Closing / Production Smoke Gate

Current status:
- G10A completed on 2026-05-01:
  - Daily closing PDF now includes grocery/product sales, decimal product quantities, GST total, top services, and top products.
  - Closing summary separates Gross Sales, Total Discount, and Net Revenue.
  - New report aggregation lives in `src/blite_v6/reports/retail_summary.py`.
- G10B in progress/completed in source on 2026-05-01:
  - Reports screen has a `Grocery Reports` tab.
  - Supports quick filters for Today, This Week, This Month, plus custom from/to dates.
  - Shows Gross Sales, Net Revenue, Product Sales, Discount, GST, and Bills cards.
  - Shows product-wise quantity/unit/revenue/cost/margin and GST summary tables.

Scope:
- Software report view for grocery/retail sales.
- Daily closing PDF.
- Weekly/monthly/custom date range report visibility.
- Production readiness audit.
- Source smoke.
- EXE smoke.
- Fresh install with sample catalog on.
- Fresh install with sample catalog off.
- Upgrade install preserves existing data.

Manual checklist:
- App opens and license stays activated.
- Billing service bill.
- Billing packet product bill.
- Billing loose kg/g product bill.
- Barcode product.
- Discount/offer/redeem/points.
- Save/PDF/Print/WhatsApp.
- Inventory add/edit/delete/restore.
- Product import preview/import.
- Vendor add/edit.
- Purchase entry stock increase.
- Reports sales list/export/saved bills/chart.
- Grocery Reports Today/Week/Month.
- Closing Report PDF with service/product/GST sections.

Remaining before production-ready sign-off:
- Full automated gate across billing, inventory, settings, reports, purchase/vendor, import, GST, and licensing tests.
- Source-mode smoke for:
  - service bill,
  - packet product bill,
  - loose decimal product bill,
  - discount below-cost warning,
  - item-wise GST mixed-rate bill,
  - purchase bill/vendor history,
  - import preview/apply,
  - grocery reports day/week/month,
  - closing PDF.
- EXE rebuild/reinstall smoke. Installed EXE will not show source changes until rebuild.
- License activation smoke after rebuild.
- Print/PDF/WhatsApp smoke after rebuild.
- Clean install sample-data policy decision:
  - ship with sample products/services on, or
  - provide clean-install toggle/off mode.
- Dashboard graphical interface remains optional/pending after final core audit.
- Final wrapper-size audit:
  - avoid further growth in `billing.py`, `inventory.py`, `reports.py`, `closing_report.py`, `salon_settings.py`.
  - move any new production logic to focused `src/blite_v6/` modules.
- Final data safety audit:
  - DB migrations additive only,
  - no silent financial rewrite,
  - old salon/spa billing behavior preserved.

## Recommended Implementation Order

1. G0: Baseline and documentation.
2. G1: Pure helpers and tests.
3. G2: Additive schema and dry-run tests.
4. G3: Inventory UI product master.
5. G4: Billing loose quantity integration.
6. G5: Vendor, purchase, and purchase bill foundation.
7. G6: Bulk product import wizard.
8. G7-G8: Product-wise GST and below-cost guard.
9. G9: Optional dashboard graphical interface.
10. G10: Reports/closing integration and manual/EXE smoke.

## Stop Conditions

Pause implementation and do not continue to the next phase if:
- Existing salon billing breaks.
- Existing V6 license activation fails.
- Any migration attempts to rewrite invalid financial/stock data silently.
- Full/source tests cannot be run and the change touches billing totals, stock deduction, or GST.
- Manual smoke finds a crash in Billing, Inventory, Reports, or Settings.

## Shrink Plan for Old Wrapper Files

Do not shrink wrappers during G1-G5 unless a phase naturally extracts logic already being changed.

Safe later shrink target:
- `inventory.py`, because grocery work will touch it.

Avoid for now:
- `billing.py`: keep stable until grocery billing smoke passes.
- `reports.py`: keep stable until item-wise GST/report output smoke passes.
- `main.py`: no more shrink unless startup/navigation bug appears.
- `salon_settings.py`: no more shrink unless settings bug appears.

Final wrapper cleanup should be a separate phase after G10, not mixed with new retail features.
