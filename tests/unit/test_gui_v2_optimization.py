from datetime import UTC, datetime, timedelta
from decimal import Decimal

from PyQt5 import QtWidgets

from trading_ig_assistant.app.projections.optimization import (
    OptimizationReviewStatus,
)
from trading_ig_assistant.app.projections.optimization_projection import (
    build_optimization_review,
)
from trading_ig_assistant.app.runtime.trading_runtime import TradingRuntime
from trading_ig_assistant.domain.journal import JournalEvent, PnlStatus

NOW = datetime(2026, 11, 9, 12, 0, tzinfo=UTC)


def _application() -> QtWidgets.QApplication:
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _closure(index: int, *, currency: str = "EUR") -> JournalEvent:
    return JournalEvent(
        event_id=f"CLOSE-{index}",
        timestamp_utc=NOW + timedelta(minutes=index),
        event_type="PAPER_POSITION_CLOSED",
        correlation_id=f"TRADE-{index}",
        account_ref="paper:local-paper-preview",
        instrument_id="CS.D.EURUSD.CFD.IP",
        pnl_amount=Decimal("1") if index % 2 else Decimal("-0.5"),
        pnl_currency=currency,
        pnl_status=PnlStatus.REALIZED,
    )


def test_optimization_review_refuses_to_invent_proposals_without_versioned_replay() -> None:
    snapshot = build_optimization_review(
        generation_id=4,
        events=tuple(_closure(index) for index in range(40)),
        generated_at_utc=NOW,
    )

    assert snapshot.status is OptimizationReviewStatus.INSUFFICIENT_EVIDENCE
    assert snapshot.trade_count == 40
    assert snapshot.currencies == ("EUR",)
    assert "SAMPLE_SIZE_EXPLORATORY" not in snapshot.reason_codes
    assert "DATASET_NOT_VERSIONED" in snapshot.reason_codes
    assert "OUT_OF_SAMPLE_REPLAY_NOT_RUN" in snapshot.reason_codes
    assert snapshot.external_ai_authorized is False
    assert snapshot.proposals == ()


def test_optimization_review_is_generation_scoped_and_rejects_stale_publish() -> None:
    runtime = TradingRuntime(now_provider=lambda: NOW)
    snapshot = build_optimization_review(
        generation_id=runtime.generation_id,
        events=(_closure(1),),
        generated_at_utc=NOW,
    )
    runtime.begin_generation()

    assert runtime.publish_optimization(snapshot) is False
    assert runtime.read_optimization().trade_count == 0


def test_history_and_dashboard_render_governed_optimization_evidence() -> None:
    from trading_ig_assistant.ui.i18n.language_manager import LanguageManager
    from trading_ig_assistant.ui.pages.dashboard_page import DashboardPage
    from trading_ig_assistant.ui.pages.history_page import HistoryPage

    app = _application()
    snapshot = build_optimization_review(
        generation_id=0,
        events=(_closure(1), _closure(2, currency="USD")),
        generated_at_utc=NOW,
    )
    language = LanguageManager("fr_FR")
    dashboard = DashboardPage(language)
    history = HistoryPage(language)
    dashboard.set_optimization(snapshot)
    history.set_optimization(snapshot)
    dashboard.show()
    history.show()
    app.processEvents()

    assert "INSUFFICIENT_EVIDENCE" in dashboard.ai_message.text()
    assert dashboard.ai_evidence.rowCount() == 6
    assert "INSUFFICIENT_EVIDENCE" in history.optimization_status.text()
    assert history.optimization_table.rowCount() == 5 + len(snapshot.reason_codes)
    assert not history.findChildren(QtWidgets.QPushButton)
    rendered = " ".join(
        history.optimization_table.item(row, 1).text()
        for row in range(history.optimization_table.rowCount())
    )
    assert "NON AUTORISÉ" in rendered
    assert "Dataset non versionné" in rendered

    language.set_locale("en_US")
    history.retranslate_ui()
    assert "NOT AUTHORIZED" in " ".join(
        history.optimization_table.item(row, 1).text()
        for row in range(history.optimization_table.rowCount())
    )
    dashboard.close()
    history.close()
    language.close()
