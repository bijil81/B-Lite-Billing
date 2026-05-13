# Licensing Phase L1 Report

Date: 2026-04-29

## Goal

Make V6 licensing usable with a verify-only production client. The app must not contain a private signing key or V5.6 HMAC signing secret.

## Implemented

- Added `licensing/public_key.py` for client-side public verification material.
- Updated `licensing/crypto.py` to verify BLV2 tokens through the public-key module.
- Added `licensing_admin/keygen.py` as admin-only tooling for:
  - RSA key-pair generation
  - public key installation into `licensing/public_key.py`
  - activation token generation
  - trial-extension token generation
- Updated `GENERATE_LICENSE_KEY.bat` wording to V6 BLV2.
- Updated `WhiteLabelApp.spec` hidden imports for `licensing.public_key` and retained `licensing_admin` exclusions.
- Added focused tests for admin token signing and packaging hygiene.
- Added user activation note: `HOW_TO_ACTIVATE_LICENSE_V6.md`.

## V5.6 Comparison

V5.6 has `licensing/crypto.py` with `_SECRET_DEPRECATED`, `SECRET`, HMAC validation, and `build_key()`. That means key generation logic and key verification secret live in the client path.

V6 now has no client-side key generator. The client only verifies signed `BLV2` tokens. Token signing is isolated in `licensing_admin/`, which is excluded from the PyInstaller package.

## Remaining Release Gates

- Run first-time production key ceremony and replace placeholder `licensing/public_key.py`.
- Build EXE after public key installation.
- Inspect `dist/` to confirm no `licensing_admin`, tests, pytest, or private key files ship.
- Manual source-mode license smoke:
  - activation token accepted
  - trial-extension token accepted
  - tampered token rejected
  - wrong-device token rejected
- Manual built-EXE license smoke with the same scenarios.

## Verification Run

- `python -m py_compile licensing\crypto.py licensing\public_key.py licensing_admin\keygen.py tests\test_licensing_admin_keygen.py tests\test_packaging_hygiene.py`
- Direct targeted checks:
  - `tests.test_licensing_admin_keygen`
  - `tests.test_packaging_hygiene.test_pyinstaller_spec_excludes_admin_tests_and_dev_tooling`

Full `python -m pytest -q` was not run in this environment because pytest is not available in the current bundled Python/runtime.

