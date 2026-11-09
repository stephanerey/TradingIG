from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from trading_ig_assistant.domain.adapter_contracts import (
    AccountIsolationError,
    AccountRef,
    BrokerAdapter,
    CapabilitySupport,
    ExecutionStatus,
    OrderDirection,
    OrderIntent,
)
from trading_ig_assistant.domain.positions import (
    PaperExitReason,
    PaperFillAssumptions,
    PaperPositionStatus,
    PaperQuote,
)
from trading_ig_assistant.domain.risk import (
    AccountRiskState,
    PortfolioRiskSnapshot,
    RiskAction,
    RiskDecision,
    RiskDecisionStatus,
    RiskRequest,
)
from trading_ig_assistant.services.order_execution_coordinator import (
    PaperOrderExecutionCoordinator,
)
from trading_ig_assistant.services.paper_broker import PaperBroker
from trading_ig_assistant.services.risk_engine import RiskEngine

NOW = datetime(2026, 10, 22, 12, 0, tzinfo=UTC)
ACCOUNT = AccountRef("paper", "paper", "PAPER-A")


def _quote(
    bid: str = "100",
    ask: str = "101",
    *,
    observed_at: datetime = NOW,
    fresh: bool = True,
) -> PaperQuote:
    return PaperQuote(
        product_id="WTI-PAPER",
        observed_at_utc=observed_at,
        bid=Decimal(bid),
        ask=Decimal(ask),
        currency="EUR",
        fresh=fresh,
        provenance="fixture:quote-1",
    )


def _intent(
    intent_id: str = "INTENT-1",
    *,
    direction: OrderDirection = OrderDirection.BUY,
    quantity: str = "2",
    stop: str | None = "95",
    target: str | None = "110",
    knockout: str | None = "90",
) -> OrderIntent:
    return OrderIntent(
        intent_id=intent_id,
        account=ACCOUNT,
        product_id="WTI-PAPER",
        underlying_id="WTI",
        direction=direction,
        quantity=Decimal(quantity),
        requested_stop=Decimal(stop) if stop else None,
        requested_target=Decimal(target) if target else None,
        requested_ko=Decimal(knockout) if knockout else None,
        signal_id="SIGNAL-1",
        expires_at_utc=NOW + timedelta(hours=1),
    )


def _approved() -> RiskDecision:
    return RiskDecision(status=RiskDecisionStatus.APPROVED)


def _broker() -> PaperBroker:
    broker = PaperBroker(
        (ACCOUNT,),
        PaperFillAssumptions(
            fee_per_unit_per_side=Decimal("1"),
            slippage_points_per_side=Decimal("0.5"),
            model_version="fixture-v1",
        ),
    )
    broker.publish_quote(_quote())
    return broker


def test_paper_broker_is_contract_compatible_but_never_live_capable() -> None:
    broker = _broker()

    assert isinstance(broker, BrokerAdapter)
    capabilities = broker.capabilities(ACCOUNT, "WTI-PAPER")
    assert capabilities.place_orders is CapabilitySupport.SUPPORTED
    assert capabilities.demo_execution is CapabilitySupport.UNSUPPORTED
    assert capabilities.live_execution is CapabilitySupport.UNSUPPORTED


def test_direct_submission_without_risk_approval_is_rejected() -> None:
    broker = _broker()

    result = broker.submit(_intent())

    assert result.status is ExecutionStatus.REJECTED
    assert result.message == "RISK_APPROVAL_REQUIRED"
    assert broker.positions(ACCOUNT) == ()


def test_approved_fill_retains_cost_slippage_and_provenance() -> None:
    broker = _broker()
    intent = _intent()
    broker.authorize(intent, _approved())

    result = broker.submit(intent)
    position = broker.positions(ACCOUNT)[0]

    assert result.status is ExecutionStatus.CONFIRMED
    assert position.entry_price == Decimal("101.5")
    assert position.opening_fee == Decimal("2")
    assert position.entry_slippage == Decimal("0.5")
    assert position.price_provenance == "fixture:quote-1"
    assert broker.events()[0].payload["fill_model"] == "fixture-v1"


