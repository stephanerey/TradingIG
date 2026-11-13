"""Qt boundary for secure provider credentials and non-blocking probes."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from PyQt5 import QtCore

from trading_ig_assistant.app.config import (
    ApiProviderConfig,
    AppConfig,
    save_config,
)
from trading_ig_assistant.domain.api_credentials import (
    ApiConnectionTestResult,
    ApiProviderStatus,
)
from trading_ig_assistant.services.api_credential_manager import ApiCredentialManager


class _ConnectionTestWorker(QtCore.QObject):
    succeeded = QtCore.pyqtSignal(object)
    finished = QtCore.pyqtSignal()

    def __init__(self, manager: ApiCredentialManager, provider_id: str) -> None:
        super().__init__()
        self._manager = manager
        self._provider_id = provider_id

    @QtCore.pyqtSlot()
    def run(self) -> None:
        try:
            self.succeeded.emit(self._manager.test_connection(self._provider_id))
        finally:
            self.finished.emit()


class ApiCredentialsController(QtCore.QObject):
    states_changed = QtCore.pyqtSignal(object)
    provider_configuration_changed = QtCore.pyqtSignal(str)
    test_busy_changed = QtCore.pyqtSignal(str, bool)
    test_completed = QtCore.pyqtSignal(object)
    secret_revealed = QtCore.pyqtSignal(str, object)
    error = QtCore.pyqtSignal(str, str)

    def __init__(self, manager: ApiCredentialManager, config: AppConfig, config_path) -> None:
        super().__init__()
        self._manager = manager
        self._config = config
        self._config_path = config_path
        self._threads: dict[str, QtCore.QThread] = {}
        self._workers: dict[str, _ConnectionTestWorker] = {}

    @property
    def manager(self) -> ApiCredentialManager:
        return self._manager

    def publish_states(self) -> None:
        states = []
        for definition in self._manager.definitions:
            settings = self._settings(definition.provider_id)
            state = self._manager.provider_state(
                    definition.provider_id,
                    enabled=settings.enabled,
                )
            if state.last_success_at_utc is None and settings.last_success_at_utc:
                try:
                    state = replace(
                        state,
                        last_success_at_utc=datetime.fromisoformat(
                            settings.last_success_at_utc
                        ),
                    )
                except ValueError:
                    pass
            states.append(state)
        self.states_changed.emit(tuple(states))

    @QtCore.pyqtSlot(str, bool)
    def set_enabled(self, provider_id: str, enabled: bool) -> None:
        settings = self._settings(provider_id)
        settings.enabled = enabled
        self._persist(provider_id)

    @QtCore.pyqtSlot(str, str)
    def set_api_key(self, provider_id: str, key: str) -> None:
        try:
            self._manager.set_api_key(provider_id, key)
        except Exception:
            self.error.emit(provider_id, "API_KEY_SAVE_FAILED")
            return
        self._settings(provider_id).enabled = True
        self._persist(provider_id)

    @QtCore.pyqtSlot(str)
    def delete_api_key(self, provider_id: str) -> None:
        try:
            self._manager.delete_api_key(provider_id)
        except Exception:
            self.error.emit(provider_id, "API_KEY_DELETE_FAILED")
            return
        self._persist(provider_id)

    @QtCore.pyqtSlot(str)
    def reveal_api_key(self, provider_id: str) -> None:
        secret = self._manager.get_api_key(provider_id)
        if secret is not None:
            self.secret_revealed.emit(provider_id, secret)

    @QtCore.pyqtSlot(str)
    def test_connection(self, provider_id: str) -> None:
        if provider_id in self._threads:
            return
        thread = QtCore.QThread(self)
        worker = _ConnectionTestWorker(self._manager, provider_id)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.succeeded.connect(self._on_test_result)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._finish_test(provider_id))
        self._threads[provider_id] = thread
        self._workers[provider_id] = worker
        self.test_busy_changed.emit(provider_id, True)
        thread.start()

    @QtCore.pyqtSlot(object)
    def _on_test_result(self, value: object) -> None:
        if not isinstance(value, ApiConnectionTestResult):
            return
        if value.status is ApiProviderStatus.CONNECTED:
            self._settings(value.provider_id).last_success_at_utc = (
                value.tested_at_utc.isoformat()
            )
            try:
                save_config(self._config, self._config_path)
            except OSError:
                self.error.emit(value.provider_id, "PROVIDER_SETTINGS_SAVE_FAILED")
        self.test_completed.emit(value)
        self.publish_states()

    def _finish_test(self, provider_id: str) -> None:
        self._threads.pop(provider_id, None)
        self._workers.pop(provider_id, None)
        self.test_busy_changed.emit(provider_id, False)

    def _settings(self, provider_id: str) -> ApiProviderConfig:
        return self._config.api_providers.setdefault(provider_id, ApiProviderConfig())

    def _persist(self, provider_id: str) -> None:
        try:
            save_config(self._config, self._config_path)
        except OSError:
            self.error.emit(provider_id, "PROVIDER_SETTINGS_SAVE_FAILED")
            return
        self.provider_configuration_changed.emit(provider_id)
        self.publish_states()
