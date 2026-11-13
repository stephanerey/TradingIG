"""Centralized API key retrieval and safe connection-test orchestration."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Protocol

from trading_ig_assistant.adapters.credentials import SecretValue
from trading_ig_assistant.domain.api_credentials import (
    API_PROVIDER_BY_ID,
    API_PROVIDER_DEFINITIONS,
    ApiConnectionTestResult,
    ApiCredentialSource,
    ApiProviderDefinition,
    ApiProviderState,
    ApiProviderStatus,
)


class ApiKeyStore(Protocol):
    def get(self, provider_id: str) -> SecretValue | None: ...

    def set(self, provider_id: str, key: SecretValue) -> None: ...

    def delete(self, provider_id: str) -> None: ...


class ApiConnectionTester(Protocol):
    def __call__(
        self,
        definition: ApiProviderDefinition,
        key: SecretValue | None,
    ) -> ApiConnectionTestResult: ...


class ApiCredentialManager:
    """Keep secret storage independent from non-secret provider settings.

    Resolution priority is deliberately stable: operating-system keyring first,
    environment variable second, then public/no-key access where supported.
    """

    def __init__(
        self,
        store: ApiKeyStore,
        *,
        environment: Mapping[str, str] | None = None,
        testers: Mapping[str, ApiConnectionTester] | None = None,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self._store = store
        self._environment = environment if environment is not None else os.environ
        self._testers = dict(testers or {})
        self._now_provider = now_provider or (lambda: datetime.now(UTC))
        self._last_results: dict[str, ApiConnectionTestResult] = {}

    @property
    def definitions(self) -> tuple[ApiProviderDefinition, ...]:
        return API_PROVIDER_DEFINITIONS

    def get_api_key(self, provider_id: str) -> SecretValue | None:
        definition = self._definition(provider_id)
        stored = self._stored_key(definition.provider_id)
        if stored is not None:
            return stored
        if definition.environment_variable:
            value = self._environment.get(definition.environment_variable, "").strip()
            if value:
                return SecretValue(value)
        return None

    def set_api_key(self, provider_id: str, key: SecretValue | str) -> None:
        definition = self._definition(provider_id)
        if not definition.requires_api_key:
            raise ValueError("Public providers do not accept API keys.")
        secret = key if isinstance(key, SecretValue) else SecretValue(key.strip())
        self._store.set(definition.provider_id, secret)
        self._last_results.pop(definition.provider_id, None)

    def delete_api_key(self, provider_id: str) -> None:
        definition = self._definition(provider_id)
        self._store.delete(definition.provider_id)
        self._last_results.pop(definition.provider_id, None)

    def has_api_key(self, provider_id: str) -> bool:
        definition = self._definition(provider_id)
        return not definition.requires_api_key or self.get_api_key(provider_id) is not None

    def credential_source(self, provider_id: str) -> ApiCredentialSource:
        definition = self._definition(provider_id)
        if not definition.requires_api_key:
            return ApiCredentialSource.PUBLIC
        if self._stored_key(provider_id) is not None:
            return ApiCredentialSource.KEYRING
        if definition.environment_variable and self._environment.get(
            definition.environment_variable, ""
        ).strip():
            return ApiCredentialSource.ENVIRONMENT
        return ApiCredentialSource.NONE

    def test_connection(self, provider_id: str) -> ApiConnectionTestResult:
        definition = self._definition(provider_id)
        key = self.get_api_key(provider_id)
        if definition.requires_api_key and key is None:
            result = ApiConnectionTestResult(
                provider_id=provider_id,
                status=ApiProviderStatus.NOT_CONFIGURED,
                reason_code="API_KEY_MISSING",
                tested_at_utc=self._now_provider(),
            )
        elif (tester := self._testers.get(provider_id)) is None:
            result = ApiConnectionTestResult(
                provider_id=provider_id,
                status=ApiProviderStatus.ERROR,
                reason_code="CONNECTION_TEST_UNAVAILABLE",
                tested_at_utc=self._now_provider(),
            )
        else:
            try:
                result = tester(definition, key)
            except Exception:
                result = ApiConnectionTestResult(
                    provider_id=provider_id,
                    status=ApiProviderStatus.ERROR,
                    reason_code="CONNECTION_TEST_FAILED",
                    tested_at_utc=self._now_provider(),
                )
        self._last_results[provider_id] = result
        return result

    def provider_state(self, provider_id: str, *, enabled: bool) -> ApiProviderState:
        definition = self._definition(provider_id)
        result = self._last_results.get(provider_id)
        source = self.credential_source(provider_id)
        if not enabled:
            status = ApiProviderStatus.DISABLED
        elif result is not None:
            status = result.status
        elif source is ApiCredentialSource.PUBLIC:
            status = ApiProviderStatus.PUBLIC
        elif source is ApiCredentialSource.NONE:
            status = ApiProviderStatus.NOT_CONFIGURED
        else:
            status = ApiProviderStatus.NOT_CONFIGURED
        return ApiProviderState(
            definition=definition,
            enabled=enabled,
            source=source,
            status=status,
            last_success_at_utc=(
                result.tested_at_utc
                if result is not None and result.status is ApiProviderStatus.CONNECTED
                else None
            ),
            reason_code=result.reason_code if result is not None else "",
            quota_used=result.quota_used if result is not None else None,
            quota_remaining=result.quota_remaining if result is not None else None,
        )

    @staticmethod
    def _definition(provider_id: str) -> ApiProviderDefinition:
        normalized = provider_id.strip().lower()
        try:
            return API_PROVIDER_BY_ID[normalized]
        except KeyError as exc:
            raise ValueError("Unknown API provider.") from exc

    def _stored_key(self, provider_id: str) -> SecretValue | None:
        try:
            return self._store.get(provider_id)
        except Exception:
            return None
