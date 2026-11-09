from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from trading_ig_assistant.domain.adapter_contracts import AccountRef, OrderDirection, OrderIntent
from trading_ig_assistant.domain.pending_orders import (
    PendingGate,
    PendingObservation,
    PendingOrderState,
    PendingTriggerType,
    SoftwarePendingOrder,
)
from trading_ig_assistant.domain.risk import (
    RiskDecision,
    RiskDecisionStatus,
    RiskRejectionReason,
)
from trading_ig_assistant.services.pending_order_engine import PendingOrderEngine

NOW = datetime(2026, 10, 22, 12, 0, tzinfo=UTC)
ACCOUNT = AccountRef("paper", "paper", "PAPER-A")


def _intent() -> OrderIntent:
    return OrderIntent(
        intent_id="INTENT-PENDING",
        account=ACCOUNT,
        product_id="WTI-PAPER",
        underlying_id="WTI",
        direction=OrderDirection.BUY,
        quantity=Decimal("1"),
        requested_stop=Decimal("95"),
        requested_target=Decimal("110"),
        requested_ko=Decimal("90"),
        signal_id="SIGNAL-1",
        expires_at_utc=NOW + timedelta(hours=1),
    )


def _order(
    trigger: PendingTriggerType,
    *,
    confirmation: bool = False,
    expires_at: datetime | None = None,
    hold_seconds: int = 0,
) -> SoftwarePendingOrder:
    zone = (Decimal("99"), Decimal("101")) if trigger is PendingTriggerType.TOUCH_ZONE else None
    return SoftwarePendingOrder(
        pending_id="PENDING-1",
        intent=_intent(),
        trigger_type=trigger,
        trigger_level=None if zone else Decimal("100"),
        trigger_zone=zone,
        tolerance=Decimal("0"),
        hold_seconds=hold_seconds,
        expires_at_utc=expires_at or NOW + timedelta(minutes=30),
        confirmation_required=confirmation,
    )


def _observation(
    price: str,
    *,
    at: datetime = NOW + timedelta(minutes=1),
    high: str | None = None,
    low: str | None = None,
    close: str | None = None,
    closed: bool = True,
    fresh: bool = True,
    macro: bool = True,
) -> PendingObservation:
    value = Decimal(price)
    return PendingObservation(
        observed_at_utc=at,
        price=value,
        high=Decimal(high) if high else value,
        low=Decimal(low) if low else value,
        close=Decimal(close) if close else value,
        candle_closed=closed,
        data_fresh=fresh,
        market_open=True,
        product_supported=True,
        macro_allows_entry=macro,
    )


def _gate(approved: bool = True) -> PendingGate:
    return PendingGate(
        RiskDecision(
            status=(RiskDecisionStatus.APPROVED if approved else RiskDecisionStatus.REJECTED),
            reasons=(() if approved else (RiskRejectionReason.DAILY_LOSS_LIMIT,)),
        )
    )


def _armed(order: SoftwarePendingOrder) -> PendingOrderEngine:
    engine = PendingOrderEngine()
    engine.add(order)
    armed = engine.arm(order.pending_id, NOW)
    assert armed.armed_at_utc == NOW
    return engine


def test_closed_candle_rule_ignores_wick_then_triggers_on_close() -> None:
    engine = _armed(_order(PendingTriggerType.CANDLE_CLOSE_ABOVE))

    wick = engine.evaluate(
        "PENDING-1",
        _observation("99", high="105", low="98", close="99"),
        _gate(),
    )
    close = engine.evaluate(
        "PENDING-1",
        _observation("101", high="102", low="99", close="101", at=NOW + timedelta(minutes=2)),
        _gate(),
    )

    assert wick.order.state is PendingOrderState.ARMED
    assert wick.reason_codes == ("CLOSE_CONFIRMATION_MISSING",)
    assert close.order.state is PendingOrderState.TRIGGERED


def test_expired_pending_order_never_triggers() -> None:
    engine = _armed(
        _order(
            PendingTriggerType.CANDLE_CLOSE_ABOVE,
            expires_at=NOW + timedelta(seconds=30),
        )
    )

    result = engine.evaluate(
        "PENDING-1",
        _observation("110", at=NOW + timedelta(minutes=1)),
        _gate(),
    )

    assert result.order.state is PendingOrderState.EXPIRED
    assert result.reason_codes == ("EXPIRED",)


