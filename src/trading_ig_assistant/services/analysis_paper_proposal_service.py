"""Build a Paper-only ticket/risk handoff from an approved analysis directive."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from trading_ig_assistant.domain.adapter_contracts import (
    AccountRef,
    OrderDirection,
)
from trading_ig_assistant.domain.analysis import (
    ScannerRecommendation,
    ScannerResult,
    SignalSide,
)
from trading_ig_assistant.domain.analysis_directives import (
    AnalysisDirective,
    AnalysisDirectiveStatus,
)
from trading_ig_assistant.domain.paper_proposals import PaperProposalDraft
from trading_ig_assistant.domain.positions import PaperFillAssumptions, PaperQuote
from trading_ig_assistant.services.ticket_builder import TicketBuilder, TicketValidationError


class AnalysisPaperProposalError(ValueError):
    """Raised when advisory evidence cannot safely become a Paper proposal."""


class AnalysisPaperProposalService:
    """Create a draft only; never evaluate risk, reserve exposure or submit an intent."""

    def build(
        self,
        *,
        proposal_id: str,
        intent_id: str,
        directive: AnalysisDirective,
        scanner_result: ScannerResult,
        account: AccountRef,
        quote: PaperQuote,
        underlying_id: str,
        quantity: Decimal,
        knockout: Decimal | None,
        maximum_ko_loss: Decimal | None,
        assumptions: PaperFillAssumptions,
        created_at_utc: datetime,
    ) -> PaperProposalDraft:
        if not proposal_id.strip() or not intent_id.strip():
            raise AnalysisPaperProposalError("paper proposal and intent identities are required")
        if not underlying_id.strip():
            raise AnalysisPaperProposalError("paper proposal underlying identity is required")
        _validate_handoff(
            directive=directive,
            scanner_result=scanner_result,
            quote=quote,
            created_at_utc=created_at_utc,
        )
        assert directive.side is not None
        assert directive.entry_zone is not None
        assert directive.invalidation is not None
        assert directive.target is not None
        direction = {
            SignalSide.BUY: OrderDirection.BUY,
            SignalSide.SELL: OrderDirection.SELL,
        }[directive.side]
        try:
            ticket = TicketBuilder().build(
                intent_id=intent_id,
                account=account,
                quote=quote,
                underlying_id=underlying_id,
                direction=direction,
                quantity=quantity,
                stop=directive.invalidation,
                target=directive.target,
                knockout=knockout,
                expires_at_utc=directive.valid_until_utc,
                assumptions=assumptions,
                signal_id=directive.signal_id,
                scanner_ranking=scanner_result.ranking_score,
                scanner_commentary=scanner_result.commentary,
            )
        except TicketValidationError as exc:
            raise AnalysisPaperProposalError(str(exc)) from exc
        lower_entry, upper_entry = directive.entry_zone
        if not lower_entry <= ticket.entry_price <= upper_entry:
            raise AnalysisPaperProposalError(
                "current Paper entry is outside the directive technical entry zone"
            )
        risk_request = TicketBuilder.risk_request(
            ticket,
            maximum_ko_loss=maximum_ko_loss,
        )
        warnings = tuple(
            dict.fromkeys(
                (
                    *ticket.warnings,
                    "ANALYSIS_DIRECTIVE_ADVISORY_ONLY",
                    "RISK_ENGINE_EVALUATION_REQUIRED",
                    "NO_EXECUTION_ATTEMPTED",
                )
            )
        )
        provenance = tuple(
            dict.fromkeys(
                (
                    f"directive:{directive.directive_id}",
                    f"directive_policy:{directive.policy_id}",
                    f"scanner_signal:{scanner_result.signal_id}",
                    f"scanner_semantics:{scanner_result.score_semantics}",
                    f"quote:{quote.provenance}",
                    f"quote_observed_at:{quote.observed_at_utc.isoformat()}",
                    f"paper_fill_model:{assumptions.model_version}",
                    *directive.provenance,
                    *scanner_result.provenance,
                )
            )
        )
        return PaperProposalDraft(
            proposal_id=proposal_id,
            directive_id=directive.directive_id,
            created_at_utc=created_at_utc,
            ticket=ticket,
            risk_request=risk_request,
            fill_assumptions=assumptions,
            provenance=provenance,
            warnings=warnings,
        )


def _validate_handoff(
    *,
    directive: AnalysisDirective,
    scanner_result: ScannerResult,
    quote: PaperQuote,
    created_at_utc: datetime,
) -> None:
    if created_at_utc.tzinfo is None or created_at_utc.utcoffset() != UTC.utcoffset(created_at_utc):
        raise AnalysisPaperProposalError("paper proposal time must use UTC")
    if directive.status is not AnalysisDirectiveStatus.READY:
        raise AnalysisPaperProposalError("paper proposal requires a READY analysis directive")
    if created_at_utc < directive.generated_at_utc:
        raise AnalysisPaperProposalError("analysis directive is from the future")
    if created_at_utc >= directive.valid_until_utc:
        raise AnalysisPaperProposalError("analysis directive has expired")
    if quote.observed_at_utc > created_at_utc:
        raise AnalysisPaperProposalError("Paper quote is from the future")
    if quote.product_id != directive.instrument_id:
        raise AnalysisPaperProposalError("Paper quote product does not match analysis directive")
    if scanner_result.instrument_id != directive.instrument_id:
        raise AnalysisPaperProposalError("Scanner result instrument does not match directive")
    if scanner_result.signal_id != directive.signal_id:
        raise AnalysisPaperProposalError("Scanner result signal does not match directive")
    if directive.signal_id not in directive.source_signal_ids:
        raise AnalysisPaperProposalError("analysis directive does not cite its strategy signal")
    if scanner_result.recommendation is ScannerRecommendation.NO_TRADE:
        raise AnalysisPaperProposalError("NO_TRADE Scanner result cannot produce a Paper proposal")
    if scanner_result.ranking_score is None:
        raise AnalysisPaperProposalError(
            "unavailable Scanner score cannot produce a Paper proposal"
        )
    if any(component.veto for component in scanner_result.components):
        raise AnalysisPaperProposalError("Scanner component veto blocks the Paper proposal")
