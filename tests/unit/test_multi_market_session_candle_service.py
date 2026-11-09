from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from trading_ig_assistant.app.config import IGEnvironment
from trading_ig_assistant.domain.market_data import ChartCandleUpdate, ChartPriceBasis
from trading_ig_assistant.domain.market_navigation import IGProductMarketBinding
from trading_ig_assistant.domain.markets import CanonicalUnderlyingId
from trading_ig_assistant.services.candle_history_service import CandleHistoryService
from trading_ig_assistant.services.market_navigation_catalog_service import (
    IGProductMarketBindingRegistry,
    MarketNavigationCatalogError,
)
from trading_ig_assistant.services.multi_market_session_candle_service import (
    MultiMarketSessionCandleService,
)

US_REFERENCE = "IX.D.NASDAQ.IFD.IP"
GOLD_REFERENCE = "CS.D.CFEGOLD.CEF.IP"
START = datetime(2026, 11, 5, 18, 0, tzinfo=UTC)


def _binding(
    product_epic: str,
    underlying: CanonicalUnderlyingId,
    reference_epic: str,
) -> IGProductMarketBinding:
    return IGProductMarketBinding(
        product_epic=product_epic,
        canonical_underlying_id=underlying,
        reference_epic=reference_epic,
        provenance=("fixture:explicit",),
    )


def _update(epic: str, minute: int, close: str) -> ChartCandleUpdate:
    close_value = Decimal(close)
    return ChartCandleUpdate(
        epic=epic,
        interval="1MINUTE",
        timestamp_ms=int((START + timedelta(minutes=minute)).timestamp() * 1000),
        end_of_candle=True,
        raw={
            "BID_OPEN": str(close_value - Decimal("0.5")),
            "BID_HIGH": str(close_value + Decimal("1")),
            "BID_LOW": str(close_value - Decimal("1")),
            "BID_CLOSE": str(close_value),
            "OFR_OPEN": str(close_value - Decimal("0.3")),
            "OFR_HIGH": str(close_value + Decimal("1.2")),
            "OFR_LOW": str(close_value - Decimal("0.8")),
            "OFR_CLOSE": str(close_value + Decimal("0.2")),
        },
    )


def _service(tmp_path) -> MultiMarketSessionCandleService:
    bindings = (
        _binding(
            "IX.D.NASDAQ.OPTCALL2.IP",
            CanonicalUnderlyingId.US_TECH_100,
            US_REFERENCE,
        ),
        _binding(
            "IX.D.NASDAQ.OPTPUT2.IP",
            CanonicalUnderlyingId.US_TECH_100,
            US_REFERENCE,
        ),
        _binding(
            "GOLD.BARRIER.CALL",
            CanonicalUnderlyingId.SPOT_GOLD,
            GOLD_REFERENCE,
        ),
    )
    return MultiMarketSessionCandleService(
        IGProductMarketBindingRegistry(bindings),
        candle_history_service=CandleHistoryService(cache_root_provider=lambda: tmp_path),
    )


def test_update_is_routed_to_products_with_the_exact_reference_only(tmp_path) -> None:
    service = _service(tmp_path)

    updated = service.ingest_m1_update(
        environment=IGEnvironment.DEMO,
        account_id="DEMO-ACCOUNT",
        chart_update=_update(US_REFERENCE, 0, "100"),
        resolution_seconds=60,
        price_basis=ChartPriceBasis.MID,
    )

    assert tuple(item.binding.product_epic for item in updated) == (
        "IX.D.NASDAQ.OPTCALL2.IP",
        "IX.D.NASDAQ.OPTPUT2.IP",
    )
    assert all(item.series.chart_source_epic == US_REFERENCE for item in updated)
    assert all(len(item.series.candles) == 1 for item in updated)
    gold = service.series_for_product(
        environment=IGEnvironment.DEMO,
        account_id="DEMO-ACCOUNT",
        product_epic="GOLD.BARRIER.CALL",
        resolution_seconds=60,
        price_basis=ChartPriceBasis.MID,
    )
    assert gold.series.candles == ()
    assert list(tmp_path.rglob("*.jsonl")) == []


