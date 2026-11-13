from datetime import UTC, datetime, timedelta
from decimal import Decimal

from PyQt5 import QtTest, QtWidgets

from trading_ig_assistant.app.projections.account_projection import (
    build_runtime_health_projection,
)
from trading_ig_assistant.app.qt_paper_session_controller import PaperSessionController
from trading_ig_assistant.app.runtime.trading_runtime import TradingRuntime
from trading_ig_assistant.domain.adapter_contracts import (
    ExecutionResult,
    ExecutionStatus,
    OrderDirection,
)
from trading_ig_assistant.domain.journal import JournalEvent, PnlStatus
from trading_ig_assistant.domain.market_data import Quote
from trading_ig_assistant.domain.positions import PaperFillAssumptions, PaperQuote
from trading_ig_assistant.domain.risk import AccountRiskState, PortfolioRiskSnapshot
from trading_ig_assistant.persistence.repositories import PaperSessionSnapshotRepository
from trading_ig_assistant.persistence.sqlite_store import SQLiteStore
from trading_ig_assistant.services.paper_session import (
    LOCAL_PAPER_ACCOUNT,
    PaperSessionService,
    PaperSessionState,
    PaperTicketSubmission,
)
from trading_ig_assistant.services.risk_engine import resolve_risk_settings
from trading_ig_assistant.services.ticket_builder import TicketBuilder

NOW = datetime(2026, 11, 9, 18, 0, tzinfo=UTC)


def _application() -> QtWidgets.QApplication:
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _session(session_id: str, event_id: str) -> PaperSessionService:
    event = JournalEvent(
        event_id=event_id,
        timestamp_utc=NOW,
        event_type="PAPER_POSITION_CLOSED",
        correlation_id=event_id,
        account_ref="paper:local-paper-preview",
        instrument_id="IX.D.CAC.IMF.IP",
        pnl_amount=Decimal("12.50"),
        pnl_currency="EUR",
        pnl_status=PnlStatus.REALIZED,
    )
    return PaperSessionService.from_checkpoint_state(
        PaperSessionState(
            session_id=session_id,
            orders=(),
            positions=(),
            events=(event,),
            latest_quotes=(),
            assumptions=(),
            currencies=(),
        ),
        now_provider=lambda: NOW,
    )


def _paper_submission(at: datetime) -> PaperTicketSubmission:
    quote = PaperQuote(
        product_id="IX.D.CAC.IMF.IP",
        observed_at_utc=at,
        bid=Decimal("8261.7"),
        ask=Decimal("8264.2"),
        currency="EUR",
        provenance="gui-received-quote",
    )
    assumptions = PaperFillAssumptions(
        fee_per_unit_per_side=Decimal("0"),
        slippage_points_per_side=Decimal("0"),
        model_version="gui-v2-controller-test",
    )
    ticket = TicketBuilder().build(
        intent_id="gui-v2-paper-submit",
        account=LOCAL_PAPER_ACCOUNT,
        quote=quote,
        underlying_id="FRANCE_40",
        direction=OrderDirection.BUY,
        quantity=Decimal("0.5"),
        stop=Decimal("8259.2"),
        target=Decimal("8275.2"),
        knockout=None,
        expires_at_utc=at + timedelta(minutes=15),
        assumptions=assumptions,
    )
    return PaperTicketSubmission(
        ticket=ticket,
        risk_request=TicketBuilder.risk_request(ticket, maximum_ko_loss=None),
        risk_snapshot=PortfolioRiskSnapshot(
            reference_currency="EUR",
            accounts=(
                AccountRiskState(
                    account=LOCAL_PAPER_ACCOUNT,
                    currency="EUR",
                    equity_reference_day=Decimal("1000"),
                    equity_current=Decimal("1000"),
                    daily_net_pnl=Decimal("0"),
                    confirmed=True,
                ),
            ),
        ),
        risk_settings=resolve_risk_settings(),
        quote=quote,
        assumptions=assumptions,
    )


