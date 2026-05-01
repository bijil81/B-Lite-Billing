# Known Issues Register (Phase-2)

Last updated: 2026-04-29
Owner: QA / Engineering

## Critical

- **ISSUE-001: Redeem code phone restriction not consistently enforced in billing path**
  - Area: `billing.py`, `redeem_codes.py`
  - Risk: Unauthorized discount application
  - Status: Closed (fixed in current patch)
  - Action: Implemented `customer_phone` pass-through in apply + totals discount calculation, including blank-phone rejection for phone-bound codes

- **ISSUE-002: Redeem transaction stores total discount instead of redeem discount**
  - Area: `services_v5/billing_service.py`
  - Risk: Financial analytics corruption
  - Status: Closed (fixed in current patch)
  - Action: Added `redeem_discount` payload field and now persist redeem-specific amount

- **ISSUE-003: Missing accounting invariants in invoice validator**
  - Area: `validators/billing_validator.py`
  - Risk: Wrong totals can be persisted
  - Status: Closed (fixed in current patch)
  - Action: Enforced net-total and payment-total invariants, plus item line-total checks

- **ISSUE-004: No DB-level CHECK constraints for negative qty/amount**
  - Area: `sql/v5_schema.sql`
  - Risk: Data integrity drift (negative stock/amount values)
  - Status: Closed for new databases and V6 migration helper; staging apply still required before production rollout
  - Action: Added CHECK constraints for inventory, invoice, invoice-item, payment, and product variant numeric columns; added dry-run/backup-first existing DB migration helper

- **ISSUE-011: Client-side licensing HMAC/keygen material**
  - Area: `licensing/crypto.py`, `licensing/license_manager.py`, `licensing/storage.py`, `WhiteLabelApp.spec`
  - Risk: License key forgery if client secrets are extracted
  - Status: Partially closed in V6 client; production public key ceremony/admin signer still pending
  - Action: Replaced client HMAC key validation with verify-only signed-token validation and added packaging exclusion tests

## High

- **ISSUE-005: Membership discount state leak risk across customer switch**
  - Area: `billing.py`
  - Risk: Incorrect discount applied to another customer
  - Status: Closed (fixed in current patch)
  - Action: Reset `_membership_disc_pct` in non-member and invalid-phone lookup branches

- **ISSUE-007: Discount order not fully canonical**
  - Area: `billing.py`
  - Risk: Incorrect stacked-discount totals
  - Status: Closed (fixed in current patch)
  - Action: Offer and redeem bases now subtract manual, membership, and points discounts in order

- **ISSUE-006: Restore operation can leave mixed live state on partial failure**
  - Area: `backup_system.py`
  - Risk: Partial data restore / operational inconsistency
  - Status: Open
  - Action: Introduce rollback manifest or directory-level atomic switch strategy

- **ISSUE-012: Google Drive token stored as pickle**
  - Area: `google_backup.py`
  - Risk: Unsafe token deserialization and avoidable credential portability risk
  - Status: Closed in V6
  - Action: Store Google credentials as JSON and migrate old `gdrive_token.pickle` to `gdrive_token.json`

- **ISSUE-013: Existing customer DB CHECK migration not yet staged on real data**
  - Area: `db_core/constraint_migration.py`, customer `salon.db`
  - Risk: Production DB could contain invalid rows that block migration
  - Status: Open release gate
  - Action: Run migration dry-run on a staging copy, review invalid-row report, then apply only after backup confirmation

- **ISSUE-014: V6 licensing admin signer not yet created**
  - Area: `licensing_admin`, `licensing/crypto.py`
  - Risk: V6 verify-only client cannot activate production licenses until an external signer issues V6 signed tokens
  - Status: Tooling closed in Phase L1; production key ceremony, dist inspection, and manual activation smoke remain release gates
  - Action: Added admin-only BLV2 token generator, public-key module, packaging hygiene checks, and `HOW_TO_ACTIVATE_LICENSE_V6.md`

## Regression Tracking

- Current QA suite has no expected-failure tests for the Phase-2 critical validator/database items.
- Remaining high-risk work is tracked as phased follow-up: real staging DB migration dry-run/apply, production licensing key ceremony, and real dist artifact inspection.
# Known Issues -- B-Lite Management v5.6

**Version:** 5.6.0
**Last Updated:** 2026-04-04

---

## Issues by Severity

### Medium

