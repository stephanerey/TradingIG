"""Immutable read models for the V2 Paper dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from trading_ig_assistant.app.projections.common import Amount, Availability, DataProvenance
from trading_ig_assistant.domain.journal import PnlPeriod


@dataclass(frozen=True)
class PositionRowVM:
    generation_id: int
    environment: str
    account_id: str
    execution_mode: str
    position_id: str
    product_id: str
    underlying_id: str
    direction: str
    quantity: Decimal
    entry_price: Amount
    mark_price: Amount
    net_pnl: Amount
    current_stop: Decimal | None
    target: Decimal | None
    knockout: Decimal | None
    status: str
    opened_at_utc: datetime

    def __post_init__(self) -> None:
        required = (
            self.environment,
            self.account_id,
            self.execution_mode,
            self.position_id,
            self.product_id,
            self.underlying_id,
            self.direction,
            self.status,
        )
        if self.generation_id < 0 or any(not value.strip() for value in required):
            raise ValueError("position projection identity is required")
        if self.quantity <= 0:
            raise ValueError("position projection quantity must be positive")
        _require_utc(self.opened_at_utc)


@dataclass(frozen=True)
class RealizedPnlVM:
    period: PnlPeriod
    period_key: str
    amount: Amount
    event_count: int

    def __post_init__(self) -> None:
        if not self.period_key.strip() or self.event_count <= 0:
            raise ValueError("realized PnL projection requires a period and events")


@dataclass(frozen=True)
class DashboardVM:
    generation_id: int
    account_id: str
    execution_mode: str
    generated_at_utc: datetime
    availability: Availability
    equity: Amount | None
    available_funds: Amount | None
    realized_pnl: tuple[RealizedPnlVM, ...]
    open_positions: tuple[PositionRowVM, ...]
    win_rate: Decimal | None = None
    profit_factor: Decimal | None = None
    drawdown: Amount | None = None
    equity_history_available: bool = False
    broker_account_id: str | None = None
    account_balance: Amount | None = None
    account_profit_loss: Amount | None = None
    margin_deposit: Amount | None = None

    def __post_init__(self) -> None:
        if self.generation_id < 0 or not self.account_id.strip():
            raise ValueError("dashboard projection identity is required")
        if self.execution_mode != "PAPER":
            raise ValueError("the initial dashboard projection is PAPER-only")
        _require_utc(self.generated_at_utc)
        if any(row.generation_id != self.generation_id for row in self.open_positions):
            raise ValueError("dashboard positions must share one generation")


def empty_dashboard_projection(
    generation_id: int,
    generated_at_utc: datetime,
) -> DashboardVM:
    return DashboardVM(
        generation_id=generation_id,
        account_id="local-paper-preview",
        execution_mode="PAPER",
        generated_at_utc=generated_at_utc,
        availability=Availability.UNAVAILABLE,
        equity=None,
        available_funds=None,
        realized_pnl=(),
        open_positions=(),
    )


def _require_utc(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("projection timestamp must use UTC")


def unavailable_amount(
    *,
    currency: str,
    source: str,
    scope: str,
    received_at_utc: datetime,
    reason_code: str,
) -> Amount:
    return Amount(
        value=None,
        currency=currency,
        provenance=DataProvenance(
            source=source,
            observed_at_utc=None,
            received_at_utc=received_at_utc,
            scope=scope,
            availability=Availability.STALE,
            reason_codes=(reason_code,),
        ),
        estimate=True,
    )
