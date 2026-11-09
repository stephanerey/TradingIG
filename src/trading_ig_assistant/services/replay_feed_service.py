"""Chronological, future-blind candle feed for offline replay."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from trading_ig_assistant.domain.analysis import AnalysisCandle, IndicatorInput
from trading_ig_assistant.domain.market_data import ChartCandleSeries
from trading_ig_assistant.domain.replay import (
    ReplayDataset,
    ReplayExperimentConfig,
    ReplayFrame,
)


def dataset_from_chart_series(
    series: ChartCandleSeries,
    *,
    dataset_id: str,
    dataset_version: str,
    timeframe: str,
    available_through_utc: datetime,
) -> ReplayDataset:
    if not series.sources:
        raise ValueError("replay chart series requires explicit source provenance")
    if available_through_utc.tzinfo is None or available_through_utc.utcoffset() != UTC.utcoffset(
        available_through_utc
    ):
        raise ValueError("replay availability boundary must use UTC")
    for candle in series.candles:
        if candle.timestamp.tzinfo is None or candle.timestamp.utcoffset() != UTC.utcoffset(
            candle.timestamp
        ):
            raise ValueError("replay chart candle timestamps must use UTC")
    source = "+".join(item.value for item in series.sources)
    candles = tuple(
        AnalysisCandle(
            timestamp_utc=candle.timestamp,
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
            volume=candle.volume,
            closed=True,
        )
        for candle in series.candles
        if candle.timestamp + timedelta(seconds=series.resolution_seconds) <= available_through_utc
    )
    return ReplayDataset(
        dataset_id=dataset_id,
        dataset_version=dataset_version,
        instrument_id=series.chart_source_epic,
        timeframe=timeframe,
        source=source,
        price_basis=series.price_basis.value,
        resolution_seconds=series.resolution_seconds,
        candles=candles,
    )


def build_chronological_frames(
    config: ReplayExperimentConfig,
    dataset: ReplayDataset,
    *,
    required_warmup_points: int = 0,
) -> tuple[ReplayFrame, ...]:
    if required_warmup_points < 0:
        raise ValueError("replay warmup points must not be negative")
    if config.dataset_id != dataset.dataset_id or config.dataset_version != dataset.dataset_version:
        raise ValueError("replay experiment and dataset provenance do not match")

    frames = []
    for index in range(len(dataset.candles)):
        visible_candles = dataset.candles[: index + 1]
        frames.append(
            ReplayFrame(
                dataset_id=dataset.dataset_id,
                dataset_version=dataset.dataset_version,
                sequence_number=index + 1,
                required_warmup_points=required_warmup_points,
                resolution_seconds=dataset.resolution_seconds,
                indicator_input=IndicatorInput(
                    instrument_id=dataset.instrument_id,
                    timeframe=dataset.timeframe,
                    source=dataset.source,
                    price_basis=dataset.price_basis,
                    candles=visible_candles,
                ),
            )
        )
    return tuple(frames)
