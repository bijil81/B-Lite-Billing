# QA Test Matrix (Phase-2, CI-Ready)

Last updated: 2026-04-29
Scope: Tkinter salon billing production audit baseline

## Test Suites

- `tests/test_billing.py`
  - Focus: invoice validation, totals persistence, transaction safety signals
  - Priority: Critical

- `tests/test_database.py`
  - Focus: duplicate customer prevention, rollback behavior, data integrity constraints
  - Priority: Critical

- `tests/test_validation.py`
  - Focus: required field enforcement, numeric checks, payload safety
  - Priority: Critical

- `tests/test_schema_constraint_migration.py`
  - Focus: existing SQLite CHECK migration dry-run, backup-first apply, dirty-data block, product variant constraints
  - Priority: Critical

- `tests/test_licensing_security.py`
  - Focus: verify-only signed license tokens, no client signing secrets/keygen, legacy HMAC-key transition behavior
  - Priority: Critical

- `tests/test_licensing_admin_keygen.py`
  - Focus: admin-only V6 BLV2 activation/trial-extension token generation verified by client crypto
  - Priority: Critical

- `tests/test_packaging_hygiene.py`
  - Focus: PyInstaller spec excludes admin/test/dev tooling and build script runs dist validation
  - Priority: Critical

- `tests/test_google_backup_tokens.py`
  - Focus: Google credential JSON token persistence and one-time legacy pickle migration
  - Priority: High

## Coverage Map

- **Billing calculations**
  - Covered: negative amount rejection, saved invoice totals/items/payments persistence
  - Covered: accounting invariants and canonical discount base order for current billing path
  - Covered: V5.6 QA fixes ported into V6 split helpers and wrappers

- **Duplicate detection**
  - Covered: upsert uniqueness by customer phone
  - Covered: phone format hard validation in customer validator

- **Runtime dependency coverage**
  - Covered: import smoke for main/settings/security/advanced/print/update/WhatsApp/runtime support modules
  - Gate pending: manual Settings tab smoke after copying missing runtime modules

- **Database operations**
  - Covered: transactional rollback on payment failure
  - Covered: DB-level negative-value CHECK enforcement for new DBs
  - Covered: controlled migration helper for existing DBs created before CHECK constraints
  - Gate pending: manual dry-run/apply on a staging copy of a real customer DB

- **Validation logic**
  - Covered: required fields, non-negative money fields, accounting invariants, strict phone format enforcement

- **Licensing security**
  - Covered: V6 client verifies signed tokens with public-key material only
  - Covered: V6 client no longer exposes HMAC signing/keygen secrets
  - Covered: Phase L1 external admin signer/token generator for activation and trial extension
  - Gate pending: source-mode and built-EXE activation smoke with a real V6 signed token

- **Packaging hygiene**
  - Covered: spec-level exclusion checks for `licensing_admin`, tests, pytest, and dev tooling
  - Gate pending: inspect real `dist/` output after build

- **Google backup credentials**
  - Covered: token JSON serialization and legacy pickle token migration

## Execution Commands

- Run full regression:
  - `python -m pytest -q`

- Run only critical production gate:
  - `python -m pytest -m critical -q`

- Run Phase-2 suites only:
  - `python -m pytest tests/test_billing.py tests/test_database.py tests/test_validation.py -q`

- Run next-update hardening suites only:
  - `python -m pytest tests/test_schema_constraint_migration.py tests/test_licensing_security.py tests/test_packaging_hygiene.py tests/test_google_backup_tokens.py -q`

## CI Gate Recommendation

- **Pull Request gate**
  - Required: `python -m pytest -m critical -q`
  - Optional: full regression on nightly

- **Nightly gate**
  - `python -m pytest -q`
  - Publish artifact: JUnit XML report for trend tracking

Suggested artifact command:
- `python -m pytest -m critical --junitxml=reports/critical-junit.xml`

## Pass Criteria

- No failing `critical` tests
- No unexpected xpass on known-defect tests (review if xfail turns xpass)
- No new untriaged high/critical defects introduced

## Release Blockers

- Any failing `critical` test
- Any unresolved issue in `known_issues.md` Critical section without explicit waiver
- Any DB migration apply on production data without a staging dry-run and backup confirmation
- Any release build where `licensing_admin`, private keys, tests, pytest, or dev artifacts appear in `dist/`
- Any V6 verify-only release without a working external V6 signer and manual activation smoke
