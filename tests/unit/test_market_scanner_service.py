from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from trading_ig_assistant.domain.analysis import ScoreBand, ScoreComponentName, StrategyId
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
from trading_ig_assistant.domain.markets import CanonicalUnderlyingId
from trading_ig_assistant.domain.products import AssetClass, ProductType, TradableProduct
from trading_ig_assistant.domain.scanner_profiles import (
    ScannerProfileCatalog,
    ScannerProfilePatch,
)
from trading_ig_assistant.services.market_scanner_service import (
    MarketScannerInput,
    MarketScannerService,
)
from trading_ig_assistant.services.scanner_preview_service import (
    ScannerStrategyProfile,
    default_scanner_strategy_profile,
)
from trading_ig_assistant.services.scanner_profile_resolver import (
    ResolvedScannerStrategyProfile,
    resolve_scanner_profiles_from_catalog,
)
from trading_ig_assistant.services.setup_scoring_service import build_banded_score_component

NOW = datetime(2026, 11, 5, 16, 0, tzinfo=UTC)


def _product(epic: str) -> TradableProduct:
    return TradableProduct(
        epic=epic,
        name=epic,
        product_type=ProductType.CASH_OR_DFB,
        asset_class=AssetClass.INDICES,
        status="TRADEABLE",
    )


def _series(epic: str, *, stale: bool = False) -> ChartCandleSeries:
    end = NOW - (timedelta(hours=1) if stale else timedelta(0))
    candles = tuple(
        Candle(
            timestamp=end - timedelta(minutes=30 - index),
            open=Decimal("100") + Decimal(index),
            high=Decimal("101") + Decimal(index),
            low=Decimal("99") + Decimal(index),
            close=Decimal("100.8") + Decimal(index),
        )
        for index in range(31)
    )
    return ChartCandleSeries(
        selected_product_epic=epic,
        chart_source_epic=epic,
        resolution_seconds=60,
        price_basis=ChartPriceBasis.MID,
        candles=candles,
        sources=(CandleSource.STREAM,) * len(candles),
    )


def _context():
    return build_banded_score_component(
        ScoreComponentName.CONTEXT,
        ScoreBand.FAVORABLE,
        provenance=("context:fixture",),
    )


def _macro() -> MacroRibbonState:
    return MacroRibbonState(
        schema_version=1,
        regime=MarketRegime.NEUTRAL,
        index_bias=DirectionalBias.NEUTRAL,
        gold_bias=DirectionalBias.NEUTRAL,
        event_risk=EventRisk.LOW,
        signals=(),
        generated_at_utc=NOW,
        reason_codes=(),
        provenance=("macro:fixture",),
    )


def _input(epic: str, *, stale: bool = False) -> MarketScannerInput:
    return MarketScannerInput(
        product=_product(epic),
        candle_series=_series(epic, stale=stale),
        context_component=_context(),
        product_spread=Decimal("0.1"),
        fee_per_unit_per_side=Decimal("0"),
        execution_price_scale_verified=True,
    )


def test_multi_market_scan_is_deterministic_and_keeps_per_market_results() -> None:
    batch = MarketScannerService().scan(
        (_input("Z.EPIC"), _input("A.EPIC")),
        evaluated_at_utc=NOW,
        macro_state=_macro(),
    )

    assert tuple(item.product.epic for item in batch.items) == ("A.EPIC", "Z.EPIC")
    assert all(item.results for item in batch.items)
    assert len(batch.ranked_results) == sum(len(item.results) for item in batch.items)
    assert batch.failures == ()
    assert batch.evaluated_at_utc == NOW


def test_invalid_market_is_isolated_without_hiding_valid_market() -> None:
    batch = MarketScannerService().scan(
        (_input("VALID"), _input("STALE", stale=True)),
        evaluated_at_utc=NOW,
        macro_state=_macro(),
    )

    assert tuple(item.product.epic for item in batch.items) == ("VALID",)
    assert len(batch.failures) == 1
    assert batch.failures[0].product_epic == "STALE"
    assert "STALE_HISTORY" in batch.failures[0].reason


def test_multi_market_scan_rejects_duplicate_epics_and_naive_time() -> None:
    item = _input("DUPLICATE")
    service = MarketScannerService()

    with pytest.raises(ValueError, match="unique"):
        service.scan((item, item), evaluated_at_utc=NOW, macro_state=_macro())
    with pytest.raises(ValueError, match="timezone-aware"):
        service.scan((item,), evaluated_at_utc=NOW.replace(tzinfo=None), macro_state=_macro())


