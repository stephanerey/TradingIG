"""Dataset fingerprinting and explicit chronological validation planning."""

from __future__ import annotations

import hashlib
import json
from datetime import timedelta
from decimal import Decimal

from trading_ig_assistant.domain.replay import ReplayDataset
from trading_ig_assistant.domain.replay_validation import (
    ReplayDatasetFingerprint,
    ReplayPartition,
    ReplayPartitionKind,
    ReplayValidationFold,
    ReplayValidationMode,
    ReplayValidationPlan,
)


def fingerprint_replay_dataset(dataset: ReplayDataset) -> ReplayDatasetFingerprint:
    payload = {
        "dataset_id": dataset.dataset_id,
        "dataset_version": dataset.dataset_version,
        "instrument_id": dataset.instrument_id,
        "timeframe": dataset.timeframe,
        "source": dataset.source,
        "price_basis": dataset.price_basis,
        "resolution_seconds": dataset.resolution_seconds,
        "candles": [
            {
                "timestamp_utc": candle.timestamp_utc.isoformat(),
                "open": _decimal_text(candle.open),
                "high": _decimal_text(candle.high),
                "low": _decimal_text(candle.low),
                "close": _decimal_text(candle.close),
                "volume": _decimal_text(candle.volume) if candle.volume is not None else None,
                "closed": candle.closed,
            }
            for candle in dataset.candles
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    resolution = timedelta(seconds=dataset.resolution_seconds)
    return ReplayDatasetFingerprint(
        dataset_id=dataset.dataset_id,
        dataset_version=dataset.dataset_version,
        sha256=hashlib.sha256(encoded).hexdigest(),
        candle_count=len(dataset.candles),
        first_available_at_utc=dataset.candles[0].timestamp_utc + resolution,
        last_available_at_utc=dataset.candles[-1].timestamp_utc + resolution,
    )


def build_chronological_validation_plan(
    dataset: ReplayDataset,
    *,
    train_points: int,
    validation_points: int,
    test_points: int,
) -> ReplayValidationPlan:
    _require_positive_sizes(train_points, validation_points, test_points)
    if train_points + validation_points + test_points != len(dataset.candles):
        raise ValueError("single-split point counts must consume the complete dataset")
    fold = _build_fold(
        dataset,
        fold_number=1,
        start_index=0,
        train_points=train_points,
        validation_points=validation_points,
        test_points=test_points,
    )
    return ReplayValidationPlan(
        mode=ReplayValidationMode.SINGLE_SPLIT,
        dataset=fingerprint_replay_dataset(dataset),
        train_points=train_points,
        validation_points=validation_points,
        test_points=test_points,
        step_points=None,
        folds=(fold,),
        unused_tail_points=0,
    )


def build_rolling_walk_forward_plan(
    dataset: ReplayDataset,
    *,
    train_points: int,
    validation_points: int,
    test_points: int,
    step_points: int,
) -> ReplayValidationPlan:
    _require_positive_sizes(train_points, validation_points, test_points)
    if step_points <= 0:
        raise ValueError("walk-forward step points must be positive")
    window_points = train_points + validation_points + test_points
    if window_points > len(dataset.candles):
        raise ValueError("walk-forward window exceeds the dataset")
    starts = range(0, len(dataset.candles) - window_points + 1, step_points)
    folds = tuple(
        _build_fold(
            dataset,
            fold_number=fold_number,
            start_index=start_index,
            train_points=train_points,
            validation_points=validation_points,
            test_points=test_points,
        )
        for fold_number, start_index in enumerate(starts, start=1)
    )
    last_consumed_index = folds[-1].test.end_index_exclusive
    return ReplayValidationPlan(
        mode=ReplayValidationMode.ROLLING_WALK_FORWARD,
        dataset=fingerprint_replay_dataset(dataset),
        train_points=train_points,
        validation_points=validation_points,
        test_points=test_points,
        step_points=step_points,
        folds=folds,
        unused_tail_points=len(dataset.candles) - last_consumed_index,
    )


def assert_plan_matches_dataset(
    plan: ReplayValidationPlan,
    dataset: ReplayDataset,
) -> None:
    if plan.dataset != fingerprint_replay_dataset(dataset):
        raise ValueError("replay validation plan does not match dataset content")


def _build_fold(
    dataset: ReplayDataset,
    *,
    fold_number: int,
    start_index: int,
    train_points: int,
    validation_points: int,
    test_points: int,
) -> ReplayValidationFold:
    train_end = start_index + train_points
    validation_end = train_end + validation_points
    test_end = validation_end + test_points
    return ReplayValidationFold(
        fold_number=fold_number,
        train=_partition(dataset, ReplayPartitionKind.TRAIN, start_index, train_end),
        validation=_partition(
            dataset,
            ReplayPartitionKind.VALIDATION,
            train_end,
            validation_end,
        ),
        test=_partition(dataset, ReplayPartitionKind.TEST, validation_end, test_end),
    )


def _partition(
    dataset: ReplayDataset,
    kind: ReplayPartitionKind,
    start_index: int,
    end_index_exclusive: int,
) -> ReplayPartition:
    resolution = timedelta(seconds=dataset.resolution_seconds)
    return ReplayPartition(
        kind=kind,
        start_index=start_index,
        end_index_exclusive=end_index_exclusive,
        first_available_at_utc=dataset.candles[start_index].timestamp_utc + resolution,
        last_available_at_utc=dataset.candles[end_index_exclusive - 1].timestamp_utc + resolution,
    )


def _require_positive_sizes(*sizes: int) -> None:
    if any(size <= 0 for size in sizes):
        raise ValueError("replay partition point counts must be positive")


def _decimal_text(value: Decimal) -> str:
    return format(value.normalize(), "f")
