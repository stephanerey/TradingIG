"""Broker and market-data contracts independent from Qt and concrete providers."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Protocol, runtime_checkable

from trading_ig_assistant.domain.market_data import PriceSeries
from trading_ig_assistant.domain.streaming import PRICE_QUOTE_SPEC, StreamSubscriptionSpec


class CapabilitySupport(StrEnum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"


class BrokerCapability(StrEnum):
    DISCOVER_PRODUCTS = "discover_products"
    READ_ACCOUNTS = "read_accounts"
    READ_POSITIONS = "read_positions"
    PLACE_ORDERS = "place_orders"
    MODIFY_STOPS = "modify_stops"
    CLOSE_POSITIONS = "close_positions"
    NATIVE_PENDING_ORDERS = "native_pending_orders"
    BARRIER_KNOCKOUTS = "barrier_knockouts"
    DEMO_EXECUTION = "demo_execution"
    LIVE_EXECUTION = "live_execution"


class UnsupportedCapabilityError(RuntimeError):
    """Raised when an adapter is asked to approximate an unsupported operation."""


class AccountIsolationError(RuntimeError):
    """Raised when a broker operation crosses its explicit account scope."""


class InstrumentMappingNotFoundError(LookupError):
    """Raised when no explicit provider-to-canonical instrument mapping exists."""


@dataclass(frozen=True)
class AccountRef:
    broker_id: str
    environment: str
    account_id: str

    def __post_init__(self) -> None:
        if not self.broker_id.strip():
            raise ValueError("broker_id is required")
        if not self.environment.strip():
            raise ValueError("environment is required")
        if not self.account_id.strip():
            raise ValueError("account_id is required")


@dataclass(frozen=True)
class BrokerCapabilities:
    discover_products: CapabilitySupport = CapabilitySupport.UNSUPPORTED
    read_accounts: CapabilitySupport = CapabilitySupport.UNSUPPORTED
    read_positions: CapabilitySupport = CapabilitySupport.UNSUPPORTED
    place_orders: CapabilitySupport = CapabilitySupport.UNSUPPORTED
    modify_stops: CapabilitySupport = CapabilitySupport.UNSUPPORTED
    close_positions: CapabilitySupport = CapabilitySupport.UNSUPPORTED
    native_pending_orders: CapabilitySupport = CapabilitySupport.UNSUPPORTED
    barrier_knockouts: CapabilitySupport = CapabilitySupport.UNSUPPORTED
    demo_execution: CapabilitySupport = CapabilitySupport.UNSUPPORTED
    live_execution: CapabilitySupport = CapabilitySupport.UNSUPPORTED

    def support_for(self, capability: BrokerCapability) -> CapabilitySupport:
        return CapabilitySupport(getattr(self, capability.value))

    def require(self, capability: BrokerCapability) -> None:
        if self.support_for(capability) == CapabilitySupport.UNSUPPORTED:
            raise UnsupportedCapabilityError(
                f"Broker capability {capability.value!r} is unsupported."
            )


class OrderDirection(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True)
class OrderIntent:
    intent_id: str
    account: AccountRef
    product_id: str
    underlying_id: str
    direction: OrderDirection
    quantity: Decimal
    requested_stop: Decimal | None
    requested_target: Decimal | None
    requested_ko: Decimal | None
    signal_id: str | None
    expires_at_utc: datetime

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.expires_at_utc.tzinfo is None:
            raise ValueError("expires_at_utc must be timezone-aware")


class ExecutionStatus(StrEnum):
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ExecutionResult:
    intent_id: str
    account: AccountRef
    status: ExecutionStatus
    broker_reference: str | None = None
    message: str | None = None

    @property
    def requires_reconciliation(self) -> bool:
        return self.status == ExecutionStatus.UNKNOWN


class InstrumentKind(StrEnum):
    CASH = "cash"
    DFB = "dfb"
    FUTURE = "future"
    BARRIER = "barrier"
    OPTION = "option"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class InstrumentMapping:
    provider_id: str
    instrument_id: str
    canonical_instrument_id: str
    underlying_id: str
    currency: str
    instrument_kind: InstrumentKind
    unit: str
    quote_increment: Decimal
    trading_hours: str
    timezone: str
    delayed: bool
    provenance: str

    def __post_init__(self) -> None:
        required = {
            "provider_id": self.provider_id,
            "instrument_id": self.instrument_id,
            "canonical_instrument_id": self.canonical_instrument_id,
            "underlying_id": self.underlying_id,
            "currency": self.currency,
            "unit": self.unit,
            "trading_hours": self.trading_hours,
            "timezone": self.timezone,
            "provenance": self.provenance,
        }
        missing = [name for name, value in required.items() if not value.strip()]
        if missing:
            raise ValueError(f"Instrument mapping fields are required: {', '.join(missing)}")
        if self.quote_increment <= 0:
            raise ValueError("quote_increment must be positive")


class InstrumentMappingRegistry:
    def __init__(self, mappings: Sequence[InstrumentMapping] = ()) -> None:
        self._by_provider_instrument: dict[tuple[str, str], InstrumentMapping] = {}
        for mapping in mappings:
            self.add(mapping)

    def add(self, mapping: InstrumentMapping) -> None:
        key = (mapping.provider_id, mapping.instrument_id)
        existing = self._by_provider_instrument.get(key)
        if existing is not None and existing != mapping:
            raise ValueError("Conflicting instrument mapping for the same provider instrument.")
        self._by_provider_instrument[key] = mapping

    def resolve(self, provider_id: str, instrument_id: str) -> InstrumentMapping:
        try:
            return self._by_provider_instrument[(provider_id, instrument_id)]
        except KeyError as exc:
            raise InstrumentMappingNotFoundError(
                "No explicit instrument mapping exists for this provider instrument."
            ) from exc

    def for_canonical_instrument(
        self,
        canonical_instrument_id: str,
    ) -> tuple[InstrumentMapping, ...]:
        return tuple(
            mapping
            for mapping in self._by_provider_instrument.values()
            if mapping.canonical_instrument_id == canonical_instrument_id
        )


def ensure_account_scope(expected: AccountRef, actual: AccountRef) -> None:
    if expected != actual:
        raise AccountIsolationError("Broker operation does not match the active account scope.")


@runtime_checkable
class HistoricalMarketDataProvider(Protocol):
    @property
    def provider_id(self) -> str:
        """Stable provider identifier used by instrument mappings."""

    def get_prices(
        self,
        instrument_id: str,
        *,
        resolution: str | None = None,
        max_points: int | None = None,
        start_time: object | None = None,
        end_time: object | None = None,
    ) -> PriceSeries:
        """Return historical provider prices for one provider instrument."""


@runtime_checkable
class StreamingMarketDataProvider(Protocol):
    @property
    def provider_id(self) -> str:
        """Stable provider identifier used by instrument mappings."""

    @property
    def event_sink(self) -> object | None:
        """Current event sink."""

    @event_sink.setter
    def event_sink(self, value: object | None) -> None:
        """Set the event sink."""

    def start(self) -> None:
        """Start streaming."""

    def stop(self) -> None:
        """Stop streaming."""

    def subscribe_quote(
        self,
        instrument_id: str,
        *,
        spec: StreamSubscriptionSpec = PRICE_QUOTE_SPEC,
    ) -> None:
        """Subscribe to one provider quote item."""


@runtime_checkable
class BrokerAdapter(Protocol):
    @property
    def broker_id(self) -> str:
        """Stable broker identifier."""

    def capabilities(self, account: AccountRef, product_id: str) -> BrokerCapabilities:
        """Return explicit capabilities for this account and product."""

    def accounts(self) -> Sequence[AccountRef]:
        """Return broker accounts."""

    def positions(self, account: AccountRef) -> Sequence[object]:
        """Return positions scoped to one explicit account."""

    def submit(self, intent: OrderIntent) -> ExecutionResult:
        """Submit an intent only when the declared capability permits it."""

    def reconcile(self, account: AccountRef, intent_id: str) -> ExecutionResult:
        """Resolve an ambiguous execution outcome before any resubmission."""

    def move_stop(
        self,
        account: AccountRef,
        position_id: str,
        stop: Decimal,
    ) -> ExecutionResult:
        """Move a stop when supported."""

    def close(self, account: AccountRef, position_id: str) -> ExecutionResult:
        """Close a position when supported."""
