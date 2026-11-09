"""Combine scanner and AI evidence into a non-executable advisory directive."""

from __future__ import annotations

from datetime import UTC, datetime

from trading_ig_assistant.domain.ai_context import AIAnalysisStatus, MarketAIAnalysis
from trading_ig_assistant.domain.analysis import (
    DataState,
    ScannerResult,
    SignalSide,
    StrategyConsensus,
    StrategySignal,
)
from trading_ig_assistant.domain.analysis_directives import (
    AnalysisDirective,
    AnalysisDirectivePolicy,
    AnalysisDirectiveStatus,
)
from trading_ig_assistant.domain.macro_context import DirectionalBias


class AnalysisDirectiveService:
    """Evaluate evidence only; never build a ticket, quantity or broker intent."""

    def evaluate(
        self,
        *,
        signal: StrategySignal,
        scanner_result: ScannerResult,
        consensus: StrategyConsensus,
        ai_analysis: MarketAIAnalysis | None,
        policy: AnalysisDirectivePolicy,
        evaluated_at_utc: datetime,
    ) -> AnalysisDirective:
        _validate_evidence_identity(signal, scanner_result, consensus)
        if evaluated_at_utc.tzinfo is None or evaluated_at_utc.utcoffset() != UTC.utcoffset(
            evaluated_at_utc
        ):
            raise ValueError("analysis directive evaluation time must use UTC")

        reasons: list[str] = []
        if signal.data_state is not DataState.READY:
            reasons.append(f"SIGNAL_{signal.data_state.value.upper()}")
        if signal.side is SignalSide.FLAT:
            reasons.append("SIGNAL_FLAT")
        if evaluated_at_utc < signal.generated_at_utc:
            reasons.append("SIGNAL_FROM_FUTURE")
        if evaluated_at_utc >= signal.valid_until_utc:
            reasons.append("SIGNAL_EXPIRED")
        if signal.entry_zone is None or signal.invalidation is None or signal.target is None:
            reasons.append("TECHNICAL_LEVELS_UNAVAILABLE")
        if scanner_result.recommendation not in policy.allowed_recommendations:
            reasons.append("SCANNER_RECOMMENDATION_NOT_ALLOWED")
        if scanner_result.ranking_score is None:
            reasons.append("SCANNER_SCORE_UNAVAILABLE")
        if any(component.veto for component in scanner_result.components):
            reasons.append("SCANNER_COMPONENT_VETO")
        if consensus.status not in policy.allowed_consensus_statuses:
            reasons.append("CONSENSUS_NOT_ALLOWED")

        ai_source_ids: tuple[str, ...] = ()
        ai_valid_until: datetime | None = None
        if policy.require_ai_alignment:
            ai_reasons, ai_source_ids, ai_valid_until = _evaluate_required_ai(
                signal=signal,
                ai_analysis=ai_analysis,
                policy=policy,
                evaluated_at_utc=evaluated_at_utc,
            )
            reasons.extend(ai_reasons)

        status = AnalysisDirectiveStatus.NO_TRADE if reasons else AnalysisDirectiveStatus.READY
        valid_until = evaluated_at_utc
        if status is AnalysisDirectiveStatus.READY:
            valid_until = signal.valid_until_utc
            if ai_valid_until is not None:
                valid_until = min(valid_until, ai_valid_until)
        provenance = tuple(
            dict.fromkeys(
                (
                    *signal.provenance,
                    *scanner_result.provenance,
                    f"directive_policy:{policy.policy_id}",
                    f"scanner_recommendation:{scanner_result.recommendation.value}",
                    f"consensus:{consensus.status.value}",
                    *(
                        (
                            f"ai_model:{ai_analysis.model_id}",
                            f"ai_prompt:{ai_analysis.prompt_version}",
                        )
                        if ai_analysis is not None
                        else ()
                    ),
                )
            )
        )
        return AnalysisDirective(
            directive_id=f"DIRECTIVE:{policy.policy_id}:{signal.signal_id}",
            policy_id=policy.policy_id,
            status=status,
            instrument_id=signal.instrument_id,
            strategy_id=signal.strategy_id,
            signal_id=signal.signal_id,
            side=signal.side if status is AnalysisDirectiveStatus.READY else None,
            entry_zone=signal.entry_zone if status is AnalysisDirectiveStatus.READY else None,
            invalidation=signal.invalidation if status is AnalysisDirectiveStatus.READY else None,
            target=signal.target if status is AnalysisDirectiveStatus.READY else None,
            generated_at_utc=evaluated_at_utc,
            valid_until_utc=valid_until,
            reason_codes=("ANALYSIS_DIRECTIVE_READY",)
            if status is AnalysisDirectiveStatus.READY
            else tuple(dict.fromkeys(reasons)),
            source_signal_ids=tuple(dict.fromkeys((signal.signal_id, *ai_source_ids))),
            provenance=provenance,
        )


def _validate_evidence_identity(
    signal: StrategySignal,
    scanner_result: ScannerResult,
    consensus: StrategyConsensus,
) -> None:
    if scanner_result.signal_id != signal.signal_id:
        raise ValueError("scanner result does not match the strategy signal")
    if scanner_result.instrument_id != signal.instrument_id:
        raise ValueError("scanner result instrument does not match the strategy signal")
    if consensus.instrument_id != signal.instrument_id:
        raise ValueError("strategy consensus instrument does not match the strategy signal")
    if signal.signal_id not in {item.signal_id for item in consensus.signals}:
        raise ValueError("strategy consensus does not contain the strategy signal")


def _evaluate_required_ai(
    *,
    signal: StrategySignal,
    ai_analysis: MarketAIAnalysis | None,
    policy: AnalysisDirectivePolicy,
    evaluated_at_utc: datetime,
) -> tuple[list[str], tuple[str, ...], datetime | None]:
    if ai_analysis is None:
        return ["AI_ANALYSIS_MISSING"], (), None
    reasons: list[str] = []
    if ai_analysis.status is not AIAnalysisStatus.AVAILABLE:
        reasons.append("AI_ANALYSIS_UNAVAILABLE")
    if ai_analysis.market_scope != signal.instrument_id:
        reasons.append("AI_SCOPE_MISMATCH")
    if evaluated_at_utc < ai_analysis.generated_at_utc:
        reasons.append("AI_ANALYSIS_FROM_FUTURE")
    if evaluated_at_utc >= ai_analysis.valid_until_utc:
        reasons.append("AI_ANALYSIS_EXPIRED")
    if ai_analysis.event_risk in policy.blocked_ai_event_risks:
        reasons.append(f"AI_EVENT_RISK_BLOCKED:{ai_analysis.event_risk.value}")
    expected_bias = {
        SignalSide.BUY: DirectionalBias.BULLISH,
        SignalSide.SELL: DirectionalBias.BEARISH,
        SignalSide.FLAT: DirectionalBias.UNKNOWN,
    }[signal.side]
    if ai_analysis.directional_bias is not expected_bias:
        reasons.append("AI_DIRECTION_NOT_ALIGNED")
    if policy.minimum_ai_confidence is not None and (
        ai_analysis.confidence is None or ai_analysis.confidence < policy.minimum_ai_confidence
    ):
        reasons.append("AI_CONFIDENCE_BELOW_MINIMUM")
    return reasons, ai_analysis.source_signal_ids, ai_analysis.valid_until_utc