def test_intent_specific_assumptions_are_used_for_open_and_close() -> None:
    broker = _broker()
    intent = _intent(target=None)
    assumptions = PaperFillAssumptions(
        fee_per_unit_per_side=Decimal("0.25"),
        slippage_points_per_side=Decimal("0.2"),
        model_version="ticket-specific-v1",
    )
    broker.authorize(intent, _approved(), assumptions)

    opened = broker.submit(intent)
    broker.publish_quote(_quote("105", "106", observed_at=NOW + timedelta(minutes=1)))
    broker.close(ACCOUNT, opened.broker_reference or "")
    position = broker.positions(ACCOUNT)[0]

    assert position.entry_price == Decimal("101.2")
    assert position.opening_fee == Decimal("0.50")
    assert position.close_price == Decimal("104.8")
    assert position.closing_fee == Decimal("0.50")
    assert position.fill_model_version == "ticket-specific-v1"
    assert broker.events()[-1].payload["fill_model"] == "ticket-specific-v1"


def test_duplicate_concurrent_intent_creates_one_fill() -> None:
    broker = _broker()
    intent = _intent()
    broker.authorize(intent, _approved())

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(lambda _index: broker.submit(intent), range(4)))

    assert len({result.broker_reference for result in results}) == 1
    assert len(broker.positions(ACCOUNT)) == 1
    assert len(broker.events()) == 1


def test_manual_close_uses_executable_side_and_realizes_net_pnl() -> None:
    broker = _broker()
    intent = _intent(target=None)
    broker.authorize(intent, _approved())
    opened = broker.submit(intent)
    broker.publish_quote(_quote("105", "106", observed_at=NOW + timedelta(minutes=1)))

    result = broker.close(ACCOUNT, opened.broker_reference or "")
    position = broker.positions(ACCOUNT)[0]

    assert result.status is ExecutionStatus.CONFIRMED
    assert position.status is PaperPositionStatus.CLOSED
    assert position.close_price == Decimal("104.5")
    assert position.realized_pnl == Decimal("2.0")
    assert position.exit_reason is PaperExitReason.MANUAL
    assert broker.events()[-1].pnl_amount == Decimal("2.0")


def test_gap_through_stop_fills_at_observed_executable_price() -> None:
    broker = _broker()
    intent = _intent(stop="95", target=None, knockout=None)
    broker.authorize(intent, _approved())
    broker.submit(intent)

    results = broker.process_quote(_quote("90", "91", observed_at=NOW + timedelta(minutes=1)))
    position = broker.positions(ACCOUNT)[0]

    assert len(results) == 1
    assert position.exit_reason is PaperExitReason.STOP
    assert position.close_price == Decimal("89.5")
    assert position.close_price != intent.requested_stop


def test_stale_quote_cannot_trigger_a_paper_exit() -> None:
    broker = _broker()
    intent = _intent(stop="95", target=None, knockout=None)
    broker.authorize(intent, _approved())
    broker.submit(intent)

    results = broker.process_quote(
        _quote("90", "91", observed_at=NOW + timedelta(minutes=1), fresh=False)
    )

    assert results == ()
    assert broker.positions(ACCOUNT)[0].status is PaperPositionStatus.OPEN


def test_direct_intent_with_contradictory_levels_is_rejected() -> None:
    broker = _broker()
    intent = _intent(stop="105")
    broker.authorize(intent, _approved())

    result = broker.submit(intent)

    assert result.status is ExecutionStatus.REJECTED
    assert result.message == "INVALID_DIRECTIONAL_LEVELS"


def test_stop_cannot_be_widened_but_can_be_tightened() -> None:
    broker = _broker()
    intent = _intent()
    broker.authorize(intent, _approved())
    opened = broker.submit(intent)
    position_id = opened.broker_reference or ""

    widened = broker.move_stop(ACCOUNT, position_id, Decimal("94"))
    tightened = broker.move_stop(ACCOUNT, position_id, Decimal("100"))

    assert widened.status is ExecutionStatus.REJECTED
    assert widened.message == "STOP_WIDENING_FORBIDDEN"
    assert tightened.status is ExecutionStatus.CONFIRMED
    assert broker.positions(ACCOUNT)[0].current_stop == Decimal("100")


