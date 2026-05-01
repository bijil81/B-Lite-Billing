# Next Update QA Blueprint

Last updated: 2026-04-29
Scope: Production QA findings handoff for the next refactor/update branch

## Current Release Position

V6 source tests are currently green after the split/runtime-dependency/QA-fix port, but the build is not yet a release candidate.

Release blockers before a V6 EXE handoff:
- Manual live app smoke from `main.py`.
- Existing customer DB migration dry-run on a staging copy.
- Real `dist/` artifact inspection after build.
- Licensing activation path must be finalized because the client has moved to verify-only licensing.

Do not ship V6 with the verify-only licensing client until either:
- Phase L1 creates and tests the external V6 admin signer/token generator, or
- the licensing crypto cutover is explicitly deferred and the previous V5.6-compatible licensing path is restored for this release.

## Fixes Already Applied

### Billing and Redeem Code

- Phone-bound redeem codes now require a matching billing customer phone.
- Phone-bound redeem codes are rejected when billing phone is blank.
- Legacy non-v5 redeem apply path now passes `customer_phone`.
- V5 billing payload now carries `redeem_discount` separately from total discount.
- V5 redeem transaction stores the redeem-only discount amount.
- Offer/redeem discount bases now subtract manual, membership, and points discounts in order.

Primary files:
- `redeem_codes.py`
- `billing.py`
- `billing_logic.py`
- `services_v5/billing_service.py`

### Validation

- Invoice validator now enforces:
  - at least one item
  - at least one payment
  - non-negative gross/discount/tax/net totals
  - item line total equals qty * unit price within 0.01
  - net total equals gross - discount + tax within 0.01
  - payment total equals net total within 0.01
- Customer validator now enforces existing 10-digit phone validation.

Primary files:
- `validators/billing_validator.py`
- `validators/customer_validator.py`

### Schema for New Databases

- New database schema now includes CHECK constraints for:
  - `v5_inventory_items.current_qty`
  - `v5_inventory_items.min_qty`
  - `v5_inventory_items.cost_price`
  - `v5_inventory_items.sale_price`
  - `v5_invoices.gross_total`
  - `v5_invoices.discount_total`
  - `v5_invoices.tax_total`
  - `v5_invoices.net_total`
  - `v5_invoice_items.qty`
  - `v5_invoice_items.unit_price`
  - `v5_invoice_items.line_total`
  - `v5_invoice_items.discount_amount`
  - `v5_payments.amount`

Important limitation: this only affects newly created tables. Existing SQLite tables need a rebuild/copy migration.

Primary file:
- `sql/v5_schema.sql`

### QA Tests

- Phase-2 QA tests are present:
  - `tests/test_billing.py`
  - `tests/test_database.py`
  - `tests/test_validation.py`
- CI markers are configured:
  - `pytest.ini`
  - `.github/workflows/qa-critical.yml`
- Latest verification:
  - `python -m pytest -q` -> 86 passed
  - `python -m pytest -m critical -q` -> 9 passed

## Deferred Findings For Next Update

## V6 Hardening Progress - 2026-04-29

Implemented in the V6 workspace only:

- Added `db_core/constraint_migration.py` with explicit dry-run and backup-first apply behavior for existing SQLite tables that need new CHECK constraints.
- Added non-negative CHECK constraints for `v5_product_variants.sale_price`, `cost_price`, `stock_qty`, and `reorder_level` in `sql/v5_product_variant_schema.sql`.
- Replaced client-side license HMAC/keygen model with verify-only signed-token validation in `licensing/crypto.py`.
- Removed license record/storage HMAC signing secrets from the V6 client path; old HMAC-style keys now return `legacy_key_reactivation_required`.
- Added packaging hygiene tests for `WhiteLabelApp.spec` exclusions and build validation presence.
- Replaced Google Drive token write path with `gdrive_token.json` serialization and one-time migration from `gdrive_token.pickle`.
- Ported the earlier V5.6 QA fixes into the V6 split architecture:
  - redeem phone enforcement including blank billing phone block
  - customer 10-digit phone validation
  - invoice accounting/payment invariants
  - redeem-only discount persistence
  - discount base order: manual, membership, points, offer, redeem
