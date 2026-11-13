"""Immutable market-level scanner read models for GUI V2."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from trading_ig_assistant.app.projections.common import Availability, DataProvenance


@dataclass(frozen=True)
class ScannerSignalVM:
    signal_id: str
    product_epic: str
    strategy_id: str
    side: str
    data_state: str
    entry_low: Decimal | None
    entry_high: Decimal | None
    invalidation: Decimal | None
    target: Decimal | None
    confidence: Decimal | None
    data_quality: Decimal | None
    features: tuple[tuple[str, Decimal | str], ...]
    reason_codes: tuple[str, ...]
    provenance: tuple[str, ...]
    generated_at_utc: datetime
    valid_until_utc: datetime


@dataclass(frozen=True)
class ScannerIndicatorVM:
    indicator_id: str
    name: str
    component: str | None
    state: str
    value: Decimal | None
    required_points: int
    observed_points: int
    parameters: tuple[str, ...]
    reason_codes: tuple[str, ...]
    provenance: tuple[str, ...]


@dataclass(frozen=True)
class ScannerMarketRowVM:
    underlying_id: str
    reference_epic: str
    name: str
    asset_class: str
    bid: Decimal | None
    offer: Decimal | None
    net_change: Decimal | None
    percent_change: Decimal | None
    quote_provenance: DataProvenance
    technical_score: Decimal | None
    context_score: Decimal | None
    signal_direction: str
    recommendation: str
    observed_candles: int
    required_candles: int
    reason_codes: tuple[str, ...]
    evaluated_at_utc: datetime | None
    strategy_signals: tuple[ScannerSignalVM, ...] = ()
    context_level: str | None = None
    context_components: tuple[str, ...] = ()
    context_reason_codes: tuple[str, ...] = ()
    context_provenance: tuple[str, ...] = ()
    context_safety_veto: bool = False
    indicators: tuple[ScannerIndicatorVM, ...] = ()


@dataclass(frozen=True)
class ScannerVM:
    generation_id: int
    rows: tuple[ScannerMarketRowVM, ...]
    availability: Availability
    generated_at_utc: datetime
    paused: bool = False

    def __post_init__(self) -> None:
        if self.generation_id < 0:
            raise ValueError("scanner generation must be non-negative")
        if self.generated_at_utc.tzinfo is None or (
            self.generated_at_utc.utcoffset() != UTC.utcoffset(self.generated_at_utc)
        ):
            raise ValueError("scanner timestamp must use UTC")
        identities = tuple(row.underlying_id for row in self.rows)
        if len(identities) != len(set(identities)):
            raise ValueError("scanner rows must have unique underlying identities")
        if any(
            row.observed_candles < 0 or row.required_candles <= 0 or row.observed_candles > 100_000
            for row in self.rows
        ):
            raise ValueError("scanner candle progress is invalid")
