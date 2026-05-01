# Salon Settings.py Split Master Blueprint

Project: B-Lite management_Billing_V6.0
Source under work: salon_settings.py
Stable source rule: do not mutate V5.6. All split work happens in V6 only.

## Goal

Shrink `salon_settings.py` safely without changing current app behavior. Settings is a high-risk module because it controls shop identity, theme, billing defaults, GST, print layout, security, preferences, notifications, backup, AI, WhatsApp API, multibranch, licensing, and update/about diagnostics.

The split must make settings maintainable while preserving the stable app startup and existing settings file compatibility. No feature expansion is allowed in this split unless it directly fixes a stability bug or protects an existing workflow.

## Audit Summary

- Current size: about 103 KB and 1,967 lines.
- Public entry points:
  - `get_settings()`
  - `save_settings(data)`
  - `apply_theme(theme_key)`
  - `get_current_theme()`
  - `feature_enabled(feature_name, settings=None)`
  - `setup_windows_startup(enable)`
  - `SettingsFrame`
- Current mixed responsibilities:
  - settings defaults, JSON persistence, file-mtime cache
  - theme registry, legacy theme mapping, runtime color mutation
  - Windows startup registry behavior
  - notebook tab creation, lazy tab loading, optional feature tabs
  - reusable Tk widgets and settings context menus
  - Shop Info, Theme, Bill/GST, Print/Bill, Security, Preferences, Notifications
  - Advanced Features, WhatsApp API, Multibranch, AI Assistant
  - Backup, Licensing, About, update diagnostics
- Current test status:
  - Dedicated settings tests now exist for core/theme, startup, tab specs, and Bill/GST + print helper extraction.
  - Continue adding focused tests around pure helpers before extracting UI-heavy code.

## Non-Negotiable Rules

- Keep `salon_settings.py` import-compatible throughout the split.
- Keep `SettingsFrame` as the public UI entry point until final integration.
- Preserve `salon_settings.json` keys, defaults, and backward compatibility.
- Do not change billing/GST/print/security defaults silently.
- Do not expose secrets in UI, logs, tests, or saved JSON.
- Do not change licensing behavior in this split; licensing production ceremony remains a separate final phase.
- Do not use broad UI rewrites while extracting helpers.
- Each phase must leave the app importable and settings page openable.
- Every extracted pure helper needs focused tests.
- Manual smoke is required after any phase touching UI tab build or save behavior.

## Target Module Layout

Planned package:

`src/blite_v6/settings/`

- `core.py`
  - defaults merge, cache invalidation, load/save wrappers, feature flag helper
- `themes.py`
  - theme registry, legacy map, theme apply/current helpers
- `startup.py`
  - Windows startup shortcut/registry behavior
- `tab_specs.py`
  - tab definitions, optional tab visibility, feature status view data
- `form_widgets.py`
  - small reusable widget builders where safe
- `bill_gst.py`
  - Bill/GST view model, validation, save payload preparation
- `print_settings.py`
  - print preview model, print setting validation and save payload
- `security_settings.py`
  - password/security validation helpers, visibility state helpers
- `preferences.py`
  - preferences/session/notification payload helpers
- `advanced_features.py`
  - WhatsApp API and multibranch config view models and validation wrappers
- `ai_settings.py`
  - AI config persistence helpers and secure-store interactions
- `backup_license_about.py`
  - backup tab view helpers, license/about diagnostic view models
- `context_menus.py`
  - settings context-menu callback/view helpers

UI-heavy Tk layout can remain in `SettingsFrame` until late phases. The first extractions should be pure data builders and validators.

## Phase Plan

### Phase 0 - Audit and Guardrails

Status: complete for blueprint.

Actions:
- Identify file size and public entry points.
- Map current method boundaries and responsibility groups.
- Confirm no dedicated settings tests exist.

Gate:
- No behavior changes.
- Blueprint created before implementation.

### Phase 1 - Core Settings Persistence and Theme Helpers

Status: complete.

Target:
- Extract `DEFAULTS`, cache invalidation, `get_settings`, `save_settings`, `feature_enabled` into `src/blite_v6/settings/core.py`.
- Extract `THEMES`, `LEGACY_THEME_MAP`, and `apply_theme` into `src/blite_v6/settings/themes.py`.
- Keep `get_current_theme` with the core settings loader because it depends on `get_settings()`.
- Keep compatibility imports/aliases in `salon_settings.py`.

