from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from trading_ig_assistant.app.config import IGEnvironment
from trading_ig_assistant.domain.market_data import (
    CandleSource,
    ChartCandleUpdate,
    ChartPriceBasis,
    PriceSeries,
)
from trading_ig_assistant.services.candle_history_service import CandleHistoryService


def test_reset_active_series_discards_only_the_in_memory_merge_base(tmp_path) -> None:
    service = CandleHistoryService(cache_root_provider=lambda: tmp_path)
    service.activate_series(
        selected_product_epic="SELECTED",
        chart_source_epic="SOURCE",
        resolution_seconds=60,
        price_basis=ChartPriceBasis.MID,
    )

    service.reset_active_series()

    assert service.current_series is None


def test_session_m1_accumulates_and_reprojects_timeframes_without_disk(
    tmp_path: Path,
) -> None:
    service = CandleHistoryService(cache_root_provider=lambda: tmp_path)
    start = datetime(2026, 11, 5, 10, 0, tzinfo=UTC)
    latest = None
    for index in range(25):
        value = 100 + index
        latest = service.apply_session_m1_update(
            environment=IGEnvironment.LIVE,
            account_id="ACC123456",
            selected_product_epic="SELECTED",
            chart_source_epic="SOURCE",
            resolution_seconds=60,
            price_basis=ChartPriceBasis.MID,
            chart_update=ChartCandleUpdate(
                epic="SOURCE",
                interval="1MINUTE",
                timestamp_ms=int((start + timedelta(minutes=index)).timestamp() * 1000),
                end_of_candle=True,
                raw={
                    "BID_OPEN": str(value),
                    "BID_HIGH": str(value + 1),
                    "BID_LOW": str(value - 1),
                    "BID_CLOSE": str(value + 0.5),
                    "OFR_OPEN": str(value + 0.2),
                    "OFR_HIGH": str(value + 1.2),
                    "OFR_LOW": str(value - 0.8),
                    "OFR_CLOSE": str(value + 0.7),
                },
            ),
        )

    assert latest is not None
    assert len(latest.candles) == 25
    five_minute = service.session_series(
        environment=IGEnvironment.LIVE,
        account_id="ACC123456",
        selected_product_epic="SELECTED",
        chart_source_epic="SOURCE",
        resolution_seconds=300,
        price_basis=ChartPriceBasis.MID,
    )
    hourly = service.session_series(
        environment=IGEnvironment.LIVE,
        account_id="ACC123456",
        selected_product_epic="SELECTED",
        chart_source_epic="SOURCE",
        resolution_seconds=3600,
        price_basis=ChartPriceBasis.MID,
    )

    assert len(five_minute.candles) == 5
    assert five_minute.candles[0].open == Decimal("100.1")
    assert five_minute.candles[0].close == Decimal("104.6")
    assert len(hourly.candles) == 1
    assert hourly.candles[0].close == Decimal("124.6")
    assert list(tmp_path.rglob("*.jsonl")) == []


def test_session_m1_revision_and_price_basis_are_preserved_in_memory(tmp_path: Path) -> None:
    service = CandleHistoryService(cache_root_provider=lambda: tmp_path)
    timestamp_ms = int(datetime(2026, 11, 5, 10, 0, tzinfo=UTC).timestamp() * 1000)
    for close in ("100.5", "101.5"):
        service.apply_session_m1_update(
            environment=IGEnvironment.LIVE,
            account_id="ACC123456",
            selected_product_epic="SELECTED",
            chart_source_epic="SOURCE",
            resolution_seconds=60,
            price_basis=ChartPriceBasis.MID,
            chart_update=ChartCandleUpdate(
                epic="SOURCE",
                interval="1MINUTE",
                timestamp_ms=timestamp_ms,
                end_of_candle=False,
                raw={
                    "BID_OPEN": "100.0",
                    "BID_HIGH": "102.0",
                    "BID_LOW": "99.0",
                    "BID_CLOSE": close,
                    "OFR_OPEN": "100.2",
                    "OFR_HIGH": "102.2",
                    "OFR_LOW": "99.2",
                    "OFR_CLOSE": str(Decimal(close) + Decimal("0.2")),
                },
            ),
        )

    bid = service.session_series(
        environment=IGEnvironment.LIVE,
        account_id="ACC123456",
        selected_product_epic="SELECTED",
        chart_source_epic="SOURCE",
        resolution_seconds=60,
        price_basis=ChartPriceBasis.BID,
    )
    ask = service.session_series(
        environment=IGEnvironment.LIVE,
        account_id="ACC123456",
        selected_product_epic="SELECTED",
        chart_source_epic="SOURCE",
        resolution_seconds=60,
        price_basis=ChartPriceBasis.ASK,
    )

    assert len(bid.candles) == 1
    assert bid.candles[0].close == Decimal("101.5")
    assert ask.candles[0].close == Decimal("101.7")


