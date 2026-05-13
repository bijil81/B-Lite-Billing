# Migration Ledger

## 2026-05-04 - Service master runtime migration

Scope:
- Move service master runtime storage from legacy `services_db.json` blob semantics to dedicated SQLite tables.
- Keep JSON only as optional seed/import-export format.

Files added:
- `repositories/services_repo.py`
- `services_v5/service_master_service.py`

Files updated:
- `adapters/sqlite_legacy_bridge.py`
- `utils.py`
- `product_catalog_adapter.py`
- `adapters/product_catalog_adapter.py`
- `inventory.py`

Behavior before:
- `F_SERVICES` logical payload was still treated as the live source for services/products.
- Runtime could continue to depend on the legacy SQLite blob key `legacy_services_db_json`.
- UI/import messages still described the product source as `services_db.json`.

Behavior after:
- Services load/save now route through `v5_services` via `ServiceMasterService`.
- Legacy `services_db.json` load/save is synthesized from relational runtime data for compatibility only.
- One-time migration imports any old `legacy_services_db_json` blob into `v5_services` and inventory, then clears the blob key.
- `init_services_db()` seeds relational tables only when both services and inventory are empty.
- `init_sample_data()` now builds its snapshot from relational services and inventory first.
- Inventory import wording now refers to the current product catalog, not a physical JSON file.

Compatibility path kept:
- `load_json(F_SERVICES, ...)` and `save_json(F_SERVICES, ...)` still work for legacy callers, but they now bridge to relational runtime storage.
- `main.py` did not need structural edits; `init_services_db()` remains safe as thin startup wiring.

Verification:
- `py_compile` passed for:
  - `repositories/services_repo.py`
  - `services_v5/service_master_service.py`
  - `adapters/sqlite_legacy_bridge.py`
  - `utils.py`
  - `product_catalog_adapter.py`
  - `adapters/product_catalog_adapter.py`
  - `admin.py`
  - `inventory.py`
  - `billing.py`
- Relational/bridge smoke results:
  - service categories loaded: `17`
  - inventory rows available: `168`
  - `build_item_codes()` count: `246`
  - save/load round-trip through `F_SERVICES`: `OK`
  - old blob key cleared after migration: `OK`

Known follow-up:
- For public/generic builds, `services_db.json` may now be shipped empty and used only as an optional import template.
- Shop-specific delivery can pre-seed SQLite instead of relying on bundled service JSON.

## 2026-05-04 - Printerless print fallback hardening

Scope:
- Avoid confusing Notepad printer prompts on systems without `pywin32`, default printer, or running print spooler.
- Keep `PRINT` usable in printerless/manual-QA environments.

Files updated:
- `billing.py`
- `reports.py`
- `utils.py`

Behavior before:
- `PRINT` tried direct `win32print` raw printing.
- If `win32print` was missing, app wrote a `.txt` file and invoked Windows shell print via Notepad.
- On systems without an installed/reachable printer, Notepad raised a printer-install prompt and QA could not continue cleanly.

Behavior after:
- Billing print now falls back to generated PDF when direct printer printing is unavailable.
- Reports text-preview print now opens a manual text preview file instead of trying shell print.
- Shared text fallback helper no longer auto-invokes Windows shell print.

Verification:
- `py_compile` passed for `billing.py`, `reports.py`, `utils.py`, `print_engine.py`
- Render smoke passed for templates:
  - `thermal_58mm`
  - `thermal_72mm`
  - `thermal_76mm`
  - `thermal_80mm`
  - `thermal_112mm`
  - `a5_halfpage`
  - `a4_standard`
  - `invoice_compact`
  - `invoice_detailed`
