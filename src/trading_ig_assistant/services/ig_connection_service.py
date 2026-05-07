"""Read-only IG connection workflow used by the GUI and future controllers."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from trading_ig_assistant.adapters.credentials import IGCredentials
from trading_ig_assistant.adapters.ig_rest import IGRestAdapter, IGSession
from trading_ig_assistant.app.config import IGEnvironment
from trading_ig_assistant.domain.instruments import Account


class IGAccountAdapter(Protocol):
    def login(self, credentials: IGCredentials) -> IGSession:
        """Authenticate against IG."""

    def get_accounts(self) -> list[Account]:
        """Fetch accounts for the authenticated session."""

    def switch_account(self, account_id: str, *, set_default: bool = False) -> IGSession:
        """Switch active account context without placing any order."""

    def logout(self) -> None:
        """Close the authenticated session."""


@dataclass(frozen=True)
class IGConnectionRequest:
    environment: IGEnvironment
    username: str
    password: str
    api_key: str
    selected_account_id: str | None = None


@dataclass(frozen=True)
class IGConnectionResult:
    environment: IGEnvironment
    current_account_id: str | None
    accounts: list[Account]


AdapterFactory = Callable[[IGEnvironment], IGAccountAdapter]
IG_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,30}$")


class IGConnectionService:
    """Service boundary for read-only IG login/account retrieval.

    The service deliberately logs nothing and always logs out after fetching account metadata.
    """

    def __init__(self, adapter_factory: AdapterFactory | None = None) -> None:
        self._adapter_factory = adapter_factory or self._default_adapter_factory

    def validate_read_only_connection(self, request: IGConnectionRequest) -> IGConnectionResult:
        if not IG_IDENTIFIER_PATTERN.fullmatch(request.username):
            raise ValueError(
                "Invalid IG API identifier. Use the API identifier, not an email address. "
                "It must contain only letters, digits, '-' or '_' and be 1-30 characters."
            )
        credentials = IGCredentials(
            username=request.username,
            password=request.password,
            api_key=request.api_key.strip(),
        )
        adapter = self._adapter_factory(request.environment)
        try:
            session = adapter.login(credentials)
            accounts = adapter.get_accounts()
            if _account_exists(accounts, request.selected_account_id):
                session = adapter.switch_account(request.selected_account_id or "")
            return IGConnectionResult(
                environment=request.environment,
                current_account_id=session.current_account_id,
                accounts=accounts,
            )
        finally:
            adapter.logout()

    @staticmethod
    def _default_adapter_factory(environment: IGEnvironment) -> IGAccountAdapter:
        return IGRestAdapter(environment=environment, read_only=True)


def _account_exists(accounts: list[Account], account_id: str | None) -> bool:
    if not account_id:
        return False
    return any(account.account_id == account_id for account in accounts)