- Copied missing app runtime dependencies from V5.6 needed by Settings/security/advanced/print/update/WhatsApp/support tabs.

Verification so far:

- `python -m pytest -p no:cacheprovider tests\test_schema_constraint_migration.py tests\test_licensing_security.py tests\test_packaging_hygiene.py tests\test_google_backup_tokens.py -q` -> 10 passed.
- `python -m pytest -q` -> 157 passed.

Important release note:

- The existing DB migration helper is intentionally not auto-run at startup. A staging dry-run and backup/apply command must be executed manually before enabling it in any production workflow.
- The licensing change requires a production key ceremony and admin/keygen tooling outside the client package before live license issuance. The V6 client now has verify-only behavior, but real production public key values must be finalized before release.
- Current V6 activation with old V5 HMAC keys is intentionally not release-ready after this change. Next licensing task is to create the external V6 admin signer/token generator or temporarily defer the licensing crypto cutover.

## Next Phase Definition

### Phase L1 - V6 Licensing Admin Signer and Activation Gate

Goal:
- Make V6 activation usable without putting private signing secrets inside the app or EXE.
- Keep the production client verify-only.
- Keep admin/private-key tooling outside the PyInstaller bundle.

Why this is next:
- Billing/main split tests pass and missing runtime files have been copied.
- The current V6 client rejects old V5 HMAC keys as `legacy_key_reactivation_required`.
- Without a V6 signer, a packaged V6 app cannot be activated with new production licenses.

Decision required inside Phase L1:
- Preferred path: create a V6 admin-only signer/token generator and use new V6 signed activation/trial-extension tokens.
- Temporary fallback path: defer verify-only licensing for the first V6 test EXE and restore V5.6-compatible licensing until the signer is ready.
- The preferred path is safer for international-standard licensing, but it must be tested end-to-end before release.

Scope:
- Create or update `licensing_admin/keygen.py` for V6 signed tokens.
- Keep private key material outside `licensing/`, outside `WhiteLabelApp.spec` datas, and outside `dist/`.
- Add a documented key ceremony:
  - generate private/public key pair
  - store private key only in admin/offline tooling
  - copy public verification material into the client
  - record fingerprint in release notes
- Support activation and trial-extension token payloads:
  - `kind`
  - `device_id`
  - `install_id`
  - `days` for trial extension
  - issued-at timestamp and optional expiry if needed
- Add admin signer tests and client verification tests.
- Add packaging tests that fail if private keys, `licensing_admin`, tests, or dev artifacts are bundled.

Out of scope:
- No online licensing server in this phase.
- No silent migration of old V5 license keys.
- No private key in source-controlled production client files.

Acceptance criteria:
- Admin tool can generate a V6 activation token for a device/install pair.
- V6 client can activate offline using that token.
- V6 client can apply a signed trial-extension token.
- Invalid/tampered/wrong-device tokens are rejected.
- Production client files contain no private key or signing function.
- `WhiteLabelApp.spec` excludes `licensing_admin` and private key files.
- `python -m pytest -q` passes.

Phase L1 implementation status:
- Done: `licensing_admin/keygen.py` can generate admin RSA keys, install the public key into `licensing/public_key.py`, and issue BLV2 activation/trial-extension tokens.
- Done: V6 client verifies tokens with public-key material only; old V5.6 HMAC keys remain rejected.
- Done: `WhiteLabelApp.spec` excludes `licensing_admin`; focused packaging hygiene test updated.
- Done: user-facing admin note added at `HOW_TO_ACTIVATE_LICENSE_V6.md`.
- Pending release gate: first real production key ceremony, EXE rebuild, dist artifact inspection, and manual source/EXE activation smoke.
- Test note: focused py_compile/direct licensing tests passed in current environment; full pytest is pending because pytest is not installed in the bundled runtime.

