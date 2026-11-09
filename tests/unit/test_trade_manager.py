from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from trading_ig_assistant.domain.adapter_contracts import (
    AccountRef,
    ExecutionResult,
    ExecutionStatus,
    OrderDirection,
)
from trading_ig_assistant.domain.trade_state import ManagedTrade, StopProposal, TradeState
from trading_ig_assistant.services.trade_manager import TradeManager

NOW = datetime(2026, 10, 22, 12, 0, tzinfo=UTC)
ACCOUNT = AccountRef("paper", "paper", "PAPER-A")


def _trade(direction: OrderDirection = OrderDirection.BUY) -> ManagedTrade:
    stop = Decimal("90") if direction is OrderDirection.BUY else Decimal("110")
    return ManagedTrade(
        position_id="PAPER-1",
        account=ACCOUNT,
        direction=direction,
        entry_price=Decimal("100"),
        initial_stop=stop,
        confirmed_stop=stop,
        quantity=Decimal("2"),
        round_trip_cost_per_unit=Decimal("1"),
        state=TradeState.OPEN,
        opened_at_utc=NOW,
    )


def _execution(status: ExecutionStatus) -> ExecutionResult:
    return ExecutionResult(
        intent_id="INTENT-1",
        account=ACCOUNT,
        status=status,
        broker_reference="PAPER-1",
    )


def test_long_break_even_is_net_of_costs_and_non_guaranteed() -> None:
    recommendation = TradeManager().recommend_break_even(
        _trade(),
        current_price=Decimal("110"),
        generated_at_utc=NOW + timedelta(minutes=1),
    )

    proposal = recommendation.proposal
    assert proposal is not None
    assert proposal.proposed_stop == Decimal("101")
    assert proposal.theoretical_net_pnl == Decimal("0")
    assert proposal.guaranteed is False
    assert "NON_GUARANTEED_GAP_SLIPPAGE" in recommendation.reason_codes


def test_short_break_even_moves_stop_down() -> None:
    recommendation = TradeManager().recommend_break_even(
        _trade(OrderDirection.SELL),
        current_price=Decimal("90"),
        generated_at_utc=NOW + timedelta(minutes=1),
    )

    assert recommendation.proposal is not None
    assert recommendation.proposal.proposed_stop == Decimal("99")


def test_threshold_cooldown_and_minimum_step_are_explicit() -> None:
    manager = TradeManager()
    below = manager.recommend_break_even(
        _trade(),
        current_price=Decimal("109"),
        generated_at_utc=NOW + timedelta(minutes=1),
    )
    confirmed = replace(
        _trade(),
        confirmed_stop=Decimal("101"),
        state=TradeState.PROTECTED,
        last_stop_confirmation_utc=NOW,
    )
    cooldown = manager.recommend_fixed_r_trailing(
        confirmed,
        current_price=Decimal("120"),
        generated_at_utc=NOW + timedelta(seconds=30),
        trigger_r=Decimal("2"),
        lock_r=Decimal("1.1"),
        minimum_step=Decimal("1"),
        cooldown=timedelta(minutes=1),
    )

    assert below.reason_codes == ("THRESHOLD_NOT_REACHED",)
    assert cooldown.reason_codes == ("COOLDOWN_ACTIVE",)


def test_manager_refuses_any_automatic_stop_widening() -> None:
    trade = replace(
        _trade(),
        confirmed_stop=Decimal("105"),
        state=TradeState.TRAILING,
    )

    recommendation = TradeManager().recommend_fixed_r_trailing(
        trade,
        current_price=Decimal("120"),
        generated_at_utc=NOW + timedelta(minutes=1),
        trigger_r=Decimal("2"),
        lock_r=Decimal("0.2"),
    )

    assert recommendation.proposal is None
    assert recommendation.reason_codes == ("STOP_WIDENING_FORBIDDEN",)


def test_manager_does_not_repeat_same_stop_or_regress_trailing_state() -> None:
    manager = TradeManager()
    trade = replace(
        _trade(),
        confirmed_stop=Decimal("101"),
        state=TradeState.TRAILING,
    )
    repeated = manager.recommend_break_even(
        trade,
        current_price=Decimal("115"),
        generated_at_utc=NOW + timedelta(minutes=1),
    )
    manual_regression = StopProposal(
        position_id=trade.position_id,
        old_stop=trade.confirmed_stop,
        proposed_stop=Decimal("102"),
        target_state=TradeState.PROTECTED,
        reason_code="INVALID_REGRESSION",
        theoretical_net_pnl=Decimal("2"),
        generated_at_utc=NOW + timedelta(minutes=1),
    )
    outcome = manager.apply_stop_confirmation(
        trade,
        manual_regression,
        _execution(ExecutionStatus.CONFIRMED),
    )

    assert repeated.reason_codes == ("NO_STOP_IMPROVEMENT",)
    assert outcome.applied is False
    assert outcome.reason_codes == ("TRADE_STATE_REGRESSION_FORBIDDEN",)


def test_trade_advances_only_after_confirmed_stop() -> None:
    manager = TradeManager()
    trade = _trade()
    proposal = manager.recommend_break_even(
        trade,
        current_price=Decimal("110"),
        generated_at_utc=NOW + timedelta(minutes=1),
    ).proposal
    assert proposal is not None

    rejected = manager.apply_stop_confirmation(
        trade,
        proposal,
        _execution(ExecutionStatus.REJECTED),
    )
    confirmed = manager.apply_stop_confirmation(
        trade,
        proposal,
        _execution(ExecutionStatus.CONFIRMED),
    )

    assert rejected.applied is False
    assert rejected.trade.state is TradeState.OPEN
    assert confirmed.applied is True
    assert confirmed.trade.state is TradeState.PROTECTED
    assert confirmed.trade.confirmed_stop == Decimal("101")
    assert [event.event_type for event in manager.events()] == [
        "STOP_RECOMMENDED",
        "STOP_UPDATE_REJECTED",
        "STOP_UPDATE_CONFIRMED",
    ]


def test_confirmation_cannot_apply_a_manually_widened_proposal() -> None:
    trade = _trade()
    proposal = StopProposal(
        position_id=trade.position_id,
        old_stop=trade.confirmed_stop,
        proposed_stop=Decimal("89"),
        target_state=TradeState.PROTECTED,
        reason_code="INVALID_FIXTURE",
        theoretical_net_pnl=Decimal("-24"),
        generated_at_utc=NOW + timedelta(minutes=1),
    )

    outcome = TradeManager().apply_stop_confirmation(
        trade,
        proposal,
        _execution(ExecutionStatus.CONFIRMED),
    )

    assert outcome.applied is False
    assert outcome.reason_codes == ("STOP_WIDENING_FORBIDDEN",)


def test_closed_state_requires_confirmed_close() -> None:
    manager = TradeManager()
    closing = manager.mark_closing(_trade(), NOW + timedelta(minutes=1))

    still_closing = manager.confirm_closed(
        closing,
        _execution(ExecutionStatus.UNKNOWN),
        NOW + timedelta(minutes=2),
    )
    closed = manager.confirm_closed(
        closing,
        _execution(ExecutionStatus.CONFIRMED),
        NOW + timedelta(minutes=3),
    )

    assert still_closing.state is TradeState.CLOSING
    assert closed.state is TradeState.CLOSED
    assert [event.event_type for event in manager.events()] == [
        "TRADE_CLOSING",
        "TRADE_CLOSE_NOT_CONFIRMED",
        "TRADE_CLOSED",
    ]
