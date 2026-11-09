"""Deterministic paper-position models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from trading_ig_assistant.domain.adapter_contracts import AccountRef, OrderDirection


class PaperPositionStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


class PaperExitReason(StrEnum):
    MANUAL = "manual"
    STOP = "stop"
    TARGET = "target"
    KNOCKOUT = "knockout"


@dataclass(frozen=True)
class PaperQuote:
    product_id: str
    observed_at_utc: datetime
    bid: Decimal
    ask: Decimal
    currency: str
    fresh: bool = True
    market_open: bool = True
    product_supported: bool = True
    provenance: str = "paper-fixture"

    def __post_init__(self) -> None:
        if not self.product_id.strip() or not self.currency.strip() or not self.provenance.strip():
            raise ValueError("paper quote product, currency and provenance are required")
        if self.observed_at_utc.tzinfo is None or self.observed_at_utc.utcoffset() != UTC.utcoffset(
            self.observed_at_utc
        ):
            raise ValueError("paper quote timestamp must use UTC")
        if self.bid <= 0 or self.ask <= 0 or self.ask < self.bid:
            raise ValueError("paper quote requires positive bid <= ask")


@dataclass(frozen=True)
class PaperFillAssumptions:
    fee_per_unit_per_side: Decimal = Decimal("0")
    slippage_points_per_side: Decimal = Decimal("0")
    model_version: str = "paper-fill-v1"

    def __post_init__(self) -> None:
        if self.fee_per_unit_per_side < 0 or self.slippage_points_per_side < 0:
            raise ValueError("paper fees and slippage must not be negative")
        if not self.model_version.strip():
            raise ValueError("paper fill model_version is required")


@dataclass(frozen=True)
class PaperPosition:
    position_id: str
    intent_id: str
    account: AccountRef
    product_id: str
    underlying_id: str
    direction: OrderDirection
    quantity: Decimal
    entry_price: Decimal
    current_stop: Decimal | None
    target: Decimal | None
    knockout: Decimal | None
    opened_at_utc: datetime
    opening_fee: Decimal
    entry_slippage: Decimal
    currency: str
    price_provenance: str
    fill_model_version: str
    status: PaperPositionStatus = PaperPositionStatus.OPEN
    closed_at_utc: datetime | None = None
    close_price: Decimal | None = None
    closing_fee: Decimal | None = None
    realized_pnl: Decimal | None = None
    exit_reason: PaperExitReason | None = None

    def __post_init__(self) -> None:
        required = (
            self.position_id,
            self.intent_id,
            self.product_id,
            self.underlying_id,
            self.currency,
            self.price_provenance,
            self.fill_model_version,
        )
        if any(not item.strip() for item in required):
            raise ValueError("paper position identifiers and provenance are required")
        if self.quantity <= 0 or self.entry_price <= 0:
            raise ValueError("paper position quantity and entry must be positive")
        if self.opening_fee < 0 or self.entry_slippage < 0:
            raise ValueError("paper position fee and slippage must not be negative")
        for timestamp in (self.opened_at_utc, self.closed_at_utc):
            if timestamp is not None and (
                timestamp.tzinfo is None or timestamp.utcoffset() != UTC.utcoffset(timestamp)
            ):
                raise ValueError("paper position timestamps must use UTC")
        if self.status is PaperPositionStatus.CLOSED and (
            self.closed_at_utc is None
            or self.close_price is None
            or self.closing_fee is None
            or self.realized_pnl is None
            or self.exit_reason is None
        ):
            raise ValueError("closed paper position requires complete exit details")
        if self.close_price is not None and self.close_price <= 0:
            raise ValueError("paper close price must be positive")
        if self.closing_fee is not None and self.closing_fee < 0:
            raise ValueError("paper closing fee must not be negative")
