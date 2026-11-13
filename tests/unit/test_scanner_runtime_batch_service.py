from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

from trading_ig_assistant.app.config import AppConfig, IGEnvironment
from trading_ig_assistant.app.projections.catalogue import CatalogueVM
from trading_ig_assistant.app.projections.common import Availability
from trading_ig_assistant.app.projections.scanner_projection import (
    _consensus_signal_direction,
    build_scanner_projection,
    empty_scanner_projection,
    merge_scanner_analysis,
)
from trading_ig_assistant.domain.analysis import DataState, SignalSide
from trading_ig_assistant.domain.macro_context import (
    ContextSeverity,
    ContextSignal,
    DirectionalBias,
    EventRisk,
    MacroRibbonState,
    MarketRegime,
)
from trading_ig_assistant.domain.market_data import ChartCandleUpdate, ChartPriceBasis
from trading_ig_assistant.domain.market_navigation import IGProductMarketBinding
from trading_ig_assistant.domain.markets import CanonicalUnderlyingId
from trading_ig_assistant.domain.products import (
    AssetClass,
    ProductDirection,
    ProductType,
    TradableProduct,
)
from trading_ig_assistant.domain.scanner_profiles import ScannerProfileCatalog
from trading_ig_assistant.services.macro_context_service import MacroContextService
from trading_ig_assistant.services.market_navigation_catalog_service import (
    IGProductMarketBindingRegistry,
)
from trading_ig_assistant.services.multi_market_session_candle_service import (
    MultiMarketSessionCandleService,
)
from trading_ig_assistant.services.scanner_preview_service import (
    default_scanner_strategy_profile,
    required_closed_candles,
)
from trading_ig_assistant.services.scanner_runtime_batch_service import (
    ScannerRuntimeBatchService,
)

NOW = datetime(2026, 11, 6, 10, 30, tzinfo=UTC)


def test_consensus_direction_uses_all_ready_actionable_strategies() -> None:
    scored = SimpleNamespace()

    def choice(side: SignalSide, state: DataState = DataState.READY):
        return scored, SimpleNamespace(side=side, data_state=state)

    assert _consensus_signal_direction([choice(SignalSide.FLAT), choice(SignalSide.BUY)]) == (
        "bullish"
    )
    assert _consensus_signal_direction([choice(SignalSide.FLAT), choice(SignalSide.SELL)]) == (
        "bearish"
    )
    assert _consensus_signal_direction([choice(SignalSide.BUY), choice(SignalSide.SELL)]) == (
        "neutral"
    )
    assert _consensus_signal_direction(
        [choice(SignalSide.BUY, DataState.WARMING_UP), choice(SignalSide.FLAT)]
    ) == "neutral"
REFERENCE_EPIC = "IX.D.NASDAQ.IFD.IP"
BUY_EPIC = "IX.D.NASDAQ.OPTCALL2.IP"
SELL_EPIC = "IX.D.NASDAQ.OPTPUT2.IP"


def test_default_scanner_profile_requires_24_closed_continuous_candles() -> None:
    assert required_closed_candles(default_scanner_strategy_profile()) == 24


def _binding(product_epic: str) -> IGProductMarketBinding:
    return IGProductMarketBinding(
        product_epic=product_epic,
        canonical_underlying_id=CanonicalUnderlyingId.US_TECH_100,
        reference_epic=REFERENCE_EPIC,
        provenance=("test:exact-binding",),
    )


def _product(product_epic: str, direction: ProductDirection) -> TradableProduct:
    return TradableProduct(
        epic=product_epic,
        name=product_epic,
        product_type=ProductType.BARRIER,
        asset_class=AssetClass.INDICES,
        direction=direction,
        status="TRADEABLE",
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
        provenance=("test:macro",),
    )