| ID | Issue | Impact | Workaround | Planned Fix |
|---|---|---|---|---|
| KI-01 | **Unsigned EXE triggers SmartScreen** -- Windows Defender SmartScreen may warn about unknown publisher on first launch | User sees warning dialog before app opens | Click "More info" > "Run anyway". Can be permanently resolved by adding exception in Windows Security | Code signing with Authenticode certificate (~$100-400/year) |
| KI-02 | **VC++ Runtime required** -- `PyMuPDF` (PDF import) requires Microsoft Visual C++ 2015-2022 Redistributable. May fail on fresh Windows installs | PDF features may not work if runtime missing | Install [VC++ Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist). Most Win10/11 systems already have it | Bundle runtime check + download link in app |
| KI-03 | **No auto-update mechanism** -- Users must manually download and install updates | Users may run outdated versions | Inform users of new releases. Use Upgrade Guide for safe update | Lightweight version checker in future release |
| KI-04 | **No global crash handler** -- Unhandled exceptions in the main thread do not log to `app_debug.log` | Unexpected crashes leave no trace in logs | Check Windows Event Viewer for crash details | Add `sys.excepthook` to log crashes to file |

### Low

| ID | Issue | Impact | Workaround | Planned Fix |
|---|---|---|---|---|
| KI-05 | **`loading_logo.gif` missing** -- Splash screen animation GIF not included at project root. Falls back to static `logo.png` | Splash screen shows static image instead of animated GIF | Place a `loading_logo.gif` in project root before building. Use animated GIF ~360px wide | Include animated GIF in assets |
| KI-06 | **`worker_pool.py` is dead code** -- Module exists but is not imported by any other module. `backup_system.py` imports it but only when `auto_backup` is enabled | None -- module is harmless | No action needed. Module is safely excluded from distribution | Remove in next cleanup or add import |
| KI-07 | **`hidden_import_checker.py` limited scope** -- Only checks 16 primary module keys, not full transitive import tree | Developer convenience only -- PyInstaller's own dependency analysis catches missing imports | Run full build via `BUILD.bat` which includes additional validation | Enhance checker to scan all local imports |
| KI-08 | **Symmetric license signing** -- License signing secret ships in client binary and could theoretically be extracted to forge keys | A determined user with reverse engineering skills could forge activation keys. Not a concern for typical salon operators | None needed for current threat model | Migrate to asymmetric signing (private key on build server) |
| KI-09 | **Single-station design** -- App is not designed for concurrent multi-user LAN access. Each station would need its own database | Multi-branch or multi-counter environments cannot share a live database | Use Multi-Branch sync module (optional feature) for periodic sync between branches | Real-time multi-station support in future major version |
| KI-10 | **Selenium dependency size** -- The `selenium` package and browser drivers add ~45MB to the bundle but are only needed for WhatsApp Selenium mode | Larger install size for users who don't use WhatsApp features | Disable WhatsApp API feature in Settings > Advanced Features if not needed | Consider optional Selenium download in installer |
| KI-11 | **No installer for portable builds** -- Without running `BUILD.bat` + NSIS, the app is distributed as a folder without desktop shortcuts or uninstaller | Manual setup required for USB/portable distribution | Create desktop shortcut manually. Delete folder to uninstall | Use `OPTIONAL_INSTALLER_SCRIPT.iss` (included) with Inno Setup |

---

## Issues Resolved in v5.6

| ID | Issue | Resolution |
|---|---|---|
| RES-01 | `trial_status()` crashed on corrupted timestamps | Added graceful error handling with safe defaults |
| RES-02 | Integrity check crashed if critical files were quarantined | Added exception handling, skips unreadable files |
| RES-03 | `now_str()` NameError on login/logout | Added missing import in `auth.py` |
| RES-04 | Runtime `print()` statements in production code | Converted all to `app_log()` for silent logging |
| RES-05 | 16 missing hidden imports in PyInstaller spec | Added all missing modules to spec |
| RES-06 | No corruption handling for `install.dat` | State now self-heals missing keys on load |

---

## Reporting New Issues

If you encounter an issue not listed here:

1. Check `%APPDATA%\BLiteManagement_Data\app_debug.log` for error details
2. Note the steps to reproduce the issue
3. Record your Windows version and whether this is a fresh install or upgrade
4. Contact your system administrator or support provider with these details

---

*This list will be updated as new issues are identified and resolved.*
