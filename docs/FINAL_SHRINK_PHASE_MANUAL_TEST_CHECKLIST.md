# Final Shrink Phase Manual Test Checklist

Date started: 2026-04-30

Purpose:
- Close the large-file split work safely after source/EXE smoke passed.
- Keep public wrapper files in place.
- Remove only dead, duplicate, unreachable, or already-extracted compatibility code.
- Do not add new features in this phase.

## Phase 1 - Salon Settings Wrapper Shrink

Status: completed and source-smoke passed.

Changed file:
- `salon_settings.py`

What changed:
- Removed unreachable old Shop Info UI code after `return render_shop_info_tab(self)`.
- Removed unreachable old Theme UI code after `return render_theme_tab(self)`.
- Kept `SettingsFrame`, `_save_info`, `_browse_logo`, `_apply_theme`, and all public settings helpers.
- No V5.6 files changed.
- No Settings behavior intentionally changed.

Before/after:
- Before this phase: 1,744 lines.
- After this phase: 1,571 lines.
- Removed: 173 unreachable lines.

Automated verification:
- `py_compile` passed for:
  - `salon_settings.py`
  - `salon_info_tab.py`
  - `theme_tab.py`
  - `src/blite_v6/settings/*.py`
- Focused tests passed:
  - `tests/test_settings_core_theme.py`
  - `tests/test_settings_tab_specs.py`
  - `tests/test_settings_bill_print.py`
  - `tests/test_settings_security_prefs_notifications.py`
  - `tests/test_settings_advanced_integrations.py`
  - `tests/test_settings_backup_license_about.py`
- Result: 34 passed.

Manual test checklist:
- Source smoke from `main.py`: passed by user screenshots on 2026-04-30.
- Open installed EXE.
- Login as admin/owner.
- Open Settings page.
- Open Shop Info tab.
- Edit a harmless value only if needed, save, and confirm no crash.
- Open Theme tab.
- Switch theme or re-save current theme; if restart prompt appears, choose `No` first.
- Open Bill & GST tab.
- Open Security tab.
- Open Preferences tab.
- Open Notifications tab.
- Open Backup tab.
- Open AI Assistant tab if enabled.
- Open Advanced Features tab.
- Open Licensing tab and confirm Activated/Lifetime still appears.
- Open About tab and confirm contact/version info appears.
- Return to Billing page and confirm app still responds.

Pass condition:
- Every Settings tab opens.
- Theme tab does not close the app unless the user explicitly accepts restart.
- License still shows activated/lifetime.
- Billing still opens after leaving Settings.

If a problem appears:
- Record screenshot.
- Record exact tab/action.
- Do not continue to Phase 2 until fixed.

## Phase 2 - Main Wrapper Shrink

Status: completed in source.

Changed file:
- `main.py`

What changed:
- Removed unused old full-screen startup splash methods:
  - `_show_startup_splash`
  - `_finish_startup_splash`
  - `_play_startup_media`
- Removed only imports that existed for those unused methods.
- Kept the current startup path used by the app:
  - hidden root build
  - source/EXE startup placeholder logo
  - loading text/logo animation
  - lazy page loading
- Kept `main.py` as the app entry point.
- Kept `SalonApp` public class and current login/license flow.
- No V5.6 files changed.
- No navigation, billing, reports, inventory, or settings behavior intentionally changed.

Before/after:
- Before this phase: 1,643 lines.
- After this phase: 1,513 lines.
- Removed: 130 unused startup-splash lines.

Automated verification:
- `py_compile` passed for:
  - `main.py`
  - `src/blite_v6/app/startup_ui.py`
  - `src/blite_v6/app/startup_runtime.py`
  - `src/blite_v6/app/app_shell.py`
  - `src/blite_v6/app/navigation.py`
- Focused Main tests passed:
  - `tests/test_main_app_specs.py`
  - `tests/test_main_startup_runtime.py`
  - `tests/test_main_runtime_features.py`
  - `tests/test_main_shell_specs.py`
  - `tests/test_main_navigation.py`
  - `tests/test_main_startup_ui.py`
  - `tests/test_main_session_events.py`
  - `tests/test_main_final_integration_smoke.py`
  - `tests/test_license_gate_deferred.py`
- Result: 44 passed.

