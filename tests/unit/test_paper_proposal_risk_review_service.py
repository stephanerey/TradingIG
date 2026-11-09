from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from trading_ig_assistant.domain.adapter_contracts import AccountRef, ExecutionStatus
from trading_ig_assistant.domain.analysis import ScannerRecommendation, ScannerResult, SignalSide
from trading_ig_assistant.domain.analysis_directives import (
    AnalysisDirective,
    AnalysisDirectiveStatus,
)
from trading_ig_assistant.domain.positions import PaperFillAssumptions, PaperQuote
from trading_ig_assistant.domain.risk import (
    AccountRiskState,
    ExposureState,
    PortfolioRiskSnapshot,
    RiskDecisionStatus,
    RiskRejectionReason,
)
from trading_ig_assistant.services.analysis_paper_proposal_service import (
    AnalysisPaperProposalService,
)
from trading_ig_assistant.services.order_execution_coordinator import (
    PaperOrderExecutionCoordinator,
)
from trading_ig_assistant.services.paper_broker import PaperBroker
from trading_ig_assistant.services.paper_proposal_execution_service import (
    PaperProposalExecutionError,
    PaperProposalExecutionService,
)
from trading_ig_assistant.services.paper_proposal_risk_review_service import (
    PaperProposalRiskReviewError,
    PaperProposalRiskReviewService,
)
from trading_ig_assistant.services.risk_engine import RiskEngine

NOW = datetime(2026, 11, 5, 19, 0, tzinfo=UTC)
ACCOUNT = AccountRef("paper", "paper", "PAPER-A")


def _proposal():
    directive = AnalysisDirective(
        directive_id="DIRECTIVE-1",
        policy_id="paper-review-v1",
        status=AnalysisDirectiveStatus.READY,
        instrument_id="SYNTHETIC.PRODUCT",
        strategy_id="breakout",
        signal_id="SIGNAL-1",
        side=SignalSide.BUY,
        entry_zone=(Decimal("101"), Decimal("102")),
        invalidation=Decimal("96"),
        target=Decimal("111"),
        generated_at_utc=NOW - timedelta(minutes=1),
        valid_until_utc=NOW + timedelta(minutes=4),
        reason_codes=("ANALYSIS_DIRECTIVE_READY",),
        source_signal_ids=("SIGNAL-1",),
        provenance=("directive:fixture",),
    )
    scanner = ScannerResult(
        instrument_id=directive.instrument_id,
        signal_id=directive.signal_id,
        recommendation=ScannerRecommendation.CANDIDATE,
        ranking_score=Decimal("82.5"),
        components=(),
        reason_codes=("FIXTURE",),
        commentary="Ranking only, not a probability.",
        provenance=("scanner:fixture",),
    )
    return AnalysisPaperProposalService().build(
        proposal_id="PROPOSAL-1",
        intent_id="INTENT-1",
        directive=directive,
        scanner_result=scanner,
        account=ACCOUNT,
        quote=PaperQuote(
            product_id=directive.instrument_id,
            observed_at_utc=NOW - timedelta(seconds=1),
            bid=Decimal("100"),
            ask=Decimal("101"),
            currency="EUR",
            provenance="quote:fixture",
        ),
        underlying_id="US_TECH_100",
        quantity=Decimal("1"),
        knockout=Decimal("90"),
        maximum_ko_loss=Decimal("9"),
        assumptions=PaperFillAssumptions(
            fee_per_unit_per_side=Decimal("0.1"),
            slippage_points_per_side=Decimal("0.5"),
            model_version="risk-review-fixture-v1",
        ),
        created_at_utc=NOW,
    )


def _snapshot(*, equity: Decimal = Decimal("1000")) -> PortfolioRiskSnapshot:
    return PortfolioRiskSnapshot(
        reference_currency="EUR",
        accounts=(
            AccountRiskState(
                account=ACCOUNT,
                currency="EUR",
                equity_reference_day=equity,
                equity_current=equity,
                daily_net_pnl=Decimal("0"),
                confirmed=True,
            ),
        ),
    )


def _review(engine: RiskEngine, *, equity: Decimal = Decimal("1000")):
    return PaperProposalRiskReviewService(engine).review(
        proposal=_proposal(),
        snapshot=_snapshot(equity=equity),
        reviewed_at_utc=NOW + timedelta(seconds=1),
    )


def test_review_exposes_approval_without_reserving_or_executing() -> None:
    engine = RiskEngine()

    review = PaperProposalRiskReviewService(engine).review(
        proposal=_proposal(),
        snapshot=_snapshot(),
        reviewed_at_utc=NOW + timedelta(seconds=1),
    )

    assert review.decision.status is RiskDecisionStatus.APPROVED
    assert review.decision.budget_reference == Decimal("10.00")
    assert engine.reservations() == ()
    assert "RISK_REVIEW_DOES_NOT_RESERVE_OR_EXECUTE" in review.warnings
    assert "EXPLICIT_OPERATOR_ACTION_STILL_REQUIRED" in review.warnings
    assert dict(review.settings_sources)["per_trade_fraction"] == "default"


