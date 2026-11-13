"""Deterministic technical-analysis and scanner contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Protocol

from trading_ig_assistant.domain.context_sources import MacroEvent


class DataState(StrEnum):
    READY = "ready"
    WARMING_UP = "warming_up"
    INVALID = "invalid"


class SignalSide(StrEnum):
    BUY = "buy"
    SELL = "sell"
    FLAT = "flat"


class StrategyId(StrEnum):
    TREND_FOLLOW = "trend_follow"
    BREAKOUT = "breakout"
    PULLBACK = "pullback"
    EVENT_DRIVEN = "event_driven"


TECHNICAL_STRATEGY_IDS: tuple[StrategyId, ...] = (
    StrategyId.TREND_FOLLOW,
    StrategyId.BREAKOUT,
    StrategyId.PULLBACK,
)


class ScoreComponentName(StrEnum):
    TECHNICAL = "technical"
    CONTEXT = "context"
    REWARD_RISK = "reward_risk"
    MARKET_RISK = "market_risk"
    EXECUTION_COST = "execution_cost"
    DATA_QUALITY = "data_quality"


class ScoreBand(StrEnum):
    """Human-approved ordinal scanner scale; values are rankings, not probabilities."""

    EXCEPTIONAL = "exceptional"
    FAVORABLE = "favorable"
    CAUTION = "caution"
    UNFAVORABLE = "unfavorable"
    UNKNOWN = "unknown"

    @property
    def score(self) -> Decimal | None:
        return {
            ScoreBand.EXCEPTIONAL: Decimal("100"),
            ScoreBand.FAVORABLE: Decimal("75"),
            ScoreBand.CAUTION: Decimal("50"),
            ScoreBand.UNFAVORABLE: Decimal("0"),
            ScoreBand.UNKNOWN: None,
        }[self]


class ScannerRecommendation(StrEnum):
    CANDIDATE = "candidate"
    WATCH = "watch"
    NO_TRADE = "no_trade"


class ConsensusStatus(StrEnum):
    ALIGNED = "aligned"
    DIVERGENT = "divergent"
    SINGLE = "single"
    NO_SIGNAL = "no_signal"


@dataclass(frozen=True)
class AnalysisCandle:
    timestamp_utc: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal | None = None
    closed: bool = True


@dataclass(frozen=True)
class IndicatorInput:
    instrument_id: str
    timeframe: str
    source: str
    price_basis: str
    candles: tuple[AnalysisCandle, ...]

    def provenance(self) -> tuple[str, ...]:
        return (
            f"instrument:{self.instrument_id}",
            f"timeframe:{self.timeframe}",
            f"source:{self.source}",
            f"price_basis:{self.price_basis}",
        )


@dataclass(frozen=True)
class IndicatorValue:
    name: str
    state: DataState
    value: Decimal | None
    required_points: int
    observed_points: int
    reason_codes: tuple[str, ...]
    provenance: tuple[str, ...]


@dataclass(frozen=True)
class IndicatorSeriesPoint:
    """One timestamped, deterministic indicator value."""

    timestamp_utc: datetime
    value: Decimal

    def __post_init__(self) -> None:
        if self.timestamp_utc.tzinfo is None or self.timestamp_utc.utcoffset() != UTC.utcoffset(
            self.timestamp_utc
        ):
            raise ValueError("indicator-series timestamps must be UTC")


@dataclass(frozen=True)
class IndicatorSeriesValue:
    """A complete indicator curve, or an explicit non-ready state without points."""

    name: str
    state: DataState
    points: tuple[IndicatorSeriesPoint, ...]
    required_points: int
    observed_points: int
    reason_codes: tuple[str, ...]
    provenance: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("indicator-series name is required")
        if self.required_points <= 0 or self.observed_points < 0:
            raise ValueError("indicator-series point counts are invalid")
        if self.state is DataState.READY and not self.points:
            raise ValueError("ready indicator-series points cannot be empty")
        if self.state is not DataState.READY and self.points:
            raise ValueError("non-ready indicator-series points must be empty")
        if any(
            current.timestamp_utc <= previous.timestamp_utc
            for previous, current in zip(self.points, self.points[1:], strict=False)
        ):
            raise ValueError("indicator-series timestamps must be strictly increasing")


@dataclass(frozen=True)
class IndicatorSeriesSetValue:
    """Several synchronized indicator curves sharing one readiness contract."""

    name: str
    state: DataState
    series: tuple[IndicatorSeriesValue, ...]
    required_points: int
    observed_points: int
    reason_codes: tuple[str, ...]
    provenance: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("indicator-series-set name is required")
        if self.required_points <= 0 or self.observed_points < 0:
            raise ValueError("indicator-series-set point counts are invalid")
        series_names = tuple(item.name for item in self.series)
        if len(set(series_names)) != len(series_names):
            raise ValueError("indicator-series-set names must be unique")
        if self.state is DataState.READY and not self.series:
            raise ValueError("ready indicator-series-set cannot be empty")
        if self.state is not DataState.READY and self.series:
            raise ValueError("non-ready indicator-series-set must be empty")
        if any(item.state is not DataState.READY for item in self.series):
            raise ValueError("indicator-series-set curves must be ready")


@dataclass(frozen=True)
class IndicatorSetValue:
    name: str
    state: DataState
    values: tuple[tuple[str, Decimal], ...]
    required_points: int
    observed_points: int
    reason_codes: tuple[str, ...]
    provenance: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("indicator-set name is required")
        if self.required_points <= 0 or self.observed_points < 0:
            raise ValueError("indicator-set point counts are invalid")
        value_names = tuple(name for name, _value in self.values)
        if any(not name.strip() for name in value_names) or len(set(value_names)) != len(
            value_names
        ):
            raise ValueError("indicator-set value names must be non-empty and unique")
        if self.state is DataState.READY and not self.values:
            raise ValueError("ready indicator-set values cannot be empty")
        if self.state is not DataState.READY and self.values:
            raise ValueError("non-ready indicator-set values must be empty")


@dataclass(frozen=True)
class StrategySignal:
    signal_id: str
    strategy_id: str
    strategy_version: str
    instrument_id: str
    side: SignalSide
    generated_at_utc: datetime
    valid_until_utc: datetime
    data_state: DataState
    reason_codes: tuple[str, ...]
    features: tuple[tuple[str, Decimal | str], ...]
    provenance: tuple[str, ...]
    entry_zone: tuple[Decimal, Decimal] | None = None
    invalidation: Decimal | None = None
    target: Decimal | None = None
    confidence_estimate: Decimal | None = None
    data_quality: Decimal | None = None

    def __post_init__(self) -> None:
        required = {
            "signal_id": self.signal_id,
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "instrument_id": self.instrument_id,
        }
        if any(not value.strip() for value in required.values()):
            raise ValueError("signal identifiers are required")
        for timestamp in (self.generated_at_utc, self.valid_until_utc):
            if timestamp.tzinfo is None or timestamp.utcoffset() != UTC.utcoffset(timestamp):
                raise ValueError("signal timestamps must use UTC")
        if self.valid_until_utc < self.generated_at_utc:
            raise ValueError("valid_until_utc cannot precede generated_at_utc")
        if self.entry_zone is not None and self.entry_zone[0] > self.entry_zone[1]:
            raise ValueError("entry_zone lower bound cannot exceed upper bound")
        for name, value in (
            ("confidence_estimate", self.confidence_estimate),
            ("data_quality", self.data_quality),
        ):
            if value is not None and not Decimal("0") <= value <= Decimal("1"):
                raise ValueError(f"{name} must be between 0 and 1")


@dataclass(frozen=True)
class EventContextAssessment:
    event: MacroEvent
    directional_side: SignalSide
    assessed_at_utc: datetime
    valid_until_utc: datetime
    source: str
    source_signal_ids: tuple[str, ...]
    confidence: Decimal | None

    def __post_init__(self) -> None:
        for timestamp in (self.assessed_at_utc, self.valid_until_utc):
            if timestamp.tzinfo is None or timestamp.utcoffset() != UTC.utcoffset(timestamp):
                raise ValueError("event-context timestamps must use UTC")
        if self.valid_until_utc <= self.assessed_at_utc:
            raise ValueError("event-context validity must follow assessment")
        if not self.source.strip():
            raise ValueError("event-context source is required")
        if not self.source_signal_ids or any(not item.strip() for item in self.source_signal_ids):
            raise ValueError("event-context source IDs are required")
        if len(set(self.source_signal_ids)) != len(self.source_signal_ids):
            raise ValueError("event-context source IDs must be unique")
        if self.event.event_id not in self.source_signal_ids:
            raise ValueError("event-context assessment must cite its macro event")
        if self.confidence is not None and not Decimal("0") <= self.confidence <= Decimal("1"):
            raise ValueError("event-context confidence must be between zero and one")


@dataclass(frozen=True)
class ScoreComponent:
    name: ScoreComponentName
    score: Decimal | None
    weight: Decimal
    reason_codes: tuple[str, ...] = ()
    provenance: tuple[str, ...] = ()
    veto: bool = False
    band: ScoreBand | None = None

    def __post_init__(self) -> None:
        if self.score is not None and not Decimal("0") <= self.score <= Decimal("100"):
            raise ValueError("component score must be between 0 and 100")
        if self.weight < 0:
            raise ValueError("component weight must not be negative")
        if self.band is not None and self.score != self.band.score:
            raise ValueError("banded component score must match the approved scanner scale")


@dataclass(frozen=True)
class ScannerResult:
    instrument_id: str
    signal_id: str
    recommendation: ScannerRecommendation
    ranking_score: Decimal | None
    components: tuple[ScoreComponent, ...]
    reason_codes: tuple[str, ...]
    commentary: str
    provenance: tuple[str, ...]
    score_semantics: str = "ranking_not_probability"


@dataclass(frozen=True)
class StrategyConsensus:
    instrument_id: str
    status: ConsensusStatus
    signals: tuple[StrategySignal, ...]
    reason_codes: tuple[str, ...]


class Strategy(Protocol):
    @property
    def strategy_id(self) -> str:
        """Return a stable strategy identifier."""

    def evaluate(self, indicator_input: IndicatorInput) -> StrategySignal:
        """Return one explicit signal or no-trade signal."""
