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
from trading_ig_assistant.services.candle_aggregation_service import (
    CandleAggregationService,
    chart_update_ohlc,
)


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
        self._session_m1_candles: dict[
            tuple[str, str, str, ChartPriceBasis],
            tuple[Candle, ...],
        ] = {}

    @property
    def current_series(self) -> ChartCandleSeries | None:
        return self._current_series

    def reset_active_series(self) -> None:
        """Drop the in-memory merge base without deleting any persisted diagnostics."""
        self._current_series = None

    def session_series(
        self,
        *,
        environment: IGEnvironment,
        account_id: str | None,
        selected_product_epic: str,
        chart_source_epic: str,
        resolution_seconds: int,
        price_basis: ChartPriceBasis,
    ) -> ChartCandleSeries:
        """Project the current process' canonical M1 observations into one timeframe."""
        if resolution_seconds < 60 or resolution_seconds % 60:
            raise ValueError("session candle resolution must be a whole number of minutes")
        key = _session_key(
            environment=environment,
            account_id=account_id,
            chart_source_epic=chart_source_epic,
            price_basis=price_basis,
        )
        canonical = self._session_m1_candles.get(key, ())
        candles = _aggregate_session_candles(
            canonical,
            target_interval_seconds=resolution_seconds,
        )
        self._current_series = ChartCandleSeries(
            selected_product_epic=selected_product_epic,
            chart_source_epic=chart_source_epic,
            resolution_seconds=resolution_seconds,
            price_basis=price_basis,
            candles=candles,
            sources=(CandleSource.STREAM,) if candles else (),
        )
        return self._current_series

    def apply_session_m1_update(
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
        """Retain one session-only M1 update and rebuild the requested chart timeframe.

        All three price bases are retained in memory from the same broker update so changing the
        displayed basis does not discard observations already received during this process. No
        persisted cache is read or written by this path.
        """
        if _chart_interval_seconds(chart_update.interval) != 60:
            raise ValueError("session candle accumulation requires a 1MINUTE stream")
        if chart_update.timestamp_ms is None:
            return self.session_series(
                environment=environment,
                account_id=account_id,
                selected_product_epic=selected_product_epic,
                chart_source_epic=chart_source_epic,
                resolution_seconds=resolution_seconds,
                price_basis=price_basis,
            )
        timestamp = datetime.fromtimestamp(
            _bucket_timestamp_ms(chart_update.timestamp_ms, 60) / 1000,
            tz=UTC,
        )
        for basis in ChartPriceBasis:
            raw_ohlc = chart_update_ohlc(chart_update, price_basis=basis)
            if raw_ohlc is None:
                continue
            open_value, high_value, low_value, close_value = raw_ohlc
            candle = Candle(
                timestamp=timestamp,
                open=Decimal(str(open_value)),
                high=Decimal(str(high_value)),
                low=Decimal(str(low_value)),
                close=Decimal(str(close_value)),
                volume=(
                    Decimal(str(chart_update.volume)) if chart_update.volume is not None else None
                ),
            )
            key = _session_key(
                environment=environment,
                account_id=account_id,
                chart_source_epic=chart_source_epic,
                price_basis=basis,
            )
            self._session_m1_candles[key] = _merge_candles(
                self._session_m1_candles.get(key, ()),
                (candle,),
                prefer_incoming=True,
            )
        return self.session_series(
            environment=environment,
            account_id=account_id,
            selected_product_epic=selected_product_epic,
            chart_source_epic=chart_source_epic,
            resolution_seconds=resolution_seconds,
            price_basis=price_basis,
        )

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
        cache_path = _stream_cache_path(
            environment=environment,
            account_id=account_id,
            chart_source_epic=chart_source_epic,
            resolution_seconds=resolution_seconds,
            price_basis=price_basis,
            cache_root_provider=self._cache_root_provider,
        )
        canonical_path = _stream_cache_path(
            environment=environment,
            account_id=account_id,
            chart_source_epic=chart_source_epic,
            resolution_seconds=60,
            price_basis=price_basis,
            cache_root_provider=self._cache_root_provider,
        )
        if not cache_path.exists() and (resolution_seconds <= 60 or not canonical_path.exists()):
            return None
        series = self.activate_series(
            selected_product_epic=selected_product_epic,
            chart_source_epic=chart_source_epic,
            resolution_seconds=resolution_seconds,
            price_basis=price_basis,
        )
        candles = _load_stream_candles(cache_path)
        if resolution_seconds > 60 and canonical_path.exists():
            canonical = _load_stream_candles(canonical_path)
            locally_aggregated = _aggregate_complete_candles(
                canonical,
                source_interval_seconds=60,
                target_interval_seconds=resolution_seconds,
            )
            candles = _merge_candles(candles, locally_aggregated, prefer_incoming=True)
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
            cache_path=cache_path if cache_path.exists() else canonical_path,
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
        # A restored REST cache may be older than a candle already revised by the
        # stream cache.  Only a live stream update is allowed to replace an
        # existing timestamp; cached/history data fills gaps without regressing it.
        prefer_incoming = source == CandleSource.STREAM
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
        source_interval_seconds = _chart_interval_seconds(chart_update.interval)
        if (
            chart_update.end_of_candle
            and chart_update.timestamp_ms is not None
            and source_interval_seconds == 60
            and resolution_seconds > 60
        ):
            raw_ohlc = chart_update_ohlc(chart_update, price_basis=price_basis)
            if raw_ohlc is not None:
                raw_open, raw_high, raw_low, raw_close = raw_ohlc
                self._persist_candle(
                    environment=environment,
                    account_id=account_id,
                    chart_source_epic=chart_source_epic,
                    resolution_seconds=60,
                    price_basis=price_basis,
                    candle=Candle(
                        timestamp=datetime.fromtimestamp(
                            _bucket_timestamp_ms(chart_update.timestamp_ms, 60) / 1000,
                            tz=UTC,
                        ),
                        open=Decimal(str(raw_open)),
                        high=Decimal(str(raw_high)),
                        low=Decimal(str(raw_low)),
                        close=Decimal(str(raw_close)),
                        volume=(
                            Decimal(str(chart_update.volume))
                            if chart_update.volume is not None
                            else None
                        ),
                    ),
                )
        if (
            chart_update.end_of_candle
            and chart_update.timestamp_ms is not None
            and _target_bucket_is_closed(
                chart_update.timestamp_ms,
                source_interval_seconds=source_interval_seconds,
                target_interval_seconds=resolution_seconds,
            )
        ):
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
        self._persist_candle(
            environment=environment,
            account_id=account_id,
            chart_source_epic=chart_source_epic,
            resolution_seconds=resolution_seconds,
            price_basis=price_basis,
            candle=closed_candle,
        )

    def _persist_candle(
        self,
        *,
        environment: IGEnvironment,
        account_id: str | None,
        chart_source_epic: str,
        resolution_seconds: int,
        price_basis: ChartPriceBasis,
        candle: Candle,
    ) -> None:
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
                "timestamp": candle.timestamp.isoformat(),
                "open": str(candle.open),
                "high": str(candle.high),
                "low": str(candle.low),
                "close": str(candle.close),
                "volume": str(candle.volume) if candle.volume is not None else None,
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


def _chart_interval_seconds(interval: str) -> int | None:
    return {
        "1MINUTE": 60,
        "5MINUTE": 300,
        "15MINUTE": 900,
        "30MINUTE": 1800,
        "HOUR": 3600,
    }.get(interval.strip().upper())


def _target_bucket_is_closed(
    timestamp_ms: int,
    *,
    source_interval_seconds: int | None,
    target_interval_seconds: int,
) -> bool:
    if source_interval_seconds is None or source_interval_seconds >= target_interval_seconds:
        return True
    target_start_ms = _bucket_timestamp_ms(timestamp_ms, target_interval_seconds)
    source_end_ms = timestamp_ms + (source_interval_seconds * 1000)
    target_end_ms = target_start_ms + (target_interval_seconds * 1000)
    return source_end_ms >= target_end_ms


def _aggregate_complete_candles(
    candles: tuple[Candle, ...],
    *,
    source_interval_seconds: int,
    target_interval_seconds: int,
) -> tuple[Candle, ...]:
    if target_interval_seconds <= source_interval_seconds:
        return candles
    if target_interval_seconds % source_interval_seconds:
        return ()
    grouped: OrderedDict[int, list[Candle]] = OrderedDict()
    for candle in sorted(candles, key=lambda item: item.timestamp):
        timestamp_ms = int(candle.timestamp.timestamp() * 1000)
        bucket_ms = _bucket_timestamp_ms(timestamp_ms, target_interval_seconds)
        grouped.setdefault(bucket_ms, []).append(candle)
    expected_count = target_interval_seconds // source_interval_seconds
    aggregated: list[Candle] = []
    for bucket_ms, group in grouped.items():
        by_timestamp = {int(item.timestamp.timestamp()): item for item in group}
        bucket_seconds = bucket_ms // 1000
        expected_timestamps = {
            bucket_seconds + (index * source_interval_seconds) for index in range(expected_count)
        }
        if set(by_timestamp) != expected_timestamps:
            continue
        ordered = [by_timestamp[timestamp] for timestamp in sorted(expected_timestamps)]
        volumes = [item.volume for item in ordered if item.volume is not None]
        aggregated.append(
            Candle(
                timestamp=datetime.fromtimestamp(bucket_seconds, tz=UTC),
                open=ordered[0].open,
                high=max(item.high for item in ordered),
                low=min(item.low for item in ordered),
                close=ordered[-1].close,
                volume=sum(volumes, Decimal("0")) if volumes else None,
            )
        )
    return tuple(aggregated)


def _aggregate_session_candles(
    candles: tuple[Candle, ...],
    *,
    target_interval_seconds: int,
) -> tuple[Candle, ...]:
    """Aggregate canonical M1 candles, retaining only the current partial target bucket.

    An older incomplete bucket is omitted rather than fabricated. Its absence creates an explicit
    chart gap once a later complete bucket exists, which keeps scanner inputs conservative.
    """
    if target_interval_seconds == 60:
        return candles
    grouped: OrderedDict[int, list[Candle]] = OrderedDict()
    for candle in sorted(candles, key=lambda item: item.timestamp):
        timestamp_ms = int(candle.timestamp.timestamp() * 1000)
        bucket_ms = _bucket_timestamp_ms(timestamp_ms, target_interval_seconds)
        grouped.setdefault(bucket_ms, []).append(candle)
    if not grouped:
        return ()
    latest_bucket_ms = next(reversed(grouped))
    expected_count = target_interval_seconds // 60
    aggregated: list[Candle] = []
    for bucket_ms, group in grouped.items():
        by_timestamp = {int(item.timestamp.timestamp()): item for item in group}
        bucket_seconds = bucket_ms // 1000
        expected_timestamps = {bucket_seconds + (index * 60) for index in range(expected_count)}
        is_complete = set(by_timestamp) == expected_timestamps
        if not is_complete and bucket_ms != latest_bucket_ms:
            continue
        ordered = [by_timestamp[timestamp] for timestamp in sorted(by_timestamp)]
        volumes = [item.volume for item in ordered if item.volume is not None]
        aggregated.append(
            Candle(
                timestamp=datetime.fromtimestamp(bucket_seconds, tz=UTC),
                open=ordered[0].open,
                high=max(item.high for item in ordered),
                low=min(item.low for item in ordered),
                close=ordered[-1].close,
                volume=sum(volumes, Decimal("0")) if volumes else None,
            )
        )
    return tuple(aggregated)


def _session_key(
    *,
    environment: IGEnvironment,
    account_id: str | None,
    chart_source_epic: str,
    price_basis: ChartPriceBasis,
) -> tuple[str, str, str, ChartPriceBasis]:
    return (
        environment.value,
        _account_marker(account_id),
        chart_source_epic,
        price_basis,
    )


def _account_marker(account_id: str | None) -> str:
    if not account_id:
        return "no-account"
    return hashlib.sha1(account_id.encode("utf-8")).hexdigest()[:12]
