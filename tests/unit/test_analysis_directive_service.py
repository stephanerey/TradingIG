from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from trading_ig_assistant.domain.ai_context import AIAnalysisStatus, MarketAIAnalysis
from trading_ig_assistant.domain.analysis import (
    ConsensusStatus,
    DataState,
    ScannerRecommendation,
    ScannerResult,
    SignalSide,
    StrategyConsensus,
    StrategySignal,
)
from trading_ig_assistant.domain.analysis_directives import (
    AnalysisDirectivePolicy,
    AnalysisDirectiveStatus,
)
from trading_ig_assistant.domain.macro_context import DirectionalBias, EventRisk
from trading_ig_assistant.services.analysis_directive_service import AnalysisDirectiveService

NOW = datetime(2026, 11, 5, 16, 0, tzinfo=UTC)


def _policy() -> AnalysisDirectivePolicy:
    return AnalysisDirectivePolicy(
        policy_id="strict-analysis-v1",
        allowed_recommendations=(ScannerRecommendation.CANDIDATE,),
        allowed_consensus_statuses=(ConsensusStatus.ALIGNED, ConsensusStatus.SINGLE),
        require_ai_alignment=True,
        minimum_ai_confidence=Decimal("0.60"),
        blocked_ai_event_risks=(EventRisk.HIGH, EventRisk.UNKNOWN),
    )


def _signal(side: SignalSide = SignalSide.BUY) -> StrategySignal:
    return StrategySignal(
        signal_id="SIGNAL-1",
        strategy_id="breakout",
        strategy_version="v1",
        instrument_id="IX.D.NASDAQ.IFD.IP",
        side=side,
        generated_at_utc=NOW - timedelta(minutes=1),
        valid_until_utc=NOW + timedelta(minutes=4),
        data_state=DataState.READY,
        reason_codes=("BREAKOUT_CONFIRMED",),
        features=(),
        provenance=("timeframe:M1",),
        entry_zone=(Decimal("100"), Decimal("101")),
        invalidation=Decimal("98"),
        target=Decimal("105"),
    )


def _scanner(signal: StrategySignal) -> ScannerResult:
    return ScannerResult(
        instrument_id=signal.instrument_id,
        signal_id=signal.signal_id,
        recommendation=ScannerRecommendation.CANDIDATE,
        ranking_score=Decimal("82.50"),
        components=(),
        reason_codes=(),
        commentary="Ranking only",
        provenance=("scanner:fixture",),
    )


def _consensus(signal: StrategySignal) -> StrategyConsensus:
    return StrategyConsensus(
        instrument_id=signal.instrument_id,
        status=ConsensusStatus.SINGLE,
        signals=(signal,),
        reason_codes=(),
    )


def _ai(
    *,
    bias: DirectionalBias = DirectionalBias.BULLISH,
    risk: EventRisk = EventRisk.MEDIUM,
    confidence: Decimal = Decimal("0.75"),
) -> MarketAIAnalysis:
    return MarketAIAnalysis(
        status=AIAnalysisStatus.AVAILABLE,
        model_id="openai-responses:test",
        prompt_version="prompt-v1",
        market_scope="IX.D.NASDAQ.IFD.IP",
        directional_bias=bias,
        event_risk=risk,
        confidence=confidence,
        summary="Aligned test context",
        risk_flags=(),
        source_signal_ids=("OFFICIAL-NEWS-1",),
        generated_at_utc=NOW - timedelta(minutes=2),
        valid_until_utc=NOW + timedelta(minutes=3),
    )


def test_aligned_scanner_consensus_and_ai_produce_advisory_directive() -> None:
    signal = _signal()

    directive = AnalysisDirectiveService().evaluate(
        signal=signal,
        scanner_result=_scanner(signal),
        consensus=_consensus(signal),
        ai_analysis=_ai(),
        policy=_policy(),
        evaluated_at_utc=NOW,
    )

    assert directive.status is AnalysisDirectiveStatus.READY
    assert directive.side is SignalSide.BUY
    assert directive.entry_zone == signal.entry_zone
    assert directive.valid_until_utc == NOW + timedelta(minutes=3)
    assert directive.source_signal_ids == ("SIGNAL-1", "OFFICIAL-NEWS-1")
    assert directive.reason_codes == ("ANALYSIS_DIRECTIVE_READY",)
    assert not hasattr(directive, "account")
    assert not hasattr(directive, "quantity")


