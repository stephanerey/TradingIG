from datetime import UTC, datetime, timedelta


def _cash_product():
    from trading_ig_assistant.domain.products import ProductType, TradableProduct

    return TradableProduct(
        epic="PAPER.EUR.ONE",
        name="Paper EUR Market",
        product_type=ProductType.CASH_OR_DFB,
        currency="EUR",
        status="TRADEABLE",
        min_size=1.0,
    )


def _fresh_quote():
    from trading_ig_assistant.domain.market_data import Quote

    return Quote(
        epic="PAPER.EUR.ONE",
        bid=100.0,
        offer=101.0,
        market_state="TRADEABLE",
    )


def _configured_widget(now):
    from trading_ig_assistant.ui.ticket_view import PaperTicketWidget

    widget = PaperTicketWidget(now_provider=lambda: now)
    widget.set_product(_cash_product())
    widget.set_quote(_fresh_quote(), received_at_utc=now)
    widget.absolute_levels.setChecked(True)
    widget.quantity.setValue(1.0)
    widget.stop.setValue(99.0)
    widget.target.setValue(108.0)
    return widget


def test_product_exposure_does_not_derive_paper_order_direction() -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.domain.adapter_contracts import OrderDirection
    from trading_ig_assistant.domain.products import ProductDirection, ProductType, TradableProduct
    from trading_ig_assistant.ui.ticket_view import PaperTicketWidget

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    widget = PaperTicketWidget()
    put = TradableProduct(
        epic="OPTION.PUT",
        name="Put",
        product_type=ProductType.OPTION,
        direction=ProductDirection.PUT,
    )
    bearish_barrier = TradableProduct(
        epic="BARRIER.SHORT",
        name="Barrière Vente",
        product_type=ProductType.BARRIER,
        direction=ProductDirection.SELL,
    )
    widget.set_product(put)
    assert widget.direction.currentData() is OrderDirection.BUY
    widget.direction.setCurrentIndex(widget.direction.findData(OrderDirection.SELL))
    widget.set_product(put)
    assert widget.direction.currentData() is OrderDirection.SELL
    widget.set_product(bearish_barrier)
    assert widget.direction.currentData() is OrderDirection.BUY
    widget.direction.setCurrentIndex(widget.direction.findData(OrderDirection.SELL))
    assert widget.direction.currentData() is OrderDirection.SELL
    assert app is not None


def test_relative_levels_are_prefilled_and_resolved_for_buy_and_sell() -> None:
    from decimal import Decimal

    from PyQt5 import QtWidgets

    from trading_ig_assistant.domain.adapter_contracts import OrderDirection
    from trading_ig_assistant.ui.ticket_view import PaperTicketWidget

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    now = datetime(2026, 10, 23, 10, 0, tzinfo=UTC)
    widget = PaperTicketWidget(now_provider=lambda: now)
    widget.set_product(_cash_product())
    widget.set_quote(_fresh_quote(), received_at_utc=now)
    widget.equity_reference.setValue(10_000.0)
    widget.equity_current.setValue(10_000.0)

    assert widget.relative_levels.isChecked()
    assert widget.stop.value() == 4.0
    assert widget.target.value() == 12.0
    assert widget.maximum_ko_loss.value() == 9.0

    widget.evaluate_proposal()

    assert widget.last_ticket is not None
    assert widget.last_ticket.intent.requested_stop == Decimal("97.0")
    assert widget.last_ticket.intent.requested_target == Decimal("113.0")
    assert "Mode niveaux: RELATIF" in widget.summary.toPlainText()
    assert "RELATIVE_LEVELS_RESOLVED_LOCALLY" in widget.summary.toPlainText()

    widget.direction.setCurrentIndex(widget.direction.findData(OrderDirection.SELL))
    widget.evaluate_proposal()

    assert widget.last_ticket is not None
    assert widget.last_ticket.intent.requested_stop == Decimal("104.0")
    assert widget.last_ticket.intent.requested_target == Decimal("88.0")


