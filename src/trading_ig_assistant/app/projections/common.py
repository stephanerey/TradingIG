"""Shared immutable projection primitives with explicit provenance."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum


class Availability(StrEnum):
    READY = "ready"
    WARMING_UP = "warming_up"
    STALE = "stale"
    DATA_GAP = "data_gap"
    UNAVAILABLE = "unavailable"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class DataProvenance:
    source: str
    observed_at_utc: datetime | None
    received_at_utc: datetime | None
    scope: str
    availability: Availability
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.source.strip() or not self.scope.strip():
            raise ValueError("projection provenance requires source and scope")
        for value in (self.observed_at_utc, self.received_at_utc):
            if value is not None and (
                value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value)
            ):
                raise ValueError("projection timestamps must use UTC")


@dataclass(frozen=True)
class Amount:
    value: Decimal | None
    currency: str
    provenance: DataProvenance
    estimate: bool = False

    def __post_init__(self) -> None:
        if not self.currency.strip():
            raise ValueError("amount currency is required")
        if self.value is not None and not self.value.is_finite():
            raise ValueError("amount value must be finite")
