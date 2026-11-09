"""Append-only journal and deterministic P&L domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any


class PnlStatus(StrEnum):
    REALIZED = "realized"
    UNREALIZED = "unrealized"
    ESTIMATED = "estimated"
    UNKNOWN = "unknown"


class PnlPeriod(StrEnum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


@dataclass(frozen=True)
class JournalEvent:
    event_id: str
    timestamp_utc: datetime
    event_type: str
    correlation_id: str
    account_ref: str
    instrument_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict, repr=False)
    pnl_amount: Decimal | None = None
    pnl_currency: str | None = None
    pnl_status: PnlStatus = PnlStatus.UNKNOWN

    def __post_init__(self) -> None:
        required = {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "correlation_id": self.correlation_id,
            "account_ref": self.account_ref,
        }
        missing = [name for name, value in required.items() if not value.strip()]
        if missing:
            raise ValueError(f"Journal fields are required: {', '.join(missing)}")
        if self.timestamp_utc.tzinfo is None:
            raise ValueError("timestamp_utc must be timezone-aware")
        if self.timestamp_utc.utcoffset() != UTC.utcoffset(self.timestamp_utc):
            raise ValueError("timestamp_utc must use UTC")
        if not isinstance(self.payload, dict):
            raise ValueError("payload must be a JSON object")
        if (self.pnl_amount is None) != (self.pnl_currency is None):
            raise ValueError("pnl_amount and pnl_currency must be provided together")
        if self.pnl_currency is not None and not self.pnl_currency.strip():
            raise ValueError("pnl_currency must not be blank")
        if self.pnl_status == PnlStatus.REALIZED and self.pnl_amount is None:
            raise ValueError("realized P&L requires an amount and currency")

    def timestamp_text(self) -> str:
        return self.timestamp_utc.isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class PnlTotal:
    period: PnlPeriod
    period_key: str
    currency: str
    amount: Decimal
    event_count: int
