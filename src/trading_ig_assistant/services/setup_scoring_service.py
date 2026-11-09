"""Deterministic setup ranking with explicit no-trade outcomes."""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal

from trading_ig_assistant.domain.analysis import (
    ConsensusStatus,
    DataState,
    IndicatorInput,
    ScannerRecommendation,
    ScannerResult,
    ScoreBand,
    ScoreComponent,
    ScoreComponentName,
    SignalSide,
    Strategy,
    StrategyConsensus,
    StrategySignal,
)

DEFAULT_COMPONENT_WEIGHTS: dict[ScoreComponentName, Decimal] = {
    ScoreComponentName.TECHNICAL: Decimal("30"),
    ScoreComponentName.CONTEXT: Decimal("15"),
    ScoreComponentName.REWARD_RISK: Decimal("20"),
    ScoreComponentName.MARKET_RISK: Decimal("15"),
    ScoreComponentName.EXECUTION_COST: Decimal("10"),
    ScoreComponentName.DATA_QUALITY: Decimal("10"),
}


def build_banded_score_component(
    name: ScoreComponentName,
    band: ScoreBand,
    *,
    weight: Decimal | None = None,
    reason_codes: tuple[str, ...] = (),
    provenance: tuple[str, ...] = (),
    veto: bool = False,
) -> ScoreComponent:
    """Build one component on the shared 100/75/50/0/unavailable scale."""

    return ScoreComponent(
        name=name,
        score=band.score,
        weight=DEFAULT_COMPONENT_WEIGHTS[name] if weight is None else weight,
        reason_codes=reason_codes,
        provenance=provenance,
        veto=veto,
        band=band,
    )


class SetupScoringService:
    """Combine explainable components into a ranking, never a probability."""

    def __init__(
        self,
        *,
        candidate_threshold: Decimal = Decimal("75"),
        watch_threshold: Decimal = Decimal("60"),
    ) -> None:
        if not Decimal("0") <= watch_threshold <= candidate_threshold <= Decimal("100"):
            raise ValueError("score thresholds must satisfy 0 <= watch <= candidate <= 100")
        self._candidate_threshold = candidate_threshold
        self._watch_threshold = watch_threshold

    def score(
        self,
        signal: StrategySignal,
        components: Iterable[ScoreComponent],
    ) -> ScannerResult:
        supplied = tuple(components)
        by_name = {component.name: component for component in supplied}
        if len(by_name) != len(supplied):
            raise ValueError("score component names must be unique")

        ordered = tuple(
            by_name.get(
                name,
                ScoreComponent(
                    name=name,
                    score=None,
                    weight=DEFAULT_COMPONENT_WEIGHTS[name],
                    reason_codes=(f"MISSING_{name.value.upper()}",),
                ),
            )
            for name in ScoreComponentName
        )
        reasons = list(signal.reason_codes)
        missing = [component for component in ordered if component.score is None]
        for component in ordered:
            reasons.extend(component.reason_codes)
        reasons.extend(f"MISSING_{component.name.value.upper()}" for component in missing)

        total_weight = sum((component.weight for component in ordered), Decimal("0"))
        if total_weight <= 0:
            raise ValueError("total score weight must be positive")
        ranking_score = None
        if not missing:
            weighted = sum(
                (
                    component.score * component.weight
                    for component in ordered
                    if component.score is not None
                ),
                Decimal("0"),
            )
            ranking_score = (weighted / total_weight).quantize(Decimal("0.01"))

        veto = any(component.veto for component in ordered)
        if signal.data_state is not DataState.READY:
            recommendation = ScannerRecommendation.NO_TRADE
            reasons.append(signal.data_state.value.upper())
        elif signal.side is SignalSide.FLAT:
            recommendation = ScannerRecommendation.NO_TRADE
            reasons.append("FLAT_SIGNAL")
        elif missing:
            recommendation = ScannerRecommendation.NO_TRADE
        elif veto:
            recommendation = ScannerRecommendation.NO_TRADE
            reasons.append("COMPONENT_VETO")
        elif ranking_score is not None and ranking_score >= self._candidate_threshold:
            recommendation = ScannerRecommendation.CANDIDATE
        elif ranking_score is not None and ranking_score >= self._watch_threshold:
            recommendation = ScannerRecommendation.WATCH
        else:
            recommendation = ScannerRecommendation.NO_TRADE
            reasons.append("BELOW_WATCH_THRESHOLD")

        unique_reasons = tuple(dict.fromkeys(reasons))
        provenance = tuple(
            dict.fromkeys(
                (
                    *signal.provenance,
                    *(item for component in ordered for item in component.provenance),
                )
            )
        )
        component_text = ", ".join(self._describe_component(component) for component in ordered)
        score_text = str(ranking_score) if ranking_score is not None else "unavailable"
        commentary = (
            f"Ranking score {score_text}/100 (ranking, not a probability). "
            f"Components: {component_text}. Decision: {recommendation.value}."
        )
        if unique_reasons:
            commentary += f" Reasons: {', '.join(unique_reasons)}."

        return ScannerResult(
            instrument_id=signal.instrument_id,
            signal_id=signal.signal_id,
            recommendation=recommendation,
            ranking_score=ranking_score,
            components=ordered,
            reason_codes=unique_reasons,
            commentary=commentary,
            provenance=provenance,
        )

    @staticmethod
    def _describe_component(component: ScoreComponent) -> str:
        value = component.score if component.score is not None else "unavailable"
        return f"{component.name.value}={value}@{component.weight}"

    @staticmethod
    def rank(results: Iterable[ScannerResult]) -> tuple[ScannerResult, ...]:
        """Rank actionable results first, deterministically breaking ties by identifiers."""

        order = {
            ScannerRecommendation.CANDIDATE: 0,
            ScannerRecommendation.WATCH: 1,
            ScannerRecommendation.NO_TRADE: 2,
        }
        return tuple(
            sorted(
                results,
                key=lambda result: (
                    order[result.recommendation],
                    -(result.ranking_score if result.ranking_score is not None else Decimal("-1")),
                    result.instrument_id,
                    result.signal_id,
                ),
            )
        )


