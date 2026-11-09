from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from trading_ig_assistant.adapters.ig_rest import IGRestAdapter, IGSession
from trading_ig_assistant.adapters.ig_streaming import IGStreamingAdapter
from trading_ig_assistant.domain.adapter_contracts import (
    AccountIsolationError,
    AccountRef,
    BrokerCapabilities,
    BrokerCapability,
    CapabilitySupport,
    ExecutionResult,
    ExecutionStatus,
    HistoricalMarketDataProvider,
    InstrumentKind,
    InstrumentMapping,
    InstrumentMappingNotFoundError,
    InstrumentMappingRegistry,
    OrderDirection,
    OrderIntent,
    StreamingMarketDataProvider,
    UnsupportedCapabilityError,
    ensure_account_scope,
)
from trading_ig_assistant.domain.market_data import PriceSeries
from trading_ig_assistant.services.market_data_service import MarketDataService


class FakeHistoryProvider:
    def __init__(self, provider_id: str, instrument_id: str) -> None:
        self._provider_id = provider_id
        self.instrument_id = instrument_id

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def get_prices(self, instrument_id: str, **_kwargs: object) -> PriceSeries:
        assert instrument_id == self.instrument_id
        return PriceSeries(
            epic=instrument_id,
            prices=[
                {
                    "snapshotTimeUTC": "2026-10-22T10:00:00Z",
                    "openPrice": {"bid": 70.0, "offer": 70.2},
                    "highPrice": {"bid": 71.0, "offer": 71.2},
                    "lowPrice": {"bid": 69.5, "offer": 69.7},
                    "closePrice": {"bid": 70.5, "offer": 70.7},
                }
            ],
        )


class FakeStreamingProvider:
    provider_id = "fake-stream"

    def __init__(self) -> None:
        self.event_sink = None

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def subscribe_quote(self, instrument_id: str, **_kwargs: object) -> None:
        self.instrument_id = instrument_id


def _mapping(provider_id: str, instrument_id: str) -> InstrumentMapping:
    return InstrumentMapping(
        provider_id=provider_id,
        instrument_id=instrument_id,
        canonical_instrument_id="CRUDE_OIL_US",
        underlying_id="WTI",
        currency="USD",
        instrument_kind=InstrumentKind.DFB,
        unit="USD/barrel",
        quote_increment=Decimal("0.01"),
        trading_hours="provider-defined",
        timezone="UTC",
        delayed=provider_id != "ig",
        provenance=f"{provider_id} contract fixture",
    )


@pytest.mark.parametrize(
    ("provider_id", "instrument_id"),
    [("ig", "CC.D.CL.UMP.IP"), ("file", "WTI.csv")],
)
def test_market_data_service_accepts_multiple_provider_contracts(
    provider_id: str,
    instrument_id: str,
) -> None:
    provider = FakeHistoryProvider(provider_id, instrument_id)
    stream = FakeStreamingProvider()

    assert isinstance(provider, HistoricalMarketDataProvider)
    assert isinstance(stream, StreamingMarketDataProvider)

    service = MarketDataService(provider, lambda: stream)
    event = service.load_historical_candles(instrument_id, resolution="MINUTE_5")

    assert event.epic == instrument_id
    assert len(event.candles) == 1


def test_instrument_mapping_requires_provider_specific_resolution() -> None:
    registry = InstrumentMappingRegistry(
        [
            _mapping("ig", "CC.D.CL.UMP.IP"),
            _mapping("file", "WTI.csv"),
        ]
    )

    ig_mapping = registry.resolve("ig", "CC.D.CL.UMP.IP")
    file_mapping = registry.resolve("file", "WTI.csv")

    assert ig_mapping.canonical_instrument_id == file_mapping.canonical_instrument_id
    assert ig_mapping.delayed is False
    assert file_mapping.delayed is True
    assert len(registry.for_canonical_instrument("CRUDE_OIL_US")) == 2
    with pytest.raises(InstrumentMappingNotFoundError):
        registry.resolve("ig", "WTI.csv")


def test_account_scope_rejects_cross_account_operation() -> None:
    expected = AccountRef(broker_id="ig", environment="demo", account_id="ACCOUNT_A")
    other = AccountRef(broker_id="ig", environment="demo", account_id="ACCOUNT_B")

    ensure_account_scope(expected, expected)
    with pytest.raises(AccountIsolationError):
        ensure_account_scope(expected, other)


def test_unsupported_broker_capability_is_explicit() -> None:
    capabilities = BrokerCapabilities(
        discover_products=CapabilitySupport.SUPPORTED,
        read_accounts=CapabilitySupport.SUPPORTED,
    )

    capabilities.require(BrokerCapability.READ_ACCOUNTS)
    assert capabilities.support_for(BrokerCapability.PLACE_ORDERS) == (
        CapabilitySupport.UNSUPPORTED
    )
    with pytest.raises(UnsupportedCapabilityError):
        capabilities.require(BrokerCapability.PLACE_ORDERS)


def test_unknown_execution_result_requires_reconciliation() -> None:
    account = AccountRef(broker_id="fake", environment="paper", account_id="ACCOUNT_A")
    intent = OrderIntent(
        intent_id="intent-1",
        account=account,
        product_id="WTI-PAPER",
        underlying_id="WTI",
        direction=OrderDirection.BUY,
        quantity=Decimal("1"),
        requested_stop=None,
        requested_target=None,
        requested_ko=None,
        signal_id=None,
        expires_at_utc=datetime(2026, 10, 22, 18, 0, tzinfo=UTC),
    )
    result = ExecutionResult(
        intent_id=intent.intent_id,
        account=account,
        status=ExecutionStatus.UNKNOWN,
        message="synthetic timeout",
    )

    assert result.requires_reconciliation is True
    assert result.status != ExecutionStatus.CONFIRMED


def test_existing_ig_adapters_expose_market_data_provider_identity() -> None:
    rest = IGRestAdapter()
    stream = IGStreamingAdapter(
        session=IGSession(cst="fake", security_token="fake"),
        account_id="ACCOUNT_A",
    )

    assert rest.provider_id == "ig"
    assert stream.provider_id == "ig"
    assert isinstance(rest, HistoricalMarketDataProvider)
    assert isinstance(stream, StreamingMarketDataProvider)


def test_ig_capabilities_remain_explicitly_read_only_and_account_scoped() -> None:
    rest = IGRestAdapter()
    demo_account = AccountRef(broker_id="ig", environment="demo", account_id="ACCOUNT_A")

    capabilities = rest.capabilities(demo_account, "CC.D.CL.UMP.IP")

    assert capabilities.read_accounts == CapabilitySupport.SUPPORTED
    assert capabilities.place_orders == CapabilitySupport.UNSUPPORTED
    assert capabilities.live_execution == CapabilitySupport.UNSUPPORTED
    with pytest.raises(AccountIsolationError):
        rest.capabilities(
            AccountRef(broker_id="ig", environment="live", account_id="ACCOUNT_A"),
            "CC.D.CL.UMP.IP",
        )