Manual test checklist:
- Run `main.py`.
- Confirm login opens normally.
- Login as admin/owner.
- Confirm splash/loading behavior is not worse than before this phase.
- Open Dashboard.
- Open Billing.
- Open Customers.
- Open Appointments.
- Open Inventory.
- Open Reports.
- Open Settings.
- In Settings, open Shop Info, Theme, Bill & GST, Security, Preferences, Notifications, Backup, AI Assistant, Advanced Features, Licensing, About, and Print/Bill.
- Confirm Licensing still shows Activated/Lifetime on an activated PC.
- Return to Billing and confirm the app still responds.

Pass condition:
- App starts from `main.py`.
- No startup crash.
- No blank/white main window remains on screen.
- All main pages open.
- Settings tabs still open as in Phase 1 screenshots.

If a problem appears:
- Record screenshot.
- Record exact page/action.
- Do not continue to Phase 3 until fixed.

## Phase 3 - Reports Wrapper Shrink

Status: completed in source.

Changed file:
- `reports.py`

What changed:
- Cleaned corrupted/mojibake wrapper comments and docstrings.
- Kept `ReportsFrame` public class and all report actions.
- Kept report helper delegation through `src/blite_v6/reports/*`.
- No report loading, export, print, delete/restore, chart, saved bill, or service report runtime logic intentionally changed.
- No V5.6 files changed.

Before/after:
- Before this phase: 1,794 lines.
- After this phase: 1,783 lines.
- Removed: 11 non-runtime wrapper text lines.

Automated verification:
- `py_compile` passed for:
  - `reports.py`
  - `src/blite_v6/reports/bill_text.py`
  - `src/blite_v6/reports/chart_data.py`
  - `src/blite_v6/reports/delete_restore.py`
  - `src/blite_v6/reports/export_actions.py`
  - `src/blite_v6/reports/report_view.py`
  - `src/blite_v6/reports/saved_bills.py`
  - `src/blite_v6/reports/service_report.py`
- Focused Reports tests passed:
  - `tests/test_billing_report_persistence_legacy.py`
  - `tests/test_reports_bill_text.py`
  - `tests/test_reports_chart_data.py`
  - `tests/test_reports_delete_restore.py`
  - `tests/test_reports_export_actions.py`
  - `tests/test_reports_final_integration_smoke.py`
  - `tests/test_reports_saved_bills.py`
  - `tests/test_reports_service_report.py`
  - `tests/test_reports_view_model.py`
- Result: 46 passed.

Manual test checklist:
- Run `main.py`.
- Login as admin/owner.
- Open Reports page.
- Confirm Sales List tab opens.
- Use `Today`, `This Month`, `All`, and date `Filter`.
- Select a sale row and confirm preview appears.
- Use `Load to Bill` on a selected row and confirm Billing opens with bill data.
- Use `Print` only if printer/PDF fallback behavior is ready to test.
- Use `Delete Bill` only on a disposable test bill.
- Open Charts tab and confirm chart area loads.
- Open Saved Bills (PDF) tab and confirm saved PDF list/preview works if PDFs exist.
- Open Service Report tab and generate summary.
- Test export buttons with disposable output folder if needed:
  - More Exports
  - GST Export
  - Export PDF
  - Export CSV
  - Export Excel

Pass condition:
- Reports page opens without crash.
- Existing report rows load.
- Selecting a report row updates preview.
- Charts, Saved Bills, and Service Report tabs open.
- Exports either complete or show a clear recoverable error if a dependency/output path is missing.

If a problem appears:
- Record screenshot.
- Record exact tab/action.
- Do not continue to Phase 4 until fixed.

## Phase 4 - Billing Wrapper Shrink

Status: completed in source.

Changed file:
- `billing.py`

What changed:
- Cleaned corrupted/mojibreak wrapper comments and docstrings.
- Kept `BillingFrame` public class and all billing action methods.
- Kept billing helper delegation through `src/blite_v6/billing/*`.
- No billing totals, save, PDF, print, WhatsApp, product unit, barcode, offer, coupon, redeem, or cart runtime logic intentionally changed.
- No V5.6 files changed.

Before/after:
- Before this phase: 2,371 lines.
- After this phase: 2,349 lines.
- Removed: 22 non-runtime wrapper text lines.

