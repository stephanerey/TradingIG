"""Prepare Scanner inputs only from explicit product/market bindings."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from trading_ig_assistant.domain.ai_context import MarketContextSnapshot
from trading_ig_assistant.domain.analysis import StrategySignal
from trading_ig_assistant.domain.macro_context import MacroRibbonState
from trading_ig_assistant.domain.market_data import ChartCandleSeries
from trading_ig_assistant.domain.market_navigation import IGProductMarketBinding
from trading_ig_assistant.domain.products import TradableProduct
from trading_ig_assistant.domain.scanner_profiles import ScannerProfileCatalog
from trading_ig_assistant.services.market_navigation_catalog_service import (
    IGProductMarketBindingRegistry,
)
from trading_ig_assistant.services.market_scanner_service import MarketScannerInput
from trading_ig_assistant.services.product_context_projection_service import (
    ProductContextProjection,
    ProductContextProjectionService,
    build_context_score_component,
)
from trading_ig_assistant.services.scanner_profile_resolver import (
    resolve_scanner_profiles_from_catalog,
)


@dataclass(frozen=True)
class PreparedScannerMarket:
    scanner_input: MarketScannerInput
    binding: IGProductMarketBinding
    context: ProductContextProjection


class ScannerMarketInputService:
    """Join session candles, context and profiles without guessing product ancestry."""

    def __init__(
        self,
        binding_registry: IGProductMarketBindingRegistry,
        *,
        context_service: ProductContextProjectionService | None = None,
    ) -> None:
        self._binding_registry = binding_registry
        self._context_service = context_service or ProductContextProjectionService()

    def prepare(
        self,
        *,
        product: TradableProduct,
        candle_series: ChartCandleSeries,
        macro_state: MacroRibbonState,
        evaluated_at_utc: datetime,
        profile_catalog: ScannerProfileCatalog,
        account_id: str | None = None,
        ai_snapshot: MarketContextSnapshot | None = None,
        qualified_event_signal: StrategySignal | None = None,
        product_spread: Decimal | None = None,
        fee_per_unit_per_side: Decimal | None = None,
    ) -> PreparedScannerMarket:
        binding = self._binding_registry.resolve(product.epic)
        if candle_series.selected_product_epic != product.epic:
            raise ValueError("session candle series does not belong to the selected product")
        if candle_series.chart_source_epic != binding.reference_epic:
            raise ValueError("session candle source does not match the explicit reference EPIC")

        context = self._context_service.project(
            product,
            macro_state,
            evaluated_at_utc=evaluated_at_utc,
            ai_snapshot=ai_snapshot,
            qualified_event_signal=qualified_event_signal,
        )
        profiles = resolve_scanner_profiles_from_catalog(
            profile_catalog,
            canonical_underlying_id=binding.canonical_underlying_id,
            account_id=account_id,
        )
        scanner_input = MarketScannerInput(
            product=product,
            candle_series=candle_series,
            context_component=build_context_score_component(context),
            product_spread=product_spread,
            fee_per_unit_per_side=fee_per_unit_per_side,
            execution_price_scale_verified=product.epic == binding.reference_epic,
            resolved_strategy_profiles=profiles,
        )
        return PreparedScannerMarket(
            scanner_input=scanner_input,
            binding=binding,
            context=context,
        )