def test_session_aggregation_omits_an_old_incomplete_bucket(tmp_path: Path) -> None:
    service = CandleHistoryService(cache_root_provider=lambda: tmp_path)
    start = datetime(2026, 11, 5, 10, 0, tzinfo=UTC)
    for index in (0, 1, 2, 3, 5, 6, 7, 8, 9):
        service.apply_session_m1_update(
            environment=IGEnvironment.LIVE,
            account_id="ACC123456",
            selected_product_epic="SELECTED",
            chart_source_epic="SOURCE",
            resolution_seconds=300,
            price_basis=ChartPriceBasis.MID,
            chart_update=ChartCandleUpdate(
                epic="SOURCE",
                interval="1MINUTE",
                timestamp_ms=int((start + timedelta(minutes=index)).timestamp() * 1000),
                end_of_candle=True,
                close=float(100 + index),
            ),
        )

    current = service.current_series
    assert current is not None
    assert tuple(candle.timestamp for candle in current.candles) == (start + timedelta(minutes=5),)


def test_stream_candle_cache_stores_completed_candles(tmp_path: Path) -> None:
    service = CandleHistoryService(cache_root_provider=lambda: tmp_path)

    service.apply_stream_update(
        environment=IGEnvironment.LIVE,
        account_id="ACC123456",
        selected_product_epic="IX.D.NASDAQ.OPTCALL2.IP",
        chart_source_epic="IX.D.NASDAQ.IFD.IP",
        resolution_seconds=300,
        price_basis=ChartPriceBasis.MID,
        chart_update=ChartCandleUpdate(
            epic="IX.D.NASDAQ.IFD.IP",
            interval="5MINUTE",
            timestamp_ms=1_778_493_600_000,
            end_of_candle=True,
            raw={
                "BID_OPEN": "100.0",
                "BID_HIGH": "101.0",
                "BID_LOW": "99.0",
                "BID_CLOSE": "100.5",
                "OFR_OPEN": "100.2",
                "OFR_HIGH": "101.2",
                "OFR_LOW": "99.2",
                "OFR_CLOSE": "100.7",
            },
        ),
    )

    files = list(tmp_path.rglob("*.jsonl"))
    assert len(files) == 1
    text = files[0].read_text(encoding="utf-8")
    assert "ACC123456" not in text
    assert "IX.D.NASDAQ.IFD.IP" in text


def test_stream_candle_cache_loads_candles_on_startup(tmp_path: Path) -> None:
    service = CandleHistoryService(cache_root_provider=lambda: tmp_path)
    service.apply_stream_update(
        environment=IGEnvironment.LIVE,
        account_id="ACC123456",
        selected_product_epic="IX.D.NASDAQ.OPTCALL2.IP",
        chart_source_epic="IX.D.NASDAQ.IFD.IP",
        resolution_seconds=300,
        price_basis=ChartPriceBasis.MID,
        chart_update=ChartCandleUpdate(
            epic="IX.D.NASDAQ.IFD.IP",
            interval="5MINUTE",
            timestamp_ms=1_778_493_600_000,
            end_of_candle=True,
            raw={
                "BID_OPEN": "100.0",
                "BID_HIGH": "101.0",
                "BID_LOW": "99.0",
                "BID_CLOSE": "100.5",
                "OFR_OPEN": "100.2",
                "OFR_HIGH": "101.2",
                "OFR_LOW": "99.2",
                "OFR_CLOSE": "100.7",
            },
        ),
    )

    reloaded = CandleHistoryService(cache_root_provider=lambda: tmp_path)
    result = reloaded.load_stream_cache(
        environment=IGEnvironment.LIVE,
        account_id="ACC123456",
        selected_product_epic="IX.D.NASDAQ.OPTCALL2.IP",
        chart_source_epic="IX.D.NASDAQ.IFD.IP",
        resolution_seconds=300,
        price_basis=ChartPriceBasis.MID,
    )

    assert result is not None
    assert result.loaded_count == 1
    assert result.series.chart_source_epic == "IX.D.NASDAQ.IFD.IP"


