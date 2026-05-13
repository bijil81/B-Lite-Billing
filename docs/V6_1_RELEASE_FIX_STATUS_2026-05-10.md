# B-Lite Management V6.1.0 - Release Fix Status

**Updated:** 2026-05-10 14:28 +05:30  
**Purpose:** Current single-page status for the Antigravity/Codex verification pass.

## Current Decision

Do not revert the Antigravity source fixes. They were unauthorized for a report-only request, but the actual code changes are valid fixes and the current regression suite passes.

## Verified Fixes Kept

| Area | Status | Notes |
|---|---|---|
| Login lockout | Fixed | Wrong-password failure is counted once instead of twice |
| Inventory stock movement | Fixed | Stock validation and stock movement now both use case-insensitive lookup |
| Due-clearance payment validation | Fixed | Payment can exceed current invoice only when covered by due clearance |
| Staff commission diagnostics | Fixed | Unknown staff commission skip now writes a warning log |
| RSA key generation | Fixed | Admin keygen now guards against 2047-bit modulus output |

## Licensing Key Status

| Item | Status |
|---|---|
| Client public key | `licensing/public_key.py` fingerprint `84D2E830E37775067190D400` |
| Secure private key | `G:\chimmu\Bobys_Salon Billing\License_Admin_Secrets\v6_license_private_key.json` |
| Old private key | Backed up as `v6_license_private_key_OLD_before_84D2_20260510_142018.json` |
| Project-root `admin_keys` | Removed after secure copy |
| Public/private match | Verified true |

## Verification

| Check | Result |
|---|---|
| `py_compile` on touched runtime files | PASS |
| Full regression | `467 passed` |
| Private key outside project folder | PASS |

## Remaining Before Customer Handoff

1. Rebuild latest-source EXE.
2. Inspect `dist/` for private keys, `licensing_admin`, tests, pytest, and dev artifacts.
3. Generate a BLV2 activation token from the secure private key and activate the rebuilt EXE.
4. Run one real-printer smoke if the target shop uses direct thermal printing.
5. Run one PDF/A4 print smoke, one VOID smoke, and one backup restore smoke.
