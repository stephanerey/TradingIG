from __future__ import annotations

from datetime import UTC, datetime

from trading_ig_assistant.adapters.credentials import (
    InMemoryApiKeyStore,
    KeyringApiKeyStore,
    SecretValue,
)
from trading_ig_assistant.domain.api_credentials import (
    ApiConnectionTestResult,
    ApiCredentialSource,
    ApiProviderStatus,
)
from trading_ig_assistant.services.api_credential_manager import ApiCredentialManager

NOW = datetime(2026, 11, 11, 9, 0, tzinfo=UTC)


class FakeKeyring:
    def __init__(self) -> None:
        self.values: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, username: str) -> str | None:
        return self.values.get((service, username))

    def set_password(self, service: str, username: str, password: str) -> None:
        self.values[(service, username)] = password

    def delete_password(self, service: str, username: str) -> None:
        self.values.pop((service, username), None)


def test_keyring_api_store_never_exposes_secret_in_representation() -> None:
    backend = FakeKeyring()
    store = KeyringApiKeyStore(keyring_backend=backend)
    store.set("tavily", SecretValue("private-test-value"))

    loaded = store.get("tavily")

    assert loaded is not None
    assert loaded.reveal() == "private-test-value"
    assert "private-test-value" not in repr(loaded)
    store.delete("tavily")
    assert store.get("tavily") is None


def test_manager_resolves_keyring_before_environment_and_falls_back_after_delete() -> None:
    store = InMemoryApiKeyStore()
    store.set("tavily", SecretValue("stored-value"))
    manager = ApiCredentialManager(
        store,
        environment={"TAVILY_API_KEY": "environment-value"},
        now_provider=lambda: NOW,
    )

    assert manager.get_api_key("tavily").reveal() == "stored-value"
    assert manager.credential_source("tavily") is ApiCredentialSource.KEYRING

    manager.delete_api_key("tavily")

    assert manager.get_api_key("tavily").reveal() == "environment-value"
    assert manager.credential_source("tavily") is ApiCredentialSource.ENVIRONMENT


def test_public_provider_needs_no_key() -> None:
    manager = ApiCredentialManager(InMemoryApiKeyStore(), environment={})

    assert manager.has_api_key("gdelt") is True
    assert manager.credential_source("gdelt") is ApiCredentialSource.PUBLIC


def test_connection_test_returns_safe_status_without_leaking_tester_error() -> None:
    def failing_tester(_definition, _key):
        raise RuntimeError("secret-provider-payload")

    manager = ApiCredentialManager(
        InMemoryApiKeyStore(),
        environment={"TAVILY_API_KEY": "private-test-value"},
        testers={"tavily": failing_tester},
        now_provider=lambda: NOW,
    )

    result = manager.test_connection("tavily")

    assert result.status is ApiProviderStatus.ERROR
    assert result.reason_code == "CONNECTION_TEST_FAILED"
    assert "secret" not in repr(result)


def test_successful_connection_test_exposes_only_quota_metadata() -> None:
    def tester(definition, _key):
        return ApiConnectionTestResult(
            provider_id=definition.provider_id,
            status=ApiProviderStatus.CONNECTED,
            reason_code="CONNECTION_TEST_SUCCEEDED",
            tested_at_utc=NOW,
            quota_used=1,
            quota_remaining=999,
        )

    manager = ApiCredentialManager(
        InMemoryApiKeyStore(),
        environment={"TAVILY_API_KEY": "private-test-value"},
        testers={"tavily": tester},
        now_provider=lambda: NOW,
    )

    result = manager.test_connection("tavily")
    state = manager.provider_state("tavily", enabled=True)

    assert result.status is ApiProviderStatus.CONNECTED
    assert state.last_success_at_utc == NOW
    assert state.quota_used == 1
    assert state.quota_remaining == 999
