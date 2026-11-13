"""GUI V2 settings, including secure API and data-provider management."""

from __future__ import annotations

from PyQt5 import QtCore, QtWidgets

from trading_ig_assistant.adapters.credentials import SecretValue
from trading_ig_assistant.app.config import AppConfig
from trading_ig_assistant.app.qt_api_credentials_controller import ApiCredentialsController
from trading_ig_assistant.domain.api_credentials import (
    ApiCredentialSource,
    ApiProviderState,
    ApiProviderStatus,
)
from trading_ig_assistant.ui.i18n.language_manager import LanguageManager
from trading_ig_assistant.ui.shell.page_specs import PAGE_SPEC_BY_KEY


class _ProviderRow(QtWidgets.QGroupBox):
    def __init__(self, state: ApiProviderState, controller: ApiCredentialsController) -> None:
        super().__init__(state.definition.display_name)
        self.provider_id = state.definition.provider_id
        self._controller = controller
        self._state = state
        layout = QtWidgets.QGridLayout(self)
        self.enabled = QtWidgets.QCheckBox("Activé")
        self.enabled.toggled.connect(
            lambda checked: controller.set_enabled(self.provider_id, checked)
        )
        self.key_edit = QtWidgets.QLineEdit()
        self.key_edit.setEchoMode(QtWidgets.QLineEdit.Password)
        self.show_button = QtWidgets.QPushButton("Afficher")
        self.show_button.setCheckable(True)
        self.show_button.toggled.connect(self._toggle_secret)
        self.save_button = QtWidgets.QPushButton("Enregistrer / remplacer")
        self.save_button.clicked.connect(self._save)
        self.delete_button = QtWidgets.QPushButton("Supprimer")
        self.delete_button.clicked.connect(
            lambda: controller.delete_api_key(self.provider_id)
        )
        self.test_button = QtWidgets.QPushButton("Tester la connexion")
        self.test_button.clicked.connect(
            lambda: controller.test_connection(self.provider_id)
        )
        self.status = QtWidgets.QLabel()
        self.details = QtWidgets.QLabel()
        self.details.setWordWrap(True)
        layout.addWidget(self.enabled, 0, 0)
        layout.addWidget(self.key_edit, 0, 1, 1, 3)
        layout.addWidget(self.show_button, 0, 4)
        layout.addWidget(self.save_button, 1, 1)
        layout.addWidget(self.delete_button, 1, 2)
        layout.addWidget(self.test_button, 1, 3)
        layout.addWidget(self.status, 1, 4)
        layout.addWidget(self.details, 2, 0, 1, 5)
        layout.setColumnStretch(3, 1)
        self.apply_state(state)

    def apply_state(self, state: ApiProviderState) -> None:
        self._state = state
        blocked = self.enabled.blockSignals(True)
        self.enabled.setChecked(state.enabled)
        self.enabled.blockSignals(blocked)
        public = not state.definition.requires_api_key
        for widget in (
            self.key_edit,
            self.show_button,
            self.save_button,
            self.delete_button,
        ):
            widget.setVisible(not public)
        self.key_edit.setPlaceholderText(
            "Clé enregistrée"
            if state.source is not ApiCredentialSource.NONE
            else "Clé API"
        )
        self.test_button.setEnabled(state.definition.connection_test_available)
        labels = {
            ApiProviderStatus.DISABLED: "Désactivé",
            ApiProviderStatus.CONNECTED: "Connecté",
            ApiProviderStatus.NOT_CONFIGURED: "Non configuré",
            ApiProviderStatus.ERROR: "Erreur",
            ApiProviderStatus.QUOTA_EXHAUSTED: "Quota atteint",
            ApiProviderStatus.PUBLIC: "Accès public",
            ApiProviderStatus.TESTING: "Test en cours",
        }
        status_text = labels[state.status]
        if (
            self.provider_id == "gdelt"
            and state.status is ApiProviderStatus.QUOTA_EXHAUSTED
        ):
            status_text = "Limité temporairement"
        self.status.setText(status_text)
        source = {
            ApiCredentialSource.KEYRING: "Coffre système",
            ApiCredentialSource.ENVIRONMENT: "Variable d’environnement (repli)",
            ApiCredentialSource.PUBLIC: "Sans clé",
            ApiCredentialSource.NONE: "Aucune clé",
        }[state.source]
        details = [f"Source : {source}"]
        if state.last_success_at_utc is not None:
            date = state.last_success_at_utc.astimezone().strftime("%Y-%m-%d %H:%M:%S")
            details.append(f"Dernier test réussi : {date}")
        if state.quota_used is not None:
            details.append(f"Consommation du test : {state.quota_used}")
        if state.quota_remaining is not None:
            details.append(f"Quota restant : {state.quota_remaining}")
        if state.definition.test_may_consume_quota:
            details.append("Le test explicite peut consommer du quota ; aucun test automatique.")
        if self.provider_id == "gdelt" and state.reason_code == "GDELT_RATE_LIMITED":
            details.append("Service public saturé (HTTP 429) ; réessayer plus tard.")
        self.details.setText(" · ".join(details))

    def set_test_busy(self, busy: bool) -> None:
        self.test_button.setEnabled(
            not busy and self._state.definition.connection_test_available
        )
        if busy:
            self.status.setText("Test en cours…")

    def reveal(self, secret: SecretValue) -> None:
        self.key_edit.setText(secret.reveal())
        self.key_edit.setEchoMode(QtWidgets.QLineEdit.Normal)
        self.show_button.setChecked(True)
        QtCore.QTimer.singleShot(8_000, self._hide_secret)

    def _toggle_secret(self, visible: bool) -> None:
        if visible and not self.key_edit.text():
            self._controller.reveal_api_key(self.provider_id)
            return
        self.key_edit.setEchoMode(
            QtWidgets.QLineEdit.Normal if visible else QtWidgets.QLineEdit.Password
        )

    def _hide_secret(self) -> None:
        self.key_edit.clear()
        self.key_edit.setEchoMode(QtWidgets.QLineEdit.Password)
        self.show_button.setChecked(False)

    def _save(self) -> None:
        value = self.key_edit.text().strip()
        if value:
            self._controller.set_api_key(self.provider_id, value)
            self._hide_secret()


