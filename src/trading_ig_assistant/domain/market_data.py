"""Market-data domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

QUOTE_FRESHNESS_SECONDS = 30


class ChartPriceBasis(StrEnum):
    BID = "bid"
    MID = "mid"
    ASK = "ask"


class CandleSource(StrEnum):
    REST = "REST"
    CACHE = "CACHE"
    STREAM = "STREAM"


@dataclass(frozen=True)
class Candle:
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal | None = None


@dataclass(frozen=True)
class PriceSeries:
    epic: str
    prices: list[dict[str, Any]]
    raw: dict[str, Any] = field(default_factory=dict, repr=False)


@dataclass(frozen=True)
class Quote:
    epic: str
    bid: float | None = None
    offer: float | None = None
    net_change: float | None = None
    percent_change: float | None = None
    market_state: str | None = None
    timestamp_ms: int | None = None
    snapshot: bool = False
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def delayed(self) -> bool | None:
        """Return the IG delay flag when explicitly supplied; absence remains unknown."""
        for key in ("DELAY", "MARKET_DELAY"):
            value = self.raw.get(key)
            if value is None or value == "":
                continue
            normalized = str(value).strip().lower()
            if normalized in {"1", "true"}:
                return True
            if normalized in {"0", "false"}:
                return False
            return None
        return None


@dataclass(frozen=True)
class ChartCandleUpdate:
    epic: str
    interval: str
    timestamp_ms: int | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: float | None = None
    tick_count: int | None = None
    end_of_candle: bool = False
    snapshot: bool = False
    raw: dict[str, Any] = field(default_factory=dict, repr=False)


@dataclass(frozen=True)
class ChartCandleSeries:
    selected_product_epic: str
    chart_source_epic: str
    resolution_seconds: int
    price_basis: ChartPriceBasis
    candles: tuple[Candle, ...] = ()
    sources: tuple[CandleSource, ...] = ()
