"""Single owner for the read-only IG REST session lifecycle."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from threading import RLock

from trading_ig_assistant.adapters.credentials import IGCredentials
from trading_ig_assistant.adapters.ig_rest import (
    IGAPIError,
    IGRestAdapter,
    is_invalid_security_token_error,
)
from trading_ig_assistant.app.config import IGEnvironment
from trading_ig_assistant.domain.instruments import Account
from trading_ig_assistant.services.ig_connection_service import (
    AccountSwitchNotConfirmedError,
    IGConnectionRequest,
)

AdapterFactory = Callable[[IGEnvironment], IGRestAdapter]
LOGGER = logging.getLogger(__name__)


@dataclass
class ActiveIGConnection:
    """Authenticated read-only context owned by the application runtime."""

    environment: IGEnvironment
    current_account_id: str | None
    accounts: list[Account]
    adapter: IGRestAdapter


class ReadOnlyIGSessionRuntime:
    """Own exactly one authenticated IG adapter without exposing order commands."""

    def __init__(
        self,
        adapter_factory: AdapterFactory | None = None,
        *,
        token_retry_delay_seconds: float = 1.0,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self._adapter_factory = adapter_factory or self._default_adapter_factory
        self._token_retry_delay_seconds = max(0.0, token_retry_delay_seconds)
        self._sleep = sleep_fn
        self._active_connection: ActiveIGConnection | None = None
        self._lock = RLock()

    @property
    def active_connection(self) -> ActiveIGConnection | None:
        with self._lock:
            return self._active_connection

    def connect(self, request: IGConnectionRequest) -> ActiveIGConnection:
        """Authenticate and retain one read-only adapter for the runtime."""

        with self._lock:
            if self._active_connection is not None:
                raise RuntimeError("disconnect the active IG session before reconnecting")

        credentials = IGCredentials(
            username=request.username,
            password=request.password,
            api_key=request.api_key,
        )
        adapter = self._adapter_factory(request.environment)
        try:
            session = adapter.login(credentials)
            try:
                accounts = adapter.get_accounts()
            except IGAPIError as exc:
                if not is_invalid_security_token_error(exc):
                    raise
                LOGGER.warning(
                    "IG rejected a freshly issued client token; retrying one clean session"
                )
                self._best_effort_logout(adapter)
                self._sleep(self._token_retry_delay_seconds)
                adapter = self._adapter_factory(request.environment)
                session = adapter.login(credentials)
                try:
                    accounts = adapter.get_accounts()
                except IGAPIError as retry_exc:
                    if is_invalid_security_token_error(retry_exc):
                        raise IGAPIError("connection.session_token_invalid") from retry_exc
                    raise
            if (
                request.selected_account_id
                and request.selected_account_id != session.current_account_id
                and _account_id_exists(accounts, request.selected_account_id)
            ):
                requested_account_id = request.selected_account_id
                switched_session = adapter.switch_account(requested_account_id)
                if switched_session.current_account_id != requested_account_id:
                    raise AccountSwitchNotConfirmedError(
                        "IG did not confirm the requested account context."
                    )
                session = switched_session
            connection = ActiveIGConnection(
                environment=request.environment,
                current_account_id=session.current_account_id,
                accounts=accounts,
                adapter=adapter,
            )
            with self._lock:
                if self._active_connection is not None:
                    raise RuntimeError("another IG session became active during connection")
                self._active_connection = connection
            return connection
        except Exception:
            self._best_effort_logout(adapter)
            raise

    def switch_account(self, account_id: str) -> ActiveIGConnection:
        """Switch account only after IG confirms the requested context."""

        with self._lock:
            connection = self._active_connection
            if connection is None:
                raise RuntimeError("no active IG session")
            if connection.current_account_id == account_id:
                return connection
            session = connection.adapter.switch_account(account_id)
            if session.current_account_id != account_id:
                raise AccountSwitchNotConfirmedError(
                    "IG did not confirm the requested account context."
                )
            connection.current_account_id = session.current_account_id
            return connection

    def disconnect(self) -> None:
        """Clear runtime ownership and then close the former adapter session."""

        with self._lock:
            connection = self._active_connection
            self._active_connection = None
        if connection is not None:
            connection.adapter.logout()

    def replace_for_legacy_migration(
        self,
        connection: ActiveIGConnection | None,
    ) -> None:
        """Compatibility seam for legacy tests and callbacks during incremental migration."""

        with self._lock:
            self._active_connection = connection

    @staticmethod
    def _default_adapter_factory(environment: IGEnvironment) -> IGRestAdapter:
        return IGRestAdapter(environment=environment, read_only=True)

    @staticmethod
    def _best_effort_logout(adapter: IGRestAdapter) -> None:
        try:
            adapter.logout()
        except IGAPIError:
            pass


def _account_id_exists(accounts: list[Account], account_id: str) -> bool:
    return any(account.account_id == account_id for account in accounts)