def test_missing_stream_cache_does_not_replace_active_series(tmp_path: Path) -> None:
    service = CandleHistoryService(cache_root_provider=lambda: tmp_path)
    active = service.activate_series(
        selected_product_epic="IX.D.NASDAQ.OPTCALL2.IP",
        chart_source_epic="IX.D.NASDAQ.IFD.IP",
        resolution_seconds=300,
        price_basis=ChartPriceBasis.MID,
    )

    result = service.load_stream_cache(
        environment=IGEnvironment.LIVE,
        account_id="ACC123456",
        selected_product_epic="IX.D.NASDAQ.OPTCALL2.IP",
        chart_source_epic="IX.D.NASDAQ.OPTCALL2.IP",
        resolution_seconds=300,
        price_basis=ChartPriceBasis.MID,
    )

    assert result is None
    assert service.current_series is active
    assert service.current_series.chart_source_epic == "IX.D.NASDAQ.IFD.IP"


def test_one_minute_stream_builds_restartable_five_minute_cache(tmp_path: Path) -> None:
    service = CandleHistoryService(cache_root_provider=lambda: tmp_path)
    start = datetime(2026, 5, 11, 10, 0, tzinfo=UTC)
    for index in range(5):
        value = 100 + index
        service.apply_stream_update(
            environment=IGEnvironment.LIVE,
            account_id="ACC123456",
            selected_product_epic="IX.D.NASDAQ.OPTCALL2.IP",
            chart_source_epic="IX.D.NASDAQ.IFD.IP",
            resolution_seconds=300,
            price_basis=ChartPriceBasis.MID,
            chart_update=ChartCandleUpdate(
                epic="IX.D.NASDAQ.IFD.IP",
                interval="1MINUTE",
                timestamp_ms=int((start + timedelta(minutes=index)).timestamp() * 1000),
                end_of_candle=True,
                raw={
                    "BID_OPEN": str(value),
                    "BID_HIGH": str(value + 1),
                    "BID_LOW": str(value - 1),
                    "BID_CLOSE": str(value + 0.5),
                    "OFR_OPEN": str(value + 0.2),
                    "OFR_HIGH": str(value + 1.2),
                    "OFR_LOW": str(value - 0.8),
                    "OFR_CLOSE": str(value + 0.7),
                },
            ),
        )

    cache_files = sorted(path.name for path in tmp_path.rglob("*.jsonl"))
    assert any("__60s__" in name for name in cache_files)
    assert any("__300s__" in name for name in cache_files)

    reloaded = CandleHistoryService(cache_root_provider=lambda: tmp_path)
    result = reloaded.load_stream_cache(
        environment=IGEnvironment.LIVE,
        account_id="ACC123456",
        selected_product_epic="IX.D.NASDAQ.OPTCALL2.IP",
        chart_source_epic="IX.D.NASDAQ.IFD.IP",
        resolution_seconds=300,
        price_basis=ChartPriceBasis.MID,
    )

    assert result is not None
    assert result.loaded_count == 1
    assert len(result.series.candles) == 1
    assert result.series.candles[0].open == Decimal("100.1")
    assert result.series.candles[0].close == Decimal("104.6")


def test_canonical_series_merges_rest_and_stream_without_duplicates(tmp_path: Path) -> None:
    service = CandleHistoryService(cache_root_provider=lambda: tmp_path)
    rest_series = PriceSeries(
        epic="IX.D.NASDAQ.IFD.IP",
        prices=[
            {
                "snapshotTimeUTC": "2026-05-11T10:00:00Z",
                "openPrice": {"bid": 100.0, "offer": 100.2},
                "highPrice": {"bid": 101.0, "offer": 101.2},
                "lowPrice": {"bid": 99.0, "offer": 99.2},
                "closePrice": {"bid": 100.5, "offer": 100.7},
            }
        ],
    )
    service.merge_price_series(
        selected_product_epic="IX.D.NASDAQ.OPTCALL2.IP",
        chart_source_epic="IX.D.NASDAQ.IFD.IP",
        resolution_seconds=300,
        resolution="MINUTE_5",
        price_basis=ChartPriceBasis.MID,
        series=rest_series,
        source=CandleSource.REST,
    )

    service.apply_stream_update(
        environment=IGEnvironment.LIVE,
        account_id="ACC123456",
        selected_product_epic="IX.D.NASDAQ.OPTCALL2.IP",
        chart_source_epic="IX.D.NASDAQ.IFD.IP",
        resolution_seconds=300,
        price_basis=ChartPriceBasis.MID,
        chart_update=ChartCandleUpdate(
            epic="IX.D.NASDAQ.IFD.IP",
            interval="5MINUTE",
            timestamp_ms=1_778_493_600_000,
            end_of_candle=True,
            raw={
                "BID_OPEN": "100.0",
                "BID_HIGH": "101.5",
                "BID_LOW": "99.0",
                "BID_CLOSE": "100.8",
                "OFR_OPEN": "100.2",
                "OFR_HIGH": "101.7",
                "OFR_LOW": "99.2",
                "OFR_CLOSE": "101.0",
            },
        ),
    )

    current = service.current_series
    assert current is not None
    assert len(current.candles) == 1
    assert CandleSource.REST in current.sources
    assert CandleSource.STREAM in current.sources


