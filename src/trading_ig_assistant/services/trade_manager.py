"""Deterministic R-based paper trade manager."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal
from threading import Lock

from trading_ig_assistant.domain.adapter_contracts import (
    ExecutionResult,
    ExecutionStatus,
    OrderDirection,
)
from trading_ig_assistant.domain.journal import JournalEvent
from trading_ig_assistant.domain.trade_state import (
    ManagedTrade,
    StopProposal,
    StopRecommendation,
    StopUpdateOutcome,
    TradeState,
)


class TradeManager:
    def __init__(self) -> None:
        self._events: list[JournalEvent] = []
        self._event_sequence = 0
        self._event_lock = Lock()

    def events(self) -> tuple[JournalEvent, ...]:
        with self._event_lock:
            return tuple(self._events)

    def recommend_break_even(
        self,
        trade: ManagedTrade,
        *,
        current_price: Decimal,
        generated_at_utc: datetime,
        threshold_r: Decimal = Decimal("1"),
        cushion: Decimal = Decimal("0"),
        minimum_step: Decimal = Decimal("0"),
        cooldown: timedelta = timedelta(0),
    ) -> StopRecommendation:
        if threshold_r < 0 or cushion < 0:
            raise ValueError("break-even threshold and cushion must not be negative")
        favorable = self._favorable_move(trade, current_price)
        if favorable < trade.initial_risk_per_unit * threshold_r:
            return StopRecommendation(None, ("THRESHOLD_NOT_REACHED",))
        costs = trade.round_trip_cost_per_unit
        candidate = trade.entry_price + costs + cushion
        if trade.direction is OrderDirection.SELL:
            candidate = trade.entry_price - costs - cushion
        return self._recommend(
            trade,
            candidate,
            TradeState.PROTECTED,
            "BREAK_EVEN_NET_PLUS_CUSHION",
            generated_at_utc,
            minimum_step,
            cooldown,
        )

    def recommend_fixed_r_trailing(
        self,
        trade: ManagedTrade,
        *,
        current_price: Decimal,
        generated_at_utc: datetime,
        trigger_r: Decimal,
        lock_r: Decimal,
        minimum_step: Decimal = Decimal("0"),
        cooldown: timedelta = timedelta(0),
    ) -> StopRecommendation:
        if trigger_r < 0 or lock_r < 0 or lock_r > trigger_r:
            raise ValueError("trailing R values must satisfy 0 <= lock_r <= trigger_r")
        favorable = self._favorable_move(trade, current_price)
        if favorable < trade.initial_risk_per_unit * trigger_r:
            return StopRecommendation(None, ("TRAIL_THRESHOLD_NOT_REACHED",))
        candidate = trade.entry_price + (trade.initial_risk_per_unit * lock_r)
        if trade.direction is OrderDirection.SELL:
            candidate = trade.entry_price - (trade.initial_risk_per_unit * lock_r)
        return self._recommend(
            trade,
            candidate,
            TradeState.TRAILING,
            "FIXED_R_TRAILING",
            generated_at_utc,
            minimum_step,
            cooldown,
        )

    def apply_stop_confirmation(
        self,
        trade: ManagedTrade,
        proposal: StopProposal,
        execution: ExecutionResult,
    ) -> StopUpdateOutcome:
        if proposal.position_id != trade.position_id:
            raise ValueError("stop proposal does not target this trade")
        if execution.account != trade.account:
            raise ValueError("stop confirmation account mismatch")
        if execution.status is not ExecutionStatus.CONFIRMED:
            outcome = StopUpdateOutcome(
                trade=trade,
                proposal=proposal,
                execution=execution,
                applied=False,
                reason_codes=("STOP_NOT_CONFIRMED",),
            )
            self._record(trade, proposal, "STOP_UPDATE_REJECTED", False, "STOP_NOT_CONFIRMED")
            return outcome
        if trade.state is TradeState.TRAILING and proposal.target_state is TradeState.PROTECTED:
            outcome = StopUpdateOutcome(
                trade=trade,
                proposal=proposal,
                execution=execution,
                applied=False,
                reason_codes=("TRADE_STATE_REGRESSION_FORBIDDEN",),
            )
            self._record(
                trade,
                proposal,
                "STOP_UPDATE_REJECTED",
                False,
                "TRADE_STATE_REGRESSION_FORBIDDEN",
            )
            return outcome
        if self._would_widen(trade, proposal.proposed_stop):
            outcome = StopUpdateOutcome(
                trade=trade,
                proposal=proposal,
                execution=execution,
                applied=False,
                reason_codes=("STOP_WIDENING_FORBIDDEN",),
            )
            self._record(
                trade,
                proposal,
                "STOP_UPDATE_REJECTED",
                False,
                "STOP_WIDENING_FORBIDDEN",
            )
            return outcome
        updated = replace(
            trade,
            confirmed_stop=proposal.proposed_stop,
            state=proposal.target_state,
            last_stop_confirmation_utc=proposal.generated_at_utc,
        )
        outcome = StopUpdateOutcome(
            trade=updated,
            proposal=proposal,
            execution=execution,
            applied=True,
            reason_codes=("STOP_CONFIRMED", "NON_GUARANTEED_GAP_SLIPPAGE"),
        )
        self._record(trade, proposal, "STOP_UPDATE_CONFIRMED", True, "STOP_CONFIRMED")
        return outcome

    def mark_closing(self, trade: ManagedTrade, timestamp_utc: datetime) -> ManagedTrade:
        if trade.state is TradeState.CLOSED:
            raise ValueError("closed trade cannot return to closing")
        updated = replace(trade, state=TradeState.CLOSING)
        self._record_state(trade, timestamp_utc, "TRADE_CLOSING", True)
        return updated

    def confirm_closed(
        self,
        trade: ManagedTrade,
        execution: ExecutionResult,
        timestamp_utc: datetime,
    ) -> ManagedTrade:
        if trade.state is not TradeState.CLOSING:
            raise ValueError("trade must be closing before closed")
        if execution.status is not ExecutionStatus.CONFIRMED:
            self._record_state(trade, timestamp_utc, "TRADE_CLOSE_NOT_CONFIRMED", False)
            return trade
        updated = replace(trade, state=TradeState.CLOSED)
        self._record_state(trade, timestamp_utc, "TRADE_CLOSED", True)
        return updated

    def _recommend(
        self,
        trade: ManagedTrade,
        candidate: Decimal,
        target_state: TradeState,
        reason: str,
        generated_at_utc: datetime,
        minimum_step: Decimal,
        cooldown: timedelta,
    ) -> StopRecommendation:
        if minimum_step < 0 or cooldown < timedelta(0):
            raise ValueError("minimum step and cooldown must not be negative")
        if generated_at_utc < trade.opened_at_utc:
            raise ValueError("stop recommendation cannot precede trade opening")
        if trade.state in {TradeState.CLOSING, TradeState.CLOSED}:
            return StopRecommendation(None, ("TRADE_NOT_MANAGEABLE",))
        if self._would_widen(trade, candidate):
            return StopRecommendation(None, ("STOP_WIDENING_FORBIDDEN",))
        improvement = abs(candidate - trade.confirmed_stop)
        if improvement == 0:
            return StopRecommendation(None, ("NO_STOP_IMPROVEMENT",))
        if improvement < minimum_step:
            return StopRecommendation(None, ("MINIMUM_STEP_NOT_REACHED",))
        if (
            trade.last_stop_confirmation_utc is not None
            and generated_at_utc - trade.last_stop_confirmation_utc < cooldown
        ):
            return StopRecommendation(None, ("COOLDOWN_ACTIVE",))
        if trade.state is TradeState.TRAILING and target_state is TradeState.PROTECTED:
            target_state = TradeState.TRAILING
        theoretical = self._net_pnl_at_stop(trade, candidate)
        proposal = StopProposal(
            position_id=trade.position_id,
            old_stop=trade.confirmed_stop,
            proposed_stop=candidate,
            target_state=target_state,
            reason_code=reason,
            theoretical_net_pnl=theoretical,
            generated_at_utc=generated_at_utc,
            guaranteed=False,
        )
        self._record(trade, proposal, "STOP_RECOMMENDED", False, reason)
        return StopRecommendation(proposal, (reason, "NON_GUARANTEED_GAP_SLIPPAGE"))

    def _record(
        self,
        trade: ManagedTrade,
        proposal: StopProposal,
        event_type: str,
        applied: bool,
        reason: str,
    ) -> None:
        with self._event_lock:
            self._event_sequence += 1
            self._events.append(
                JournalEvent(
                    event_id=f"TRADE-MANAGER-{self._event_sequence}",
                    timestamp_utc=proposal.generated_at_utc,
                    event_type=event_type,
                    correlation_id=trade.position_id,
                    account_ref=f"{trade.account.broker_id}:{trade.account.account_id}",
                    instrument_id=trade.position_id,
                    payload={
                        "old_stop": str(proposal.old_stop),
                        "proposed_stop": str(proposal.proposed_stop),
                        "theoretical_net_pnl": str(proposal.theoretical_net_pnl),
                        "target_state": proposal.target_state.value,
                        "reason": reason,
                        "applied": applied,
                        "guaranteed": proposal.guaranteed,
                    },
                )
            )

    def _record_state(
        self,
        trade: ManagedTrade,
        timestamp_utc: datetime,
        event_type: str,
        applied: bool,
    ) -> None:
        with self._event_lock:
            self._event_sequence += 1
            self._events.append(
                JournalEvent(
                    event_id=f"TRADE-MANAGER-{self._event_sequence}",
                    timestamp_utc=timestamp_utc,
                    event_type=event_type,
                    correlation_id=trade.position_id,
                    account_ref=f"{trade.account.broker_id}:{trade.account.account_id}",
                    instrument_id=trade.position_id,
                    payload={
                        "previous_state": trade.state.value,
                        "applied": applied,
                    },
                )
            )

    @staticmethod
    def _favorable_move(trade: ManagedTrade, current_price: Decimal) -> Decimal:
        if trade.direction is OrderDirection.BUY:
            return current_price - trade.entry_price
        return trade.entry_price - current_price

    @staticmethod
    def _would_widen(trade: ManagedTrade, stop: Decimal) -> bool:
        if trade.direction is OrderDirection.BUY:
            return stop < trade.confirmed_stop
        return stop > trade.confirmed_stop

    @staticmethod
    def _net_pnl_at_stop(trade: ManagedTrade, stop: Decimal) -> Decimal:
        price_pnl = stop - trade.entry_price
        if trade.direction is OrderDirection.SELL:
            price_pnl = -price_pnl
        return (price_pnl - trade.round_trip_cost_per_unit) * trade.quantity
