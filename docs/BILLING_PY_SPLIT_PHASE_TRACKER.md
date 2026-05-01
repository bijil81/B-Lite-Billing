# Billing.py Split Phase Tracker

## Status Summary
- Total phases: 13
- Completed: 13
- Current phase: Complete
- Current test baseline: 160 tests passing

## Phase Checklist

| Phase | Name | Status |
| --- | --- | --- |
| 0 | Baseline, Rules, and Tracking | Complete |
| 1 | Billing Totals Domain | Complete |
| 2 | Save/Report Persistence Core | Complete |
| 3 | Customer Context | Complete |
| 4 | Catalog Search and Barcode | Complete |
| 5 | Cart Operations | Complete |
| 6 | Offers, Coupons, Redeem, Discount State | Complete |
| 7 | Bill Preview and BillData Builder | Complete |
| 8 | PDF, Print, WhatsApp Side Effects | Complete |
| 9 | UI Build Decomposition | Complete |
| 10 | Shortcuts, Context Menu, Fast Mode, Reload | Complete |
| 11 | Final Integration and Shrink BillingFrame | Complete |
| 12 | Runtime Bridge Extraction and Final Closure | Complete |

## Phase 3 Entry Checklist
- Read all customer-related methods in `billing.py`. Status: complete.
- Identify pure matching logic versus Tkinter popup rendering. Status: complete.
- Extract only non-UI logic first. Status: Phase 3A complete.
- Keep wrapper methods in `BillingFrame`.
- Add tests before changing UI behavior.

## Phase 3 Progress
- 3A - Pure Customer Rules: Complete.
- 3B - Suggestion Matching: Complete.
- 3C - BillingFrame Wrappers: Complete.
- 3D - Tests: Complete.

## Phase 3 Target Files
- `src/blite_v6/billing/customer_context.py`
- `src/blite_v6/billing/customer_suggestions.py`
- `tests/test_billing_customer_context.py`
- `tests/test_billing_customer_suggestions.py`
- `tests/test_billing_customer_ui_smoke.py`

## Phase 4 Result
- Extracted catalog search helpers:
  - `src/blite_v6/billing/catalog_search.py`
  - `tests/test_billing_catalog_search.py`
- Extracted barcode helpers:
  - `src/blite_v6/billing/barcode_lookup.py`
  - `tests/test_billing_barcode_lookup.py`
- Added wrapper smoke:
  - `tests/test_billing_catalog_barcode_ui_smoke.py`
- `billing.py` keeps UI rendering and method names.
- Verification:
  - AST parse passed for edited Phase 4 files.
  - `python -m pytest -p no:cacheprovider tests -q`
  - Result: 47 passed.
  - No cache or bytecode files left in V6.
  - V5.6 source git status clean.

## Phase 5 Result
- Extracted cart operation helpers:
  - `src/blite_v6/billing/cart_operations.py`
  - `tests/test_billing_cart_operations.py`
- Added wrapper smoke:
  - `tests/test_billing_cart_ui_smoke.py`
- `billing.py` keeps dialogs, message boxes, focus handling, and refresh calls.
- Moved tested rules for:
  - quantity parsing
  - inventory cache TTL decision
  - variant stock guard
  - product inventory quantity counting
  - add or merge item
  - edit quantity
  - edit price
  - remove item
  - undo last item
- Verification:
  - AST parse passed for edited Phase 5 files.
  - `python -m pytest -p no:cacheprovider tests -q`
  - Result: 56 passed.
  - No cache or bytecode files left in V6.
  - V5.6 source git status clean.

## Phase 6 Result
- Extracted discount state helpers:
  - `src/blite_v6/billing/discounts.py`
  - `tests/test_billing_discounts.py`
- Added wrapper smoke:
  - `tests/test_billing_discounts_ui_smoke.py`
- `billing.py` keeps message boxes, entry mutation, combobox mutation, and refresh calls.
- Moved tested rules for:
  - manual discount toggle state
  - offer option formatting
  - selected offer mapping
  - coupon code normalization
  - coupon success/invalid state
  - offer clear state
  - redeem success/invalid state
  - redeem clear info visibility
