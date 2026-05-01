from __future__ import annotations

import math
from pathlib import Path

from licensing import crypto
from licensing_admin import keygen


def _is_probable_prime(n: int) -> bool:
    if n < 2:
        return False
    for prime in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
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


def _test_private_key() -> dict:
    p = _next_prime((1 << 520) + 159)
    q = _next_prime((1 << 521) + 181)
    n = p * q
    e = 65537
    phi = (p - 1) * (q - 1)
    assert math.gcd(e, phi) == 1
    d = pow(e, -1, phi)
    return {
        "schema": "blite-v6-rsa-private-key",
        "bits": 1042,
        "n": f"{n:x}",
        "e": e,
        "d": f"{d:x}",
        "p": f"{p:x}",
        "q": f"{q:x}",
        "public_fingerprint": "TEST",
    }


def test_admin_keygen_builds_activation_token_verified_by_client_crypto():
    private_key = _test_private_key()
    public_key = keygen.public_key_from_private(private_key)

    token = keygen.build_token("activation", "DEVICE-1", "INSTALL-1", private_key)
    ok, reason, payload = crypto.decode_signed_key(token, public_key)

    assert ok is True
    assert reason == ""
    assert payload["kind"] == "activation"
    assert payload["device_id"] == "DEVICE-1"
    assert payload["install_id"] == "INSTALL-1"


def test_admin_keygen_builds_trial_extension_token_with_days():
    private_key = _test_private_key()
    public_key = keygen.public_key_from_private(private_key)

    token = keygen.build_token("trial_extend", "DEVICE-2", "INSTALL-2", private_key, days=14)
    ok, _, payload = crypto.decode_signed_key(token, public_key)

    assert ok is True
    assert payload["kind"] == "trial_extend"
    assert payload["days"] == 14


def test_public_key_module_contains_no_private_exponents():
    private_key = _test_private_key()
    root = Path(__file__).resolve().parents[1]
    output = root / ".licensing_admin_public_key_test.py"
    try:
        keygen.write_public_key_module(private_key, output)
        text = output.read_text(encoding="utf-8")
    finally:
        if output.exists():
            output.unlink()

    assert "DEFAULT_PUBLIC_KEY" in text
    assert '"d"' not in text
    assert '"p"' not in text
    assert '"q"' not in text
    assert "private" not in text.lower()
