"""Application settings dialog.

The first tab stores IG connection profiles. Secrets are saved only through the credential store;
the JSON config receives non-secret profile metadata.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from PyQt5 import QtCore, QtWidgets

from trading_ig_assistant.adapters.credentials import IGCredentials, SecretValue
from trading_ig_assistant.app.config import (
    AppConfig,
    IGConnectionProfileConfig,
    IGEnvironment,
    ScannerExecutionCostConfig,
    ScannerScoringConfig,
)
from trading_ig_assistant.domain.ai_context import AIAnalysisStatus, MarketContextSnapshot
from trading_ig_assistant.domain.context_sources import ProviderCollectionStatus
from trading_ig_assistant.services.openai_context_probe_service import (
    run_openai_context_probe,
)
from trading_ig_assistant.services.trading_economics_calendar_runtime import (
    TradingEconomicsRuntimeConfig,
    TradingEconomicsRuntimeResult,
    refresh_trading_economics_calendar,
)
from trading_ig_assistant.ui.economic_calendar_refresh import (
    CalendarRuntimeRunner,
    EconomicCalendarRefreshWorker,
)

OpenAIProbeRunner = Callable[..., MarketContextSnapshot]
OpenAIKeyReader = Callable[[], str]
CalendarKeyReader = Callable[[], str]

IG_FR_INDICATIVE_SCANNER_FEES = ScannerExecutionCostConfig(
    cash_or_dfb_fee_per_unit_per_side=Decimal("0"),
    barrier_fee_per_unit_per_side=Decimal("0.1"),
    option_fee_per_unit_per_side=Decimal("0.1"),
    unknown_fee_per_unit_per_side=None,
    defaults_initialized=True,
)


class SettingsDialog(QtWidgets.QDialog):
    config_applied = QtCore.pyqtSignal(object)
    openai_runtime_validated = QtCore.pyqtSignal(str, int, bool)
    calendar_runtime_validated = QtCore.pyqtSignal(object)

    def __init__(
        self,
        config: AppConfig,
        credential_store: object | None,
        parent: QtWidgets.QWidget | None = None,
        *,
        openai_probe_runner: OpenAIProbeRunner = run_openai_context_probe,
        openai_key_reader: OpenAIKeyReader | None = None,
        calendar_probe_runner: CalendarRuntimeRunner = refresh_trading_economics_calendar,
        calendar_key_reader: CalendarKeyReader | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Trading IG Assistant Settings")
        self.resize(620, 420)
        self._config = config
        self._credential_store = credential_store
        self._openai_probe_runner = openai_probe_runner
        self._openai_key_reader = openai_key_reader or (
            lambda: os.environ.get("OPENAI_API_KEY", "")
        )
        self._calendar_probe_runner = calendar_probe_runner
        self._calendar_key_reader = calendar_key_reader or (
            lambda: os.environ.get("TRADING_ECONOMICS_API_KEY", "")
        )
        self._openai_thread: QtCore.QThread | None = None
        self._openai_worker: OpenAIProbeWorker | None = None
        self._openai_probe_request: tuple[str, int, bool] | None = None
        self._calendar_thread: QtCore.QThread | None = None
        self._calendar_worker: EconomicCalendarRefreshWorker | None = None
        self._profile_tabs: dict[IGEnvironment, ConnectionProfileWidget] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        self.tabs = QtWidgets.QTabWidget()
        credentials_tab = QtWidgets.QWidget()
        credentials_layout = QtWidgets.QVBoxLayout(credentials_tab)

        for environment in (IGEnvironment.LIVE, IGEnvironment.DEMO):
            profile = self._config.connection_profiles[environment]
            editor = ConnectionProfileWidget(environment, profile, self._credential_store)
            self._profile_tabs[environment] = editor
            credentials_layout.addWidget(editor)

        credentials_layout.addStretch(1)
        self.tabs.addTab(credentials_tab, "IG credentials")
        self.openai_settings = OpenAISettingsWidget(api_key_present=bool(self._openai_key_reader()))
        self.openai_settings.test_requested.connect(self._start_openai_probe)
        self.tabs.addTab(self.openai_settings, "OpenAI")
        self.calendar_settings = TradingEconomicsSettingsWidget(
            api_key_present=bool(self._calendar_key_reader())
        )
        self.calendar_settings.test_requested.connect(self._start_calendar_probe)
        self.tabs.addTab(self.calendar_settings, "Calendrier macro")
        self.scanner_cost_settings = ScannerExecutionCostSettingsWidget(
            self._config.scanner_execution_costs
        )
        self.tabs.addTab(self.scanner_cost_settings, "Coûts Scanner")
        self.scanner_scoring_settings = ScannerScoringSettingsWidget(self._config.scanner_scoring)
        self.tabs.addTab(self.scanner_scoring_settings, "Score Scanner")
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

    @QtCore.pyqtSlot(str, int)
    def _start_openai_probe(self, model: str, max_output_tokens: int) -> None:
        if self._openai_thread is not None or self._calendar_thread is not None:
            return
        api_key = self._openai_key_reader()
        if not api_key:
            self.openai_settings.set_key_present(False)
            self.openai_settings.show_failure(
                "OPENAI_API_KEY est absente du processus. Redémarrez l'application après "
                "avoir défini la variable."
            )
            return

        self._openai_probe_request = (
            model,
            max_output_tokens,
            self.openai_settings.periodic_refresh.isChecked(),
        )
        thread = QtCore.QThread(self)
        worker = OpenAIProbeWorker(
            runner=self._openai_probe_runner,
            model=model,
            api_key=SecretValue(api_key),
            max_output_tokens=max_output_tokens,
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.completed.connect(self._handle_openai_probe_result)
        worker.failed.connect(self.openai_settings.show_failure)
        worker.completed.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.completed.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(self._finish_openai_probe)
        thread.finished.connect(thread.deleteLater)
        self._openai_thread = thread
        self._openai_worker = worker
        self._set_openai_busy(True)
        thread.start()

    @QtCore.pyqtSlot(object)
    def _handle_openai_probe_result(self, snapshot: MarketContextSnapshot) -> None:
        analysis = snapshot.ai_analysis
        if analysis.status is AIAnalysisStatus.AVAILABLE:
            periodic_enabled = bool(
                self._openai_probe_request is not None and self._openai_probe_request[2]
            )
            runtime_message = (
                " Le contexte officiel sera analysé toutes les 15 minutes pendant cette session."
                if periodic_enabled
                else " Le contexte réel reste déclenché manuellement."
            )
            self.openai_settings.show_success(
                "Connexion validée. Réponse structurée reçue avec "
                f"{analysis.model_id}. Aucune donnée IG n'a été transmise."
                f"{runtime_message}"
            )
            if self._openai_probe_request is not None:
                self.openai_runtime_validated.emit(*self._openai_probe_request)
            return
        reasons = ", ".join(snapshot.reason_codes) or "AI_PROVIDER_ERROR"
        self.openai_settings.show_failure(
            f"OpenAI est indisponible ou la réponse a été refusée. Codes sûrs : {reasons}."
        )

    @QtCore.pyqtSlot()
    def _finish_openai_probe(self) -> None:
        self._openai_thread = None
        self._openai_worker = None
        self._openai_probe_request = None
        self._set_openai_busy(False)

    def _set_openai_busy(self, busy: bool) -> None:
        self.openai_settings.set_busy(busy)
        self._update_dialog_buttons()

    @QtCore.pyqtSlot(object)
    def _start_calendar_probe(self, config: TradingEconomicsRuntimeConfig) -> None:
        if self._calendar_thread is not None or self._openai_thread is not None:
            return
        api_key = self._calendar_key_reader()
        if not api_key:
            self.calendar_settings.set_key_present(False)
            self.calendar_settings.show_failure(
                "TRADING_ECONOMICS_API_KEY est absente du processus. Redémarrez l'application "
                "après avoir défini la variable."
            )
            return
        thread = QtCore.QThread(self)
        worker = EconomicCalendarRefreshWorker(
            api_key=SecretValue(api_key),
            config=config,
            runner=self._calendar_probe_runner,
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.completed.connect(self._handle_calendar_probe_result)
        worker.failed.connect(self.calendar_settings.show_failure)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(self._finish_calendar_probe)
        thread.finished.connect(thread.deleteLater)
        self._calendar_thread = thread
        self._calendar_worker = worker
        self._set_calendar_busy(True)
        thread.start()

    @QtCore.pyqtSlot(object)
    def _handle_calendar_probe_result(self, result: object) -> None:
        if not isinstance(result, TradingEconomicsRuntimeResult):
            self.calendar_settings.show_failure("Résultat calendrier invalide.")
            return
        if result.snapshot.status is ProviderCollectionStatus.AVAILABLE:
            self.calendar_settings.show_success(
                "Connexion validée : "
                f"{len(result.snapshot.events)} événement(s) normalisé(s). Les droits "
                "d'utilisation restent UNKNOWN jusqu'à qualification de l'abonnement."
            )
            self.calendar_runtime_validated.emit(result)
            return
        reasons = ", ".join(result.snapshot.reason_codes) or "CALENDAR_PROVIDER_ERROR"
        self.calendar_settings.show_failure(f"Calendrier indisponible. Diagnostic sûr : {reasons}.")

    @QtCore.pyqtSlot()
    def _finish_calendar_probe(self) -> None:
        self._calendar_thread = None
        self._calendar_worker = None
        self._set_calendar_busy(False)

    def _set_calendar_busy(self, busy: bool) -> None:
        self.calendar_settings.set_busy(busy)
        self._update_dialog_buttons()

    def _update_dialog_buttons(self) -> None:
        idle = self._openai_thread is None and self._calendar_thread is None
        self.apply_button.setEnabled(idle)
        self.save_button.setEnabled(idle)
        self.close_button.setEnabled(idle)

    def closeEvent(self, event) -> None:
        if self._openai_thread is not None or self._calendar_thread is not None:
            self.status.setText(
                "Un test réseau est en cours ; attendez sa fin avant de fermer cette fenêtre."
            )
            event.ignore()
            return
        super().closeEvent(event)

    def apply(self) -> bool:
        try:
            config = self.updated_config()
            self._save_credentials(config)
        except (ValueError, InvalidOperation) as exc:
            self.status.setText(f"Configuration invalide : {exc}")
            return False
        except Exception as exc:
            self.status.setText(f"Credential save failed: {exc}")
            return False

        self._config = config
        self.status.setText("Settings applied. Secrets are stored in the OS keyring.")
        self.config_applied.emit(config)
        return True

    def save_and_close(self) -> None:
        if self.apply():
            self.accept()

    def updated_config(self) -> AppConfig:
        profiles = {
            environment: editor.profile_config()
            for environment, editor in self._profile_tabs.items()
        }
        return AppConfig(
            environment=self._config.environment,
            ig_username=self._config.ig_username,
            ig_password=self._config.ig_password,
            ig_api_key=self._config.ig_api_key,
            selected_account_id=self._config.selected_account_id,
            last_selected_product_epic=self._config.last_selected_product_epic,
            chart_source_overrides=dict(self._config.chart_source_overrides),
            product_market_bindings=self._config.product_market_bindings,
            connection_profiles=profiles,
            workspace=self._config.workspace,
            scanner_execution_costs=self.scanner_cost_settings.config(),
            scanner_scoring=self.scanner_scoring_settings.config(),
            scanner_profiles=self._config.scanner_profiles,
            read_only=True,
            enable_live_trading=False,
        )

    def _save_credentials(self, config: AppConfig) -> None:
        if self._credential_store is None:
            if any(editor.has_secret_values() for editor in self._profile_tabs.values()):
                raise RuntimeError(
                    "No secure credential store is available. Install keyring in this venv "
                    "or run on Windows with Credential Manager available."
                )
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


class ScannerExecutionCostSettingsWidget(QtWidgets.QWidget):
    """Manual, optional scanner fee estimates; blank always means unknown."""

    def __init__(
        self,
        config: ScannerExecutionCostConfig,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        displayed_config = config if config.defaults_initialized else IG_FR_INDICATIVE_SCANNER_FEES
        layout = QtWidgets.QVBoxLayout(self)
        explanation = QtWidgets.QLabel(
            "Frais estimés dans la devise du produit, par unité et par côté. "
            "Laissez un champ vide si le tarif n'est pas qualifié : le score Coûts restera "
            "gris/inconnu. La valeur 0 doit être saisie explicitement."
        )
        explanation.setWordWrap(True)
        layout.addWidget(explanation)

        form = QtWidgets.QFormLayout()
        self.cash_or_dfb_fee = _optional_decimal_field(
            displayed_config.cash_or_dfb_fee_per_unit_per_side
        )
        self.barrier_fee = _optional_decimal_field(displayed_config.barrier_fee_per_unit_per_side)
        self.option_fee = _optional_decimal_field(displayed_config.option_fee_per_unit_per_side)
        self.unknown_fee = _optional_decimal_field(displayed_config.unknown_fee_per_unit_per_side)
        form.addRow("CFD / DFB", self.cash_or_dfb_fee)
        form.addRow("Barrières", self.barrier_fee)
        form.addRow("Options", self.option_fee)
        form.addRow("Type inconnu", self.unknown_fee)
        layout.addLayout(form)

        self.restore_indicative_button = QtWidgets.QPushButton(
            "Rétablir les valeurs indicatives IG France"
        )
        self.restore_indicative_button.clicked.connect(self._restore_indicative_values)
        layout.addWidget(self.restore_indicative_button)

        warning = QtWidgets.QLabel(
            "Profil indicatif consulté le 05/11/2026 : CFD/DFB hors actions = 0 (spread traité "
            "séparément), Barrières = 0,1, Options = 0,1. Ne couvre pas actions, financement "
            "overnight, coût KO ni stop garanti. Vérifiez toujours les conditions du produit. "
            "Ces valeurs ne modifient aucun ticket et ne déclenchent aucun ordre."
        )
        warning.setWordWrap(True)
        warning.setStyleSheet("QLabel { color: #4f5965; font-size: 11px; }")
        layout.addWidget(warning)
        layout.addStretch(1)

    def config(self) -> ScannerExecutionCostConfig:
        return ScannerExecutionCostConfig(
            cash_or_dfb_fee_per_unit_per_side=_parse_optional_decimal(
                self.cash_or_dfb_fee.text(), "Frais CFD / DFB"
            ),
            barrier_fee_per_unit_per_side=_parse_optional_decimal(
                self.barrier_fee.text(), "Frais Barrières"
            ),
            option_fee_per_unit_per_side=_parse_optional_decimal(
                self.option_fee.text(), "Frais Options"
            ),
            unknown_fee_per_unit_per_side=_parse_optional_decimal(
                self.unknown_fee.text(), "Frais type inconnu"
            ),
            defaults_initialized=True,
        )

    @QtCore.pyqtSlot()
    def _restore_indicative_values(self) -> None:
        self.cash_or_dfb_fee.setText("0")
        self.barrier_fee.setText("0.1")
        self.option_fee.setText("0.1")
        self.unknown_fee.clear()


class ScannerScoringSettingsWidget(QtWidgets.QWidget):
    """Editable global weights and recommendation thresholds from the PRD defaults."""

    def __init__(
        self,
        config: ScannerScoringConfig,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        explanation = QtWidgets.QLabel(
            "Poids globaux du classement Scanner. Le score reste un classement explicable, "
            "jamais une probabilité de gain. Une composante inconnue conserve NO_TRADE même si "
            "son poids est nul."
        )
        explanation.setWordWrap(True)
        layout.addWidget(explanation)

        weights = QtWidgets.QGroupBox("Poids des composantes")
        weight_form = QtWidgets.QFormLayout(weights)
        self.technical_weight = _required_decimal_field(config.technical_weight)
        self.context_weight = _required_decimal_field(config.context_weight)
        self.reward_risk_weight = _required_decimal_field(config.reward_risk_weight)
        self.market_risk_weight = _required_decimal_field(config.market_risk_weight)
        self.execution_cost_weight = _required_decimal_field(config.execution_cost_weight)
        self.data_quality_weight = _required_decimal_field(config.data_quality_weight)
        weight_form.addRow("Technique", self.technical_weight)
        weight_form.addRow("Contexte / sentiment", self.context_weight)
        weight_form.addRow("Potentiel R/R", self.reward_risk_weight)
        weight_form.addRow("Risque marché", self.market_risk_weight)
        weight_form.addRow("Coûts / exécution", self.execution_cost_weight)
        weight_form.addRow("Qualité des données", self.data_quality_weight)
        layout.addWidget(weights)

        thresholds = QtWidgets.QGroupBox("Seuils de décision")
        threshold_form = QtWidgets.QFormLayout(thresholds)
        self.candidate_threshold = _required_decimal_field(config.candidate_threshold)
        self.watch_threshold = _required_decimal_field(config.watch_threshold)
        threshold_form.addRow("Candidate si score ≥", self.candidate_threshold)
        threshold_form.addRow("Watch si score ≥", self.watch_threshold)
        threshold_form.addRow("Reject / NO_TRADE", QtWidgets.QLabel("score < seuil Watch"))
        layout.addWidget(thresholds)
        layout.addStretch(1)

    def config(self) -> ScannerScoringConfig:
        return ScannerScoringConfig(
            technical_weight=_parse_required_decimal(
                self.technical_weight.text(), "Poids Technique"
            ),
            context_weight=_parse_required_decimal(self.context_weight.text(), "Poids Contexte"),
            reward_risk_weight=_parse_required_decimal(self.reward_risk_weight.text(), "Poids R/R"),
            market_risk_weight=_parse_required_decimal(
                self.market_risk_weight.text(), "Poids Risque marché"
            ),
            execution_cost_weight=_parse_required_decimal(
                self.execution_cost_weight.text(), "Poids Coûts"
            ),
            data_quality_weight=_parse_required_decimal(
                self.data_quality_weight.text(), "Poids Qualité"
            ),
            candidate_threshold=_parse_required_decimal(
                self.candidate_threshold.text(), "Seuil Candidate"
            ),
            watch_threshold=_parse_required_decimal(self.watch_threshold.text(), "Seuil Watch"),
        )


class ConnectionProfileWidget(QtWidgets.QGroupBox):
    def __init__(
        self,
        environment: IGEnvironment,
        profile: IGConnectionProfileConfig,
        credential_store: object | None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(environment.value.upper(), parent)
        self._environment = environment
        self._credential_store = credential_store
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
        self.selected_account_id.setReadOnly(True)
        self.selected_account_id.setPlaceholderText("Updated from the top account dropdown")
        self.diagnostic = QtWidgets.QLabel("")
        self.diagnostic.setWordWrap(True)
        self.diagnostic.setStyleSheet("QLabel { color: #4f5965; font-size: 11px; }")

        form.addRow("API identifier", self.identifier)
        form.addRow("Password", self.password_field)
        form.addRow("API key", self.api_key_field)
        form.addRow("Last selected account", self.selected_account_id)
        form.addRow("Status", self.diagnostic)

        self.identifier.textChanged.connect(self._update_diagnostic)
        self.password_field.textChanged.connect(self._update_diagnostic)
        self.api_key_field.textChanged.connect(self._update_diagnostic)
        self._update_diagnostic()

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

    def _update_diagnostic(self) -> None:
        identifier_present = bool(self.identifier.text().strip())
        password_present = bool(self.password_field.text().strip())
        api_key_present = bool(self.api_key_field.text().strip())
        stored_present = self._stored_credentials_present()
        self.diagnostic.setText(
            "Profile status: "
            f"ID={'OK' if identifier_present else 'MISSING'}, "
            f"password={_status_text(password_present, stored_present)}, "
            f"API key={'OK' if api_key_present else ('STORED' if stored_present else 'MISSING')}."
        )

    def _stored_credentials_present(self) -> bool:
        if self._credential_store is None:
            return False
        loader = getattr(self._credential_store, "load_profile", None)
        if loader is None:
            return False
        identifier = self.identifier.text().strip()
        if not identifier:
            return False
        try:
            return loader(self._environment.value, identifier) is not None
        except Exception:
            return False


def _status_text(is_present: bool, stored_present: bool) -> str:
    if is_present:
        return "OK"
    if stored_present:
        return "STORED"
    return "MISSING"


class OpenAISettingsWidget(QtWidgets.QWidget):
    """Explicit, validation-only OpenAI settings panel."""

    test_requested = QtCore.pyqtSignal(str, int)

    def __init__(
        self,
        *,
        api_key_present: bool,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._key_present = api_key_present
        self._busy = False
        layout = QtWidgets.QVBoxLayout(self)

        title = QtWidgets.QLabel("Validation de la connexion OpenAI")
        title.setStyleSheet("QLabel { font-weight: 600; }")
        layout.addWidget(title)

        explanation = QtWidgets.QLabel(
            "Ce test manuel envoie uniquement un contexte synthétique borné. Il n'envoie aucune "
            "donnée de compte, de marché IG, de ticket ou d'ordre et n'active pas l'IA dans le "
            "scanner."
        )
        explanation.setWordWrap(True)
        layout.addWidget(explanation)

        self.key_status = QtWidgets.QLabel()
        self.key_status.setWordWrap(True)
        layout.addWidget(self.key_status)

        form = QtWidgets.QFormLayout()
        self.model = QtWidgets.QComboBox()
        self.model.setEditable(True)
        self.model.addItem("")
        self.model.addItem("gpt-6-luna")
        self.model.lineEdit().setPlaceholderText("Choisir ou saisir un modèle exact")
        self.max_output_tokens = QtWidgets.QSpinBox()
        self.max_output_tokens.setRange(1, 2_000)
        self.max_output_tokens.setValue(600)
        self.max_output_tokens.setSuffix(" tokens max")
        form.addRow("Modèle", self.model)
        form.addRow("Limite de sortie", self.max_output_tokens)
        layout.addLayout(form)

        self.acknowledgement = QtWidgets.QCheckBox(
            "J'autorise un appel OpenAI unique potentiellement facturé avec ces métadonnées "
            "synthétiques."
        )
        layout.addWidget(self.acknowledgement)

        self.periodic_refresh = QtWidgets.QCheckBox(
            "Après validation, j'autorise l'analyse du contexte officiel toutes les 15 minutes "
            "pendant cette session uniquement."
        )
        self.periodic_refresh.setToolTip(
            "Non persisté. Aucun compte, ticket ou ordre n'est transmis. Le premier cycle "
            "automatique intervient 15 minutes après la validation."
        )
        layout.addWidget(self.periodic_refresh)

        self.test_button = QtWidgets.QPushButton("Tester la connexion OpenAI")
        self.test_button.clicked.connect(self._request_test)
        layout.addWidget(self.test_button)

        self.result = QtWidgets.QLabel("Aucun test lancé.")
        self.result.setWordWrap(True)
        self.result.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        layout.addWidget(self.result)
        layout.addStretch(1)

        self.model.currentTextChanged.connect(self._update_test_button)
        self.acknowledgement.toggled.connect(self._update_test_button)
        self.set_key_present(api_key_present)

    def set_key_present(self, present: bool) -> None:
        self._key_present = present
        if present:
            self.key_status.setText(
                "OPENAI_API_KEY : DÉTECTÉE dans l'environnement du processus (valeur masquée)."
            )
            self.key_status.setStyleSheet("QLabel { color: #176b2c; }")
        else:
            self.key_status.setText(
                "OPENAI_API_KEY : ABSENTE du processus. La clé n'est ni saisie ni stockée ici."
            )
            self.key_status.setStyleSheet("QLabel { color: #9b1c1c; }")
        self._update_test_button()

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.model.setEnabled(not busy)
        self.max_output_tokens.setEnabled(not busy)
        self.acknowledgement.setEnabled(not busy)
        self.periodic_refresh.setEnabled(not busy)
        if busy:
            self.result.setText("Test OpenAI en cours…")
            self.result.setStyleSheet("")
        self._update_test_button()

    @QtCore.pyqtSlot(str)
    def show_success(self, message: str) -> None:
        self.result.setText(message)
        self.result.setStyleSheet("QLabel { color: #176b2c; font-weight: 600; }")

    @QtCore.pyqtSlot(str)
    def show_failure(self, message: str) -> None:
        self.result.setText(message)
        self.result.setStyleSheet("QLabel { color: #9b1c1c; font-weight: 600; }")

    @QtCore.pyqtSlot()
    def _request_test(self) -> None:
        model = self.model.currentText().strip()
        if not self._key_present or not model or not self.acknowledgement.isChecked():
            return
        self.test_requested.emit(model, self.max_output_tokens.value())

    @QtCore.pyqtSlot()
    def _update_test_button(self) -> None:
        self.test_button.setEnabled(
            self._key_present
            and bool(self.model.currentText().strip())
            and self.acknowledgement.isChecked()
            and not self._busy
        )


class OpenAIProbeWorker(QtCore.QObject):
    """Execute the explicit network probe outside the Qt GUI thread."""

    completed = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)

    def __init__(
        self,
        *,
        runner: OpenAIProbeRunner,
        model: str,
        api_key: SecretValue,
        max_output_tokens: int,
    ) -> None:
        super().__init__()
        self._runner = runner
        self._model = model
        self._api_key = api_key
        self._max_output_tokens = max_output_tokens

    @QtCore.pyqtSlot()
    def run(self) -> None:
        try:
            snapshot = self._runner(
                model=self._model,
                api_key=self._api_key,
                max_output_tokens=self._max_output_tokens,
            )
        except Exception:
            self.failed.emit(
                "Le test OpenAI a échoué avant validation. Aucun détail sensible n'est affiché."
            )
            return
        self.completed.emit(snapshot)


class TradingEconomicsSettingsWidget(QtWidgets.QWidget):
    """Explicit session-only Trading Economics validation panel."""

    test_requested = QtCore.pyqtSignal(object)

    def __init__(
        self,
        *,
        api_key_present: bool,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._key_present = api_key_present
        self._busy = False
        layout = QtWidgets.QVBoxLayout(self)

        title = QtWidgets.QLabel("Validation du calendrier Trading Economics")
        title.setStyleSheet("QLabel { font-weight: 600; }")
        layout.addWidget(title)
        explanation = QtWidgets.QLabel(
            "Le test lit une fenêtre calendrier bornée. Après succès, le rafraîchissement "
            "périodique est actif pour cette session uniquement. Aucun ordre IG n'est créé."
        )
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        self.key_status = QtWidgets.QLabel()
        self.key_status.setWordWrap(True)
        layout.addWidget(self.key_status)

        form = QtWidgets.QFormLayout()
        self.countries = QtWidgets.QLineEdit("united states,euro area")
        self.countries.setPlaceholderText("pays séparés par des virgules")
        self.lookahead_hours = QtWidgets.QSpinBox()
        self.lookahead_hours.setRange(1, 24 * 30)
        self.lookahead_hours.setValue(48)
        self.lookahead_hours.setSuffix(" h")
        self.pre_event_minutes = QtWidgets.QSpinBox()
        self.pre_event_minutes.setRange(1, 24 * 60)
        self.pre_event_minutes.setValue(60)
        self.pre_event_minutes.setSuffix(" min")
        self.post_event_minutes = QtWidgets.QSpinBox()
        self.post_event_minutes.setRange(1, 24 * 60)
        self.post_event_minutes.setValue(15)
        self.post_event_minutes.setSuffix(" min")
        form.addRow("Pays", self.countries)
        form.addRow("Horizon futur", self.lookahead_hours)
        form.addRow("Alerte avant événement", self.pre_event_minutes)
        form.addRow("Risque après événement", self.post_event_minutes)
        layout.addLayout(form)

        self.acknowledgement = QtWidgets.QCheckBox(
            "J'autorise un appel Trading Economics potentiellement facturé et son "
            "rafraîchissement toutes les 15 minutes pendant cette session."
        )
        layout.addWidget(self.acknowledgement)
        self.test_button = QtWidgets.QPushButton("Tester et activer le calendrier")
        self.test_button.clicked.connect(self._request_test)
        layout.addWidget(self.test_button)
        self.result = QtWidgets.QLabel("Aucun test lancé.")
        self.result.setWordWrap(True)
        self.result.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        layout.addWidget(self.result)
        layout.addStretch(1)

        self.countries.textChanged.connect(self._update_test_button)
        self.acknowledgement.toggled.connect(self._update_test_button)
        self.set_key_present(api_key_present)

    def set_key_present(self, present: bool) -> None:
        self._key_present = present
        if present:
            self.key_status.setText(
                "TRADING_ECONOMICS_API_KEY : DÉTECTÉE dans le processus (valeur masquée)."
            )
            self.key_status.setStyleSheet("QLabel { color: #176b2c; }")
        else:
            self.key_status.setText(
                "TRADING_ECONOMICS_API_KEY : ABSENTE du processus. La clé n'est ni saisie ni "
                "stockée ici."
            )
            self.key_status.setStyleSheet("QLabel { color: #9b1c1c; }")
        self._update_test_button()

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        for control in (
            self.countries,
            self.lookahead_hours,
            self.pre_event_minutes,
            self.post_event_minutes,
            self.acknowledgement,
        ):
            control.setEnabled(not busy)
        if busy:
            self.result.setText("Test Trading Economics en cours…")
            self.result.setStyleSheet("")
        self._update_test_button()

    @QtCore.pyqtSlot(str)
    def show_success(self, message: str) -> None:
        self.result.setText(message)
        self.result.setStyleSheet("QLabel { color: #176b2c; font-weight: 600; }")

    @QtCore.pyqtSlot(str)
    def show_failure(self, message: str) -> None:
        self.result.setText(message)
        self.result.setStyleSheet("QLabel { color: #9b1c1c; font-weight: 600; }")

    @QtCore.pyqtSlot()
    def _request_test(self) -> None:
        if not self.test_button.isEnabled():
            return
        countries = tuple(item.strip() for item in self.countries.text().split(","))
        try:
            config = TradingEconomicsRuntimeConfig(
                countries=countries,
                lookahead=timedelta(hours=self.lookahead_hours.value()),
                pre_event_window=timedelta(minutes=self.pre_event_minutes.value()),
                post_event_window=timedelta(minutes=self.post_event_minutes.value()),
            )
        except ValueError as exc:
            self.show_failure(str(exc))
            return
        self.test_requested.emit(config)

    @QtCore.pyqtSlot()
    def _update_test_button(self) -> None:
        self.test_button.setEnabled(
            self._key_present
            and bool(self.countries.text().strip())
            and self.acknowledgement.isChecked()
            and not self._busy
        )


def _optional_decimal_field(value: Decimal | None) -> QtWidgets.QLineEdit:
    field = QtWidgets.QLineEdit("" if value is None else format(value, "f"))
    field.setPlaceholderText("Vide = inconnu")
    field.setClearButtonEnabled(True)
    return field


def _required_decimal_field(value: Decimal) -> QtWidgets.QLineEdit:
    field = QtWidgets.QLineEdit(format(value, "f"))
    field.setClearButtonEnabled(True)
    return field


def _parse_optional_decimal(text: str, label: str) -> Decimal | None:
    normalized = text.strip().replace(",", ".")
    if not normalized:
        return None
    try:
        value = Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError(f"{label} doit être un nombre décimal ou rester vide") from exc
    if not value.is_finite() or value < 0:
        raise ValueError(f"{label} doit être un nombre fini positif ou nul")
    return value


def _parse_required_decimal(text: str, label: str) -> Decimal:
    value = _parse_optional_decimal(text, label)
    if value is None:
        raise ValueError(f"{label} est obligatoire")
    return value
