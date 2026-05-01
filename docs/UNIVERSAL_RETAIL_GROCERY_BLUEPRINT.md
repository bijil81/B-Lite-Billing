# Universal Retail / Grocery Blueprint

Last updated: 2026-04-30

Execution blueprint:
- `docs/INVENTORY_GROCERY_IMPLEMENTATION_BLUEPRINT.md`

Current implementation decision:
- Treat the broad Billing/Main/Reports/Settings split work as functionally complete, but keep the top-level wrapper files.
- Do not delete `billing.py`, `main.py`, `reports.py`, or `salon_settings.py`; they remain compatibility entry points.
- New retail/grocery logic should be added in focused new modules, not by growing the legacy wrapper files.
- `inventory.py` is the only justified next split/wiring target because grocery work directly touches inventory product master, stock, import, purchase, vendor, and item tax behavior.

## Current State Verified

- Inventory has product category on the add/edit item dialog.
- Inventory category is currently a readonly combo fed from existing inventory rows, not a full category master.
- Inventory has product metadata:
  - category
  - brand
  - base product
  - item name
  - bill label
  - unit
  - pack size
  - quantity
  - reorder/min stock
  - cost
  - sale price
  - barcode
- V5 product variant SQLite foundation exists for brands, categories, products, variants, stock movements.
- Product variant schema does not yet include item-level GST/tax rate, HSN/SAC, vendor, purchase batch, MRP, expiry, or tax category.
- Billing currently supports one global GST rate per bill, not per-item GST.
- Inventory has a quick stock update type named `Add (Purchase)`, but there is no purchase invoice module, vendor master, supplier ledger, purchase return, or batch-cost workflow.
- Admin Products tab has JSON and Excel import for product rows. It accepts item name, category, brand, pack size, unit, price, and stock. This is a catalog import, not a full purchase import.
- Inventory has import helpers that copy bundled `services_db.json` products into stock, but there is no clean-install import wizard on the Inventory page for a shop owner to bulk-load a real catalog.
- Current import paths treat one `price` value as both sale price and cost price in the v5 product variant foundation. This is not enough for retail/grocery accounting.
- Inventory add/edit currently stores cost and preserves an existing sale price, but the visible Inventory dialog does not provide a clear separate sale-price field for new item setup.
- Billing does not currently warn when a product is sold below cost. A safe implementation should warn and require explicit confirmation before continuing.

## White-label Build Catalog Shipping

### Phase B0 - Optional Sample Catalog Packaging

Goal:
- Let a release build ship either with the demo salon catalog or with a clean empty catalog.

Recommended branding/config flag:
- `ship_sample_catalog`: true/false

Behavior:
- If true, package/copy the bundled `services_db.json` sample services/products.
- If false, package a valid empty catalog:
  - `Services`: `{}`
  - `Products`: `{}`
- Do not delete `services_db.json`; build validation expects a valid catalog file.
- Existing installed AppData must not be silently wiped. The flag only controls fresh installs or clean AppData.

Acceptance tests:
- Fresh install with sample catalog enabled shows demo services/products.
- Fresh install with sample catalog disabled starts with empty Services/Products.
- Existing AppData keeps customer data and existing catalog after update.
- Build validation still passes.

## Immediate Safe UI Phase

### Phase G0 - Billing Unit Visibility

Goal:
- Make the already implemented loose quantity logic visible and understandable in Billing UI.

Status:
- Completed on 2026-04-29.

Scope:
- Add the unit UI into the marked billing row by shrinking the price area and adding a compact unit/help area beside Qty.
- Product selection should update:
  - `Qty (kg)` / `Qty (g)` / `Qty (ml)` / `Qty (L)` / `Qty (pcs)`
  - small helper text such as `Enter 1.24 or 1240g`
  - unit badge such as `Loose kg`
- Hide this helper for pure service mode.
- Show it when:
  - billing mode is `product_only`, or
  - billing mode is `mixed` and current mode is Products.

Risk:
- Low, if limited to labels and helper text.
- Existing totals, save, PDF, print, WhatsApp logic should remain unchanged.

Acceptance tests:
- Product with unit `kg`: selecting it changes Qty label/helper.
- Product with unit `pcs`: selecting it shows normal piece quantity.
- Service mode does not show grocery helper.
- `python -m pytest -q` passes.

Implemented verification:
- `tests/test_billing_unit_visibility.py`
- `tests/test_billing_ui_build_smoke.py`
- Full suite: `171 passed`.

## Product Master / Inventory Foundation

### Phase G1 - Universal Product Master UI

Goal:
- Make inventory item creation suitable for salon, service-plus-product, retail, supermarket, and grocery workflows.

Recommended fields:
- Product name
- Category
- Brand
- Base product
- Variant / pack label
- Sell unit: pcs, kg, g, L, ml, meter, custom
- Price basis: per piece, per kg, per g, per L, per ml
- Barcode / SKU
- MRP
- Sale price
- Cost price
- Opening stock
- Reorder level
- HSN/SAC
- GST rate
- Tax inclusive/exclusive flag
- Active/inactive

Category behavior:
- Replace readonly category-only combo with searchable combo that allows a new category through a controlled create path.
- Longer term: add category master with active/inactive state.

Risk:
- Medium. Inventory data shape changes touch billing search, barcode lookup, stock deduction, import, reports, and migration.

### Phase G1A - Bulk Product Import Wizard

Goal:
- Make clean installs usable for real shops without adding every product one by one.

