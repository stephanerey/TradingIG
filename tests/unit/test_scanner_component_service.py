from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from trading_ig_assistant.domain.analysis import (
    ConsensusStatus,
    DataState,
    ScoreBand,
    ScoreComponentName,
    SignalSide,
    StrategyConsensus,
    StrategySignal,
)
from trading_ig_assistant.domain.macro_context import (
    DirectionalBias,
    EventRisk,
    MacroRibbonState,
    MarketRegime,
)
from trading_ig_assistant.services.scanner_component_service import (
    MarketRiskState,
    ScannerComponentService,
)
from trading_ig_assistant.services.setup_scoring_service import build_banded_score_component

NOW = datetime(2026, 11, 5, 14, 0, tzinfo=UTC)


def _signal(
    signal_id: str,
    *,
    side: SignalSide = SignalSide.BUY,
    state: DataState = DataState.READY,
    entry: tuple[str, str] | None = ("100", "101"),
    stop: str | None = "99",
    target: str | None = "107",
) -> StrategySignal:
    return StrategySignal(
        signal_id=signal_id,
        strategy_id=signal_id,
        strategy_version="fixture-v1",
        instrument_id="SYNTHETIC",
        side=side,
        generated_at_utc=NOW,
        valid_until_utc=NOW + timedelta(minutes=5),
        data_state=state,
        reason_codes=(),
        features=(),
        provenance=(f"source:{signal_id}",),
        entry_zone=(Decimal(entry[0]), Decimal(entry[1])) if entry else None,
        invalidation=Decimal(stop) if stop is not None else None,
        target=Decimal(target) if target is not None else None,
        data_quality=Decimal("1") if state is DataState.READY else Decimal("0"),
    )


def test_technical_component_uses_consensus_and_vetoes_divergence() -> None:
    service = ScannerComponentService()
    aligned_signals = (_signal("a"), _signal("b"), _signal("c", side=SignalSide.FLAT))
    aligned = service.technical(
        StrategyConsensus("SYNTHETIC", ConsensusStatus.ALIGNED, aligned_signals, ())
    )
    divergent = service.technical(
        StrategyConsensus(
            "SYNTHETIC",
            ConsensusStatus.DIVERGENT,
            (_signal("buy"), _signal("sell", side=SignalSide.SELL)),
            ("CONTRADICTORY_BUY_SELL",),
        )
    )

    assert aligned.band is ScoreBand.EXCEPTIONAL
    assert aligned.score == Decimal("100")
    assert divergent.band is ScoreBand.UNFAVORABLE
    assert divergent.veto is True


def test_technical_component_keeps_warmup_unknown() -> None:
    signal = _signal("warming", side=SignalSide.FLAT, state=DataState.WARMING_UP)
    component = ScannerComponentService().technical(
        StrategyConsensus("SYNTHETIC", ConsensusStatus.NO_SIGNAL, (signal,), ())
    )

    assert component.band is ScoreBand.UNKNOWN
    assert component.score is None


@pytest.mark.parametrize(
    ("target", "expected"),
    (("107", ScoreBand.EXCEPTIONAL), ("105", ScoreBand.FAVORABLE), ("103", ScoreBand.CAUTION)),
)
def test_reward_risk_uses_conservative_entry_edge(target, expected) -> None:
    component = ScannerComponentService().reward_risk(_signal("rr", target=target))

    assert component.band is expected


def test_reward_risk_invalid_geometry_is_red_veto() -> None:
    component = ScannerComponentService().reward_risk(_signal("rr", stop="102"))

    assert component.band is ScoreBand.UNFAVORABLE
    assert component.veto is True


@pytest.mark.parametrize(
    ("cost", "expected"),
    (
        ("5", ScoreBand.EXCEPTIONAL),
        ("10", ScoreBand.FAVORABLE),
        ("20", ScoreBand.CAUTION),
        ("21", ScoreBand.UNFAVORABLE),
    ),
)
def test_execution_cost_bands_are_percent_of_potential_gain(cost, expected) -> None:
    component = ScannerComponentService().execution_cost(
        estimated_cost=Decimal(cost),
        potential_gross_gain=Decimal("100"),
    )

    assert component.band is expected


def test_data_quality_requires_ready_fresh_continuous_data() -> None:
    service = ScannerComponentService()
    exceptional = service.data_quality(
        state=DataState.READY,
        quality=Decimal("1"),
        fresh=True,
        continuous=True,
    )
    stale = service.data_quality(
        state=DataState.READY,
        quality=Decimal("1"),
        fresh=False,
        continuous=True,
    )
    unknown = service.data_quality(
        state=DataState.WARMING_UP,
        quality=None,
        fresh=True,
        continuous=True,
    )

    assert exceptional.band is ScoreBand.EXCEPTIONAL
    assert stale.band is ScoreBand.UNFAVORABLE and stale.veto
    assert unknown.band is ScoreBand.UNKNOWN and unknown.score is None


@pytest.mark.parametrize(
    ("state", "band", "veto"),
    (
        (MarketRiskState.VERY_LOW, ScoreBand.EXCEPTIONAL, False),
        (MarketRiskState.NORMAL, ScoreBand.FAVORABLE, False),
        (MarketRiskState.ELEVATED, ScoreBand.CAUTION, False),
        (MarketRiskState.CRITICAL, ScoreBand.UNFAVORABLE, True),
        (MarketRiskState.UNKNOWN, ScoreBand.UNKNOWN, False),
    ),
)
def test_market_risk_uses_the_shared_scale(state, band, veto) -> None:
    component = ScannerComponentService().market_risk(state, observed_at_utc=NOW)

    assert component.band is band
    assert component.veto is veto


