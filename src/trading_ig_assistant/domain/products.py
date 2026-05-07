"""Broker-independent product discovery domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ProductType(StrEnum):
    CASH_OR_DFB = "cash_or_dfb"
    BARRIER = "barrier"
    OPTION = "option"
    UNKNOWN = "unknown"


class ProductDirection(StrEnum):
    BUY = "buy"
    SELL = "sell"
    CALL = "call"
    PUT = "put"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class TradableProduct:
    epic: str
    name: str
    product_type: ProductType
    direction: ProductDirection = ProductDirection.UNKNOWN
    instrument_type: str | None = None
    expiry: str | None = None
    currency: str | None = None
    min_size: float | None = None
    max_size: float | None = None
    lot_size: float | None = None
    status: str | None = None
    ko_level: float | None = None
    strike: float | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "epic": self.epic,
            "name": self.name,
            "product_type": self.product_type.value,
            "direction": self.direction.value,
            "instrument_type": self.instrument_type,
            "expiry": self.expiry,
            "currency": self.currency,
            "min_size": self.min_size,
            "max_size": self.max_size,
            "lot_size": self.lot_size,
            "status": self.status,
            "ko_level": self.ko_level,
            "strike": self.strike,
            "raw": self.raw,
        }
