"""Deterministic builders for the human-approved scanner score bands."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from trading_ig_assistant.domain.analysis import (
    ConsensusStatus,
    DataState,
    ScannerResult,
    ScoreBand,
    ScoreComponent,
    ScoreComponentName,
    SignalSide,
    StrategyConsensus,
    StrategySignal,
)
from trading_ig_assistant.domain.macro_context import EventRisk, MacroRibbonState
from trading_ig_assistant.services.setup_scoring_service import (
    SetupScoringService,
    build_banded_score_component,
)


class MarketRiskState(StrEnum):
    VERY_LOW = "very_low"
    NORMAL = "normal"
    ELEVATED = "elevated"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class ScannerComponentService:
    """Build score components without calculating a broker command or probability."""

    def technical(self, consensus: StrategyConsensus) -> ScoreComponent:
        signals = consensus.signals
        provenance = _signal_provenance(signals)
        if consensus.status is ConsensusStatus.DIVERGENT:
            return _component(
                ScoreComponentName.TECHNICAL,
                ScoreBand.UNFAVORABLE,
                ("TECHNICAL_CONSENSUS_DIVERGENT", *consensus.reason_codes),
                provenance,
                veto=True,
            )
        if any(signal.data_state is DataState.INVALID for signal in signals):
            return _component(
                ScoreComponentName.TECHNICAL,
                ScoreBand.UNKNOWN,
                ("TECHNICAL_INPUT_INVALID",),
                provenance,
            )
        actionable = tuple(
            signal
            for signal in signals
            if signal.data_state is DataState.READY and signal.side is not SignalSide.FLAT
        )
        if len(actionable) >= 2 and all(signal.side is actionable[0].side for signal in actionable):
            return _component(
                ScoreComponentName.TECHNICAL,
                ScoreBand.EXCEPTIONAL,
                ("TECHNICAL_MULTI_STRATEGY_ALIGNED",),
                provenance,
            )
        if len(actionable) == 1 and all(signal.data_state is DataState.READY for signal in signals):
            return _component(
                ScoreComponentName.TECHNICAL,
                ScoreBand.FAVORABLE,
                ("TECHNICAL_SINGLE_ACTIONABLE_SIGNAL",),
                provenance,
            )
        if actionable:
            return _component(
                ScoreComponentName.TECHNICAL,
                ScoreBand.CAUTION,
                ("TECHNICAL_SIGNAL_WITH_INCOMPLETE_CONFIRMATION",),
                provenance,
            )
        if signals and all(signal.data_state is DataState.READY for signal in signals):
            return _component(
                ScoreComponentName.TECHNICAL,
                ScoreBand.CAUTION,
                ("TECHNICAL_NO_ACTIONABLE_SETUP",),
                provenance,
            )
        return _component(
            ScoreComponentName.TECHNICAL,
            ScoreBand.UNKNOWN,
            ("TECHNICAL_WARMING_UP",),
            provenance,
        )

    def reward_risk(self, signal: StrategySignal) -> ScoreComponent:
        provenance = signal.provenance
        if signal.entry_zone is None or signal.invalidation is None or signal.target is None:
            return _component(
                ScoreComponentName.REWARD_RISK,
                ScoreBand.UNKNOWN,
                ("REWARD_RISK_LEVELS_MISSING",),
                provenance,
            )
        entry = _conservative_entry(signal)
        if signal.side is SignalSide.BUY:
            risk = entry - signal.invalidation
            reward = signal.target - entry
        elif signal.side is SignalSide.SELL:
            risk = signal.invalidation - entry
            reward = entry - signal.target
        else:
            return _component(
                ScoreComponentName.REWARD_RISK,
                ScoreBand.UNKNOWN,
                ("REWARD_RISK_FLAT_SIGNAL",),
                provenance,
            )
        if risk <= 0 or reward <= 0:
            return _component(
                ScoreComponentName.REWARD_RISK,
                ScoreBand.UNFAVORABLE,
                ("REWARD_RISK_INVALID_GEOMETRY",),
                provenance,
                veto=True,
            )
        ratio = reward / risk
        if ratio >= Decimal("3"):
            band = ScoreBand.EXCEPTIONAL
        elif ratio >= Decimal("2"):
            band = ScoreBand.FAVORABLE
        elif ratio >= Decimal("1"):
            band = ScoreBand.CAUTION
        else:
            band = ScoreBand.UNFAVORABLE
        return _component(
            ScoreComponentName.REWARD_RISK,
            band,
            (f"REWARD_RISK_RATIO:{ratio.quantize(Decimal('0.0001'))}",),
            (*provenance, f"reward_risk_ratio:{ratio}"),
        )

    def execution_cost(
        self,
        *,
        estimated_cost: Decimal | None,
        potential_gross_gain: Decimal | None,
        provenance: tuple[str, ...] = (),
    ) -> ScoreComponent:
        if estimated_cost is None or potential_gross_gain is None:
            return _component(
                ScoreComponentName.EXECUTION_COST,
                ScoreBand.UNKNOWN,
                ("EXECUTION_COST_INPUT_MISSING",),
                provenance,
            )
        if estimated_cost < 0:
            raise ValueError("estimated execution cost must not be negative")
        if potential_gross_gain <= 0:
            return _component(
                ScoreComponentName.EXECUTION_COST,
                ScoreBand.UNFAVORABLE,
                ("EXECUTION_GAIN_NOT_POSITIVE",),
                provenance,
                veto=True,
            )
        ratio_percent = estimated_cost / potential_gross_gain * Decimal("100")
        if ratio_percent <= Decimal("5"):
            band = ScoreBand.EXCEPTIONAL
        elif ratio_percent <= Decimal("10"):
            band = ScoreBand.FAVORABLE
        elif ratio_percent <= Decimal("20"):
            band = ScoreBand.CAUTION
        else:
            band = ScoreBand.UNFAVORABLE
        return _component(
            ScoreComponentName.EXECUTION_COST,
            band,
            (f"EXECUTION_COST_PERCENT:{ratio_percent.quantize(Decimal('0.01'))}",),
            (*provenance, f"execution_cost_percent:{ratio_percent}"),
        )

    def data_quality(
        self,
        *,
        state: DataState,
        quality: Decimal | None,
        fresh: bool | None,
        continuous: bool | None,
        provenance: tuple[str, ...] = (),
    ) -> ScoreComponent:
        if state is DataState.INVALID or fresh is False or continuous is False:
            reasons = ["DATA_QUALITY_INVALID"]
            if fresh is False:
                reasons.append("DATA_STALE")
            if continuous is False:
                reasons.append("DATA_DISCONTINUOUS")
            return _component(
                ScoreComponentName.DATA_QUALITY,
                ScoreBand.UNFAVORABLE,
                tuple(reasons),
                provenance,
                veto=True,
            )
        if state is DataState.WARMING_UP or quality is None or fresh is None or continuous is None:
            return _component(
                ScoreComponentName.DATA_QUALITY,
                ScoreBand.UNKNOWN,
                ("DATA_QUALITY_INSUFFICIENT",),
                provenance,
            )
        if not Decimal("0") <= quality <= Decimal("1"):
            raise ValueError("data quality must be between zero and one")
        if quality >= Decimal("0.95"):
            band = ScoreBand.EXCEPTIONAL
        elif quality >= Decimal("0.80"):
            band = ScoreBand.FAVORABLE
        elif quality >= Decimal("0.50"):
            band = ScoreBand.CAUTION
        else:
            band = ScoreBand.UNFAVORABLE
        return _component(
            ScoreComponentName.DATA_QUALITY,
            band,
            (f"DATA_QUALITY_RATIO:{quality}",),
            (*provenance, f"data_quality:{quality}"),
            veto=band is ScoreBand.UNFAVORABLE,
        )

    def market_risk(
        self,
        risk_state: MarketRiskState,
        *,
        observed_at_utc: datetime | None = None,
        provenance: tuple[str, ...] = (),
    ) -> ScoreComponent:
        band = {
            MarketRiskState.VERY_LOW: ScoreBand.EXCEPTIONAL,
            MarketRiskState.NORMAL: ScoreBand.FAVORABLE,
            MarketRiskState.ELEVATED: ScoreBand.CAUTION,
            MarketRiskState.CRITICAL: ScoreBand.UNFAVORABLE,
            MarketRiskState.UNKNOWN: ScoreBand.UNKNOWN,
        }[risk_state]
        timestamp_provenance = (
            (f"market_risk_observed_at:{observed_at_utc.isoformat()}",)
            if observed_at_utc is not None
            else ()
        )
        return _component(
            ScoreComponentName.MARKET_RISK,
            band,
            (f"MARKET_RISK_{risk_state.value.upper()}",),
            (*provenance, *timestamp_provenance),
            veto=risk_state is MarketRiskState.CRITICAL,
        )

    def market_risk_from_macro(
        self,
        state: MacroRibbonState | None,
    ) -> ScoreComponent:
        """Project the validated event-risk proxy without conflating direction and safety."""

        if state is None:
            return self.market_risk(
                MarketRiskState.UNKNOWN,
                provenance=("macro_state:unavailable",),
            )
        normalized = {
            EventRisk.HIGH: MarketRiskState.CRITICAL,
            EventRisk.MEDIUM: MarketRiskState.ELEVATED,
            EventRisk.LOW: MarketRiskState.NORMAL,
            EventRisk.UNKNOWN: MarketRiskState.UNKNOWN,
        }[state.event_risk]
        return self.market_risk(
            normalized,
            observed_at_utc=state.generated_at_utc,
            provenance=(
                "market_risk_proxy:event_risk",
                f"macro_event_risk:{state.event_risk.value}",
                *state.provenance,
            ),
        )

    def score_signals(
        self,
        consensus: StrategyConsensus,
        context_component: ScoreComponent,
        *,
        fresh: bool,
        continuous: bool,
        market_risk_state: MarketRiskState = MarketRiskState.UNKNOWN,
        market_risk_component: ScoreComponent | None = None,
        product_spread: Decimal | None = None,
        fee_per_unit_per_side: Decimal | None = None,
        execution_price_scale_verified: bool = False,
        component_weights: Mapping[ScoreComponentName, Decimal] | None = None,
        candidate_threshold: Decimal = Decimal("75"),
        watch_threshold: Decimal = Decimal("60"),
    ) -> tuple[ScannerResult, ...]:
        """Build honest per-signal results; unavailable components keep totals unavailable."""

        if context_component.name is not ScoreComponentName.CONTEXT:
            raise ValueError("context_component must be the context score component")
        technical = self.technical(consensus)
        if (
            market_risk_component is not None
            and market_risk_component.name is not ScoreComponentName.MARKET_RISK
        ):
            raise ValueError("market_risk_component must be the market-risk score component")
        market_risk = market_risk_component or self.market_risk(market_risk_state)
        scoring = SetupScoringService(
            candidate_threshold=candidate_threshold,
            watch_threshold=watch_threshold,
        )
        results = []
        for signal in consensus.signals:
            execution_cost = self._signal_execution_cost(
                signal,
                product_spread=product_spread,
                fee_per_unit_per_side=fee_per_unit_per_side,
                price_scale_verified=execution_price_scale_verified,
            )
            data_quality = self.data_quality(
                state=signal.data_state,
                quality=signal.data_quality,
                fresh=fresh,
                continuous=continuous,
                provenance=signal.provenance,
            )
            components = (
                technical,
                context_component,
                self.reward_risk(signal),
                market_risk,
                execution_cost,
                data_quality,
            )
            if component_weights is not None:
                components = tuple(
                    replace(
                        component,
                        weight=component_weights.get(component.name, component.weight),
                    )
                    for component in components
                )
            results.append(scoring.score(signal, components))
        return tuple(results)

    def _signal_execution_cost(
        self,
        signal: StrategySignal,
        *,
        product_spread: Decimal | None,
        fee_per_unit_per_side: Decimal | None,
        price_scale_verified: bool,
    ) -> ScoreComponent:
        if not price_scale_verified:
            return self.execution_cost(
                estimated_cost=None,
                potential_gross_gain=None,
                provenance=("execution_price_scale:unverified",),
            )
        if product_spread is not None and product_spread < 0:
            raise ValueError("product spread must not be negative")
        if fee_per_unit_per_side is not None and fee_per_unit_per_side < 0:
            raise ValueError("fee per unit per side must not be negative")
        estimated_cost = (
            product_spread + fee_per_unit_per_side * Decimal("2")
            if product_spread is not None and fee_per_unit_per_side is not None
            else None
        )
        potential_gross_gain = _potential_gross_gain(signal)
        provenance = tuple(
            item
            for item in (
                "execution_price_scale:verified",
                f"product_spread:{product_spread}" if product_spread is not None else None,
                (
                    f"manual_fee_per_unit_per_side:{fee_per_unit_per_side}"
                    if fee_per_unit_per_side is not None
                    else None
                ),
                "round_trip_fee_sides:2" if fee_per_unit_per_side is not None else None,
            )
            if item is not None
        )
        return self.execution_cost(
            estimated_cost=estimated_cost,
            potential_gross_gain=potential_gross_gain,
            provenance=provenance,
        )


def _conservative_entry(signal: StrategySignal) -> Decimal:
    assert signal.entry_zone is not None
    if signal.side is SignalSide.BUY:
        return signal.entry_zone[1]
    return signal.entry_zone[0]


def _potential_gross_gain(signal: StrategySignal) -> Decimal | None:
    if signal.entry_zone is None or signal.target is None:
        return None
    entry = _conservative_entry(signal)
    if signal.side is SignalSide.BUY:
        return signal.target - entry
    if signal.side is SignalSide.SELL:
        return entry - signal.target
    return None


def _signal_provenance(signals: tuple[StrategySignal, ...]) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            item
            for signal in signals
            for item in (
                f"signal:{signal.signal_id}",
                f"strategy:{signal.strategy_id}",
                *signal.provenance,
            )
        )
    )


def _component(
    name: ScoreComponentName,
    band: ScoreBand,
    reasons: tuple[str, ...],
    provenance: tuple[str, ...],
    *,
    veto: bool = False,
) -> ScoreComponent:
    return build_banded_score_component(
        name,
        band,
        reason_codes=tuple(dict.fromkeys(reasons)),
        provenance=tuple(dict.fromkeys(provenance)),
        veto=veto,
    )
