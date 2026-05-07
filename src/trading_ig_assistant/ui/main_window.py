"""Minimal GUI shell for P01."""

from __future__ import annotations

import sys

from PyQt5 import QtCore, QtWidgets

from trading_ig_assistant.adapters.credentials import build_default_credential_store
from trading_ig_assistant.adapters.ig_rest import IGAPIError, is_invalid_security_token_error
from trading_ig_assistant.app.config import (
    AppConfig,
    IGConnectionProfileConfig,
    IGEnvironment,
    default_config_path,
    load_config,
    save_config,
)
from trading_ig_assistant.domain.instruments import Account
from trading_ig_assistant.services.ig_connection_service import (
    IGConnectionRequest,
    IGConnectionResult,
    IGConnectionService,
)
from trading_ig_assistant.services.product_discovery_service import (
    ProductDiscoveryResult,
    ProductDiscoveryService,
    write_discovery_report,
)
from trading_ig_assistant.ui.about_dialog import AboutDialog
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


class ProductDiscoveryWorker(QtCore.QObject):
    succeeded = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()

    def __init__(
        self,
        request: IGConnectionRequest,
    ) -> None:
        super().__init__()
        self._request = request

    @QtCore.pyqtSlot()
    def run(self) -> None:
        from trading_ig_assistant.adapters.ig_rest import IGRestAdapter

        try:
            last_error: Exception | None = None
            for attempt in range(2):
                adapter = IGRestAdapter(environment=self._request.environment, read_only=True)
                try:
                    credentials = _credentials_from_request(self._request)
                    adapter.login(credentials)
                    if self._request.selected_account_id:
                        adapter.switch_account(self._request.selected_account_id)
                    service = ProductDiscoveryService(adapter)
                    results = [service.discover_all_products()]
                    if _results_contain_invalid_security_token(results):
                        raise IGAPIError(
                            "invalid-security-token: IG rejected the discovery session token."
                        )
                    self.succeeded.emit(results)
                    return
                except Exception as exc:
                    last_error = exc
                    if attempt == 0 and is_invalid_security_token_error(exc):
                        continue
                    self.failed.emit(str(exc))
                    return
                finally:
                    try:
                        adapter.logout()
                    except IGAPIError as exc:
                        if not is_invalid_security_token_error(exc):
                            last_error = exc
            if last_error is not None:
                self.failed.emit(str(last_error))
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
        self._discovery_thread: QtCore.QThread | None = None
        self._discovery_worker: ProductDiscoveryWorker | None = None
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

        help_menu = self.menuBar().addMenu("&Help")
        help_action = help_menu.addAction("Help")
        help_action.triggered.connect(self._show_help)
        about_action = help_menu.addAction("About TradingIG")
        about_action.triggered.connect(self._show_about)

    def _build_layout(self) -> None:
        root = QtWidgets.QWidget()
        root_layout = QtWidgets.QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)

        self.account_status = AccountStatusRibbonWidget()
        self.account_status.connect_requested.connect(self._connect_environment)
        self.account_status.disconnect_requested.connect(self._disconnect)
        self.account_status.settings_requested.connect(self._open_settings)
        self.account_status.account_selected.connect(self._select_account)
        root_layout.addWidget(self.account_status)
        root_layout.addWidget(MacroRibbonWidget())

        body = QtWidgets.QSplitter()
        body.setOrientation(QtCore.Qt.Horizontal)
        body.addWidget(ChartView())

        right_tabs = QtWidgets.QTabWidget()
        self.product_selector = ProductSelectorWidget()
        self.product_selector.discover_requested.connect(self._discover_products)
        self.product_selector.export_requested.connect(self._export_discovery_report)
        right_tabs.addTab(self.product_selector, "Products / Ticket")
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
        request = self._build_request_for_environment(environment)
        if request is None:
            return
        self._config.environment = environment
        self._connect_read_only(request)

    def _build_request_for_environment(
        self,
        environment: IGEnvironment,
    ) -> IGConnectionRequest | None:
        profile = self._config.connection_profiles[environment]
        if not profile.identifier:
            self.statusBar().showMessage(
                f"Configure {environment.value} API identifier first.",
                7000,
            )
            self._open_settings()
            return None
        if self._credential_store is None:
            self.statusBar().showMessage("OS keyring credential store is unavailable.", 7000)
            return None
        credentials = self._credential_store.load_profile(environment.value, profile.identifier)
        if credentials is None:
            self.statusBar().showMessage(
                f"Configure {environment.value} password and API key first.",
                7000,
            )
            self._open_settings()
            return None
        return IGConnectionRequest(
            environment=environment,
            username=credentials.username,
            password=credentials.password.reveal(),
            api_key=credentials.api_key.reveal(),
            selected_account_id=profile.selected_account_id,
        )

    @QtCore.pyqtSlot()
    def _disconnect(self) -> None:
        if self._connection_thread is not None:
            self.statusBar().showMessage("Connection is busy; wait before disconnecting.", 5000)
            return
        self.account_status.set_disconnected()
        self.statusBar().showMessage("Disconnected locally. No IG session is kept open.", 5000)

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
        configured_account_id = self._config.connection_profiles[
            result.environment
        ].selected_account_id
        selected_account_id = _resolve_account_id(
            result.accounts,
            configured_account_id,
            result.current_account_id,
        )
        self.account_status.set_accounts(
            result.accounts,
            selected_account_id,
            result.environment,
            connected=False,
        )
        self._set_profile_account(result.environment, selected_account_id)
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
    def _discover_products(self, search_terms: object) -> None:
        if self._discovery_thread is not None:
            return
        request = self._build_request_for_environment(self._config.environment)
        if request is None:
            return
        self.product_selector.set_busy(True)
        self.statusBar().showMessage(
            f"Discovering products on IG {request.environment.value}...",
            0,
        )
        self._discovery_thread = QtCore.QThread(self)
        self._discovery_worker = ProductDiscoveryWorker(request)
        self._discovery_worker.moveToThread(self._discovery_thread)
        self._discovery_thread.started.connect(self._discovery_worker.run)
        self._discovery_worker.succeeded.connect(self._on_discovery_success)
        self._discovery_worker.failed.connect(self._on_discovery_failure)
        self._discovery_worker.finished.connect(self._discovery_thread.quit)
        self._discovery_worker.finished.connect(self._discovery_worker.deleteLater)
        self._discovery_thread.finished.connect(self._discovery_thread.deleteLater)
        self._discovery_thread.finished.connect(self._clear_discovery_worker)
        self._discovery_thread.start()

    @QtCore.pyqtSlot(object)
    def _on_discovery_success(self, results: list[ProductDiscoveryResult]) -> None:
        self.product_selector.set_results(results)
        product_count = sum(len(result.products) for result in results)
        self.statusBar().showMessage(f"Product discovery complete: {product_count} products.", 7000)

    @QtCore.pyqtSlot(str)
    def _on_discovery_failure(self, message: str) -> None:
        self.statusBar().showMessage(
            f"Product discovery failed: {humanize_ig_error(message)}",
            12000,
        )

    @QtCore.pyqtSlot()
    def _clear_discovery_worker(self) -> None:
        self._discovery_thread = None
        self._discovery_worker = None
        self.product_selector.set_busy(False)

    @QtCore.pyqtSlot(object)
    def _export_discovery_report(self, output_path: object) -> None:
        write_discovery_report(self.product_selector.results(), output_path)
        self.statusBar().showMessage(f"Sanitized report written to {output_path}", 7000)

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

    @QtCore.pyqtSlot()
    def _show_help(self) -> None:
        QtWidgets.QMessageBox.information(
            self,
            "TradingIG Help",
            "Help content will be loaded from a Markdown file in a future update.",
        )

    @QtCore.pyqtSlot()
    def _show_about(self) -> None:
        AboutDialog(self).exec()


def run_gui() -> int:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


def _credentials_from_request(request: IGConnectionRequest):
    from trading_ig_assistant.adapters.credentials import IGCredentials

    return IGCredentials(
        username=request.username,
        password=request.password,
        api_key=request.api_key,
    )


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
    if "invalid-security-token" in message or "client-token-invalid" in message:
        return (
            "IG rejected the session security token. The app retried once automatically. "
            "If it persists, disconnect/reconnect and verify that the selected account belongs "
            "to the selected live/demo environment."
        )
    return message


def _resolve_account_id(
    accounts: list[Account],
    preferred_account_id: str | None,
    fallback_account_id: str | None,
) -> str | None:
    known_ids = {account.account_id for account in accounts}
    if preferred_account_id in known_ids:
        return preferred_account_id
    if fallback_account_id in known_ids:
        return fallback_account_id
    for account in accounts:
        if account.preferred:
            return account.account_id
    return accounts[0].account_id if accounts else None


def _results_contain_invalid_security_token(results: list[ProductDiscoveryResult]) -> bool:
    return any(
        is_invalid_security_token_error(error.message)
        for result in results
        for error in result.errors
    )
