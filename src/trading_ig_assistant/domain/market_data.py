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