Why first:
- Lowest UI risk.
- Pure or near-pure behavior can be tested without opening Tkinter.
- Many modules depend on these public functions.

Gate:
- Tests for default merge, unknown keys preservation, cache invalidation, legacy theme mapping, invalid theme fallback.
- `python -m py_compile salon_settings.py src\blite_v6\settings\core.py src\blite_v6\settings\themes.py`
- Focused settings tests pass.

Result:
- Created `src/blite_v6/settings/core.py`.
- Created `src/blite_v6/settings/themes.py`.
- Created `src/blite_v6/settings/__init__.py`.
- Kept `salon_settings.py` public compatibility imports for:
  - `DEFAULTS`
  - `F_SETTINGS`
  - `_invalidate_settings_cache`
  - `get_settings`
  - `save_settings`
  - `get_current_theme`
  - `feature_enabled`
  - `THEMES`
  - `LEGACY_THEME_MAP`
  - `apply_theme`
- Added focused tests in `tests/test_settings_core_theme.py`.
- Current `salon_settings.py` size after Phase 1:
  - 97,208 bytes
  - 1,817 lines

### Phase 2 - Startup Runtime Utility

Status: complete.

Target:
- Extract `setup_windows_startup(enable)` to `src/blite_v6/settings/startup.py`.
- Keep compatibility alias in `salon_settings.py`.

Risk:
- Windows-specific behavior and startup entry paths.

Gate:
- Tests mock Windows paths/registry or shell-link behavior where practical.
- No real registry writes during tests.

Result:
- Created `src/blite_v6/settings/startup.py`.
- Moved Windows Run-key setup/delete behavior out of `salon_settings.py`.
- Preserved the public `salon_settings.setup_windows_startup` import.
- Added `default_main_script_path()` to preserve the project-root `main.py` startup target after module extraction.
- Added `build_startup_command()` for testable command construction.
- Added focused tests in `tests/test_settings_startup.py`.
- Current `salon_settings.py` size after Phase 2:
  - 96,347 bytes
  - 1,793 lines.

### Phase 3 - Tab Specs and Lazy Tab Coordination

Status: complete.

Target:
- Extract `_settings_tab_defs`, optional tab feature visibility rules, and feature-status display data into `tab_specs.py`.
- Keep `SettingsFrame` responsible for actual Notebook creation.

Risk:
- Missing tabs, wrong order, or tab not loading.

Gate:
- Tests for tab list in mixed/product/service modes and feature flag combinations.
- Manual smoke: Settings opens, each tab can be selected, no app close.

Result:
- Created `src/blite_v6/settings/tab_specs.py`.
- Extracted settings tab order and AI tab insertion decision.
- Extracted optional AI tab sync plan data.
- Extracted Advanced Features status-card data builder.
- Kept actual `ttk.Notebook` creation, tab add/remove/forget/select, icon assignment, and lazy tab rendering in `SettingsFrame`.
- Added focused tests in `tests/test_settings_tab_specs.py`.
- Current `salon_settings.py` size after Phase 3:
  - 95,327 bytes
  - 1,772 lines.

### Phase 4 - Bill/GST and Print Settings Models

Status: complete.

Target:
- Extract Bill/GST payload preparation and validation into `bill_gst.py`.
- Extract print preview data and existing print width/font save behavior into `print_settings.py`.
- Keep Tk widgets inside `SettingsFrame` during this phase.

Risk:
- Billing mode, GST type/rate, footer, print width, and paper size affect invoices.

Gate:
- Tests for GST setting payload, billing mode values, footer preservation, print char width, font size boundaries.
- Manual smoke: change theme, change billing mode, save Bill/GST, open Billing and verify mode behavior.
- Manual smoke: change print settings and verify bill preview/print fallback still works.

Result:
- Added `src/blite_v6/settings/bill_gst.py` for Bill/GST payload building, GST-rate fallback parsing, and saved-message text.
- Added `src/blite_v6/settings/print_settings.py` for print payload building, width fallback parsing, saved-message text, and preview text generation.
- `salon_settings.py` still owns the actual Tk widgets and save button bindings, but delegates save/preview models to the extracted helpers.
- Existing behavior preserved: invalid GST rate falls back to 18.0 and invalid print width falls back to 48, matching the previous inline behavior.
- Added `tests/test_settings_bill_print.py`.
- Current `salon_settings.py` size after Phase 4:
  - 94,133 bytes
  - 1,941 physical lines
