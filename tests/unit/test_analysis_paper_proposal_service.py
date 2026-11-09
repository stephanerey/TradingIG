from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from trading_ig_assistant.domain.adapter_contracts import AccountRef, OrderDirection
from trading_ig_assistant.domain.analysis import (
    ScannerRecommendation,
    ScannerResult,
    ScoreComponent,
    ScoreComponentName,
    SignalSide,
)
from trading_ig_assistant.domain.analysis_directives import (
    AnalysisDirective,
    AnalysisDirectiveStatus,
)
from trading_ig_assistant.domain.positions import PaperFillAssumptions, PaperQuote
from trading_ig_assistant.services.analysis_paper_proposal_service import (
    AnalysisPaperProposalError,
    AnalysisPaperProposalService,
)

NOW = datetime(2026, 11, 5, 18, 0, tzinfo=UTC)
ACCOUNT = AccountRef("paper", "paper", "PAPER-A")
ASSUMPTIONS = PaperFillAssumptions(
    fee_per_unit_per_side=Decimal("0.1"),
    slippage_points_per_side=Decimal("0.5"),
    model_version="paper-proposal-fixture-v1",
)


def _directive(side: SignalSide = SignalSide.BUY) -> AnalysisDirective:
    levels = {
        SignalSide.BUY: ((Decimal("101"), Decimal("102")), Decimal("96"), Decimal("111")),
        SignalSide.SELL: ((Decimal("99"), Decimal("100")), Decimal("105"), Decimal("90")),
    }[side]
    return AnalysisDirective(
        directive_id=f"DIRECTIVE:{side.value}",
        policy_id="paper-handoff-v1",
        status=AnalysisDirectiveStatus.READY,
        instrument_id="SYNTHETIC.PRODUCT",
        strategy_id="breakout",
        signal_id=f"SIGNAL:{side.value}",
        side=side,
        entry_zone=levels[0],
        invalidation=levels[1],
        target=levels[2],
        generated_at_utc=NOW - timedelta(minutes=1),
        valid_until_utc=NOW + timedelta(minutes=4),
        reason_codes=("ANALYSIS_DIRECTIVE_READY",),
        source_signal_ids=(f"SIGNAL:{side.value}", "AI:fixture"),
        provenance=("directive:fixture",),
    )


def _scanner(directive: AnalysisDirective) -> ScannerResult:
    return ScannerResult(
        instrument_id=directive.instrument_id,
        signal_id=directive.signal_id,
        recommendation=ScannerRecommendation.CANDIDATE,
        ranking_score=Decimal("82.5"),
        components=(),
        reason_codes=("FIXTURE",),
        commentary="Ranking only, not a probability.",
        provenance=("scanner:fixture",),
    )


def _quote() -> PaperQuote:
    return PaperQuote(
        product_id="SYNTHETIC.PRODUCT",
        observed_at_utc=NOW - timedelta(seconds=1),
        bid=Decimal("100"),
        ask=Decimal("101"),
        currency="EUR",
        provenance="paper-quote-fixture",
    )


def _build(side: SignalSide = SignalSide.BUY):
    directive = _directive(side)
    return AnalysisPaperProposalService().build(
        proposal_id=f"PROPOSAL:{side.value}",
        intent_id=f"INTENT:{side.value}",
        directive=directive,
        scanner_result=_scanner(directive),
        account=ACCOUNT,
        quote=_quote(),
        underlying_id="US_TECH_100",
        quantity=Decimal("1"),
        knockout=Decimal("90") if side is SignalSide.BUY else Decimal("110"),
        maximum_ko_loss=Decimal("9"),
        assumptions=ASSUMPTIONS,
        created_at_utc=NOW,
    )


@pytest.mark.parametrize(
    "side, expected_direction, expected_entry",
    (
        (SignalSide.BUY, OrderDirection.BUY, Decimal("101.5")),
        (SignalSide.SELL, OrderDirection.SELL, Decimal("99.5")),
    ),
)
def test_ready_directive_builds_paper_ticket_and_pending_risk_request_only(
    side: SignalSide,
    expected_direction: OrderDirection,
    expected_entry: Decimal,
) -> None:
    proposal = _build(side)

    assert proposal.ticket.intent.direction is expected_direction
    assert proposal.ticket.entry_price == expected_entry
    assert proposal.ticket.intent.signal_id == f"SIGNAL:{side.value}"
    assert proposal.ticket.intent.expires_at_utc == NOW + timedelta(minutes=4)
    assert proposal.risk_request.intent_id == proposal.ticket.intent.intent_id
    assert proposal.risk_request.maximum_ko_loss == Decimal("9")
    assert proposal.ticket.scanner_ranking == Decimal("82.5")
    assert "RISK_ENGINE_EVALUATION_REQUIRED" in proposal.warnings
    assert "NO_EXECUTION_ATTEMPTED" in proposal.warnings
    assert "directive:fixture" in proposal.provenance
    assert "scanner:fixture" in proposal.provenance