Release gate after Phase L1:
- Manual license smoke:
  - open V6 app
  - copy device/install ID from license screen
  - generate activation token with admin tool
  - activate V6 app
  - close/reopen and confirm activated state persists
  - repeat trial-extension flow on a fresh test install
- Build artifact smoke:
  - build EXE
  - inspect `dist/` for `licensing_admin`, private keys, tests, pytest, and dev artifacts
  - run activation in the built EXE, not only source mode

## Future Phase Definition - Universal Retail/Grocery Foundation

Detailed blueprint:
- `docs/UNIVERSAL_RETAIL_GROCERY_BLUEPRINT.md`
- `docs/INVENTORY_GROCERY_IMPLEMENTATION_BLUEPRINT.md`

Position:
- Licensing Phase L1 source/EXE activation smoke is now functionally passed on the test machine.
- Broad split work is functionally complete, but wrapper files must stay in place.
- Do not delete or aggressively shrink `billing.py`, `main.py`, `reports.py`, or `salon_settings.py` while grocery work is in progress.
- New retail/grocery logic should be added under focused modules such as `src/blite_v6/inventory_grocery/`.
- Phase G0: Billing Unit Visibility is complete. It only exposes the already implemented loose-quantity behavior in the UI.
- Next implementation path starts with Inventory/Grocery G0/G1, not a broad wrapper shrink.

Required later phases:
- G0: Safety baseline and split-gate closure.
- G1: Pure product/unit domain helpers.
- G2: Additive schema extension with dry-run/backup-first behavior.
- G3: Universal product master UI.
- G4: Bulk product import wizard.
- G5: Billing loose quantity full integration.
- G6: Vendor/supplier master.
- G7: Purchase entry and stock movement audit.
- G8: Product-wise GST calculation and bill/report output.
- G9: Below-cost guard everywhere.
- G10: Source and EXE manual smoke gate.
- B0: Branding/build flag to ship either sample catalog or clean empty catalog.

Current V6 inventory/catalog notes:
- Admin Products tab already has JSON/Excel product import, but it is a catalog import and not a purchase-bill workflow.
- Current import paths do not fully separate cost price from sale price in the UI/flow; they often default `cost_price` to the same value as `sale_price`.
- Inventory has a shallow `Add (Purchase)` stock adjustment, not vendor-backed purchase invoices.
- Below-cost sales are not currently guarded. Future retail work must warn/block by default when sale price is lower than purchase/cost price, with an explicit `Continue anyway` override and audit note.

Risk note:
- G1-G5 affect financial correctness and stock accounting. They must not be rushed into the stable manual-smoke branch without focused tests and migration rules.

## Future Phase Definition - Dashboard Graphical Mode

Position:
- Do not add this before the current EXE build/license smoke gate.
- Keep the current dashboard as the default stable view.
- Add this as a later user-satisfaction/UI phase after core billing, licensing, and packaging gates are clean.

Suggested scope:
- Add Settings > Preferences switch for `dashboard_view`: `classic` / `graphical`.
- Build graphical dashboard as a separate read-only helper/module, not inside the existing dashboard logic.
- Use lightweight Tkinter/Canvas charts first to avoid packaging new chart dependencies.
- Suggested visuals:
  - daily sales trend
  - monthly sales bar chart
  - service vs product split
  - payment mode split
  - low-stock visual summary
  - recent bills timeline

Safety rules:
- Read-only analytics only; do not write billing/inventory data from dashboard charts.
- Must handle empty data without errors.
- Must support dark/light themes and responsive window sizes.
- Must keep classic dashboard fallback available.

