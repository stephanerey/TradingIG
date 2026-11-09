"""Immutable provenance and metric contracts for deterministic Paper replay."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum

from trading_ig_assistant.domain.analysis import AnalysisCandle, IndicatorInput, StrategySignal
from trading_ig_assistant.domain.positions import PaperPosition, PaperPositionStatus


class ReplayPricePrecision(StrEnum):
    BID_ASK = "bid_ask"
    MID_APPROXIMATION = "mid_approximation"
    OHLC_APPROXIMATION = "ohlc_approximation"


@dataclass(frozen=True)
class ReplayExperimentConfig:
    experiment_id: str
    dataset_id: str
    dataset_version: str
    strategy_id: str
    rules_version: str
    code_revision: str
    management_mode: str
    currency: str
    fill_model_version: str
    price_precision: ReplayPricePrecision

    def __post_init__(self) -> None:
        values = (
            self.experiment_id,
            self.dataset_id,
            self.dataset_version,
            self.strategy_id,
            self.rules_version,
            self.code_revision,
            self.management_mode,
            self.currency,
            self.fill_model_version,
        )
        if any(not value.strip() for value in values):
            raise ValueError("replay experiment provenance fields are required")
        if len(self.currency) != 3 or self.currency != self.currency.upper():
            raise ValueError("replay experiment currency must be a three-letter uppercase code")


@dataclass(frozen=True)
class ReplayDataset:
    dataset_id: str
    dataset_version: str
    instrument_id: str
    timeframe: str
    source: str
    price_basis: str
    resolution_seconds: int
    candles: tuple[AnalysisCandle, ...]

    def __post_init__(self) -> None:
        provenance = (
            self.dataset_id,
            self.dataset_version,
            self.instrument_id,
            self.timeframe,
            self.source,
            self.price_basis,
        )
        if any(not value.strip() for value in provenance):
            raise ValueError("replay dataset provenance fields are required")
        if self.resolution_seconds <= 0:
            raise ValueError("replay dataset resolution must be positive")
        if not self.candles:
            raise ValueError("replay dataset must contain at least one candle")
        previous_timestamp = None
        for candle in self.candles:
            _require_utc(candle.timestamp_utc, "candle")
            if not candle.closed:
                raise ValueError("replay dataset requires closed candles")
            if candle.high < max(candle.open, candle.close):
                raise ValueError("replay dataset contains an invalid candle high")
            if candle.low > min(candle.open, candle.close):
                raise ValueError("replay dataset contains an invalid candle low")
            if previous_timestamp is not None and candle.timestamp_utc <= previous_timestamp:
                raise ValueError("replay dataset timestamps must be strictly increasing")
            previous_timestamp = candle.timestamp_utc


@dataclass(frozen=True)
class ReplayFrame:
    dataset_id: str
    dataset_version: str
    sequence_number: int
    required_warmup_points: int
    resolution_seconds: int
    indicator_input: IndicatorInput

    def __post_init__(self) -> None:
        if not self.dataset_id.strip() or not self.dataset_version.strip():
            raise ValueError("replay frame dataset provenance is required")
        if self.sequence_number <= 0:
            raise ValueError("replay frame sequence must be positive")
        if self.required_warmup_points < 0:
            raise ValueError("replay warmup points must not be negative")
        if self.resolution_seconds <= 0:
            raise ValueError("replay frame resolution must be positive")
        if self.sequence_number != len(self.indicator_input.candles):
            raise ValueError("replay frame sequence must match its visible candle count")

    @property
    def warmup_complete(self) -> bool:
        return self.sequence_number >= self.required_warmup_points

    @property
    def latest_source_at_utc(self) -> datetime:
        latest = self.indicator_input.candles[-1]
        return latest.timestamp_utc + timedelta(seconds=self.resolution_seconds)


@dataclass(frozen=True)
class ReplaySignalEvidence:
    frame: ReplayFrame
    signal: StrategySignal

    def __post_init__(self) -> None:
        if self.signal.instrument_id != self.frame.indicator_input.instrument_id:
            raise ValueError("replay signal instrument does not match its input frame")
        if self.signal.generated_at_utc < self.frame.latest_source_at_utc:
            raise ValueError("replay signal predates its latest available source")

    @property
    def provenance(self) -> tuple[str, ...]:
        return (
            f"dataset:{self.frame.dataset_id}",
            f"dataset_version:{self.frame.dataset_version}",
            f"sequence:{self.frame.sequence_number}",
            f"latest_source:{self.frame.latest_source_at_utc.isoformat()}",
            f"warmup_complete:{str(self.frame.warmup_complete).lower()}",
            *self.frame.indicator_input.provenance(),
            *self.signal.provenance,
        )


@dataclass(frozen=True)
class ReplayTradeEvidence:
    position: PaperPosition
    latest_source_at_utc: datetime
    decision_at_utc: datetime
    initial_risk_amount: Decimal

    def __post_init__(self) -> None:
        _require_utc(self.latest_source_at_utc, "latest source")
        _require_utc(self.decision_at_utc, "decision")
        if self.initial_risk_amount <= 0:
            raise ValueError("replay initial risk must be positive")
        if self.position.status is not PaperPositionStatus.CLOSED:
            raise ValueError("replay metrics require a closed Paper position")
        if self.position.closed_at_utc is None or self.position.realized_pnl is None:
            raise ValueError("replay closed position evidence is incomplete")
        if self.latest_source_at_utc > self.decision_at_utc:
            raise ValueError("replay look-ahead detected: source is newer than decision")
        if self.decision_at_utc > self.position.opened_at_utc:
            raise ValueError("replay decision cannot follow its simulated fill")
        if self.position.opened_at_utc >= self.position.closed_at_utc:
            raise ValueError("replay close must follow its simulated fill")


@dataclass(frozen=True)
class ReplayMetrics:
    config: ReplayExperimentConfig
    trade_count: int
    win_count: int
    loss_count: int
    flat_count: int
    net_pnl: Decimal
    total_r: Decimal
    expectancy_r: Decimal
    win_rate: Decimal
    max_drawdown: Decimal
    max_drawdown_r: Decimal


def _require_utc(value: datetime, label: str) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"replay {label} timestamp must use UTC")