@pytest.mark.parametrize(
    ("event_risk", "band", "veto"),
    (
        (EventRisk.LOW, ScoreBand.FAVORABLE, False),
        (EventRisk.MEDIUM, ScoreBand.CAUTION, False),
        (EventRisk.HIGH, ScoreBand.UNFAVORABLE, True),
        (EventRisk.UNKNOWN, ScoreBand.UNKNOWN, False),
    ),
)
def test_macro_event_risk_proxy_preserves_direction_risk_separation(event_risk, band, veto) -> None:
    state = MacroRibbonState(
        schema_version=1,
        regime=MarketRegime.RISK_ON,
        index_bias=DirectionalBias.BULLISH,
        gold_bias=DirectionalBias.BEARISH,
        event_risk=event_risk,
        signals=(),
        generated_at_utc=NOW,
        reason_codes=(),
        provenance=("source:fixture",),
    )

    component = ScannerComponentService().market_risk_from_macro(state)

    assert component.band is band
    assert component.veto is veto
    assert "market_risk_proxy:event_risk" in component.provenance
    assert f"macro_event_risk:{event_risk.value}" in component.provenance
    assert component.band is not ScoreBand.EXCEPTIONAL


def test_missing_macro_state_keeps_market_risk_unknown() -> None:
    component = ScannerComponentService().market_risk_from_macro(None)

    assert component.band is ScoreBand.UNKNOWN
    assert component.provenance == ("macro_state:unavailable",)


def test_missing_levels_and_costs_stay_unknown() -> None:
    service = ScannerComponentService()
    reward_risk = service.reward_risk(replace(_signal("rr"), entry_zone=None))
    costs = service.execution_cost(estimated_cost=None, potential_gross_gain=Decimal("100"))

    assert reward_risk.band is ScoreBand.UNKNOWN
    assert costs.band is ScoreBand.UNKNOWN


def test_partial_preview_components_never_manufacture_a_total_score() -> None:
    service = ScannerComponentService()
    signal = _signal("trend")
    consensus = StrategyConsensus(
        "SYNTHETIC",
        ConsensusStatus.SINGLE,
        (signal,),
        (),
    )
    context = build_banded_score_component(
        ScoreComponentName.CONTEXT,
        ScoreBand.FAVORABLE,
        provenance=("context:fixture",),
    )

    (result,) = service.score_signals(
        consensus,
        context,
        fresh=True,
        continuous=True,
    )

    assert result.ranking_score is None
    assert result.recommendation.value == "no_trade"
    assert "MISSING_MARKET_RISK" in result.reason_codes
    assert "MISSING_EXECUTION_COST" in result.reason_codes


def test_verified_price_scale_uses_spread_and_two_manual_fee_sides() -> None:
    service = ScannerComponentService()
    signal = _signal("costed", target="107")
    consensus = StrategyConsensus("SYNTHETIC", ConsensusStatus.SINGLE, (signal,), ())
    context = build_banded_score_component(
        ScoreComponentName.CONTEXT,
        ScoreBand.FAVORABLE,
    )

    (result,) = service.score_signals(
        consensus,
        context,
        fresh=True,
        continuous=True,
        market_risk_state=MarketRiskState.NORMAL,
        product_spread=Decimal("0.1"),
        fee_per_unit_per_side=Decimal("0.1"),
        execution_price_scale_verified=True,
    )

    costs = next(
        component
        for component in result.components
        if component.name is ScoreComponentName.EXECUTION_COST
    )
    assert costs.band is ScoreBand.EXCEPTIONAL
    assert "product_spread:0.1" in costs.provenance
    assert "manual_fee_per_unit_per_side:0.1" in costs.provenance
    assert result.ranking_score is not None


def test_unverified_price_scale_keeps_configured_cost_unknown() -> None:
    signal = _signal("derivative")
    consensus = StrategyConsensus("SYNTHETIC", ConsensusStatus.SINGLE, (signal,), ())
    context = build_banded_score_component(
        ScoreComponentName.CONTEXT,
        ScoreBand.FAVORABLE,
    )

    (result,) = ScannerComponentService().score_signals(
        consensus,
        context,
        fresh=True,
        continuous=True,
        market_risk_state=MarketRiskState.NORMAL,
        product_spread=Decimal("0.1"),
        fee_per_unit_per_side=Decimal("0"),
        execution_price_scale_verified=False,
    )

    costs = next(
        component
        for component in result.components
        if component.name is ScoreComponentName.EXECUTION_COST
    )
    assert costs.band is ScoreBand.UNKNOWN
    assert "execution_price_scale:unverified" in costs.provenance
    assert result.ranking_score is None


def test_runtime_scoring_uses_configured_weights_and_thresholds() -> None:
    signal = _signal("weighted", target="107")
    consensus = StrategyConsensus("SYNTHETIC", ConsensusStatus.SINGLE, (signal,), ())
    context = build_banded_score_component(
        ScoreComponentName.CONTEXT,
        ScoreBand.FAVORABLE,
    )
    weights = {name: Decimal("0") for name in ScoreComponentName}
    weights[ScoreComponentName.TECHNICAL] = Decimal("100")

    (result,) = ScannerComponentService().score_signals(
        consensus,
        context,
        fresh=True,
        continuous=True,
        market_risk_state=MarketRiskState.NORMAL,
        product_spread=Decimal("0.1"),
        fee_per_unit_per_side=Decimal("0.1"),
        execution_price_scale_verified=True,
        component_weights=weights,
        candidate_threshold=Decimal("80"),
        watch_threshold=Decimal("70"),
    )

    assert result.ranking_score == Decimal("75.00")
    assert result.recommendation.value == "watch"
    assert next(
        component
        for component in result.components
        if component.name is ScoreComponentName.TECHNICAL
    ).weight == Decimal("100")
