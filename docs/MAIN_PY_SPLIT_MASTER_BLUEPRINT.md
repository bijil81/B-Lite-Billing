# Main.py Split Master Blueprint

Date: 2026-04-28

Source file:
- Stable source: `G:\chimmu\Bobys_Salon Billing\Bobys Billing V5.6 Development\main.py`
- V6 working copy: `G:\chimmu\Bobys_Salon Billing\B-Lite management_Billing_V6.0\main.py`
- V6 untouched reference: `G:\chimmu\Bobys_Salon Billing\B-Lite management_Billing_V6.0\legacy_reference\main.py`
- Current size: 1,698 lines, 69,896 bytes

Goal:
- Split `main.py` safely after the completed `billing.py` split.
- Preserve the V5.6 startup behavior while making V6 runnable and easier to test.
- Keep `SalonApp` as the UI coordinator until startup, navigation, session, and shell behavior are covered by focused tests.
- Do not add new features during this pass. Stability, predictable startup, and clean dependency gates are the target.

## Current Baseline

Completed before this blueprint:
- Copied V5.6 `main.py` into the V6 project folder.
- Preserved a byte-for-byte reference copy in `legacy_reference\main.py`.
- Verified the V5.6 source, V6 working copy, and V6 reference copy hashes match.
- Verified `main.py` parses with Python AST.
- Verified the V5.6 git status remains clean.
- Completed the Phase 0 dependency gate for import/module smoke.

Current `main.py` structure:
- `SalonApp` class: lines 157-1571, 1,415 lines.
- `_build`: lines 803-1117, 315 lines.
- `__init__`: lines 631-738, 108 lines.
- `_show_startup_splash`: lines 253-340, 88 lines.
- `_ensure_frame`: lines 1258-1328, 71 lines.
- `_show_startup_placeholder`: lines 1143-1209, 67 lines.
- `switch_to`: lines 1330-1391, 62 lines.

Top-level startup helpers:
- `_enable_windows_dpi_awareness`
- `_relaunch_current_app`
- `_log_exception`
- `_show_fatal_error_dialog`
- `_install_global_exception_hooks`
- `_run_startup_step`
- `_start_login`

## Safety Rules

- Never edit the stable V5.6 source folder during the V6 migration.
- Copy dependencies in controlled batches, not as a blind full-project copy.
- Keep `main.py` runnable after each phase where dependencies allow it.
- Extract one responsibility at a time and keep wrapper methods in `SalonApp` during migration.
- Do not split `_build` first. It is a high-risk UI construction method and should be decomposed only after startup specs and navigation contracts are stable.
- Do not guess at mojibake or text encoding fixes. Preserve text exactly unless there is a verified source and test.
- Every phase must update `docs\MIGRATION_LEDGER.md`.
- Every phase must run at least AST/import/focused tests. Full GUI smoke is reserved for the final integration gate.

## First-Order Dependency Gate

The copied V6 `main.py` currently imports these local dependencies that are not yet present in V6:

- `activity_log.py`
- `admin.py`
- `ai_assistant\`
- `appointments.py`
- `auth.py`
- `backup_system.py`
- `branding.py`
- `db.py`
- `help_system.py`
- `icon_system.py`
- `licensing\`
- `migration_state.py`
- `migrations\`
- `notifications.py`
- `reports_data.py`
- `salon_settings.py`
- `scheduled_backup.py`
- `secure_store.py`
- `shared\`
- `ui_responsive.py`
- `ui_text.py`
- `ui_theme.py`
- `utils.py`

Lazy page modules required for a full manual app smoke:

- `dashboard.py`
- `customers.py`
- `booking_calendar.py`
- `membership.py`
- `offers.py`
- `redeem_codes.py`
- `cloud_sync.py`
- `staff.py`
- `inventory.py`
- `expenses.py`
- `whatsapp_bulk.py`
- `reports.py`
- `accounting.py`
- `closing_report.py`
- `salon_settings.py`

Dependency copy policy:
- Phase 0 copies only startup/import dependencies needed to import and launch the app shell.
- Lazy page modules are copied when the navigation gate needs them.
- Existing V6 `billing.py` remains the active billing target and should not be replaced from V5.6.

Phase 0 copied dependency batches:
- First-order startup/import dependencies:
  - `activity_log.py`
  - `admin.py`
  - `ai_assistant\`
  - `appointments.py`
  - `auth.py`
  - `backup_system.py`
  - `branding.py`
  - `db.py`
  - `help_system.py`
  - `icon_system.py`
  - `licensing\`
  - `migration_state.py`
  - `migrations\`
  - `notifications.py`
  - `reports_data.py`
  - `salon_settings.py`
  - `scheduled_backup.py`
  - `secure_store.py`
  - `shared\`
  - `ui_responsive.py`
  - `ui_text.py`
  - `ui_theme.py`
  - `utils.py`
- Second-order dependencies found by import smoke:
  - `auth_security.py`
  - `whatsapp_api\`
  - `multibranch\`
  - `help_content.py`
- Navigation/manual smoke page dependencies:
  - `dashboard.py`
  - `customers.py`
  - `booking_calendar.py`
  - `membership.py`
  - `offers.py`
  - `redeem_codes.py`
  - `cloud_sync.py`
  - `staff.py`
  - `inventory.py`
  - `expenses.py`
  - `whatsapp_bulk.py`
  - `reports.py`
  - `accounting.py`
  - `closing_report.py`
- Additional module dependencies found by navigation import smoke:
  - `adapters\product_catalog_adapter.py`
  - `services_v5\`
  - `repositories\`
  - `db_core\`
  - `validators\`
  - `date_helpers.py`
  - `ui_utils.py`
  - `barcode_utils.py`
  - `soft_delete.py`
  - `reports_export.py`

## Responsibility Map

Startup/process:
- DPI awareness, relaunch, fatal error dialogs, exception hooks, startup step wrapper, login entry.

Application state:
- Root creation, current user/session, role permissions, responsive manager, animation engine, module registry, current frame.

Navigation and permissions:
- `NAV`, `ACTION_ROLES`, `_has_access`, `has_permission`, `require_permission`, `_first_allowed_nav_key`, `_init_modules`, `_ensure_frame`, `switch_to`.

Runtime settings:
- Theme preferences, AI settings, feature visibility, sidebar visibility, nav row visibility.

UI shell:
- Window layout, sidebar, topbar, user panel, notification/help/admin/logout buttons, draggable sidebar divider, content frame.

Startup UI:
- Splash, startup placeholder, loading text, logo/media animation, page reveal.

Session/security:
- Activity tracking, inactivity timeout, logout due to inactivity, user switch, restart, shutdown cleanup.

Notifications/reminders/admin:
- Notification count, notification popup, appointment reminders, admin window opening.

Billing integration:
- `on_bill_saved`, `_refresh_today`, and the billing page load path must continue to work with the already-split V6 billing modules.

## Phase Count

Safe `main.py` split needs 9 phases: Phase 0 through Phase 8.

Reason:
- The file is smaller than the original `billing.py`, but it is more connected to startup and GUI side effects.
- Fewer than 7 phases would combine startup, shell, navigation, and session changes into risky batches.
- More than 10 phases would add process overhead without much additional safety.
- 9 phases keeps one verification gate per major responsibility cluster.

## Phase Plan

### Phase 0 - Copy, Baseline, Dependency Gate
Status: complete

Deliverables:
- V6 `main.py` working copy and untouched reference.
- Hash comparison against V5.6 source.
- AST parse confirmation.
- First-order dependency list.
- Controlled dependency copy queue for startup/import smoke.

Verification:
- V5.6 git status is clean.
- V6 `main.py` and `legacy_reference\main.py` match the V5.6 source before edits.
- No `billing.py` regression tests are changed by this phase.
- `import main` smoke passes.
- Main navigation module import smoke passes for dashboard, billing, customers, appointments, membership, offers, redeem, cloud sync, staff, inventory, expenses, WhatsApp bulk, reports, accounting, closing report, and settings modules.
- `python -m pytest -p no:cacheprovider tests -q` passes with 99 tests.
- Generated cache folders were removed after verification.

Exit criteria:
- Required startup dependencies are copied in a controlled batch.
- `main.py` and navigation module import smoke reaches the app boundary without missing-module failures.

### Phase 1 - App Specs and Policy Extraction
Status: complete

Target module:
- `src\blite_v6\app\app_specs.py`

Extract:
- `NAV`
- `ACTION_ROLES`
- Module/page metadata
- Role normalization and access decisions.
- First allowed navigation key decision.

Keep in `main.py`:
- `SalonApp` method wrappers and UI mutation.

Tests:
- Role access matrix.
- First allowed navigation key.
- Module spec order and labels.
- Billing page key still maps to the V6 billing frame.

Verification:
- Added `tests\test_main_app_specs.py`.
- `main.py` syntax compile passed.
- `import main` smoke passed.
- Navigation module import smoke passed.
- `python -m pytest -p no:cacheprovider tests -q` passed with 104 tests.
- `main.py` reduced from 1,698 lines to 1,649 lines.

### Phase 2 - Startup Runtime Utilities
Status: complete

Target module:
- `src\blite_v6\app\startup_runtime.py`

Extract:
- DPI awareness helper.
- Relaunch helper.
- Exception logging/fatal dialog helper.
- Global exception hook installer.
- Startup step runner.

Keep in `main.py`:
- The actual `if __name__ == "__main__"` orchestration and login entry wrapper until final integration.

Tests:
- Startup step success/failure behavior.
- Exception text normalization.
- Relaunch command construction without executing a relaunch.

Verification:
- Added `tests\test_main_startup_runtime.py`.
- `main.py` and `startup_runtime.py` syntax compile passed.
- Focused Phase 1/2 tests passed with 10 tests.
- `import main` smoke passed.
- Navigation module import smoke passed.
- `python -m pytest -p no:cacheprovider tests -q` passed with 109 tests.
- `main.py` reduced from 1,649 lines to 1,551 lines.
- Relaunch helper preserves the real `main.py` entry path after moving out of `main.py`.

### Phase 3 - Runtime Preferences and Feature Flags
Status: complete

Target module:
- `src\blite_v6\app\runtime_features.py`

Extract:
- Theme preference decisions.
- AI setting normalization.
- Feature visibility decisions.
- Sidebar/nav row visibility data preparation.

Keep in `main.py`:
- Direct widget mutation and app object assignment.

Tests:
- Missing/invalid settings fallback safely.
- AI enabled/disabled state.
- Feature visibility rules for navigation rows.

Verification:
- Added `tests\test_main_runtime_features.py`.
- `main.py` and `runtime_features.py` syntax compile passed.
- Focused Phase 1/2/3 app tests passed with 16 tests.
- `import main` smoke passed.
- Navigation module import smoke passed.
- `python -m pytest -p no:cacheprovider tests -q` passed with 115 tests.
- Direct widget mutation, AI controller mutation, frame destruction, and page switching remain in `main.py`.

### Phase 4 - Shell Build Decomposition
Status: complete

Target modules:
- `src\blite_v6\app\app_shell.py`
- `src\blite_v6\app\shell_sections.py`

Extract:
- Shell layout specs.
- Sidebar shell metrics and section view specs.
- Draggable sidebar divider setup helpers.
- Button metadata and icon/text decisions.

Keep in `main.py`:
- `SalonApp._build` as the coordinator.
- Existing widget attribute names used by other methods.

Tests:
- UI spec smoke using lightweight fake widgets where possible.
- Navigation button metadata stability.
- No removal of expected `SalonApp` attributes.

Verification:
- Added `src\blite_v6\app\app_shell.py`.
- Added `src\blite_v6\app\shell_sections.py`.
- Added `tests\test_main_shell_specs.py`.
- `main.py`, `app_shell.py`, and `shell_sections.py` syntax compile passed.
- Focused app-shell tests passed with 22 tests.
- `import main` smoke passed.
- Navigation module import smoke passed.
- `python -m pytest -p no:cacheprovider tests -q` passed with 121 tests.
- `SalonApp._build` remains the Tk widget creation coordinator.
- Direct topbar button creation remains in `main.py`; only the button specs are extracted in this phase.

### Phase 5 - Navigation and Lazy Module Loading
Status: complete

Target module:
- `src\blite_v6\app\navigation.py`

Extract:
- Module registry preparation.
- Lazy module import decisions.
- Frame cache decisions.
- Page switch sequence planning.
- Restore-visible-page decision logic.

Keep in `main.py`:
- Actual Tk frame creation, `pack`, `pack_forget`, and widget side effects.

Tests:
- Module map covers all navigation keys.
- Access-denied paths do not instantiate frames.
- Billing page loads the current V6 `billing.py`.
- AI tab special case is preserved.

Verification:
- Added `src\blite_v6\app\navigation.py`.
- Added `tests\test_main_navigation.py`.
- `main.py` and `navigation.py` syntax compile passed.
- Focused app navigation tests passed with 28 tests.
- `import main` smoke passed.
- Navigation module import smoke passed.
- `python -m pytest -p no:cacheprovider tests -q` passed with 127 tests.
- Actual Tk frame creation, error placeholders, frame placement, nav button mutation, and refresh side effects remain in `main.py`.
- Billing page remains mapped to the current V6 root `billing.py`.

### Phase 6 - Startup Splash, Placeholder, and Animation
Status: complete

Target module:
- `src\blite_v6\app\startup_ui.py`

Extract:
- Splash state decisions.
- Loading text sequence.
- Startup placeholder state.
- Animation timing/spec decisions.

Keep in `main.py`:
- Direct Tk widget creation and media playback side effects until final smoke.

Tests:
- Animation disabled fallback.
- Splash completion callback selection.
- Placeholder specs do not require real media files.

Verification:
- Added `src\blite_v6\app\startup_ui.py`.
- Added `tests\test_main_startup_ui.py`.
- `main.py` and `startup_ui.py` syntax compile passed.
- Focused Phase 1-6 app tests passed with 33 tests.
- `import main` smoke passed.
- Navigation module import smoke passed.
- `python -m pytest -p no:cacheprovider tests -q` passed with 132 tests.
- Direct Tk widget creation, media playback, `PhotoImage`, and `after` scheduling remain in `main.py`.

### Phase 7 - Session, Events, Notifications, and Admin
Status: complete

Target modules:
- `src\blite_v6\app\session_security.py`
- `src\blite_v6\app\app_events.py`

Extract:
- Session timeout calculations.
- Root `after` id normalization.
- Appointment reminder schedule handling.
- Notification count/button view decisions.
- Admin access decision flow.
- Bill-saved refresh event planning.
- Logout username extraction.

Keep in `main.py`:
- Message boxes, actual window destruction, `after` callbacks, and Toplevel creation.

Tests:
- Timeout minutes fallback.
- Activity reset logic.
- Notification count display rules.
- Appointment reminder thresholds.
- Bill-saved route refresh calls.

Verification:
- Added `src\blite_v6\app\session_security.py`.
- Added `src\blite_v6\app\app_events.py`.
- Added `tests\test_main_session_events.py`.
- `main.py`, `session_security.py`, and `app_events.py` syntax compile passed.
- Focused Phase 1-7 app tests passed with 39 tests.
- `import main` smoke passed.
- Navigation module import smoke passed.
- `python -m pytest -p no:cacheprovider tests -q` passed with 138 tests.
- Message boxes, attendance marking, scheduler calls, popup creation, admin window creation, and root destruction remain in `main.py`.
- Appointment reminder scheduling now uses enumerate-based staggering, preserving stagger behavior even when duplicate appointment objects are returned.

### Phase 8 - Final Integration and Manual Smoke Gate
Status: complete

Deliverables:
- `main.py` reduced to startup and `SalonApp` coordination wrappers.
- All startup dependencies required for the V6 app copied.
- Lazy modules required for manual smoke copied in controlled batches.
- Final docs and migration ledger updated.
- Final report created at `docs\PHASE8_MAIN_FINAL_INTEGRATION_REPORT.md`.
- Manual live smoke checklist prepared.

Automated verification:
- AST parse for edited files.
- Full available V6 pytest suite.
- Import smoke for `main.py` where GUI environment permits.
- No cache or bytecode files left in V6.
- V5.6 git status remains clean.
- `main.py` and `billing.py` syntax compile passed.
- `tests\test_main_final_integration_smoke.py` passed with 3 tests.
- `python -m pytest -p no:cacheprovider tests -q` passed with 141 tests.

Manual smoke checklist:
- App starts from V6 `main.py`.
- Login succeeds with expected V5.6-compatible flow.
- Billing page opens.
- Service bill save.
- Product bill save.
- Barcode entry.
- Discount, offers, coupons, redeem, and loyalty points.
- Save, PDF, print, and WhatsApp paths.
- Duplicate-save guard.
- Navigation to each copied page.
- Logout, switch user, inactivity timeout, restart/shutdown paths.

## Recommended Next Action

Phase 0 dependency gate is complete.

Next safe action:
1. Run live V6 manual smoke from `main.py`.
2. Use `docs\PHASE8_MAIN_FINAL_INTEGRATION_REPORT.md` as the checklist.
3. Fix only confirmed manual-smoke bugs.
4. After manual smoke passes, commit and publish the V6 checkpoint.