def _session_service(
    registry: IGProductMarketBindingRegistry,
    reference_epic: str = REFERENCE_EPIC,
) -> MultiMarketSessionCandleService:
    service = MultiMarketSessionCandleService(
        registry,
        reference_epics=(reference_epic,),
    )
    for index in range(31):
        value = Decimal("100") + index
        timestamp = NOW - timedelta(minutes=30 - index)
        service.ingest_m1_update(
            environment=IGEnvironment.DEMO,
            account_id="DEMO-ACCOUNT",
            chart_update=ChartCandleUpdate(
                epic=reference_epic,
                interval="1MINUTE",
                timestamp_ms=int(timestamp.timestamp() * 1000),
                end_of_candle=index < 30,
                raw={
                    "BID_OPEN": str(value),
                    "BID_HIGH": str(value + 1),
                    "BID_LOW": str(value - 1),
                    "BID_CLOSE": str(value + Decimal("0.5")),
                    "OFR_OPEN": str(value + Decimal("0.2")),
                    "OFR_HIGH": str(value + Decimal("1.2")),
                    "OFR_LOW": str(value - Decimal("0.8")),
                    "OFR_CLOSE": str(value + Decimal("0.7")),
                },
            ),
            resolution_seconds=60,
            price_basis=ChartPriceBasis.MID,
        )
    return service


def test_demo_france_reference_scans_its_own_session_candles() -> None:
    epic = "IX.D.CAC.IMF.IP"
    registry = IGProductMarketBindingRegistry(AppConfig().product_market_bindings)
    service = ScannerRuntimeBatchService(registry, _session_service(registry, epic))
    product = TradableProduct(
        epic=epic,
        name="France 40 CFD",
        product_type=ProductType.CASH_OR_DFB,
        asset_class=AssetClass.INDICES,
        status="TRADEABLE",
    )

    result = service.scan(
        products=(product,),
        environment=IGEnvironment.DEMO,
        account_id="DEMO-ACCOUNT",
        resolution_seconds=60,
        price_basis=ChartPriceBasis.MID,
        macro_state=_macro(),
        evaluated_at_utc=NOW,
        profile_catalog=ScannerProfileCatalog(),
    )

    assert len(result.batch.items) == 1
    assert result.batch.items[0].product.epic == epic
    assert len(result.batch.items[0].results) == 3


def test_runtime_batch_scans_only_exact_bound_products_and_preserves_context() -> None:
    registry = IGProductMarketBindingRegistry((_binding(BUY_EPIC), _binding(SELL_EPIC)))
    service = ScannerRuntimeBatchService(registry, _session_service(registry))
    buy = _product(BUY_EPIC, ProductDirection.BUY)
    sell = _product(SELL_EPIC, ProductDirection.SELL)
    unbound = _product("UNBOUND.PRODUCT", ProductDirection.BUY)

    result = service.scan(
        products=(unbound, sell, buy),
        environment=IGEnvironment.DEMO,
        account_id="DEMO-ACCOUNT",
        resolution_seconds=60,
        price_basis=ChartPriceBasis.MID,
        macro_state=_macro(),
        evaluated_at_utc=NOW,
        profile_catalog=ScannerProfileCatalog(),
        product_spreads={BUY_EPIC: Decimal("1.8"), SELL_EPIC: Decimal("1.8")},
        fee_per_unit_per_side={BUY_EPIC: Decimal("0.1"), SELL_EPIC: Decimal("0.1")},
    )

    assert tuple(item.product.epic for item in result.batch.items) == (BUY_EPIC, SELL_EPIC)
    assert result.configured_product_epics == (BUY_EPIC, SELL_EPIC)
    assert result.context_for(BUY_EPIC).label == "ALIGNÉ"
    assert result.context_for(SELL_EPIC).label == "DÉFAVORABLE"
    assert result.batch.failures == ()
    assert all(len(item.results) == 3 for item in result.batch.items)
    assert "UNBOUND.PRODUCT" not in result.configured_product_epics

    projection = merge_scanner_analysis(
        empty_scanner_projection(0, NOW),
        result=result,
        binding_registry=registry,
        generated_at_utc=NOW,
    )
    row = projection.rows[0]
    assert row.context_level in {"aligned", "unfavorable"}
    assert row.context_components
    assert row.context_reason_codes
    assert "test:macro" in row.context_provenance
    assert len(row.strategy_signals) == 6
    assert {signal.product_epic for signal in row.strategy_signals} == {
        BUY_EPIC,
        SELL_EPIC,
    }
    assert {signal.strategy_id for signal in row.strategy_signals} == {
        "trend_follow",
        "breakout",
        "pullback",
    }
    assert {indicator.name for indicator in row.indicators} == {
        "atr",
        "ema",
        "recent_levels",
        "rsi",
    }
    assert all(indicator.state == "ready" for indicator in row.indicators)
    assert all(
        indicator.observed_points >= indicator.required_points
        for indicator in row.indicators
    )

    quote_refresh = build_scanner_projection(
        generation_id=projection.generation_id,
        catalogue=CatalogueVM(
            generation_id=projection.generation_id,
            query=None,
            rows=(),
            availability=Availability.UNAVAILABLE,
            generated_at_utc=NOW,
            kind="test-refresh",
        ),
        generated_at_utc=NOW,
        previous=projection,
    )
    refreshed_row = quote_refresh.rows[0]
    assert quote_refresh.availability is Availability.READY
    assert refreshed_row.strategy_signals == row.strategy_signals
    assert refreshed_row.indicators == row.indicators


