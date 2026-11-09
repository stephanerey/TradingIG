from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from trading_ig_assistant.domain.analysis import AnalysisCandle
from trading_ig_assistant.domain.market_data import (
    Candle,
    CandleSource,
    ChartCandleSeries,
    ChartPriceBasis,
)
from trading_ig_assistant.domain.replay import (
    ReplayDataset,
    ReplayExperimentConfig,
    ReplayPricePrecision,
)
from trading_ig_assistant.services.replay_feed_service import (
    build_chronological_frames,
    dataset_from_chart_series,
)

START = datetime(2026, 10, 23, 9, 0, tzinfo=UTC)


def _config() -> ReplayExperimentConfig:
    return ReplayExperimentConfig(
        experiment_id="SYNTHETIC-FEED",
        dataset_id="SYNTHETIC-DATASET",
        dataset_version="fixture-v1",
        strategy_id="UNSELECTED-STRATEGY",
        rules_version="rules-v1",
        code_revision="synthetic-revision",
        management_mode="feed-only",
        currency="EUR",
        fill_model_version="paper-fill-v1",
        price_precision=ReplayPricePrecision.MID_APPROXIMATION,
    )


def _candle(index: int, close: str | None = None) -> AnalysisCandle:
    value = Decimal(close or str(100 + index))
    return AnalysisCandle(
        timestamp_utc=START + timedelta(minutes=index),
        open=value,
        high=value + Decimal("1"),
        low=value - Decimal("1"),
        close=value,
        volume=Decimal("10"),
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


def test_frames_expose_only_the_chronological_prefix_and_warmup_state() -> None:
    dataset = _dataset()

    frames = build_chronological_frames(_config(), dataset, required_warmup_points=3)

    assert [len(frame.indicator_input.candles) for frame in frames] == [1, 2, 3]
    assert [frame.warmup_complete for frame in frames] == [False, False, True]
    assert frames[0].indicator_input.candles == dataset.candles[:1]
    assert dataset.candles[1] not in frames[0].indicator_input.candles
    assert frames[-1].latest_source_at_utc == START + timedelta(minutes=3)


def test_chart_series_adapter_preserves_market_provenance_without_io() -> None:
    candle = Candle(
        timestamp=START,
        open=Decimal("100"),
        high=Decimal("102"),
        low=Decimal("99"),
        close=Decimal("101"),
        volume=Decimal("25"),
    )
    future_candle = replace(candle, timestamp=START + timedelta(minutes=1))
    series = ChartCandleSeries(
        selected_product_epic="SYNTHETIC-PRODUCT",
        chart_source_epic="SYNTHETIC-UNDERLYING",
        resolution_seconds=60,
        price_basis=ChartPriceBasis.MID,
        candles=(candle, future_candle),
        sources=(CandleSource.CACHE, CandleSource.STREAM),
    )

    dataset = dataset_from_chart_series(
        series,
        dataset_id="SYNTHETIC-DATASET",
        dataset_version="fixture-v1",
        timeframe="M1",
        available_through_utc=START + timedelta(minutes=1),
    )

    assert dataset.instrument_id == "SYNTHETIC-UNDERLYING"
    assert dataset.source == "CACHE+STREAM"
    assert dataset.price_basis == "mid"
    assert dataset.candles[0].close == Decimal("101")
    assert len(dataset.candles) == 1


def test_dataset_rejects_open_non_utc_invalid_and_non_increasing_candles() -> None:
    dataset = _dataset()

    with pytest.raises(ValueError, match="closed candles"):
        replace(dataset, candles=(replace(_candle(0), closed=False),))
    with pytest.raises(ValueError, match="UTC"):
        replace(
            dataset,
            candles=(replace(_candle(0), timestamp_utc=START.replace(tzinfo=None)),),
        )
    with pytest.raises(ValueError, match="invalid candle high"):
        replace(dataset, candles=(replace(_candle(0), high=Decimal("99")),))
    with pytest.raises(ValueError, match="strictly increasing"):
        replace(dataset, candles=(_candle(0), _candle(0)))


def test_feed_rejects_dataset_provenance_mismatch_and_negative_warmup() -> None:
    dataset = _dataset()

    with pytest.raises(ValueError, match="provenance do not match"):
        build_chronological_frames(
            replace(_config(), dataset_version="fixture-v2"),
            dataset,
        )
    with pytest.raises(ValueError, match="warmup"):
        build_chronological_frames(_config(), dataset, required_warmup_points=-1)


def test_chart_series_without_source_or_candles_is_rejected() -> None:
    empty = ChartCandleSeries(
        selected_product_epic="SYNTHETIC-PRODUCT",
        chart_source_epic="SYNTHETIC-UNDERLYING",
        resolution_seconds=60,
        price_basis=ChartPriceBasis.MID,
    )

    with pytest.raises(ValueError, match="source provenance"):
        dataset_from_chart_series(
            empty,
            dataset_id="SYNTHETIC-DATASET",
            dataset_version="fixture-v1",
            timeframe="M1",
            available_through_utc=START,
        )
    with pytest.raises(ValueError, match="at least one candle"):
        dataset_from_chart_series(
            replace(empty, sources=(CandleSource.CACHE,)),
            dataset_id="SYNTHETIC-DATASET",
            dataset_version="fixture-v1",
            timeframe="M1",
            available_through_utc=START,
        )
    with pytest.raises(ValueError, match="availability boundary must use UTC"):
        dataset_from_chart_series(
            replace(empty, sources=(CandleSource.CACHE,)),
            dataset_id="SYNTHETIC-DATASET",
            dataset_version="fixture-v1",
            timeframe="M1",
            available_through_utc=START.replace(tzinfo=None),
        )
    naive_candle = Candle(
        timestamp=START.replace(tzinfo=None),
        open=Decimal("100"),
        high=Decimal("101"),
        low=Decimal("99"),
        close=Decimal("100"),
    )
    with pytest.raises(ValueError, match="candle timestamps must use UTC"):
        dataset_from_chart_series(
            replace(
                empty,
                sources=(CandleSource.CACHE,),
                candles=(naive_candle,),
            ),
            dataset_id="SYNTHETIC-DATASET",
            dataset_version="fixture-v1",
            timeframe="M1",
            available_through_utc=START,
        )
