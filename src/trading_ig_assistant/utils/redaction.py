"""Helpers for preventing secret leakage in repr, logs, and exceptions."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

REDACTED = "***REDACTED***"

DEFAULT_SECRET_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "api-key",
        "password",
        "passwd",
        "secret",
        "token",
        "cst",
        "x-security-token",
        "authorization",
    }
)


def is_secret_key(key: str) -> bool:
    normalized = key.lower().replace("_", "-")
    return normalized in DEFAULT_SECRET_KEYS or "token" in normalized or "secret" in normalized


def redact_value(value: Any) -> str:
    if value is None:
        return ""
    return REDACTED


def redact_mapping(mapping: Mapping[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in mapping.items():
        if is_secret_key(str(key)):
            redacted[str(key)] = REDACTED
        elif isinstance(value, Mapping):
            redacted[str(key)] = redact_mapping(value)
        else:
            redacted[str(key)] = value
    return redacted


def redact_text(text: str, secrets: list[str] | tuple[str, ...]) -> str:
    safe = text
    for secret in secrets:
        if secret:
            safe = safe.replace(secret, REDACTED)
    return safe
