"""Instrument and account domain models used by adapters and services."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Account:
    account_id: str
    account_name: str
    account_type: str | None = None
    currency: str | None = None
    balance: float | None = None
    available: float | None = None
    deposit: float | None = None
    profit_loss: float | None = None
    preferred: bool = False
    raw: dict[str, Any] = field(default_factory=dict, repr=False)


@dataclass(frozen=True)
class MarketSummary:
    epic: str
    instrument_name: str
    instrument_type: str | None = None
    expiry: str | None = None
    market_status: str | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False)


@dataclass(frozen=True)
class MarketDetails:
    epic: str
    instrument_name: str
    raw: dict[str, Any] = field(default_factory=dict, repr=False)
