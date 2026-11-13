"""Provider-neutral API credential metadata without secret material."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class ApiProviderStatus(StrEnum):
    DISABLED = "disabled"
    CONNECTED = "connected"
    NOT_CONFIGURED = "not_configured"
    ERROR = "error"
    QUOTA_EXHAUSTED = "quota_exhausted"
    PUBLIC = "public"
    TESTING = "testing"


class ApiCredentialSource(StrEnum):
    KEYRING = "keyring"
    ENVIRONMENT = "environment"
    PUBLIC = "public"
    NONE = "none"


@dataclass(frozen=True)
class ApiProviderDefinition:
    provider_id: str
    display_name: str
    environment_variable: str | None
    requires_api_key: bool = True
    connection_test_available: bool = False
    test_may_consume_quota: bool = False


@dataclass(frozen=True)
class ApiConnectionTestResult:
    provider_id: str
    status: ApiProviderStatus
    reason_code: str
    tested_at_utc: datetime
    quota_used: int | None = None
    quota_remaining: int | None = None


@dataclass(frozen=True)
class ApiProviderState:
    definition: ApiProviderDefinition
    enabled: bool
    source: ApiCredentialSource
    status: ApiProviderStatus
    last_success_at_utc: datetime | None = None
    reason_code: str = ""
    quota_used: int | None = None
    quota_remaining: int | None = None


API_PROVIDER_DEFINITIONS = (
    ApiProviderDefinition("ig", "IG Trading API", "IG_API_KEY"),
    ApiProviderDefinition(
        "tavily",
        "Tavily Search",
        "TAVILY_API_KEY",
        connection_test_available=True,
        test_may_consume_quota=True,
    ),
    ApiProviderDefinition(
        "gdelt",
        "GDELT",
        None,
        requires_api_key=False,
        connection_test_available=True,
    ),
    ApiProviderDefinition(
        "fred",
        "FRED",
        "FRED_API_KEY",
        connection_test_available=True,
    ),
    ApiProviderDefinition(
        "eia",
        "EIA",
        "EIA_API_KEY",
        connection_test_available=True,
    ),
    ApiProviderDefinition(
        "openai",
        "OpenAI",
        "OPENAI_API_KEY",
        connection_test_available=True,
        test_may_consume_quota=True,
    ),
)

API_PROVIDER_BY_ID = {
    definition.provider_id: definition for definition in API_PROVIDER_DEFINITIONS
}
