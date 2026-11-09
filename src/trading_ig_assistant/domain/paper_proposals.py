"""Paper-only proposal envelope awaiting an independent risk decision."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from trading_ig_assistant.domain.positions import PaperFillAssumptions
from trading_ig_assistant.domain.risk import (
    ResolvedRiskSettings,
    RiskDecision,
    RiskRequest,
)
from trading_ig_assistant.domain.tickets import TicketDraft


@dataclass(frozen=True)
class PaperProposalDraft:
    proposal_id: str
    directive_id: str
    created_at_utc: datetime
    ticket: TicketDraft
    risk_request: RiskRequest
    fill_assumptions: PaperFillAssumptions
    provenance: tuple[str, ...]
    warnings: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.proposal_id.strip() or not self.directive_id.strip():
            raise ValueError("paper proposal identity fields are required")
        if self.created_at_utc.tzinfo is None or self.created_at_utc.utcoffset() != UTC.utcoffset(
            self.created_at_utc
        ):
            raise ValueError("paper proposal timestamp must use UTC")
        if self.ticket.intent.intent_id != self.risk_request.intent_id:
            raise ValueError("paper proposal ticket and risk request intent must match")
        if self.ticket.intent.account != self.risk_request.account:
            raise ValueError("paper proposal ticket and risk request account must match")
        if self.ticket.intent.underlying_id != self.risk_request.underlying_id:
            raise ValueError("paper proposal ticket and risk request underlying must match")
        if self.ticket.intent.account.broker_id != "paper":
            raise ValueError("paper proposal requires a paper account")
        if not self.provenance:
            raise ValueError("paper proposal provenance is required")
        required_warnings = {"PAPER_SIMULATION_ONLY", "RISK_ENGINE_EVALUATION_REQUIRED"}
        if not required_warnings.issubset(self.warnings):
            raise ValueError("paper proposal safety warnings are incomplete")


@dataclass(frozen=True)
class PaperProposalRiskReview:
    """Immutable risk review which grants no reservation or execution authority."""

    proposal: PaperProposalDraft
    reviewed_at_utc: datetime
    decision: RiskDecision
    settings: ResolvedRiskSettings
    warnings: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.reviewed_at_utc.tzinfo is None or self.reviewed_at_utc.utcoffset() != UTC.utcoffset(
            self.reviewed_at_utc
        ):
            raise ValueError("paper proposal risk-review timestamp must use UTC")
        required_warnings = {
            "PAPER_SIMULATION_ONLY",
            "RISK_REVIEW_DOES_NOT_RESERVE_OR_EXECUTE",
        }
        if not required_warnings.issubset(self.warnings):
            raise ValueError("paper proposal risk-review warnings are incomplete")

    @property
    def settings_sources(self) -> tuple[tuple[str, str], ...]:
        return self.settings.sources
