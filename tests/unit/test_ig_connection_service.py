from trading_ig_assistant.adapters.credentials import IGCredentials
from trading_ig_assistant.adapters.ig_rest import IGSession
from trading_ig_assistant.app.config import IGEnvironment
from trading_ig_assistant.domain.instruments import Account
from trading_ig_assistant.services.ig_connection_service import (
    IGConnectionRequest,
    IGConnectionService,
)


class FakeAccountAdapter:
    def __init__(self) -> None:
        self.logged_out = False
        self.credentials: IGCredentials | None = None

    def login(self, credentials: IGCredentials) -> IGSession:
        self.credentials = credentials
        return IGSession(cst="fake-cst", security_token="fake-token", current_account_id="ACC123")

    def get_accounts(self) -> list[Account]:
        return [
            Account(
                account_id="ACC123",
                account_name="Demo CFD",
                account_type="CFD",
                currency="EUR",
                balance=1000.0,
                available=900.0,
                preferred=True,
            )
        ]

    def switch_account(self, account_id: str, *, set_default: bool = False) -> IGSession:
        return IGSession(
            cst="fake-cst",
            security_token="fake-token-switched",
            current_account_id=account_id,
        )

    def logout(self) -> None:
        self.logged_out = True


def test_connection_service_fetches_accounts_and_logs_out() -> None:
    adapter = FakeAccountAdapter()
    service = IGConnectionService(adapter_factory=lambda _environment: adapter)

    result = service.validate_read_only_connection(
        IGConnectionRequest(
            environment=IGEnvironment.DEMO,
            username="demo-user",
            password="fake-password",
            api_key="fake-api-key",
        )
    )

    assert result.current_account_id == "ACC123"
    assert result.accounts[0].account_name == "Demo CFD"
    assert result.accounts[0].available == 900.0
    assert adapter.logged_out is True
    assert adapter.credentials is not None
    assert "fake-password" not in repr(adapter.credentials)


def test_connection_service_switches_to_selected_account() -> None:
    adapter = FakeAccountAdapter()
    service = IGConnectionService(adapter_factory=lambda _environment: adapter)

    result = service.validate_read_only_connection(
        IGConnectionRequest(
            environment=IGEnvironment.DEMO,
            username="demo-user",
            password="fake-password",
            api_key="fake-api-key",
            selected_account_id="ACC123",
        )
    )

    assert result.current_account_id == "ACC123"


def test_connection_service_rejects_email_identifier_before_http() -> None:
    adapter = FakeAccountAdapter()
    service = IGConnectionService(adapter_factory=lambda _environment: adapter)

    try:
        service.validate_read_only_connection(
            IGConnectionRequest(
                environment=IGEnvironment.DEMO,
                username="demo@example.com",
                password="fake-password",
                api_key="fake-api-key",
            )
        )
    except ValueError as exc:
        assert "not an email address" in str(exc)
    else:
        raise AssertionError("Expected ValueError")

    assert adapter.credentials is None
