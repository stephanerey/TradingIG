from datetime import UTC, datetime
from decimal import Decimal

from PyQt5 import QtCore, QtWidgets

from trading_ig_assistant.app.projections.account_projection import (
    build_account_header_projection,
)
from trading_ig_assistant.app.projections.common import Availability
from trading_ig_assistant.app.projections.dashboard_projection import (
    build_paper_dashboard_projection,
    merge_account_metrics_into_dashboard,
)
from trading_ig_assistant.app.projections.paper_history_projection import (
    build_paper_history_projection,
)
from trading_ig_assistant.app.runtime.trading_runtime import TradingRuntime
from trading_ig_assistant.domain.adapter_contracts import AccountRef, OrderDirection
from trading_ig_assistant.domain.instruments import Account
from trading_ig_assistant.domain.journal import JournalEvent, PnlPeriod, PnlStatus
from trading_ig_assistant.domain.positions import PaperPosition
from trading_ig_assistant.services.paper_session import PaperPositionSnapshot

NOW = datetime(2026, 11, 9, 12, 0, tzinfo=UTC)
PAPER_ACCOUNT = AccountRef("paper", "paper", "local-paper-preview")


def _application() -> QtWidgets.QApplication:
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _position(position_id: str = "PAPER-1") -> PaperPosition:
    return PaperPosition(
        position_id=position_id,
        intent_id=f"INTENT-{position_id}",
        account=PAPER_ACCOUNT,
        product_id="CS.D.EURUSD.CFD.IP",
        underlying_id="EURUSD",
        direction=OrderDirection.BUY,
        quantity=Decimal("2"),
        entry_price=Decimal("1.1000"),
        current_stop=Decimal("1.0900"),
        target=Decimal("1.1200"),
        knockout=None,
        opened_at_utc=NOW,
        opening_fee=Decimal("0.20"),
        entry_slippage=Decimal("0.0001"),
        currency="EUR",
        price_provenance="paper-fixture",
        fill_model_version="paper-fill-v1",
    )


def _realized_event(event_id: str, amount: str, currency: str) -> JournalEvent:
    return JournalEvent(
        event_id=event_id,
        timestamp_utc=NOW,
        event_type="PAPER_POSITION_CLOSED",
        correlation_id=event_id,
        account_ref="paper:local-paper-preview",
        instrument_id="CS.D.EURUSD.CFD.IP",
        pnl_amount=Decimal(amount),
        pnl_currency=currency,
        pnl_status=PnlStatus.REALIZED,
    )


def test_dashboard_projection_keeps_paper_scope_currency_and_unknowns_explicit() -> None:
    fresh = PaperPositionSnapshot(
        position=_position("PAPER-FRESH"),
        mark_price=Decimal("1.1050"),
        net_pnl=Decimal("9.40"),
    )
    stale = PaperPositionSnapshot(
        position=_position("PAPER-STALE"),
        mark_price=None,
        net_pnl=None,
    )

    dashboard = build_paper_dashboard_projection(
        generation_id=3,
        positions=(fresh, stale),
        events=(
            _realized_event("EVENT-EUR", "12.50", "EUR"),
            _realized_event("EVENT-USD", "5.00", "USD"),
        ),
        generated_at_utc=NOW,
    )

    assert dashboard.execution_mode == "PAPER"
    assert dashboard.account_id == "local-paper-preview"
    assert dashboard.equity is None
    assert dashboard.available_funds is None
    assert dashboard.win_rate is None
    assert dashboard.equity_history_available is False
    assert len(dashboard.open_positions) == 2
    assert dashboard.open_positions[0].net_pnl.estimate is True
    assert dashboard.open_positions[1].mark_price.value is None
    assert dashboard.open_positions[1].mark_price.provenance.availability is Availability.STALE
    day_totals = [item for item in dashboard.realized_pnl if item.period is PnlPeriod.DAY]
    assert [(item.amount.value, item.amount.currency) for item in day_totals] == [
        (Decimal("12.50"), "EUR"),
        (Decimal("5.00"), "USD"),
    ]


