from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from trading_ig_assistant.app.config import IGEnvironment
from trading_ig_assistant.domain.market_data import (
    CandleSource,
    ChartCandleUpdate,
    ChartPriceBasis,
    PriceSeries,
)
from trading_ig_assistant.services.candle_history_service import CandleHistoryService


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
