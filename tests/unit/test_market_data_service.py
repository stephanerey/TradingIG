from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from trading_ig_assistant.domain.market_data import (
    ChartCandleUpdate,
    ChartPriceBasis,
    PriceSeries,
    Quote,
)
from trading_ig_assistant.domain.streaming import PRICE_QUOTE_SPEC, StreamState
from trading_ig_assistant.services.candle_aggregation_service import (
    CandleAggregationService,
    chart_update_ohlc,
    live_price_for_quote,
    price_ohlc_from_payload,
)
from trading_ig_assistant.services.market_data_service import MarketDataService


class FakeRestAdapter:
    def get_prices(
        self,
        epic: str,
        *,
        resolution: str | None = None,
        max_points: int | None = None,
        start_time: object | None = None,
        end_time: object | None = None,
    ) -> PriceSeries:
        return PriceSeries(
            epic=epic,
            prices=[
                {
                    "snapshotTimeUTC": "2026-05-11T10:00:00Z",
                    "openPrice": {"bid": 10.0},
                    "highPrice": {"bid": 12.0},
                    "lowPrice": {"bid": 9.0},
                    "closePrice": {"bid": 11.0},
                }
            ],
        )


class FakeStreamingAdapter:
    def __init__(self) -> None:
        self.event_sink = None
        self.started = False
        self.stopped = False
        self.subscribed: tuple[str, str] | None = None

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True

    def subscribe_quote(self, epic: str, *, spec=PRICE_QUOTE_SPEC) -> None:
        self.subscribed = (epic, spec.name)


def test_market_data_service_loads_history_and_emits_updates() -> None:
    service = MarketDataService(FakeRestAdapter(), lambda: FakeStreamingAdapter())
    events = []
    service.add_candle_listener(events.append)

    event = service.load_historical_candles("EPIC.ONE", resolution="MINUTE")

    assert event.epic == "EPIC.ONE"
    assert len(event.candles) == 1
    assert events[0].epic == "EPIC.ONE"


def test_market_data_service_handles_stream_lifecycle_and_stale_detection() -> None:
    fake_stream = FakeStreamingAdapter()
    service = MarketDataService(
        FakeRestAdapter(),
        lambda: fake_stream,
        stale_after_seconds=2.0,
    )

    service.start_live_quotes("EPIC.ONE")
    assert fake_stream.started is True
    assert fake_stream.subscribed == ("EPIC.ONE", "PRICE")
    assert service.snapshot.stream_state == StreamState.SUBSCRIBED_WAITING_FIRST_TICK

    service.on_quote(Quote(epic="EPIC.ONE", bid=100.0, offer=101.0))
    assert service.snapshot.last_quote is not None
    assert service.current_stream_state(now_monotonic=0.0) == StreamState.LIVE

    service._last_update_monotonic = 1.0
    assert service.current_stream_state(now_monotonic=4.5) == StreamState.STALE

    service.on_chart(
        ChartCandleUpdate(
            epic="EPIC.ONE",
            interval="1MINUTE",
            timestamp_ms=1_778_493_600_000,
            open=100.0,
            high=101.0,
            low=99.5,
            close=100.5,
        )
    )
    assert service.snapshot.last_chart_update is not None
    assert len(service.snapshot.candles) == 1

    service.stop()
    assert fake_stream.stopped is True
    assert service.snapshot.stream_state == StreamState.DISCONNECTED


def test_live_price_for_quote_uses_selected_basis() -> None:
    quote = Quote(epic="EPIC.ONE", bid=100.0, offer=101.0)

    assert live_price_for_quote(quote, ChartPriceBasis.BID) == 100.0
    assert live_price_for_quote(quote, ChartPriceBasis.ASK) == 101.0
    assert live_price_for_quote(quote, ChartPriceBasis.MID) == 100.5


