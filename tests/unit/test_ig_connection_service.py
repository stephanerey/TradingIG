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
                preferred=True,
            )
        ]

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
    assert adapter.logged_out is True
    assert adapter.credentials is not None
    assert "fake-password" not in repr(adapter.credentials)
