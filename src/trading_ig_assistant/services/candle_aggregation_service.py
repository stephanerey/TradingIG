"""Candle aggregation helpers decoupled from Qt."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from trading_ig_assistant.domain.market_data import (
    Candle,
    ChartCandleUpdate,
    ChartPriceBasis,
    PriceSeries,
    Quote,
)


@dataclass(frozen=True)
class CandleSeriesUpdated:
    epic: str
    resolution: str
    candles: tuple[Candle, ...]
    source: str


class CandleAggregationService:
    def from_price_series(
        self,
        series: PriceSeries,
        *,
        resolution: str,
        price_basis: ChartPriceBasis = ChartPriceBasis.MID,
    ) -> CandleSeriesUpdated:
        candles: list[Candle] = []
        for price in series.prices:
            timestamp = _price_timestamp(price)
            ohlc = price_ohlc_from_payload(price, price_basis=price_basis)
            if ohlc is None:
                continue
            open_price, high_price, low_price, close_price = ohlc
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
        *,
        price_basis: ChartPriceBasis = ChartPriceBasis.MID,
    ) -> CandleSeriesUpdated:
        ohlc = chart_update_ohlc(chart_update, price_basis=price_basis)
        if chart_update.timestamp_ms is None or ohlc is None:
            return CandleSeriesUpdated(
                epic=chart_update.epic,
                resolution=chart_update.interval,
                candles=current,
                source="stream",
            )
        timestamp = datetime.fromtimestamp(chart_update.timestamp_ms / 1000.0, tz=UTC)
        open_value, high_value, low_value, close_value = ohlc
        candle = Candle(
            timestamp=timestamp,
            open=Decimal(str(open_value)),
            high=Decimal(str(high_value)),
            low=Decimal(str(low_value)),
            close=Decimal(str(close_value)),
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


def live_price_for_quote(
    quote: Quote,
    price_basis: ChartPriceBasis = ChartPriceBasis.MID,
) -> float | None:
    return _basis_float_value(quote.bid, quote.offer, price_basis)


def price_ohlc_from_payload(
    payload: dict[str, object],
    price_basis: ChartPriceBasis = ChartPriceBasis.MID,
) -> tuple[Decimal, Decimal, Decimal, Decimal] | None:
    close_price = _basis_decimal_from_payload(
        payload,
        bid_keys=["closePrice", "close", "close_price", "BID_CLOSE", "bid"],
        ask_keys=["closePrice", "close", "close_price", "OFR_CLOSE", "offer"],
        price_basis=price_basis,
    )
    if close_price is None:
        return None
    open_price = _basis_decimal_from_payload(
        payload,
        bid_keys=["openPrice", "open", "open_price", "BID_OPEN"],
        ask_keys=["openPrice", "open", "open_price", "OFR_OPEN"],
        price_basis=price_basis,
    ) or close_price
    high_price = _basis_decimal_from_payload(
        payload,
        bid_keys=["highPrice", "high", "high_price", "BID_HIGH"],
        ask_keys=["highPrice", "high", "high_price", "OFR_HIGH"],
        price_basis=price_basis,
    ) or max(open_price, close_price)
    low_price = _basis_decimal_from_payload(
        payload,
        bid_keys=["lowPrice", "low", "low_price", "BID_LOW"],
        ask_keys=["lowPrice", "low", "low_price", "OFR_LOW"],
        price_basis=price_basis,
    ) or min(open_price, close_price)
    return (
        open_price,
        max(open_price, close_price, high_price),
        min(open_price, close_price, low_price),
        close_price,
    )


def chart_update_ohlc(
    chart_update: ChartCandleUpdate,
    price_basis: ChartPriceBasis = ChartPriceBasis.MID,
) -> tuple[float, float, float, float] | None:
    raw = chart_update.raw or {}
    close_price = _basis_float_from_payload(
        raw,
        bid_keys=["BID_CLOSE"],
        ask_keys=["OFR_CLOSE"],
        price_basis=price_basis,
    )
    if close_price is None:
        fallback_close = chart_update.close
        if fallback_close is None:
            return None
        close_price = float(fallback_close)
    open_price = _basis_float_from_payload(
        raw,
        bid_keys=["BID_OPEN"],
        ask_keys=["OFR_OPEN"],
        price_basis=price_basis,
    ) or chart_update.open
    high_price = _basis_float_from_payload(
        raw,
        bid_keys=["BID_HIGH"],
        ask_keys=["OFR_HIGH"],
        price_basis=price_basis,
    ) or chart_update.high
    low_price = _basis_float_from_payload(
        raw,
        bid_keys=["BID_LOW"],
        ask_keys=["OFR_LOW"],
        price_basis=price_basis,
    ) or chart_update.low
    open_price = open_price if open_price is not None else close_price
    high_price = high_price if high_price is not None else max(open_price, close_price)
    low_price = low_price if low_price is not None else min(open_price, close_price)
    return (
        open_price,
        max(open_price, close_price, high_price),
        min(open_price, close_price, low_price),
        close_price,
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


def _first_float(payload: dict[str, object], keys: list[str]) -> float | None:
    for key in keys:
        value = payload.get(key)
        if value in (None, ""):
            continue
        try:
            return float(str(value).replace(",", ""))
        except Exception:
            continue
    return None


def _basis_decimal_from_payload(
    payload: dict[str, object],
    *,
    bid_keys: list[str],
    ask_keys: list[str],
    price_basis: ChartPriceBasis,
) -> Decimal | None:
    bid_value = _first_decimal_side(payload, bid_keys, "bid")
    ask_value = _first_decimal_side(payload, ask_keys, "offer")
    return _basis_decimal_value(bid_value, ask_value, price_basis)


def _basis_float_from_payload(
    payload: dict[str, object],
    *,
    bid_keys: list[str],
    ask_keys: list[str],
    price_basis: ChartPriceBasis,
) -> float | None:
    bid_value = _first_float_side(payload, bid_keys, "bid")
    ask_value = _first_float_side(payload, ask_keys, "offer")
    return _basis_float_value(bid_value, ask_value, price_basis)


def _basis_decimal_value(
    bid_value: Decimal | None,
    ask_value: Decimal | None,
    price_basis: ChartPriceBasis,
) -> Decimal | None:
    if price_basis == ChartPriceBasis.BID:
        return bid_value or ask_value
    if price_basis == ChartPriceBasis.ASK:
        return ask_value or bid_value
    if bid_value is not None and ask_value is not None:
        return (bid_value + ask_value) / Decimal("2")
    return bid_value or ask_value


def _basis_float_value(
    bid_value: float | None,
    ask_value: float | None,
    price_basis: ChartPriceBasis,
) -> float | None:
    if price_basis == ChartPriceBasis.BID:
        return bid_value if bid_value is not None else ask_value
    if price_basis == ChartPriceBasis.ASK:
        return ask_value if ask_value is not None else bid_value
    if bid_value is not None and ask_value is not None:
        return (bid_value + ask_value) / 2.0
    return bid_value if bid_value is not None else ask_value


def _first_decimal_side(
    payload: dict[str, object],
    keys: list[str],
    nested_key: str,
) -> Decimal | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, dict):
            if value.get(nested_key) is not None:
                value = value.get(nested_key)
            elif value.get("value") is not None:
                value = value.get("value")
        if value in (None, ""):
            continue
        try:
            return Decimal(str(value))
        except Exception:
            continue
    return None


def _first_float_side(
    payload: dict[str, object],
    keys: list[str],
    nested_key: str,
) -> float | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, dict):
            if value.get(nested_key) is not None:
                value = value.get(nested_key)
            elif value.get("value") is not None:
                value = value.get("value")
        if value in (None, ""):
            continue
        try:
            return float(str(value).replace(",", ""))
        except Exception:
            continue
    return None
