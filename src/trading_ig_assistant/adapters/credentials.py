"""Credential value objects and storage abstractions."""

from __future__ import annotations

import subprocess
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

    def load_profile(self, profile_key: str, username: str) -> IGCredentials | None:
        password = self._keyring.get_password(self._service_name, f"{profile_key}:password")
        api_key = self._keyring.get_password(self._service_name, f"{profile_key}:api_key")
        if (not password or not api_key) and username:
            legacy_password = self._keyring.get_password(self._service_name, f"{username}:password")
            legacy_api_key = self._keyring.get_password(self._service_name, f"{username}:api_key")
            password = password or legacy_password
            api_key = api_key or legacy_api_key
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

    def save_profile(self, profile_key: str, credentials: IGCredentials) -> None:
        for key in {profile_key, credentials.username}:
            self._keyring.set_password(
                self._service_name,
                f"{key}:password",
                credentials.password.reveal(),
            )
            self._keyring.set_password(
                self._service_name,
                f"{key}:api_key",
                credentials.api_key.reveal(),
            )

    def delete(self, username: str) -> None:
        for suffix in ("password", "api_key"):
            try:
                self._keyring.delete_password(self._service_name, f"{username}:{suffix}")
            except Exception:
                # Keyring backends raise different exceptions for missing entries.
                continue


class WindowsCredentialStore:
    """Windows Credential Manager fallback using built-in system tools."""

    def __init__(self, service_name: str = "trading-ig-assistant") -> None:
        self._service_name = service_name

    def load(self, username: str) -> IGCredentials | None:
        password = self._read_secret(f"{username}:password")
        api_key = self._read_secret(f"{username}:api_key")
        if not password or not api_key:
            return None
        return IGCredentials(username=username, password=password, api_key=api_key)

    def save(self, credentials: IGCredentials) -> None:
        self._write_secret(f"{credentials.username}:password", credentials.password.reveal())
        self._write_secret(f"{credentials.username}:api_key", credentials.api_key.reveal())

    def load_profile(self, profile_key: str, username: str) -> IGCredentials | None:
        password = self._read_secret(f"{profile_key}:password")
        api_key = self._read_secret(f"{profile_key}:api_key")
        if not password or not api_key:
            return None
        return IGCredentials(username=username, password=password, api_key=api_key)

    def save_profile(self, profile_key: str, credentials: IGCredentials) -> None:
        for key in {profile_key, credentials.username}:
            self._write_secret(f"{key}:password", credentials.password.reveal())
            self._write_secret(f"{key}:api_key", credentials.api_key.reveal())

    def delete(self, username: str) -> None:
        self._delete_secret(f"{username}:password")
        self._delete_secret(f"{username}:api_key")

    def _target(self, key: str) -> str:
        return f"{self._service_name}:{key}"

    def _write_secret(self, key: str, secret: str) -> None:
        subprocess.run(
            [
                "cmdkey.exe",
                f"/generic:{self._target(key)}",
                "/user:TradingIG",
                f"/pass:{secret}",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    def _read_secret(self, key: str) -> str | None:
        target = self._target(key)
        script = (
            "$signature = @'\n"
            "using System;\n"
            "using System.Runtime.InteropServices;\n"
            "public static class CredMan {\n"
            "  [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]\n"
            "  public struct CREDENTIAL {\n"
            "    public UInt32 Flags;\n"
            "    public UInt32 Type;\n"
            "    public string TargetName;\n"
            "    public string Comment;\n"
            "    public System.Runtime.InteropServices.ComTypes.FILETIME LastWritten;\n"
            "    public UInt32 CredentialBlobSize;\n"
            "    public IntPtr CredentialBlob;\n"
            "    public UInt32 Persist;\n"
            "    public UInt32 AttributeCount;\n"
            "    public IntPtr Attributes;\n"
            "    public string TargetAlias;\n"
            "    public string UserName;\n"
            "  }\n"
            "  [DllImport(\"advapi32.dll\", SetLastError=true, CharSet=CharSet.Unicode)]\n"
            "  public static extern bool CredRead(string target, int type, int reservedFlag, "
            "out IntPtr credentialPtr);\n"
            "  [DllImport(\"advapi32.dll\", SetLastError=true)]\n"
            "  public static extern void CredFree(IntPtr buffer);\n"
            "}\n"
            "'@\n"
            "Add-Type $signature -ErrorAction SilentlyContinue\n"
            "$ptr = [IntPtr]::Zero\n"
            f"$ok = [CredMan]::CredRead('{target}', 1, 0, [ref]$ptr)\n"
            "if (-not $ok) { exit 0 }\n"
            "$cred = [Runtime.InteropServices.Marshal]::PtrToStructure($ptr, "
            "[type][CredMan+CREDENTIAL])\n"
            "$secret = [Runtime.InteropServices.Marshal]::PtrToStringUni("
            "$cred.CredentialBlob, [int]($cred.CredentialBlobSize / 2))\n"
            "[CredMan]::CredFree($ptr)\n"
            "Write-Output $secret\n"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            check=False,
            capture_output=True,
            text=True,
        )
        secret = result.stdout.strip()
        return secret or None

    def _delete_secret(self, key: str) -> None:
        subprocess.run(
            ["cmdkey.exe", f"/delete:{self._target(key)}"],
            check=False,
            capture_output=True,
            text=True,
        )


def build_default_credential_store() -> object | None:
    try:
        return KeyringCredentialStore()
    except RuntimeError:
        pass

    try:
        subprocess.run(
            ["cmdkey.exe", "/list"],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None
    return WindowsCredentialStore()
