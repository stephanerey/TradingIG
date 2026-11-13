"""Governed, non-executable optimization review models for GUI V2."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class OptimizationReviewStatus(StrEnum):
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    READY_FOR_REVIEW = "ready_for_review"


class OptimizationProposalStatus(StrEnum):
    DRAFT = "draft"


@dataclass(frozen=True)
class OptimizationProposalVM:
    """A review artifact only; it deliberately carries no apply command."""

    proposal_id: str
    target_parameter: str
    hypothesis: str
    evidence: tuple[str, ...]
    risk_notes: tuple[str, ...]
    status: OptimizationProposalStatus = OptimizationProposalStatus.DRAFT

    def __post_init__(self) -> None:
        if not all(
            value.strip()
            for value in (self.proposal_id, self.target_parameter, self.hypothesis)
        ):
            raise ValueError("optimization proposal identity is required")
        if not self.evidence or not self.risk_notes:
            raise ValueError("optimization proposal evidence and risks are required")


@dataclass(frozen=True)
class OptimizationReviewVM:
    generation_id: int
    generated_at_utc: datetime
    scope: str
    execution_mode: str
    trade_count: int
    currencies: tuple[str, ...]
    first_trade_at_utc: datetime | None
    last_trade_at_utc: datetime | None
    dataset_version: str | None
    status: OptimizationReviewStatus
    reason_codes: tuple[str, ...]
    external_ai_authorized: bool
    proposals: tuple[OptimizationProposalVM, ...]

    def __post_init__(self) -> None:
        if self.generation_id < 0 or self.trade_count < 0:
            raise ValueError("optimization review generation and count are invalid")
        if not self.scope.strip() or self.execution_mode != "PAPER":
            raise ValueError("optimization review must have an explicit PAPER scope")
        _require_optional_utc(self.first_trade_at_utc)
        _require_optional_utc(self.last_trade_at_utc)
        _require_utc(self.generated_at_utc)
        if self.first_trade_at_utc and self.last_trade_at_utc:
            if self.first_trade_at_utc > self.last_trade_at_utc:
                raise ValueError("optimization review date range is invalid")
        if self.status is OptimizationReviewStatus.INSUFFICIENT_EVIDENCE:
            if not self.reason_codes or self.proposals:
                raise ValueError("insufficient evidence cannot expose proposals")
        if self.external_ai_authorized:
            raise ValueError("GUI V2 does not authorize external AI implicitly")


def empty_optimization_review(
    generation_id: int,
    generated_at_utc: datetime,
) -> OptimizationReviewVM:
    return OptimizationReviewVM(
        generation_id=generation_id,
        generated_at_utc=generated_at_utc,
        scope="paper:local-paper-preview:closed-trades",
        execution_mode="PAPER",
        trade_count=0,
        currencies=(),
        first_trade_at_utc=None,
        last_trade_at_utc=None,
        dataset_version=None,
        status=OptimizationReviewStatus.INSUFFICIENT_EVIDENCE,
        reason_codes=("NO_ATTESTED_CLOSED_TRADES", "DATASET_NOT_VERSIONED"),
        external_ai_authorized=False,
        proposals=(),
    )


def _require_optional_utc(value: datetime | None) -> None:
    if value is not None:
        _require_utc(value)


def _require_utc(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("optimization review timestamp must use UTC")
