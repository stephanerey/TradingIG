"""Route session-only M1 updates to explicitly bound Scanner markets."""

from __future__ import annotations

from dataclasses import dataclass

from trading_ig_assistant.app.config import IGEnvironment
from trading_ig_assistant.domain.market_data import (
    ChartCandleSeries,
    ChartCandleUpdate,
    ChartPriceBasis,
)
from trading_ig_assistant.domain.market_navigation import IGProductMarketBinding
from trading_ig_assistant.services.candle_history_service import CandleHistoryService
from trading_ig_assistant.services.market_navigation_catalog_service import (
    IGProductMarketBindingRegistry,
    MarketNavigationCatalogError,
)


@dataclass(frozen=True)
class BoundSessionCandleSeries:
    binding: IGProductMarketBinding
    series: ChartCandleSeries


class MultiMarketSessionCandleService:
    """Keep independent in-memory series; never read REST history or persisted candle caches."""

    def __init__(
        self,
        binding_registry: IGProductMarketBindingRegistry,
        *,
        candle_history_service: CandleHistoryService | None = None,
        reference_epics: tuple[str, ...] = (),
    ) -> None:
        if any(not epic.strip() for epic in reference_epics):
            raise ValueError("session reference EPICs must not be empty")
        if len(set(reference_epics)) != len(reference_epics):
            raise ValueError("session reference EPICs must be unique")
        self._binding_registry = binding_registry
        self._candles = candle_history_service or CandleHistoryService()
        self._reference_epics = frozenset(reference_epics)

    def ingest_m1_update(
        self,
        *,
        environment: IGEnvironment,
        account_id: str | None,
        chart_update: ChartCandleUpdate,
        resolution_seconds: int,
        price_basis: ChartPriceBasis,
    ) -> tuple[BoundSessionCandleSeries, ...]:
        bindings = self._binding_registry.for_reference_epic(chart_update.epic)
        if not bindings and chart_update.epic not in self._reference_epics:
            raise MarketNavigationCatalogError(
                "stream update reference EPIC has no explicit product binding"
            )

        # Keep one canonical session series per reference market. Product bindings project that
        # shared series instead of duplicating the same M1 updates for every derivative.
        self._candles.apply_session_m1_update(
            environment=environment,
            account_id=account_id,
            selected_product_epic=chart_update.epic,
            chart_source_epic=chart_update.epic,
            resolution_seconds=resolution_seconds,
            price_basis=price_basis,
            chart_update=chart_update,
        )
        return tuple(
            self.series_for_product(
                environment=environment,
                account_id=account_id,
                product_epic=binding.product_epic,
                resolution_seconds=resolution_seconds,
                price_basis=price_basis,
            )
            for binding in bindings
        )

    def reference_series(
        self,
        *,
        environment: IGEnvironment,
        account_id: str | None,
        reference_epic: str,
        resolution_seconds: int,
        price_basis: ChartPriceBasis,
    ) -> ChartCandleSeries:
        if (
            reference_epic not in self._reference_epics
            and not self._binding_registry.for_reference_epic(reference_epic)
        ):
            raise MarketNavigationCatalogError(
                "reference EPIC is outside the configured session universe"
            )
        return self._candles.session_series(
            environment=environment,
            account_id=account_id,
            selected_product_epic=reference_epic,
            chart_source_epic=reference_epic,
            resolution_seconds=resolution_seconds,
            price_basis=price_basis,
        )

    def series_for_product(
        self,
        *,
        environment: IGEnvironment,
        account_id: str | None,
        product_epic: str,
        resolution_seconds: int,
        price_basis: ChartPriceBasis,
    ) -> BoundSessionCandleSeries:
        binding = self._binding_registry.resolve(product_epic)
        series = self._candles.session_series(
            environment=environment,
            account_id=account_id,
            selected_product_epic=binding.product_epic,
            chart_source_epic=binding.reference_epic,
            resolution_seconds=resolution_seconds,
            price_basis=price_basis,
        )
        return BoundSessionCandleSeries(binding=binding, series=series)
