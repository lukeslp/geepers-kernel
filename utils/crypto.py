"""
Lightweight cryptographic helpers (hashing, HMAC, optional symmetric encryption).
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Optional, Tuple

try:
    from cryptography.fernet import Fernet

    _FERNET_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    _FERNET_AVAILABLE = False

__all__ = [
    "hash_text",
    "generate_hmac",
    "verify_hmac",
    "generate_random_key",
    "derive_key",
    "generate_symmetric_key",
    "encrypt_text",
    "decrypt_text",
    "FERNET_AVAILABLE",
]

FERNET_AVAILABLE = _FERNET_AVAILABLE


def hash_text(text: str, algorithm: str = "sha256") -> str:
    """
    Hash text using the specified algorithm.
    """
    try:
        hasher = hashlib.new(algorithm)
    except ValueError as exc:  # pragma: no cover - depends on algorithm availability
        raise ValueError(f"Unsupported hash algorithm '{algorithm}'") from exc
    hasher.update(text.encode("utf-8"))
    return hasher.hexdigest()


def generate_hmac(message: str, secret: str, algorithm: str = "sha256") -> str:
    """
    Generate a hex-encoded HMAC signature for message.
    """
    digest = hmac.new(secret.encode("utf-8"), message.encode("utf-8"), algorithm)
    return digest.hexdigest()


def verify_hmac(message: str, secret: str, signature: str, algorithm: str = "sha256") -> bool:
    """
    Verify an HMAC signature using constant time comparison.
    """
    expected = generate_hmac(message, secret, algorithm)
    return hmac.compare_digest(expected, signature)


def generate_random_key(length: int = 32) -> str:
    """
    Generate a random hexadecimal key of desired length.
    """
    if length <= 0:
        raise ValueError("length must be positive")
    return secrets.token_hex(length // 2 if length % 2 == 0 else length)


def derive_key(
    password: str,
    *,
    salt: Optional[str] = None,
    iterations: int = 100_000,
    length: int = 32,
    algorithm: str = "sha256",
) -> Tuple[str, str]:
    """
    Derive a key from a password using PBKDF2-HMAC.

    Returns a tuple of (derived_key_hex, salt_hex).
    """
    salt_bytes = bytes.fromhex(salt) if salt else secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac(
        algorithm,
        password.encode("utf-8"),
        salt_bytes,
        iterations,
        dklen=length,
    )
    return derived.hex(), salt_bytes.hex()


def generate_symmetric_key() -> str:
    """
    Generate a Fernet key when the cryptography package is available.
    """
    if not _FERNET_AVAILABLE:
        raise RuntimeError("cryptography package not installed; install 'cryptography' to use Fernet")
    return Fernet.generate_key().decode("utf-8")


def encrypt_text(text: str, key: str) -> str:
    """
    Encrypt text using Fernet symmetric encryption.
    """
    if not _FERNET_AVAILABLE:
        raise RuntimeError("cryptography package not installed; install 'cryptography' to use Fernet")
    fernet = Fernet(key.encode("utf-8"))
    token = fernet.encrypt(text.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_text(token: str, key: str) -> str:
    """
    Decrypt text using Fernet symmetric encryption.
    """
    if not _FERNET_AVAILABLE:
        raise RuntimeError("cryptography package not installed; install 'cryptography' to use Fernet")
    fernet = Fernet(key.encode("utf-8"))
    plaintext = fernet.decrypt(token.encode("utf-8"))
    return plaintext.decode("utf-8")

