"""Application settings dialog.

The first tab stores IG connection profiles. Secrets are saved only through the credential store;
the JSON config receives non-secret profile metadata.
"""

from __future__ import annotations

from PyQt5 import QtCore, QtWidgets

from trading_ig_assistant.adapters.credentials import IGCredentials
from trading_ig_assistant.app.config import AppConfig, IGConnectionProfileConfig, IGEnvironment


class SettingsDialog(QtWidgets.QDialog):
    config_applied = QtCore.pyqtSignal(object)

    def __init__(
        self,
        config: AppConfig,
        credential_store: object | None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Trading IG Assistant Settings")
        self.resize(620, 420)
        self._config = config
        self._credential_store = credential_store
        self._profile_tabs: dict[IGEnvironment, ConnectionProfileWidget] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        self.tabs = QtWidgets.QTabWidget()
        credentials_tab = QtWidgets.QWidget()
        credentials_layout = QtWidgets.QVBoxLayout(credentials_tab)

        for environment in (IGEnvironment.LIVE, IGEnvironment.DEMO):
            profile = self._config.connection_profiles[environment]
            editor = ConnectionProfileWidget(environment, profile)
            self._profile_tabs[environment] = editor
            credentials_layout.addWidget(editor)

        credentials_layout.addStretch(1)
        self.tabs.addTab(credentials_tab, "IG credentials")
        self.tabs.addTab(_placeholder_tab(), "Application")
        layout.addWidget(self.tabs)

        self.status = QtWidgets.QLabel("")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        buttons = QtWidgets.QHBoxLayout()
        buttons.addStretch(1)
        self.apply_button = QtWidgets.QPushButton("Apply")
        self.save_button = QtWidgets.QPushButton("Save")
        self.close_button = QtWidgets.QPushButton("Close")
        self.apply_button.clicked.connect(self.apply)
        self.save_button.clicked.connect(self.save_and_close)
        self.close_button.clicked.connect(self.close)
        buttons.addWidget(self.apply_button)
        buttons.addWidget(self.save_button)
        buttons.addWidget(self.close_button)
        layout.addLayout(buttons)

    def apply(self) -> None:
        config = self.updated_config()
        try:
            self._save_credentials(config)
        except Exception as exc:
            self.status.setText(f"Credential save failed: {exc}")
            return

        self._config = config
        self.status.setText("Settings applied. Secrets are stored in the OS keyring.")
        self.config_applied.emit(config)

    def save_and_close(self) -> None:
        self.apply()
        if not self.status.text().startswith("Credential save failed"):
            self.accept()

    def updated_config(self) -> AppConfig:
        profiles = {
            environment: editor.profile_config()
            for environment, editor in self._profile_tabs.items()
        }
        return AppConfig(
            environment=self._config.environment,
            connection_profiles=profiles,
            read_only=True,
            enable_live_trading=False,
        )

    def _save_credentials(self, config: AppConfig) -> None:
        if self._credential_store is None:
            if any(editor.has_secret_values() for editor in self._profile_tabs.values()):
                raise RuntimeError("No OS keyring credential store is available.")
            return

        for environment, editor in self._profile_tabs.items():
            identifier = config.connection_profiles[environment].identifier
            if not identifier or not editor.has_secret_values():
                continue
            if not editor.password() or not editor.api_key():
                raise ValueError(f"{environment.value} password and API key must both be filled.")
            credentials = IGCredentials(
                username=identifier,
                password=editor.password(),
                api_key=editor.api_key(),
            )
            self._credential_store.save_profile(environment.value, credentials)


class ConnectionProfileWidget(QtWidgets.QGroupBox):
    def __init__(
        self,
        environment: IGEnvironment,
        profile: IGConnectionProfileConfig,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(environment.value.upper(), parent)
        self._environment = environment
        form = QtWidgets.QFormLayout(self)

        self.identifier = QtWidgets.QLineEdit(profile.identifier)
        self.identifier.setPlaceholderText("API identifier")
        self.password_field = QtWidgets.QLineEdit()
        self.password_field.setEchoMode(QtWidgets.QLineEdit.Password)
        self.password_field.setPlaceholderText("Leave blank to keep stored password")
        self.api_key_field = QtWidgets.QLineEdit()
        self.api_key_field.setEchoMode(QtWidgets.QLineEdit.Password)
        self.api_key_field.setPlaceholderText("Leave blank to keep stored API key")
        self.selected_account_id = QtWidgets.QLineEdit(profile.selected_account_id or "")
        self.selected_account_id.setPlaceholderText("Filled after account selection")

        form.addRow("API identifier", self.identifier)
        form.addRow("Password", self.password_field)
        form.addRow("API key", self.api_key_field)
        form.addRow("Selected account ID", self.selected_account_id)

    def profile_config(self) -> IGConnectionProfileConfig:
        return IGConnectionProfileConfig(
            environment=self._environment,
            identifier=self.identifier.text().strip(),
            selected_account_id=self.selected_account_id.text().strip() or None,
        )

    def has_secret_values(self) -> bool:
        return bool(self.password() or self.api_key())

    def password(self) -> str:
        return self.password_field.text()

    def api_key(self) -> str:
        return self.api_key_field.text().strip()


def _placeholder_tab() -> QtWidgets.QWidget:
    widget = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(widget)
    label = QtWidgets.QLabel("Future application settings will be added here.")
    label.setWordWrap(True)
    layout.addWidget(label)
    layout.addStretch(1)
    return widget
