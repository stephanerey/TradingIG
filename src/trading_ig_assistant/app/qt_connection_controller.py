"""Qt controller for explicit read-only IG account intents in GUI V2."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from PyQt5 import QtCore

from trading_ig_assistant.adapters.credentials import IGCredentials
from trading_ig_assistant.app.config import (
    AppConfig,
    IGConnectionProfileConfig,
    IGEnvironment,
    save_config,
)
from trading_ig_assistant.app.projections.account_projection import (
    build_account_header_projection,
    build_runtime_health_projection,
)
from trading_ig_assistant.app.projections.dashboard_projection import (
    merge_account_metrics_into_dashboard,
)
from trading_ig_assistant.app.runtime.ig_session_runtime import ActiveIGConnection
from trading_ig_assistant.app.runtime.trading_runtime import TradingRuntime
from trading_ig_assistant.services.ig_connection_service import IGConnectionRequest


class ProfileCredentialStore(Protocol):
    def load_profile(self, profile_key: str, username: str) -> IGCredentials | None: ...


class _RuntimeConnectWorker(QtCore.QObject):
    succeeded = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()

    def __init__(self, runtime: TradingRuntime, request: IGConnectionRequest) -> None:
        super().__init__()
        self._runtime = runtime
        self._request = request

    @QtCore.pyqtSlot()
    def run(self) -> None:
        try:
            self.succeeded.emit(self._runtime.connect_ig_read_only(self._request))
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()


class _RuntimeAccountSwitchWorker(QtCore.QObject):
    succeeded = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()

    def __init__(self, runtime: TradingRuntime, account_id: str) -> None:
        super().__init__()
        self._runtime = runtime
        self._account_id = account_id

    @QtCore.pyqtSlot()
    def run(self) -> None:
        try:
            self.succeeded.emit(self._runtime.switch_ig_account(self._account_id))
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()


class ReadOnlyConnectionController(QtCore.QObject):
    """Translate explicit V2 account intents into bounded runtime operations."""

    busy_changed = QtCore.pyqtSignal(bool)
    connection_changed = QtCore.pyqtSignal(object)
    accounts_changed = QtCore.pyqtSignal(object, object)
    error = QtCore.pyqtSignal(str)
    ready_to_close = QtCore.pyqtSignal()

    def __init__(
        self,
        *,
        runtime: TradingRuntime,
        config: AppConfig,
        config_path: Path,
        credential_store: ProfileCredentialStore | None,
        api_key_reader: Callable[[], str] | None = None,
        save_config_fn: Callable[[AppConfig, Path], None] = save_config,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        super().__init__()
        self._runtime = runtime
        self._config = config
        self._config_path = config_path
        self._credential_store = credential_store
        self._api_key_reader = api_key_reader
        self._save_config = save_config_fn
        self._now_provider = now_provider or (lambda: datetime.now(UTC))
        self._thread: QtCore.QThread | None = None
        self._worker: QtCore.QObject | None = None
        self._operation: str | None = None
        self._closing = False

    @property
    def busy(self) -> bool:
        return self._thread is not None

    @property
    def active_connection(self) -> ActiveIGConnection | None:
        return self._runtime.active_ig_connection

    @QtCore.pyqtSlot()
    def connect_demo(self) -> None:
        self._connect(IGEnvironment.DEMO)

    @QtCore.pyqtSlot()
    def connect_live(self) -> None:
        """Connect to IG LIVE for account and market data only."""
        self._connect(IGEnvironment.LIVE)

    def _connect(self, environment: IGEnvironment) -> None:
        if self.busy:
            self.error.emit("connection.busy")
            return
        if self._runtime.active_ig_connection is not None:
            self.error.emit("connection.already_connected")
            return
        profile = self._config.connection_profiles[environment]
        if not profile.identifier:
            self.error.emit(f"connection.profile_missing.{environment.value}")
            return
        if self._credential_store is None:
            self.error.emit("connection.store_unavailable")
            return
        credentials = self._credential_store.load_profile(
            environment.value,
            profile.identifier,
        )
        if credentials is None:
            self.error.emit(f"connection.credentials_missing.{environment.value}")
            return
        self._runtime.begin_generation()
        self._publish_connection(None, rest_status="connecting")
        central_api_key = (
            self._api_key_reader().strip() if self._api_key_reader is not None else ""
        )
        request = IGConnectionRequest(
            environment=environment,
            username=credentials.username,
            password=credentials.password.reveal(),
            api_key=central_api_key or credentials.api_key.reveal(),
            selected_account_id=profile.selected_account_id,
        )
        self._start_worker(_RuntimeConnectWorker(self._runtime, request), "connect")

    @QtCore.pyqtSlot()
    def disconnect(self) -> None:
        if self.busy:
            self.error.emit("connection.busy")
            return
        try:
            self._runtime.disconnect_ig()
        except Exception as exc:
            self.error.emit(str(exc))
        finally:
            self._runtime.begin_generation()
            self._publish_connection(None, rest_status="disconnected")
            self.connection_changed.emit(None)
            self.accounts_changed.emit((), None)

    @QtCore.pyqtSlot(str)
    def switch_account(self, account_id: str) -> None:
        normalized = account_id.strip()
        connection = self._runtime.active_ig_connection
        if self.busy:
            self.error.emit("connection.busy")
            return
        if connection is None or not normalized:
            self.error.emit("connection.not_connected")
            return
        if connection.current_account_id == normalized:
            return
        known_ids = {account.account_id for account in connection.accounts}
        if normalized not in known_ids:
            self.error.emit("connection.account_unknown")
            return
        self._start_worker(
            _RuntimeAccountSwitchWorker(self._runtime, normalized),
            "switch",
        )

    def close(self) -> bool:
        if self.busy:
            self._closing = True
            return False
        self.disconnect()
        return True

    def _start_worker(self, worker: QtCore.QObject, operation: str) -> None:
        thread = QtCore.QThread(self)
        self._thread = thread
        self._worker = worker
        self._operation = operation
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.succeeded.connect(self._on_operation_success)
        worker.failed.connect(self._on_operation_failure)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_worker)
        self.busy_changed.emit(True)
        thread.start()

    @QtCore.pyqtSlot(object)
    def _on_operation_success(self, connection: object) -> None:
        if not isinstance(connection, ActiveIGConnection):
            self._on_operation_failure("connection.invalid_result")
            return
        self._runtime.begin_generation()
        self._publish_connection(connection, rest_status="connected")
        self._persist_confirmed_account(connection)
        self.connection_changed.emit(connection)
        self.accounts_changed.emit(tuple(connection.accounts), connection.current_account_id)

    @QtCore.pyqtSlot(str)
    def _on_operation_failure(self, message: str) -> None:
        if self._operation == "connect":
            self._runtime.begin_generation()
            self._publish_connection(None, rest_status="disconnected")
        self.error.emit(message)

    @QtCore.pyqtSlot()
    def _clear_worker(self) -> None:
        self._thread = None
        self._worker = None
        self._operation = None
        self.busy_changed.emit(False)
        if self._closing:
            self._closing = False
            self.disconnect()
            self.ready_to_close.emit()

    def _publish_connection(
        self,
        connection: ActiveIGConnection | None,
        *,
        rest_status: str,
    ) -> None:
        now = self._now_provider()
        account = None
        if connection is not None and connection.current_account_id:
            account = next(
                (
                    candidate
                    for candidate in connection.accounts
                    if candidate.account_id == connection.current_account_id
                ),
                None,
            )
        generation_id = self._runtime.generation_id
        header = build_account_header_projection(
            generation_id=generation_id,
            account=account,
            environment=connection.environment.value if connection is not None else None,
            execution_mode="PAPER",
            open_positions_count=None,
            rest_status=rest_status,
            stream_status="disconnected",
            ai_status="not_configured",
            generated_at_utc=now,
        )
        health = build_runtime_health_projection(
            generation_id=generation_id,
            rest_status=rest_status,
            stream_status="disconnected",
            ai_status="not_configured",
            observed_at_utc=now,
        )
        self._runtime.publish_account_header(header)
        self._runtime.publish_dashboard(
            merge_account_metrics_into_dashboard(
                self._runtime.read_dashboard(),
                header,
            )
        )
        self._runtime.publish_health(health, generation_id=generation_id)

    def _persist_confirmed_account(self, connection: ActiveIGConnection) -> None:
        profile = self._config.connection_profiles[connection.environment]
        self._config.environment = connection.environment
        self._config.connection_profiles[connection.environment] = IGConnectionProfileConfig(
            environment=connection.environment,
            identifier=profile.identifier,
            selected_account_id=connection.current_account_id,
        )
        try:
            self._save_config(self._config, self._config_path)
        except OSError:
            self.error.emit("connection.config_save_failed")
