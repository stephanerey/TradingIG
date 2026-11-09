"""Typed AI market-context contracts independent from model providers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Protocol

from trading_ig_assistant.domain.macro_context import (
    ContextSeverity,
    ContextSignal,
    DirectionalBias,
    EventRisk,
    MacroRibbonState,
)

AI_EVIDENCE_TAG = "ai_evidence"


class AIAnalysisStatus(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class MarketAIAnalysis:
    status: AIAnalysisStatus
    model_id: str
    prompt_version: str
    market_scope: str
    directional_bias: DirectionalBias
    event_risk: EventRisk
    confidence: Decimal | None
    summary: str
    risk_flags: tuple[str, ...]
    source_signal_ids: tuple[str, ...]
    generated_at_utc: datetime
    valid_until_utc: datetime

    def __post_init__(self) -> None:
        required = (self.model_id, self.prompt_version, self.market_scope, self.summary)
        if any(not value.strip() for value in required):
            raise ValueError("AI analysis identity, scope and summary are required")
        _require_utc(self.generated_at_utc, "AI generation")
        _require_utc(self.valid_until_utc, "AI validity")
        if self.valid_until_utc <= self.generated_at_utc:
            raise ValueError("AI analysis validity must follow generation")
        if self.confidence is not None and not Decimal("0") <= self.confidence <= Decimal("1"):
            raise ValueError("AI analysis confidence must be between 0 and 1")
        if len(set(self.risk_flags)) != len(self.risk_flags):
            raise ValueError("AI analysis risk flags must be unique")
        if len(set(self.source_signal_ids)) != len(self.source_signal_ids):
            raise ValueError("AI analysis source signal IDs must be unique")
        if self.status is AIAnalysisStatus.AVAILABLE:
            if self.confidence is None or not self.source_signal_ids:
                raise ValueError("available AI analysis requires confidence and source signals")
        elif (
            self.confidence is not None
            or self.directional_bias is not DirectionalBias.UNKNOWN
            or self.event_risk is not EventRisk.UNKNOWN
            or self.source_signal_ids
        ):
            raise ValueError("unavailable AI analysis must remain unknown and source-free")


@dataclass(frozen=True)
class MarketContextSnapshot:
    schema_version: int
    snapshot_id: str
    instrument_id: str
    macro_state: MacroRibbonState
    ai_analysis: MarketAIAnalysis
    generated_at_utc: datetime
    valid_until_utc: datetime
    reason_codes: tuple[str, ...]
    provenance: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.schema_version <= 0:
            raise ValueError("market context schema version must be positive")
        if not self.snapshot_id.strip() or not self.instrument_id.strip():
            raise ValueError("market context snapshot and instrument IDs are required")
        _require_utc(self.generated_at_utc, "market context generation")
        _require_utc(self.valid_until_utc, "market context validity")
        if self.valid_until_utc <= self.generated_at_utc:
            raise ValueError("market context validity must follow generation")
        if self.macro_state.generated_at_utc > self.generated_at_utc:
            raise ValueError("market context cannot consume a future macro state")
        if self.ai_analysis.market_scope != self.instrument_id:
            raise ValueError("AI analysis scope does not match snapshot instrument")
        if self.ai_analysis.generated_at_utc != self.generated_at_utc:
            raise ValueError("AI analysis and snapshot generation must match")
        if self.valid_until_utc > self.ai_analysis.valid_until_utc:
            raise ValueError("snapshot cannot outlive its AI analysis")


@dataclass(frozen=True)
class MarketAIRequest:
    instrument_id: str
    prompt_version: str
    macro_state: MacroRibbonState
    generated_at_utc: datetime


class MarketAIProvider(Protocol):
    @property
    def model_id(self) -> str:
        """Return a stable provider/model identity."""

    def analyze(self, request: MarketAIRequest) -> Mapping[str, object]:
        """Return JSON-like structured market context."""


def is_ai_citation_eligible(signal: ContextSignal, generated_at_utc: datetime) -> bool:
    """Allow assessed signals or explicitly marked evidence without changing macro aggregates."""

    if signal.observed_at_utc > generated_at_utc:
        return False
    if signal.valid_until_utc is not None and signal.valid_until_utc <= generated_at_utc:
        return False
    tags = {tag.lower() for tag in signal.tags}
    if "data_health" in tags:
        return False
    return signal.severity is not ContextSeverity.GRAY or AI_EVIDENCE_TAG in tags


def _require_utc(value: datetime, label: str) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"{label} timestamp must use UTC")
