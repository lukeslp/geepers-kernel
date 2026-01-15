"""
Authentication helpers for Flask blueprints.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any, Callable, Dict, Optional

from flask import Request, current_app, request

__all__ = [
    "get_bearer_token",
    "require_api_token",
    "generate_signed_token",
    "verify_signed_token",
]


def get_bearer_token(req: Optional[Request] = None) -> Optional[str]:
    """
    Extract Bearer token from Authorization header.
    """
    req = req or request
    auth_header = req.headers.get("Authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header.split(" ", 1)[1].strip()
    return None


def require_api_token(validate: Optional[Callable[[str], bool]] = None):
    """
    Decorator enforcing API token presence and optional validation.

    If `validate` is None, the decorator will compare the token against the
    `WEB_API_TOKEN` Flask config value (or environment variable).
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any):
            token = get_bearer_token()
            validator = validate or _default_validator
            if not token or not validator(token):
                return {"error": "Unauthorized"}, 401
            return func(*args, **kwargs)

        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper

    return decorator


def generate_signed_token(
    payload: Dict[str, Any],
    secret: str,
    *,
    expires_in: int = 3600,
) -> str:
    """
    Generate a signed token using HMAC-SHA256.
    """
    data = dict(payload)
    data["exp"] = int(time.time()) + expires_in
    serialized = json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), serialized, hashlib.sha256).digest()
    token = (
        base64.urlsafe_b64encode(serialized).rstrip(b"=").decode("utf-8")
        + "."
        + base64.urlsafe_b64encode(signature).rstrip(b"=").decode("utf-8")
    )
    return token


def verify_signed_token(token: str, secret: str) -> Dict[str, Any]:
    """
    Verify a signed token and return the payload.

    Raises:
        ValueError if token is invalid or expired.
    """
    try:
        data_part, signature_part = token.split(".")
        serialized = base64.urlsafe_b64decode(_pad_base64(data_part))
        provided_signature = base64.urlsafe_b64decode(_pad_base64(signature_part))
    except ValueError as exc:
        raise ValueError("Malformed token") from exc

    expected_signature = hmac.new(secret.encode("utf-8"), serialized, hashlib.sha256).digest()
    if not hmac.compare_digest(provided_signature, expected_signature):
        raise ValueError("Invalid token signature")

    payload = json.loads(serialized)
    if payload.get("exp", 0) < time.time():
        raise ValueError("Token expired")
    return payload


def _default_validator(token: str) -> bool:
    expected = current_app.config.get("WEB_API_TOKEN")
    return bool(expected) and hmac.compare_digest(expected, token)


def _pad_base64(value: str) -> str:
    return value + "=" * (-len(value) % 4)