Acceptance criteria:
- Classic dashboard still works.
- Graphical dashboard loads with empty and real sales data.
- Settings switch persists and can be changed without restart if practical.
- EXE packaging does not require large new libraries unless explicitly approved.

Recommended next command prompt:

```text
Start Phase L1 - V6 Licensing Admin Signer and Activation Gate.
Work only in V6. Do not edit V5.6.
Read NEXT_UPDATE_QA_BLUEPRINT.md, KNOWN_ISSUES.md, qa_test_matrix.md, and docs/MIGRATION_LEDGER.md first.
Implement a V6 admin-only signer/token generator outside the production client path.
Keep private keys out of licensing/, WhiteLabelApp.spec datas, and dist/.
Add activation and trial-extension tests.
Run python -m pytest -q before handoff.
```

### 1. Existing DB CHECK Constraint Migration

Risk: High.

Problem:
- `CREATE TABLE IF NOT EXISTS` does not add CHECK constraints to existing SQLite tables.
- Existing customer databases can still contain or accept invalid numeric values if tables were created before the schema hardening.

Required approach:
- Add a controlled migration with backup-first behavior.
- For each constrained table, create a new table with CHECK constraints, copy valid data, detect invalid rows, swap tables only after validation, and record migration status.
- Provide dry-run mode that reports blocking rows without changing the DB.
- Do not silently coerce financial values unless explicitly approved.

Suggested files:
- `db_core/schema_manager.py`
- new migration helper under `db_core/` or `migrations/`
- `sql/v5_schema.sql`
- `sql/v5_product_variant_schema.sql`
- tests under `tests/test_database.py` or a new `tests/test_schema_migration.py`

Acceptance criteria:
- Status: Implemented in V6 helper; pending full regression and staging DB trial.
- Existing DB dry-run reports invalid rows clearly.
- Clean existing DB migrates with a backup and preserves data.
- Dirty existing DB blocks safely and leaves original DB unchanged.
- `python -m pytest -q` must pass before release handoff.

### 2. Licensing Asymmetric Verify-Only Model

Risk: High.

Problem:
- Admin tools are excluded from the PyInstaller spec, but client modules still contain HMAC signing secrets.
- This is not a crash risk, but it is a licensing bypass/keygen risk.

Required approach:
- Keep private signing key only in admin/keygen tooling outside the production client package.
- Production client must contain only a public verification key.
- Prefer Ed25519 signatures.
- Maintain a transition plan for old licenses:
  - either support legacy keys with expiry/waiver window
  - or require reactivation with new signed license format
- Verify `WhiteLabelApp.spec`, `BUILD.bat`, and installer outputs do not ship admin tooling or private keys.

Suggested files:
- `licensing/crypto.py`
- `licensing/license_manager.py`
- `licensing/storage.py`
- `licensing_admin/keygen.py`
- `WhiteLabelApp.spec`
- `BUILD.bat`
- tests under `tests/test_transactions_and_security.py` or new `tests/test_licensing_security.py`

Acceptance criteria:
- Status: Client-side verify-only model implemented in V6; production key ceremony/admin signer still pending.
- No production client file contains signing/private secrets.
- Client can verify valid signed licenses offline.
- Client cannot generate licenses.
- Installer artifact inspection confirms no `licensing_admin` package is bundled.
- Phase L1 is complete before any verify-only licensing V6 release.

### 3. Product Variant Schema Constraints

Risk: Medium.

Problem:
- `sql/v5_product_variant_schema.sql` still lacks CHECK constraints for variant money/stock fields.

Required approach:
- Add CHECK constraints for `sale_price`, `cost_price`, `stock_qty`, and `reorder_level` for new DBs.
- Include these tables in the existing DB migration strategy.

Status: Implemented in V6 schema and migration helper; pending full regression.

### 4. Backup/Restore Atomicity

Risk: Medium-High.

Problem:
- Restore can leave mixed live state if file replacement fails mid-way.

Required approach:
- Add rollback manifest or directory-level atomic switch strategy.
- Verify restore from a real backup on staging data.