def test_switching_level_mode_preserves_the_resolved_buy_levels() -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.ui.ticket_view import PaperTicketWidget

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    now = datetime(2026, 10, 23, 10, 0, tzinfo=UTC)
    widget = PaperTicketWidget(now_provider=lambda: now)
    widget.set_product(_cash_product())
    widget.set_quote(_fresh_quote(), received_at_utc=now)

    widget.absolute_levels.setChecked(True)

    assert widget.stop.value() == 97.0
    assert widget.target.value() == 113.0
    assert "Niveaux absolus" in widget.level_help.text()

    widget.relative_levels.setChecked(True)

    assert widget.stop.value() == 4.0
    assert widget.target.value() == 12.0


def test_paper_ticket_widget_builds_approved_preview_without_execution() -> None:
    from PyQt5 import QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    now = datetime(2026, 10, 23, 10, 0, tzinfo=UTC)
    widget = _configured_widget(now)

    widget.evaluate_proposal()

    assert widget.last_outcome_approved is True
    assert widget.last_ticket is not None
    assert widget.last_ticket.intent.account.broker_id == "paper"
    assert widget.last_ticket.intent.account.environment == "paper"
    assert "APPROUVÉ POUR SIMULATION UNIQUEMENT" in widget.summary.toPlainText()
    assert "Aucune exécution n'a été tentée" in widget.summary.toPlainText()
    assert "Évaluer" in widget.evaluate_button.text()
    assert "Trade" not in widget.evaluate_button.text()
    assert widget.execute_button.isEnabled()
    assert "simulée locale" in widget.execute_button.text()


def test_paper_ticket_revalidates_before_emitting_local_execution() -> None:
    from PyQt5 import QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    now = datetime(2026, 10, 23, 10, 0, tzinfo=UTC)
    widget = _configured_widget(now)
    emitted = []
    widget.paper_execution_requested.connect(emitted.append)

    widget.evaluate_proposal()
    first_intent_id = widget.last_ticket.intent.intent_id
    widget.request_paper_execution()

    assert len(emitted) == 1
    assert emitted[0].ticket.intent.intent_id != first_intent_id
    assert widget.last_submission == emitted[0]
    assert not widget.execute_button.isEnabled()


def test_delayed_quote_invalidates_approved_paper_ticket() -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.domain.market_data import Quote

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    now = datetime(2026, 10, 23, 10, 0, tzinfo=UTC)
    widget = _configured_widget(now)
    widget.evaluate_proposal()
    assert widget.last_outcome_approved
    widget.set_quote(
        Quote(epic="PAPER.EUR.ONE", bid=100, offer=101, raw={"DELAY": "1"}),
        received_at_utc=now,
    )
    assert not widget.last_outcome_approved
    assert not widget.execute_button.isEnabled()
    assert not widget.evaluate_button.isEnabled()
    assert "différé" in widget.product_status.text()
    widget.evaluate_proposal()
    assert "différée" in widget.summary.toPlainText()
    widget.set_quote(
        Quote(epic="PAPER.EUR.ONE", bid=100, offer=101, raw={"DELAY": "0"}),
        received_at_utc=now,
    )
    assert widget.evaluate_button.isEnabled()
    widget.evaluate_proposal()
    assert widget.last_outcome_approved
    widget.close()


def test_ticket_input_change_invalidates_paper_execution_button() -> None:
    from PyQt5 import QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    now = datetime(2026, 10, 23, 10, 0, tzinfo=UTC)
    widget = _configured_widget(now)
    widget.evaluate_proposal()
    assert widget.execute_button.isEnabled()

    widget.quantity.setValue(2.0)

    assert not widget.execute_button.isEnabled()
    assert widget.last_submission is None


