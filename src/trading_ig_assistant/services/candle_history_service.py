"""Canonical candle history store with local stream-cache persistence."""

from __future__ import annotations

import hashlib
import json
import re
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from trading_ig_assistant.app.config import IGEnvironment
from trading_ig_assistant.domain.market_data import (
    Candle,
    CandleSource,
    ChartCandleSeries,
    ChartCandleUpdate,
    ChartPriceBasis,
    PriceSeries,
)
from trading_ig_assistant.services.candle_aggregation_service import CandleAggregationService


@dataclass(frozen=True)
class StreamCacheLoadResult:
    series: ChartCandleSeries
    loaded_count: int
    cache_path: Path


class CandleHistoryService:
    def __init__(
        self,
        *,
        candle_aggregation_service: CandleAggregationService | None = None,
        cache_root_provider: Callable[[], Path] | None = None,
    ) -> None:
        self._aggregation_service = candle_aggregation_service or CandleAggregationService()
        self._cache_root_provider = cache_root_provider or _stream_cache_root
        self._current_series: ChartCandleSeries | None = None

    @property
    def current_series(self) -> ChartCandleSeries | None:
        return self._current_series

    def activate_series(
        self,
        *,
        selected_product_epic: str,
        chart_source_epic: str,
        resolution_seconds: int,
        price_basis: ChartPriceBasis,
    ) -> ChartCandleSeries:
        current = self._current_series
        if (
            current is not None
            and current.selected_product_epic == selected_product_epic
            and current.chart_source_epic == chart_source_epic
            and current.resolution_seconds == resolution_seconds
            and current.price_basis == price_basis
        ):
            return current
        self._current_series = ChartCandleSeries(
            selected_product_epic=selected_product_epic,
            chart_source_epic=chart_source_epic,
            resolution_seconds=resolution_seconds,
            price_basis=price_basis,
            candles=(),
            sources=(),
        )
        return self._current_series

    def load_stream_cache(
        self,
        *,
        environment: IGEnvironment,
        account_id: str | None,
        selected_product_epic: str,
        chart_source_epic: str,
        resolution_seconds: int,
        price_basis: ChartPriceBasis,
    ) -> StreamCacheLoadResult | None:
        series = self.activate_series(
            selected_product_epic=selected_product_epic,
            chart_source_epic=chart_source_epic,
            resolution_seconds=resolution_seconds,
            price_basis=price_basis,
        )
        cache_path = _stream_cache_path(
            environment=environment,
            account_id=account_id,
            chart_source_epic=chart_source_epic,
            resolution_seconds=resolution_seconds,
            price_basis=price_basis,
            cache_root_provider=self._cache_root_provider,
        )
        if not cache_path.exists():
            return None
        candles = _load_stream_candles(cache_path)
        merged = _merge_candles(series.candles, candles, prefer_incoming=True)
        self._current_series = ChartCandleSeries(
            selected_product_epic=selected_product_epic,
            chart_source_epic=chart_source_epic,
            resolution_seconds=resolution_seconds,
            price_basis=price_basis,
            candles=merged,
            sources=_merge_sources(series.sources, CandleSource.CACHE),
        )
        return StreamCacheLoadResult(
            series=self._current_series,
            loaded_count=len(candles),
            cache_path=cache_path,
        )

    def merge_price_series(
        self,
        *,
        selected_product_epic: str,
        chart_source_epic: str,
        resolution_seconds: int,
        resolution: str,
        price_basis: ChartPriceBasis,
        series: PriceSeries,
        source: CandleSource,
    ) -> ChartCandleSeries:
        self.activate_series(
            selected_product_epic=selected_product_epic,
            chart_source_epic=chart_source_epic,
            resolution_seconds=resolution_seconds,
            price_basis=price_basis,
        )
        candle_event = self._aggregation_service.from_price_series(
            series,
            resolution=resolution,
            price_basis=price_basis,
        )
        prefer_incoming = source in {CandleSource.CACHE, CandleSource.STREAM}
        merged = _merge_candles(
            self._current_series.candles if self._current_series is not None else (),
            candle_event.candles,
            prefer_incoming=prefer_incoming,
        )
        self._current_series = ChartCandleSeries(
            selected_product_epic=selected_product_epic,
            chart_source_epic=chart_source_epic,
            resolution_seconds=resolution_seconds,
            price_basis=price_basis,
            candles=merged,
            sources=_merge_sources(
                self._current_series.sources if self._current_series is not None else (),
                source,
            ),
        )
        return self._current_series

    def apply_stream_update(
        self,
        *,
        environment: IGEnvironment,
        account_id: str | None,
        selected_product_epic: str,
        chart_source_epic: str,
        resolution_seconds: int,
        price_basis: ChartPriceBasis,
        chart_update: ChartCandleUpdate,
    ) -> ChartCandleSeries:
        current = self.activate_series(
            selected_product_epic=selected_product_epic,
            chart_source_epic=chart_source_epic,
            resolution_seconds=resolution_seconds,
            price_basis=price_basis,
        )
        candle_event = self._aggregation_service.apply_chart_update(
            current.candles,
            chart_update,
            price_basis=price_basis,
            interval_seconds=resolution_seconds,
        )
        self._current_series = ChartCandleSeries(
            selected_product_epic=selected_product_epic,
            chart_source_epic=chart_source_epic,
            resolution_seconds=resolution_seconds,
            price_basis=price_basis,
            candles=candle_event.candles,
            sources=_merge_sources(current.sources, CandleSource.STREAM),
        )
        if chart_update.end_of_candle and chart_update.timestamp_ms is not None:
            self._persist_closed_candle(
                environment=environment,
                account_id=account_id,
                chart_source_epic=chart_source_epic,
                resolution_seconds=resolution_seconds,
                price_basis=price_basis,
                timestamp_ms=chart_update.timestamp_ms,
            )
        return self._current_series

    def _persist_closed_candle(
        self,
        *,
        environment: IGEnvironment,
        account_id: str | None,
        chart_source_epic: str,
        resolution_seconds: int,
        price_basis: ChartPriceBasis,
        timestamp_ms: int,
    ) -> None:
        if self._current_series is None:
            return
        bucket_ms = _bucket_timestamp_ms(timestamp_ms, resolution_seconds)
        closed_candle = None
        for candle in self._current_series.candles:
            if int(candle.timestamp.timestamp() * 1000) == bucket_ms:
                closed_candle = candle
                break
        if closed_candle is None:
            return
        cache_path = _stream_cache_path(
            environment=environment,
            account_id=account_id,
            chart_source_epic=chart_source_epic,
            resolution_seconds=resolution_seconds,
            price_basis=price_basis,
            cache_root_provider=self._cache_root_provider,
        )
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(
            {
                "saved_at": datetime.now(UTC).isoformat(),
                "environment": environment.value,
                "chart_source_epic": chart_source_epic,
                "interval_seconds": resolution_seconds,
                "price_basis": price_basis.value,
                "source": CandleSource.STREAM.value,
                "timestamp": closed_candle.timestamp.isoformat(),
                "open": str(closed_candle.open),
                "high": str(closed_candle.high),
                "low": str(closed_candle.low),
                "close": str(closed_candle.close),
                "volume": str(closed_candle.volume) if closed_candle.volume is not None else None,
            },
            sort_keys=True,
        )
        with cache_path.open("a", encoding="utf-8") as stream:
            stream.write(payload)
            stream.write("\n")


