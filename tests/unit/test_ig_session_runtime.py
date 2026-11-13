from unittest import mock

from trading_ig_assistant.adapters.credentials import IGCredentials
from trading_ig_assistant.adapters.ig_rest import IGAPIError, IGSession
from trading_ig_assistant.app.config import IGEnvironment
from trading_ig_assistant.app.runtime.ig_session_runtime import ReadOnlyIGSessionRuntime
from trading_ig_assistant.domain.instruments import Account
from trading_ig_assistant.services.ig_connection_service import (
    AccountSwitchNotConfirmedError,
    IGConnectionRequest,
)


class FakeReadOnlyAdapter:
    def __init__(self) -> None:
        self.credentials: IGCredentials | None = None
        self.logged_out = False
        self.switch_result = "ACCOUNT-B"

    def login(self, credentials: IGCredentials) -> IGSession:
        self.credentials = credentials
        return IGSession(
            cst="fake-cst",
            security_token="fake-token",
            current_account_id="ACCOUNT-A",
        )

    def get_accounts(self) -> list[Account]:
        return [
            Account(account_id="ACCOUNT-A", account_name="Demo A"),
            Account(account_id="ACCOUNT-B", account_name="Demo B"),
        ]

    def switch_account(self, _account_id: str) -> IGSession:
        return IGSession(
            cst="fake-cst",
            security_token="fake-token",
            current_account_id=self.switch_result,
        )

    def logout(self) -> None:
        self.logged_out = True


def _request(*, selected_account_id: str | None = None) -> IGConnectionRequest:
    return IGConnectionRequest(
        environment=IGEnvironment.DEMO,
        username="synthetic-user",
        password="fake-password",
        api_key="fake-api-key",
        selected_account_id=selected_account_id,
    )


def test_read_only_session_runtime_owns_one_adapter_until_disconnect() -> None:
    adapter = FakeReadOnlyAdapter()
    factory_calls: list[IGEnvironment] = []
    runtime = ReadOnlyIGSessionRuntime(
        lambda environment: factory_calls.append(environment) or adapter
    )

    connection = runtime.connect(_request())

    assert runtime.active_connection is connection
    assert connection.adapter is adapter
    assert factory_calls == [IGEnvironment.DEMO]
    assert adapter.credentials is not None
    assert "fake-password" not in repr(adapter.credentials)

    runtime.disconnect()

    assert runtime.active_connection is None
    assert adapter.logged_out is True


def test_default_live_adapter_is_always_constructed_read_only() -> None:
    runtime = ReadOnlyIGSessionRuntime()
    sentinel = object()

    with mock.patch(
        "trading_ig_assistant.app.runtime.ig_session_runtime.IGRestAdapter",
        return_value=sentinel,
    ) as adapter_type:
        adapter = runtime._default_adapter_factory(IGEnvironment.LIVE)

    assert adapter is sentinel
    adapter_type.assert_called_once_with(environment=IGEnvironment.LIVE, read_only=True)


def test_read_only_session_runtime_rejects_a_second_active_adapter() -> None:
    adapter = FakeReadOnlyAdapter()
    factory_calls = 0

    def factory(_environment: IGEnvironment):
        nonlocal factory_calls
        factory_calls += 1
        return adapter

    runtime = ReadOnlyIGSessionRuntime(factory)
    runtime.connect(_request())

    try:
        runtime.connect(_request())
    except RuntimeError as exc:
        assert "disconnect" in str(exc)
    else:
        raise AssertionError("a second active IG adapter must be rejected")

    assert factory_calls == 1
    runtime.disconnect()


def test_read_only_session_runtime_requires_confirmed_account_switch() -> None:
    adapter = FakeReadOnlyAdapter()
    runtime = ReadOnlyIGSessionRuntime(lambda _environment: adapter)
    connection = runtime.connect(_request())
    adapter.switch_result = "OTHER"

    try:
        runtime.switch_account("ACCOUNT-B")
    except AccountSwitchNotConfirmedError:
        pass
    else:
        raise AssertionError("an unconfirmed account switch must be rejected")

    assert connection.current_account_id == "ACCOUNT-A"
    assert runtime.active_connection is connection
    runtime.disconnect()


def test_failed_connection_logs_out_and_keeps_runtime_empty() -> None:
    class FailingAdapter(FakeReadOnlyAdapter):
        def get_accounts(self) -> list[Account]:
            raise RuntimeError("synthetic account failure")

    adapter = FailingAdapter()
    runtime = ReadOnlyIGSessionRuntime(lambda _environment: adapter)

    try:
        runtime.connect(_request())
    except RuntimeError as exc:
        assert "synthetic account failure" in str(exc)
    else:
        raise AssertionError("the synthetic connection must fail")

    assert runtime.active_connection is None
    assert adapter.logged_out is True


def test_fresh_invalid_client_token_retries_one_clean_session() -> None:
    class InvalidTokenAdapter(FakeReadOnlyAdapter):
        def get_accounts(self) -> list[Account]:
            raise IGAPIError(
                "IG REST request failed with HTTP 401: "
                "{'errorCode': 'error.security.client-token-invalid'}"
            )

    first = InvalidTokenAdapter()
    second = FakeReadOnlyAdapter()
    adapters = [first, second]
    delays: list[float] = []
    runtime = ReadOnlyIGSessionRuntime(
        lambda _environment: adapters.pop(0),
        token_retry_delay_seconds=0.25,
        sleep_fn=delays.append,
    )

    connection = runtime.connect(_request())

    assert connection.adapter is second
    assert first.logged_out is True
    assert delays == [0.25]
    runtime.disconnect()


def test_two_invalid_client_tokens_return_actionable_connection_error() -> None:
    class InvalidTokenAdapter(FakeReadOnlyAdapter):
        def get_accounts(self) -> list[Account]:
            raise IGAPIError(
                "IG REST request failed with HTTP 401: "
                "{'errorCode': 'error.security.client-token-invalid'}"
            )

    first = InvalidTokenAdapter()
    second = InvalidTokenAdapter()
    adapters = [first, second]
    runtime = ReadOnlyIGSessionRuntime(
        lambda _environment: adapters.pop(0),
        token_retry_delay_seconds=0,
        sleep_fn=lambda _delay: None,
    )

    try:
        runtime.connect(_request())
    except IGAPIError as exc:
        assert str(exc) == "connection.session_token_invalid"
    else:
        raise AssertionError("two rejected session tokens must fail explicitly")

    assert runtime.active_connection is None
    assert first.logged_out is True
    assert second.logged_out is True

