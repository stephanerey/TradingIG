"""Structured market-context models independent from providers and Qt."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum


class ContextSeverity(StrEnum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"
    GRAY = "gray"


class MarketRegime(StrEnum):
    RISK_ON = "risk_on"
    NEUTRAL = "neutral"
    RISK_OFF = "risk_off"
    UNKNOWN = "unknown"


class DirectionalBias(StrEnum):
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"
    UNKNOWN = "unknown"


class EventRisk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ContextSignal:
    signal_id: str
    label: str
    severity: ContextSeverity
    score: Decimal | None
    summary: str
    source: str
    source_url: str | None
    observed_at_utc: datetime
    valid_until_utc: datetime | None
    confidence: Decimal | None
    tags: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.signal_id.strip() or not self.label.strip() or not self.source.strip():
            raise ValueError("context signal id, label and source are required")
        for timestamp in (self.observed_at_utc, self.valid_until_utc):
            if timestamp is not None and (
                timestamp.tzinfo is None or timestamp.utcoffset() != UTC.utcoffset(timestamp)
            ):
                raise ValueError("context timestamps must use UTC")
        if self.score is not None and not Decimal("-100") <= self.score <= Decimal("100"):
            raise ValueError("context score must be between -100 and 100")
        if self.confidence is not None and not Decimal("0") <= self.confidence <= Decimal("1"):
            raise ValueError("context confidence must be between 0 and 1")


@dataclass(frozen=True)
class MacroRibbonState:
    schema_version: int
    regime: MarketRegime
    index_bias: DirectionalBias
    gold_bias: DirectionalBias
    event_risk: EventRisk
    signals: tuple[ContextSignal, ...]
    generated_at_utc: datetime
    reason_codes: tuple[str, ...]
    provenance: tuple[str, ...]
