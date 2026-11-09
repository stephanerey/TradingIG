"""Explicit operator boundary from an approved review to local Paper execution."""

from __future__ import annotations

from datetime import UTC, datetime

from trading_ig_assistant.domain.paper_proposals import PaperProposalRiskReview
from trading_ig_assistant.domain.risk import PortfolioRiskSnapshot
from trading_ig_assistant.services.order_execution_coordinator import (
    PaperExecutionOutcome,
    PaperOrderExecutionCoordinator,
)


class PaperProposalExecutionError(ValueError):
    """Raised when explicit local Paper execution is not currently authorized."""


class PaperProposalExecutionService:
    """Recheck risk and execute locally only after an explicit operator confirmation."""

    def __init__(self, coordinator: PaperOrderExecutionCoordinator) -> None:
        self._coordinator = coordinator

    def execute(
        self,
        *,
        review: PaperProposalRiskReview,
        snapshot: PortfolioRiskSnapshot,
        requested_at_utc: datetime,
        operator_confirmed: bool,
    ) -> PaperExecutionOutcome:
        if not operator_confirmed:
            raise PaperProposalExecutionError("explicit operator confirmation is required")
        if not review.decision.approved:
            raise PaperProposalExecutionError("rejected risk review cannot be executed")
        if requested_at_utc.tzinfo is None or requested_at_utc.utcoffset() != UTC.utcoffset(
            requested_at_utc
        ):
            raise PaperProposalExecutionError("Paper execution request time must use UTC")
        if requested_at_utc < review.reviewed_at_utc:
            raise PaperProposalExecutionError("Paper execution cannot precede its risk review")
        proposal = review.proposal
        if requested_at_utc >= proposal.ticket.intent.expires_at_utc:
            raise PaperProposalExecutionError("Paper proposal intent has expired")

        return self._coordinator.execute(
            proposal.ticket.intent,
            proposal.risk_request,
            snapshot,
            assumptions=proposal.fill_assumptions,
            settings=review.settings,
        )