- Verification:
  - AST parse passed for edited Phase 6 files.
  - `python -m pytest -p no:cacheprovider tests -q`
  - Result: 64 passed.
  - No cache or bytecode files left in V6.
  - V5.6 source git status clean.

## Phase 7 Result
- Extracted bill document helpers:
  - `src/blite_v6/billing/bill_document.py`
  - `tests/test_billing_bill_document.py`
- Added wrapper smoke:
  - `tests/test_billing_bill_document_ui_smoke.py`
- `billing.py` keeps `print_engine` calls, text widget updates, total label updates, and PDF path caller surface.
- Moved tested rules for:
  - service/product item splitting
  - print width resolution
  - print settings width application
  - invoice branding fallback
  - shared `BillData` kwargs building
  - offer name fallback
  - PDF path construction
- Verification:
  - AST parse passed for edited Phase 7 files.
  - `python -m pytest -p no:cacheprovider tests -q`
  - Result: 71 passed.
  - No cache or bytecode files left in V6.
  - V5.6 source git status clean.

## Phase 8 Result
- Extracted billing action helpers:
  - `src/blite_v6/billing/billing_actions.py`
  - `tests/test_billing_actions.py`
- Extracted WhatsApp action helpers:
  - `src/blite_v6/billing/whatsapp_actions.py`
  - `tests/test_billing_whatsapp_actions.py`
- Added wrapper smoke:
  - `tests/test_billing_actions_ui_smoke.py`
- `billing.py` keeps PDF generation, file opening, printer access, WhatsApp helper calls, Tkinter message boxes, button mutation, and thread scheduling.
- Moved tested rules for:
  - bill-empty action guard
  - report-save argument mapping from totals
  - save, PDF, print, and WhatsApp dialog text
  - auto-clear-after-print setting decision
  - WhatsApp status button view mapping
  - WhatsApp session result mapping
  - WhatsApp send error extraction
- Verification:
  - AST parse passed for edited Phase 8 files.
  - `python -m pytest -p no:cacheprovider tests -q`
  - Result: 81 passed.
  - No cache or bytecode files left in V6.
  - V5.6 source git status clean.

## Phase 9 Result
- Extracted generic UI section helpers:
  - `src/blite_v6/billing/ui_sections.py`
  - `tests/test_billing_ui_sections.py`
- Extracted UI binding helpers:
  - `src/blite_v6/billing/ui_bindings.py`
- Added wrapper smoke:
  - `tests/test_billing_ui_build_smoke.py`
- `billing.py` keeps `BillingFrame._build`, widget attribute ownership, Tkinter widget creation flow, and all named attributes used by downstream methods.
- Moved tested rules/helpers for:
  - billing mode visibility and initial mode selection
  - bill preview font bounds
  - responsive left-panel width calculation
  - finish-action button spec order, grouping, command names, and widths
  - combobox style setup wrapper
  - reusable card/intro/scrollable-panel builders
  - customer/search/barcode/quantity/discount/preview binding wrappers
  - preview font resize and paned split sync wrappers
- Verification:
  - AST parse passed for edited Phase 9 files.
  - `python -m pytest -p no:cacheprovider tests -q`
  - Result: 87 passed.
  - No cache or bytecode files left in V6.
  - V5.6 source git status clean.

## Phase 10 Result
- Extracted UI action helpers:
  - `src/blite_v6/billing/ui_actions.py`
  - `tests/test_billing_ui_actions.py`
- Added wrapper smoke:
  - `tests/test_billing_ui_actions_smoke.py`
- `billing.py` keeps Tk root bindings, bind-all registration, widget Return bindings, context-menu service imports, action registration, clipboard copy calls, menu rendering, popup display, product catalog refresh, and widget mutation.
- Moved tested rules/helpers for:
  - context menu visibility
  - context total extraction and context extra payload
  - context action and clipboard specs
  - shortcut binding specs
  - fast-mode toggle state and button view
  - billing tab refresh action sequence
  - booking prefill normalization and confirmation copy
  - reload reset state
