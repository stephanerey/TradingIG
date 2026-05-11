"""Read-only market data orchestration outside the GUI."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from trading_ig_assistant.domain.market_data import ChartCandleUpdate, PriceSeries, Quote
from trading_ig_assistant.domain.streaming import (
    PRICE_QUOTE_SPEC,
    StreamState,
    StreamSubscriptionSpec,
)
from trading_ig_assistant.services.candle_aggregation_service import (
    CandleAggregationService,
    CandleSeriesUpdated,
)


class RestMarketDataAdapter(Protocol):
    def get_prices(
        self,
        epic: str,
        *,
        resolution: str | None = None,
        max_points: int | None = None,
        start_time: object | None = None,
        end_time: object | None = None,
    ) -> PriceSeries:
        """Return historical prices."""


class StreamingMarketDataAdapter(Protocol):
    def start(self) -> None:
        """Start streaming."""

    def stop(self) -> None:
        """Stop streaming."""

    def subscribe_quote(
        self,
        epic: str,
        *,
        spec: StreamSubscriptionSpec = PRICE_QUOTE_SPEC,
    ) -> None:
        """Subscribe to a quote item."""

    @property
    def event_sink(self) -> object | None:
        """Current sink."""

    @event_sink.setter
    def event_sink(self, value: object | None) -> None:
        """Set sink."""


@dataclass
class MarketDataSnapshot:
    last_quote: Quote | None = None
    last_chart_update: ChartCandleUpdate | None = None
    candles: tuple = ()
    stream_state: StreamState = StreamState.DISCONNECTED


class MarketDataService:
    def __init__(
        self,
        rest_adapter: RestMarketDataAdapter,
        streaming_adapter_factory: Callable[[], StreamingMarketDataAdapter],
        *,
        candle_aggregation_service: CandleAggregationService | None = None,
        stale_after_seconds: float = 5.0,
    ) -> None:
        self._rest_adapter = rest_adapter
        self._streaming_adapter_factory = streaming_adapter_factory
        self._candle_service = candle_aggregation_service or CandleAggregationService()
        self._stale_after_seconds = stale_after_seconds
        self._streaming_adapter: StreamingMarketDataAdapter | None = None
        self._listeners: list[Callable[[CandleSeriesUpdated], None]] = []
        self._snapshot = MarketDataSnapshot()
        self._last_update_monotonic: float | None = None

    @property
    def snapshot(self) -> MarketDataSnapshot:
        return self._snapshot

    def add_candle_listener(self, listener: Callable[[CandleSeriesUpdated], None]) -> None:
        self._listeners.append(listener)

    def load_historical_candles(
        self,
        epic: str,
        *,
        resolution: str,
        max_points: int | None = None,
        start_time: object | None = None,
        end_time: object | None = None,
    ) -> CandleSeriesUpdated:
        series = self._rest_adapter.get_prices(
            epic,
            resolution=resolution,
            max_points=max_points,
            start_time=start_time,
            end_time=end_time,
        )
        event = self._candle_service.from_price_series(series, resolution=resolution)
        self._snapshot.candles = event.candles
        self._emit_candles(event)
        return event

    def start_live_quotes(
        self,
        epic: str,
        *,
        spec: StreamSubscriptionSpec = PRICE_QUOTE_SPEC,
    ) -> None:
        adapter = self._streaming_adapter_factory()
        adapter.event_sink = _MarketDataStreamSink(self)
        adapter.start()
        adapter.subscribe_quote(epic, spec=spec)
        self._streaming_adapter = adapter
        self._snapshot.stream_state = StreamState.SUBSCRIBED_WAITING_FIRST_TICK

    def stop(self) -> None:
        if self._streaming_adapter is not None:
            self._streaming_adapter.stop()
            self._streaming_adapter = None
        self._snapshot.stream_state = StreamState.DISCONNECTED

    def on_stream_status(self, status: str) -> None:
        normalized = status.upper()
        if normalized.startswith("CONNECTED"):
            self._snapshot.stream_state = StreamState.CONNECTED
        elif normalized.startswith("SUBSCRIBED"):
            self._snapshot.stream_state = StreamState.SUBSCRIBED_WAITING_FIRST_TICK
        elif normalized.startswith("DISCONNECTED"):
            self._snapshot.stream_state = StreamState.DISCONNECTED
        elif normalized.startswith("RECONNECTING"):
            self._snapshot.stream_state = StreamState.RECONNECTING

    def on_quote(self, quote: Quote) -> None:
        self._snapshot.last_quote = quote
        self._snapshot.stream_state = StreamState.LIVE
        self._last_update_monotonic = time.monotonic()

    def on_chart(self, chart_update: ChartCandleUpdate) -> None:
        self._snapshot.last_chart_update = chart_update
        event = self._candle_service.apply_chart_update(self._snapshot.candles, chart_update)
        self._snapshot.candles = event.candles
        self._snapshot.stream_state = StreamState.LIVE
        self._last_update_monotonic = time.monotonic()
        self._emit_candles(event)

    def on_stream_error(self, _message: str) -> None:
        self._snapshot.stream_state = StreamState.FAILED

    def current_stream_state(self, *, now_monotonic: float | None = None) -> StreamState:
        if self._snapshot.stream_state != StreamState.LIVE:
            return self._snapshot.stream_state
        if self._last_update_monotonic is None:
            return self._snapshot.stream_state
        reference = now_monotonic if now_monotonic is not None else time.monotonic()
        if reference - self._last_update_monotonic > self._stale_after_seconds:
            return StreamState.STALE
        return self._snapshot.stream_state

    def _emit_candles(self, event: CandleSeriesUpdated) -> None:
        for listener in self._listeners:
            listener(event)


class _MarketDataStreamSink:
    def __init__(self, service: MarketDataService) -> None:
        self._service = service

    def on_stream_status(self, status: str) -> None:
        self._service.on_stream_status(status)

    def on_quote(self, quote: Quote) -> None:
        self._service.on_quote(quote)

    def on_chart(self, chart_update: ChartCandleUpdate) -> None:
        self._service.on_chart(chart_update)

    def on_stream_error(self, message: str) -> None:
        self._service.on_stream_error(message)
