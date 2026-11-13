"""Collect bounded session-only reference candles for GUI V2 scanner analysis."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime

from PyQt5 import QtCore

from trading_ig_assistant.app.config import AppConfig
from trading_ig_assistant.app.runtime.trading_runtime import TradingRuntime
from trading_ig_assistant.domain.analysis import ScoreComponentName
from trading_ig_assistant.domain.macro_context import (
    DirectionalBias,
    EventRisk,
    MacroRibbonState,
    MarketRegime,
)
from trading_ig_assistant.domain.market_data import ChartCandleUpdate, ChartPriceBasis
from trading_ig_assistant.domain.market_navigation import (
    INITIAL_IG_REFERENCE_EPICS,
    IGProductMarketBinding,
)
from trading_ig_assistant.domain.markets import CanonicalUnderlyingId
from trading_ig_assistant.domain.products import (
    AssetClass,
    ProductDirection,
    ProductType,
    TradableProduct,
)
from trading_ig_assistant.services.market_navigation_catalog_service import (
    IGProductMarketBindingRegistry,
    MarketNavigationCatalogError,
)
from trading_ig_assistant.services.multi_market_session_candle_service import (
    MultiMarketSessionCandleService,
)
from trading_ig_assistant.services.scanner_preview_service import (
    chart_series_to_closed_indicator_input,
    required_closed_candles,
)
from trading_ig_assistant.services.scanner_profile_resolver import (
    resolve_scanner_profiles_from_catalog,
)
from trading_ig_assistant.services.scanner_runtime_batch_service import ScannerRuntimeBatchService
from trading_ig_assistant.services.technical_research_journal import (
    TechnicalResearchJournalError,
    TechnicalResearchRecorder,
)


class ScannerSessionController(QtCore.QObject):
    """Ingest chart ticks only; never loads history and never creates an order."""

    error = QtCore.pyqtSignal(str)

    def __init__(
        self,
        runtime: TradingRuntime,
        binding_registry: IGProductMarketBindingRegistry,
        config: AppConfig,
        *,
        reference_epics: tuple[str, ...],
        now_provider: Callable[[], datetime] | None = None,
        research_recorder: TechnicalResearchRecorder | None = None,
    ) -> None:
        super().__init__()
        self._runtime = runtime
        self._configured_bindings = binding_registry
        self._bindings = _reference_analysis_registry(
            binding_registry,
            reference_epics=reference_epics,
        )
        self._config = config
        self._reference_epics = frozenset(reference_epics)
        self._now_provider = now_provider or (lambda: datetime.now(UTC))
        self._research_recorder = research_recorder
        self._candles = MultiMarketSessionCandleService(
            self._bindings,
            reference_epics=reference_epics,
        )
        self._scanner = ScannerRuntimeBatchService(self._bindings, self._candles)
        self._product_fallback_bindings = _exact_product_analysis_registry(binding_registry)
        self._product_fallback_candles = MultiMarketSessionCandleService(
            self._product_fallback_bindings,
            reference_epics=tuple(
                binding.product_epic
                for binding in self._product_fallback_bindings.bindings()
            ),
        )
        self._product_fallback_scanner = ScannerRuntimeBatchService(
            self._product_fallback_bindings,
            self._product_fallback_candles,
        )
        self._unavailable_reference_epics: set[str] = set()
        self._last_analyzed_counts: dict[tuple[str | None, str], int] = {}

    @QtCore.pyqtSlot()
    def reset_context(self) -> None:
        """Forget account-specific entitlement decisions and session candles."""

        self._candles = MultiMarketSessionCandleService(
            self._bindings,
            reference_epics=tuple(self._reference_epics),
        )
        self._scanner = ScannerRuntimeBatchService(self._bindings, self._candles)
        self._product_fallback_candles = MultiMarketSessionCandleService(
            self._product_fallback_bindings,
            reference_epics=tuple(
                binding.product_epic
                for binding in self._product_fallback_bindings.bindings()
            ),
        )
        self._product_fallback_scanner = ScannerRuntimeBatchService(
            self._product_fallback_bindings,
            self._product_fallback_candles,
        )
        self._unavailable_reference_epics.clear()
        self._last_analyzed_counts.clear()

    @QtCore.pyqtSlot(str)
    def enable_product_quote_fallback(self, reference_epic: str) -> None:
        """Authorize exact-product PRICE candles only for a denied reference CHART."""

        normalized = reference_epic.strip()
        if normalized:
            self._unavailable_reference_epics.add(normalized)

    @QtCore.pyqtSlot(object)
    def ingest_chart_update(self, value: object) -> None:
        if not isinstance(value, ChartCandleUpdate) or value.epic not in self._reference_epics:
            return
        connection = self._runtime.active_ig_connection
        if connection is None:
            return
        try:
            self._candles.ingest_m1_update(
                environment=connection.environment,
                account_id=connection.current_account_id,
                chart_update=value,
                resolution_seconds=60,
                price_basis=ChartPriceBasis.BID,
            )
            series = self._candles.reference_series(
                environment=connection.environment,
                account_id=connection.current_account_id,
                reference_epic=value.epic,
                resolution_seconds=60,
                price_basis=ChartPriceBasis.BID,
            )
        except (MarketNavigationCatalogError, ValueError) as exc:
            self.error.emit(str(exc))
            return
        observed = len(chart_series_to_closed_indicator_input(series).candles)
        key = (connection.current_account_id, value.epic)
        if self._last_analyzed_counts.get(key) == observed:
            return
        required = self._required_closed_candles(
            value.epic,
            connection.current_account_id,
        )
        self._runtime.publish_scanner_candle_progress(
            generation_id=self._runtime.generation_id,
            reference_epic=value.epic,
            observed_candles=observed,
            required_candles=required,
            generated_at_utc=self._now_provider(),
        )
        self._last_analyzed_counts[key] = observed
        if observed < 2:
            return
        self._run_analysis()

    @QtCore.pyqtSlot(object)
    def ingest_product_chart_update(self, value: object) -> None:
        """Analyze exact-product M1 candles when its reference CHART is unavailable."""

        if not isinstance(value, ChartCandleUpdate):
            return
        connection = self._runtime.active_ig_connection
        if connection is None:
            return
        try:
            configured_binding = self._configured_bindings.resolve(value.epic)
        except MarketNavigationCatalogError:
            return
        if configured_binding.reference_epic not in self._unavailable_reference_epics:
            return
        try:
            self._product_fallback_candles.ingest_m1_update(
                environment=connection.environment,
                account_id=connection.current_account_id,
                chart_update=value,
                resolution_seconds=60,
                price_basis=ChartPriceBasis.BID,
            )
            series = self._product_fallback_candles.reference_series(
                environment=connection.environment,
                account_id=connection.current_account_id,
                reference_epic=value.epic,
                resolution_seconds=60,
                price_basis=ChartPriceBasis.BID,
            )
        except (MarketNavigationCatalogError, ValueError) as exc:
            self.error.emit(str(exc))
            return
        observed = len(chart_series_to_closed_indicator_input(series).candles)
        key = (connection.current_account_id, value.epic)
        if self._last_analyzed_counts.get(key) == observed:
            return
        required = self._required_closed_candles_for_underlying(
            configured_binding.canonical_underlying_id,
            connection.current_account_id,
        )
        self._runtime.publish_scanner_candle_progress(
            generation_id=self._runtime.generation_id,
            reference_epic=configured_binding.reference_epic,
            observed_candles=observed,
            required_candles=required,
            generated_at_utc=self._now_provider(),
        )
        self._last_analyzed_counts[key] = observed
        if observed < 2:
            return
        self._run_analysis(
            scanner=self._product_fallback_scanner,
            binding_registry=self._product_fallback_bindings,
            provenance_marker="gui-v2:exact-product-price-candle-fallback",
        )

    def _run_analysis(
        self,
        *,
        scanner: ScannerRuntimeBatchService | None = None,
        binding_registry: IGProductMarketBindingRegistry | None = None,
        provenance_marker: str | None = None,
    ) -> None:
        connection = self._runtime.active_ig_connection
        if connection is None:
            return
        now = self._now_provider()
        products = tuple(_product_from_row(row) for row in self._runtime.read_catalogue().rows)
        if not products:
            return
        spreads = {
            row.epic: (
                row.offer - row.bid if row.offer is not None and row.bid is not None else None
            )
            for row in self._runtime.read_catalogue().rows
        }
        fees = {
            product.epic: (
                None
                if product.asset_class is AssetClass.SHARES
                else self._config.scanner_execution_costs.fee_for_product_type(product.product_type)
            )
            for product in products
        }
        scoring = self._config.scanner_scoring
        weights = {
            ScoreComponentName(name): weight for name, weight in scoring.component_weights().items()
        }
        ai_snapshot = self._runtime.read_market_context()
        macro = (
            ai_snapshot.macro_state
            if ai_snapshot is not None
            else MacroRibbonState(
                schema_version=1,
                regime=MarketRegime.UNKNOWN,
                index_bias=DirectionalBias.UNKNOWN,
                gold_bias=DirectionalBias.UNKNOWN,
                event_risk=EventRisk.UNKNOWN,
                signals=(),
                generated_at_utc=now,
                reason_codes=("GUI_V2_MACRO_CONTEXT_UNAVAILABLE",),
                provenance=("gui-v2-session-scanner",),
            )
        )
        try:
            result = (scanner or self._scanner).scan(
                products=products,
                environment=connection.environment,
                account_id=connection.current_account_id,
                resolution_seconds=60,
                price_basis=ChartPriceBasis.BID,
                macro_state=macro,
                ai_snapshot=ai_snapshot,
                evaluated_at_utc=now,
                profile_catalog=self._config.scanner_profiles,
                product_spreads=spreads,
                fee_per_unit_per_side=fees,
                component_weights=weights,
                candidate_threshold=scoring.candidate_threshold,
                watch_threshold=scoring.watch_threshold,
            )
        except ValueError as exc:
            self.error.emit(str(exc))
            return
        if provenance_marker:
            result = replace(
                result,
                batch=replace(
                    result.batch,
                    items=tuple(
                        replace(
                            item,
                            preview=replace(
                                item.preview,
                                signals=tuple(
                                    replace(
                                        signal,
                                        provenance=tuple(
                                            dict.fromkeys(
                                                (*signal.provenance, provenance_marker)
                                            )
                                        ),
                                    )
                                    for signal in item.preview.signals
                                ),
                            ),
                        )
                        for item in result.batch.items
                    ),
                ),
            )
        self._runtime.publish_scanner_analysis(
            generation_id=self._runtime.generation_id,
            result=result,
            binding_registry=binding_registry or self._bindings,
            generated_at_utc=now,
        )
        if self._research_recorder is not None:
            try:
                self._research_recorder.record(
                    result,
                    environment=connection.environment,
                    account_id=connection.current_account_id,
                )
            except TechnicalResearchJournalError as exc:
                self.error.emit(str(exc))

    def _required_closed_candles(
        self,
        reference_epic: str,
        account_id: str | None,
    ) -> int:
        underlying_by_epic = {
            epic: underlying for underlying, epic in INITIAL_IG_REFERENCE_EPICS
        }
        profiles = resolve_scanner_profiles_from_catalog(
            self._config.scanner_profiles,
            canonical_underlying_id=underlying_by_epic[reference_epic],
            account_id=account_id,
        )
        return max(required_closed_candles(item.profile) for item in profiles)

    def _required_closed_candles_for_underlying(
        self,
        canonical_underlying_id: CanonicalUnderlyingId,
        account_id: str | None,
    ) -> int:
        profiles = resolve_scanner_profiles_from_catalog(
            self._config.scanner_profiles,
            canonical_underlying_id=canonical_underlying_id,
            account_id=account_id,
        )
        return max(required_closed_candles(item.profile) for item in profiles)


def _product_from_row(row: object) -> TradableProduct:
    return TradableProduct(
        epic=row.epic,
        name=row.name,
        product_type=_enum_or_default(ProductType, row.product_type, ProductType.UNKNOWN),
        direction=_enum_or_default(ProductDirection, row.direction, ProductDirection.UNKNOWN),
        currency=row.currency,
        status=row.status,
        asset_class=_enum_or_default(AssetClass, row.asset_class, AssetClass.OTHER),
        bid=float(row.bid) if row.bid is not None else None,
        offer=float(row.offer) if row.offer is not None else None,
        percent_change=(float(row.percent_change) if row.percent_change is not None else None),
    )


def _reference_analysis_registry(
    configured: IGProductMarketBindingRegistry,
    *,
    reference_epics: tuple[str, ...],
) -> IGProductMarketBindingRegistry:
    """Add analysis-only self bindings without changing persisted trading bindings."""

    by_product = {binding.product_epic: binding for binding in configured.bindings()}
    underlying_by_epic = {
        epic: underlying for underlying, epic in INITIAL_IG_REFERENCE_EPICS
    }
    for reference_epic in reference_epics:
        if reference_epic in by_product:
            continue
        by_product[reference_epic] = IGProductMarketBinding(
            product_epic=reference_epic,
            canonical_underlying_id=underlying_by_epic[reference_epic],
            reference_epic=reference_epic,
            provenance=("gui-v2:analysis-only-reference-market",),
        )
    return IGProductMarketBindingRegistry(tuple(by_product.values()))


def _exact_product_analysis_registry(
    configured: IGProductMarketBindingRegistry,
) -> IGProductMarketBindingRegistry:
    """Keep exact product identity when M1 candles originate from its PRICE stream."""

    return IGProductMarketBindingRegistry(
        tuple(
            IGProductMarketBinding(
                product_epic=binding.product_epic,
                canonical_underlying_id=binding.canonical_underlying_id,
                reference_epic=binding.product_epic,
                provenance=(
                    *binding.provenance,
                    "gui-v2:exact-product-price-candle-fallback",
                ),
            )
            for binding in configured.bindings()
        )
    )


def _enum_or_default(enum_type: object, value: str, default: object) -> object:
    try:
        return enum_type(value)
    except ValueError:
        return default