Automated verification:
- `py_compile` passed for:
  - `billing.py`
  - `src/blite_v6/billing/barcode_lookup.py`
  - `src/blite_v6/billing/bill_document.py`
  - `src/blite_v6/billing/billing_actions.py`
  - `src/blite_v6/billing/catalog_search.py`
  - `src/blite_v6/billing/cart_operations.py`
  - `src/blite_v6/billing/customer_context.py`
  - `src/blite_v6/billing/customer_suggestions.py`
  - `src/blite_v6/billing/discounts.py`
  - `src/blite_v6/billing/report_persistence.py`
  - `src/blite_v6/billing/runtime_services.py`
  - `src/blite_v6/billing/totals.py`
  - `src/blite_v6/billing/ui_actions.py`
  - `src/blite_v6/billing/ui_bindings.py`
  - `src/blite_v6/billing/ui_sections.py`
  - `src/blite_v6/billing/whatsapp_actions.py`
- Focused Billing tests passed:
  - all `tests/test_billing*.py`
  - `tests/test_inventory_loose_quantity.py`
  - `tests/test_loose_quantity_printing.py`
- Result: 116 passed.
- Final source test gate:
  - `python -m pytest -q tests`
  - Result: 276 passed.
  - Note: root-level `python -m pytest -q` was blocked by permission-protected temporary folders outside `tests`; the source test folder itself passed.

Manual test checklist:
- Run `main.py`.
- Login as admin/owner.
- Open Billing page.
- Add a service bill and confirm preview total updates.
- Add a product bill and confirm preview total updates.
- Search product/service by name and category.
- Test barcode scan/type + Enter with a disposable product.
- Test loose/unit product quantity display if grocery/unit product data exists.
- Test GST on/off and inclusive/exclusive setting if configured.
- Test discount checkbox and discount amount.
- Test offer, coupon, redeem code, and loyalty points with disposable data.
- Test Save and confirm duplicate-save guard still prevents double entry.
- Test PDF export.
- Test Print or PDF fallback depending on printer availability.
- Test WhatsApp manual/auto workflow according to available browser driver/session.
- Test Undo Last and Clear.
- Test fast mode toggle, shortcuts, and context menu where available.
- If auto clear after save/print is enabled, confirm draft clears only after the selected action completes.

Pass condition:
- Billing page opens without crash.
- Totals and preview match added items.
- Save/PDF/Print/WhatsApp actions either complete or show clear recoverable errors.
- No duplicate report row/points/visit is created from repeated Save/PDF/Print/WA clicks.
- Existing product unit visibility behavior remains unchanged from the last accepted smoke.

If a problem appears:
- Record screenshot.
- Record exact action and invoice number.
- Do not start Inventory/Grocery implementation until fixed.

## Final Shrink Close Gate

Status: source automated gate passed; manual gate reported passed by user on 2026-04-30.

Source test result:
- `python -m pytest -q tests`
- 276 passed.

Manual gate before next implementation:
- Run `main.py`.
- Open Dashboard, Billing, Inventory, Reports, Settings.
- In Billing, complete one disposable service bill.
- In Billing, complete one disposable product bill.
- Save, PDF, Print/PDF fallback, and WhatsApp flow.
- In Reports, confirm the saved bills appear and preview/load works.
- In Settings, confirm Licensing still shows Activated/Lifetime on this PC.

After this manual gate passes:
- Final Shrink/Splitting side can be treated as closed unless a new manual smoke issue is reported.
- Start Inventory/Grocery Phase G1 from the inventory/grocery blueprint.

## Input Polish Follow-Up Gate

Automated verification:
- `python -m py_compile billing.py customers.py src\blite_v6\ui\input_behaviors.py`
- `python -m pytest -q tests\test_input_behaviors.py tests\test_billing_customer_context.py tests\test_billing_customer_ui_smoke.py`
- `python -m pytest -q tests`
- Result: 278 passed.

Manual checks:
- Billing customer name: type `biji kumar`; confirm it becomes `Biji Kumar`.
- Billing birthday: type `17121981`; confirm it becomes `17-12-1981`.
- Existing customer lookup: confirm stored birthday like `1981-12-17` displays as `17-12-1981`.
- Customers add/edit form: confirm Name auto-capitalizes and Birthday keeps `DD-MM-YYYY`.
- Do not expect auto-capitalization in search, barcode, password, API key, invoice, or code fields.

Printer note:
- If Windows has no default printer or print driver, the print fallback may open Notepad/Windows print setup. This is normal OS behavior, not a billing crash.

Date-format policy:
- Save/storage should remain ISO `YYYY-MM-DD`.
- UI display/input can use `DD-MM-YYYY`.
- A selectable date-format setting is intentionally not planned now because it adds parsing risk.
