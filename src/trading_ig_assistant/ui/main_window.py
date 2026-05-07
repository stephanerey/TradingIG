"""Minimal GUI shell for P01."""

from __future__ import annotations

import sys

from PyQt5 import QtCore, QtWidgets

from trading_ig_assistant.adapters.credentials import build_default_credential_store
from trading_ig_assistant.app.config import (
    AppConfig,
    IGConnectionProfileConfig,
    IGEnvironment,
    default_config_path,
    load_config,
    save_config,
)
from trading_ig_assistant.services.ig_connection_service import (
    IGConnectionRequest,
    IGConnectionResult,
    IGConnectionService,
)
from trading_ig_assistant.ui.account_status_widget import AccountStatusRibbonWidget
from trading_ig_assistant.ui.chart_view import ChartView
from trading_ig_assistant.ui.macro_ribbon_widget import MacroRibbonWidget
from trading_ig_assistant.ui.product_selector import ProductSelectorWidget
from trading_ig_assistant.ui.settings_dialog import SettingsDialog


class ConnectionWorker(QtCore.QObject):
    succeeded = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()

    def __init__(self, service: IGConnectionService, request: IGConnectionRequest) -> None:
        super().__init__()
        self._service = service
        self._request = request

    @QtCore.pyqtSlot()
    def run(self) -> None:
        try:
            result = self._service.validate_read_only_connection(self._request)
            self.succeeded.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Trading IG Assistant - P01 read-only shell")
        self.resize(1280, 820)
        self._config_path = default_config_path()
        self._config = load_config(self._config_path)
        self._credential_store = self._build_credential_store()
        self._connection_service = IGConnectionService()
        self._connection_thread: QtCore.QThread | None = None
        self._connection_worker: ConnectionWorker | None = None
        self._build_menu()
        self._build_layout()

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        quit_action = file_menu.addAction("Quit")
        quit_action.triggered.connect(self.close)

        tools_menu = self.menuBar().addMenu("&Tools")
        settings_action = tools_menu.addAction("Settings")
        settings_action.triggered.connect(self._open_settings)
        disabled_action = tools_menu.addAction("Live trading disabled")
        disabled_action.setEnabled(False)

    def _build_layout(self) -> None:
        root = QtWidgets.QWidget()
        root_layout = QtWidgets.QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)

        root_layout.addWidget(MacroRibbonWidget())
        self.account_status = AccountStatusRibbonWidget()
        self.account_status.connect_requested.connect(self._connect_environment)
        self.account_status.settings_requested.connect(self._open_settings)
        self.account_status.account_selected.connect(self._select_account)
        root_layout.addWidget(self.account_status)

        body = QtWidgets.QSplitter()
        body.setOrientation(QtCore.Qt.Horizontal)
        body.addWidget(ChartView())

        right_tabs = QtWidgets.QTabWidget()
        right_tabs.addTab(ProductSelectorWidget(), "Products / Ticket")
        right_tabs.setMinimumWidth(360)
        body.addWidget(right_tabs)
        body.setStretchFactor(0, 4)
        body.setStretchFactor(1, 1)

        root_layout.addWidget(body, stretch=1)
        self.setCentralWidget(root)

    @staticmethod
    def _build_credential_store() -> object | None:
        return build_default_credential_store()

    @QtCore.pyqtSlot()
    def _open_settings(self) -> None:
        dialog = SettingsDialog(self._config, self._credential_store, self)
        dialog.config_applied.connect(self._apply_config)
        dialog.exec()

    @QtCore.pyqtSlot(object)
    def _apply_config(self, config: AppConfig) -> None:
        self._config = config
        save_config(self._config, self._config_path)
        self.statusBar().showMessage("Settings saved.", 5000)

    @QtCore.pyqtSlot(object)
    def _connect_environment(self, environment: IGEnvironment) -> None:
        profile = self._config.connection_profiles[environment]
        if not profile.identifier:
            self.statusBar().showMessage(
                f"Configure {environment.value} API identifier first.",
                7000,
            )
            self._open_settings()
            return
        if self._credential_store is None:
            self.statusBar().showMessage("OS keyring credential store is unavailable.", 7000)
            return
        credentials = self._credential_store.load_profile(environment.value, profile.identifier)
        if credentials is None:
            self.statusBar().showMessage(
                f"Configure {environment.value} password and API key first.",
                7000,
            )
            self._open_settings()
            return
        self._config.environment = environment
        self._connect_read_only(
            IGConnectionRequest(
                environment=environment,
                username=credentials.username,
                password=credentials.password.reveal(),
                api_key=credentials.api_key.reveal(),
            )
        )

    @QtCore.pyqtSlot(object)
    def _connect_read_only(self, request: IGConnectionRequest) -> None:
        if self._connection_thread is not None:
            return
        self.statusBar().showMessage(
            f"Connecting to IG {request.environment.value} in read-only mode...",
            0,
        )
        self._connection_thread = QtCore.QThread(self)
        self._connection_worker = ConnectionWorker(self._connection_service, request)
        self._connection_worker.moveToThread(self._connection_thread)
        self._connection_thread.started.connect(self._connection_worker.run)
        self._connection_worker.succeeded.connect(self._on_connection_success)
        self._connection_worker.failed.connect(self._on_connection_failure)
        self._connection_worker.finished.connect(self._connection_thread.quit)
        self._connection_worker.finished.connect(self._connection_worker.deleteLater)
        self._connection_thread.finished.connect(self._connection_thread.deleteLater)
        self._connection_thread.finished.connect(self._clear_connection_worker)
        self._connection_thread.start()

    @QtCore.pyqtSlot(object)
    def _on_connection_success(self, result: IGConnectionResult) -> None:
        self.account_status.set_accounts(result.accounts, result.current_account_id)
        self._set_profile_account(result.environment, result.current_account_id)
        message = (
            f"Connected to IG {result.environment.value}. "
            f"Accounts fetched: {len(result.accounts)}."
        )
        self.statusBar().showMessage(
            message,
            7000,
        )

    @QtCore.pyqtSlot(str)
    def _on_connection_failure(self, message: str) -> None:
        self.statusBar().showMessage(f"Connection failed: {humanize_ig_error(message)}", 12000)

    @QtCore.pyqtSlot()
    def _clear_connection_worker(self) -> None:
        self._connection_thread = None
        self._connection_worker = None

    @QtCore.pyqtSlot(object)
    def _select_account(self, account_id: object) -> None:
        self._set_profile_account(self._config.environment, str(account_id) if account_id else None)

    def _set_profile_account(self, environment: IGEnvironment, account_id: str | None) -> None:
        profile = self._config.connection_profiles[environment]
        self._config.connection_profiles[environment] = IGConnectionProfileConfig(
            environment=environment,
            identifier=profile.identifier,
            selected_account_id=account_id,
        )
        save_config(self._config, self._config_path)


