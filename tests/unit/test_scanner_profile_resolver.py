from dataclasses import replace
from decimal import Decimal

import pytest

from trading_ig_assistant.domain.adapter_contracts import (
    InstrumentKind,
    InstrumentMapping,
    InstrumentMappingNotFoundError,
    InstrumentMappingRegistry,
)
from trading_ig_assistant.domain.analysis import StrategyId
from trading_ig_assistant.domain.markets import CanonicalUnderlyingId
from trading_ig_assistant.domain.scanner_profiles import ScannerProfileCatalog
from trading_ig_assistant.services.scanner_preview_service import (
    ScannerStrategyProfile,
    default_scanner_strategy_profile,
)
from trading_ig_assistant.services.scanner_profile_resolver import (
    ScannerProfilePatch,
    resolve_scanner_profile_for_instrument,
    resolve_scanner_profile_from_catalog,
    resolve_scanner_profiles_from_catalog,
    resolve_scanner_strategy_profile,
)


def test_scanner_profile_resolver_preserves_defaults_without_patch() -> None:
    base = default_scanner_strategy_profile()

    resolved = resolve_scanner_strategy_profile(base_profile=base)

    assert resolved.profile == base
    assert resolved.source_for("profile_id") == "default"
    assert resolved.source_for("trend_follow.fast_ema_period") == "default"
    assert resolved.source_for("breakout.levels.stop_atr") == "default"


def test_scanner_profile_resolver_applies_approved_precedence_with_leaf_origins() -> None:
    base = default_scanner_strategy_profile()
    resolved = resolve_scanner_strategy_profile(
        base_profile=base,
        global_patch=ScannerProfilePatch(
            patch_id="global-v1",
            overrides=(("trend_follow.max_extension_atr", Decimal("1.8")),),
        ),
        account_patch=ScannerProfilePatch(
            patch_id="account-demo",
            overrides=(
                ("trend_follow.max_extension_atr", Decimal("1.6")),
                ("breakout.levels.stop_atr", Decimal("1.2")),
            ),
        ),
        strategy_patch=ScannerProfilePatch(
            patch_id="strategy-conservative",
            overrides=(("trend_follow.max_extension_atr", Decimal("1.4")),),
        ),
        market_patch=ScannerProfilePatch(
            patch_id="market-nasdaq",
            overrides=(("trend_follow.max_extension_atr", Decimal("1.25")),),
        ),
    )

    assert resolved.profile.trend_follow.max_extension_atr == Decimal("1.25")
    assert resolved.profile.breakout.levels.stop_atr == Decimal("1.2")
    assert resolved.source_for("trend_follow.max_extension_atr") == "market:market-nasdaq"
    assert resolved.source_for("breakout.levels.stop_atr") == "account:account-demo"
    assert resolved.source_for("pullback.rsi_period") == "default"
    assert "global=global-v1" in resolved.profile.profile_id
    assert "market=market-nasdaq" in resolved.profile.profile_id


def test_scanner_profile_patch_is_atomic_for_coupled_parameters() -> None:
    resolved = resolve_scanner_strategy_profile(
        global_patch=ScannerProfilePatch(
            patch_id="slow-trend",
            overrides=(
                ("trend_follow.fast_ema_period", 30),
                ("trend_follow.slow_ema_period", 40),
            ),
        )
    )

    assert resolved.profile.trend_follow.fast_ema_period == 30
    assert resolved.profile.trend_follow.slow_ema_period == 40


def test_scanner_profile_patch_can_select_a_non_empty_strategy_subset() -> None:
    resolved = resolve_scanner_strategy_profile(
        strategy_patch=ScannerProfilePatch(
            patch_id="breakout-only",
            overrides=(("enabled_strategies", (StrategyId.BREAKOUT,)),),
        )
    )

    assert resolved.profile.enabled_strategies == (StrategyId.BREAKOUT,)
    assert resolved.source_for("enabled_strategies") == "strategy:breakout-only"


@pytest.mark.parametrize(
    "patch",
    (
        ScannerProfilePatch(patch_id="unknown", overrides=(("missing.field", 1),)),
        ScannerProfilePatch(patch_id="branch", overrides=(("trend_follow.levels", object()),)),
        ScannerProfilePatch(
            patch_id="bad-periods",
            overrides=(("trend_follow.fast_ema_period", 50),),
        ),
        ScannerProfilePatch(
            patch_id="empty-strategies",
            overrides=(("enabled_strategies", ()),),
        ),
    ),
)
def test_scanner_profile_resolver_rejects_unknown_branch_or_invalid_result(
    patch: ScannerProfilePatch,
) -> None:
    with pytest.raises(ValueError):
        resolve_scanner_strategy_profile(market_patch=patch)


def test_scanner_profile_patch_rejects_ambiguous_or_reserved_paths() -> None:
    with pytest.raises(ValueError):
        ScannerProfilePatch(
            patch_id="duplicate",
            overrides=(("pullback.rsi_period", 10), ("pullback.rsi_period", 12)),
        )
    with pytest.raises(ValueError):
        ScannerProfilePatch(patch_id="reserved", overrides=(("profile_id", "hidden"),))