def test_runtime_rejects_stale_dashboard_generation() -> None:
    runtime = TradingRuntime(now_provider=lambda: NOW)
    stale = build_paper_dashboard_projection(
        generation_id=runtime.generation_id,
        positions=(),
        events=(),
        generated_at_utc=NOW,
    )
    runtime.begin_generation()

    assert runtime.publish_dashboard(stale) is False
    assert runtime.read_dashboard().availability is Availability.UNAVAILABLE


def test_dashboard_merges_attested_ig_account_rest_metrics() -> None:
    dashboard = build_paper_dashboard_projection(
        generation_id=2,
        positions=(),
        events=(),
        generated_at_utc=NOW,
    )
    account = Account(
        account_id="DEMO-CFD",
        account_name="Demo CFD",
        account_type="CFD",
        currency="EUR",
        balance=10000.0,
        available=9250.5,
        deposit=500.0,
        profit_loss=-249.5,
    )
    header = build_account_header_projection(
        generation_id=2,
        account=account,
        environment="demo",
        execution_mode="PAPER",
        open_positions_count=0,
        rest_status="connected",
        stream_status="disconnected",
        ai_status="not_configured",
        generated_at_utc=NOW,
    )

    merged = merge_account_metrics_into_dashboard(dashboard, header)

    assert merged.broker_account_id == "DEMO-CFD"
    assert merged.account_balance is not None
    assert merged.account_balance.value == Decimal("10000.0")
    assert merged.available_funds is not None
    assert merged.available_funds.value == Decimal("9250.5")
    assert merged.account_profit_loss is not None
    assert merged.account_profit_loss.value == Decimal("-249.5")
    assert merged.margin_deposit is not None
    assert merged.margin_deposit.value == Decimal("500.0")
    assert merged.account_balance.provenance.source == "ig-rest-accounts"


def test_dashboard_statistics_require_one_attested_paper_currency() -> None:
    dashboard = build_paper_dashboard_projection(
        generation_id=0,
        positions=(),
        events=(
            _realized_event("WIN", "10", "EUR"),
            _realized_event("LOSS", "-4", "EUR"),
        ),
        generated_at_utc=NOW,
    )

    assert dashboard.win_rate == Decimal("0.5")
    assert dashboard.profit_factor == Decimal("2.5")
    assert dashboard.drawdown is not None
    assert dashboard.drawdown.value == Decimal("4")
    assert dashboard.drawdown.currency == "EUR"


def test_dashboard_page_renders_read_only_paper_rows_and_honest_na() -> None:
    from trading_ig_assistant.ui.i18n.language_manager import LanguageManager
    from trading_ig_assistant.ui.pages.dashboard_page import DashboardPage

    app = _application()
    dashboard = build_paper_dashboard_projection(
        generation_id=0,
        positions=(
            PaperPositionSnapshot(
                position=_position(),
                mark_price=Decimal("1.1050"),
                net_pnl=Decimal("9.40"),
            ),
        ),
        events=(_realized_event("EVENT-EUR", "12.50", "EUR"),),
        generated_at_utc=NOW,
    )
    language = LanguageManager("fr_FR")
    page = DashboardPage(language)
    page.set_snapshot(dashboard)
    page.show()
    app.processEvents()

    assert page._kpis["balance"].value.text() == "N/A"
    assert page._kpis["day_pnl"].value.text() == "12.50 EUR"
    assert page._kpis["positions"].value.text() == "1"
    assert page.position_model.rowCount() == 1
    assert (
        page.position_model.data(page.position_model.index(0, 0), QtCore.Qt.UserRole) == "PAPER-1"
    )
    assert "snapshot" in page.equity_history_message.text().lower()
    assert page._kpis["win_rate"].value.text() == "100.00%"
    assert page._kpis["drawdown"].value.text() == "0 EUR"
    assert len(page.performance_plot.getPlotItem().items) == 1

    page.performance_mode.setCurrentIndex(page.performance_mode.findData("percent"))
    app.processEvents()
    assert "N/A" in page.performance_message.text()
    assert page.performance_plot.getPlotItem().items == []

    language.set_locale("en_US")
    page.retranslate_ui()
    assert page._kpis["positions"].title.text() == "Open simulated positions"
    page.close()
    language.close()
    app.processEvents()