Suggested files:
- `backup_system.py`
- `scheduled_backup.py`
- restore-related tests if feasible

### 5. Google Credential Token Serialization

Risk: Medium.

Problem:
- `google_backup.py` still stores Google credentials with pickle.

Required approach:
- Replace pickle token persistence with JSON credential serialization using Google credential APIs.
- Provide a one-time migration from old `gdrive_token.pickle` to JSON, then remove or ignore pickle.

Suggested file:
- `google_backup.py`

Status: Implemented in V6 with JSON token persistence and one-time legacy pickle migration; pending full regression.

## Packaging Hygiene Before Release

- Confirm `WhiteLabelApp.spec` excludes:
  - `licensing_admin`
  - tests
  - pytest/dev tooling
- Do not ship or commit generated dev artifacts unless intentionally needed:
  - `node_modules/`
  - `playwright-report/`
  - `test-results/`
  - unnecessary `package*.json`
  - `tests/e2e/` unless frontend/e2e work is intentional

## Recommended Next-Update Task Prompt

Use this prompt for the next agent working on the update:

```text
You are working in the Tkinter salon billing app repo:
G:\chimmu\Bobys_Salon Billing\Bobys Billing V5.6 Development

Goal: implement the next production-hardening update without destabilizing the currently stable EXE path.

Context:
- Code-only QA fixes are already applied for redeem phone enforcement, customer phone validation, invoice accounting invariants, redeem_discount persistence, and billing discount base ordering.
- Current tests pass: `python -m pytest -q` -> 86 passed, `python -m pytest -m critical -q` -> 9 passed.
- Do not undo existing user/Codex/Cursor changes.
- Billing.py is planned for a later split/refactor; keep edits minimal unless the current branch is explicitly the split/refactor branch.

Must do in this next update:
1. Implement controlled migration/dry-run for existing SQLite DBs so CHECK constraints added in schema are applied safely to already-created v5 tables. [V6 implemented; staging run pending]
2. Add constraints and migration coverage for `v5_product_variants` fields: sale_price, cost_price, stock_qty, reorder_level. [V6 implemented]
3. Replace licensing HMAC-secret client model with asymmetric verify-only client model. Keep private signing key only in admin tooling, not in production client modules or PyInstaller bundle. [V6 client + Phase L1 admin signer implemented; production key ceremony/manual smoke pending]
4. Verify packaging: `WhiteLabelApp.spec` and build output must not ship `licensing_admin`, private keys, tests, pytest, or dev artifacts. [Spec tests added; real dist inspection pending]
5. Replace Google Drive pickle token persistence with JSON credential serialization and add safe migration from old pickle token if possible. [V6 implemented]
6. Add/adjust tests for migration safety, licensing verify-only behavior, variant constraints, and token serialization. [Focused tests added]

Safety rules:
- Backup-first for any DB migration.
- Add dry-run mode before destructive or table-swap migration.
- If invalid existing data is found, block migration and report rows; do not silently rewrite financial/stock values.
- Preserve backward compatibility for existing users unless a reactivation/migration step is explicitly documented.
- Run `python -m pytest -q` before handoff.

Deliverables:
- Updated code and tests.
- Updated `KNOWN_ISSUES.md`, `qa_test_matrix.md`, and this `NEXT_UPDATE_QA_BLUEPRINT.md`.
- Short release gate report with: tests run, packaging check result, migration dry-run result, remaining risks.
```

## Manual Release Gate After Next Update

- Fresh install on clean Windows machine.
- Existing customer DB migration dry-run.
- Existing customer DB migration apply on staging copy.
- Billing UAT:
  - normal bill
  - manual discount bill
  - membership discount bill
  - loyalty points bill
  - offer bill
  - redeem code bill
  - product stock bill
- Backup restore test.
- License activation/trial-extension test.
- EXE artifact inspection.