- Verification:
  - AST parse passed for edited Phase 10 files.
  - `python -m pytest -p no:cacheprovider tests -q`
  - Result: 94 passed.
  - No cache or bytecode files left in V6.
  - V5.6 source git status clean.

## Phase 11 Result
- Extracted final non-V5 report persistence core:
  - `src/blite_v6/billing/report_persistence.py`
  - `tests/test_billing_report_persistence_legacy.py`
- Added final integration smoke:
  - `tests/test_billing_final_integration_smoke.py`
- Added final report:
  - `docs/PHASE11_FINAL_INTEGRATION_REPORT.md`
- `billing.py` keeps `BillingFrame` UI coordination and the V5 billing branch.
- Moved tested rules/helpers for:
  - non-V5 CSV report write
  - duplicate invoice guard
  - inventory/customer/visit/points/redeem/cloud/app callback side-effect ordering
  - optional side-effect failure tolerance
- Verification:
  - AST parse passed for edited Phase 11 files.
  - `python -m pytest -p no:cacheprovider tests -q`
  - Result: 99 passed.
  - No cache or bytecode files left in V6.
  - V5.6 source git status clean.
- Final status:
  - Billing split blueprint phases 0-11 are complete.

## Phase 12 Result
- Extracted billing runtime bridge helpers:
  - `src/blite_v6/billing/runtime_services.py`
  - `tests/test_billing_runtime_services.py`
- `billing.py` keeps the public compatibility names by importing aliases:
  - `_auto_save_customer`
  - `_billing_get_customers`
  - `_billing_save_customer`
  - `_billing_record_visit`
  - `_billing_redeem_points`
  - `_billing_entry_fg`
  - `_billing_card_fg`
  - `_load_services_products`
- Moved runtime bridge responsibilities for:
  - entry/card contrast color helpers
  - V5/legacy customer service bridge
  - auto-save customer identity normalization
  - visit and loyalty point bridge
  - service/product snapshot loading
- Verification:
  - Focused Phase 12 tests: 18 passed.
  - `python -m pytest -q`
  - Result: 160 passed.
- Final status:
  - Billing split phases 0-12 are complete.
  - Remaining `billing.py` size is mostly Tkinter UI coordination; next large-file target should be `reports.py`.

## Product Billing Add-on Result - Loose Grocery Quantities
- Scope:
  - small product-side enhancement after billing split closure
  - no V5.6 source edits
  - no broad UI redesign
- Implemented:
  - decimal quantity parsing in `src/blite_v6/billing/cart_operations.py`
  - unit suffix conversion for kg/g and L/ml
  - cart quantity labels for loose products
  - BillingFrame add/edit quantity integration
  - print/PDF decimal quantity preservation
  - legacy inventory decimal stock deduction/display/save/quick-update support
- Safety notes:
  - services and packet products continue to work as `pcs`
  - no silent rewrite of existing product data
  - existing totals path already multiplies numeric price and quantity, so subtotal logic remained stable
- Verification:
  - focused grocery quantity tests: 14 passed
  - full suite: `166 passed`
- Manual gate:
  - create/select loose kg product
  - add `1240g`
  - confirm subtotal, stock balance, bill save, PDF, print preview, WhatsApp, and duplicate-save guard.

## Product Unit Metadata Follow-up
- Confirmed and fixed unit auto-selection:
  - V5 variant products use their `unit_type`.
  - Legacy inventory products now pass `inventory.json` unit metadata into billing selection.
- Manual source startup issue:
  - root cause was deferred licensing work, not grocery quantity logic.
  - source `main.py` now bypasses unfinished licensing enforcement for manual smoke.
  - packaged EXE licensing enforcement remains in place for Phase L1/release validation.
- Verification:
  - focused follow-up tests: 16 passed
  - full suite: `168 passed`
