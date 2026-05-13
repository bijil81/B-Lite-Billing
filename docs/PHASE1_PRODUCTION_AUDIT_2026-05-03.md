# Phase 1 Production Audit (2026-05-03)

## Scope Completed
- Reviewed current status docs (`FINAL_PROJECT_STATUS`, `FINAL_AUDIT_REPORT_V6`, archive audit docs).
- Inspected core runtime/storage modules: `main.py`, `utils.py`, `db.py`, `db_core/*`, `reports.py`, `billing.py`, `inventory.py`, `redeem_codes.py`.
- Implemented SQLite migration bridge for:
  - `redeem_codes.json`
  - `services_db.json`
  - `invoice_counter.json`
- Ran static compile checks on changed and critical modules.
- Ran runtime smoke scripts for bridge read/write and redeem lifecycle.

## Code Changes Done in This Phase
1. Added SQLite bridge adapter:
   - `adapters/sqlite_legacy_bridge.py`
   - Routes selected legacy JSON paths to v5 SQLite storage.
2. Wired `utils.load_json/save_json` to bridge before kv-store fallback.
3. Fixed sample data seeding guards to avoid reset loops in pure-SQLite mode:
   - Replaced file-existence checks with `load_json(...)` emptiness checks.
4. Extended redeem schema compatibility:
   - Added additive columns `note`, `used_on` for `v5_redeem_codes` in schema manager.
   - Added same columns in base `sql/v5_schema.sql`.

## Verification Executed
- `py_compile` passed for:
  - `adapters/sqlite_legacy_bridge.py`
  - `utils.py`
  - `db_core/schema_manager.py`
  - `redeem_codes.py`
  - `billing.py`
  - `main.py`
  - `reports.py`
  - `inventory.py`
  - `closing_report.py`
- Smoke checks passed (with controlled APPDATA):
  - save/load for services/invoice/redeem bridge.
  - redeem create -> validate -> apply -> revalidate flow.
  - schema presence of `v5_redeem_codes.note` and `v5_redeem_codes.used_on`.

## Critical Findings (Current)
1. EXE build spec currently excludes chart dependencies:
   - `WhiteLabelApp.spec` excludes `matplotlib` and `numpy` while reports/dashboard import and use them.
   - This can break Reports->Charts and dashboard analytics in packaged build.
2. Runtime environment sensitivity at data-dir bootstrap:
   - `_init_dirs()` is strict about non-folder collisions for required paths.
   - In this audit runtime, default APPDATA path produced a `Bills` path-type conflict during import.
3. Full automated test gate not executed:
   - `pytest` not available in current runtime (`No module named pytest`), so only compile/smoke were run.

## Production Readiness (Phase 1 Position)
- **Core direction improved**: the requested 3 JSON targets now have SQLite-first routing in runtime.
- **Not yet final-production signoff** because:
  - Packaging dependency mismatch for chart modules is still open.
  - Full pytest gate has not been executed in this environment.
  - Installed-EXE end-to-end smoke (installer + post-install workflows) pending.

## Recommended Next Phase (Phase 2)
1. Fix `WhiteLabelApp.spec` packaging policy for chart dependencies.
2. Run full pytest in the same interpreter/environment used for build.
3. Run source manual regression checklist:
   - Billing, Inventory, Reports, Closing Report, Settings.
4. Rebuild EXE and run installed build smoke checklist.