def test_runtime_batch_isolates_missing_configured_product_and_warmup() -> None:
    registry = IGProductMarketBindingRegistry((_binding(BUY_EPIC), _binding(SELL_EPIC)))
    empty_session = MultiMarketSessionCandleService(
        registry,
        reference_epics=(REFERENCE_EPIC,),
    )
    service = ScannerRuntimeBatchService(registry, empty_session)

    result = service.scan(
        products=(_product(BUY_EPIC, ProductDirection.BUY),),
        environment=IGEnvironment.DEMO,
        account_id="DEMO-ACCOUNT",
        resolution_seconds=60,
        price_basis=ChartPriceBasis.MID,
        macro_state=_macro(),
        evaluated_at_utc=NOW,
        profile_catalog=ScannerProfileCatalog(),
    )

    assert result.batch.items == ()
    failures = {failure.product_epic: failure.reason for failure in result.batch.failures}
    assert "requires chart candles" in failures[BUY_EPIC]
    assert "absent from product discovery" in failures[SELL_EPIC]


def test_runtime_batch_revalidates_expired_market_risk() -> None:
    from trading_ig_assistant.domain.analysis import ScoreComponentName

    registry = IGProductMarketBindingRegistry((_binding(BUY_EPIC),))
    service = ScannerRuntimeBatchService(registry, _session_service(registry))
    event = ContextSignal(
        signal_id="EVENT",
        label="Event",
        severity=ContextSeverity.GREEN,
        score=None,
        summary="fixture",
        source="fixture",
        source_url=None,
        observed_at_utc=NOW - timedelta(minutes=1),
        valid_until_utc=NOW,
        confidence=None,
        tags=("event",),
    )
    state = MacroContextService().build_state((event,), NOW - timedelta(seconds=1))
    assert state.event_risk is EventRisk.LOW
    result = service.scan(
        products=(_product(BUY_EPIC, ProductDirection.BUY),),
        environment=IGEnvironment.DEMO,
        account_id="DEMO-ACCOUNT",
        resolution_seconds=60,
        price_basis=ChartPriceBasis.MID,
        macro_state=state,
        evaluated_at_utc=NOW,
        profile_catalog=ScannerProfileCatalog(),
    )
    assert result.batch.items
    for scored in result.batch.items[0].results:
        risk = next(c for c in scored.components if c.name is ScoreComponentName.MARKET_RISK)
        assert risk.score is None


def test_runtime_batch_rejects_conflicting_duplicate_product_identity() -> None:
    registry = IGProductMarketBindingRegistry((_binding(BUY_EPIC),))
    service = ScannerRuntimeBatchService(registry, _session_service(registry))
    first = _product(BUY_EPIC, ProductDirection.BUY)
    conflicting = TradableProduct(
        epic=BUY_EPIC,
        name="Conflicting product",
        product_type=ProductType.OPTION,
        asset_class=AssetClass.INDICES,
        direction=ProductDirection.BUY,
    )

    try:
        service.scan(
            products=(first, conflicting),
            environment=IGEnvironment.DEMO,
            account_id="DEMO-ACCOUNT",
            resolution_seconds=60,
            price_basis=ChartPriceBasis.MID,
            macro_state=_macro(),
            evaluated_at_utc=NOW,
            profile_catalog=ScannerProfileCatalog(),
        )
    except ValueError as exc:
        assert "conflicting duplicate product" in str(exc)
    else:
        raise AssertionError("conflicting duplicate product identity must fail closed")
