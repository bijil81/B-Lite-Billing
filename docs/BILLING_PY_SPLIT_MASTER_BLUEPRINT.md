# Billing.py Split Master Blueprint

Date: 2026-04-28

Source file:
- `G:\chimmu\Bobys_Salon Billing\B-Lite management_Billing_V6.0\billing.py`
- Current size: 2,607 lines, 340,786 bytes

Goal:
- Split `billing.py` safely without changing working billing behavior.
- Move money logic, save/report logic, search, cart operations, customer context, preview, print, PDF, and WhatsApp side effects into focused modules.
- Keep `BillingFrame` as the UI coordinator until all behavior is covered by tests.

## Safety Rules
- Never edit the stable V5.6 source folder during this migration.
- Each phase must preserve the public behavior of `BillingFrame`.
- Move one responsibility at a time.
- Keep wrapper methods in `billing.py` during migration.
- Add focused tests before or during each extraction.
- Run focused tests after every extraction.
- Update `docs/MIGRATION_LEDGER.md` after every phase.
- Do not split `_build` first. It is the highest-risk method and should be decomposed only after dependent behavior is extracted.

## Current Risk Map

Largest methods:
- `_build`: 648 lines. Full billing UI construction.
- `_ss_show`: 104 lines. Smart-search popup rendering and interactions.
- `_edit_item_qty`: 90 lines. Cart item edit dialog and validation.
- `send_whatsapp`: 70 lines. Save, PDF, WhatsApp status, external send flow.
- `add_item`: 66 lines. Cart item creation and inventory/product metadata.
- `_save_report`: 62 lines. Legacy report persistence and side effects.
- `_build_suggestion_popup`: 61 lines. Customer autocomplete UI.
- `_refresh_bill_inner`: 57 lines. Bill preview generation.
- `_on_barcode_enter`: 56 lines. Barcode workflow.
- `_ss_typing`: 53 lines. Smart-search state and filtering.
- `_lookup_barcode`: 51 lines. Product lookup behavior.

Main responsibility clusters:
- Billing totals and tax.
- Save/report persistence.
- Customer lookup, autocomplete, birthday, membership.
- Product/service catalog, smart search, barcode scan.
- Cart item add/edit/remove/reset.
- Offer, coupon, redeem code, discount state.
- Bill preview and `BillData` building.
- PDF, print, WhatsApp side effects.
- UI layout construction.
- Keyboard shortcuts, context menu, fast mode, reload.

## Phase Count

Safe split originally used 12 phases: Phase 0 through Phase 11.

After runtime dependency and QA-fix porting, an additional closure phase was added:
- Phase 12 - Runtime bridge extraction and final billing split closure.

Reason:
- The file mixes UI, state, money calculation, persistence, hardware/external side effects, and customer/product lookup.
- Splitting fewer than 8 phases would bundle unrelated risks together.
- Splitting more than 12 phases would slow migration without much extra safety.
- 12 phases gives one verification gate per responsibility cluster.

## Phase Plan

### Phase 0 - Baseline, Rules, and Tracking
Status: complete

Deliverables:
- V6 workspace created.
- Engineering rules and master prompt created.
- Migration ledger created.
- Exact-copy references preserved.

Verification:
- V5.6 remains untouched.
- Copied files compared before editing.

### Phase 1 - Billing Totals Domain
Status: complete

Extracted module:
- `src/blite_v6/billing/totals.py`

Moved responsibility:
- Service subtotal.
- Product subtotal.
- Direct discount.
- Membership discount.
- Loyalty points discount.
- Offer discount.
- Redeem discount.
- GST inclusive/exclusive calculation.

Verification:
- Focused totals tests.
- Legacy formula comparison tests.

### Phase 2 - Save/Report Persistence Core
Status: complete

Extracted module:
- `src/blite_v6/billing/report_persistence.py`

Moved responsibility:
- Legacy CSV row formatting.
- Invoice payload construction.
- CSV mirror write.
- Save orchestration with injected dependencies.

Verification:
- Existing `tests/test_billing_logic.py`.
- Full current V6 focused test suite.

### Phase 3 - Customer Context
Status: complete

Target methods:
- `_billing_get_customers`
- `_billing_save_customer`
- `_billing_record_visit`
- `_billing_redeem_points`
- `_auto_save_customer`
- `_on_customer_keyrelease`
- `_show_suggestions`
- `_build_suggestion_popup`
- `_commit_customer_suggestion`
- `_fill_customer`
- `_on_phone_lookup`
- `_check_membership_discount`
- `_check_birthday_offer`

Planned modules:
- `src/blite_v6/billing/customer_context.py`
- `src/blite_v6/billing/customer_suggestions.py`

Safety gate:
- Pure tests for customer matching and selected customer payload.
- Wrapper methods remain in `billing.py`.

