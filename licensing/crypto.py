"""Verify-only licensing crypto for production clients.

The client contains a public RSA key and verifies server/admin-signed
license tokens. It intentionally contains no signing secret and no
license-generation function.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
from typing import Any

from .public_key import DEFAULT_PUBLIC_KEY


TOKEN_PREFIX = "BLV2"
LEGACY_KEY_PATTERN = re.compile(r"^[AT][0-9A-Z]{3}(?:-[0-9A-Z]{4}){5}$")

_SHA256_DER_PREFIX = bytes.fromhex("3031300d060960864801650304020105000420")


def _canonical_payload(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _b64url_decode(value: str) -> bytes:
    padded = value + ("=" * (-len(value) % 4))
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def inspect_key_format(raw_key: str):
    key = (raw_key or "").strip()
    if key.startswith(f"{TOKEN_PREFIX}."):
        parts = key.split(".")
        if len(parts) != 3:
            return False, "invalid_key"
        return True, "signed_token"
    compact = "".join(ch for ch in key.upper() if ch.isalnum())
    formatted = "-".join(compact[i : i + 4] for i in range(0, len(compact), 4))
    if LEGACY_KEY_PATTERN.match(formatted):
        return False, "legacy_key_reactivation_required"
    return False, "invalid_key"


def verify_signed_payload(
    payload: dict[str, Any],
    signature: bytes,
    public_key: dict[str, int] | None = None,
) -> bool:
    key = public_key or DEFAULT_PUBLIC_KEY
    modulus = int(key["n"])
    exponent = int(key["e"])
    key_len = (modulus.bit_length() + 7) // 8
    if len(signature) != key_len:
        return False
    signed_int = int.from_bytes(signature, "big")
    encoded = pow(signed_int, exponent, modulus).to_bytes(key_len, "big")
    digest = hashlib.sha256(_canonical_payload(payload)).digest()
    expected_tail = _SHA256_DER_PREFIX + digest
    if not encoded.startswith(b"\x00\x01"):
        return False
    try:
        sep_index = encoded.index(b"\x00", 2)
    except ValueError:
        return False
    padding = encoded[2:sep_index]
    return len(padding) >= 8 and set(padding) == {0xFF} and encoded[sep_index + 1 :] == expected_tail


def decode_signed_key(raw_key: str, public_key: dict[str, int] | None = None):
    ok, reason = inspect_key_format(raw_key)
    if not ok:
        return False, reason, {}
    try:
        _, payload_part, signature_part = raw_key.strip().split(".")
        payload = json.loads(_b64url_decode(payload_part).decode("utf-8"))
        signature = _b64url_decode(signature_part)
    except Exception:
        return False, "invalid_key", {}
    if not isinstance(payload, dict):
        return False, "invalid_key", {}
    if not verify_signed_payload(payload, signature, public_key):
        return False, "invalid_signature", {}
    return True, "", payload


def build_signed_token_for_tests(payload: dict[str, Any], signature: bytes) -> str:
    """Assemble a token from an externally-created signature.

    This is not a signer. Tests/admin tooling may use it after signing
    payload bytes outside the production client.
    """
    return f"{TOKEN_PREFIX}.{_b64url_encode(_canonical_payload(payload))}.{_b64url_encode(signature)}"


def validate_key(raw_key: str, kind: str, device_id: str, install_id: str, days: int = 10):
    ok, reason, payload = decode_signed_key(raw_key)
    if not ok:
        return False, reason
    if payload.get("kind") != kind:
        return False, "wrong_key_type"
    if payload.get("device_id") != device_id or payload.get("install_id") != install_id:
        return False, "device_or_install_mismatch"
    if kind == "trial_extend" and int(payload.get("days", -1)) != int(days):
        return False, "wrong_trial_extension_days"
    return True, ""
