"""Thin settings placeholder view."""

from __future__ import annotations

from PyQt5 import QtCore, QtWidgets


class SettingsView(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        form = QtWidgets.QFormLayout(self)

        self.environment = QtWidgets.QComboBox()
        self.environment.addItems(["demo", "live"])
        self.environment.setCurrentText("demo")

        self.username = QtWidgets.QLineEdit()
        self.username.setPlaceholderText("IG username")

        self.password = QtWidgets.QLineEdit()
        self.password.setPlaceholderText("Stored securely later; env var in P01")
        self.password.setEchoMode(QtWidgets.QLineEdit.Password)

        self.api_key = QtWidgets.QLineEdit()
        self.api_key.setPlaceholderText("Stored securely later; env var in P01")
        self.api_key.setEchoMode(QtWidgets.QLineEdit.Password)

        self.selected_account = QtWidgets.QComboBox()
        self.selected_account.addItem("No account selected")

        self.read_only = QtWidgets.QCheckBox("Read-only mode")
        self.read_only.setChecked(True)
        self.read_only.setEnabled(False)

        live_disabled = QtWidgets.QLabel("Live trading disabled")
        live_disabled.setAlignment(QtCore.Qt.AlignCenter)
        live_disabled.setStyleSheet(
            "QLabel { color: #8a1c1c; background: #fde7e7; padding: 6px; font-weight: 700; }"
        )

        form.addRow("Environment", self.environment)
        form.addRow("Username", self.username)
        form.addRow("Password", self.password)
        form.addRow("API key", self.api_key)
        form.addRow("Selected account", self.selected_account)
        form.addRow("Mode", self.read_only)
        form.addRow("Execution", live_disabled)