def test_non_paper_account_is_rejected() -> None:
    broker = _broker()
    live = AccountRef("ig", "live", "LIVE-A")

    with pytest.raises(AccountIsolationError):
        broker.positions(live)


def test_execution_coordinator_requires_real_risk_approval() -> None:
    broker = _broker()
    engine = RiskEngine()
    coordinator = PaperOrderExecutionCoordinator(engine, broker)
    intent = _intent(quantity="1")
    snapshot = PortfolioRiskSnapshot(
        reference_currency="EUR",
        accounts=(
            AccountRiskState(
                account=ACCOUNT,
                currency="EUR",
                equity_reference_day=Decimal("10000"),
                equity_current=Decimal("10000"),
                daily_net_pnl=Decimal("0"),
                confirmed=True,
            ),
        ),
    )
    request = RiskRequest(
        intent_id=intent.intent_id,
        account=ACCOUNT,
        underlying_id="WTI",
        action=RiskAction.OPEN,
        estimated_stop_loss=Decimal("5"),
        anticipated_costs=Decimal("2"),
        scenario_slippage=Decimal("1"),
    )

    outcome = coordinator.execute(intent, request, snapshot)
    duplicate = coordinator.execute(intent, request, snapshot)

    assert outcome.risk_decision.approved is True
    assert outcome.execution_result.status is ExecutionStatus.CONFIRMED
    assert duplicate == outcome
    assert len(broker.positions(ACCOUNT)) == 1
    assert engine.reservations()[0].intent_id == intent.intent_id


def test_coordinator_does_not_submit_when_risk_rejects_stale_price() -> None:
    broker = _broker()
    engine = RiskEngine()
    coordinator = PaperOrderExecutionCoordinator(engine, broker)
    intent = _intent(quantity="1")
    snapshot = PortfolioRiskSnapshot(
        reference_currency="EUR",
        accounts=(
            AccountRiskState(
                account=ACCOUNT,
                currency="EUR",
                equity_reference_day=Decimal("10000"),
                equity_current=Decimal("10000"),
                daily_net_pnl=Decimal("0"),
                confirmed=True,
            ),
        ),
    )
    request = RiskRequest(
        intent_id=intent.intent_id,
        account=ACCOUNT,
        underlying_id="WTI",
        action=RiskAction.OPEN,
        estimated_stop_loss=Decimal("5"),
        price_fresh=False,
    )

    outcome = coordinator.execute(intent, request, snapshot)

    assert outcome.risk_decision.approved is False
    assert outcome.execution_result.status is ExecutionStatus.REJECTED
    assert broker.positions(ACCOUNT) == ()


def test_coordinator_releases_reservation_after_quote_closes_position() -> None:
    broker = _broker()
    engine = RiskEngine()
    coordinator = PaperOrderExecutionCoordinator(engine, broker)
    intent = _intent(quantity="1", target="105")
    snapshot = PortfolioRiskSnapshot(
        reference_currency="EUR",
        accounts=(
            AccountRiskState(
                account=ACCOUNT,
                currency="EUR",
                equity_reference_day=Decimal("10000"),
                equity_current=Decimal("10000"),
                daily_net_pnl=Decimal("0"),
                confirmed=True,
            ),
        ),
    )
    request = RiskRequest(
        intent_id=intent.intent_id,
        account=ACCOUNT,
        underlying_id="WTI",
        action=RiskAction.OPEN,
        estimated_stop_loss=Decimal("5"),
    )
    coordinator.execute(intent, request, snapshot)

    results = coordinator.process_quote(
        _quote("105", "106", observed_at=NOW + timedelta(minutes=1))
    )

    assert results[0].status is ExecutionStatus.CONFIRMED
    assert engine.reservations() == ()