@pytest.mark.parametrize(
    ("ai", "reason"),
    (
        (_ai(bias=DirectionalBias.BEARISH), "AI_DIRECTION_NOT_ALIGNED"),
        (_ai(risk=EventRisk.HIGH), "AI_EVENT_RISK_BLOCKED:high"),
        (_ai(confidence=Decimal("0.40")), "AI_CONFIDENCE_BELOW_MINIMUM"),
        (None, "AI_ANALYSIS_MISSING"),
    ),
)
def test_ai_mismatch_missing_or_risk_produces_no_trade(
    ai: MarketAIAnalysis | None,
    reason: str,
) -> None:
    signal = _signal()

    directive = AnalysisDirectiveService().evaluate(
        signal=signal,
        scanner_result=_scanner(signal),
        consensus=_consensus(signal),
        ai_analysis=ai,
        policy=_policy(),
        evaluated_at_utc=NOW,
    )

    assert directive.status is AnalysisDirectiveStatus.NO_TRADE
    assert directive.side is None
    assert reason in directive.reason_codes


def test_sell_requires_bearish_ai_alignment() -> None:
    signal = _signal(SignalSide.SELL)

    directive = AnalysisDirectiveService().evaluate(
        signal=signal,
        scanner_result=_scanner(signal),
        consensus=_consensus(signal),
        ai_analysis=_ai(bias=DirectionalBias.BEARISH),
        policy=_policy(),
        evaluated_at_utc=NOW,
    )

    assert directive.status is AnalysisDirectiveStatus.READY
    assert directive.side is SignalSide.SELL


def test_scanner_and_consensus_vetoes_override_aligned_ai() -> None:
    signal = _signal()
    scanner = replace(
        _scanner(signal),
        recommendation=ScannerRecommendation.NO_TRADE,
        ranking_score=None,
    )
    consensus = replace(_consensus(signal), status=ConsensusStatus.DIVERGENT)

    directive = AnalysisDirectiveService().evaluate(
        signal=signal,
        scanner_result=scanner,
        consensus=consensus,
        ai_analysis=_ai(),
        policy=_policy(),
        evaluated_at_utc=NOW,
    )

    assert directive.status is AnalysisDirectiveStatus.NO_TRADE
    assert "SCANNER_RECOMMENDATION_NOT_ALLOWED" in directive.reason_codes
    assert "SCANNER_SCORE_UNAVAILABLE" in directive.reason_codes
    assert "CONSENSUS_NOT_ALLOWED" in directive.reason_codes


def test_expired_signal_and_ai_never_produce_ready_directive() -> None:
    signal = replace(_signal(), valid_until_utc=NOW - timedelta(seconds=1))
    ai = replace(_ai(), valid_until_utc=NOW - timedelta(seconds=1))

    directive = AnalysisDirectiveService().evaluate(
        signal=signal,
        scanner_result=_scanner(signal),
        consensus=_consensus(signal),
        ai_analysis=ai,
        policy=_policy(),
        evaluated_at_utc=NOW,
    )

    assert directive.status is AnalysisDirectiveStatus.NO_TRADE
    assert directive.valid_until_utc == NOW
    assert "SIGNAL_EXPIRED" in directive.reason_codes
    assert "AI_ANALYSIS_EXPIRED" in directive.reason_codes


def test_mismatched_evidence_identity_is_rejected() -> None:
    signal = _signal()
    scanner = replace(_scanner(signal), signal_id="OTHER")

    with pytest.raises(ValueError, match="does not match"):
        AnalysisDirectiveService().evaluate(
            signal=signal,
            scanner_result=scanner,
            consensus=_consensus(signal),
            ai_analysis=_ai(),
            policy=_policy(),
            evaluated_at_utc=NOW,
        )