def test_profile_rejects_string_strategy_ids_even_when_values_match() -> None:
    base = default_scanner_strategy_profile()

    with pytest.raises(ValueError, match="invalid strategy ID"):
        ScannerStrategyProfile(
            profile_id="invalid-types",
            enabled_strategies=("breakout",),  # type: ignore[arg-type]
            trend_follow=base.trend_follow,
            breakout=base.breakout,
            pullback=base.pullback,
        )


def test_resolution_does_not_mutate_base_profile() -> None:
    base = default_scanner_strategy_profile()
    original = replace(base)

    resolve_scanner_strategy_profile(
        base_profile=base,
        market_patch=ScannerProfilePatch(
            patch_id="market",
            overrides=(("pullback.maximum_distance_atr", Decimal("0.75")),),
        ),
    )

    assert base == original


def test_catalog_resolution_uses_exact_approved_identity_keys_and_precedence() -> None:
    catalog = ScannerProfileCatalog(
        global_patch=ScannerProfilePatch(
            patch_id="global",
            overrides=(("trend_follow.max_extension_atr", Decimal("1.8")),),
        ),
        account_patches=(
            (
                "DEMO-ABC123",
                ScannerProfilePatch(
                    patch_id="account",
                    overrides=(("trend_follow.max_extension_atr", Decimal("1.6")),),
                ),
            ),
        ),
        strategy_patches=(
            (
                StrategyId.TREND_FOLLOW,
                ScannerProfilePatch(
                    patch_id="strategy",
                    overrides=(("trend_follow.max_extension_atr", Decimal("1.4")),),
                ),
            ),
        ),
        market_patches=(
            (
                CanonicalUnderlyingId.US_TECH_100,
                ScannerProfilePatch(
                    patch_id="market",
                    overrides=(("trend_follow.max_extension_atr", Decimal("1.25")),),
                ),
            ),
        ),
    )

    resolved = resolve_scanner_profile_from_catalog(
        catalog,
        account_id="DEMO-ABC123",
        strategy_id=StrategyId.TREND_FOLLOW,
        canonical_underlying_id=CanonicalUnderlyingId.US_TECH_100,
    )
    different_market = resolve_scanner_profile_from_catalog(
        catalog,
        account_id="DEMO-ABC123",
        strategy_id=StrategyId.TREND_FOLLOW,
        canonical_underlying_id=CanonicalUnderlyingId.GERMANY_40,
    )

    assert resolved.profile.trend_follow.max_extension_atr == Decimal("1.25")
    assert resolved.source_for("trend_follow.max_extension_atr") == "market:market"
    assert different_market.profile.trend_follow.max_extension_atr == Decimal("1.4")
    assert different_market.source_for("trend_follow.max_extension_atr") == "strategy:strategy"


def test_catalog_resolution_rejects_product_epic_as_a_canonical_underlying() -> None:
    catalog = ScannerProfileCatalog(
        market_patches=(
            (
                CanonicalUnderlyingId.US_TECH_100,
                ScannerProfilePatch(
                    patch_id="canonical-market",
                    overrides=(("breakout.level_lookback", 30),),
                ),
            ),
        )
    )

    with pytest.raises(ValueError, match="CanonicalUnderlyingId"):
        resolve_scanner_profile_from_catalog(
            catalog,
            strategy_id=StrategyId.BREAKOUT,
            canonical_underlying_id="IX.D.NASDAQ.OPTCALL2.IP",  # type: ignore[arg-type]
        )


def test_catalog_rejects_event_driven_strategy_patch() -> None:
    with pytest.raises(ValueError, match="event-driven"):
        ScannerProfileCatalog(
            strategy_patches=(
                (
                    StrategyId.EVENT_DRIVEN,
                    ScannerProfilePatch(
                        patch_id="unsupported",
                        overrides=(("breakout.level_lookback", 25),),
                    ),
                ),
            )
        )


def test_catalog_rejects_a_free_form_market_key() -> None:
    with pytest.raises(ValueError, match="CanonicalUnderlyingId"):
        ScannerProfileCatalog(
            market_patches=(
                (
                    "US Tech 100",  # type: ignore[arg-type]
                    ScannerProfilePatch(
                        patch_id="free-form",
                        overrides=(("breakout.level_lookback", 25),),
                    ),
                ),
            )
        )


