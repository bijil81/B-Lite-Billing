from __future__ import annotations

import hashlib
import math
from pathlib import Path

import pytest

from licensing import crypto


def _is_probable_prime(n: int) -> bool:
    if n < 2:
        return False
    small_primes = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for prime in small_primes:
        if n % prime == 0:
            return n == prime
    d = n - 1
    s = 0
    while d % 2 == 0:
        s += 1
        d //= 2
    for a in (2, 3, 5, 7, 11, 13, 17):
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


def _next_prime(seed: int) -> int:
    candidate = seed | 1
    while not _is_probable_prime(candidate):
        candidate += 2
    return candidate


def _test_rsa_keypair():
    p = _next_prime((1 << 520) + 159)
    q = _next_prime((1 << 521) + 181)
    n = p * q
    e = 65537
    phi = (p - 1) * (q - 1)
    assert math.gcd(e, phi) == 1
    d = pow(e, -1, phi)
    return {"n": n, "e": e}, d


def _sign(payload: dict, private_exponent: int, modulus: int) -> bytes:
    key_len = (modulus.bit_length() + 7) // 8
    digest = hashlib.sha256(crypto._canonical_payload(payload)).digest()
    tail = crypto._SHA256_DER_PREFIX + digest
    padding = b"\xff" * (key_len - len(tail) - 3)
    encoded = b"\x00\x01" + padding + b"\x00" + tail
    return pow(int.from_bytes(encoded, "big"), private_exponent, modulus).to_bytes(key_len, "big")


def test_verify_only_signed_license_token_round_trip(monkeypatch):
    public_key, private_exponent = _test_rsa_keypair()
    payload = {
        "kind": "activation",
        "device_id": "DEV-1",
        "install_id": "INSTALL-1",
    }
    token = crypto.build_signed_token_for_tests(
        payload,
        _sign(payload, private_exponent, public_key["n"]),
    )
    monkeypatch.setattr(crypto, "DEFAULT_PUBLIC_KEY", public_key)

    assert crypto.validate_key(token, "activation", "DEV-1", "INSTALL-1", 0) == (True, "")
    assert crypto.validate_key(token, "activation", "OTHER", "INSTALL-1", 0) == (
        False,
        "device_or_install_mismatch",
    )
    assert crypto.decode_signed_key(token + "x")[0] is False


def test_legacy_hmac_keys_require_reactivation():
    assert crypto.inspect_key_format("A123-4567-89AB-CDEF-GHJK-MNPQ") == (
        False,
        "legacy_key_reactivation_required",
    )


def test_production_licensing_client_contains_no_signing_secret_or_keygen():
    root = Path(__file__).resolve().parents[1]
    client_files = list((root / "licensing").glob("*.py"))
    text = "\n".join(path.read_text(encoding="utf-8") for path in client_files)

    forbidden = [
        "hmac.new",
        "LICENSE_SIGNING_SECRET",
        "SIGNING_SECRET",
        "_SECRET_DEPRECATED",
        "BOBYS_V5_OFFLINE_2026_LOCAL_SIGNING_SECRET",
        "BOBYS_V5_LICENSE_DAT_HMAC_2026",
        "BOBYS_V5_STORAGE_HMAC_2026",
        "def build_key(",
    ]
    for marker in forbidden:
        assert marker not in text