def test_positions_page_reuses_paper_projection_with_local_persistence_only() -> None:
    from trading_ig_assistant.ui.i18n.language_manager import LanguageManager
    from trading_ig_assistant.ui.pages.positions_page import PositionsPage

    app = _application()
    dashboard = build_paper_dashboard_projection(
        generation_id=0,
        positions=(
            PaperPositionSnapshot(
                position=_position(),
                mark_price=Decimal("1.1050"),
                net_pnl=Decimal("9.40"),
            ),
        ),
        events=(),
        generated_at_utc=NOW,
    )
    language = LanguageManager("fr_FR")
    page = PositionsPage(language)
    page.set_snapshot(dashboard)
    page.show()
    app.processEvents()

    assert page.tabs.count() == 5
    assert page.open_model.rowCount() == 1
    assert page.paper_model.rowCount() == 1
    buttons = page.findChildren(QtWidgets.QPushButton)
    assert buttons == [
        page.paper_save_button,
        page.paper_restore_button,
        page.paper_stop_button,
        page.paper_close_button,
    ]
    assert all("IG" in button.toolTip() for button in buttons)
    button_text = " ".join(button.text() for button in buttons)
    assert all(term not in button_text for term in ("LIVE", "AUTO"))
    assert "Lecture seule" in page.safety.text()
    requested: list[str] = []
    page.paper_close_requested.connect(requested.append)
    page.paper_table.selectRow(0)
    page.paper_close_button.click()
    assert requested == ["PAPER-1"]

    page.close()
    language.close()


def test_history_page_shows_only_attested_realized_pnl_and_macro_stays_inactive() -> None:
    from trading_ig_assistant.ui.i18n.language_manager import LanguageManager
    from trading_ig_assistant.ui.pages.history_page import HistoryPage
    from trading_ig_assistant.ui.pages.macro_page import MacroPage

    app = _application()
    dashboard = build_paper_dashboard_projection(
        generation_id=0,
        positions=(),
        events=(_realized_event("EVENT-EUR", "12.50", "EUR"),),
        generated_at_utc=NOW,
    )
    language = LanguageManager("fr_FR")
    history = HistoryPage(language)
    history.set_snapshot(dashboard)
    history.set_paper_history(
        build_paper_history_projection(
            generation_id=0,
            events=(
                _realized_event("EVENT-EUR", "12.50", "EUR"),
                _realized_event("EVENT-USD", "5.00", "USD"),
            ),
            generated_at_utc=NOW,
        )
    )
    macro = MacroPage(language)
    history.show()
    macro.show()
    app.processEvents()

    assert history.pnl_table.rowCount() >= 1
    assert history.journal_table.rowCount() == 2
    history.journal_filter.setText("EVENT-USD")
    app.processEvents()
    assert sum(
        not history.journal_table.isRowHidden(row)
        for row in range(history.journal_table.rowCount())
    ) == 1
    assert "append-only" in history.pnl_scope.text()
    assert macro.tabs.count() == 4
    assert set(macro.findChildren(QtWidgets.QPushButton)) == {
        macro.news_refresh_button,
        macro.ai_run_button,
    }
    assert "RSS" in macro.news_refresh_button.toolTip()
    assert "OPENAI_API_KEY" in macro._messages[3].text()
    assert macro.ai_run_button.isEnabled() is False

    history.close()
    macro.close()
    language.close()