class StrategyRegistry:
    """Registry for deterministic, broker-independent strategy evaluation."""

    def __init__(self) -> None:
        self._strategies: dict[str, Strategy] = {}

    def register(self, strategy: Strategy) -> None:
        if strategy.strategy_id in self._strategies:
            raise ValueError(f"strategy already registered: {strategy.strategy_id}")
        self._strategies[strategy.strategy_id] = strategy

    def evaluate(self, indicator_input: IndicatorInput) -> tuple[StrategySignal, ...]:
        return tuple(
            self._strategies[strategy_id].evaluate(indicator_input)
            for strategy_id in sorted(self._strategies)
        )


def build_consensus(signals: Iterable[StrategySignal]) -> StrategyConsensus:
    """Preserve every strategy result and expose BUY/SELL divergence explicitly."""
    ordered = tuple(sorted(signals, key=lambda signal: (signal.strategy_id, signal.signal_id)))
    if not ordered:
        raise ValueError("consensus requires at least one strategy signal")
    instrument_ids = {signal.instrument_id for signal in ordered}
    if len(instrument_ids) != 1:
        raise ValueError("consensus signals must target one instrument")
    sides = {signal.side for signal in ordered if signal.side is not SignalSide.FLAT}
    if SignalSide.BUY in sides and SignalSide.SELL in sides:
        status = ConsensusStatus.DIVERGENT
        reasons = ("CONTRADICTORY_BUY_SELL",)
    elif not sides:
        status = ConsensusStatus.NO_SIGNAL
        reasons = ("ALL_STRATEGIES_FLAT",)
    elif len(ordered) == 1:
        status = ConsensusStatus.SINGLE
        reasons = ()
    else:
        status = ConsensusStatus.ALIGNED
        reasons = ()
    return StrategyConsensus(
        instrument_id=ordered[0].instrument_id,
        status=status,
        signals=ordered,
        reason_codes=reasons,
    )
