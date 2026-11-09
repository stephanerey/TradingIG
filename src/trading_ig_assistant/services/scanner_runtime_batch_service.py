"""Assemble the manual Scanner batch from exact bindings and session candles."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from trading_ig_assistant.app.config import IGEnvironment
from trading_ig_assistant.domain.ai_context import MarketContextSnapshot
from trading_ig_assistant.domain.analysis import ScoreComponentName
from trading_ig_assistant.domain.macro_context import MacroRibbonState
from trading_ig_assistant.domain.market_data import ChartPriceBasis
from trading_ig_assistant.domain.products import TradableProduct
from trading_ig_assistant.domain.scanner_profiles import ScannerProfileCatalog
from trading_ig_assistant.services.macro_context_service import MacroContextService
from trading_ig_assistant.services.market_navigation_catalog_service import (
    IGProductMarketBindingRegistry,
)
from trading_ig_assistant.services.market_scanner_service import (
    MarketScannerBatch,
    MarketScannerFailure,
    MarketScannerService,
)
from trading_ig_assistant.services.multi_market_session_candle_service import (
    MultiMarketSessionCandleService,
)
from trading_ig_assistant.services.product_context_projection_service import (
    ProductContextProjection,
)
from trading_ig_assistant.services.scanner_market_input_service import (
    ScannerMarketInputService,
)


@dataclass(frozen=True)
class ScannerRuntimeBatchResult:
    """Scanner batch plus the exact context projection used for each prepared product."""

    batch: MarketScannerBatch
    contexts: tuple[tuple[str, ProductContextProjection], ...]
    configured_product_epics: tuple[str, ...]

    def context_for(self, product_epic: str) -> ProductContextProjection:
        try:
            return dict(self.contexts)[product_epic]
        except KeyError as exc:
            raise KeyError(f"Scanner context is unavailable for {product_epic}") from exc


class ScannerRuntimeBatchService:
    """Join read-only runtime state without inferring products or scheduling refreshes."""

    def __init__(
        self,
        binding_registry: IGProductMarketBindingRegistry,
        session_candles: MultiMarketSessionCandleService,
        *,
        input_service: ScannerMarketInputService | None = None,
        scanner_service: MarketScannerService | None = None,
    ) -> None:
        self._bindings = binding_registry
        self._session_candles = session_candles
        self._inputs = input_service or ScannerMarketInputService(binding_registry)
        self._scanner = scanner_service or MarketScannerService()

    def scan(
        self,
        *,
        products: tuple[TradableProduct, ...],
        environment: IGEnvironment,
        account_id: str | None,
        resolution_seconds: int,
        price_basis: ChartPriceBasis,
        macro_state: MacroRibbonState,
        evaluated_at_utc: datetime,
        profile_catalog: ScannerProfileCatalog,
        ai_snapshot: MarketContextSnapshot | None = None,
        product_spreads: Mapping[str, Decimal | None] | None = None,
        fee_per_unit_per_side: Mapping[str, Decimal | None] | None = None,
        component_weights: Mapping[ScoreComponentName, Decimal] | None = None,
        candidate_threshold: Decimal = Decimal("75"),
        watch_threshold: Decimal = Decimal("60"),
    ) -> ScannerRuntimeBatchResult:
        macro_state = MacroContextService().revalidate_state(macro_state, evaluated_at_utc)
        product_by_epic = _index_products(products)
        spreads = product_spreads or {}
        fees = fee_per_unit_per_side or {}
        inputs = []
        contexts: list[tuple[str, ProductContextProjection]] = []
        preparation_failures: list[MarketScannerFailure] = []
        bindings = self._bindings.bindings()

        for binding in bindings:
            product = product_by_epic.get(binding.product_epic)
            if product is None:
                preparation_failures.append(
                    MarketScannerFailure(
                        product_epic=binding.product_epic,
                        reason="configured Scanner product is absent from product discovery",
                    )
                )
                continue
            try:
                bound_series = self._session_candles.series_for_product(
                    environment=environment,
                    account_id=account_id,
                    product_epic=product.epic,
                    resolution_seconds=resolution_seconds,
                    price_basis=price_basis,
                )
                prepared = self._inputs.prepare(
                    product=product,
                    candle_series=bound_series.series,
                    macro_state=macro_state,
                    evaluated_at_utc=evaluated_at_utc,
                    profile_catalog=profile_catalog,
                    account_id=account_id,
                    ai_snapshot=ai_snapshot,
                    product_spread=spreads.get(product.epic),
                    fee_per_unit_per_side=fees.get(product.epic),
                )
            except ValueError as exc:
                preparation_failures.append(
                    MarketScannerFailure(product_epic=product.epic, reason=str(exc))
                )
                continue
            inputs.append(prepared.scanner_input)
            contexts.append((product.epic, prepared.context))

        batch = self._scanner.scan(
            tuple(inputs),
            evaluated_at_utc=evaluated_at_utc,
            macro_state=macro_state,
            component_weights=component_weights,
            candidate_threshold=candidate_threshold,
            watch_threshold=watch_threshold,
        )
        combined_failures = tuple(
            sorted(
                (*preparation_failures, *batch.failures),
                key=lambda failure: (failure.product_epic, failure.reason),
            )
        )
        return ScannerRuntimeBatchResult(
            batch=MarketScannerBatch(
                items=batch.items,
                ranked_results=batch.ranked_results,
                failures=combined_failures,
                evaluated_at_utc=batch.evaluated_at_utc,
            ),
            contexts=tuple(sorted(contexts, key=lambda item: item[0])),
            configured_product_epics=tuple(binding.product_epic for binding in bindings),
        )


def _index_products(
    products: tuple[TradableProduct, ...],
) -> dict[str, TradableProduct]:
    indexed: dict[str, TradableProduct] = {}
    for product in products:
        previous = indexed.get(product.epic)
        if previous is not None and previous != product:
            raise ValueError(f"conflicting duplicate product identity: {product.epic}")
        indexed[product.epic] = product
    return indexed