def test_review_retains_risk_rejection_without_reserving() -> None:
    engine = RiskEngine()

    review = PaperProposalRiskReviewService(engine).review(
        proposal=_proposal(),
        snapshot=_snapshot(equity=Decimal("500")),
        reviewed_at_utc=NOW + timedelta(seconds=1),
    )

    assert review.decision.status is RiskDecisionStatus.REJECTED
    assert RiskRejectionReason.PER_TRADE_LIMIT in review.decision.reasons
    assert RiskRejectionReason.KO_LOSS_LIMIT in review.decision.reasons
    assert engine.reservations() == ()


def test_expired_future_and_non_utc_reviews_are_rejected_before_risk_evaluation() -> None:
    proposal = _proposal()
    service = PaperProposalRiskReviewService(RiskEngine())

    with pytest.raises(PaperProposalRiskReviewError, match="expired"):
        service.review(
            proposal=proposal,
            snapshot=_snapshot(),
            reviewed_at_utc=proposal.ticket.intent.expires_at_utc,
        )
    with pytest.raises(PaperProposalRiskReviewError, match="precede"):
        service.review(
            proposal=proposal,
            snapshot=_snapshot(),
            reviewed_at_utc=proposal.created_at_utc - timedelta(seconds=1),
        )
    with pytest.raises(PaperProposalRiskReviewError, match="UTC"):
        service.review(
            proposal=proposal,
            snapshot=_snapshot(),
            reviewed_at_utc=NOW.astimezone(timezone(timedelta(hours=1))),
        )


def test_non_opening_request_is_rejected() -> None:
    proposal = _proposal()
    invalid_request = replace(proposal.risk_request, action="close")

    with pytest.raises(PaperProposalRiskReviewError, match="opening"):
        PaperProposalRiskReviewService(RiskEngine()).review(
            proposal=replace(proposal, risk_request=invalid_request),
            snapshot=_snapshot(),
            reviewed_at_utc=NOW + timedelta(seconds=1),
        )


def test_explicit_operator_action_rechecks_risk_and_opens_one_local_paper_position() -> None:
    engine = RiskEngine()
    broker = PaperBroker((ACCOUNT,))
    broker.publish_quote(
        PaperQuote(
            product_id="SYNTHETIC.PRODUCT",
            observed_at_utc=NOW + timedelta(seconds=1),
            bid=Decimal("100"),
            ask=Decimal("101"),
            currency="EUR",
            provenance="execution-quote:fixture",
        )
    )
    service = PaperProposalExecutionService(PaperOrderExecutionCoordinator(engine, broker))
    review = _review(engine)

    first = service.execute(
        review=review,
        snapshot=_snapshot(),
        requested_at_utc=NOW + timedelta(seconds=2),
        operator_confirmed=True,
    )
    second = service.execute(
        review=review,
        snapshot=_snapshot(),
        requested_at_utc=NOW + timedelta(seconds=2),
        operator_confirmed=True,
    )

    assert first == second
    assert first.execution_result.status is ExecutionStatus.CONFIRMED
    assert len(broker.positions(ACCOUNT)) == 1
    assert len(engine.reservations()) == 1


def test_missing_operator_confirmation_opens_nothing() -> None:
    engine = RiskEngine()
    broker = PaperBroker((ACCOUNT,))

    with pytest.raises(PaperProposalExecutionError, match="operator confirmation"):
        PaperProposalExecutionService(PaperOrderExecutionCoordinator(engine, broker)).execute(
            review=_review(engine),
            snapshot=_snapshot(),
            requested_at_utc=NOW + timedelta(seconds=2),
            operator_confirmed=False,
        )

    assert broker.positions(ACCOUNT) == ()
    assert engine.reservations() == ()


def test_operator_action_rejects_changed_exposure_before_paper_submission() -> None:
    engine = RiskEngine()
    broker = PaperBroker((ACCOUNT,))
    review = _review(engine)
    occupied = replace(
        _snapshot(),
        open_exposures=(
            ExposureState(
                exposure_id="EXPOSURE-1",
                account=ACCOUNT,
                underlying_id="US_TECH_100",
            ),
        ),
    )

    outcome = PaperProposalExecutionService(PaperOrderExecutionCoordinator(engine, broker)).execute(
        review=review,
        snapshot=occupied,
        requested_at_utc=NOW + timedelta(seconds=2),
        operator_confirmed=True,
    )

    assert outcome.execution_result.status is ExecutionStatus.REJECTED
    assert RiskRejectionReason.GLOBAL_EXPOSURE_LIMIT in outcome.risk_decision.reasons
    assert broker.positions(ACCOUNT) == ()
    assert engine.reservations() == ()


def test_rejected_review_and_expired_action_cannot_execute() -> None:
    engine = RiskEngine()
    service = PaperProposalExecutionService(
        PaperOrderExecutionCoordinator(engine, PaperBroker((ACCOUNT,)))
    )

    with pytest.raises(PaperProposalExecutionError, match="rejected"):
        service.execute(
            review=_review(engine, equity=Decimal("500")),
            snapshot=_snapshot(),
            requested_at_utc=NOW + timedelta(seconds=2),
            operator_confirmed=True,
        )
    with pytest.raises(PaperProposalExecutionError, match="expired"):
        service.execute(
            review=_review(engine),
            snapshot=_snapshot(),
            requested_at_utc=NOW + timedelta(minutes=4),
            operator_confirmed=True,
        )
