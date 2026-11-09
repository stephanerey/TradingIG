"""Immutable contracts for chronological replay validation plans."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class ReplayPartitionKind(StrEnum):
    TRAIN = "train"
    VALIDATION = "validation"
    TEST = "test"


class ReplayValidationMode(StrEnum):
    SINGLE_SPLIT = "single_split"
    ROLLING_WALK_FORWARD = "rolling_walk_forward"


@dataclass(frozen=True)
class ReplayDatasetFingerprint:
    dataset_id: str
    dataset_version: str
    sha256: str
    candle_count: int
    first_available_at_utc: datetime
    last_available_at_utc: datetime

    def __post_init__(self) -> None:
        if not self.dataset_id.strip() or not self.dataset_version.strip():
            raise ValueError("replay fingerprint dataset provenance is required")
        if len(self.sha256) != 64 or any(
            character not in "0123456789abcdef" for character in self.sha256
        ):
            raise ValueError("replay fingerprint must be a lowercase SHA-256 digest")
        if self.candle_count <= 0:
            raise ValueError("replay fingerprint candle count must be positive")
        _require_utc(self.first_available_at_utc, "first availability")
        _require_utc(self.last_available_at_utc, "last availability")
        if self.last_available_at_utc < self.first_available_at_utc:
            raise ValueError("replay fingerprint availability cannot move backward")


@dataclass(frozen=True)
class ReplayPartition:
    kind: ReplayPartitionKind
    start_index: int
    end_index_exclusive: int
    first_available_at_utc: datetime
    last_available_at_utc: datetime

    def __post_init__(self) -> None:
        if self.start_index < 0 or self.end_index_exclusive <= self.start_index:
            raise ValueError("replay partition indices must define a non-empty forward range")
        _require_utc(self.first_available_at_utc, "partition first availability")
        _require_utc(self.last_available_at_utc, "partition last availability")
        if self.last_available_at_utc < self.first_available_at_utc:
            raise ValueError("replay partition availability cannot move backward")

    @property
    def point_count(self) -> int:
        return self.end_index_exclusive - self.start_index


@dataclass(frozen=True)
class ReplayValidationFold:
    fold_number: int
    train: ReplayPartition
    validation: ReplayPartition
    test: ReplayPartition

    def __post_init__(self) -> None:
        if self.fold_number <= 0:
            raise ValueError("replay fold number must be positive")
        if self.train.kind is not ReplayPartitionKind.TRAIN:
            raise ValueError("replay fold train partition has the wrong kind")
        if self.validation.kind is not ReplayPartitionKind.VALIDATION:
            raise ValueError("replay fold validation partition has the wrong kind")
        if self.test.kind is not ReplayPartitionKind.TEST:
            raise ValueError("replay fold test partition has the wrong kind")
        if self.train.end_index_exclusive != self.validation.start_index:
            raise ValueError("replay train and validation partitions must be contiguous")
        if self.validation.end_index_exclusive != self.test.start_index:
            raise ValueError("replay validation and test partitions must be contiguous")
        if self.train.last_available_at_utc >= self.validation.first_available_at_utc:
            raise ValueError("replay validation must follow training chronologically")
        if self.validation.last_available_at_utc >= self.test.first_available_at_utc:
            raise ValueError("replay test must follow validation chronologically")


@dataclass(frozen=True)
class ReplayValidationPlan:
    mode: ReplayValidationMode
    dataset: ReplayDatasetFingerprint
    train_points: int
    validation_points: int
    test_points: int
    step_points: int | None
    folds: tuple[ReplayValidationFold, ...]
    unused_tail_points: int

    def __post_init__(self) -> None:
        if min(self.train_points, self.validation_points, self.test_points) <= 0:
            raise ValueError("replay validation plan point counts must be positive")
        if self.mode is ReplayValidationMode.SINGLE_SPLIT and self.step_points is not None:
            raise ValueError("single-split replay plan must not declare a step")
        if self.mode is ReplayValidationMode.ROLLING_WALK_FORWARD and (
            self.step_points is None or self.step_points <= 0
        ):
            raise ValueError("rolling replay plan requires a positive step")
        if not self.folds:
            raise ValueError("replay validation plan requires at least one fold")
        if self.unused_tail_points < 0:
            raise ValueError("replay unused tail points must not be negative")
        previous_start = None
        for expected_number, fold in enumerate(self.folds, start=1):
            if fold.fold_number != expected_number:
                raise ValueError("replay fold numbers must be consecutive")
            if (
                fold.train.point_count != self.train_points
                or fold.validation.point_count != self.validation_points
                or fold.test.point_count != self.test_points
            ):
                raise ValueError("replay fold sizes do not match plan parameters")
            if previous_start is not None and fold.train.start_index <= previous_start:
                raise ValueError("replay folds must advance chronologically")
            if (
                previous_start is not None
                and self.step_points is not None
                and fold.train.start_index - previous_start != self.step_points
            ):
                raise ValueError("replay fold advance does not match the declared step")
            previous_start = fold.train.start_index


def _require_utc(value: datetime, label: str) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"replay {label} must use UTC")
