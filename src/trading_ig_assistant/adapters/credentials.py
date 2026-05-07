"""Credential value objects and storage abstractions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from trading_ig_assistant.utils.redaction import REDACTED


@dataclass(frozen=True, repr=False)
class SecretValue:
    """A secret that redacts itself in string and repr output."""

    _value: str

    def __post_init__(self) -> None:
        if not isinstance(self._value, str) or not self._value:
            raise ValueError("Secret values must be non-empty strings.")

    def reveal(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return REDACTED

    def __str__(self) -> str:
        return REDACTED


def _coerce_secret(value: SecretValue | str) -> SecretValue:
    return value if isinstance(value, SecretValue) else SecretValue(value)


@dataclass(frozen=True, repr=False)
class IGCredentials:
    username: str
    password: SecretValue
    api_key: SecretValue

    def __init__(self, username: str, password: SecretValue | str, api_key: SecretValue | str):
        if not username:
            raise ValueError("IG username is required.")
        object.__setattr__(self, "username", username)
        object.__setattr__(self, "password", _coerce_secret(password))
        object.__setattr__(self, "api_key", _coerce_secret(api_key))

    def __repr__(self) -> str:
        return (
            "IGCredentials("
            f"username={self.username!r}, "
            f"password={REDACTED}, "
            f"api_key={REDACTED})"
        )


class CredentialStore(Protocol):
    def load(self, username: str) -> IGCredentials | None:
        """Load credentials for a username."""

    def save(self, credentials: IGCredentials) -> None:
        """Persist credentials."""

    def delete(self, username: str) -> None:
        """Delete credentials for a username."""


class InMemoryCredentialStore:
    """Test-only credential store."""

    def __init__(self) -> None:
        self._credentials: dict[str, IGCredentials] = {}

    def load(self, username: str) -> IGCredentials | None:
        return self._credentials.get(username)

    def save(self, credentials: IGCredentials) -> None:
        self._credentials[credentials.username] = credentials

    def delete(self, username: str) -> None:
        self._credentials.pop(username, None)


class KeyringCredentialStore:
    """OS keyring-backed credential store.

    This adapter imports keyring lazily so the base package remains dependency-light.
    """

    def __init__(self, service_name: str = "trading-ig-assistant") -> None:
        try:
            import keyring  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError(
                "keyring is not installed. Install with: pip install -e .[secure-store]"
            ) from exc
        self._keyring = keyring
        self._service_name = service_name

    def load(self, username: str) -> IGCredentials | None:
        password = self._keyring.get_password(self._service_name, f"{username}:password")
        api_key = self._keyring.get_password(self._service_name, f"{username}:api_key")
        if not password or not api_key:
            return None
        return IGCredentials(username=username, password=password, api_key=api_key)

    def save(self, credentials: IGCredentials) -> None:
        self._keyring.set_password(
            self._service_name,
            f"{credentials.username}:password",
            credentials.password.reveal(),
        )
        self._keyring.set_password(
            self._service_name,
            f"{credentials.username}:api_key",
            credentials.api_key.reveal(),
        )

    def delete(self, username: str) -> None:
        for suffix in ("password", "api_key"):
            try:
                self._keyring.delete_password(self._service_name, f"{username}:{suffix}")
            except Exception:
                # Keyring backends raise different exceptions for missing entries.
                continue