- Verification:
  - `py_compile` passed with bundled Python for `salon_settings.py` and all extracted settings helper modules.
  - Direct helper smoke passed with test `APPDATA`, including compatibility import from `salon_settings`.
  - Full `pytest` could not be rerun in this resumed environment because `python`/`py` are not on PATH, bundled Python has no `pytest`, and the existing `.venv-build` launcher points to a missing Python install.
- Manual smoke still required: Bill/GST save, Billing mode behavior, Print/Bill save, PDF/print fallback.

### Phase 5 - Security, Preferences, and Notifications

Status: complete.

Target:
- Extract password-change validation, security save payload, session timeout validation, and notification payload helpers.
- Keep actual password verification call boundary explicit.

Risk:
- Admin lockout, auto logout, password-required billing flow, dismissed notifications.

Gate:
- Tests for password mismatch, empty password rejection, session timeout numeric validation, notification popup time boundaries.
- Manual smoke: Security tab opens, password fields toggle, Preferences save, Notifications save/reset dismissed.

Result:
- Added `src/blite_v6/settings/security_settings.py` for current-user normalization, password visibility state, new-password validation, session-timeout normalization, and security payload building.
- Added `src/blite_v6/settings/preferences.py` for preferences payload building and startup-warning saved-message text.
- Added `src/blite_v6/settings/notifications.py` for notification payload building, popup-time boundary normalization, dismissed-count label text, and dismissed reset payload.
- `salon_settings.py` keeps password verification, password hashing, user persistence, Windows startup registry call, runtime preference application, and all Tk messageboxes in the existing boundary.
- Added `tests/test_settings_security_prefs_notifications.py`.
- Current `salon_settings.py` size after Phase 5:
  - 94,247 bytes
  - 1,954 physical lines
- Verification:
  - `py_compile` passed with bundled Python for `salon_settings.py`, Phase 5 helper modules, and the new test file.
  - Direct Phase 5 helper smoke passed with test `APPDATA`, including compatibility imports from `salon_settings`.
  - Full `pytest` could not be rerun in this resumed environment because `python`/`py` are not on PATH, bundled Python has no `pytest`, and the existing `.venv-build` launcher points to a missing Python install.
- Manual smoke still required: Security tab opens, password visibility toggles, invalid password messages display, Preferences save, Notifications save/reset dismissed.

### Phase 6 - Advanced Features, WhatsApp API, Multibranch, AI

Status: complete.

Target:
- Extract WhatsApp API provider config validation, multibranch config validation, AI config payload, and secure-store wrappers where safe.
- Do not change provider behavior or secrets.

Risk:
- Secret leakage, broken WhatsApp API test, broken AI key storage, broken multibranch connection test.

Gate:
- Tests use fake secure-store/provider objects.
- No API key/secret written to test output.
- Manual smoke: Advanced Features tab opens, AI tab opens, toggles save without crash.

Result:
- Added `src/blite_v6/settings/advanced_integrations.py` for WhatsApp API config/message helpers, Multi-Branch config/status helpers, advanced feature payload building, AI config/status/message helpers, and AI model constants.
- `salon_settings.py` still owns secure-store calls, keyring warnings, provider creation, Multi-Branch manager calls, runtime feature application, and all Tk messageboxes.
- Secret safety preserved: helper payloads keep `api_key` as an empty string and use `storage` metadata only.
- Added `tests/test_settings_advanced_integrations.py`.
- Current `salon_settings.py` size after Phase 6:
  - 92,973 bytes
  - 1,943 physical lines
- Verification:
  - `py_compile` passed with bundled Python for `salon_settings.py`, `advanced_integrations.py`, and the new test file.
  - Direct Phase 6 test functions passed with test `APPDATA`, including compatibility imports from `salon_settings`.
  - Full `pytest` could not be rerun in this resumed environment because `python`/`py` are not on PATH, bundled Python has no `pytest`, and the existing `.venv-build` launcher points to a missing Python install.
- Manual smoke still required: Advanced Features tab opens, provider validation/test buttons do not crash, Multi-Branch test status updates, AI tab opens, AI save/status refresh works.

