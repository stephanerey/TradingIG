"""Software pending-order models with explicit trigger semantics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from trading_ig_assistant.domain.adapter_contracts import OrderIntent
from trading_ig_assistant.domain.risk import RiskDecision


class PendingOrderState(StrEnum):
    DRAFT = "draft"
    ARMED = "armed"
    TRIGGERED = "triggered"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    CONFIRMED = "confirmed"
    EXECUTED = "executed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    FAILED = "failed"


class PendingTriggerType(StrEnum):
    CROSS_ABOVE = "cross_above"
    CROSS_BELOW = "cross_below"
    TOUCH_ZONE = "touch_zone"
    BREAKOUT_HOLD_ABOVE = "breakout_hold_above"
    BREAKOUT_HOLD_BELOW = "breakout_hold_below"
    CANDLE_CLOSE_ABOVE = "candle_close_above"
    CANDLE_CLOSE_BELOW = "candle_close_below"
    PULLBACK_REBOUND = "pullback_rebound"


@dataclass(frozen=True)
class SoftwarePendingOrder:
    pending_id: str
    intent: OrderIntent
    trigger_type: PendingTriggerType
    trigger_level: Decimal | None
    trigger_zone: tuple[Decimal, Decimal] | None
    tolerance: Decimal
    hold_seconds: int
    expires_at_utc: datetime
    confirmation_required: bool
    max_acceptable_spread: Decimal | None = None
    max_acceptable_slippage: Decimal | None = None
    state: PendingOrderState = PendingOrderState.DRAFT
    armed_at_utc: datetime | None = None
    last_transition_utc: datetime | None = None

    def __post_init__(self) -> None:
        if not self.pending_id.strip():
            raise ValueError("pending_id is required")
        for timestamp in (
            self.expires_at_utc,
            self.armed_at_utc,
            self.last_transition_utc,
        ):
            if timestamp is not None and (
                timestamp.tzinfo is None or timestamp.utcoffset() != UTC.utcoffset(timestamp)
            ):
                raise ValueError("pending timestamps must use UTC")
        if self.tolerance < 0 or self.hold_seconds < 0:
            raise ValueError("pending tolerance and hold time must not be negative")
        if any(
            value is not None and value < 0
            for value in (self.max_acceptable_spread, self.max_acceptable_slippage)
        ):
            raise ValueError("pending spread and slippage limits must not be negative")
        if self.trigger_zone is not None and self.trigger_zone[0] > self.trigger_zone[1]:
            raise ValueError("pending trigger zone bounds are reversed")
        if self.trigger_type is PendingTriggerType.TOUCH_ZONE and self.trigger_zone is None:
            raise ValueError("touch-zone trigger requires a zone")
        if self.trigger_type is not PendingTriggerType.TOUCH_ZONE and self.trigger_level is None:
            raise ValueError("pending trigger requires a level")
        if self.expires_at_utc > self.intent.expires_at_utc:
            raise ValueError("pending expiry cannot exceed its immutable intent expiry")

    @property
    def runtime_warning(self) -> str:
        return "APP_MANAGED_PENDING_NOT_PROTECTED_WHEN_STOPPED"


@dataclass(frozen=True)
class PendingObservation:
    observed_at_utc: datetime
    price: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    candle_closed: bool
    data_fresh: bool
    market_open: bool
    product_supported: bool
    macro_allows_entry: bool
    rebound_confirmed: bool = False
    spread: Decimal = Decimal("0")
    estimated_slippage: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if self.observed_at_utc.tzinfo is None or self.observed_at_utc.utcoffset() != UTC.utcoffset(
            self.observed_at_utc
        ):
            raise ValueError("pending observation timestamp must use UTC")
        if min(self.price, self.high, self.low, self.close) <= 0:
            raise ValueError("pending observation prices must be positive")
        if self.spread < 0 or self.estimated_slippage < 0:
            raise ValueError("pending observed spread and slippage must not be negative")
        if self.high < max(self.price, self.close) or self.low > min(self.price, self.close):
            raise ValueError("pending observation OHLC range is invalid")


@dataclass(frozen=True)
class PendingGate:
    risk_decision: RiskDecision
    reason_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class PendingEvaluation:
    order: SoftwarePendingOrder
    transitioned: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class PendingTransition:
    pending_id: str
    previous_state: PendingOrderState
    current_state: PendingOrderState
    timestamp_utc: datetime
    reason_code: str