def test_controller_explicit_save_and_restore_publish_local_paper_state(tmp_path) -> None:
    database_path = tmp_path / "paper.sqlite"
    source_runtime = TradingRuntime(now_provider=lambda: NOW)
    source = PaperSessionController(
        runtime=source_runtime,
        database_path=database_path,
        session=_session("source-session", "SOURCE-EVENT"),
        now_provider=lambda: NOW,
    )
    messages: list[str] = []
    source.message.connect(messages.append)

    source.save()

    assert database_path.exists()
    assert messages == ["paper.save_succeeded"]
    paper_health = {
        item.service_id: item for item in source_runtime.read_health()
    }["paper-sqlite"]
    assert paper_health.summary == "snapshot saved"
    assert paper_health.last_success_at_utc == NOW

    restored_runtime = TradingRuntime(now_provider=lambda: NOW)
    restored = PaperSessionController(
        runtime=restored_runtime,
        database_path=database_path,
        now_provider=lambda: NOW,
    )
    restored.message.connect(messages.append)

    restored.request_restore()

    assert restored.session.session_id == "source-session"
    assert len(restored.session.events()) == 2
    assert restored_runtime.read_dashboard().availability.value == "ready"
    assert restored_runtime.read_dashboard().realized_pnl
    assert len(restored_runtime.read_paper_history().rows) == 2
    assert {
        row.event_type for row in restored_runtime.read_paper_history().rows
    } == {"PAPER_POSITION_CLOSED", "PAPER_SESSION_RESTORED"}
    assert messages[-1] == "paper.restore_succeeded"


def test_restore_requires_confirmation_before_replacing_nonempty_session(tmp_path) -> None:
    database_path = tmp_path / "paper.sqlite"
    source = PaperSessionController(
        runtime=TradingRuntime(now_provider=lambda: NOW),
        database_path=database_path,
        session=_session("saved-session", "SAVED-EVENT"),
        now_provider=lambda: NOW,
    )
    source.save()
    target = PaperSessionController(
        runtime=TradingRuntime(now_provider=lambda: NOW),
        database_path=database_path,
        session=_session("current-session", "CURRENT-EVENT"),
        now_provider=lambda: NOW,
    )
    confirmations: list[bool] = []
    target.restore_confirmation_required.connect(lambda: confirmations.append(True))

    target.request_restore()
    assert confirmations == [True]
    assert target.session.session_id == "current-session"

    target.confirm_restore(False)
    assert target.session.session_id == "current-session"

    target.request_restore()
    target.confirm_restore(True)
    assert target.session.session_id == "saved-session"


def test_invalid_checkpoint_is_rejected_without_replacing_current_session(tmp_path) -> None:
    database_path = tmp_path / "paper.sqlite"
    store = SQLiteStore(database_path)
    store.initialize()
    PaperSessionSnapshotRepository(store).save(
        snapshot_id="invalid",
        session_id="invalid-session",
        saved_at_utc=NOW,
        payload={"format_version": 999},
    )
    current = _session("current-session", "CURRENT-EVENT")
    controller = PaperSessionController(
        runtime=TradingRuntime(now_provider=lambda: NOW),
        database_path=database_path,
        session=current,
        now_provider=lambda: NOW,
    )
    errors: list[str] = []
    controller.error.connect(errors.append)

    controller.request_restore()

    assert controller.session is current
    assert errors and errors[0].startswith("paper.restore_failed|")


def test_empty_session_cannot_create_a_snapshot(tmp_path) -> None:
    database_path = tmp_path / "paper.sqlite"
    controller = PaperSessionController(
        runtime=TradingRuntime(now_provider=lambda: NOW),
        database_path=database_path,
        now_provider=lambda: NOW,
    )
    errors: list[str] = []
    controller.error.connect(errors.append)

    controller.save()

    assert errors == ["paper.save_empty"]
    assert not database_path.exists()


def test_explicit_confirmed_submission_opens_only_the_local_paper_session(tmp_path) -> None:
    _application()
    runtime = TradingRuntime(now_provider=lambda: NOW)
    controller = PaperSessionController(
        runtime=runtime,
        database_path=tmp_path / "paper.sqlite",
        now_provider=lambda: NOW,
    )
    completed: list[object] = []
    messages: list[str] = []
    controller.submission_completed.connect(completed.append)
    controller.message.connect(messages.append)

    controller.submit(_paper_submission(NOW))

    assert len(completed) == 1
    assert len(controller.session.position_snapshots()) == 1
    assert len(runtime.read_dashboard().open_positions) == 1
    assert messages == ["paper.open_succeeded"]


def test_controller_rejects_a_submission_whose_quote_expired_before_confirmation(
    tmp_path,
) -> None:
    _application()
    controller = PaperSessionController(
        runtime=TradingRuntime(now_provider=lambda: NOW),
        database_path=tmp_path / "paper.sqlite",
        now_provider=lambda: NOW,
    )
    errors: list[str] = []
    controller.error.connect(errors.append)

    controller.submit(_paper_submission(NOW - timedelta(minutes=1)))

    assert errors == ["paper.open_stale"]
    assert controller.session.position_snapshots() == ()