def test_instrument_profile_resolution_requires_explicit_underlying_mapping() -> None:
    catalog = ScannerProfileCatalog(
        market_patches=(
            (
                CanonicalUnderlyingId.US_TECH_100,
                ScannerProfilePatch(
                    patch_id="nasdaq",
                    overrides=(("breakout.level_lookback", 30),),
                ),
            ),
        )
    )
    registry = InstrumentMappingRegistry(
        (
            InstrumentMapping(
                provider_id="ig",
                instrument_id="IX.D.NASDAQ.OPTCALL2.IP",
                canonical_instrument_id="US_TECH_100_BARRIER_CALL",
                underlying_id="US_TECH_100",
                currency="EUR",
                instrument_kind=InstrumentKind.BARRIER,
                unit="contract",
                quote_increment=Decimal("0.1"),
                trading_hours="IG market hours",
                timezone="UTC",
                delayed=False,
                provenance="unit-test-explicit-mapping",
            ),
        )
    )

    resolved = resolve_scanner_profile_for_instrument(
        catalog,
        registry,
        provider_id="ig",
        instrument_id="IX.D.NASDAQ.OPTCALL2.IP",
        strategy_id=StrategyId.BREAKOUT,
    )

    assert resolved.profile.breakout.level_lookback == 30
    assert resolved.source_for("breakout.level_lookback") == "market:nasdaq"

    with pytest.raises(InstrumentMappingNotFoundError):
        resolve_scanner_profile_for_instrument(
            catalog,
            registry,
            provider_id="ig",
            instrument_id="UNMAPPED.EPIC",
            strategy_id=StrategyId.BREAKOUT,
        )


def test_instrument_profile_resolution_rejects_unknown_mapped_underlying() -> None:
    registry = InstrumentMappingRegistry(
        (
            InstrumentMapping(
                provider_id="ig",
                instrument_id="IX.D.UNKNOWN.IFD.IP",
                canonical_instrument_id="UNKNOWN",
                underlying_id="NASDAQ",
                currency="EUR",
                instrument_kind=InstrumentKind.DFB,
                unit="contract",
                quote_increment=Decimal("0.1"),
                trading_hours="IG market hours",
                timezone="UTC",
                delayed=False,
                provenance="unit-test-invalid-underlying",
            ),
        )
    )

    with pytest.raises(ValueError, match="unsupported canonical underlying"):
        resolve_scanner_profile_for_instrument(
            ScannerProfileCatalog(),
            registry,
            provider_id="ig",
            instrument_id="IX.D.UNKNOWN.IFD.IP",
            strategy_id=StrategyId.BREAKOUT,
        )


def test_multi_strategy_catalog_resolution_keeps_distinct_configuration_and_sources() -> None:
    catalog = ScannerProfileCatalog(
        account_patches=(
            (
                "DEMO-ABC123",
                ScannerProfilePatch(
                    patch_id="account",
                    overrides=(("breakout.atr_period", 12),),
                ),
            ),
        ),
        strategy_patches=(
            (
                StrategyId.TREND_FOLLOW,
                ScannerProfilePatch(
                    patch_id="trend",
                    overrides=(("trend_follow.fast_ema_period", 8),),
                ),
            ),
            (
                StrategyId.BREAKOUT,
                ScannerProfilePatch(
                    patch_id="breakout",
                    overrides=(("breakout.level_lookback", 18),),
                ),
            ),
            (
                StrategyId.PULLBACK,
                ScannerProfilePatch(
                    patch_id="pullback",
                    overrides=(("pullback.rsi_period", 10),),
                ),
            ),
        ),
    )

    resolved = resolve_scanner_profiles_from_catalog(
        catalog,
        account_id="DEMO-ABC123",
        canonical_underlying_id=CanonicalUnderlyingId.US_TECH_100,
        strategy_ids=(StrategyId.PULLBACK, StrategyId.TREND_FOLLOW, StrategyId.BREAKOUT),
    )

    assert tuple(item.profile.enabled_strategies[0] for item in resolved) == (
        StrategyId.TREND_FOLLOW,
        StrategyId.BREAKOUT,
        StrategyId.PULLBACK,
    )
    assert resolved[0].profile.trend_follow.fast_ema_period == 8
    assert resolved[0].source_for("trend_follow.fast_ema_period") == "strategy:trend"
    assert resolved[1].profile.breakout.level_lookback == 18
    assert resolved[1].source_for("breakout.atr_period") == "account:account"
    assert resolved[2].profile.pullback.rsi_period == 10
    assert resolved[2].source_for("enabled_strategies") == "selector:pullback"


@pytest.mark.parametrize(
    "strategy_ids, message",
    (
        ((), "must not be empty"),
        ((StrategyId.BREAKOUT, StrategyId.BREAKOUT), "must be unique"),
        ((StrategyId.EVENT_DRIVEN,), "does not accept EVENT_DRIVEN"),
    ),
)
def test_multi_strategy_catalog_resolution_rejects_invalid_selection(
    strategy_ids: tuple[StrategyId, ...],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        resolve_scanner_profiles_from_catalog(
            ScannerProfileCatalog(),
            canonical_underlying_id=CanonicalUnderlyingId.US_TECH_100,
            strategy_ids=strategy_ids,
        )


def test_multi_strategy_catalog_resolution_rejects_layer_selection_override() -> None:
    catalog = ScannerProfileCatalog(
        strategy_patches=(
            (
                StrategyId.TREND_FOLLOW,
                ScannerProfilePatch(
                    patch_id="wrong-selection",
                    overrides=(("enabled_strategies", (StrategyId.BREAKOUT,)),),
                ),
            ),
        )
    )

    with pytest.raises(ValueError, match="changed the explicit"):
        resolve_scanner_profiles_from_catalog(
            catalog,
            canonical_underlying_id=CanonicalUnderlyingId.US_TECH_100,
            strategy_ids=(StrategyId.TREND_FOLLOW,),
        )