def test_missing_product_currency_requires_explicit_three_letter_confirmation() -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.domain.market_data import Quote
    from trading_ig_assistant.domain.products import ProductType, TradableProduct
    from trading_ig_assistant.ui.ticket_view import PaperTicketWidget

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    now = datetime(2026, 10, 23, 10, 0, tzinfo=UTC)
    widget = PaperTicketWidget(now_provider=lambda: now)
    widget.set_product(
        TradableProduct(
            epic="PAPER.UNKNOWN.CURRENCY",
            name="Paper product without currency metadata",
            product_type=ProductType.CASH_OR_DFB,
            status="TRADEABLE",
        )
    )
    widget.set_quote(
        Quote(
            epic="PAPER.UNKNOWN.CURRENCY",
            bid=100.0,
            offer=101.0,
            market_state="TRADEABLE",
        ),
        received_at_utc=now,
    )
    widget.absolute_levels.setChecked(True)
    widget.stop.setValue(99.0)
    widget.target.setValue(108.0)

    widget.evaluate_proposal()
    assert "confirmer la devise produit" in widget.summary.toPlainText()
    assert not widget.execute_button.isEnabled()

    widget.product_currency.setText("EUR")
    widget.evaluate_proposal()

    assert widget.last_outcome_approved is True
    assert widget.last_submission is not None
    assert widget.last_submission.quote.currency == "EUR"
    assert "PRODUCT_CURRENCY_USER_CONFIRMED:EUR" in widget.summary.toPlainText()


def test_invalid_or_unconverted_currency_keeps_financial_veto() -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.domain.market_data import Quote
    from trading_ig_assistant.domain.products import ProductType, TradableProduct
    from trading_ig_assistant.ui.ticket_view import PaperTicketWidget

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    now = datetime(2026, 10, 23, 10, 0, tzinfo=UTC)
    widget = PaperTicketWidget(now_provider=lambda: now)
    widget.set_product(
        TradableProduct(
            epic="PAPER.USD.ONE",
            name="Paper USD Market",
            product_type=ProductType.CASH_OR_DFB,
            status="TRADEABLE",
        )
    )
    widget.set_quote(
        Quote(
            epic="PAPER.USD.ONE",
            bid=100.0,
            offer=101.0,
            market_state="TRADEABLE",
        ),
        received_at_utc=now,
    )
    widget.absolute_levels.setChecked(True)
    widget.stop.setValue(99.0)
    widget.target.setValue(108.0)

    widget.product_currency.setText("EU1")
    widget.evaluate_proposal()
    assert "code de trois lettres" in widget.summary.toPlainText()

    widget.product_currency.setText("USD")
    widget.evaluate_proposal()
    assert widget.last_outcome_approved is False
    assert "fx_incomplete" in widget.summary.toPlainText()

    widget.fx_rate_to_eur.setValue(0.9)
    widget.evaluate_proposal()
    assert widget.last_outcome_approved is True


def test_known_product_currency_is_visible_and_locked() -> None:
    from PyQt5 import QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    widget = _configured_widget(datetime(2026, 10, 23, 10, 0, tzinfo=UTC))

    assert widget.product_currency.text() == "EUR"
    assert widget.product_currency.isReadOnly()
    assert widget.absolute_levels.isChecked()
    assert "Niveaux absolus" in widget.level_help.text()


def test_user_confirmed_eur_unblocks_barrier_with_valid_absolute_levels() -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.domain.market_data import Quote
    from trading_ig_assistant.domain.products import ProductType, TradableProduct
    from trading_ig_assistant.ui.ticket_view import PaperTicketWidget

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    now = datetime(2026, 10, 23, 15, 30, tzinfo=UTC)
    widget = PaperTicketWidget(now_provider=lambda: now)
    widget.set_product(
        TradableProduct(
            epic="PAPER.BARRIER.UNKNOWN.CURRENCY",
            name="US Tech 100 Barrières Achat",
            product_type=ProductType.BARRIER,
            status="TRADEABLE",
        )
    )
    widget.set_quote(
        Quote(
            epic="PAPER.BARRIER.UNKNOWN.CURRENCY",
            bid=28_883.2,
            offer=28_885.0,
            market_state="TRADEABLE",
        ),
        received_at_utc=now,
    )
    widget.absolute_levels.setChecked(True)
    widget.product_currency.setText("EUR")
    widget.quantity.setValue(1.0)
    widget.stop.setValue(28_880.0)
    widget.target.setValue(28_895.0)
    widget.knockout.setValue(28_879.0)
    widget.maximum_ko_loss.setValue(9.0)

    widget.evaluate_proposal()

    assert widget.last_outcome_approved is True
    assert widget.execute_button.isEnabled()
    assert "PRODUCT_CURRENCY_USER_CONFIRMED:EUR" in widget.summary.toPlainText()


