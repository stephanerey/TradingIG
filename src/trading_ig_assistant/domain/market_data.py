"""Market-data domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any


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