def test_no_trade_or_expired_directive_is_rejected() -> None:
    ready = _directive()
    no_trade = replace(
        ready,
        status=AnalysisDirectiveStatus.NO_TRADE,
        side=None,
        entry_zone=None,
        invalidation=None,
        target=None,
    )
    service = AnalysisPaperProposalService()
    common = dict(
        proposal_id="PROPOSAL",
        intent_id="INTENT",
        scanner_result=_scanner(ready),
        account=ACCOUNT,
        quote=_quote(),
        underlying_id="US_TECH_100",
        quantity=Decimal("1"),
        knockout=Decimal("90"),
        maximum_ko_loss=Decimal("9"),
        assumptions=ASSUMPTIONS,
        created_at_utc=NOW,
    )

    with pytest.raises(AnalysisPaperProposalError, match="READY"):
        service.build(directive=no_trade, **common)
    with pytest.raises(AnalysisPaperProposalError, match="expired"):
        service.build(
            directive=replace(
                ready,
                generated_at_utc=NOW - timedelta(minutes=10),
                valid_until_utc=NOW,
            ),
            **common,
        )


@pytest.mark.parametrize(
    "scanner_change, message",
    (
        ({"signal_id": "OTHER"}, "signal does not match"),
        ({"instrument_id": "OTHER"}, "instrument does not match"),
        (
            {
                "recommendation": ScannerRecommendation.NO_TRADE,
                "ranking_score": Decimal("82.5"),
            },
            "NO_TRADE",
        ),
        ({"ranking_score": None}, "unavailable Scanner score"),
    ),
)
def test_scanner_identity_and_decision_must_match_exactly(
    scanner_change: dict[str, object],
    message: str,
) -> None:
    directive = _directive()
    scanner = replace(_scanner(directive), **scanner_change)

    with pytest.raises(AnalysisPaperProposalError, match=message):
        AnalysisPaperProposalService().build(
            proposal_id="PROPOSAL",
            intent_id="INTENT",
            directive=directive,
            scanner_result=scanner,
            account=ACCOUNT,
            quote=_quote(),
            underlying_id="US_TECH_100",
            quantity=Decimal("1"),
            knockout=Decimal("90"),
            maximum_ko_loss=Decimal("9"),
            assumptions=ASSUMPTIONS,
            created_at_utc=NOW,
        )


def test_component_veto_and_entry_outside_zone_are_rejected() -> None:
    directive = _directive()
    veto = ScoreComponent(
        name=ScoreComponentName.MARKET_RISK,
        score=Decimal("0"),
        weight=Decimal("15"),
        veto=True,
    )
    service = AnalysisPaperProposalService()
    common = dict(
        proposal_id="PROPOSAL",
        intent_id="INTENT",
        directive=directive,
        account=ACCOUNT,
        quote=_quote(),
        underlying_id="US_TECH_100",
        quantity=Decimal("1"),
        knockout=Decimal("90"),
        maximum_ko_loss=Decimal("9"),
        assumptions=ASSUMPTIONS,
        created_at_utc=NOW,
    )

    with pytest.raises(AnalysisPaperProposalError, match="veto"):
        service.build(scanner_result=replace(_scanner(directive), components=(veto,)), **common)
    with pytest.raises(AnalysisPaperProposalError, match="outside"):
        service.build(
            directive=replace(
                directive,
                entry_zone=(Decimal("102"), Decimal("103")),
            ),
            scanner_result=_scanner(directive),
            **{key: value for key, value in common.items() if key != "directive"},
        )


def test_quote_product_future_time_and_non_paper_account_are_rejected() -> None:
    directive = _directive()
    service = AnalysisPaperProposalService()
    common = dict(
        proposal_id="PROPOSAL",
        intent_id="INTENT",
        directive=directive,
        scanner_result=_scanner(directive),
        underlying_id="US_TECH_100",
        quantity=Decimal("1"),
        knockout=Decimal("90"),
        maximum_ko_loss=Decimal("9"),
        assumptions=ASSUMPTIONS,
        created_at_utc=NOW,
    )

    with pytest.raises(AnalysisPaperProposalError, match="does not match"):
        service.build(
            account=ACCOUNT,
            quote=replace(_quote(), product_id="OTHER"),
            **common,
        )
    with pytest.raises(AnalysisPaperProposalError, match="from the future"):
        service.build(
            account=ACCOUNT,
            quote=replace(_quote(), observed_at_utc=NOW + timedelta(seconds=1)),
            **common,
        )
    with pytest.raises(AnalysisPaperProposalError, match="paper"):
        service.build(
            account=AccountRef("ig", "demo", "DEMO-A"),
            quote=_quote(),
            **common,
        )


@pytest.mark.parametrize(
    "identity_change",
    (
        {"proposal_id": ""},
        {"intent_id": " "},
        {"underlying_id": ""},
    ),
)
def test_proposal_intent_and_underlying_identities_are_required(
    identity_change: dict[str, str],
) -> None:
    directive = _directive()
    arguments = dict(
        proposal_id="PROPOSAL",
        intent_id="INTENT",
        directive=directive,
        scanner_result=_scanner(directive),
        account=ACCOUNT,
        quote=_quote(),
        underlying_id="US_TECH_100",
        quantity=Decimal("1"),
        knockout=Decimal("90"),
        maximum_ko_loss=Decimal("9"),
        assumptions=ASSUMPTIONS,
        created_at_utc=NOW,
    )

    with pytest.raises(AnalysisPaperProposalError, match="identit"):
        AnalysisPaperProposalService().build(**(arguments | identity_change))
