"""Immutable trade-management state and stop proposals."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from trading_ig_assistant.domain.adapter_contracts import (
    AccountRef,
    ExecutionResult,
    OrderDirection,
)


class TradeState(StrEnum):
    OPEN = "open"
    PROTECTED = "protected"
    TRAILING = "trailing"
    CLOSING = "closing"
    CLOSED = "closed"


@dataclass(frozen=True)
class ManagedTrade:
    position_id: str
    account: AccountRef
    direction: OrderDirection
    entry_price: Decimal
    initial_stop: Decimal
    confirmed_stop: Decimal
    quantity: Decimal
    round_trip_cost_per_unit: Decimal
    state: TradeState
    opened_at_utc: datetime
    last_stop_confirmation_utc: datetime | None = None

    def __post_init__(self) -> None:
        if not self.position_id.strip():
            raise ValueError("position_id is required")
        if self.entry_price <= 0 or self.quantity <= 0:
            raise ValueError("entry price and quantity must be positive")
        if self.round_trip_cost_per_unit < 0:
            raise ValueError("round-trip cost must not be negative")
        for timestamp in (self.opened_at_utc, self.last_stop_confirmation_utc):
            if timestamp is not None and (
                timestamp.tzinfo is None or timestamp.utcoffset() != UTC.utcoffset(timestamp)
            ):
                raise ValueError("trade timestamps must use UTC")
        if self.direction is OrderDirection.BUY:
            if self.initial_stop >= self.entry_price or self.confirmed_stop < self.initial_stop:
                raise ValueError("long stops must start below entry and cannot widen")
        elif self.initial_stop <= self.entry_price or self.confirmed_stop > self.initial_stop:
            raise ValueError("short stops must start above entry and cannot widen")

    @property
    def initial_risk_per_unit(self) -> Decimal:
        return abs(self.entry_price - self.initial_stop)


@dataclass(frozen=True)
class StopProposal:
    position_id: str
    old_stop: Decimal
    proposed_stop: Decimal
    target_state: TradeState
    reason_code: str
    theoretical_net_pnl: Decimal
    generated_at_utc: datetime
    guaranteed: bool = False

    def __post_init__(self) -> None:
        if not self.position_id.strip() or not self.reason_code.strip():
            raise ValueError("stop proposal position and reason are required")
        if (
            self.generated_at_utc.tzinfo is None
            or self.generated_at_utc.utcoffset() != UTC.utcoffset(self.generated_at_utc)
        ):
            raise ValueError("stop proposal timestamp must use UTC")
        if self.target_state not in {TradeState.PROTECTED, TradeState.TRAILING}:
            raise ValueError("stop proposal target must be protected or trailing")


@dataclass(frozen=True)
class StopUpdateOutcome:
    trade: ManagedTrade
    proposal: StopProposal
    execution: ExecutionResult
    applied: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class StopRecommendation:
    proposal: StopProposal | None
    reason_codes: tuple[str, ...]