def test_revisions_and_timeframe_projection_remain_isolated_by_reference(tmp_path) -> None:
    service = _service(tmp_path)
    for minute in range(5):
        service.ingest_m1_update(
            environment=IGEnvironment.DEMO,
            account_id="DEMO-ACCOUNT",
            chart_update=_update(US_REFERENCE, minute, str(100 + minute)),
            resolution_seconds=60,
            price_basis=ChartPriceBasis.MID,
        )
    service.ingest_m1_update(
        environment=IGEnvironment.DEMO,
        account_id="DEMO-ACCOUNT",
        chart_update=_update(US_REFERENCE, 4, "110"),
        resolution_seconds=60,
        price_basis=ChartPriceBasis.MID,
    )
    service.ingest_m1_update(
        environment=IGEnvironment.DEMO,
        account_id="DEMO-ACCOUNT",
        chart_update=_update(GOLD_REFERENCE, 0, "200"),
        resolution_seconds=60,
        price_basis=ChartPriceBasis.MID,
    )

    us_five = service.series_for_product(
        environment=IGEnvironment.DEMO,
        account_id="DEMO-ACCOUNT",
        product_epic="IX.D.NASDAQ.OPTCALL2.IP",
        resolution_seconds=300,
        price_basis=ChartPriceBasis.MID,
    )
    gold = service.series_for_product(
        environment=IGEnvironment.DEMO,
        account_id="DEMO-ACCOUNT",
        product_epic="GOLD.BARRIER.CALL",
        resolution_seconds=60,
        price_basis=ChartPriceBasis.MID,
    )

    assert len(us_five.series.candles) == 1
    assert us_five.series.candles[0].close == Decimal("110.1")
    assert len(gold.series.candles) == 1
    assert gold.series.candles[0].close == Decimal("200.1")


def test_unbound_reference_update_fails_closed(tmp_path) -> None:
    service = _service(tmp_path)

    with pytest.raises(MarketNavigationCatalogError, match="no explicit product binding"):
        service.ingest_m1_update(
            environment=IGEnvironment.DEMO,
            account_id="DEMO-ACCOUNT",
            chart_update=_update("UNKNOWN.REFERENCE", 0, "100"),
            resolution_seconds=60,
            price_basis=ChartPriceBasis.MID,
        )


def test_session_series_are_isolated_by_environment_and_account(tmp_path) -> None:
    service = _service(tmp_path)
    service.ingest_m1_update(
        environment=IGEnvironment.DEMO,
        account_id="DEMO-A",
        chart_update=_update(US_REFERENCE, 0, "100"),
        resolution_seconds=60,
        price_basis=ChartPriceBasis.MID,
    )

    other_account = service.series_for_product(
        environment=IGEnvironment.DEMO,
        account_id="DEMO-B",
        product_epic="IX.D.NASDAQ.OPTCALL2.IP",
        resolution_seconds=60,
        price_basis=ChartPriceBasis.MID,
    )
    live = service.series_for_product(
        environment=IGEnvironment.LIVE,
        account_id="DEMO-A",
        product_epic="IX.D.NASDAQ.OPTCALL2.IP",
        resolution_seconds=60,
        price_basis=ChartPriceBasis.MID,
    )

    assert other_account.series.candles == ()
    assert live.series.candles == ()


def test_explicit_reference_universe_accumulates_without_a_product_binding(tmp_path) -> None:
    service = MultiMarketSessionCandleService(
        IGProductMarketBindingRegistry(()),
        candle_history_service=CandleHistoryService(cache_root_provider=lambda: tmp_path),
        reference_epics=(GOLD_REFERENCE,),
    )

    updated = service.ingest_m1_update(
        environment=IGEnvironment.DEMO,
        account_id="DEMO-A",
        chart_update=_update(GOLD_REFERENCE, 0, "200"),
        resolution_seconds=60,
        price_basis=ChartPriceBasis.MID,
    )
    series = service.reference_series(
        environment=IGEnvironment.DEMO,
        account_id="DEMO-A",
        reference_epic=GOLD_REFERENCE,
        resolution_seconds=60,
        price_basis=ChartPriceBasis.MID,
    )

    assert updated == ()
    assert len(series.candles) == 1
    assert series.candles[0].close == Decimal("200.1")
    assert list(tmp_path.rglob("*.jsonl")) == []