Supported import formats:
- Excel `.xlsx`
- JSON
- Later optional CSV

Required columns:
- Product name
- Category
- Sale price

Recommended optional columns:
- Brand
- Variant / pack size
- Unit
- SKU
- Barcode
- Cost price
- MRP
- Opening stock
- Reorder level
- GST rate
- HSN/SAC
- Tax inclusive/exclusive

Validation rules:
- Preview rows before import.
- Show created, updated, skipped, and errored rows.
- Do not silently rewrite invalid prices, stock, GST, or barcode duplicates.
- Support update-by-barcode/SKU/name depending on available identifiers.

Acceptance tests:
- Import empty file safely.
- Import valid products into empty clean install.
- Import duplicate barcode warns or skips according to selected policy.
- Import product with cost price and sale price stores both separately.
- Import product with sale price below cost warns during import and requires explicit approval or skips the row.

## Purchase and Vendor Foundation

### Phase G2 - Vendor Master

Goal:
- Add vendors/suppliers for purchase workflows.

Recommended vendor fields:
- Vendor name
- Phone
- GSTIN
- Address
- Opening balance
- Active/inactive

Current status:
- No real vendor master exists.

### Phase G3 - Purchase Entry

Goal:
- Replace the shallow `Add (Purchase)` stock adjustment with auditable purchase entries.

Recommended purchase fields:
- Purchase invoice no
- Vendor
- Purchase date
- Product/variant
- Quantity
- Unit
- Cost
- MRP
- Sale price
- Item GST rate
- Batch no
- Expiry date for grocery/medicine-like workflows
- Payment status

Stock rule:
- Purchase increases stock through stock movement records.
- Direct correction remains available separately as an admin-only adjustment.

Pricing safety rule:
- If sale price is lower than cost/purchase price, block by default with a warning.
- Allow `Continue anyway` only after explicit user confirmation and record the override in the activity log or purchase movement note.
- This warning must apply in:
  - product master save
  - bulk import
  - purchase bill entry
  - billing/manual price override if manual price editing is allowed

Current status:
- `cost_price`, `sale_price`, and `stock_qty` fields exist in the v5 product variant foundation.
- A full purchase bill UI, vendor ledger, purchase report, and below-cost warning flow are not implemented yet.

Risk:
- High if rushed, because stock valuation and financial reports depend on it.

## Item-wise GST

### Phase G4 - Product Tax Profile

Goal:
- Store item-level GST/tax information when products are created.

Recommended fields:
- `gst_rate`
- `tax_inclusive`
- `hsn_sac`
- optional `tax_category`

Current status:
- Billing has one global `gst_rate`.
- `calculate_billing_totals()` computes tax on the bill grand total.
- Invoice item persistence does not store per-line tax split.

### Phase G5 - Billing Item-wise Tax Engine

Goal:
- Calculate GST per line when GST is enabled.

Rules:
- Product line uses product GST rate.
- Service line uses service/default GST rate unless a service tax profile is later added.
- Inclusive tax: line tax = line total - line total / (1 + rate).
- Exclusive tax: line tax = line total * rate and net increases.
- Bill print/PDF should show tax summary grouped by rate.

Risk:
- High. This touches totals, invoice validation, persistence, reports, print/PDF, WhatsApp, and legacy CSV compatibility.

## Recommended Sequence

1. Finish the current split/refactor foundation and keep tests green.
2. Do Phase G0 now if only visual billing-unit visibility is needed for manual smoke.
3. Complete the pending licensing Phase L1 before release-candidate build work.
4. After licensing, start G1-G5 as a separate retail/grocery expansion branch.

Reason:
- G0 is low-risk and clarifies an already implemented behavior.
- G1-G5 are not just UI changes; they introduce master data, purchase audit trails, tax accounting, and report implications.
- Doing item-wise GST before reports/persistence are ready risks incorrect financial data.

## Release Gate For Retail/Grocery Expansion

- Product creation with new category, kg loose unit, and barcode.
- Billing `1240g` for kg item.
- Billing packet item with pcs quantity.
- Mixed GST rates in one bill.
- Inclusive and exclusive GST modes.
- Purchase entry increases stock.
- Sale decreases stock.
- Purchase/vendor report.
- Sales report tax summary by GST rate.
- PDF/print/WhatsApp show correct quantities and tax summary.
- Duplicate save guard still works.
- `python -m pytest -q` passes.

## 2026-05-01 Production Readiness Update

Completed in source:
- Inventory product master for packet and loose products.
- Billing search bridge for inventory/admin products.
- Loose/decimal quantity billing and unit-aware preview.
- Import preview/apply for CSV, XLSX, and JSON.
- Vendor master, purchase bill, purchase history foundation.
- Item-wise GST settings, category master, and classification master.
- Billing-time below-cost inline alert with Preferences toggle.
- Daily closing PDF with grocery/product sales and GST summary.
- Grocery Reports UI with Today, This Week, This Month, and custom date filters.

Still pending before production-ready release:
- Full automated regression gate.
- Full source-mode manual smoke checklist.
- EXE rebuild and install/uninstall smoke.
- License activation smoke on rebuilt EXE.
- Print/PDF/WhatsApp smoke on rebuilt EXE.
- Fresh install sample-data policy and smoke.
- Optional graphical dashboard phase.
- Final wrapper-size audit and migration ledger review.
- Final data safety audit for additive DB changes, reports totals, and stock movements.