### Phase 7 - Backup, Licensing, About, Context Menus

Status: complete.

Target:
- Extract backup action view helpers, license tab view model, about diagnostics rows, and context-menu callback lists.
- Keep `open_activation_dialog` and license manager calls in stable boundaries.

Risk:
- Licensing UI confusion, update diagnostics, context menu copy actions.

Gate:
- Tests for license status display mapping and about diagnostic row formatting.
- Manual smoke: Backup, Licensing, About tabs open; context menus do not crash.

Result:
- Added `src/blite_v6/settings/backup_license_about.py` for backup schedule/info text, activity count text, license status rows/reminder note, About version rows, VC++ runtime status text, update manifest payload/message helpers, and Settings context-menu data builders.
- `salon_settings.py` still owns backup config file writes, scheduler start/stop, activity-log viewer launch, license manager status fetch, activation dialog launch, update checker threading, browser opening, context-menu renderer calls, and callback registration.
- Licensing behavior unchanged; production licensing ceremony remains outside this split.
- Added `tests/test_settings_backup_license_about.py`.
- Current `salon_settings.py` size after Phase 7:
  - 91,521 bytes
  - 1,932 physical lines
- Verification:
  - `py_compile` passed with bundled Python for `salon_settings.py`, `backup_license_about.py`, and the new test file.
  - Direct Phase 7 test functions passed with test `APPDATA`, including compatibility imports from `salon_settings`.
  - Full `pytest` could not be rerun in this resumed environment because `python`/`py` are not on PATH, bundled Python has no `pytest`, and the existing `.venv-build` launcher points to a missing Python install.
- Manual smoke still required: Backup tab opens/saves schedule, Licensing tab opens/refreshes, About tab opens/checks VC++/manifest URL, right-click context menus do not crash.

### Phase 8 - Final Integration Shrink and Manual Smoke Gate

Status: complete.

Target:
- Remove extracted code from `salon_settings.py` after wrappers are proven.
- Keep only `SettingsFrame`, small UI wiring, and compatibility imports.
- Update migration ledger and known risks.

Gate:
- `python -m pytest -q` if temp-dir permissions allow.
- At minimum: settings-focused tests, billing WhatsApp tests, report split tests, and py_compile for touched modules.
- Manual smoke:
  - App starts from `main.py`.
  - Settings opens.
  - Every settings tab opens.
  - Theme change does not close app.
  - Bill/GST save does not break Billing.
  - Print/Bill save does not show misleading PDF message.
  - Security tab opens without missing-file errors.
  - Licensing tab opens but production license ceremony remains pending.

Result:
- Removed unreachable duplicate Security and Advanced tab build code after their external renderer returns.
- Delegated AI tab rendering to `ai_settings_tab.render_ai_settings_tab(self)`.
- Added final report: `docs/SALON_SETTINGS_PHASE8_FINAL_INTEGRATION_REPORT.md`.
- Current `salon_settings.py` size after Phase 8:
  - 79,338 bytes
  - 1,699 physical lines
- Verification:
  - `py_compile` passed for `salon_settings.py`, `security_tab.py`, `advanced_tab.py`, and `ai_settings_tab.py`.
  - Import smoke passed for the same modules.
  - Settings direct no-fixture tests passed: 33 passed, 6 pytest-fixture tests skipped because pytest is unavailable in this resumed environment.
  - Full `pytest` could not be rerun for the same environment reason documented in Phases 4-7.
- Manual smoke checklist is in `docs/SALON_SETTINGS_PHASE8_FINAL_INTEGRATION_REPORT.md`.

## Recommended Next Phase

Start with Phase 1 only.

Do not begin with UI tab extraction. The safest first step is to extract core settings and theme helpers because they are mostly pure, can be tested, and keep the public `salon_settings.py` API stable.

## Known Risks Before Starting

- `salon_settings.py` currently contains mojibake in comments/header from older encoding drift. Do not rewrite comments wholesale during split.
- Settings affects nearly every page through `get_settings()`, so cache behavior must be preserved exactly.
- Theme changes mutate global `utils.C`; tests must isolate this side effect.
- Secure-store and licensing logic must not be moved in a way that exposes secrets or private keys.
- User may be testing installed EXE; source fixes require source run or rebuild to appear.
