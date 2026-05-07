"""Minimal GUI shell for P01."""

from __future__ import annotations

import sys

from PyQt5 import QtCore, QtWidgets

from trading_ig_assistant.app.config import default_config_path, save_config
from trading_ig_assistant.services.ig_connection_service import (
    IGConnectionRequest,
    IGConnectionResult,
    IGConnectionService,
)
from trading_ig_assistant.ui.account_status_widget import AccountStatusRibbonWidget
from trading_ig_assistant.ui.chart_view import ChartView
from trading_ig_assistant.ui.macro_ribbon_widget import MacroRibbonWidget
from trading_ig_assistant.ui.product_selector import ProductSelectorWidget
from trading_ig_assistant.ui.settings_view import SettingsView


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
        disabled_action = tools_menu.addAction("Live trading disabled")
        disabled_action.setEnabled(False)

    def _build_layout(self) -> None:
        root = QtWidgets.QWidget()
        root_layout = QtWidgets.QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)

        root_layout.addWidget(MacroRibbonWidget())
        self.account_status = AccountStatusRibbonWidget()
        root_layout.addWidget(self.account_status)

        body = QtWidgets.QSplitter()
        body.setOrientation(QtCore.Qt.Horizontal)
        body.addWidget(ChartView())

        right_tabs = QtWidgets.QTabWidget()
        right_tabs.addTab(ProductSelectorWidget(), "Products / Ticket")
        self.settings_view = SettingsView()
        self.settings_view.connection_requested.connect(self._connect_read_only)
        self.settings_view.save_requested.connect(self._save_non_secret_settings)
        right_tabs.addTab(self.settings_view, "Settings")
        right_tabs.setMinimumWidth(360)
        body.addWidget(right_tabs)
        body.setStretchFactor(0, 4)
        body.setStretchFactor(1, 1)

        root_layout.addWidget(body, stretch=1)
        self.setCentralWidget(root)

    @QtCore.pyqtSlot(object)
    def _connect_read_only(self, request: IGConnectionRequest) -> None:
        if self._connection_thread is not None:
            return
        self.settings_view.set_busy(True)
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
        self.settings_view.set_accounts(result.accounts, result.current_account_id)
        self.account_status.set_accounts(result.accounts, result.current_account_id)
        self.settings_view.show_connection_success(len(result.accounts))

    @QtCore.pyqtSlot(str)
    def _on_connection_failure(self, message: str) -> None:
        self.settings_view.show_message(f"Connection failed: {humanize_ig_error(message)}")

    @QtCore.pyqtSlot()
    def _clear_connection_worker(self) -> None:
        self._connection_thread = None
        self._connection_worker = None
        self.settings_view.set_busy(False)

    @QtCore.pyqtSlot(object)
    def _save_non_secret_settings(self, config: object) -> None:
        try:
            path = default_config_path()
            save_config(config, path)
            self.settings_view.show_message(f"Non-secret settings saved to {path}")
        except Exception as exc:
            self.settings_view.show_message(f"Settings save failed: {exc}")


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
