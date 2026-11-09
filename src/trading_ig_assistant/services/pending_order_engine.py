"""Locked, deterministic software pending-order state machine."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from decimal import Decimal
from threading import Lock

from trading_ig_assistant.domain.journal import JournalEvent
from trading_ig_assistant.domain.pending_orders import (
    PendingEvaluation,
    PendingGate,
    PendingObservation,
    PendingOrderState,
    PendingTransition,
    PendingTriggerType,
    SoftwarePendingOrder,
)


class PendingOrderEngine:
    def __init__(self) -> None:
        self._orders: dict[str, SoftwarePendingOrder] = {}
        self._previous_prices: dict[str, Decimal] = {}
        self._last_observed_at: dict[str, datetime] = {}
        self._hold_started: dict[str, datetime] = {}
        self._transitions: list[PendingTransition] = []
        self._journal_events: list[JournalEvent] = []
        self._event_sequence = 0
        self._lock = Lock()

    def add(self, order: SoftwarePendingOrder) -> None:
        if order.state is not PendingOrderState.DRAFT:
            raise ValueError("new software pending order must be DRAFT")
        with self._lock:
            if order.pending_id in self._orders:
                raise ValueError("pending_id already exists")
            self._orders[order.pending_id] = order

    def get(self, pending_id: str) -> SoftwarePendingOrder:
        with self._lock:
            return self._orders[pending_id]

    def transitions(self) -> tuple[PendingTransition, ...]:
        with self._lock:
            return tuple(self._transitions)

    def journal_events(self) -> tuple[JournalEvent, ...]:
        with self._lock:
            return tuple(self._journal_events)

    def arm(self, pending_id: str, timestamp_utc: datetime) -> SoftwarePendingOrder:
        with self._lock:
            order = self._orders[pending_id]
            if order.state is not PendingOrderState.DRAFT:
                raise ValueError("only DRAFT pending orders can be armed")
            if timestamp_utc >= order.expires_at_utc:
                return self._transition(order, PendingOrderState.EXPIRED, timestamp_utc, "EXPIRED")
            armed = replace(order, armed_at_utc=timestamp_utc)
            self._orders[pending_id] = armed
            return self._transition(armed, PendingOrderState.ARMED, timestamp_utc, "ARMED")

    def evaluate(
        self,
        pending_id: str,
        observation: PendingObservation,
        gate: PendingGate,
    ) -> PendingEvaluation:
        with self._lock:
            order = self._orders[pending_id]
            if order.state is not PendingOrderState.ARMED:
                return PendingEvaluation(order, False, ("NOT_ARMED",))
            previous_timestamp = self._last_observed_at.get(pending_id)
            if previous_timestamp is not None and observation.observed_at_utc < previous_timestamp:
                raise ValueError("pending observations cannot move backward in time")
            self._last_observed_at[pending_id] = observation.observed_at_utc
            if observation.observed_at_utc >= order.expires_at_utc:
                expired = self._transition(
                    order,
                    PendingOrderState.EXPIRED,
                    observation.observed_at_utc,
                    "EXPIRED",
                )
                return PendingEvaluation(expired, True, ("EXPIRED",))

            gate_reasons = self._gate_reasons(order, observation, gate)
            previous_price = self._previous_prices.get(pending_id)
            self._previous_prices[pending_id] = observation.price
            if gate_reasons:
                self._hold_started.pop(pending_id, None)
                return PendingEvaluation(order, False, gate_reasons)

            matched, reason = self._matches(order, observation, previous_price)
            if not matched:
                return PendingEvaluation(order, False, (reason,))
            state = (
                PendingOrderState.AWAITING_CONFIRMATION
                if order.confirmation_required
                else PendingOrderState.TRIGGERED
            )
            triggered = self._transition(order, state, observation.observed_at_utc, reason)
            return PendingEvaluation(triggered, True, (reason,))

    def confirm(self, pending_id: str, timestamp_utc: datetime) -> SoftwarePendingOrder:
        with self._lock:
            order = self._orders[pending_id]
            if order.state is not PendingOrderState.AWAITING_CONFIRMATION:
                raise ValueError("only an awaiting pending order can be confirmed")
            return self._transition(
                order,
                PendingOrderState.CONFIRMED,
                timestamp_utc,
                "HUMAN_CONFIRMED",
            )

    def mark_executed(self, pending_id: str, timestamp_utc: datetime) -> SoftwarePendingOrder:
        with self._lock:
            order = self._orders[pending_id]
            if order.state not in {PendingOrderState.TRIGGERED, PendingOrderState.CONFIRMED}:
                raise ValueError("pending order must be triggered or confirmed before execution")
            return self._transition(
                order,
                PendingOrderState.EXECUTED,
                timestamp_utc,
                "PAPER_EXECUTION_CONFIRMED",
            )

    def cancel(self, pending_id: str, timestamp_utc: datetime) -> SoftwarePendingOrder:
        with self._lock:
            order = self._orders[pending_id]
            if order.state in {
                PendingOrderState.EXECUTED,
                PendingOrderState.CANCELLED,
                PendingOrderState.EXPIRED,
                PendingOrderState.FAILED,
            }:
                raise ValueError("terminal pending order cannot be cancelled")
            return self._transition(
                order,
                PendingOrderState.CANCELLED,
                timestamp_utc,
                "CANCELLED",
            )

    @staticmethod
    def _gate_reasons(
        order: SoftwarePendingOrder,
        observation: PendingObservation,
        gate: PendingGate,
    ) -> tuple[str, ...]:
        reasons = list(gate.reason_codes)
        if not observation.data_fresh:
            reasons.append("STALE_DATA")
        if not observation.market_open:
            reasons.append("MARKET_CLOSED")
        if not observation.product_supported:
            reasons.append("PRODUCT_UNSUPPORTED")
        if not observation.macro_allows_entry:
            reasons.append("MACRO_BLOCKED")
        if (
            order.max_acceptable_spread is not None
            and observation.spread > order.max_acceptable_spread
        ):
            reasons.append("SPREAD_LIMIT_EXCEEDED")
        if (
            order.max_acceptable_slippage is not None
            and observation.estimated_slippage > order.max_acceptable_slippage
        ):
            reasons.append("SLIPPAGE_LIMIT_EXCEEDED")
        if not gate.risk_decision.approved:
            reasons.append("RISK_REJECTED")
            reasons.extend(reason.value.upper() for reason in gate.risk_decision.reasons)
        return tuple(dict.fromkeys(reasons))

    def _matches(
        self,
        order: SoftwarePendingOrder,
        observation: PendingObservation,
        previous_price: Decimal | None,
    ) -> tuple[bool, str]:
        level = order.trigger_level
        tolerance = order.tolerance
        trigger = order.trigger_type
        if trigger is PendingTriggerType.TOUCH_ZONE:
            assert order.trigger_zone is not None
            lower, upper = order.trigger_zone
            matched = observation.high >= lower - tolerance and observation.low <= upper + tolerance
            return matched, "ZONE_TOUCHED" if matched else "CONDITION_NOT_MET"
        assert level is not None
        if trigger is PendingTriggerType.CROSS_ABOVE:
            matched = previous_price is not None and previous_price <= level < observation.price
            return matched, "CROSS_ABOVE" if matched else "CONDITION_NOT_MET"
        if trigger is PendingTriggerType.CROSS_BELOW:
            matched = previous_price is not None and previous_price >= level > observation.price
            return matched, "CROSS_BELOW" if matched else "CONDITION_NOT_MET"
        if trigger is PendingTriggerType.CANDLE_CLOSE_ABOVE:
            matched = observation.candle_closed and observation.close > level + tolerance
            return matched, "CANDLE_CLOSE_ABOVE" if matched else "CLOSE_CONFIRMATION_MISSING"
        if trigger is PendingTriggerType.CANDLE_CLOSE_BELOW:
            matched = observation.candle_closed and observation.close < level - tolerance
            return matched, "CANDLE_CLOSE_BELOW" if matched else "CLOSE_CONFIRMATION_MISSING"
        if trigger is PendingTriggerType.PULLBACK_REBOUND:
            touched = observation.low <= level + tolerance and observation.high >= level - tolerance
            matched = touched and observation.rebound_confirmed
            return matched, "PULLBACK_REBOUND" if matched else "REBOUND_CONFIRMATION_MISSING"

        above = observation.price > level + tolerance
        if trigger is PendingTriggerType.BREAKOUT_HOLD_BELOW:
            above = observation.price < level - tolerance
        if not above:
            self._hold_started.pop(order.pending_id, None)
            return False, "HOLD_NOT_STARTED"
        started = self._hold_started.setdefault(order.pending_id, observation.observed_at_utc)
        elapsed = (observation.observed_at_utc - started).total_seconds()
        matched = elapsed >= order.hold_seconds
        return matched, "BREAKOUT_HOLD_CONFIRMED" if matched else "HOLD_IN_PROGRESS"

    def _transition(
        self,
        order: SoftwarePendingOrder,
        state: PendingOrderState,
        timestamp_utc: datetime,
        reason: str,
    ) -> SoftwarePendingOrder:
        if order.last_transition_utc is not None and timestamp_utc < order.last_transition_utc:
            raise ValueError("pending transitions cannot move backward in time")
        updated = replace(order, state=state, last_transition_utc=timestamp_utc)
        self._orders[order.pending_id] = updated
        self._transitions.append(
            PendingTransition(
                pending_id=order.pending_id,
                previous_state=order.state,
                current_state=state,
                timestamp_utc=timestamp_utc,
                reason_code=reason,
            )
        )
        self._event_sequence += 1
        self._journal_events.append(
            JournalEvent(
                event_id=f"PENDING-EVENT-{self._event_sequence}",
                timestamp_utc=timestamp_utc,
                event_type="PENDING_STATE_CHANGED",
                correlation_id=order.pending_id,
                account_ref=(f"{order.intent.account.broker_id}:{order.intent.account.account_id}"),
                instrument_id=order.intent.product_id,
                payload={
                    "previous_state": order.state.value,
                    "current_state": state.value,
                    "reason": reason,
                    "runtime_warning": order.runtime_warning,
                },
            )
        )
        return updated