def _stream_cache_root() -> Path:
    return Path.home() / ".trading_ig_assistant" / "cache" / "stream_candles"


def _stream_cache_path(
    *,
    environment: IGEnvironment,
    account_id: str | None,
    chart_source_epic: str,
    resolution_seconds: int,
    price_basis: ChartPriceBasis,
    cache_root_provider: Callable[[], Path] | None = None,
) -> Path:
    root = (cache_root_provider or _stream_cache_root)()
    account_marker = _account_marker(account_id)
    safe_epic = re.sub(r"[^A-Za-z0-9._-]+", "_", chart_source_epic)
    file_name = f"{safe_epic}__{resolution_seconds}s__{price_basis.value}.jsonl"
    return root / environment.value / account_marker / file_name


def _load_stream_candles(cache_path: Path) -> tuple[Candle, ...]:
    if not cache_path.exists():
        return ()
    by_timestamp: OrderedDict[str, Candle] = OrderedDict()
    for line in cache_path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text:
            continue
        payload = json.loads(text)
        candle = Candle(
            timestamp=datetime.fromisoformat(payload["timestamp"]),
            open=Decimal(str(payload["open"])),
            high=Decimal(str(payload["high"])),
            low=Decimal(str(payload["low"])),
            close=Decimal(str(payload["close"])),
            volume=Decimal(str(payload["volume"])) if payload.get("volume") is not None else None,
        )
        by_timestamp[candle.timestamp.isoformat()] = candle
    candles = sorted(by_timestamp.values(), key=lambda item: item.timestamp)
    return tuple(candles)


def _merge_candles(
    existing: tuple[Candle, ...],
    incoming: tuple[Candle, ...],
    *,
    prefer_incoming: bool,
) -> tuple[Candle, ...]:
    by_timestamp: OrderedDict[str, Candle] = OrderedDict(
        (candle.timestamp.isoformat(), candle) for candle in existing
    )
    for candle in incoming:
        key = candle.timestamp.isoformat()
        if prefer_incoming or key not in by_timestamp:
            by_timestamp[key] = candle
    candles = sorted(by_timestamp.values(), key=lambda item: item.timestamp)
    return tuple(candles)


def _merge_sources(
    existing: tuple[CandleSource, ...],
    new_source: CandleSource,
) -> tuple[CandleSource, ...]:
    merged = list(existing)
    if new_source not in merged:
        merged.append(new_source)
    return tuple(merged)


def _bucket_timestamp_ms(timestamp_ms: int, interval_seconds: int) -> int:
    if interval_seconds <= 1:
        return timestamp_ms
    bucket_seconds = (timestamp_ms // 1000 // interval_seconds) * interval_seconds
    return int(bucket_seconds * 1000)


def _account_marker(account_id: str | None) -> str:
    if not account_id:
        return "no-account"
    return hashlib.sha1(account_id.encode("utf-8")).hexdigest()[:12]
