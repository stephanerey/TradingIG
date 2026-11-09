from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from trading_ig_assistant.domain.analysis import AnalysisCandle
from trading_ig_assistant.domain.replay import ReplayDataset
from trading_ig_assistant.domain.replay_validation import (
    ReplayPartitionKind,
    ReplayValidationMode,
)
from trading_ig_assistant.services.replay_validation_service import (
    assert_plan_matches_dataset,
    build_chronological_validation_plan,
    build_rolling_walk_forward_plan,
    fingerprint_replay_dataset,
)

START = datetime(2026, 10, 23, 9, 0, tzinfo=UTC)


def _dataset(points: int = 10) -> ReplayDataset:
    candles = []
    for index in range(points):
        value = Decimal(100 + index)
        candles.append(
            AnalysisCandle(
                timestamp_utc=START + timedelta(minutes=index),
                open=value,
                high=value + Decimal("1"),
                low=value - Decimal("1"),
                close=value,
                volume=Decimal("10"),
            )
        )
    return ReplayDataset(
        dataset_id="SYNTHETIC-DATASET",
        dataset_version="fixture-v1",
        instrument_id="SYNTHETIC-INSTRUMENT",
        timeframe="M1",
        source="fixture",
        price_basis="mid",
        resolution_seconds=60,
        candles=tuple(candles),
    )


def test_dataset_fingerprint_is_stable_and_detects_content_or_version_changes() -> None:
    dataset = _dataset()

    first = fingerprint_replay_dataset(dataset)
    second = fingerprint_replay_dataset(dataset)
    changed_candle = replace(
        dataset.candles[0],
        close=Decimal("100.5"),
    )

    assert first == second
    assert len(first.sha256) == 64
    assert first.candle_count == 10
    assert first.first_available_at_utc == START + timedelta(minutes=1)
    assert first.last_available_at_utc == START + timedelta(minutes=10)
    assert (
        fingerprint_replay_dataset(
            replace(dataset, candles=(changed_candle, *dataset.candles[1:]))
        ).sha256
        != first.sha256
    )
    assert (
        fingerprint_replay_dataset(replace(dataset, dataset_version="fixture-v2")).sha256
        != first.sha256
    )


def test_single_split_is_exact_contiguous_and_chronological() -> None:
    plan = build_chronological_validation_plan(
        _dataset(),
        train_points=6,
        validation_points=2,
        test_points=2,
    )
    fold = plan.folds[0]

    assert plan.mode is ReplayValidationMode.SINGLE_SPLIT
    assert (plan.train_points, plan.validation_points, plan.test_points) == (6, 2, 2)
    assert plan.step_points is None
    assert plan.unused_tail_points == 0
    assert (fold.train.start_index, fold.train.end_index_exclusive) == (0, 6)
    assert (fold.validation.start_index, fold.validation.end_index_exclusive) == (6, 8)
    assert (fold.test.start_index, fold.test.end_index_exclusive) == (8, 10)
    assert fold.train.kind is ReplayPartitionKind.TRAIN
    assert fold.validation.kind is ReplayPartitionKind.VALIDATION
    assert fold.test.kind is ReplayPartitionKind.TEST
    assert fold.train.last_available_at_utc < fold.validation.first_available_at_utc
    assert fold.validation.last_available_at_utc < fold.test.first_available_at_utc


def test_single_split_requires_positive_counts_and_complete_consumption() -> None:
    dataset = _dataset()

    with pytest.raises(ValueError, match="positive"):
        build_chronological_validation_plan(
            dataset,
            train_points=0,
            validation_points=2,
            test_points=8,
        )
    with pytest.raises(ValueError, match="complete dataset"):
        build_chronological_validation_plan(
            dataset,
            train_points=5,
            validation_points=2,
            test_points=2,
        )


def test_rolling_walk_forward_plan_is_deterministic_and_reports_unused_tail() -> None:
    plan = build_rolling_walk_forward_plan(
        _dataset(11),
        train_points=4,
        validation_points=2,
        test_points=2,
        step_points=2,
    )

    assert plan.mode is ReplayValidationMode.ROLLING_WALK_FORWARD
    assert (plan.train_points, plan.validation_points, plan.test_points) == (4, 2, 2)
    assert plan.step_points == 2
    assert len(plan.folds) == 2
    assert [fold.fold_number for fold in plan.folds] == [1, 2]
    assert [fold.train.start_index for fold in plan.folds] == [0, 2]
    assert [fold.test.end_index_exclusive for fold in plan.folds] == [8, 10]
    assert plan.unused_tail_points == 1


def test_walk_forward_rejects_invalid_step_and_oversized_window() -> None:
    dataset = _dataset()

    with pytest.raises(ValueError, match="step points"):
        build_rolling_walk_forward_plan(
            dataset,
            train_points=6,
            validation_points=2,
            test_points=2,
            step_points=0,
        )
    with pytest.raises(ValueError, match="exceeds"):
        build_rolling_walk_forward_plan(
            dataset,
            train_points=8,
            validation_points=2,
            test_points=2,
            step_points=1,
        )


def test_plan_fingerprint_rejects_changed_dataset() -> None:
    dataset = _dataset()
    plan = build_chronological_validation_plan(
        dataset,
        train_points=6,
        validation_points=2,
        test_points=2,
    )

    assert_plan_matches_dataset(plan, dataset)
    with pytest.raises(ValueError, match="does not match"):
        assert_plan_matches_dataset(
            plan,
            replace(dataset, dataset_version="fixture-v2"),
        )