def test_stale_macro_or_risk_gate_keeps_order_armed() -> None:
    engine = _armed(_order(PendingTriggerType.CANDLE_CLOSE_ABOVE))

    stale = engine.evaluate("PENDING-1", _observation("110", fresh=False), _gate())
    macro = engine.evaluate(
        "PENDING-1",
        _observation("110", macro=False, at=NOW + timedelta(minutes=2)),
        _gate(),
    )
    risk = engine.evaluate(
        "PENDING-1",
        _observation("110", at=NOW + timedelta(minutes=3)),
        _gate(False),
    )

    assert stale.reason_codes == ("STALE_DATA",)
    assert macro.reason_codes == ("MACRO_BLOCKED",)
    assert "RISK_REJECTED" in risk.reason_codes
    assert risk.order.state is PendingOrderState.ARMED


def test_spread_and_slippage_are_revalidated_at_trigger_time() -> None:
    order = replace(
        _order(PendingTriggerType.CANDLE_CLOSE_ABOVE),
        max_acceptable_spread=Decimal("1"),
        max_acceptable_slippage=Decimal("0.5"),
    )
    engine = _armed(order)
    observation = replace(
        _observation("110"),
        spread=Decimal("2"),
        estimated_slippage=Decimal("1"),
    )

    result = engine.evaluate("PENDING-1", observation, _gate())

    assert result.order.state is PendingOrderState.ARMED
    assert result.reason_codes == ("SPREAD_LIMIT_EXCEEDED", "SLIPPAGE_LIMIT_EXCEEDED")
    assert result.order.runtime_warning == "APP_MANAGED_PENDING_NOT_PROTECTED_WHEN_STOPPED"


def test_crossing_triggers_exactly_once_under_concurrency() -> None:
    engine = _armed(_order(PendingTriggerType.CROSS_ABOVE, confirmation=True))
    engine.evaluate("PENDING-1", _observation("99"), _gate())
    crossed = _observation("101", at=NOW + timedelta(minutes=2))

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(lambda _index: engine.evaluate("PENDING-1", crossed, _gate()), range(2))
        )

    assert sum(result.transitioned for result in results) == 1
    assert engine.get("PENDING-1").state is PendingOrderState.AWAITING_CONFIRMATION
    triggered_transitions = [
        transition
        for transition in engine.transitions()
        if transition.current_state is PendingOrderState.AWAITING_CONFIRMATION
    ]
    assert len(triggered_transitions) == 1


def test_breakout_requires_configured_hold_time() -> None:
    engine = _armed(_order(PendingTriggerType.BREAKOUT_HOLD_ABOVE, hold_seconds=30))

    first = engine.evaluate("PENDING-1", _observation("101"), _gate())
    second = engine.evaluate(
        "PENDING-1",
        _observation("102", at=NOW + timedelta(seconds=91)),
        _gate(),
    )

    assert first.reason_codes == ("HOLD_IN_PROGRESS",)
    assert second.order.state is PendingOrderState.TRIGGERED


def test_confirmation_precedes_executed_state() -> None:
    engine = _armed(_order(PendingTriggerType.CANDLE_CLOSE_ABOVE, confirmation=True))
    engine.evaluate("PENDING-1", _observation("101"), _gate())

    confirmed = engine.confirm("PENDING-1", NOW + timedelta(minutes=2))
    executed = engine.mark_executed("PENDING-1", NOW + timedelta(minutes=3))

    assert confirmed.state is PendingOrderState.CONFIRMED
    assert executed.state is PendingOrderState.EXECUTED
    assert [transition.current_state for transition in engine.transitions()] == [
        PendingOrderState.ARMED,
        PendingOrderState.AWAITING_CONFIRMATION,
        PendingOrderState.CONFIRMED,
        PendingOrderState.EXECUTED,
    ]
    assert len(engine.journal_events()) == 4
    assert engine.journal_events()[-1].payload["current_state"] == "executed"


def test_replay_observations_cannot_move_backward_in_time() -> None:
    engine = _armed(_order(PendingTriggerType.CROSS_ABOVE))
    engine.evaluate("PENDING-1", _observation("99", at=NOW + timedelta(minutes=2)), _gate())

    with pytest.raises(ValueError, match="backward"):
        engine.evaluate(
            "PENDING-1",
            _observation("101", at=NOW + timedelta(minutes=1)),
            _gate(),
        )
