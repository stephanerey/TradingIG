"""Broker- and UI-independent multi-market scanner orchestration."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from trading_ig_assistant.domain.analysis import (
    TECHNICAL_STRATEGY_IDS,
    ScannerResult,
    ScoreComponent,
    ScoreComponentName,
)
from trading_ig_assistant.domain.macro_context import MacroRibbonState
from trading_ig_assistant.domain.market_data import ChartCandleSeries
from trading_ig_assistant.domain.products import TradableProduct
from trading_ig_assistant.services.scanner_component_service import ScannerComponentService
from trading_ig_assistant.services.scanner_preview_service import (
    ScannerPreview,
    ScannerStrategyProfile,
    build_scanner_preview,
)
from trading_ig_assistant.services.scanner_profile_resolver import (
    ResolvedScannerStrategyProfile,
)
from trading_ig_assistant.services.setup_scoring_service import (
    SetupScoringService,
    build_consensus,
)


@dataclass(frozen=True)
class MarketScannerInput:
    product: TradableProduct
    candle_series: ChartCandleSeries
    context_component: ScoreComponent
    product_spread: Decimal | None = None
    fee_per_unit_per_side: Decimal | None = None
    execution_price_scale_verified: bool = False
    strategy_profile: ScannerStrategyProfile | None = None
    resolved_strategy_profiles: tuple[ResolvedScannerStrategyProfile, ...] = ()

    def __post_init__(self) -> None:
        if self.candle_series.selected_product_epic != self.product.epic:
            raise ValueError("scanner input product must match the candle-series selected epic")
        if self.context_component.name is not ScoreComponentName.CONTEXT:
            raise ValueError("scanner input requires a context score component")
        if self.strategy_profile is not None and self.resolved_strategy_profiles:
            raise ValueError("scanner input cannot combine single and resolved strategy profiles")
        _validate_resolved_strategy_profiles(self.resolved_strategy_profiles)


@dataclass(frozen=True)
class MarketScannerItem:
    product: TradableProduct
    preview: ScannerPreview
    results: tuple[ScannerResult, ...]
    resolved_strategy_profiles: tuple[ResolvedScannerStrategyProfile, ...] = ()


@dataclass(frozen=True)
class MarketScannerFailure:
    product_epic: str
    reason: str


@dataclass(frozen=True)
class MarketScannerBatch:
    items: tuple[MarketScannerItem, ...]
    ranked_results: tuple[ScannerResult, ...]
    failures: tuple[MarketScannerFailure, ...]
    evaluated_at_utc: datetime


class MarketScannerService:
    """Evaluate independent markets without importing Qt, tickets or broker adapters."""

    def scan(
        self,
        inputs: tuple[MarketScannerInput, ...],
        *,
        evaluated_at_utc: datetime,
        macro_state: MacroRibbonState | None,
        component_weights: Mapping[ScoreComponentName, Decimal] | None = None,
        candidate_threshold: Decimal = Decimal("75"),
        watch_threshold: Decimal = Decimal("60"),
    ) -> MarketScannerBatch:
        if evaluated_at_utc.tzinfo is None or evaluated_at_utc.utcoffset() is None:
            raise ValueError("scanner batch evaluation time must be timezone-aware")
        epics = tuple(item.product.epic for item in inputs)
        if len(set(epics)) != len(epics):
            raise ValueError("scanner batch product epics must be unique")

        component_service = ScannerComponentService()
        market_risk = component_service.market_risk_from_macro(macro_state)
        items: list[MarketScannerItem] = []
        failures: list[MarketScannerFailure] = []
        all_results: list[ScannerResult] = []
        for item in sorted(inputs, key=lambda value: value.product.epic):
            try:
                preview = _build_market_preview(item, evaluated_at_utc=evaluated_at_utc)
                results = component_service.score_signals(
                    preview.consensus,
                    item.context_component,
                    fresh=True,
                    continuous=preview.excluded_pre_gap_candles == 0,
                    market_risk_component=market_risk,
                    product_spread=item.product_spread,
                    fee_per_unit_per_side=item.fee_per_unit_per_side,
                    execution_price_scale_verified=item.execution_price_scale_verified,
                    component_weights=component_weights,
                    candidate_threshold=candidate_threshold,
                    watch_threshold=watch_threshold,
                )
            except ValueError as exc:
                failures.append(
                    MarketScannerFailure(
                        product_epic=item.product.epic,
                        reason=str(exc),
                    )
                )
                continue
            market_item = MarketScannerItem(
                product=item.product,
                preview=preview,
                results=results,
                resolved_strategy_profiles=item.resolved_strategy_profiles,
            )
            items.append(market_item)
            all_results.extend(results)

        return MarketScannerBatch(
            items=tuple(items),
            ranked_results=SetupScoringService.rank(all_results),
            failures=tuple(failures),
            evaluated_at_utc=evaluated_at_utc,
        )


def _build_market_preview(
    scanner_input: MarketScannerInput,
    *,
    evaluated_at_utc: datetime,
) -> ScannerPreview:
    if not scanner_input.resolved_strategy_profiles:
        return build_scanner_preview(
            scanner_input.candle_series,
            as_of_utc=evaluated_at_utc,
            strategy_profile=scanner_input.strategy_profile,
        )

    previews = tuple(
        build_scanner_preview(
            scanner_input.candle_series,
            as_of_utc=evaluated_at_utc,
            strategy_profile=resolved.profile,
        )
        for resolved in scanner_input.resolved_strategy_profiles
    )
    first = previews[0]
    signals = tuple(
        sorted(
            (signal for preview in previews for signal in preview.signals),
            key=lambda signal: (signal.strategy_id, signal.signal_id),
        )
    )
    return ScannerPreview(
        instrument_id=first.instrument_id,
        timeframe=first.timeframe,
        used_closed_candles=first.used_closed_candles,
        excluded_trailing_candles=first.excluded_trailing_candles,
        excluded_pre_gap_candles=first.excluded_pre_gap_candles,
        signals=signals,
        consensus=build_consensus(signals),
        limitations=tuple(
            dict.fromkeys(limitation for preview in previews for limitation in preview.limitations)
        ),
        indicators=tuple(
            dict.fromkeys(
                indicator for preview in previews for indicator in preview.indicators
            )
        ),
    )


def _validate_resolved_strategy_profiles(
    profiles: tuple[ResolvedScannerStrategyProfile, ...],
) -> None:
    strategy_ids = []
    for resolved in profiles:
        if not isinstance(resolved, ResolvedScannerStrategyProfile):
            raise ValueError("resolved strategy profiles contain an invalid value")
        enabled = resolved.profile.enabled_strategies
        if len(enabled) != 1 or enabled[0] not in TECHNICAL_STRATEGY_IDS:
            raise ValueError(
                "each resolved Scanner profile must enable exactly one technical strategy"
            )
        strategy_ids.append(enabled[0])
    if len(set(strategy_ids)) != len(strategy_ids):
        raise ValueError("resolved Scanner strategy profiles must not overlap")