def test_runtime_health_updates_preserve_unrelated_paper_service(tmp_path) -> None:
    runtime = TradingRuntime(now_provider=lambda: NOW)
    PaperSessionController(
        runtime=runtime,
        database_path=tmp_path / "paper.sqlite",
        now_provider=lambda: NOW,
    )
    runtime.publish_health(
        build_runtime_health_projection(
            generation_id=runtime.generation_id,
            rest_status="connected",
            stream_status="live",
            ai_status="not_configured",
            observed_at_utc=NOW,
        ),
        generation_id=runtime.generation_id,
    )

    health = {item.service_id: item for item in runtime.read_health()}

    assert set(health) == {"paper-sqlite", "ig-rest", "ig-streaming", "openai"}
    assert health["paper-sqlite"].summary == "empty session"


def test_observed_quotes_update_only_already_tracked_local_paper_products(tmp_path) -> None:
    _application()
    tracked = PaperSessionService.from_checkpoint_state(
        PaperSessionState(
            session_id="tracked-session",
            orders=(),
            positions=(),
            events=(),
            latest_quotes=(),
            assumptions=(),
            currencies=(("TRACKED.EPIC", "EUR"),),
        ),
        now_provider=lambda: NOW,
    )
    controller = PaperSessionController(
        runtime=TradingRuntime(now_provider=lambda: NOW),
        database_path=tmp_path / "paper.sqlite",
        session=tracked,
        now_provider=lambda: NOW,
    )

    controller.process_market_quote(
        Quote(
            epic="UNTRACKED.EPIC",
            bid=10.0,
            offer=11.0,
            market_state="TRADEABLE",
        )
    )
    assert tracked.checkpoint_state().latest_quotes == ()

    controller.process_market_quote(
        Quote(
            epic="TRACKED.EPIC",
            bid=10.0,
            offer=11.0,
            market_state="TRADEABLE",
        )
    )
    QtTest.QTest.qWait(300)

    latest_quotes = dict(tracked.checkpoint_state().latest_quotes)
    assert latest_quotes["TRACKED.EPIC"].bid == Decimal("10.0")
    assert latest_quotes["TRACKED.EPIC"].fresh is True

    controller.invalidate_market_quotes()
    assert dict(tracked.checkpoint_state().latest_quotes)["TRACKED.EPIC"].fresh is False


def test_local_stop_and_close_actions_require_explicit_intents(tmp_path) -> None:
    class FakePaperSession:
        session_id = "fake-paper-session"

        def __init__(self) -> None:
            self.stop_calls: list[tuple[str, Decimal]] = []
            self.close_calls: list[str] = []

        def position_snapshots(self) -> tuple[object, ...]:
            return ()

        def events(self) -> tuple[JournalEvent, ...]:
            return ()

        def has_state(self) -> bool:
            return False

        def move_stop(self, position_id: str, stop: Decimal) -> ExecutionResult:
            self.stop_calls.append((position_id, stop))
            return ExecutionResult(
                intent_id=position_id,
                account=LOCAL_PAPER_ACCOUNT,
                status=ExecutionStatus.CONFIRMED,
            )

        def close_position(self, position_id: str) -> ExecutionResult:
            self.close_calls.append(position_id)
            return ExecutionResult(
                intent_id=position_id,
                account=LOCAL_PAPER_ACCOUNT,
                status=ExecutionStatus.CONFIRMED,
            )

    session = FakePaperSession()
    controller = PaperSessionController(
        runtime=TradingRuntime(now_provider=lambda: NOW),
        database_path=tmp_path / "paper.sqlite",
        session=session,  # type: ignore[arg-type]
        now_provider=lambda: NOW,
    )
    messages: list[str] = []
    confirmations: list[str] = []
    controller.message.connect(messages.append)
    controller.close_confirmation_required.connect(confirmations.append)

    controller.move_stop("PAPER-1", "99,5")
    controller.request_close("PAPER-1")
    controller.confirm_close("PAPER-1", False)
    controller.confirm_close("PAPER-1", True)

    assert session.stop_calls == [("PAPER-1", Decimal("99.5"))]
    assert confirmations == ["PAPER-1"]
    assert session.close_calls == ["PAPER-1"]
    assert messages == ["paper.stop_succeeded", "paper.close_succeeded"]