def test_live_stream_update_appends_to_canonical_series(tmp_path: Path) -> None:
    service = CandleHistoryService(cache_root_provider=lambda: tmp_path)
    service.apply_stream_update(
        environment=IGEnvironment.LIVE,
        account_id="ACC123456",
        selected_product_epic="IX.D.NASDAQ.OPTCALL2.IP",
        chart_source_epic="IX.D.NASDAQ.IFD.IP",
        resolution_seconds=300,
        price_basis=ChartPriceBasis.MID,
        chart_update=ChartCandleUpdate(
            epic="IX.D.NASDAQ.IFD.IP",
            interval="5MINUTE",
            timestamp_ms=1_778_493_600_000,
            end_of_candle=True,
            raw={
                "BID_OPEN": "100.0",
                "BID_HIGH": "101.0",
                "BID_LOW": "99.0",
                "BID_CLOSE": "100.5",
                "OFR_OPEN": "100.2",
                "OFR_HIGH": "101.2",
                "OFR_LOW": "99.2",
                "OFR_CLOSE": "100.7",
            },
        ),
    )
    service.apply_stream_update(
        environment=IGEnvironment.LIVE,
        account_id="ACC123456",
        selected_product_epic="IX.D.NASDAQ.OPTCALL2.IP",
        chart_source_epic="IX.D.NASDAQ.IFD.IP",
        resolution_seconds=300,
        price_basis=ChartPriceBasis.MID,
        chart_update=ChartCandleUpdate(
            epic="IX.D.NASDAQ.IFD.IP",
            interval="5MINUTE",
            timestamp_ms=1_778_493_900_000,
            end_of_candle=True,
            raw={
                "BID_OPEN": "100.5",
                "BID_HIGH": "101.1",
                "BID_LOW": "100.0",
                "BID_CLOSE": "100.8",
                "OFR_OPEN": "100.7",
                "OFR_HIGH": "101.3",
                "OFR_LOW": "100.2",
                "OFR_CLOSE": "101.0",
            },
        ),
    )

    current = service.current_series
    assert current is not None
    assert len(current.candles) == 2


def test_stream_cache_file_does_not_store_raw_account_id(tmp_path: Path) -> None:
    service = CandleHistoryService(cache_root_provider=lambda: tmp_path)
    service.apply_stream_update(
        environment=IGEnvironment.LIVE,
        account_id="ACC123456",
        selected_product_epic="IX.D.NASDAQ.OPTCALL2.IP",
        chart_source_epic="IX.D.NASDAQ.IFD.IP",
        resolution_seconds=300,
        price_basis=ChartPriceBasis.MID,
        chart_update=ChartCandleUpdate(
            epic="IX.D.NASDAQ.IFD.IP",
            interval="5MINUTE",
            timestamp_ms=1_778_493_600_000,
            end_of_candle=True,
            raw={
                "BID_OPEN": "100.0",
                "BID_HIGH": "101.0",
                "BID_LOW": "99.0",
                "BID_CLOSE": "100.5",
                "OFR_OPEN": "100.2",
                "OFR_HIGH": "101.2",
                "OFR_LOW": "99.2",
                "OFR_CLOSE": "100.7",
            },
        ),
    )

    content = next(tmp_path.rglob("*.jsonl")).read_text(encoding="utf-8")
    assert "ACC123456" not in content
    assert datetime.fromisoformat(json_timestamp_from_content(content)).tzinfo == UTC


def json_timestamp_from_content(content: str) -> str:
    return content.split('"timestamp": "')[1].split('"')[0]