def run_gui() -> int:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


def humanize_ig_error(message: str) -> str:
    if "api-key-invalid" in message:
        return (
            "API key invalid for this request. Check that the environment matches the key: "
            "demo key with demo, live key with live. If this key was exposed, revoke it and "
            "generate a new one."
        )
    if "api-key-restricted" in message:
        return "API key restricted to another account/environment."
    if "api-key-disabled" in message:
        return "API key disabled in IG settings."
    if "api-key-revoked" in message:
        return "API key revoked. Generate a new key in IG settings."
    if "validation.pattern.invalid.auth.identifier" in message:
        return (
            "Invalid API identifier format. For demo, use the demo API identifier you chose "
            "in the IG demo API tab, not your email address."
        )
    if (
        "authentication.timeout" in message
        or "get.session.timeout" in message
        or "timed out" in message
    ):
        return "IG authentication timed out. Retry once, then verify environment and credentials."
    if "invalid-details" in message:
        return "Invalid API identifier/password for the selected IG environment."
    if "client-suspended" in message:
        return (
            "IG reports this API client is suspended. Stop retrying for now, verify that you can "
            "log in to the IG web platform with the same demo API credentials, check whether IG "
            "requires agreements/KYC/API activation, then contact IG support if the account "
            "remains blocked."
        )
    if "too-many-failed-attempts" in message:
        return (
            "Too many failed IG login attempts. Wait before retrying and verify demo/live "
            "identifier, password, and API key."
        )
    return message