def test_default_relative_values_produce_approved_barrier_paper_preview() -> None:
    from decimal import Decimal

    from PyQt5 import QtWidgets

    from trading_ig_assistant.domain.market_data import Quote
    from trading_ig_assistant.domain.products import ProductType, TradableProduct
    from trading_ig_assistant.ui.ticket_view import PaperTicketWidget

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    now = datetime(2026, 10, 23, 16, 0, tzinfo=UTC)
    widget = PaperTicketWidget(now_provider=lambda: now)
    widget.set_product(
        TradableProduct(
            epic="PAPER.BARRIER.DEFAULTS",
            name="Paper Barrier with validatable defaults",
            product_type=ProductType.BARRIER,
            currency="EUR",
            status="TRADEABLE",
            ko_level=90.0,
            min_size=1.0,
        )
    )
    widget.set_quote(
        Quote(
            epic="PAPER.BARRIER.DEFAULTS",
            bid=100.0,
            offer=101.0,
            market_state="TRADEABLE",
        ),
        received_at_utc=now,
    )

    widget.evaluate_proposal()

    assert widget.relative_levels.isChecked()
    assert widget.stop.value() == 4.0
    assert widget.target.value() == 12.0
    assert widget.maximum_ko_loss.value() == 9.0
    assert widget.last_outcome_approved is True
    assert widget.last_ticket is not None
    assert widget.last_ticket.intent.requested_stop == Decimal("97.0")
    assert widget.last_ticket.intent.requested_target == Decimal("113.0")
    assert "KO_MAX_LOSS_ASSUMPTION_REQUIRES_REVIEW" in widget.summary.toPlainText()


def test_ticket_form_keeps_horizontal_scroll_disabled_at_laptop_panel_width() -> None:
    from PyQt5 import QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    widget = _configured_widget(datetime(2026, 10, 23, 10, 0, tzinfo=UTC))
    widget.resize(650, 300)
    widget.show()
    app.processEvents()

    assert widget.horizontalScrollBar().maximum() == 0

    widget.close()
    app.processEvents()


def test_paper_ticket_widget_shows_risk_rejection() -> None:
    from PyQt5 import QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    now = datetime(2026, 10, 23, 10, 0, tzinfo=UTC)
    widget = _configured_widget(now)
    widget.quantity.setValue(10.0)

    widget.evaluate_proposal()

    assert widget.last_outcome_approved is False
    assert widget.last_decision is not None
    assert "per_trade_limit" in widget.summary.toPlainText()


def test_paper_ticket_widget_rejects_reward_risk_below_configured_minimum() -> None:
    from PyQt5 import QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    now = datetime(2026, 10, 23, 10, 0, tzinfo=UTC)
    widget = _configured_widget(now)
    widget.target.setValue(103.0)

    widget.evaluate_proposal()

    assert widget.last_outcome_approved is False
    assert widget.last_decision is not None and widget.last_decision.approved
    assert "reward_risk_below_minimum" in widget.summary.toPlainText()


def test_paper_ticket_widget_rejects_stale_quote() -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.ui.ticket_view import PaperTicketWidget

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    now = datetime(2026, 10, 23, 10, 0, tzinfo=UTC)
    widget = PaperTicketWidget(now_provider=lambda: now)
    widget.set_product(_cash_product())
    widget.set_quote(_fresh_quote(), received_at_utc=now - timedelta(seconds=31))
    widget.absolute_levels.setChecked(True)
    widget.stop.setValue(99.0)
    widget.target.setValue(108.0)

    widget.evaluate_proposal()

    assert widget.last_ticket is None
    assert "prix périmé" in widget.summary.toPlainText()


