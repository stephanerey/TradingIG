from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from trading_ig_assistant.domain.macro_context import (
    DirectionalBias,
    EventRisk,
    MacroRibbonState,
    MarketRegime,
)
from trading_ig_assistant.domain.market_data import (
    Candle,
    CandleSource,
    ChartCandleSeries,
    ChartPriceBasis,
)
from trading_ig_assistant.domain.market_navigation import IGProductMarketBinding
from trading_ig_assistant.domain.markets import CanonicalUnderlyingId
from trading_ig_assistant.domain.products import (
    AssetClass,
    ProductDirection,
    ProductType,
    TradableProduct,
)
from trading_ig_assistant.domain.scanner_profiles import (
    ScannerProfileCatalog,
    ScannerProfilePatch,
)
from trading_ig_assistant.services.market_navigation_catalog_service import (
    IGProductMarketBindingRegistry,
    MarketNavigationCatalogError,
)
from trading_ig_assistant.services.market_scanner_service import MarketScannerService
from trading_ig_assistant.services.scanner_market_input_service import ScannerMarketInputService

NOW = datetime(2026, 11, 5, 18, 0, tzinfo=UTC)
PRODUCT_EPIC = "IX.D.NASDAQ.OPTCALL2.IP"
REFERENCE_EPIC = "IX.D.NASDAQ.IFD.IP"


def _binding() -> IGProductMarketBinding:
    return IGProductMarketBinding(
        product_epic=PRODUCT_EPIC,
        canonical_underlying_id=CanonicalUnderlyingId.US_TECH_100,
        reference_epic=REFERENCE_EPIC,
        provenance=("operator:explicit", "ig:demo-read-only:2026-11-05"),
    )


def _product() -> TradableProduct:
    return TradableProduct(
        epic=PRODUCT_EPIC,
        name="US Tech 100 Barrières Achat",
        product_type=ProductType.BARRIER,
        asset_class=AssetClass.INDICES,
        direction=ProductDirection.BUY,
        status="TRADEABLE",
    )


def _series(*, chart_source_epic: str = REFERENCE_EPIC) -> ChartCandleSeries:
    candles = tuple(
        Candle(
            timestamp=NOW - timedelta(minutes=30 - index),
            open=Decimal("100") + index,
            high=Decimal("101") + index,
            low=Decimal("99") + index,
            close=Decimal("100.5") + index,
        )
        for index in range(31)
    )
    return ChartCandleSeries(
        selected_product_epic=PRODUCT_EPIC,
        chart_source_epic=chart_source_epic,
        resolution_seconds=60,
        price_basis=ChartPriceBasis.MID,
        candles=candles,
        sources=(CandleSource.STREAM,) * len(candles),
    )


def _macro() -> MacroRibbonState:
    return MacroRibbonState(
        schema_version=1,
        regime=MarketRegime.RISK_ON,
        index_bias=DirectionalBias.BULLISH,
        gold_bias=DirectionalBias.UNKNOWN,
        event_risk=EventRisk.LOW,
        signals=(),
        generated_at_utc=NOW,
        reason_codes=(),
        provenance=("macro:fixture",),
    )


def test_prepare_joins_exact_binding_context_and_layered_profiles() -> None:
    catalog = ScannerProfileCatalog(
        account_patches=(
            (
                "DEMO-ACCOUNT",
                ScannerProfilePatch(
                    patch_id="demo-account",
                    overrides=(("trend_follow.fast_ema_period", 8),),
                ),
            ),
        ),
        market_patches=(
            (
                CanonicalUnderlyingId.US_TECH_100,
                ScannerProfilePatch(
                    patch_id="us-tech",
                    overrides=(("breakout.level_lookback", 18),),
                ),
            ),
        ),
    )
    service = ScannerMarketInputService(IGProductMarketBindingRegistry((_binding(),)))

    prepared = service.prepare(
        product=_product(),
        candle_series=_series(),
        macro_state=_macro(),
        evaluated_at_utc=NOW,
        profile_catalog=catalog,
        account_id="DEMO-ACCOUNT",
        product_spread=Decimal("1.8"),
        fee_per_unit_per_side=Decimal("0.1"),
    )

    assert prepared.binding.canonical_underlying_id is CanonicalUnderlyingId.US_TECH_100
    assert prepared.context.label == "ALIGNÉ"
    assert prepared.scanner_input.candle_series.chart_source_epic == REFERENCE_EPIC
    assert prepared.scanner_input.execution_price_scale_verified is False
    assert len(prepared.scanner_input.resolved_strategy_profiles) == 3
    trend_profile = prepared.scanner_input.resolved_strategy_profiles[0]
    breakout_profile = prepared.scanner_input.resolved_strategy_profiles[1]
    assert trend_profile.source_for("trend_follow.fast_ema_period") == ("account:demo-account")
    assert breakout_profile.source_for("breakout.level_lookback") == "market:us-tech"

    batch = MarketScannerService().scan(
        (prepared.scanner_input,),
        evaluated_at_utc=NOW,
        macro_state=_macro(),
    )
    assert tuple(item.product.epic for item in batch.items) == (PRODUCT_EPIC,)
    assert batch.failures == ()
    assert len(batch.items[0].results) == 3


def test_prepare_fails_closed_for_unmapped_product_or_wrong_reference_series() -> None:
    empty = ScannerMarketInputService(IGProductMarketBindingRegistry(()))
    with pytest.raises(MarketNavigationCatalogError, match="no explicit"):
        empty.prepare(
            product=_product(),
            candle_series=_series(),
            macro_state=_macro(),
            evaluated_at_utc=NOW,
            profile_catalog=ScannerProfileCatalog(),
        )

    mapped = ScannerMarketInputService(IGProductMarketBindingRegistry((_binding(),)))
    with pytest.raises(ValueError, match="reference EPIC"):
        mapped.prepare(
            product=_product(),
            candle_series=_series(chart_source_epic="WRONG.REFERENCE"),
            macro_state=_macro(),
            evaluated_at_utc=NOW,
            profile_catalog=ScannerProfileCatalog(),
        )
