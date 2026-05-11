"""Candle aggregation helpers decoupled from Qt."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from trading_ig_assistant.domain.market_data import Candle, ChartCandleUpdate, PriceSeries


@dataclass(frozen=True)
class CandleSeriesUpdated:
    epic: str
    resolution: str
    candles: tuple[Candle, ...]
    source: str


class CandleAggregationService:
    def from_price_series(self, series: PriceSeries, *, resolution: str) -> CandleSeriesUpdated:
        candles: list[Candle] = []
        for price in series.prices:
            timestamp = _price_timestamp(price)
            close_price = _first_decimal(
                price,
                ["closePrice", "close", "close_price", "OFR_CLOSE", "BID_CLOSE", "bid", "offer"],
            )
            if close_price is None:
                continue
            open_price = _first_decimal(price, ["openPrice", "open", "open_price"]) or close_price
            high_price = _first_decimal(price, ["highPrice", "high", "high_price"]) or max(
                open_price,
                close_price,
            )
            low_price = _first_decimal(price, ["lowPrice", "low", "low_price"]) or min(
                open_price,
                close_price,
            )
            candles.append(
                Candle(
                    timestamp=timestamp,
                    open=open_price,
                    high=max(open_price, close_price, high_price),
                    low=min(open_price, close_price, low_price),
                    close=close_price,
                    volume=_first_decimal(price, ["volume", "volumeTraded", "LTV", "TTV"]),
                )
            )
        return CandleSeriesUpdated(
            epic=series.epic,
            resolution=resolution,
            candles=tuple(candles),
            source="rest",
        )

    def apply_chart_update(
        self,
        current: tuple[Candle, ...],
        chart_update: ChartCandleUpdate,
    ) -> CandleSeriesUpdated:
        if chart_update.timestamp_ms is None or chart_update.close is None:
            return CandleSeriesUpdated(
                epic=chart_update.epic,
                resolution=chart_update.interval,
                candles=current,
                source="stream",
            )
        timestamp = datetime.fromtimestamp(chart_update.timestamp_ms / 1000.0, tz=UTC)
        open_value = chart_update.open if chart_update.open is not None else chart_update.close
        high_value = chart_update.high if chart_update.high is not None else chart_update.close
        low_value = chart_update.low if chart_update.low is not None else chart_update.close
        candle = Candle(
            timestamp=timestamp,
            open=Decimal(str(open_value)),
            high=Decimal(str(high_value)),
            low=Decimal(str(low_value)),
            close=Decimal(str(chart_update.close)),
            volume=Decimal(str(chart_update.volume)) if chart_update.volume is not None else None,
        )
        candles = list(current)
        for index, existing in enumerate(candles):
            if existing.timestamp == candle.timestamp:
                candles[index] = candle
                break
        else:
            candles.append(candle)
            candles.sort(key=lambda item: item.timestamp)
        return CandleSeriesUpdated(
            epic=chart_update.epic,
            resolution=chart_update.interval,
            candles=tuple(candles),
            source="stream",
        )


def _price_timestamp(price: dict[str, object]) -> datetime:
    raw = price.get("snapshotTimeUTC") or price.get("snapshotTime") or price.get("UTM")
    if isinstance(raw, (int, float)):
        return datetime.fromtimestamp(float(raw) / 1000.0, tz=UTC)
    if isinstance(raw, str):
        text = raw.strip()
        for pattern in (
            "%Y/%m/%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
        ):
            try:
                return datetime.strptime(text, pattern).replace(tzinfo=UTC)
            except ValueError:
                continue
    return datetime.fromtimestamp(0, tz=UTC)


def _first_decimal(payload: dict[str, object], keys: list[str]) -> Decimal | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, dict):
            for nested_key in ("value", "price", "bid", "offer", "mid", "close"):
                if value.get(nested_key) is not None:
                    value = value.get(nested_key)
                    break
        if value in (None, ""):
            continue
        try:
            return Decimal(str(value))
        except Exception:
            continue
    return None
