"""Build session-only M1 candles from direct product quotes.

This is a display fallback for products whose IG ``PRICE`` stream is available while the
corresponding ``CHART`` stream is not entitled.  The generated candles retain the product EPIC;
they must not be presented to the Scanner as verified underlying-market candles.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from trading_ig_assistant.domain.market_data import ChartCandleUpdate, Quote


@dataclass
class _SideState:
    open: float
    high: float
    low: float
    close: float

    def update(self, value: float) -> None:
        self.high = max(self.high, value)
        self.low = min(self.low, value)
        self.close = value


@dataclass
class _MinuteState:
    timestamp_ms: int
    bid: _SideState | None = None
    offer: _SideState | None = None
    mid: _SideState | None = None
    last_tick_ms: int = 0


class QuoteCandleFallbackService:
    """Accumulate direct quotes into independent product M1 OHLC updates."""

    def __init__(self) -> None:
        self._states: dict[tuple[str, str, str], _MinuteState] = {}

    def update(
        self,
        quote: Quote,
        *,
        observed_at_utc: datetime | None = None,
        environment: str = "",
        account_id: str = "",
    ) -> ChartCandleUpdate | None:
        if quote.bid is None and quote.offer is None:
            return None
        timestamp_ms = _usable_timestamp_ms(quote, observed_at_utc=observed_at_utc)
        minute_ms = (timestamp_ms // 60_000) * 60_000
        key = (environment, account_id, quote.epic)
        state = self._states.get(key)
        if state is not None and timestamp_ms < state.last_tick_ms:
            return None
        if state is None or state.timestamp_ms != minute_ms:
            state = _MinuteState(timestamp_ms=minute_ms)
            self._states[key] = state

        state.bid = _update_side(state.bid, quote.bid)
        state.offer = _update_side(state.offer, quote.offer)
        state.last_tick_ms = timestamp_ms
        mid = _mid_value(state.bid, state.offer, "close")
        state.mid = _update_side(state.mid, mid)
        raw = _raw_ohlc(state)
        if state.mid is None:
            return None
        return ChartCandleUpdate(
            epic=quote.epic,
            interval="1MINUTE",
            timestamp_ms=minute_ms,
            open=state.mid.open,
            high=state.mid.high,
            low=state.mid.low,
            close=state.mid.close,
            end_of_candle=False,
            snapshot=quote.snapshot,
            raw=raw,
        )


def _update_side(state: _SideState | None, value: float | None) -> _SideState | None:
    if value is None:
        return state
    numeric = float(value)
    if state is None:
        return _SideState(open=numeric, high=numeric, low=numeric, close=numeric)
    state.update(numeric)
    return state


def _raw_ohlc(state: _MinuteState) -> dict[str, float]:
    raw: dict[str, float] = {"LOCAL_QUOTE_CANDLE": 1.0}
    for prefix, side in (("BID", state.bid), ("OFR", state.offer), ("MID", state.mid)):
        if side is None:
            continue
        raw[f"{prefix}_OPEN"] = side.open
        raw[f"{prefix}_HIGH"] = side.high
        raw[f"{prefix}_LOW"] = side.low
        raw[f"{prefix}_CLOSE"] = side.close
    return raw


def _mid_value(
    bid: _SideState | None,
    offer: _SideState | None,
    field: str,
) -> float | None:
    bid_value = getattr(bid, field) if bid is not None else None
    offer_value = getattr(offer, field) if offer is not None else None
    if bid_value is not None and offer_value is not None:
        return (bid_value + offer_value) / 2.0
    return bid_value if bid_value is not None else offer_value


def _usable_timestamp_ms(quote: Quote, *, observed_at_utc: datetime | None) -> int:
    # IG normally provides epoch milliseconds in UTM.  UPDATE_TIME-style values can instead be
    # time-of-day integers, so only plausible epoch values are accepted here.
    if quote.timestamp_ms is not None and quote.timestamp_ms >= 1_000_000_000_000:
        return quote.timestamp_ms
    observed = observed_at_utc or datetime.now(UTC)
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=UTC)
    return int(observed.astimezone(UTC).timestamp() * 1000)