### Phase 4 - Catalog Search and Barcode
Status: complete

Target methods:
- `_load_services_products`
- `_get_data`
- `_use_v5_variant_products`
- `_get_v5_variant_matches`
- `_get_v5_variant_categories`
- `_apply_search_selection`
- `set_mode`
- `_refresh_cats`
- `_smart_search`
- `_ss_typing`
- `_ss_show`
- `_ss_select`
- `_on_barcode_enter`
- `_lookup_barcode`

Planned modules:
- `src/blite_v6/billing/catalog_search.py`
- `src/blite_v6/billing/barcode_lookup.py`

Safety gate:
- Tests for category filtering, exact match, barcode match, and variant metadata preservation.

### Phase 5 - Cart Operations
Status: complete

Target methods:
- `add_item`
- `_edit_item_qty`
- `_get_inventory_lookup_map`
- `undo_last`
- `_reset_form`
- `clear_all`
- `_prepare_new_bill_if_completed`

Planned module:
- `src/blite_v6/billing/cart_operations.py`

Safety gate:
- Tests for item add/edit/remove/reset.
- Inventory deduction metadata must remain unchanged.

### Phase 6 - Offers, Coupons, Redeem, Discount State
Status: complete

Target methods:
- `_toggle_discount`
- `_refresh_offer_dropdown`
- `_on_offer_select`
- `_apply_coupon`
- `_clear_offer`
- `_apply_redeem`
- `_clear_redeem`

Planned module:
- `src/blite_v6/billing/discounts.py`

Safety gate:
- Tests for manual discount, offer, coupon, redeem code, and interaction ordering with totals.

### Phase 7 - Bill Preview and BillData Builder
Status: complete

Target methods:
- `_refresh_bill`
- `_refresh_bill_inner`
- `_build_bill_data`
- `_build_bill_data_inner`
- `_pdf_path`

Planned module:
- `src/blite_v6/billing/bill_document.py`

Safety gate:
- Golden text or structured `BillData` tests for preview/PDF input.

### Phase 8 - PDF, Print, WhatsApp Side Effects
Status: complete

Target methods:
- `manual_save`
- `save_pdf`
- `print_bill`
- `send_whatsapp`
- `_check_wa_status_billing`

Planned modules:
- `src/blite_v6/billing/billing_actions.py`
- `src/blite_v6/billing/whatsapp_actions.py`

Safety gate:
- Tests with mocked PDF, print, WhatsApp, and save dependencies.
- No duplicate invoice save across Save/PDF/Print/WhatsApp.

### Phase 9 - UI Build Decomposition
Status: complete

Target method:
- `_build`

Planned modules:
- `src/blite_v6/billing/ui_sections.py`
- `src/blite_v6/billing/ui_bindings.py`

Safety gate:
- Keep the same widget attributes used by existing methods.
- Do not change visual layout unless needed to prevent breakage.

### Phase 10 - Shortcuts, Context Menu, Fast Mode, Reload
Status: complete

Target methods:
- `_right_click_menu`
- `_register_billing_context_menu_callbacks`
- `_bind_shortcuts`
- `_toggle_fast_mode`
- `_update_fast_mode_ui`
- `reload_services`
- `refresh`
- `prefill_from_booking`

Planned module:
- `src/blite_v6/billing/ui_actions.py`

Safety gate:
- Smoke tests or lightweight object tests for callbacks and mode state.

### Phase 11 - Final Integration and Shrink BillingFrame
Status: complete

Deliverables:
- `billing.py` becomes a thin UI coordinator.
- All extracted modules have focused tests.
- Legacy wrappers are reviewed and removed only when safe.
- Final full regression checklist completed.

Safety gate:
- Run all available V6 tests.
- Run manual billing smoke checklist.
- Compare critical behavior with V5.6.

### Phase 12 - Runtime Bridge Extraction and Final Closure
Status: complete

Extracted module:
- `src/blite_v6/billing/runtime_services.py`

Moved responsibility:
- Billing entry/card text contrast helpers.
- V5/legacy customer bridge.
- Auto-save customer bridge.
- Visit/points bridge.
- Billing services/products snapshot loader.

Safety gate:
- Public names remain imported in `billing.py` for existing monkeypatch/caller compatibility.
- Focused runtime service tests.
- Full V6 pytest regression.

## Current Progress
- Phase 0 complete.
- Phase 1 complete.
- Phase 2 complete.
- Phase 3 complete.
- Phase 4 complete.
- Phase 5 complete.
- Phase 6 complete.
- Phase 7 complete.
- Phase 8 complete.
- Phase 9 complete.
- Phase 10 complete.
- Phase 11 complete.
- Phase 12 complete.

## Next Action
Run live V6 app/manual billing smoke using `docs/PHASE11_FINAL_INTEGRATION_REPORT.md`, then start the next large-file split target: `reports.py`.
