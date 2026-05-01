"""Backward-compatible password hashing helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
from typing import Tuple


_LEGACY_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_PBKDF2_PREFIX = "pbkdf2_sha256"
_PBKDF2_ITERATIONS = 390000


def _legacy_sha256(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _bcrypt_available():
    try:
        import bcrypt  # type: ignore

        return bcrypt
    except Exception:
        return None


def hash_password(password: str) -> str:
    """Return a secure password hash using bcrypt when available."""
    bcrypt = _bcrypt_available()
    if bcrypt is not None:
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12))
        return f"bcrypt${hashed.decode('utf-8')}"

    salt = os.urandom(16)
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        _PBKDF2_ITERATIONS,
    )
    salt_b64 = base64.b64encode(salt).decode("ascii")
    hash_b64 = base64.b64encode(derived).decode("ascii")
    return f"{_PBKDF2_PREFIX}${_PBKDF2_ITERATIONS}${salt_b64}${hash_b64}"


def _verify_bcrypt(password: str, stored_hash: str) -> bool:
    bcrypt = _bcrypt_available()
    if bcrypt is None:
        return False
    try:
        payload = stored_hash.split("$", 1)[1].encode("utf-8")
        return bool(bcrypt.checkpw(password.encode("utf-8"), payload))
    except Exception:
        return False


def _verify_pbkdf2(password: str, stored_hash: str) -> bool:
    try:
        _, iter_text, salt_b64, hash_b64 = stored_hash.split("$", 3)
        iterations = int(iter_text)
        salt = base64.b64decode(salt_b64.encode("ascii"))
        expected = base64.b64decode(hash_b64.encode("ascii"))
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iterations,
        )
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def verify_password(password: str, stored_hash: str) -> Tuple[bool, bool]:
    """
    Return (is_valid, should_upgrade_hash).

    Old unsalted SHA256 hashes stay valid, but should be upgraded after login.
    """
    if not stored_hash:
        return False, False

    if stored_hash.startswith("bcrypt$"):
        return _verify_bcrypt(password, stored_hash), False

    if stored_hash.startswith(f"{_PBKDF2_PREFIX}$"):
        return _verify_pbkdf2(password, stored_hash), False

    if _LEGACY_SHA256_RE.fullmatch(stored_hash):
        is_valid = hmac.compare_digest(_legacy_sha256(password), stored_hash)
        return is_valid, is_valid

    return False, False