def test_chart_update_mid_basis_averages_bid_and_offer_fields() -> None:
    update = ChartCandleUpdate(
        epic="EPIC.ONE",
        interval="1MINUTE",
        timestamp_ms=1_778_493_600_000,
        raw={
            "BID_OPEN": "100.0",
            "BID_HIGH": "102.0",
            "BID_LOW": "99.0",
            "BID_CLOSE": "101.0",
            "OFR_OPEN": "100.4",
            "OFR_HIGH": "102.4",
            "OFR_LOW": "99.4",
            "OFR_CLOSE": "101.4",
        },
    )

    open_value, high_value, low_value, close_value = chart_update_ohlc(
        update,
        price_basis=ChartPriceBasis.MID,
    ) or (None, None, None, None)

    assert open_value == 100.2
    assert high_value == 102.2
    assert low_value == 99.2
    assert close_value == 101.2


def test_historical_price_conversion_uses_selected_basis() -> None:
    payload = {
        "openPrice": {"bid": 100.0, "offer": 100.6},
        "highPrice": {"bid": 102.0, "offer": 102.6},
        "lowPrice": {"bid": 99.0, "offer": 99.6},
        "closePrice": {"bid": 101.0, "offer": 101.6},
    }

    assert price_ohlc_from_payload(payload, ChartPriceBasis.BID) == (
        Decimal("100.0"),
        Decimal("102.0"),
        Decimal("99.0"),
        Decimal("101.0"),
    )
    assert price_ohlc_from_payload(payload, ChartPriceBasis.ASK) == (
        Decimal("100.6"),
        Decimal("102.6"),
        Decimal("99.6"),
        Decimal("101.6"),
    )
    assert price_ohlc_from_payload(payload, ChartPriceBasis.MID) == (
        Decimal("100.3"),
        Decimal("102.3"),
        Decimal("99.3"),
        Decimal("101.3"),
    )


def test_one_minute_updates_and_revisions_preserve_five_minute_ohlc() -> None:
    service = CandleAggregationService()
    candles = ()

    def timestamp_ms(minute: int) -> int:
        return int(datetime(2026, 5, 11, 10, minute, tzinfo=UTC).timestamp() * 1000)

    updates = [
        (0, 100.0, 102.0, 99.0, 101.0),
        (1, 101.0, 105.0, 100.0, 104.0),
        (2, 104.0, 106.0, 103.0, 105.0),
        (3, 105.0, 105.5, 102.0, 103.0),
        (4, 103.0, 104.0, 101.0, 102.0),
    ]
    for minute, open_value, high_value, low_value, close_value in updates:
        event = service.apply_chart_update(
            candles,
            ChartCandleUpdate(
                epic="EPIC.ONE",
                interval="1MINUTE",
                timestamp_ms=timestamp_ms(minute),
                open=open_value,
                high=high_value,
                low=low_value,
                close=close_value,
            ),
            interval_seconds=300,
        )
        candles = event.candles

    assert len(candles) == 1
    assert (candles[0].open, candles[0].high, candles[0].low, candles[0].close) == (
        Decimal("100.0"),
        Decimal("106.0"),
        Decimal("99.0"),
        Decimal("102.0"),
    )

    revised_first = service.apply_chart_update(
        candles,
        ChartCandleUpdate(
            epic="EPIC.ONE",
            interval="1MINUTE",
            timestamp_ms=timestamp_ms(0),
            open=98.0,
            high=101.0,
            low=97.0,
            close=100.0,
        ),
        interval_seconds=300,
    )
    revised_last = service.apply_chart_update(
        revised_first.candles,
        ChartCandleUpdate(
            epic="EPIC.ONE",
            interval="1MINUTE",
            timestamp_ms=timestamp_ms(4),
            open=103.0,
            high=107.0,
            low=101.0,
            close=106.0,
        ),
        interval_seconds=300,
    )

    candle = revised_last.candles[0]
    assert (candle.open, candle.high, candle.low, candle.close) == (
        Decimal("98.0"),
        Decimal("107.0"),
        Decimal("97.0"),
        Decimal("106.0"),
    )
