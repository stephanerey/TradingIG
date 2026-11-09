"""Paper-only ticket proposal widget with deterministic risk evaluation."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from PyQt5 import QtCore, QtWidgets

from trading_ig_assistant.domain.adapter_contracts import ExecutionStatus, OrderDirection
from trading_ig_assistant.domain.market_data import QUOTE_FRESHNESS_SECONDS, Quote
from trading_ig_assistant.domain.positions import PaperFillAssumptions, PaperQuote
from trading_ig_assistant.domain.products import ProductType, TradableProduct
from trading_ig_assistant.domain.risk import (
    AccountRiskState,
    ExposureState,
    PortfolioRiskSnapshot,
    RiskDecision,
    RiskSettingsLayer,
)
from trading_ig_assistant.domain.tickets import TicketDraft
from trading_ig_assistant.services.paper_session import (
    LOCAL_PAPER_ACCOUNT,
    PaperOrderRecord,
    PaperTicketSubmission,
)
from trading_ig_assistant.services.risk_engine import RiskEngine, resolve_risk_settings
from trading_ig_assistant.services.ticket_builder import TicketBuilder, TicketValidationError

DEFAULT_STOP_DISTANCE = 4.0
DEFAULT_TARGET_DISTANCE = 12.0
DEFAULT_MAXIMUM_KO_LOSS = 9.0


class PaperTicketWidget(QtWidgets.QScrollArea):
    """Build, evaluate and explicitly request a local Paper-only submission."""

    paper_execution_requested = QtCore.pyqtSignal(object)

    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
        *,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        super().__init__(parent)
        self._now_provider = now_provider or (lambda: datetime.now(UTC))
        self._product: TradableProduct | None = None
        self._chart_source: TradableProduct | None = None
        self._quote: Quote | None = None
        self._quote_received_at_utc: datetime | None = None
        self._open_exposures: tuple[ExposureState, ...] = ()
        self.last_ticket: TicketDraft | None = None
        self.last_submission: PaperTicketSubmission | None = None
        self.last_decision: RiskDecision | None = None
        self.last_outcome_approved = False

        self.setWidgetResizable(True)
        self.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.setMinimumSize(0, 0)
        self.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)

        content = QtWidgets.QWidget()
        content.setMinimumSize(0, 0)
        content.setSizePolicy(
            QtWidgets.QSizePolicy.Ignored,
            QtWidgets.QSizePolicy.Preferred,
        )
        layout = QtWidgets.QVBoxLayout(content)
        layout.setSizeConstraint(QtWidgets.QLayout.SetNoConstraint)

        self.mode_banner = QtWidgets.QLabel(
            "MODE PAPER — proposition locale, aucune transmission à IG"
        )
        self.mode_banner.setWordWrap(True)
        self.mode_banner.setAlignment(QtCore.Qt.AlignCenter)
        self.mode_banner.setStyleSheet(
            "QLabel { background: #e9f3ff; color: #153a5b; padding: 6px; font-weight: 700; }"
        )
        layout.addWidget(self.mode_banner)

        self.product_status = QtWidgets.QLabel("Sélectionnez un produit.")
        self.product_status.setWordWrap(True)
        layout.addWidget(self.product_status)

        form = QtWidgets.QFormLayout()
        form.setRowWrapPolicy(QtWidgets.QFormLayout.WrapLongRows)
        form.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        layout.addLayout(form)

        self.product_currency = QtWidgets.QLineEdit()
        self.product_currency.setMaxLength(3)
        self.product_currency.setPlaceholderText("Code 3 lettres, ex. EUR")

        self.direction = QtWidgets.QComboBox()
        self.direction.addItem("Achat", OrderDirection.BUY)
        self.direction.addItem("Vente", OrderDirection.SELL)
        self.direction.setToolTip(
            "Sens de l'opération Paper, indépendant de l'exposition du produit. "
            "Achat est proposé par défaut lors du changement de produit."
        )

        self._levels_are_relative = True
        level_mode = QtWidgets.QWidget()
        level_mode_layout = QtWidgets.QHBoxLayout(level_mode)
        level_mode_layout.setContentsMargins(0, 0, 0, 0)
        self.relative_levels = QtWidgets.QRadioButton("Relatif (distances)")
        self.absolute_levels = QtWidgets.QRadioButton("Absolu (prix)")
        self.relative_levels.setChecked(True)
        level_mode_layout.addWidget(self.relative_levels)
        level_mode_layout.addWidget(self.absolute_levels)
        level_mode_layout.addStretch(1)

        self.quantity = _money_spin(decimals=4, maximum=1_000_000, minimum=0.0001)
        self.quantity.setValue(1.0)
        self.stop = _money_spin(decimals=6, maximum=1_000_000_000)
        self.target = _money_spin(decimals=6, maximum=1_000_000_000)
        self.stop.setValue(DEFAULT_STOP_DISTANCE)
        self.target.setValue(DEFAULT_TARGET_DISTANCE)
        self.knockout = _money_spin(decimals=6, maximum=1_000_000_000)
        self.maximum_ko_loss = _money_spin(decimals=2, maximum=1_000_000_000)
        self.maximum_ko_loss.setValue(DEFAULT_MAXIMUM_KO_LOSS)
        self.maximum_ko_loss.setToolTip(
            "Hypothèse initiale Paper à confirmer; ce n'est pas une perte certifiée par IG."
        )
        self.fee_per_unit = _money_spin(decimals=4, maximum=1_000_000)
        self.slippage_points = _money_spin(decimals=6, maximum=1_000_000)

        self.equity_reference = _money_spin(decimals=2, maximum=1_000_000_000)
        self.equity_reference.setValue(1_000.0)
        self.equity_current = _money_spin(decimals=2, maximum=1_000_000_000)
        self.equity_current.setValue(1_000.0)
        self.daily_net_pnl = _money_spin(
            decimals=2,
            maximum=1_000_000_000,
            minimum=-1_000_000_000,
        )
        self.risk_percent = _money_spin(decimals=2, maximum=100, minimum=0.01)
        self.risk_percent.setValue(1.0)
        self.minimum_rr = _money_spin(decimals=2, maximum=100, minimum=0.01)
        self.minimum_rr.setValue(2.0)
        self.fx_rate_to_eur = _money_spin(decimals=6, maximum=1_000_000)

        form.addRow("Devise produit", self.product_currency)
        form.addRow("Sens", self.direction)
        form.addRow("Taille", self.quantity)
        form.addRow("Mode stop / objectif", level_mode)
        self.stop_label = QtWidgets.QLabel()
        self.target_label = QtWidgets.QLabel()
        form.addRow(self.stop_label, self.stop)
        form.addRow(self.target_label, self.target)
        form.addRow("KO absolu (0 = aucun)", self.knockout)
        form.addRow("Perte max KO (hypothèse)", self.maximum_ko_loss)
        form.addRow("Frais/unité/côté", self.fee_per_unit)
        form.addRow("Slippage points/côté", self.slippage_points)
        form.addRow("Equity référence", self.equity_reference)
        form.addRow("Equity actuelle", self.equity_current)
        form.addRow("P&L net journalier", self.daily_net_pnl)
        form.addRow("Risque par trade (%)", self.risk_percent)
        form.addRow("R/R minimal", self.minimum_rr)
        form.addRow("FX devise → EUR (0 si EUR)", self.fx_rate_to_eur)

        self.level_help = QtWidgets.QLabel()
        self.level_help.setWordWrap(True)
        self.level_help.setMinimumWidth(0)
        self.level_help.setSizePolicy(
            QtWidgets.QSizePolicy.Ignored,
            QtWidgets.QSizePolicy.Preferred,
        )
        self.level_help.setStyleSheet("QLabel { color: #4b5563; font-style: italic; }")
        form.addRow(self.level_help)
        self._update_level_mode_ui()

        self.evaluate_button = QtWidgets.QPushButton("Évaluer la proposition Paper")
        self.evaluate_button.setEnabled(False)
        self.evaluate_button.clicked.connect(self.evaluate_proposal)
        layout.addWidget(self.evaluate_button)

        self.execute_button = QtWidgets.QPushButton("Ouvrir la position Paper locale")
        self.execute_button.setEnabled(False)
        self.execute_button.setToolTip("Simulation locale uniquement : aucune transmission à IG.")
        self.execute_button.clicked.connect(self.request_paper_execution)
        layout.addWidget(self.execute_button)

        self.summary = QtWidgets.QTextEdit()
        self.summary.setObjectName("paperTicketSummary")
        self.summary.setReadOnly(True)
        self.summary.setMinimumHeight(150)
        self.summary.setPlainText(
            "Aucune proposition. Un prix reçu récemment et des niveaux explicites sont requis."
        )
        layout.addWidget(self.summary)
        layout.addStretch(1)
        self.setWidget(content)

        for field in (
            self.quantity,
            self.stop,
            self.target,
            self.knockout,
            self.maximum_ko_loss,
            self.fee_per_unit,
            self.slippage_points,
            self.equity_reference,
            self.equity_current,
            self.daily_net_pnl,
            self.risk_percent,
            self.minimum_rr,
            self.fx_rate_to_eur,
        ):
            field.valueChanged.connect(self._invalidate_evaluation)
        self.direction.currentIndexChanged.connect(self._invalidate_evaluation)
        self.product_currency.textChanged.connect(self._invalidate_evaluation)
        self.relative_levels.toggled.connect(self._on_relative_mode_toggled)

    def set_product(self, product: TradableProduct | None) -> None:
        if product is None:
            self._product = None
            self._quote = None
            self._quote_received_at_utc = None
            self.product_status.setText("Sélectionnez un produit.")
            self.product_currency.clear()
            self.product_currency.setReadOnly(False)
            self.evaluate_button.setEnabled(False)
            self._invalidate_evaluation()
            return
        product_changed = self._product is None or self._product.epic != product.epic
        if product_changed:
            self._quote = None
            self._quote_received_at_utc = None
        self._product = product
        metadata_currency = (product.currency or "").strip().upper()
        self.product_currency.blockSignals(True)
        if metadata_currency:
            self.product_currency.setText(metadata_currency)
            self.product_currency.setReadOnly(True)
            self.product_currency.setToolTip("Devise fournie par la métadonnée produit IG.")
        else:
            if product_changed:
                self.product_currency.clear()
            self.product_currency.setReadOnly(False)
            self.product_currency.setToolTip(
                "Métadonnée IG absente : confirmer explicitement le code devise du produit."
            )
        self.product_currency.blockSignals(False)
        self._invalidate_evaluation()
        if product_changed:
            self.direction.setCurrentIndex(self.direction.findData(OrderDirection.BUY))
        if product.min_size is not None and product.min_size > 0:
            self.quantity.setValue(product.min_size)
        if product.ko_level is not None and product.ko_level > 0:
            self.knockout.setValue(product.ko_level)
        self._refresh_product_status()

    def set_open_exposures(self, exposures: tuple[ExposureState, ...]) -> None:
        if exposures == self._open_exposures:
            return
        self._open_exposures = exposures
        self._invalidate_evaluation()

    def set_chart_source(self, product: TradableProduct | None) -> None:
        self._chart_source = product
        self._refresh_product_status()

    def set_quote(
        self,
        quote: Quote | None,
        *,
        received_at_utc: datetime | None = None,
    ) -> None:
        if quote is None:
            had_quote_or_evaluation = self._quote is not None or self.last_submission is not None
            self._quote = None
            self._quote_received_at_utc = None
            self._invalidate_evaluation()
            if had_quote_or_evaluation:
                self.summary.setPlainText(
                    "Cotation précédente invalidée. Attendez une nouvelle cotation "
                    "et réévaluez la proposition Paper."
                )
            self._refresh_product_status()
            return
        if self._product is None or quote.epic != self._product.epic:
            return
        self._quote = quote
        self._quote_received_at_utc = received_at_utc or self._now_provider()
        if quote.delayed is True:
            self._invalidate_evaluation()
            self.summary.setPlainText(
                "Cotation différée : proposition Paper indisponible jusqu'à réception "
                "d'un prix utilisable."
            )
        self._refresh_product_status()

    @QtCore.pyqtSlot()
    def evaluate_proposal(self) -> None:
        self.last_ticket = None
        self.last_submission = None
        self.last_decision = None
        self.last_outcome_approved = False
        self.execute_button.setEnabled(False)
        try:
            submission, decision, extra_rejections, ui_warnings = self._build_and_evaluate()
        except (TicketValidationError, ValueError) as exc:
            self.summary.setPlainText(f"REFUSÉ — {exc}\n\nAucune exécution n'a été tentée.")
            return

        ticket = submission.ticket
        self.last_ticket = ticket
        self.last_submission = submission
        self.last_decision = decision
        rejection_codes = [reason.value for reason in decision.reasons]
        rejection_codes.extend(extra_rejections)
        self.last_outcome_approved = decision.approved and not extra_rejections
        self.execute_button.setEnabled(self.last_outcome_approved)
        status = "APPROUVÉ POUR PAPER UNIQUEMENT" if self.last_outcome_approved else "REFUSÉ"
        estimated_gain = (
            _format_decimal(ticket.estimated_gain)
            if ticket.estimated_gain is not None
            else "inconnu"
        )
        ratio = (
            _format_decimal(ticket.reward_risk_ratio)
            if ticket.reward_risk_ratio is not None
            else "inconnu"
        )
        budget = (
            _format_decimal(decision.budget_reference)
            if decision.budget_reference is not None
            else "inconnu"
        )
        loss_reference = (
            _format_decimal(decision.estimated_loss_reference)
            if decision.estimated_loss_reference is not None
            else "inconnu"
        )
        warnings = [*ticket.warnings, *ui_warnings]
        lines = [
            status,
            "Nature: PAPER_SIMULATION_ONLY",
            f"Produit: {ticket.intent.product_id}",
            f"Sens: {ticket.intent.direction.value}",
            (
                "Mode niveaux: RELATIF — distances converties localement"
                if self._levels_are_relative
                else "Mode niveaux: ABSOLU — niveaux de prix saisis"
            ),
            f"Entrée simulée: {_format_decimal(ticket.entry_price)}",
            f"Stop résolu: {_format_optional_decimal(ticket.intent.requested_stop)}",
            f"Objectif résolu: {_format_optional_decimal(ticket.intent.requested_target)}",
            f"KO absolu: {_format_optional_decimal(ticket.intent.requested_ko)}",
            f"Perte ticket estimée: {_format_decimal(ticket.estimated_loss)}",
            f"Perte risque en EUR: {loss_reference}",
            f"Budget risque en EUR: {budget}",
            f"Gain net potentiel estimé: {estimated_gain}",
            f"R/R estimé: {ratio}",
            f"Frais estimés: {_format_decimal(ticket.fee_estimate)}",
            f"Spread estimé: {_format_decimal(ticket.spread_cost)}",
            f"Slippage estimé: {_format_decimal(ticket.slippage_estimate)}",
            f"Rejets: {', '.join(rejection_codes) if rejection_codes else 'aucun'}",
            f"Avertissements: {', '.join(warnings)}",
            "",
            "Aucune exécution n'a été tentée. Cette proposition ne prouve aucune capacité IG.",
        ]
        self.summary.setPlainText("\n".join(lines))

    @QtCore.pyqtSlot()
    def request_paper_execution(self) -> None:
        """Re-evaluate current inputs, then emit one immutable Paper-only request."""

        self.evaluate_proposal()
        if not self.last_outcome_approved or self.last_submission is None:
            return
        self.execute_button.setEnabled(False)
        self.summary.append("\nSoumission à la session Paper locale…")
        self.paper_execution_requested.emit(self.last_submission)

    def show_execution_result(self, record: PaperOrderRecord) -> None:
        result = record.outcome.execution_result
        if result.status is ExecutionStatus.CONFIRMED:
            detail = result.broker_reference or record.submission.ticket.intent.intent_id
            self.summary.append(
                "\nPOSITION PAPER OUVERTE — "
                f"{detail}\nSimulation locale uniquement; aucune transmission à IG."
            )
            return
        self.summary.append(
            "\nOUVERTURE PAPER REFUSÉE — "
            f"{result.message or result.status.value}\nAucune transmission à IG."
        )

    def _build_and_evaluate(
        self,
    ) -> tuple[PaperTicketSubmission, RiskDecision, list[str], list[str]]:
        product = self._product
        quote = self._quote
        if product is None:
            raise ValueError("aucun produit sélectionné")
        if product.product_type is ProductType.UNKNOWN:
            raise ValueError("type de produit non supporté ou inconnu")
        if quote is None or quote.bid is None or quote.offer is None:
            raise ValueError("aucun bid/ask récent reçu")
        if quote.delayed is True:
            raise ValueError("cotation IG différée; attendre un prix utilisable")
        if not self._quote_is_fresh():
            raise ValueError("prix périmé; attendre une nouvelle cotation")
        market_status = (quote.market_state or product.status or "").upper()
        if market_status != "TRADEABLE":
            raise ValueError("marché non confirmé TRADEABLE")

        knockout = _optional_decimal(self.knockout.value())
        maximum_ko_loss = _optional_decimal(self.maximum_ko_loss.value())
        if product.product_type is ProductType.BARRIER and (
            knockout is None or maximum_ko_loss is None
        ):
            raise ValueError(
                "une Barrière exige le niveau KO et une estimation explicite de perte max KO"
            )

        now = self._now_provider()
        direction = self.direction.currentData()
        if not isinstance(direction, OrderDirection):
            direction = OrderDirection(str(direction))
        currency = self.product_currency.text().strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            raise ValueError("confirmer la devise produit avec un code de trois lettres")
        metadata_currency = (product.currency or "").strip().upper()
        if metadata_currency and currency != metadata_currency:
            raise ValueError("la devise confirmée ne correspond pas à la métadonnée produit")
        paper_quote = PaperQuote(
            product_id=product.epic,
            observed_at_utc=now,
            bid=Decimal(str(quote.bid)),
            ask=Decimal(str(quote.offer)),
            currency=currency,
            fresh=True,
            market_open=True,
            product_supported=True,
            provenance="gui-received-quote",
        )
        assumptions = PaperFillAssumptions(
            fee_per_unit_per_side=_decimal(self.fee_per_unit.value()),
            slippage_points_per_side=_decimal(self.slippage_points.value()),
            model_version="paper-gui-preview-v1",
        )
        entry_price = self._preview_entry_price(direction, assumptions)
        if entry_price is None:
            raise ValueError("aucun prix d'entrée simulé disponible")
        stop, target = self._resolved_stop_target(direction, entry_price)
        ticket = TicketBuilder().build(
            intent_id=f"paper-ui-{uuid4().hex}",
            account=LOCAL_PAPER_ACCOUNT,
            quote=paper_quote,
            underlying_id=product.epic,
            direction=direction,
            quantity=_decimal(self.quantity.value()),
            stop=stop,
            target=target,
            knockout=knockout,
            expires_at_utc=now + timedelta(minutes=15),
            assumptions=assumptions,
        )
        risk_request = TicketBuilder.risk_request(
            ticket,
            maximum_ko_loss=maximum_ko_loss,
        )
        fx_rate = _optional_decimal(self.fx_rate_to_eur.value())
        account_state = AccountRiskState(
            account=LOCAL_PAPER_ACCOUNT,
            currency=currency,
            equity_reference_day=_decimal(self.equity_reference.value()),
            equity_current=_decimal(self.equity_current.value()),
            daily_net_pnl=_decimal(self.daily_net_pnl.value()),
            confirmed=True,
            active_for_opening=True,
            fx_rate_to_reference=fx_rate,
        )
        execution_snapshot = PortfolioRiskSnapshot(
            reference_currency="EUR",
            accounts=(account_state,),
            exposure_complete=True,
        )
        preview_snapshot = PortfolioRiskSnapshot(
            reference_currency=execution_snapshot.reference_currency,
            accounts=execution_snapshot.accounts,
            open_exposures=self._open_exposures,
            exposure_complete=execution_snapshot.exposure_complete,
        )
        settings = resolve_risk_settings(
            global_settings=RiskSettingsLayer(
                per_trade_fraction=_decimal(self.risk_percent.value()) / Decimal("100")
            )
        )
        decision = RiskEngine().evaluate(risk_request, preview_snapshot, settings)
        extra_rejections: list[str] = []
        if ticket.reward_risk_ratio is None or ticket.reward_risk_ratio < _decimal(
            self.minimum_rr.value()
        ):
            extra_rejections.append("reward_risk_below_minimum")
        ui_warnings = [
            (
                "LOCAL_PAPER_EXPOSURE_INCLUDED"
                if self._open_exposures
                else "LOCAL_VOLATILE_PAPER_PORTFOLIO"
            ),
            "UNDERLYING_MAPPING_UNVERIFIED_PRODUCT_EPIC_USED",
        ]
        if not metadata_currency:
            ui_warnings.append(f"PRODUCT_CURRENCY_USER_CONFIRMED:{currency}")
        if product.product_type is ProductType.BARRIER:
            ui_warnings.append("KO_MAX_LOSS_ASSUMPTION_REQUIRES_REVIEW")
        if self._levels_are_relative:
            ui_warnings.append("RELATIVE_LEVELS_RESOLVED_LOCALLY")
        if currency != "EUR":
            ui_warnings.append("MANUAL_FX_RATE")
        submission = PaperTicketSubmission(
            ticket=ticket,
            risk_request=risk_request,
            risk_snapshot=execution_snapshot,
            risk_settings=settings,
            quote=paper_quote,
            assumptions=assumptions,
        )
        return submission, decision, extra_rejections, ui_warnings

    @QtCore.pyqtSlot(bool)
    def _on_relative_mode_toggled(self, relative: bool) -> None:
        if relative == self._levels_are_relative:
            return
        direction = self._selected_direction()
        assumptions = PaperFillAssumptions(
            fee_per_unit_per_side=_decimal(self.fee_per_unit.value()),
            slippage_points_per_side=_decimal(self.slippage_points.value()),
            model_version="paper-gui-preview-v1",
        )
        entry_price = self._preview_entry_price(direction, assumptions)
        if entry_price is not None:
            stop_value = _decimal(self.stop.value())
            target_value = _decimal(self.target.value())
            if relative:
                if direction is OrderDirection.BUY:
                    stop_value = entry_price - stop_value
                    target_value = target_value - entry_price
                else:
                    stop_value = stop_value - entry_price
                    target_value = entry_price - target_value
            elif direction is OrderDirection.BUY:
                stop_value = entry_price - stop_value
                target_value = entry_price + target_value
            else:
                stop_value = entry_price + stop_value
                target_value = entry_price - target_value
            self.stop.blockSignals(True)
            self.target.blockSignals(True)
            self.stop.setValue(float(max(stop_value, Decimal("0"))))
            self.target.setValue(float(max(target_value, Decimal("0"))))
            self.stop.blockSignals(False)
            self.target.blockSignals(False)
        self._levels_are_relative = relative
        self._update_level_mode_ui()
        self._invalidate_evaluation()

    def _update_level_mode_ui(self) -> None:
        if self._levels_are_relative:
            self.stop_label.setText("Distance stop")
            self.target_label.setText("Distance objectif")
            self.stop.setSuffix(" points")
            self.target.setSuffix(" points")
            self.level_help.setText(
                "Distances relatives positives, comme dans le ticket IG : achat = stop sous "
                "l'entrée et objectif au-dessus; vente = règle inverse. Le KO reste absolu."
            )
            return
        self.stop_label.setText("Stop absolu")
        self.target_label.setText("Objectif absolu")
        self.stop.setSuffix("")
        self.target.setSuffix("")
        self.level_help.setText(
            "Niveaux absolus — Achat : stop/KO < entrée et objectif > entrée; "
            "Vente : règle inverse."
        )

    def _selected_direction(self) -> OrderDirection:
        direction = self.direction.currentData()
        if isinstance(direction, OrderDirection):
            return direction
        return OrderDirection(str(direction))

    def _preview_entry_price(
        self,
        direction: OrderDirection,
        assumptions: PaperFillAssumptions,
    ) -> Decimal | None:
        quote = self._quote
        if quote is None or quote.bid is None or quote.offer is None:
            return None
        if direction is OrderDirection.BUY:
            return Decimal(str(quote.offer)) + assumptions.slippage_points_per_side
        return Decimal(str(quote.bid)) - assumptions.slippage_points_per_side

    def _resolved_stop_target(
        self,
        direction: OrderDirection,
        entry_price: Decimal,
    ) -> tuple[Decimal, Decimal]:
        stop_input = _optional_decimal(self.stop.value())
        target_input = _optional_decimal(self.target.value())
        input_kind = "distance" if self._levels_are_relative else "niveau"
        if stop_input is None:
            raise ValueError(f"{input_kind} stop requis")
        if target_input is None:
            raise ValueError(f"{input_kind} objectif requis pour évaluer le R/R")
        if not self._levels_are_relative:
            return stop_input, target_input
        if direction is OrderDirection.BUY:
            stop = entry_price - stop_input
            target = entry_price + target_input
        else:
            stop = entry_price + stop_input
            target = entry_price - target_input
        if stop <= 0 or target <= 0:
            raise ValueError("les distances relatives produisent un niveau de prix invalide")
        return stop, target

    @QtCore.pyqtSlot()
    def _invalidate_evaluation(self) -> None:
        self.last_ticket = None
        self.last_submission = None
        self.last_decision = None
        self.last_outcome_approved = False
        if hasattr(self, "execute_button"):
            self.execute_button.setEnabled(False)

    def _quote_is_fresh(self) -> bool:
        if self._quote_received_at_utc is None:
            return False
        if self._quote is not None and self._quote.delayed is True:
            return False
        age = (self._now_provider() - self._quote_received_at_utc).total_seconds()
        return 0 <= age <= QUOTE_FRESHNESS_SECONDS

    def _refresh_product_status(self) -> None:
        product = self._product
        if product is None:
            return
        quote_text = "cotation directe récente en attente"
        if (
            self._quote is not None
            and self._quote.bid is not None
            and self._quote.offer is not None
        ):
            freshness = (
                "différé"
                if self._quote.delayed is True
                else "récent"
                if self._quote_is_fresh()
                else "périmé"
            )
            quote_text = f"bid {self._quote.bid:g} / ask {self._quote.offer:g} ({freshness})"
        elif self._chart_source is not None and self._chart_source.epic != product.epic:
            source_name = self._chart_source.name or self._chart_source.epic
            quote_text = (
                "cotation directe du produit sélectionné en attente; "
                f"le graphique utilise {source_name} comme sous-jacent, "
                "sans réutiliser son prix pour le ticket"
            )
        self.product_status.setText(
            f"{product.name or product.epic} — {product.product_type.value} — {quote_text}"
        )
        quote_ready = (
            self._quote is not None
            and self._quote.bid is not None
            and self._quote.offer is not None
            and self._quote_is_fresh()
        )
        self.evaluate_button.setEnabled(quote_ready)


def _money_spin(
    *,
    decimals: int,
    maximum: float,
    minimum: float = 0.0,
) -> QtWidgets.QDoubleSpinBox:
    field = QtWidgets.QDoubleSpinBox()
    field.setDecimals(decimals)
    field.setRange(minimum, maximum)
    field.setSingleStep(0.1)
    field.setGroupSeparatorShown(True)
    return field


def _decimal(value: float) -> Decimal:
    return Decimal(str(value))


def _optional_decimal(value: float) -> Decimal | None:
    decimal_value = _decimal(value)
    return decimal_value if decimal_value > 0 else None


def _format_decimal(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.0001")), "f").rstrip("0").rstrip(".")


def _format_optional_decimal(value: Decimal | None) -> str:
    return _format_decimal(value) if value is not None else "aucun"
