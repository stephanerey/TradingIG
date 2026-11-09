"""Evaluate a Paper proposal without reserving exposure or executing it."""

from __future__ import annotations

from datetime import UTC, datetime

from trading_ig_assistant.domain.paper_proposals import (
    PaperProposalDraft,
    PaperProposalRiskReview,
)
from trading_ig_assistant.domain.risk import PortfolioRiskSnapshot, ResolvedRiskSettings, RiskAction
from trading_ig_assistant.services.risk_engine import RiskEngine, resolve_risk_settings


class PaperProposalRiskReviewError(ValueError):
    """Raised when a Paper proposal is not eligible for a current risk review."""


class PaperProposalRiskReviewService:
    """Call only the non-reserving Risk Engine evaluation boundary."""

    def __init__(self, risk_engine: RiskEngine) -> None:
        self._risk_engine = risk_engine

    def review(
        self,
        *,
        proposal: PaperProposalDraft,
        snapshot: PortfolioRiskSnapshot,
        reviewed_at_utc: datetime,
        settings: ResolvedRiskSettings | None = None,
    ) -> PaperProposalRiskReview:
        if reviewed_at_utc.tzinfo is None or reviewed_at_utc.utcoffset() != UTC.utcoffset(
            reviewed_at_utc
        ):
            raise PaperProposalRiskReviewError("paper proposal risk-review time must use UTC")
        if reviewed_at_utc < proposal.created_at_utc:
            raise PaperProposalRiskReviewError("paper proposal risk review cannot precede creation")
        if reviewed_at_utc >= proposal.ticket.intent.expires_at_utc:
            raise PaperProposalRiskReviewError("paper proposal intent has expired")
        if proposal.risk_request.action is not RiskAction.OPEN:
            raise PaperProposalRiskReviewError("paper proposal risk request must be an opening")

        resolved_settings = settings or resolve_risk_settings()
        decision = self._risk_engine.evaluate(
            proposal.risk_request,
            snapshot,
            resolved_settings,
        )
        warnings = tuple(
            dict.fromkeys(
                (
                    *proposal.warnings,
                    "RISK_REVIEW_DOES_NOT_RESERVE_OR_EXECUTE",
                    "EXPLICIT_OPERATOR_ACTION_STILL_REQUIRED",
                )
            )
        )
        return PaperProposalRiskReview(
            proposal=proposal,
            reviewed_at_utc=reviewed_at_utc,
            decision=decision,
            settings=resolved_settings,
            warnings=warnings,
        )
