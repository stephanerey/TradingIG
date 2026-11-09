"""Advisory analysis directives that are deliberately not broker order intents."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from trading_ig_assistant.domain.analysis import (
    ConsensusStatus,
    ScannerRecommendation,
    SignalSide,
)
from trading_ig_assistant.domain.macro_context import EventRisk


class AnalysisDirectiveStatus(StrEnum):
    READY = "ready"
    NO_TRADE = "no_trade"


@dataclass(frozen=True)
class AnalysisDirectivePolicy:
    policy_id: str
    allowed_recommendations: tuple[ScannerRecommendation, ...]
    allowed_consensus_statuses: tuple[ConsensusStatus, ...]
    require_ai_alignment: bool
    minimum_ai_confidence: Decimal | None
    blocked_ai_event_risks: tuple[EventRisk, ...]

    def __post_init__(self) -> None:
        if not self.policy_id.strip():
            raise ValueError("analysis directive policy ID is required")
        for label, values in (
            ("recommendation", self.allowed_recommendations),
            ("consensus", self.allowed_consensus_statuses),
            ("event-risk", self.blocked_ai_event_risks),
        ):
            if len(set(values)) != len(values):
                raise ValueError(f"analysis directive {label} policy contains duplicates")
        if not self.allowed_recommendations or not self.allowed_consensus_statuses:
            raise ValueError("analysis directive policy must allow an explicit decision set")
        if self.minimum_ai_confidence is not None and not (
            Decimal("0") <= self.minimum_ai_confidence <= Decimal("1")
        ):
            raise ValueError("analysis directive minimum AI confidence must be between 0 and 1")
        if self.minimum_ai_confidence is not None and not self.require_ai_alignment:
            raise ValueError("AI confidence cannot be required when AI alignment is disabled")


@dataclass(frozen=True)
class AnalysisDirective:
    directive_id: str
    policy_id: str
    status: AnalysisDirectiveStatus
    instrument_id: str
    strategy_id: str
    signal_id: str
    side: SignalSide | None
    entry_zone: tuple[Decimal, Decimal] | None
    invalidation: Decimal | None
    target: Decimal | None
    generated_at_utc: datetime
    valid_until_utc: datetime
    reason_codes: tuple[str, ...]
    source_signal_ids: tuple[str, ...]
    provenance: tuple[str, ...]

    def __post_init__(self) -> None:
        required = (self.directive_id, self.policy_id, self.instrument_id, self.strategy_id)
        if any(not value.strip() for value in required):
            raise ValueError("analysis directive identity fields are required")
        for value in (self.generated_at_utc, self.valid_until_utc):
            if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
                raise ValueError("analysis directive timestamps must use UTC")
        if self.valid_until_utc < self.generated_at_utc:
            raise ValueError("analysis directive validity cannot precede generation")
        if self.status is AnalysisDirectiveStatus.READY:
            if self.side not in {SignalSide.BUY, SignalSide.SELL}:
                raise ValueError("ready analysis directive requires a directional side")
            if self.entry_zone is None or self.invalidation is None or self.target is None:
                raise ValueError("ready analysis directive requires explicit technical levels")
        elif any(
            value is not None
            for value in (self.side, self.entry_zone, self.invalidation, self.target)
        ):
            raise ValueError("no-trade analysis directive cannot expose actionable levels")
        if len(set(self.source_signal_ids)) != len(self.source_signal_ids):
            raise ValueError("analysis directive source signal IDs must be unique")