def test_market_input_rejects_product_series_mismatch() -> None:
    with pytest.raises(ValueError, match="match"):
        MarketScannerInput(
            product=_product("PRODUCT"),
            candle_series=_series("OTHER"),
            context_component=_context(),
        )


def test_per_market_strategy_profile_can_enable_breakout_only() -> None:
    profile = replace(
        default_scanner_strategy_profile(),
        profile_id="breakout-only",
        enabled_strategies=(StrategyId.BREAKOUT,),
    )
    item = replace(_input("PROFILED"), strategy_profile=profile)

    batch = MarketScannerService().scan(
        (item,),
        evaluated_at_utc=NOW,
        macro_state=_macro(),
    )

    assert tuple(signal.strategy_id for signal in batch.items[0].preview.signals) == (
        StrategyId.BREAKOUT.value,
    )
    assert "STRATEGY_PROFILE:breakout-only" in batch.items[0].preview.limitations


def test_strategy_profile_rejects_empty_or_duplicate_selection() -> None:
    default = default_scanner_strategy_profile()
    with pytest.raises(ValueError, match="at least one"):
        ScannerStrategyProfile(
            profile_id="empty",
            enabled_strategies=(),
            trend_follow=default.trend_follow,
            breakout=default.breakout,
            pullback=default.pullback,
        )
    with pytest.raises(ValueError, match="duplicate"):
        replace(
            default,
            profile_id="duplicate",
            enabled_strategies=(StrategyId.BREAKOUT, StrategyId.BREAKOUT),
        )


def test_multi_strategy_profiles_are_evaluated_then_merged_with_provenance() -> None:
    catalog = ScannerProfileCatalog(
        strategy_patches=(
            (
                StrategyId.BREAKOUT,
                ScannerProfilePatch(
                    patch_id="breakout-18",
                    overrides=(("breakout.level_lookback", 18),),
                ),
            ),
            (
                StrategyId.PULLBACK,
                ScannerProfilePatch(
                    patch_id="pullback-10",
                    overrides=(("pullback.rsi_period", 10),),
                ),
            ),
        )
    )
    profiles = resolve_scanner_profiles_from_catalog(
        catalog,
        canonical_underlying_id=CanonicalUnderlyingId.US_TECH_100,
    )
    item = replace(_input("PROFILED-MULTI"), resolved_strategy_profiles=profiles)

    batch = MarketScannerService().scan(
        (item,),
        evaluated_at_utc=NOW,
        macro_state=_macro(),
    )

    market = batch.items[0]
    assert tuple(signal.strategy_id for signal in market.preview.signals) == (
        StrategyId.BREAKOUT.value,
        StrategyId.PULLBACK.value,
        StrategyId.TREND_FOLLOW.value,
    )
    assert len(market.results) == 3
    assert market.resolved_strategy_profiles == profiles
    assert profiles[1].source_for("breakout.level_lookback") == "strategy:breakout-18"
    assert profiles[2].source_for("pullback.rsi_period") == "strategy:pullback-10"
    assert any("STRATEGY_PROFILE:" in item for item in market.preview.limitations)


def test_market_input_rejects_conflicting_or_overlapping_resolved_profiles() -> None:
    profiles = resolve_scanner_profiles_from_catalog(
        ScannerProfileCatalog(),
        canonical_underlying_id=CanonicalUnderlyingId.US_TECH_100,
        strategy_ids=(StrategyId.BREAKOUT,),
    )
    with pytest.raises(ValueError, match="cannot combine"):
        replace(
            _input("CONFLICT"),
            strategy_profile=default_scanner_strategy_profile(),
            resolved_strategy_profiles=profiles,
        )
    with pytest.raises(ValueError, match="must not overlap"):
        replace(_input("OVERLAP"), resolved_strategy_profiles=(profiles[0], profiles[0]))


def test_market_input_rejects_event_driven_resolved_profile() -> None:
    default = default_scanner_strategy_profile()
    event_profile = replace(
        default,
        profile_id="event-invalid",
        enabled_strategies=(StrategyId.EVENT_DRIVEN,),
    )
    resolved = ResolvedScannerStrategyProfile(
        profile=event_profile,
        sources=(("enabled_strategies", "fixture"),),
    )

    with pytest.raises(ValueError, match="exactly one technical"):
        replace(_input("EVENT"), resolved_strategy_profiles=(resolved,))