class SettingsPage(QtWidgets.QWidget):
    locale_requested = QtCore.pyqtSignal(str)

    def __init__(
        self,
        language: LanguageManager,
        config: AppConfig,
        api_credentials_controller: ApiCredentialsController | None = None,
    ) -> None:
        super().__init__()
        self._language = language
        self._config = config
        self._api_controller = api_credentials_controller
        self._provider_rows: dict[str, _ProviderRow] = {}
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        self.title = QtWidgets.QLabel()
        font = self.title.font()
        font.setPointSize(16)
        font.setBold(True)
        self.title.setFont(font)
        layout.addWidget(self.title)
        self.tabs = QtWidgets.QTabWidget()
        self._summaries: list[QtWidgets.QLabel] = []
        self._summary_by_tab: dict[str, QtWidgets.QLabel] = {}
        for key in PAGE_SPEC_BY_KEY["settings"].tab_keys:
            if key == "tab.connections" and api_credentials_controller is not None:
                panel = self._build_provider_panel()
            elif key == "tab.interface":
                panel = self._build_interface_panel()
            else:
                panel = QtWidgets.QWidget()
                panel_layout = QtWidgets.QVBoxLayout(panel)
                summary = QtWidgets.QLabel()
                summary.setWordWrap(True)
                summary.setAlignment(QtCore.Qt.AlignTop)
                self._summaries.append(summary)
                self._summary_by_tab[key] = summary
                panel_layout.addWidget(summary)
                panel_layout.addStretch(1)
            self.tabs.addTab(panel, "")
        layout.addWidget(self.tabs, stretch=1)
        if api_credentials_controller is not None:
            api_credentials_controller.states_changed.connect(self._set_provider_states)
            api_credentials_controller.test_busy_changed.connect(self._set_test_busy)
            api_credentials_controller.secret_revealed.connect(self._reveal_secret)
            api_credentials_controller.error.connect(self._show_provider_error)
            api_credentials_controller.publish_states()
        self.retranslate_ui()

    def _build_provider_panel(self) -> QtWidgets.QWidget:
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(panel)
        notice = QtWidgets.QLabel(
            "Priorité : coffre système, puis variable d’environnement. "
            "Aucune clé n’est enregistrée dans JSON, YAML, SQLite ou les journaux."
        )
        notice.setWordWrap(True)
        layout.addWidget(notice)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        self.provider_container = QtWidgets.QWidget()
        self.provider_layout = QtWidgets.QVBoxLayout(self.provider_container)
        self.provider_layout.addStretch(1)
        scroll.setWidget(self.provider_container)
        layout.addWidget(scroll, 1)
        return panel

    def _build_interface_panel(self) -> QtWidgets.QWidget:
        panel = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(panel)
        self.locale_combo = QtWidgets.QComboBox()
        self.locale_combo.addItem("Français", "fr_FR")
        self.locale_combo.addItem("English", "en_US")
        locale_index = self.locale_combo.findData(self._language.locale)
        self.locale_combo.setCurrentIndex(max(0, locale_index))
        self.locale_combo.currentIndexChanged.connect(self._emit_locale)
        self.locale_label = QtWidgets.QLabel()
        self.theme_value = QtWidgets.QLabel("Dark")
        self.theme_label = QtWidgets.QLabel()
        form.addRow(self.locale_label, self.locale_combo)
        form.addRow(self.theme_label, self.theme_value)
        return panel

    def retranslate_ui(self) -> None:
        self.title.setText(self._language.text("nav.settings"))
        spec = PAGE_SPEC_BY_KEY["settings"]
        for index, key in enumerate(spec.tab_keys):
            self.tabs.setTabText(index, self._language.text(key))
        self.locale_label.setText(self._language.text("settings.language"))
        self.theme_label.setText(self._language.text("settings.theme"))
        mapping = {
            "tab.connections": "settings.connections_summary",
            "tab.markets": "settings.markets_summary",
            "tab.strategies": "settings.strategies_summary",
            "tab.risk": "settings.risk_summary",
            "tab.ai": "settings.ai_summary",
            "tab.notifications": "settings.notifications_summary",
            "tab.advanced": "settings.advanced_summary",
        }
        values = {
            "environment": self._config.environment.value.upper(),
            "bindings": len(self._config.product_market_bindings),
            "candidate": self._config.scanner_scoring.candidate_threshold,
            "watch": self._config.scanner_scoring.watch_threshold,
        }
        for tab_key, label in self._summary_by_tab.items():
            label.setText(self._language.text(mapping[tab_key]).format(**values))

    @QtCore.pyqtSlot(object)
    def _set_provider_states(self, value: object) -> None:
        if self._api_controller is None:
            return
        for state in value:
            if not isinstance(state, ApiProviderState):
                continue
            row = self._provider_rows.get(state.definition.provider_id)
            if row is None:
                row = _ProviderRow(state, self._api_controller)
                self._provider_rows[state.definition.provider_id] = row
                self.provider_layout.insertWidget(self.provider_layout.count() - 1, row)
            else:
                row.apply_state(state)

    @QtCore.pyqtSlot(str, bool)
    def _set_test_busy(self, provider_id: str, busy: bool) -> None:
        if row := self._provider_rows.get(provider_id):
            row.set_test_busy(busy)

    @QtCore.pyqtSlot(str, object)
    def _reveal_secret(self, provider_id: str, value: object) -> None:
        row = self._provider_rows.get(provider_id)
        if row is not None and isinstance(value, SecretValue):
            row.reveal(value)

    @QtCore.pyqtSlot(str, str)
    def _show_provider_error(self, provider_id: str, reason_code: str) -> None:
        row = self._provider_rows.get(provider_id)
        if row is not None:
            row.status.setText(f"Erreur : {reason_code}")

    @QtCore.pyqtSlot(int)
    def _emit_locale(self, index: int) -> None:
        locale = self.locale_combo.itemData(index)
        if locale:
            self.locale_requested.emit(str(locale))