def test_barrier_preview_requires_explicit_maximum_ko_loss() -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.domain.market_data import Quote
    from trading_ig_assistant.domain.products import ProductType, TradableProduct
    from trading_ig_assistant.ui.ticket_view import PaperTicketWidget

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    now = datetime(2026, 10, 23, 10, 0, tzinfo=UTC)
    widget = PaperTicketWidget(now_provider=lambda: now)
    widget.set_product(
        TradableProduct(
            epic="PAPER.BARRIER.ONE",
            name="Paper Barrier",
            product_type=ProductType.BARRIER,
            currency="EUR",
            status="TRADEABLE",
            ko_level=90.0,
        )
    )
    widget.set_quote(
        Quote(
            epic="PAPER.BARRIER.ONE",
            bid=100.0,
            offer=101.0,
            market_state="TRADEABLE",
        ),
        received_at_utc=now,
    )
    widget.absolute_levels.setChecked(True)
    widget.stop.setValue(99.0)
    widget.target.setValue(108.0)
    widget.maximum_ko_loss.setValue(0.0)

    widget.evaluate_proposal()

    assert widget.last_ticket is None
    assert "estimation explicite de perte max KO" in widget.summary.toPlainText()


def test_product_selector_propagates_product_and_quote_to_paper_ticket() -> None:
    import inspect

    from PyQt5 import QtWidgets

    from trading_ig_assistant.ui import ticket_view
    from trading_ig_assistant.ui.product_selector import ProductSelectorWidget

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    widget = ProductSelectorWidget()

    widget.set_selected_product(_cash_product())
    widget.set_live_quote(_fresh_quote())
    widget.details_tabs.setCurrentIndex(1)

    assert widget.paper_ticket.evaluate_button.isEnabled()
    assert "Simulation" == widget.details_tabs.tabText(1)
    assert widget.product_tabs.isHidden()
    assert widget.main_layout.stretch(widget.main_layout.indexOf(widget.details_tabs)) == 2
    assert "IGRestAdapter" not in inspect.getsource(ticket_view)
    assert "PaperBroker" not in inspect.getsource(ticket_view)


def test_paper_ticket_distinguishes_chart_underlying_from_direct_product_quote() -> None:
    from PyQt5 import QtWidgets

    from trading_ig_assistant.domain.market_data import Quote
    from trading_ig_assistant.domain.products import ProductType, TradableProduct
    from trading_ig_assistant.ui.product_selector import ProductSelectorWidget

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    assert app is not None
    widget = ProductSelectorWidget()
    barrier = TradableProduct(
        epic="BARRIER.ONE",
        name="US Tech 100 Barrière Achat",
        product_type=ProductType.BARRIER,
        currency="EUR",
        status="TRADEABLE",
    )
    underlying = TradableProduct(
        epic="UNDERLYING.ONE",
        name="US Tech 100",
        product_type=ProductType.CASH_OR_DFB,
        currency="EUR",
        status="TRADEABLE",
    )

    widget.set_selected_product(barrier)
    widget.set_chart_source(underlying)
    widget.set_live_quote(
        Quote(
            epic=underlying.epic,
            bid=28_917.0,
            offer=28_919.0,
            market_state="TRADEABLE",
        )
    )

    status = widget.paper_ticket.product_status.text()
    assert "cotation directe du produit sélectionné en attente" in status
    assert "graphique utilise US Tech 100 comme sous-jacent" in status
    assert "sans réutiliser son prix pour le ticket" in status
    assert not widget.paper_ticket.evaluate_button.isEnabled()

    widget.set_live_quote(
        Quote(
            epic=barrier.epic,
            bid=101.0,
            offer=102.0,
            market_state="TRADEABLE",
        )
    )

    assert "bid 101 / ask 102" in widget.paper_ticket.product_status.text()
    assert widget.paper_ticket.evaluate_button.isEnabled()
