from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from trading_ig_assistant.domain.analysis import (
    ConsensusStatus,
    DataState,
    IndicatorInput,
    ScannerRecommendation,
    ScoreBand,
    ScoreComponent,
    ScoreComponentName,
    SignalSide,
    StrategySignal,
)
from trading_ig_assistant.services.setup_scoring_service import (
    DEFAULT_COMPONENT_WEIGHTS,
    SetupScoringService,
    StrategyRegistry,
    build_banded_score_component,
    build_consensus,
)

NOW = datetime(2026, 10, 22, 12, 0, tzinfo=UTC)


def _signal(
    signal_id: str = "SIGNAL-1",
    *,
    state: DataState = DataState.READY,
    side: SignalSide = SignalSide.BUY,
    instrument_id: str = "SYNTHETIC",
) -> StrategySignal:
    return StrategySignal(
        signal_id=signal_id,
        strategy_id="fixture",
        strategy_version="1",
        instrument_id=instrument_id,
        side=side,
        generated_at_utc=NOW,
        valid_until_utc=NOW + timedelta(minutes=5),
        data_state=state,
        reason_codes=(),
        features=(("fixture", Decimal("1")),),
        provenance=("source:fixture",),
    )


def _components(score: str = "80") -> tuple[ScoreComponent, ...]:
    return tuple(
        ScoreComponent(
            name=name,
            score=Decimal(score),
            weight=DEFAULT_COMPONENT_WEIGHTS[name],
            provenance=(f"component:{name.value}",),
        )
        for name in ScoreComponentName
    )


def test_complete_high_score_is_candidate_and_not_a_probability() -> None:
    result = SetupScoringService().score(_signal(), _components())

    assert result.recommendation is ScannerRecommendation.CANDIDATE
    assert result.ranking_score == Decimal("80.00")
    assert result.score_semantics == "ranking_not_probability"
    assert "not a probability" in result.commentary
    assert "source:fixture" in result.provenance


def test_missing_context_forces_no_trade_without_numeric_score() -> None:
    components = tuple(
        component for component in _components() if component.name is not ScoreComponentName.CONTEXT
    )

    result = SetupScoringService().score(_signal(), components)

    assert result.recommendation is ScannerRecommendation.NO_TRADE
    assert result.ranking_score is None
    assert "MISSING_CONTEXT" in result.reason_codes


@pytest.mark.parametrize(
    ("band", "expected"),
    (
        (ScoreBand.EXCEPTIONAL, Decimal("100")),
        (ScoreBand.FAVORABLE, Decimal("75")),
        (ScoreBand.CAUTION, Decimal("50")),
        (ScoreBand.UNFAVORABLE, Decimal("0")),
        (ScoreBand.UNKNOWN, None),
    ),
)
def test_all_scanner_components_share_the_approved_ordinal_scale(band, expected) -> None:
    for name in ScoreComponentName:
        component = build_banded_score_component(
            name,
            band,
            reason_codes=(f"BAND_{band.value.upper()}",),
            provenance=("policy:human-approved-2026-11-05",),
        )

        assert component.score == expected
        assert component.band is band
        assert component.weight == DEFAULT_COMPONENT_WEIGHTS[name]


def test_banded_component_rejects_a_value_outside_its_band() -> None:
    with pytest.raises(ValueError, match="approved scanner scale"):
        ScoreComponent(
            name=ScoreComponentName.TECHNICAL,
            score=Decimal("80"),
            weight=Decimal("30"),
            band=ScoreBand.FAVORABLE,
        )


def test_warming_signal_forces_no_trade() -> None:
    result = SetupScoringService().score(
        _signal(state=DataState.WARMING_UP),
        _components("95"),
    )

    assert result.recommendation is ScannerRecommendation.NO_TRADE
    assert "WARMING_UP" in result.reason_codes


def test_component_veto_overrides_high_ranking() -> None:
    components = list(_components("95"))
    context_index = next(
        index
        for index, component in enumerate(components)
        if component.name is ScoreComponentName.CONTEXT
    )
    components[context_index] = replace(components[context_index], veto=True)

    result = SetupScoringService().score(_signal(), components)

    assert result.ranking_score == Decimal("95.00")
    assert result.recommendation is ScannerRecommendation.NO_TRADE
    assert "COMPONENT_VETO" in result.reason_codes


def test_ranking_order_is_deterministic() -> None:
    service = SetupScoringService()
    watch_b = service.score(_signal("B", instrument_id="B"), _components("60"))
    candidate = service.score(_signal("C", instrument_id="C"), _components("80"))
    watch_a = service.score(_signal("A", instrument_id="A"), _components("60"))

    ranked = service.rank((watch_b, candidate, watch_a))

    assert [result.signal_id for result in ranked] == ["C", "A", "B"]


class _FixtureStrategy:
    def __init__(self, strategy_id: str) -> None:
        self.strategy_id = strategy_id

    def evaluate(self, indicator_input: IndicatorInput) -> StrategySignal:
        return _signal(self.strategy_id, instrument_id=indicator_input.instrument_id)


def test_strategy_registry_is_ordered_and_rejects_duplicates() -> None:
    registry = StrategyRegistry()
    registry.register(_FixtureStrategy("z-last"))
    registry.register(_FixtureStrategy("a-first"))
    indicator_input = IndicatorInput("SYNTHETIC", "M1", "fixture", "mid", ())

    signals = registry.evaluate(indicator_input)

    assert [signal.signal_id for signal in signals] == ["a-first", "z-last"]
    with pytest.raises(ValueError, match="already registered"):
        registry.register(_FixtureStrategy("a-first"))


def test_strategy_consensus_keeps_contradictory_signals_visible() -> None:
    consensus = build_consensus(
        (
            _signal("BUY", side=SignalSide.BUY),
            _signal("SELL", side=SignalSide.SELL),
        )
    )

    assert consensus.status is ConsensusStatus.DIVERGENT
    assert consensus.reason_codes == ("CONTRADICTORY_BUY_SELL",)
    assert [signal.signal_id for signal in consensus.signals] == ["BUY", "SELL"]


def test_thresholds_are_configurable_but_bounded() -> None:
    result = SetupScoringService(
        candidate_threshold=Decimal("90"),
        watch_threshold=Decimal("50"),
    ).score(_signal(), _components("80"))

    assert result.recommendation is ScannerRecommendation.WATCH
    with pytest.raises(ValueError, match="thresholds"):
        SetupScoringService(candidate_threshold=Decimal("50"), watch_threshold=Decimal("60"))
