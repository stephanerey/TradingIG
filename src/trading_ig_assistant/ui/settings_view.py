"""Thin settings placeholder view."""

from __future__ import annotations

from PyQt5 import QtCore, QtWidgets

from trading_ig_assistant.app.config import AppConfig, IGEnvironment
from trading_ig_assistant.domain.instruments import Account
from trading_ig_assistant.services.ig_connection_service import IGConnectionRequest


def mask_identifier(value: str | None) -> str:
    if not value:
        return "unknown"
    if len(value) <= 4:
        return "****"
    return f"{value[:2]}...{value[-2:]}"


class SettingsView(QtWidgets.QWidget):
    connection_requested = QtCore.pyqtSignal(object)
    save_requested = QtCore.pyqtSignal(object)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()
        layout.addLayout(form)

        self.environment = QtWidgets.QComboBox()
        self.environment.addItems(["demo", "live"])
        self.environment.setCurrentText("demo")

        self.username = QtWidgets.QLineEdit()
        self.username.setPlaceholderText("IG username")

        self.password = QtWidgets.QLineEdit()
        self.password.setPlaceholderText("Used in memory only for read-only validation")
        self.password.setEchoMode(QtWidgets.QLineEdit.Password)

        self.api_key = QtWidgets.QLineEdit()
        self.api_key.setPlaceholderText("Used in memory only for read-only validation")
        self.api_key.setEchoMode(QtWidgets.QLineEdit.Password)

        self.selected_account = QtWidgets.QComboBox()
        self.selected_account.addItem("No account selected")

        self.read_only = QtWidgets.QCheckBox("Read-only mode")
        self.read_only.setChecked(True)
        self.read_only.setEnabled(False)

        self.execution_status = QtWidgets.QLabel("Live trading disabled")
        self.execution_status.setAlignment(QtCore.Qt.AlignCenter)
        self.execution_status.setStyleSheet(
            "QLabel { color: #8a1c1c; background: #fde7e7; padding: 6px; font-weight: 700; }"
        )

        self.connection_status = QtWidgets.QLabel("Not connected")
        self.connection_status.setWordWrap(True)

        self.connect_button = QtWidgets.QPushButton("Test read-only IG connection")
        self.save_button = QtWidgets.QPushButton("Save non-secret settings")
        self.connect_button.clicked.connect(self._emit_connection_requested)
        self.save_button.clicked.connect(self._emit_save_requested)

        form.addRow("Environment", self.environment)
        form.addRow("Username", self.username)
        form.addRow("Password", self.password)
        form.addRow("API key", self.api_key)
        form.addRow("Selected account", self.selected_account)
        form.addRow("Mode", self.read_only)
        form.addRow("Execution", self.execution_status)
        form.addRow("Connection", self.connection_status)

        layout.addWidget(self.connect_button)
        layout.addWidget(self.save_button)
        layout.addStretch(1)

    def connection_request(self) -> IGConnectionRequest:
        return IGConnectionRequest(
            environment=IGEnvironment(self.environment.currentText()),
            username=self.username.text().strip(),
            password=self.password.text(),
            api_key=self.api_key.text(),
        )

    def safe_config(self) -> AppConfig:
        return AppConfig(
            environment=IGEnvironment(self.environment.currentText()),
            ig_username=self.username.text().strip(),
            selected_account_id=self.selected_account.currentData(),
            read_only=True,
            enable_live_trading=False,
        )

    def set_busy(self, busy: bool) -> None:
        self.connect_button.setEnabled(not busy)
        self.save_button.setEnabled(not busy)
        if busy:
            self.connection_status.setText("Connecting to IG in read-only mode...")

    def set_accounts(self, accounts: list[Account], current_account_id: str | None) -> None:
        self.selected_account.clear()
        if not accounts:
            self.selected_account.addItem("No account returned", None)
            return

        selected_index = 0
        for index, account in enumerate(accounts):
            label = (
                f"{account.account_name or 'IG account'} "
                f"({account.account_type or 'type unknown'}, {mask_identifier(account.account_id)})"
            )
            self.selected_account.addItem(label, account.account_id)
            if account.account_id == current_account_id:
                selected_index = index
        self.selected_account.setCurrentIndex(selected_index)

    def show_connection_success(self, accounts_count: int) -> None:
        self.connection_status.setText(
            f"Connected in read-only mode. Accounts fetched: {accounts_count}."
        )

    def show_message(self, message: str) -> None:
        self.connection_status.setText(message)

    def _emit_connection_requested(self) -> None:
        request = self.connection_request()
        if not request.username or not request.password or not request.api_key:
            self.show_message("Username, password, and API key are required.")
            return
        self.connection_requested.emit(request)

    def _emit_save_requested(self) -> None:
        self.save_requested.emit(self.safe_config())
