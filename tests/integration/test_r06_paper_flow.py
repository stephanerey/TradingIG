from datetime import UTC, datetime, timedelta
from decimal import Decimal

from trading_ig_assistant.domain.adapter_contracts import (
    AccountRef,
    ExecutionStatus,
    OrderDirection,
)
from trading_ig_assistant.domain.alerts import AlertCategory, AlertSeverity
from trading_ig_assistant.domain.pending_orders import (
    PendingGate,
    PendingObservation,
    PendingOrderState,
    PendingTriggerType,
    SoftwarePendingOrder,
)
from trading_ig_assistant.domain.positions import PaperFillAssumptions, PaperQuote
from trading_ig_assistant.domain.risk import AccountRiskState, PortfolioRiskSnapshot
from trading_ig_assistant.domain.trade_state import ManagedTrade, TradeState
from trading_ig_assistant.services.alert_service import LocalAlertService
from trading_ig_assistant.services.order_execution_coordinator import (
    PaperOrderExecutionCoordinator,
)
from trading_ig_assistant.services.paper_broker import PaperBroker
from trading_ig_assistant.services.pending_order_engine import PendingOrderEngine
from trading_ig_assistant.services.risk_engine import RiskEngine
from trading_ig_assistant.services.ticket_builder import TicketBuilder
from trading_ig_assistant.services.trade_manager import TradeManager


def test_complete_paper_flow_never_requires_an_ig_adapter() -> None:
    now = datetime(2026, 10, 22, 12, 0, tzinfo=UTC)
    account = AccountRef("paper", "paper", "PAPER-A")
    assumptions = PaperFillAssumptions(Decimal("0.1"), Decimal("0.1"), "replay-v1")
    trigger_quote = PaperQuote(
        "WTI-PAPER",
        now + timedelta(minutes=1),
        Decimal("101"),
        Decimal("102"),
        "EUR",
        provenance="fixture:r06-flow",
    )
    ticket = TicketBuilder().build(
        intent_id="FLOW-1",
        account=account,
        quote=trigger_quote,
        underlying_id="WTI",
        direction=OrderDirection.BUY,
        quantity=Decimal("1"),
        stop=Decimal("95"),
        target=None,
        knockout=Decimal("90"),
        expires_at_utc=now + timedelta(hours=1),
        assumptions=assumptions,
    )
    risk_request = TicketBuilder.risk_request(ticket, maximum_ko_loss=Decimal("15"))
    snapshot = PortfolioRiskSnapshot(
        reference_currency="EUR",
        accounts=(
            AccountRiskState(
                account=account,
                currency="EUR",
                equity_reference_day=Decimal("10000"),
                equity_current=Decimal("10000"),
                daily_net_pnl=Decimal("0"),
                confirmed=True,
            ),
        ),
    )
    risk_engine = RiskEngine()
    trigger_decision = risk_engine.evaluate(risk_request, snapshot)

    pending = SoftwarePendingOrder(
        pending_id="PENDING-FLOW-1",
        intent=ticket.intent,
        trigger_type=PendingTriggerType.CANDLE_CLOSE_ABOVE,
        trigger_level=Decimal("100"),
        trigger_zone=None,
        tolerance=Decimal("0"),
        hold_seconds=0,
        expires_at_utc=now + timedelta(minutes=30),
        confirmation_required=False,
    )
    pending_engine = PendingOrderEngine()
    pending_engine.add(pending)
    pending_engine.arm(pending.pending_id, now)
    triggered = pending_engine.evaluate(
        pending.pending_id,
        PendingObservation(
            observed_at_utc=trigger_quote.observed_at_utc,
            price=Decimal("101.5"),
            high=Decimal("103"),
            low=Decimal("100"),
            close=Decimal("101.5"),
            candle_closed=True,
            data_fresh=True,
            market_open=True,
            product_supported=True,
            macro_allows_entry=True,
        ),
        PendingGate(trigger_decision),
    )
    assert triggered.order.state is PendingOrderState.TRIGGERED

    broker = PaperBroker((account,), assumptions)
    broker.publish_quote(trigger_quote)
    coordinator = PaperOrderExecutionCoordinator(risk_engine, broker)
    executed = coordinator.execute(ticket.intent, risk_request, snapshot)
    assert executed.execution_result.status is ExecutionStatus.CONFIRMED
    pending_engine.mark_executed(pending.pending_id, now + timedelta(minutes=1, seconds=1))

    position = broker.positions(account)[0]
    trade = ManagedTrade(
        position_id=position.position_id,
        account=account,
        direction=position.direction,
        entry_price=position.entry_price,
        initial_stop=position.current_stop or Decimal("95"),
        confirmed_stop=position.current_stop or Decimal("95"),
        quantity=position.quantity,
        round_trip_cost_per_unit=Decimal("1.4"),
        state=TradeState.OPEN,
        opened_at_utc=position.opened_at_utc,
    )
    favorable_quote = PaperQuote(
        "WTI-PAPER",
        now + timedelta(minutes=2),
        Decimal("110"),
        Decimal("111"),
        "EUR",
        provenance="fixture:r06-flow",
    )
    broker.publish_quote(favorable_quote)
    manager = TradeManager()
    proposal = manager.recommend_break_even(
        trade,
        current_price=favorable_quote.bid,
        generated_at_utc=favorable_quote.observed_at_utc,
    ).proposal
    assert proposal is not None
    stop_result = broker.move_stop(account, position.position_id, proposal.proposed_stop)
    protected = manager.apply_stop_confirmation(trade, proposal, stop_result)
    assert protected.trade.state is TradeState.PROTECTED

    closing = manager.mark_closing(protected.trade, now + timedelta(minutes=3))
    close_result = coordinator.close(account, position.position_id)
    closed = manager.confirm_closed(closing, close_result, now + timedelta(minutes=3))
    assert closed.state is TradeState.CLOSED
    assert risk_engine.reservations() == ()

    alerts = LocalAlertService()
    alert = alerts.publish(
        category=AlertCategory.ORDER_RESULT,
        severity=AlertSeverity.INFO,
        message="Paper flow closed",
        correlation_id=ticket.intent.intent_id,
        timestamp_utc=favorable_quote.observed_at_utc,
    )
    assert alert is not None
    assert [event.event_type for event in broker.events()] == [
        "PAPER_POSITION_OPENED",
        "PAPER_STOP_CONFIRMED",
        "PAPER_POSITION_CLOSED",
    ]
