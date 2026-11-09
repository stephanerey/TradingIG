from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from trading_ig_assistant.domain.analysis import (
    AnalysisCandle,
    DataState,
    IndicatorInput,
    SignalSide,
    StrategySignal,
)
from trading_ig_assistant.domain.replay import (
    ReplayDataset,
    ReplayExperimentConfig,
    ReplayPricePrecision,
)
from trading_ig_assistant.services.replay_strategy_service import run_strategy_replay

START = datetime(2026, 10, 23, 9, 0, tzinfo=UTC)


def _candle(index: int) -> AnalysisCandle:
    value = Decimal(100 + index)
    return AnalysisCandle(
        timestamp_utc=START + timedelta(minutes=index),
        open=value,
        high=value + Decimal("1"),
        low=value - Decimal("1"),
        close=value,
        volume=Decimal("10"),
    )


def _config() -> ReplayExperimentConfig:
    return ReplayExperimentConfig(
        experiment_id="SYNTHETIC-SIGNAL-RUN",
        dataset_id="SYNTHETIC-DATASET",
        dataset_version="fixture-v1",
        strategy_id="SYNTHETIC-STRATEGY",
        rules_version="rules-v1",
        code_revision="synthetic-revision",
        management_mode="signal-only",
        currency="EUR",
        fill_model_version="paper-fill-v1",
        price_precision=ReplayPricePrecision.MID_APPROXIMATION,
    )


def _dataset() -> ReplayDataset:
    return ReplayDataset(
        dataset_id="SYNTHETIC-DATASET",
        dataset_version="fixture-v1",
        instrument_id="SYNTHETIC-INSTRUMENT",
        timeframe="M1",
        source="fixture",
        price_basis="mid",
        resolution_seconds=60,
        candles=tuple(_candle(index) for index in range(3)),
    )


class _SyntheticStrategy:
    strategy_id = "SYNTHETIC-STRATEGY"

    def __init__(self) -> None:
        self.visible_sizes: list[int] = []

    def evaluate(self, indicator_input: IndicatorInput) -> StrategySignal:
        visible = len(indicator_input.candles)
        self.visible_sizes.append(visible)
        latest = indicator_input.candles[-1]
        state = DataState.READY if visible >= 3 else DataState.WARMING_UP
        return StrategySignal(
            signal_id=f"SYNTHETIC-SIGNAL-{visible}",
            strategy_id=self.strategy_id,
            strategy_version="rules-v1",
            instrument_id=indicator_input.instrument_id,
            side=SignalSide.FLAT,
            generated_at_utc=latest.timestamp_utc + timedelta(minutes=1),
            valid_until_utc=latest.timestamp_utc + timedelta(minutes=2),
            data_state=state,
            reason_codes=("FIXTURE_ONLY",),
            features=(("visible_points", Decimal(visible)),),
            provenance=("strategy:synthetic-fixture",),
        )


def test_strategy_runs_once_per_future_blind_frame_and_preserves_warmup() -> None:
    strategy = _SyntheticStrategy()

    evidence = run_strategy_replay(
        _config(),
        _dataset(),
        strategy,
        required_warmup_points=3,
    )

    assert strategy.visible_sizes == [1, 2, 3]
    assert [item.frame.warmup_complete for item in evidence] == [False, False, True]
    assert [item.signal.data_state for item in evidence] == [
        DataState.WARMING_UP,
        DataState.WARMING_UP,
        DataState.READY,
    ]
    assert "dataset:SYNTHETIC-DATASET" in evidence[-1].provenance
    assert "strategy:synthetic-fixture" in evidence[-1].provenance


def test_strategy_identity_mismatch_is_rejected_before_evaluation() -> None:
    strategy = _SyntheticStrategy()

    with pytest.raises(ValueError, match="strategy does not match"):
        run_strategy_replay(
            replace(_config(), strategy_id="OTHER-STRATEGY"),
            _dataset(),
            strategy,
        )

    assert strategy.visible_sizes == []


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("strategy_id", "OTHER-STRATEGY", "signal strategy"),
        ("strategy_version", "rules-v2", "signal version"),
        ("instrument_id", "OTHER-INSTRUMENT", "signal instrument"),
    ),
)
def test_signal_identity_and_version_mismatches_are_rejected(
    field: str,
    value: str,
    message: str,
) -> None:
    class MismatchedStrategy(_SyntheticStrategy):
        def evaluate(self, indicator_input: IndicatorInput) -> StrategySignal:
            signal = super().evaluate(indicator_input)
            return replace(signal, **{field: value})

    with pytest.raises(ValueError, match=message):
        run_strategy_replay(_config(), _dataset(), MismatchedStrategy())


def test_signal_cannot_predate_source_or_move_backward() -> None:
    class EarlyStrategy(_SyntheticStrategy):
        def evaluate(self, indicator_input: IndicatorInput) -> StrategySignal:
            signal = super().evaluate(indicator_input)
            return replace(
                signal,
                generated_at_utc=indicator_input.candles[-1].timestamp_utc,
            )

    with pytest.raises(ValueError, match="predates"):
        run_strategy_replay(_config(), _dataset(), EarlyStrategy())

    class BackwardStrategy(_SyntheticStrategy):
        def evaluate(self, indicator_input: IndicatorInput) -> StrategySignal:
            signal = super().evaluate(indicator_input)
            generated = START + timedelta(minutes=10)
            if len(indicator_input.candles) > 1:
                generated = indicator_input.candles[-1].timestamp_utc + timedelta(minutes=1)
            return replace(
                signal,
                generated_at_utc=generated,
                valid_until_utc=generated + timedelta(minutes=1),
            )

    with pytest.raises(ValueError, match="backward"):
        run_strategy_replay(_config(), _dataset(), BackwardStrategy())


def test_strategy_cannot_report_ready_before_required_warmup() -> None:
    class PrematureStrategy(_SyntheticStrategy):
        def evaluate(self, indicator_input: IndicatorInput) -> StrategySignal:
            return replace(super().evaluate(indicator_input), data_state=DataState.READY)

    with pytest.raises(ValueError, match="before required warmup"):
        run_strategy_replay(
            _config(),
            _dataset(),
            PrematureStrategy(),
            required_warmup_points=3,
        )


def test_duplicate_signal_ids_and_strategy_errors_are_not_hidden() -> None:
    class DuplicateStrategy(_SyntheticStrategy):
        def evaluate(self, indicator_input: IndicatorInput) -> StrategySignal:
            return replace(super().evaluate(indicator_input), signal_id="DUPLICATE")

    with pytest.raises(ValueError, match="duplicate signal ID"):
        run_strategy_replay(_config(), _dataset(), DuplicateStrategy())

    class FailingStrategy(_SyntheticStrategy):
        def evaluate(self, indicator_input: IndicatorInput) -> StrategySignal:
            raise RuntimeError("synthetic strategy failure")

    with pytest.raises(RuntimeError, match="synthetic strategy failure"):
        run_strategy_replay(_config(), _dataset(), FailingStrategy())
