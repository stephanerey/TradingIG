"""Minimal GUI shell for P01."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sqlite3
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from PyQt5 import QtCore, QtWidgets

from trading_ig_assistant.adapters.credentials import SecretValue, build_default_credential_store
from trading_ig_assistant.adapters.ig_rest import (
    HistoricalPriceFetchResult,
    IGAPIError,
    IGRestAdapter,
    is_historical_allowance_error,
    is_invalid_security_token_error,
    load_prices_with_adaptive_fallback,
)
from trading_ig_assistant.adapters.ig_streaming import IGStreamingAdapter
from trading_ig_assistant.adapters.news_provider import NewsProvider
from trading_ig_assistant.adapters.official_rss_news import (
    ecb_press_news_provider,
    federal_reserve_monetary_news_provider,
)
from trading_ig_assistant.app.config import (
    AppConfig,
    IGConnectionProfileConfig,
    IGEnvironment,
    WorkspaceState,
    default_config_path,
    default_paper_database_path,
    load_config,
    save_config,
)
from trading_ig_assistant.app.projections.account_projection import (
    build_account_header_projection,
    build_runtime_health_projection,
)
from trading_ig_assistant.app.projections.dashboard_projection import (
    build_paper_dashboard_projection,
    merge_account_metrics_into_dashboard,
)
from trading_ig_assistant.app.runtime.ig_session_runtime import ActiveIGConnection
from trading_ig_assistant.app.runtime.trading_runtime import TradingRuntime
from trading_ig_assistant.app.streaming_bridge import StreamingEventBridge
from trading_ig_assistant.app.ui_facade import RuntimeUIFacade
from trading_ig_assistant.domain.ai_context import (
    AIAnalysisStatus,
    MarketContextSnapshot,
    is_ai_citation_eligible,
)
from trading_ig_assistant.domain.analysis import ScoreBand, ScoreComponentName
from trading_ig_assistant.domain.context_sources import NewsCollectionSnapshot
from trading_ig_assistant.domain.instruments import Account
from trading_ig_assistant.domain.macro_context import ContextSignal
from trading_ig_assistant.domain.market_data import (
    CandleSource,
    ChartCandleSeries,
    ChartCandleUpdate,
    ChartPriceBasis,
    PriceSeries,
    Quote,
)
from trading_ig_assistant.domain.market_navigation import initial_ig_reference_epics
from trading_ig_assistant.domain.products import AssetClass, ProductType, TradableProduct
from trading_ig_assistant.persistence.paper_session_codec import (
    decode_paper_session_state,
    encode_paper_session_state,
)
from trading_ig_assistant.persistence.repositories import (
    CorruptPaperSnapshotError,
    PaperSessionSnapshotRepository,
)
from trading_ig_assistant.persistence.sqlite_store import (
    MigrationError,
    SQLiteStore,
    UnsupportedSchemaError,
)
from trading_ig_assistant.services.candle_aggregation_service import (
    CandleAggregationService,
)
from trading_ig_assistant.services.candle_history_service import (
    CandleHistoryService,
)
from trading_ig_assistant.services.candle_history_service import (
    _stream_cache_root as _stream_candle_cache_root,
)
from trading_ig_assistant.services.ig_connection_service import (
    AccountSwitchNotConfirmedError,
    IGConnectionRequest,
)
from trading_ig_assistant.services.macro_context_service import MacroContextService
from trading_ig_assistant.services.market_navigation_catalog_service import (
    IGProductMarketBindingRegistry,
    MarketNavigationCatalogError,
)
from trading_ig_assistant.services.multi_market_session_candle_service import (
    MultiMarketSessionCandleService,
)
from trading_ig_assistant.services.news_ai_evidence_service import (
    build_news_ai_evidence_signals,
)
from trading_ig_assistant.services.news_context_health_service import (
    build_news_source_health_signal,
)
from trading_ig_assistant.services.openai_context_runtime_service import (
    run_openai_market_context,
)
from trading_ig_assistant.services.paper_session import (
    PaperSessionService,
    PaperTicketSubmission,
)
from trading_ig_assistant.services.product_context_projection_service import (
    ProductContextProjectionService,
    build_context_score_component,
)
from trading_ig_assistant.services.product_discovery_service import (
    ProductDiscoveryResult,
    ProductDiscoveryService,
    read_discovery_report,
    write_discovery_report,
)
from trading_ig_assistant.services.quote_candle_fallback_service import (
    QuoteCandleFallbackService,
)
from trading_ig_assistant.services.scanner_component_service import ScannerComponentService
from trading_ig_assistant.services.scanner_preview_service import build_scanner_preview
from trading_ig_assistant.services.scanner_runtime_batch_service import (
    ScannerRuntimeBatchResult,
    ScannerRuntimeBatchService,
)
from trading_ig_assistant.services.setup_scoring_service import build_banded_score_component
from trading_ig_assistant.services.trading_economics_calendar_runtime import (
    TradingEconomicsRuntimeResult,
    refresh_trading_economics_calendar,
)
from trading_ig_assistant.ui.about_dialog import AboutDialog
from trading_ig_assistant.ui.account_status_widget import AccountStatusRibbonWidget
from trading_ig_assistant.ui.chart_view import ChartView
from trading_ig_assistant.ui.economic_calendar_refresh import (
    CalendarRuntimeRunner,
    EconomicCalendarRefreshWorker,
)
from trading_ig_assistant.ui.log_view_dialog import LogViewDialog
from trading_ig_assistant.ui.macro_ribbon_widget import MacroRibbonWidget
from trading_ig_assistant.ui.official_news_refresh import (
    OfficialNewsRefreshResult,
    OfficialNewsRefreshWorker,
)
from trading_ig_assistant.ui.openai_context_refresh import (
    OpenAIContextRefreshWorker,
    OpenAIContextRunner,
)
from trading_ig_assistant.ui.openai_web_research import WebResearchDialog
from trading_ig_assistant.ui.paper_portfolio_view import PaperPortfolioWidget
from trading_ig_assistant.ui.product_selector import ProductSelectorWidget
from trading_ig_assistant.ui.scanner_view import ScannerPreviewWidget
from trading_ig_assistant.ui.settings_dialog import SettingsDialog
from trading_ig_assistant.utils.logging_config import configure_logging, emit_session_banner
from trading_ig_assistant.utils.redaction import mask_identifier

LOGGER = logging.getLogger(__name__)
PRODUCT_STREAM_ITEMS_LIMIT = 20
CHART_STREAM_ITEMS_LIMIT = 6
HISTORY_SNAPSHOT_POINTS = 32
HISTORY_CACHE_REFRESH_TTL = timedelta(seconds=60)
HISTORY_ALLOWANCE_PROBE_COOLDOWN = timedelta(hours=6)
OFFICIAL_NEWS_REFRESH_INTERVAL_MS = 15 * 60 * 1000
OFFICIAL_NEWS_HEALTH_VALIDITY = timedelta(minutes=15)
OPENAI_NEWS_EVIDENCE_LIMIT = 20
OPENAI_CONTEXT_REFRESH_INTERVAL_MS = 15 * 60 * 1000
CALENDAR_REFRESH_INTERVAL_MS = 15 * 60 * 1000
SESSION_ONLY_CANDLES = True


def _prioritized_price_epics(
    selected_product: TradableProduct | None,
    visible_epics: list[str],
    chart_product: TradableProduct | None,
) -> list[str]:
    """Keep the selected product inside the capped direct-quote subscription."""
    candidates = [
        selected_product.epic if selected_product is not None else "",
        *visible_epics,
        chart_product.epic if chart_product is not None else "",
    ]
    return list(dict.fromkeys(epic for epic in candidates if epic))


def _prioritized_chart_epics(
    selected_chart_product: TradableProduct | None,
    baseline_reference_epics: tuple[str, ...],
) -> list[str]:
    candidates = [
        selected_chart_product.epic if selected_chart_product is not None else "",
        *baseline_reference_epics,
    ]
    epics = list(dict.fromkeys(epic for epic in candidates if epic))
    if len(epics) > CHART_STREAM_ITEMS_LIMIT:
        raise ValueError("configured chart stream universe exceeds the bounded item limit")
    return epics


def _chart_source_overrides_from_config(config: AppConfig) -> dict[str, str]:
    overrides = dict(config.chart_source_overrides)
    for binding in config.product_market_bindings:
        overrides[binding.product_epic] = binding.reference_epic
    return overrides


@dataclass(frozen=True)
class OpenAIContextSession:
    model: str
    max_output_tokens: int
    automatic_refresh: bool = False


@dataclass
class CachedHistoryEntry:
    series: PriceSeries
    saved_at: datetime


@dataclass
class HistoricalAllowanceState:
    exhausted: bool = False
    exhausted_at: datetime | None = None
    last_error: str | None = None
    blocked_until: datetime | None = None
    affected_account_id: str | None = None
    affected_epic: str | None = None
    remaining_points: int | None = None
    total_points: int | None = None

    def is_blocked(
        self,
        *,
        account_id: str | None,
        epic: str | None = None,
    ) -> bool:
        if not self.exhausted:
            return False
        if self.blocked_until is not None and datetime.now(UTC) >= self.blocked_until:
            return False
        if self.affected_account_id and account_id and self.affected_account_id != account_id:
            return False
        if self.affected_epic in (None, "*"):
            return True
        return epic == self.affected_epic


@dataclass(frozen=True)
class ResolvedChartSource:
    product: TradableProduct
    method: str


@dataclass(frozen=True)
class PriceHistoryRequest:
    generation: int
    environment: IGEnvironment
    account_id: str | None
    selected_product_epic: str
    products: tuple[TradableProduct, ...]
    resolution: str
    range_key: str
    price_basis: ChartPriceBasis
    max_points: int


@dataclass(frozen=True)
class PriceHistoryAttempt:
    product: TradableProduct
    result: HistoricalPriceFetchResult


@dataclass(frozen=True)
class PriceHistoryLoadResult:
    request: PriceHistoryRequest
    attempts: tuple[PriceHistoryAttempt, ...]


@dataclass(frozen=True)
class PriceHistoryFailure:
    request: PriceHistoryRequest
    message: str


class ConnectionWorker(QtCore.QObject):
    succeeded = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()

    def __init__(
        self,
        request: IGConnectionRequest,
        runtime: TradingRuntime | None = None,
    ) -> None:
        super().__init__()
        self._request = request
        self._runtime = runtime or TradingRuntime(
            ig_adapter_factory=lambda environment: IGRestAdapter(
                environment=environment,
                read_only=True,
            )
        )

    @QtCore.pyqtSlot()
    def run(self) -> None:
        LOGGER.debug("Connection worker start environment=%s", self._request.environment.value)
        try:
            result = self._runtime.connect_ig_read_only(self._request)
            LOGGER.debug(
                "Connection worker success environment=%s accounts=%s",
                result.environment.value,
                len(result.accounts),
            )
            self.succeeded.emit(result)
        except Exception as exc:
            LOGGER.debug(
                "Connection worker failed environment=%s error=%s",
                self._request.environment.value,
                exc,
            )
            self.failed.emit(str(exc))
        finally:
            LOGGER.debug(
                "Connection worker finished environment=%s",
                self._request.environment.value,
            )
            self.finished.emit()


class ProductDiscoveryWorker(QtCore.QObject):
    succeeded = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()

    def __init__(
        self,
        adapter: IGRestAdapter,
        environment: IGEnvironment,
        search_term: str | None = None,
    ) -> None:
        super().__init__()
        self._adapter = adapter
        self._environment = environment
        self._search_term = search_term

    @QtCore.pyqtSlot()
    def run(self) -> None:
        try:
            LOGGER.debug(
                "Product discovery worker start environment=%s active_account=%s",
                self._environment.value,
                mask_identifier(
                    self._adapter.session.current_account_id if self._adapter.session else None
                ),
            )
            service = ProductDiscoveryService(self._adapter)
            results = [
                service.search_product_summaries(self._search_term)
                if self._search_term is not None
                else service.discover_all_products(max_details=0)
            ]
            if _results_contain_invalid_security_token(results):
                raise IGAPIError("invalid-security-token: IG rejected the discovery session token.")
            LOGGER.debug(
                "Product discovery worker success environment=%s products=%s",
                self._environment.value,
                sum(len(result.products) for result in results),
            )
            self.succeeded.emit(results)
        except Exception as exc:
            LOGGER.debug(
                "Product discovery worker failed environment=%s retryable=%s error=%s",
                self._environment.value,
                is_invalid_security_token_error(exc),
                exc,
            )
            self.failed.emit(str(exc))
        finally:
            LOGGER.debug(
                "Product discovery worker finished environment=%s",
                self._environment.value,
            )
            self.finished.emit()


class PriceHistoryWorker(QtCore.QObject):
    succeeded = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(object)
    finished = QtCore.pyqtSignal()

    def __init__(self, adapter: IGRestAdapter, request: PriceHistoryRequest) -> None:
        super().__init__()
        self._adapter = adapter
        self._request = request

    @QtCore.pyqtSlot()
    def run(self) -> None:
        try:
            LOGGER.debug(
                "Price history worker start selected_epic=%s candidates=%s",
                self._request.selected_product_epic,
                [product.epic for product in self._request.products],
            )
            attempts: list[PriceHistoryAttempt] = []
            for product in self._request.products:
                result = load_prices_with_adaptive_fallback(
                    self._adapter,
                    product.epic,
                    resolution=self._request.resolution,
                    requested_max_points=self._request.max_points,
                    stop_on_allowance_error=product.product_type == ProductType.CASH_OR_DFB,
                )
                attempts.append(PriceHistoryAttempt(product=product, result=result))
                if result.series is not None:
                    break
                if (
                    product.product_type == ProductType.CASH_OR_DFB
                    and _history_fallback_is_historical_allowance(result)
                ):
                    break
            LOGGER.debug(
                "Price history worker complete selected_epic=%s attempts=%s",
                self._request.selected_product_epic,
                len(attempts),
            )
            self.succeeded.emit(
                PriceHistoryLoadResult(
                    request=self._request,
                    attempts=tuple(attempts),
                )
            )
        except Exception as exc:
            LOGGER.debug(
                "Price history worker failed selected_epic=%s error=%s",
                self._request.selected_product_epic,
                exc,
            )
            self.failed.emit(PriceHistoryFailure(request=self._request, message=str(exc)))
        finally:
            LOGGER.debug(
                "Price history worker finished selected_epic=%s",
                self._request.selected_product_epic,
            )
            self.finished.emit()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(
        self,
        *,
        workspace_persistence: bool = False,
        paper_database_path: Path | None = None,
        official_news_providers: tuple[NewsProvider, ...] = (),
        official_news_refresh_interval_ms: int = OFFICIAL_NEWS_REFRESH_INTERVAL_MS,
        openai_context_runner: OpenAIContextRunner = run_openai_market_context,
        openai_key_reader=None,
        openai_context_refresh_interval_ms: int = OPENAI_CONTEXT_REFRESH_INTERVAL_MS,
        calendar_context_runner: CalendarRuntimeRunner = refresh_trading_economics_calendar,
        calendar_key_reader=None,
        calendar_refresh_interval_ms: int = CALENDAR_REFRESH_INTERVAL_MS,
        projection_runtime: TradingRuntime | None = None,
    ) -> None:
        super().__init__()
        LOGGER.debug("MainWindow initialization start")
        self.setWindowTitle("Trading IG Assistant - analyse et simulation locale")
        self.resize(1280, 820)
        self._config_path = default_config_path()
        self._paper_database_path = paper_database_path or default_paper_database_path()
        self._config = load_config(self._config_path)
        self._projection_runtime = projection_runtime or TradingRuntime(
            ig_adapter_factory=lambda environment: IGRestAdapter(
                environment=environment,
                read_only=True,
            )
        )
        self.ui_facade = RuntimeUIFacade(self._projection_runtime)
        self._stream_projection_status = "disconnected"
        self._workspace_persistence = workspace_persistence
        self._credential_store = self._build_credential_store()
        if official_news_refresh_interval_ms <= 0:
            raise ValueError("official news refresh interval must be positive")
        self._official_news_providers = official_news_providers
        self._official_news_thread: QtCore.QThread | None = None
        self._official_news_worker: OfficialNewsRefreshWorker | None = None
        self._official_news_refresh_timer = QtCore.QTimer(self)
        self._official_news_refresh_timer.setInterval(official_news_refresh_interval_ms)
        self._official_news_refresh_timer.timeout.connect(self._refresh_official_news)
        self._latest_news_snapshots: tuple[NewsCollectionSnapshot, ...] = ()
        self._latest_macro_state = MacroContextService().build_state((), datetime.now(UTC))
        self._latest_ai_context_snapshot: MarketContextSnapshot | None = None
        self._ai_expiry_timer = QtCore.QTimer(self)
        self._ai_expiry_timer.setSingleShot(True)
        self._ai_expiry_timer.timeout.connect(self._refresh_ai_presentation)
        self._openai_context_runner = openai_context_runner
        self._openai_key_reader = openai_key_reader or (
            lambda: os.environ.get("OPENAI_API_KEY", "")
        )
        self._openai_context_session: OpenAIContextSession | None = None
        self._openai_context_thread: QtCore.QThread | None = None
        self._openai_context_worker: OpenAIContextRefreshWorker | None = None
        if openai_context_refresh_interval_ms <= 0:
            raise ValueError("OpenAI context refresh interval must be positive")
        self._openai_context_refresh_timer = QtCore.QTimer(self)
        self._openai_context_refresh_timer.setInterval(openai_context_refresh_interval_ms)
        self._openai_context_refresh_timer.timeout.connect(self._refresh_openai_context_automatic)
        if calendar_refresh_interval_ms <= 0:
            raise ValueError("calendar refresh interval must be positive")
        self._calendar_context_runner = calendar_context_runner
        self._calendar_key_reader = calendar_key_reader or (
            lambda: os.environ.get("TRADING_ECONOMICS_API_KEY", "")
        )
        self._calendar_runtime_result: TradingEconomicsRuntimeResult | None = None
        self._calendar_context_thread: QtCore.QThread | None = None
        self._calendar_context_worker: EconomicCalendarRefreshWorker | None = None
        self._calendar_refresh_timer = QtCore.QTimer(self)
        self._calendar_refresh_timer.setInterval(calendar_refresh_interval_ms)
        self._calendar_refresh_timer.timeout.connect(self._refresh_calendar_context)
        self._connection_thread: QtCore.QThread | None = None
        self._connection_worker: ConnectionWorker | None = None
        self._discovery_thread: QtCore.QThread | None = None
        self._discovery_worker: ProductDiscoveryWorker | None = None
        self._targeted_discovery_origin: tuple[object, str | None, int] | None = None
        self._price_history_thread: QtCore.QThread | None = None
        self._price_history_worker: PriceHistoryWorker | None = None
        self._price_history_generation = 0
        self._pending_history_reload = False
        self._pending_history_force_refresh = False
        self._price_history_cache: dict[
            tuple[str, str, str, str, int],
            CachedHistoryEntry,
        ] = {}
        self._candle_aggregation_service = CandleAggregationService()
        self._candle_history_service = CandleHistoryService(
            candle_aggregation_service=self._candle_aggregation_service,
            cache_root_provider=_stream_candle_cache_root,
        )
        self._scanner_candle_history_service = CandleHistoryService(
            cache_root_provider=_stream_candle_cache_root,
        )
        self._scanner_binding_registry = IGProductMarketBindingRegistry(
            self._config.product_market_bindings
        )
        self._scanner_session_candles = MultiMarketSessionCandleService(
            self._scanner_binding_registry,
            candle_history_service=self._scanner_candle_history_service,
            reference_epics=initial_ig_reference_epics(),
        )
        self._latest_scanner_runtime_batch: ScannerRuntimeBatchResult | None = None
        self._chart_candle_series: ChartCandleSeries | None = None
        self._chart_source_resolution_method = "selected fallback"
        self._live_chart_scale_requested = "1MINUTE"
        self._live_chart_scale_actual = "1MINUTE"
        self._aggregation_mode = "direct"
        self._chart_stream_scale_fallback_attempted = False
        self._chart_stream_permission_fallback_attempted = False
        self._chart_quote_candle_fallback_active = False
        self._quote_candle_fallback_service = QuoteCandleFallbackService()
        self._last_history_gap_refresh_key: tuple[str, int, str, str] | None = None
        self._last_history_reload_price_basis: object | None = None
        self._history_allowance_state = HistoricalAllowanceState()
        self._api_allowance_exceeded = False
        self._auth_locked_out = False
        self._selected_product: TradableProduct | None = None
        self._chart_product: TradableProduct | None = None
        self._visible_price_epics: list[str] = []
        self._loaded_cache_environment: IGEnvironment | None = None
        self._streaming_adapter: IGStreamingAdapter | None = None
        self._chart_stream_epics: tuple[str, ...] = ()
        self._stream_generation = 0
        self._streaming_bridge: StreamingEventBridge | None = None
        self._paper_session = PaperSessionService()
        self._paper_freshness_timer = QtCore.QTimer(self)
        self._paper_freshness_timer.setInterval(1000)
        self._paper_freshness_timer.timeout.connect(self._refresh_paper_freshness)
        self._build_menu()
        self._build_layout()
        self._publish_runtime_projections()
        if self._workspace_persistence:
            self._restore_workspace_state()
        self._load_cached_discovery_results()
        if self._official_news_providers:
            self._official_news_refresh_timer.start()
            QtCore.QTimer.singleShot(0, self._refresh_official_news)
        LOGGER.debug("MainWindow initialization complete")

    @property
    def _active_connection(self) -> ActiveIGConnection | None:
        return self._projection_runtime.active_ig_connection

    @_active_connection.setter
    def _active_connection(self, connection: ActiveIGConnection | None) -> None:
        self._projection_runtime.replace_ig_connection_for_legacy_migration(connection)

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        quit_action = file_menu.addAction("Quit")
        quit_action.triggered.connect(self.close)

        tools_menu = self.menuBar().addMenu("&Tools")
        settings_action = tools_menu.addAction("Settings")
        settings_action.triggered.connect(self._open_settings)
        self._official_news_refresh_action = tools_menu.addAction("Refresh official source health")
        self._official_news_refresh_action.setEnabled(bool(self._official_news_providers))
        self._official_news_refresh_action.triggered.connect(self._refresh_official_news)
        self._openai_context_action = tools_menu.addAction(
            "Analyser le contexte officiel avec OpenAI (manuel/facturé)"
        )
        self._openai_context_action.setEnabled(False)
        self._openai_context_action.triggered.connect(self._refresh_openai_context)
        web_research_action = tools_menu.addAction(
            "Recherche web du marché avec OpenAI (manuel/facturé)"
        )
        web_research_action.triggered.connect(self._open_web_research)
        self._calendar_context_action = tools_menu.addAction("Refresh macro calendar")
        self._calendar_context_action.setEnabled(False)
        self._calendar_context_action.triggered.connect(self._refresh_calendar_context)
        disabled_action = tools_menu.addAction("Live trading disabled")
        disabled_action.setEnabled(False)

        help_menu = self.menuBar().addMenu("&Help")
        help_action = help_menu.addAction("Help")
        help_action.triggered.connect(self._show_help)
        log_action = help_menu.addAction("View log")
        log_action.triggered.connect(self._show_log)
        about_action = help_menu.addAction("About TradingIG")
        about_action.triggered.connect(self._show_about)

    def _build_layout(self) -> None:
        root = QtWidgets.QWidget()
        root_layout = QtWidgets.QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSizeConstraint(QtWidgets.QLayout.SetNoConstraint)

        self.account_status = AccountStatusRibbonWidget()
        self.account_status.setMinimumSize(0, 0)
        self.account_status.setSizePolicy(
            QtWidgets.QSizePolicy.Ignored,
            QtWidgets.QSizePolicy.Preferred,
        )
        self.account_status.connect_requested.connect(self._connect_environment)
        self.account_status.disconnect_requested.connect(self._disconnect)
        self.account_status.settings_requested.connect(self._open_settings)
        self.account_status.account_selected.connect(self._select_account)
        root_layout.addWidget(self.account_status)
        self.macro_ribbon = MacroRibbonWidget()
        self.macro_ribbon.setMinimumSize(0, 0)
        self.macro_ribbon.setSizePolicy(
            QtWidgets.QSizePolicy.Ignored,
            QtWidgets.QSizePolicy.Preferred,
        )
        root_layout.addWidget(self.macro_ribbon)

        self.body_splitter = QtWidgets.QSplitter()
        self.body_splitter.setOrientation(QtCore.Qt.Horizontal)
        self.body_splitter.setMinimumSize(0, 0)
        self.body_splitter.setSizePolicy(
            QtWidgets.QSizePolicy.Ignored,
            QtWidgets.QSizePolicy.Ignored,
        )
        self.chart_view = ChartView()
        self.chart_view.setMinimumSize(0, 0)
        self.chart_view.setSizePolicy(
            QtWidgets.QSizePolicy.Ignored,
            QtWidgets.QSizePolicy.Ignored,
        )
        self._last_history_reload_price_basis = self.chart_view.current_price_basis()
        self.chart_view.resolution_changed.connect(self._on_chart_resolution_changed)
        self.chart_view.history_range_changed.connect(self._on_chart_range_changed)
        self.chart_view.price_basis_changed.connect(self._on_chart_price_basis_changed)
        self.body_splitter.addWidget(self.chart_view)

        self.right_tabs = QtWidgets.QTabWidget()
        self.product_selector = ProductSelectorWidget()
        self.product_selector.set_market_bindings(self._config.product_market_bindings)
        self.product_selector.set_market_context(self._latest_macro_state)
        self.product_selector.discover_requested.connect(self._discover_products)
        self.product_selector.targeted_search_requested.connect(self._search_products_targeted)
        self.product_selector.export_requested.connect(self._export_discovery_report)
        self.product_selector.product_selected.connect(self._on_product_selected)
        self.product_selector.visible_epics_changed.connect(self._on_visible_epics_changed)
        self.product_selector.paper_ticket.paper_execution_requested.connect(
            self._execute_paper_submission
        )
        self.right_tabs.addTab(self.product_selector, "Produits / Ticket")
        self.scanner_preview = ScannerPreviewWidget()
        self.scanner_preview.refresh_requested.connect(self._refresh_scanner_preview)
        self.right_tabs.addTab(self.scanner_preview, "Scanner")
        self.paper_portfolio = PaperPortfolioWidget()
        self.paper_portfolio.stop_update_requested.connect(self._update_paper_stop)
        self.paper_portfolio.close_requested.connect(self._close_paper_position)
        self.paper_portfolio.save_requested.connect(self._save_paper_session)
        self.paper_portfolio.restore_requested.connect(self._restore_paper_session)
        self.right_tabs.addTab(self.paper_portfolio, "Portefeuille simulé")
        self.right_tabs.currentChanged.connect(self._on_right_tab_changed)
        self.right_tabs.setMinimumSize(0, 0)
        self.right_tabs.setSizePolicy(
            QtWidgets.QSizePolicy.Ignored,
            QtWidgets.QSizePolicy.Ignored,
        )
        self.body_splitter.addWidget(self.right_tabs)
        self.body_splitter.setStretchFactor(0, 1)
        self.body_splitter.setStretchFactor(1, 3)

        root_layout.addWidget(self.body_splitter, stretch=1)
        self.setCentralWidget(root)
        self._refresh_paper_session_views()

    def _publish_runtime_projections(self) -> None:
        """Mirror observed legacy state into the read-only GUI V2 boundary."""

        generated_at = datetime.now(UTC)
        connection = self._active_connection
        account = self._current_runtime_account()
        rest_status = "connected" if connection is not None else "disconnected"
        if self._latest_ai_context_snapshot is not None:
            ai_status = "available"
        elif self._openai_context_session is not None:
            ai_status = "configured"
        else:
            ai_status = "not_configured"
        open_positions_count = sum(
            snapshot.position.status.value == "open"
            for snapshot in self._paper_session.position_snapshots()
        )
        generation_id = self._projection_runtime.generation_id
        header = build_account_header_projection(
            generation_id=generation_id,
            account=account,
            environment=connection.environment.value if connection is not None else None,
            execution_mode="PAPER",
            open_positions_count=open_positions_count,
            rest_status=rest_status,
            stream_status=self._stream_projection_status,
            ai_status=ai_status,
            generated_at_utc=generated_at,
        )
        health = build_runtime_health_projection(
            generation_id=generation_id,
            rest_status=rest_status,
            stream_status=self._stream_projection_status,
            ai_status=ai_status,
            observed_at_utc=generated_at,
        )
        dashboard = merge_account_metrics_into_dashboard(
            build_paper_dashboard_projection(
                generation_id=generation_id,
                positions=self._paper_session.position_snapshots(),
                events=self._paper_session.events(),
                generated_at_utc=generated_at,
            ),
            header,
        )
        self._projection_runtime.publish_account_header(header)
        self._projection_runtime.publish_dashboard(dashboard)
        self._projection_runtime.publish_health(health, generation_id=generation_id)

    def _current_runtime_account(self) -> Account | None:
        connection = self._active_connection
        if connection is None or connection.current_account_id is None:
            return None
        return next(
            (
                account
                for account in connection.accounts
                if account.account_id == connection.current_account_id
            ),
            None,
        )

    @QtCore.pyqtSlot(int)
    def _on_right_tab_changed(self, _index: int) -> None:
        if self.right_tabs.currentWidget() is self.paper_portfolio:
            self._refresh_paper_session_views()
            self._paper_freshness_timer.start()
        else:
            self._paper_freshness_timer.stop()

    @QtCore.pyqtSlot()
    def _refresh_paper_freshness(self) -> None:
        if self.right_tabs.currentWidget() is not self.paper_portfolio:
            return
        if self._paper_session.position_snapshots() != self.paper_portfolio.position_snapshots:
            self._refresh_paper_session_views()

    @QtCore.pyqtSlot()
    def _refresh_scanner_preview(self) -> None:
        if self._active_connection is not None:
            self._refresh_bound_scanner_batch()
            return
        if self._chart_candle_series is None or len(self._chart_candle_series.candles) < 2:
            self.scanner_preview.show_unavailable(
                "WARMING_UP : aucune bougie clôturée reçue pendant cette session. L'analyse "
                "technique se débloquera progressivement; le contexte et la simulation restent "
                "disponibles séparément."
            )
            return
        evaluated_at = datetime.now(UTC)
        current_macro_state = MacroContextService().revalidate_state(
            self._latest_macro_state, evaluated_at
        )
        try:
            preview = build_scanner_preview(
                self._chart_candle_series,
                as_of_utc=evaluated_at,
            )
        except ValueError as exc:
            self.scanner_preview.show_unavailable(f"Analyse indisponible : {exc}")
            return
        product_context = None
        if self._selected_product is not None:
            product_context = ProductContextProjectionService().project(
                self._selected_product,
                current_macro_state,
                evaluated_at_utc=evaluated_at,
                ai_snapshot=self._latest_ai_context_snapshot,
            )
        context_component = (
            build_context_score_component(product_context)
            if product_context is not None
            else build_banded_score_component(
                ScoreComponentName.CONTEXT,
                ScoreBand.UNKNOWN,
                reason_codes=("PRODUCT_CONTEXT_UNAVAILABLE",),
            )
        )
        product_spread = None
        fee_per_unit_per_side = None
        execution_price_scale_verified = False
        if self._selected_product is not None:
            chart_product = self._chart_product or self._selected_product
            execution_price_scale_verified = chart_product.epic == self._selected_product.epic
            live_quote = self.product_selector.fresh_live_quote_for_epic(
                self._selected_product.epic, now=evaluated_at
            )
            product_spread = _scanner_quote_spread(live_quote)
            fee_per_unit_per_side = _scanner_fee_for_product(
                self._config,
                self._selected_product,
            )
        component_service = ScannerComponentService()
        market_risk_component = component_service.market_risk_from_macro(current_macro_state)
        scoring_config = self._config.scanner_scoring
        component_weights = {
            ScoreComponentName(name): weight
            for name, weight in scoring_config.component_weights().items()
        }
        score_results = component_service.score_signals(
            preview.consensus,
            context_component,
            fresh=True,
            continuous=preview.excluded_pre_gap_candles == 0,
            market_risk_component=market_risk_component,
            product_spread=product_spread,
            fee_per_unit_per_side=fee_per_unit_per_side,
            execution_price_scale_verified=execution_price_scale_verified,
            component_weights=component_weights,
            candidate_threshold=scoring_config.candidate_threshold,
            watch_threshold=scoring_config.watch_threshold,
        )
        self.scanner_preview.set_preview(preview, product_context, score_results)
        self.statusBar().showMessage(
            "Scanner preview mis à jour sur bougies clôturées ; aucun ticket ni ordre créé.",
            10000,
        )

    def _refresh_bound_scanner_batch(self) -> None:
        selected = self._selected_product
        connection = self._active_connection
        self._latest_scanner_runtime_batch = None
        if selected is None or connection is None:
            self.scanner_preview.show_unavailable(
                "Scanner indisponible : aucun produit sélectionné."
            )
            return
        try:
            self._scanner_binding_registry.resolve(selected.epic)
        except MarketNavigationCatalogError:
            self.scanner_preview.show_unavailable(
                "Scanner indisponible : ce produit ne possède pas de binding exact validé. "
                "Il reste disponible pour la simulation manuelle."
            )
            return

        products = _scanner_runtime_products(self.product_selector.results(), selected)
        spreads: dict[str, Decimal | None] = {}
        fees: dict[str, Decimal | None] = {}
        for binding in self._scanner_binding_registry.bindings():
            product = next(
                (item for item in products if item.epic == binding.product_epic),
                None,
            )
            if product is None:
                continue
            live_quote = self.product_selector.fresh_live_quote_for_epic(
                product.epic, now=datetime.now(UTC)
            )
            spreads[product.epic] = _scanner_quote_spread(live_quote)
            fees[product.epic] = _scanner_fee_for_product(self._config, product)

        scoring_config = self._config.scanner_scoring
        component_weights = {
            ScoreComponentName(name): weight
            for name, weight in scoring_config.component_weights().items()
        }
        try:
            result = ScannerRuntimeBatchService(
                self._scanner_binding_registry,
                self._scanner_session_candles,
            ).scan(
                products=products,
                environment=connection.environment,
                account_id=connection.current_account_id,
                resolution_seconds=self.chart_view.current_interval_seconds(),
                price_basis=self.chart_view.current_price_basis(),
                macro_state=self._latest_macro_state,
                evaluated_at_utc=datetime.now(UTC),
                profile_catalog=self._config.scanner_profiles,
                ai_snapshot=self._latest_ai_context_snapshot,
                product_spreads=spreads,
                fee_per_unit_per_side=fees,
                component_weights=component_weights,
                candidate_threshold=scoring_config.candidate_threshold,
                watch_threshold=scoring_config.watch_threshold,
            )
        except ValueError as exc:
            self.scanner_preview.show_unavailable(f"Scanner indisponible : {exc}")
            return

        self._latest_scanner_runtime_batch = result
        selected_item = next(
            (item for item in result.batch.items if item.product.epic == selected.epic),
            None,
        )
        if selected_item is None:
            selected_failure = next(
                (
                    failure
                    for failure in result.batch.failures
                    if failure.product_epic == selected.epic
                ),
                None,
            )
            reason = selected_failure.reason if selected_failure is not None else "données absentes"
            self.scanner_preview.show_unavailable(
                f"Scanner indisponible pour le produit sélectionné : {reason}"
            )
        else:
            self.scanner_preview.set_preview(
                selected_item.preview,
                result.context_for(selected.epic),
                selected_item.results,
            )
        self.statusBar().showMessage(
            "Scanner batch manuel : "
            f"{len(result.batch.items)} produit(s) lié(s), "
            f"{len(result.batch.failures)} indisponible(s) ; aucun ticket ni ordre créé.",
            12000,
        )

    @QtCore.pyqtSlot()
    def _refresh_official_news(self) -> None:
        if self._latest_news_snapshots:
            self._rebuild_macro_context(datetime.now(UTC))
        if not self._official_news_providers or self._official_news_thread is not None:
            return
        LOGGER.debug(
            "Official news refresh start provider_count=%s",
            len(self._official_news_providers),
        )
        self.statusBar().showMessage("Refreshing official source health...", 0)
        self._official_news_refresh_action.setEnabled(False)
        self._official_news_thread = QtCore.QThread(self)
        self._official_news_worker = OfficialNewsRefreshWorker(self._official_news_providers)
        self._official_news_worker.moveToThread(self._official_news_thread)
        self._official_news_thread.started.connect(self._official_news_worker.run)
        self._official_news_worker.succeeded.connect(self._on_official_news_refresh_success)
        self._official_news_worker.finished.connect(self._official_news_thread.quit)
        self._official_news_worker.finished.connect(self._official_news_worker.deleteLater)
        self._official_news_thread.finished.connect(self._official_news_thread.deleteLater)
        self._official_news_thread.finished.connect(self._clear_official_news_worker)
        self._official_news_thread.start()

    @QtCore.pyqtSlot(object)
    def _on_official_news_refresh_success(self, result: object) -> None:
        if not isinstance(result, OfficialNewsRefreshResult):
            return
        self._latest_news_snapshots = result.snapshots
        evidence_signals = self._rebuild_macro_context(result.collected_at_utc)
        available_count = sum(snapshot.status.value == "available" for snapshot in result.snapshots)
        self.statusBar().showMessage(
            "Official source health refreshed: "
            f"{available_count}/{len(result.snapshots)} available; "
            f"{len(evidence_signals)} AI metadata evidence items.",
            7000,
        )

    @QtCore.pyqtSlot()
    def _clear_official_news_worker(self) -> None:
        self._official_news_thread = None
        self._official_news_worker = None
        self._official_news_refresh_action.setEnabled(bool(self._official_news_providers))

    def _rebuild_macro_context(self, generated_at_utc: datetime) -> tuple[ContextSignal, ...]:
        if self._calendar_runtime_result is not None:
            generated_at_utc = max(
                generated_at_utc,
                self._calendar_runtime_result.snapshot.collected_at_utc,
            )
        if self._latest_news_snapshots:
            generated_at_utc = max(
                generated_at_utc,
                *(snapshot.collected_at_utc for snapshot in self._latest_news_snapshots),
            )
        signals: list[ContextSignal] = []
        evidence_signals: tuple[ContextSignal, ...] = ()
        if self._latest_news_snapshots:
            signals.append(
                build_news_source_health_signal(
                    self._latest_news_snapshots,
                    generated_at_utc=generated_at_utc,
                    valid_for=OFFICIAL_NEWS_HEALTH_VALIDITY,
                )
            )
            evidence_signals = build_news_ai_evidence_signals(
                self._latest_news_snapshots,
                generated_at_utc=generated_at_utc,
                valid_for=OFFICIAL_NEWS_HEALTH_VALIDITY,
                max_items=OPENAI_NEWS_EVIDENCE_LIMIT,
            )
            signals.extend(evidence_signals)
        if self._calendar_runtime_result is not None:
            signals.extend(self._calendar_runtime_result.signals)
        self._latest_macro_state = MacroContextService().build_state(
            tuple(signals),
            generated_at_utc,
        )
        self.macro_ribbon.set_state(self._latest_macro_state)
        self.product_selector.set_market_context(
            self._latest_macro_state,
            self._latest_ai_context_snapshot,
        )
        self._update_openai_context_action()
        return tuple(evidence_signals)

    @QtCore.pyqtSlot(object)
    def _enable_calendar_context_session(self, result: object) -> None:
        if not isinstance(result, TradingEconomicsRuntimeResult):
            return
        self._calendar_runtime_result = result
        self._rebuild_macro_context(result.snapshot.collected_at_utc)
        self._calendar_refresh_timer.start()
        self._calendar_context_action.setEnabled(True)
        self.statusBar().showMessage(
            "Calendrier Trading Economics validé pour cette session ; refresh toutes les 15 min.",
            10000,
        )

    @QtCore.pyqtSlot()
    def _refresh_calendar_context(self) -> None:
        current = self._calendar_runtime_result
        if current is None or self._calendar_context_thread is not None:
            return
        api_key = self._calendar_key_reader()
        if not api_key:
            self.statusBar().showMessage(
                "TRADING_ECONOMICS_API_KEY n'est plus disponible dans ce processus.",
                10000,
            )
            return
        thread = QtCore.QThread(self)
        worker = EconomicCalendarRefreshWorker(
            api_key=SecretValue(api_key),
            config=current.config,
            runner=self._calendar_context_runner,
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.completed.connect(self._on_calendar_context_success)
        worker.failed.connect(self._on_calendar_context_failure)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_calendar_context_worker)
        self._calendar_context_thread = thread
        self._calendar_context_worker = worker
        self._calendar_context_action.setEnabled(False)
        self.statusBar().showMessage("Rafraîchissement du calendrier macro…", 0)
        thread.start()

    @QtCore.pyqtSlot(object)
    def _on_calendar_context_success(self, result: object) -> None:
        if not isinstance(result, TradingEconomicsRuntimeResult):
            self._on_calendar_context_failure("Résultat calendrier invalide.")
            return
        self._calendar_runtime_result = result
        self._rebuild_macro_context(result.snapshot.collected_at_utc)
        self.statusBar().showMessage(
            f"Calendrier macro rafraîchi : {len(result.snapshot.events)} événement(s).",
            10000,
        )

    @QtCore.pyqtSlot(str)
    def _on_calendar_context_failure(self, message: str) -> None:
        self.statusBar().showMessage(message, 12000)

    @QtCore.pyqtSlot()
    def _clear_calendar_context_worker(self) -> None:
        self._calendar_context_thread = None
        self._calendar_context_worker = None
        self._calendar_context_action.setEnabled(self._calendar_runtime_result is not None)

    @QtCore.pyqtSlot(str, int, bool)
    def _enable_openai_context_session(
        self,
        model: str,
        max_output_tokens: int,
        automatic_refresh: bool = False,
    ) -> None:
        self._openai_context_session = OpenAIContextSession(
            model=model,
            max_output_tokens=max_output_tokens,
            automatic_refresh=automatic_refresh,
        )
        if automatic_refresh:
            self._openai_context_refresh_timer.start()
        else:
            self._openai_context_refresh_timer.stop()
        self._update_openai_context_action()
        mode = (
            "L'analyse consultative sera renouvelée toutes les 15 minutes."
            if automatic_refresh
            else "L'analyse reste manuelle et consultative."
        )
        self.statusBar().showMessage(
            f"OpenAI validé pour cette session. {mode}",
            10000,
        )

    def _has_openai_evidence(self) -> bool:
        now = datetime.now(UTC)
        return any(
            "ai_evidence" in {tag.lower() for tag in signal.tags}
            and signal.observed_at_utc <= now
            and (signal.valid_until_utc is None or now < signal.valid_until_utc)
            and is_ai_citation_eligible(signal, now)
            for signal in self._latest_macro_state.signals
        )

    @QtCore.pyqtSlot()
    def _open_web_research(self) -> None:
        session = self._openai_context_session
        api_key = self._openai_key_reader()
        if session is None or not api_key:
            QtWidgets.QMessageBox.information(
                self, "Recherche web", "Validez d'abord OpenAI dans Tools → Settings → OpenAI."
            )
            return
        if self._selected_product is None:
            QtWidgets.QMessageBox.information(self, "Recherche web", "Sélectionnez un produit.")
            return
        market = f"{self._selected_product.name} ({self._selected_product.epic})"
        dialog = WebResearchDialog(
            market=market,
            instrument_id=self._selected_product.epic,
            model=session.model,
            key=api_key,
            parent=self,
        )
        dialog.context_ready.connect(self._on_openai_context_success)
        dialog.exec()

    def _update_openai_context_action(self) -> None:
        self._openai_context_action.setEnabled(
            self._openai_context_session is not None
            and self._has_openai_evidence()
            and self._openai_context_thread is None
        )

    @QtCore.pyqtSlot()
    def _refresh_openai_context(self) -> None:
        self._start_openai_context_refresh(report_unavailable=True)

    @QtCore.pyqtSlot()
    def _refresh_openai_context_automatic(self) -> None:
        session = self._openai_context_session
        if session is None or not session.automatic_refresh:
            self._openai_context_refresh_timer.stop()
            return
        self._start_openai_context_refresh(report_unavailable=False)

    def _start_openai_context_refresh(self, *, report_unavailable: bool) -> None:
        session = self._openai_context_session
        if session is None or self._openai_context_thread is not None:
            return
        if not self._has_openai_evidence():
            if report_unavailable:
                self.statusBar().showMessage(
                    "Aucune métadonnée officielle éligible n'est disponible pour l'analyse OpenAI.",
                    10000,
                )
            else:
                LOGGER.info("Periodic OpenAI context refresh skipped: no eligible evidence")
            return
        api_key = self._openai_key_reader()
        if not api_key:
            if report_unavailable:
                self.statusBar().showMessage(
                    "OPENAI_API_KEY n'est plus disponible dans ce processus.",
                    10000,
                )
            else:
                LOGGER.warning("Periodic OpenAI context refresh skipped: key unavailable")
            return

        instrument_id = (
            self._selected_product.epic
            if self._selected_product is not None
            else "GLOBAL-MARKET-CONTEXT"
        )
        current_macro_state = MacroContextService().build_state(
            self._latest_macro_state.signals, datetime.now(UTC)
        )
        thread = QtCore.QThread(self)
        worker = OpenAIContextRefreshWorker(
            model=session.model,
            api_key=SecretValue(api_key),
            max_output_tokens=session.max_output_tokens,
            macro_state=current_macro_state,
            instrument_id=instrument_id,
            runner=self._openai_context_runner,
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.succeeded.connect(self._on_openai_context_success)
        worker.failed.connect(self._on_openai_context_failure)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_openai_context_worker)
        self._openai_context_thread = thread
        self._openai_context_worker = worker
        self._openai_context_action.setEnabled(False)
        self.statusBar().showMessage(
            "Analyse consultative OpenAI en cours…",
            0,
        )
        thread.start()

    @QtCore.pyqtSlot(object)
    def _on_openai_context_success(self, result: object) -> None:
        if not isinstance(result, MarketContextSnapshot):
            self._on_openai_context_failure("OpenAI returned an invalid runtime result.")
            return
        ai_reason_codes = tuple(code for code in result.reason_codes if code.startswith("AI_"))
        self._latest_ai_context_snapshot = result
        self._refresh_ai_presentation()
        self._publish_runtime_projections()
        LOGGER.info(
            "OpenAI consultative context completed status=%s model=%s reasons=%s",
            result.ai_analysis.status.value,
            result.ai_analysis.model_id,
            ",".join(ai_reason_codes) or "none",
        )
        if result.ai_analysis.status is AIAnalysisStatus.AVAILABLE:
            self.statusBar().showMessage(
                "Contexte consultatif OpenAI mis à jour ; aucun ticket ni ordre n'a été créé.",
                12000,
            )
        else:
            diagnostic = ", ".join(ai_reason_codes) or "AI_UNAVAILABLE"
            self.statusBar().showMessage(
                "Contexte OpenAI indisponible "
                f"({diagnostic}) ; le contexte déterministe reste inchangé.",
                12000,
            )

    @QtCore.pyqtSlot()
    def _refresh_ai_presentation(self) -> None:
        """Expire the display locally; never make a provider call from this timer."""
        self._ai_expiry_timer.stop()
        snapshot = self._latest_ai_context_snapshot
        if snapshot is None:
            return
        now = datetime.now(UTC)
        instrument_id = self._selected_product.epic if self._selected_product else ""
        reasons = tuple(code for code in snapshot.reason_codes if code.startswith("AI_"))
        self.macro_ribbon.set_ai_analysis(
            snapshot.ai_analysis,
            reasons,
            evaluated_at_utc=now,
            instrument_id=instrument_id,
            valid_until_utc=snapshot.valid_until_utc,
        )
        self.product_selector.set_market_context(self._latest_macro_state, snapshot)
        if snapshot.valid_until_utc > now:
            remaining_ms = int((snapshot.valid_until_utc - now).total_seconds() * 1000) + 1
            self._ai_expiry_timer.start(min(remaining_ms, 2_147_483_647))

    @QtCore.pyqtSlot(str)
    def _on_openai_context_failure(self, message: str) -> None:
        self.statusBar().showMessage(message, 12000)
        self._publish_runtime_projections()

    @QtCore.pyqtSlot()
    def _clear_openai_context_worker(self) -> None:
        self._openai_context_thread = None
        self._openai_context_worker = None
        self._update_openai_context_action()

    def _restore_workspace_state(self) -> None:
        workspace = self._config.workspace
        if workspace.window_width is not None and workspace.window_height is not None:
            width = workspace.window_width
            height = workspace.window_height
            screen = QtWidgets.QApplication.primaryScreen()
            if screen is not None:
                available = screen.availableGeometry()
                width = min(width, available.width())
                height = min(height, available.height())
            self.resize(width, height)
        if (
            len(workspace.splitter_sizes) == self.body_splitter.count()
            and sum(workspace.splitter_sizes) > 0
        ):
            self.body_splitter.setSizes(list(workspace.splitter_sizes))

    def _capture_workspace_state(self) -> WorkspaceState:
        return WorkspaceState(
            window_width=self.width(),
            window_height=self.height(),
            splitter_sizes=tuple(self.body_splitter.sizes()),
        )

    @staticmethod
    def _build_credential_store() -> object | None:
        return build_default_credential_store()

    @QtCore.pyqtSlot()
    def _open_settings(self) -> None:
        LOGGER.debug("Settings dialog open")
        dialog = SettingsDialog(
            self._config,
            self._credential_store,
            self,
            openai_key_reader=self._openai_key_reader,
            calendar_probe_runner=self._calendar_context_runner,
            calendar_key_reader=self._calendar_key_reader,
        )
        dialog.config_applied.connect(self._apply_config)
        dialog.openai_runtime_validated.connect(self._enable_openai_context_session)
        dialog.calendar_runtime_validated.connect(self._enable_calendar_context_session)
        dialog.exec()

    @QtCore.pyqtSlot(object)
    def _apply_config(self, config: AppConfig) -> None:
        LOGGER.debug("Settings applied environment=%s", config.environment.value)
        self._config = config
        self.product_selector.set_market_bindings(config.product_market_bindings)
        self._scanner_binding_registry = IGProductMarketBindingRegistry(
            self._config.product_market_bindings
        )
        chart_epics = _prioritized_chart_epics(
            self._chart_product or self._selected_product,
            initial_ig_reference_epics(),
        )
        self._scanner_session_candles = MultiMarketSessionCandleService(
            self._scanner_binding_registry,
            candle_history_service=self._scanner_candle_history_service,
            reference_epics=tuple(chart_epics),
        )
        save_config(self._config, self._config_path)
        self.statusBar().showMessage("Settings saved.", 5000)

    @QtCore.pyqtSlot(object)
    def _connect_environment(self, environment: IGEnvironment) -> None:
        LOGGER.debug("Connect requested environment=%s", environment.value)
        if self._auth_locked_out:
            self.statusBar().showMessage(
                "IG authentication is temporarily locked after too many failed attempts. "
                "Wait before retrying.",
                12000,
            )
            return
        request = self._build_request_for_environment(environment)
        if request is None:
            return
        self._config.environment = environment
        self._connect_read_only(request)

    def _build_request_for_environment(
        self,
        environment: IGEnvironment,
    ) -> IGConnectionRequest | None:
        profile = self._config.connection_profiles[environment]
        if not profile.identifier:
            LOGGER.debug(
                "Request build failed missing identifier environment=%s",
                environment.value,
            )
            self.statusBar().showMessage(
                f"Configure {environment.value} API identifier first.",
                7000,
            )
            self._open_settings()
            return None
        if self._credential_store is None:
            LOGGER.debug(
                "Request build failed missing credential store environment=%s",
                environment.value,
            )
            self.statusBar().showMessage("OS keyring credential store is unavailable.", 7000)
            return None
        credentials = self._credential_store.load_profile(environment.value, profile.identifier)
        if credentials is None:
            LOGGER.debug(
                "Request build failed missing credentials environment=%s",
                environment.value,
            )
            self.statusBar().showMessage(
                f"Configure {environment.value} password and API key first.",
                7000,
            )
            self._open_settings()
            return None
        return IGConnectionRequest(
            environment=environment,
            username=credentials.username,
            password=credentials.password.reveal(),
            api_key=credentials.api_key.reveal(),
            selected_account_id=profile.selected_account_id,
        )

    @QtCore.pyqtSlot()
    def _clear_connection_market_state(self) -> None:
        """Invalidate the visible, actionable state from a previous IG connection."""
        self._stream_projection_status = "disconnected"
        self._projection_runtime.begin_generation()
        results = self.product_selector.results()
        retained = [r for r in results if not r.search_term.startswith("targeted-search:")]
        if len(retained) != len(results):
            self.product_selector.set_results(retained)
        self.product_selector.clear_live_quotes()
        self.chart_view.set_live_quote(None)
        self.chart_view.set_candles(())
        self._chart_candle_series = None
        self._candle_history_service.reset_active_series()
        self._latest_scanner_runtime_batch = None
        self._paper_session.invalidate_market_quotes()
        self._refresh_paper_session_views()
        self.scanner_preview.show_unavailable(
            "Scanner indisponible : attendre les données du compte courant."
        )

    @QtCore.pyqtSlot()
    def _disconnect(self) -> None:
        LOGGER.debug("Disconnect requested")
        if self._connection_thread is not None:
            self.statusBar().showMessage("Connection is busy; wait before disconnecting.", 5000)
            return
        if self._discovery_thread is not None:
            self.statusBar().showMessage("Discovery is running; wait before disconnecting.", 5000)
            return
        self._stop_streaming()
        self._clear_connection_market_state()
        self._logout_active_connection()
        self.account_status.set_disconnected()
        self.product_selector.set_selected_product(None)
        self.chart_view.set_stream_status("DISCONNECTED")
        self.chart_view.set_live_quote(None)
        self._publish_runtime_projections()
        self.statusBar().showMessage("Disconnected from IG.", 5000)

    @QtCore.pyqtSlot(object)
    def _connect_read_only(self, request: IGConnectionRequest) -> None:
        LOGGER.debug("Connect read-only start environment=%s", request.environment.value)
        if self._connection_thread is not None:
            LOGGER.debug("Connect read-only ignored because worker is already running")
            return
        if self._active_connection is not None:
            self._stop_streaming()
            self._clear_connection_market_state()
            self._logout_active_connection()
        self.statusBar().showMessage(
            f"Connecting to IG {request.environment.value} in read-only mode...",
            0,
        )
        self._connection_thread = QtCore.QThread(self)
        self._connection_worker = ConnectionWorker(request, self._projection_runtime)
        self._connection_worker.moveToThread(self._connection_thread)
        self._connection_thread.started.connect(self._connection_worker.run)
        self._connection_worker.succeeded.connect(self._on_connection_success)
        self._connection_worker.failed.connect(self._on_connection_failure)
        self._connection_worker.finished.connect(self._connection_thread.quit)
        self._connection_worker.finished.connect(self._connection_worker.deleteLater)
        self._connection_thread.finished.connect(self._connection_thread.deleteLater)
        self._connection_thread.finished.connect(self._clear_connection_worker)
        self._connection_thread.start()

    @QtCore.pyqtSlot(object)
    def _on_connection_success(self, result: ActiveIGConnection) -> None:
        self._clear_connection_market_state()
        self._auth_locked_out = False
        self._api_allowance_exceeded = False
        self._history_allowance_state = HistoricalAllowanceState()
        self.account_status.clear_auth_locked()
        LOGGER.debug(
            "Connection success environment=%s accounts=%s current_account=%s",
            result.environment.value,
            len(result.accounts),
            mask_identifier(result.current_account_id),
        )
        configured_account_id = self._config.connection_profiles[
            result.environment
        ].selected_account_id
        selected_account_id = _resolve_account_id(
            result.accounts,
            configured_account_id,
            result.current_account_id,
        )
        self.account_status.set_accounts(
            result.accounts,
            selected_account_id,
            result.environment,
            connected=True,
        )
        self._active_connection = result
        self._active_connection.current_account_id = selected_account_id
        self._history_allowance_state = _load_history_allowance_state(
            environment=result.environment,
            account_id=selected_account_id,
        )
        LOGGER.debug(
            "Connected IG accounts environment=%s accounts=%s selected_account=%s",
            result.environment.value,
            [
                {
                    "account": mask_identifier(account.account_id),
                    "name": account.account_name,
                    "type": account.account_type,
                    "currency": account.currency,
                    "preferred": account.preferred,
                }
                for account in result.accounts
            ],
            mask_identifier(selected_account_id),
        )
        self._set_profile_account(result.environment, selected_account_id)
        if self._loaded_cache_environment != result.environment:
            self._load_cached_discovery_results()
        if self._selected_product is not None:
            self._refresh_selected_product_after_connection()
        else:
            self.chart_view.set_stream_status("STREAM READY")
            self._restart_streaming()
        self._publish_runtime_projections()
        message = (
            f"Connected to IG {result.environment.value}. Accounts fetched: {len(result.accounts)}."
        )
        self.statusBar().showMessage(
            message,
            7000,
        )

    @QtCore.pyqtSlot(str)
    def _on_connection_failure(self, message: str) -> None:
        LOGGER.debug("Connection failure message=%s", message)
        self._stream_projection_status = "disconnected"
        self._projection_runtime.begin_generation()
        if "too-many-failed-attempts" in message:
            self._auth_locked_out = True
            self.account_status.set_auth_locked(
                "IG authentication locked: too many failed attempts. Wait before trying again."
            )
        self._publish_runtime_projections()
        self.statusBar().showMessage(f"Connection failed: {humanize_ig_error(message)}", 12000)

    @QtCore.pyqtSlot()
    def _clear_connection_worker(self) -> None:
        self._connection_thread = None
        self._connection_worker = None

    @QtCore.pyqtSlot(object)
    def _discover_products(self, search_terms: object) -> None:
        LOGGER.debug("Product discovery requested")
        if self._discovery_thread is not None:
            LOGGER.debug("Product discovery ignored because worker is already running")
            return
        if self._active_connection is None or self._active_connection.adapter.session is None:
            self.statusBar().showMessage("Connect to IG before running product discovery.", 7000)
            return
        self.product_selector.set_busy(True)
        self.statusBar().showMessage(
            f"Discovering products on IG {self._active_connection.environment.value}...",
            0,
        )
        self._discovery_thread = QtCore.QThread(self)
        self._discovery_worker = ProductDiscoveryWorker(
            self._active_connection.adapter,
            self._active_connection.environment,
        )
        self._discovery_worker.moveToThread(self._discovery_thread)
        self._discovery_thread.started.connect(self._discovery_worker.run)
        self._discovery_worker.succeeded.connect(self._on_discovery_success)
        self._discovery_worker.failed.connect(self._on_discovery_failure)
        self._discovery_worker.finished.connect(self._discovery_thread.quit)
        self._discovery_worker.finished.connect(self._discovery_worker.deleteLater)
        self._discovery_thread.finished.connect(self._discovery_thread.deleteLater)
        self._discovery_thread.finished.connect(self._clear_discovery_worker)
        self._discovery_thread.start()

    @QtCore.pyqtSlot(str)
    def _search_products_targeted(self, search_term: str) -> None:
        term = search_term.strip()
        if not 3 <= len(term) <= 100:
            self.statusBar().showMessage("Saisissez de 3 à 100 caractères dans le filtre.", 10000)
            return
        if self._discovery_thread is not None:
            self.statusBar().showMessage("Une découverte est déjà en cours.", 7000)
            return
        if self._active_connection is None or self._active_connection.adapter.session is None:
            self.statusBar().showMessage("Connectez-vous à IG avant cette recherche.", 7000)
            return
        if self._api_allowance_exceeded:
            self.statusBar().showMessage("Quota API IG atteint : recherche suspendue.", 10000)
            return
        self.product_selector.set_busy(True)
        self.statusBar().showMessage("Recherche IG ciblée en lecture seule…", 0)
        self._targeted_discovery_origin = (
            self._active_connection,
            self._active_connection.current_account_id,
            self._stream_generation,
        )
        thread = QtCore.QThread(self)
        worker = ProductDiscoveryWorker(
            self._active_connection.adapter, self._active_connection.environment, term
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.succeeded.connect(self._on_targeted_discovery_success)
        worker.failed.connect(self._on_discovery_failure)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_discovery_worker)
        self._discovery_thread, self._discovery_worker = thread, worker
        thread.start()

    @QtCore.pyqtSlot(object)
    def _on_targeted_discovery_success(self, results: list[ProductDiscoveryResult]) -> None:
        origin = self._targeted_discovery_origin
        if (
            origin is None
            or self._active_connection is not origin[0]
            or self._active_connection.current_account_id != origin[1]
            or self._stream_generation != origin[2]
        ):
            self.statusBar().showMessage(
                "Recherche IG ignorée : le contexte de connexion a changé.", 10000
            )
            return
        known = {p.epic for r in self.product_selector.results() for p in r.products}
        additions = []
        for result in results:
            for product in result.products:
                if product.epic not in known:
                    additions.append(product)
                    known.add(product.epic)
        if additions:
            self.product_selector.set_results([
                *self.product_selector.results(),
                ProductDiscoveryResult(
                    search_term=results[0].search_term,
                    candidates_count=len(additions),
                    products=additions,
                ),
            ])
        returned = sum(len(result.products) for result in results)
        self.statusBar().showMessage(
            f"Recherche IG : {returned} résultat(s), {len(additions)} nouveau(x). "
            "Résultats supplémentaires conservés pour cette session.",
            15000,
        )

    @QtCore.pyqtSlot(object)
    def _on_discovery_success(self, results: list[ProductDiscoveryResult]) -> None:
        LOGGER.debug(
            "Product discovery success result_count=%s products=%s errors=%s",
            len(results),
            sum(len(result.products) for result in results),
            sum(len(result.errors) for result in results),
        )
        if any(
            _is_api_allowance_exceeded(error.message)
            for result in results
            for error in result.errors
        ):
            self._mark_api_allowance_exceeded()
        self._save_discovery_cache(results)
        self.product_selector.set_results(results)
        product_count = sum(len(result.products) for result in results)
        self.statusBar().showMessage(f"Product discovery complete: {product_count} products.", 7000)
        if self._selected_product is None:
            first_product = _first_discovered_product(results)
            if first_product is not None:
                self._on_product_selected(first_product)

    @QtCore.pyqtSlot(str)
    def _on_discovery_failure(self, message: str) -> None:
        LOGGER.debug("Product discovery failure message=%s", message)
        if _is_api_allowance_exceeded(message):
            self._mark_api_allowance_exceeded()
        self.statusBar().showMessage(
            f"Product discovery failed: {humanize_ig_error(message)}",
            12000,
        )

    @QtCore.pyqtSlot()
    def _clear_discovery_worker(self) -> None:
        LOGGER.debug("Product discovery worker cleared")
        self._discovery_thread = None
        self._discovery_worker = None
        self._targeted_discovery_origin = None
        self.product_selector.set_busy(False)

    @QtCore.pyqtSlot(object)
    def _export_discovery_report(self, output_path: object) -> None:
        LOGGER.debug("Product discovery export output_path=%s", output_path)
        write_discovery_report(self.product_selector.results(), output_path)
        self.statusBar().showMessage(f"Sanitized report written to {output_path}", 7000)

    @QtCore.pyqtSlot(object)
    def _select_account(self, account_id: object) -> None:
        selected_account_id = str(account_id) if account_id else None
        LOGGER.debug("Account selected account=%s", mask_identifier(selected_account_id))
        if selected_account_id and self._active_connection is not None:
            if not self._switch_active_account(selected_account_id):
                self._logout_active_connection()
                self.account_status.set_disconnected()
                self.chart_view.set_stream_status("DISCONNECTED")
                self._publish_runtime_projections()
                return
            self._restart_streaming()
        self._set_profile_account(self._config.environment, selected_account_id)

    def _switch_active_account(self, account_id: str) -> bool:
        if self._active_connection is None:
            return False
        if self._active_connection.current_account_id == account_id:
            return True
        try:
            connection = self._projection_runtime.switch_ig_account(account_id)
            self._stop_streaming()
            self._clear_connection_market_state()
            self._history_allowance_state = _load_history_allowance_state(
                environment=connection.environment,
                account_id=connection.current_account_id,
            )
            LOGGER.debug("Active IG account switched account=%s", mask_identifier(account_id))
            self._publish_runtime_projections()
            return True
        except (IGAPIError, AccountSwitchNotConfirmedError) as exc:
            self._stop_streaming()
            self._clear_connection_market_state()
            LOGGER.debug(
                "Active IG account switch failed account=%s error=%s",
                mask_identifier(account_id),
                exc,
            )
            self.statusBar().showMessage(
                f"Account switch failed: {humanize_ig_error(str(exc))}",
                10000,
            )
            return False

    def _set_profile_account(self, environment: IGEnvironment, account_id: str | None) -> None:
        profile = self._config.connection_profiles[environment]
        self._config.connection_profiles[environment] = IGConnectionProfileConfig(
            environment=environment,
            identifier=profile.identifier,
            selected_account_id=account_id,
        )
        save_config(self._config, self._config_path)
        LOGGER.debug(
            "Profile account saved environment=%s account=%s",
            environment.value,
            mask_identifier(account_id),
        )

    def _logout_active_connection(self) -> None:
        if self._active_connection is None:
            return
        LOGGER.debug(
            "Active IG logout start environment=%s account=%s",
            self._active_connection.environment.value,
            mask_identifier(self._active_connection.current_account_id),
        )
        try:
            self._projection_runtime.disconnect_ig()
        except IGAPIError as exc:
            LOGGER.debug("Active IG logout failed ignored error=%s", exc)
        LOGGER.debug("Active IG logout complete")

    @QtCore.pyqtSlot(object)
    def _on_product_selected(self, product: object) -> None:
        if not isinstance(product, TradableProduct):
            return
        self._selected_product = product
        self._refresh_ai_presentation()
        LOGGER.debug(
            "Product selected epic=%s name=%r",
            product.epic,
            product.name,
        )
        self._config.last_selected_product_epic = product.epic
        save_config(self._config, self._config_path)
        self._apply_selected_product_state()

    @QtCore.pyqtSlot(object)
    def _on_visible_epics_changed(self, epics: object) -> None:
        if not isinstance(epics, list):
            return
        normalized = [str(epic) for epic in epics if str(epic)]
        if normalized == self._visible_price_epics:
            return
        self._visible_price_epics = normalized
        if self._active_connection is not None:
            self._restart_streaming()

    @QtCore.pyqtSlot(int, object)
    def _on_current_stream_quote(self, generation: int, quote: object) -> None:
        if generation == self._stream_generation:
            self._on_stream_quote(quote)

    @QtCore.pyqtSlot(int, object)
    def _on_current_stream_chart(self, generation: int, chart: object) -> None:
        if generation == self._stream_generation:
            self._on_stream_chart(chart)

    @QtCore.pyqtSlot(int, str)
    def _on_current_stream_status(self, generation: int, status: str) -> None:
        if generation == self._stream_generation:
            self._on_stream_status(status)

    @QtCore.pyqtSlot(int, str)
    def _on_current_stream_error(self, generation: int, message: str) -> None:
        if generation == self._stream_generation:
            self._on_stream_error(message)

    @QtCore.pyqtSlot(object)
    def _on_stream_quote(self, quote: object) -> None:
        if isinstance(quote, Quote):
            self.product_selector.set_live_quote(quote)
            if self._paper_session.tracks_product(quote.epic):
                try:
                    self._paper_session.process_market_quote(
                        quote,
                        observed_at_utc=datetime.now(UTC),
                    )
                except ValueError as exc:
                    LOGGER.warning("Paper quote update rejected: %s", exc)
                    self.statusBar().showMessage(
                        f"Mise à jour de la simulation refusée : {exc}",
                        10000,
                    )
                self._refresh_paper_session_views()
                self._publish_runtime_projections()
            chart_product = self._chart_product or self._selected_product
            if chart_product is not None and quote.epic == chart_product.epic:
                self.chart_view.set_live_quote(quote)
            if (
                self._chart_quote_candle_fallback_active
                and self._selected_product is not None
                and quote.epic == self._selected_product.epic
            ):
                self._apply_quote_candle_fallback(quote)

    def _apply_quote_candle_fallback(self, quote: Quote) -> None:
        if self._active_connection is None or self._selected_product is None:
            return
        chart_update = self._quote_candle_fallback_service.update(
            quote,
            observed_at_utc=datetime.now(UTC),
            environment=self._active_connection.environment.value,
            account_id=self._active_connection.current_account_id or "",
        )
        if chart_update is None:
            return
        chart_series = self._candle_history_service.apply_session_m1_update(
            environment=self._active_connection.environment,
            account_id=self._active_connection.current_account_id,
            selected_product_epic=self._selected_product.epic,
            chart_source_epic=self._selected_product.epic,
            resolution_seconds=self.chart_view.current_interval_seconds(),
            price_basis=self.chart_view.current_price_basis(),
            chart_update=chart_update,
        )
        self._chart_candle_series = chart_series
        self.chart_view.set_candles(chart_series.candles, preserve_view=True)
        self.chart_view.set_live_quote(quote)

    @QtCore.pyqtSlot(object)
    def _execute_paper_submission(self, submission: object) -> None:
        if not isinstance(submission, PaperTicketSubmission):
            return
        try:
            record = self._paper_session.submit(submission)
        except ValueError as exc:
            LOGGER.warning("Paper submission rejected: %s", exc)
            self.product_selector.paper_ticket.summary.append(
                f"\nOUVERTURE SIMULÉE REFUSÉE — {exc}\nAucune transmission à IG."
            )
            self.statusBar().showMessage(f"Ouverture simulée refusée : {exc}", 10000)
            return
        self.product_selector.paper_ticket.show_execution_result(record)
        self._refresh_paper_session_views()
        self._publish_runtime_projections()
        self.right_tabs.setCurrentWidget(self.paper_portfolio)
        result = record.outcome.execution_result
        self.statusBar().showMessage(
            f"Session de simulation : {result.status.value} — {result.message or '-'}",
            10000,
        )

    def _refresh_paper_session_views(self) -> None:
        self.paper_portfolio.set_session_state(
            self._paper_session.position_snapshots(),
            self._paper_session.orders(),
            self._paper_session.events(),
        )
        self.product_selector.paper_ticket.set_open_exposures(self._paper_session.open_exposures())

    @QtCore.pyqtSlot(str, object)
    def _update_paper_stop(self, position_id: str, stop: object) -> None:
        if not isinstance(stop, Decimal):
            return
        result = self._paper_session.move_stop(position_id, stop)
        self._refresh_paper_session_views()
        self._publish_runtime_projections()
        self.paper_portfolio.show_action_result(result)
        self.statusBar().showMessage(
            f"Stop simulé local : {result.status.value} — {result.message or '-'}",
            10000,
        )

    @QtCore.pyqtSlot(str)
    def _close_paper_position(self, position_id: str) -> None:
        result = self._paper_session.close_position(position_id)
        self._refresh_paper_session_views()
        self._publish_runtime_projections()
        self.paper_portfolio.show_action_result(result)
        self.statusBar().showMessage(
            f"Clôture simulée locale : {result.status.value} — {result.message or '-'}",
            10000,
        )

    @QtCore.pyqtSlot()
    def _save_paper_session(self) -> None:
        if not self._paper_session.has_state():
            self.paper_portfolio.show_persistence_result(
                "Aucun état de simulation à sauvegarder; aucun fichier n'a été créé.",
                error=True,
            )
            return
        saved_at = datetime.now(UTC)
        snapshot_id = f"paper-snapshot-{uuid4().hex}"
        try:
            store = SQLiteStore(self._paper_database_path)
            store.initialize()
            PaperSessionSnapshotRepository(store).save(
                snapshot_id=snapshot_id,
                session_id=self._paper_session.session_id,
                saved_at_utc=saved_at,
                payload=encode_paper_session_state(self._paper_session.checkpoint_state()),
            )
        except (
            CorruptPaperSnapshotError,
            MigrationError,
            OSError,
            RuntimeError,
            sqlite3.DatabaseError,
            UnsupportedSchemaError,
            ValueError,
        ) as exc:
            LOGGER.error("Explicit Paper save failed: %s", exc)
            self.paper_portfolio.show_persistence_result(
                f"Sauvegarde de la simulation refusée : {exc}",
                error=True,
            )
            return
        message = f"Session de simulation sauvegardée explicitement à {saved_at:%H:%M:%S} UTC."
        self.paper_portfolio.show_persistence_result(message)
        self.statusBar().showMessage(message, 10000)

    @QtCore.pyqtSlot()
    def _restore_paper_session(self) -> None:
        if not self._paper_database_path.exists():
            self.paper_portfolio.show_persistence_result(
                "Aucune base de simulation locale à restaurer.",
                error=True,
            )
            return
        if self._paper_session.has_state():
            answer = QtWidgets.QMessageBox.question(
                self,
                "Restaurer la session de simulation",
                "Remplacer la session de simulation locale courante par la dernière sauvegarde ?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if answer != QtWidgets.QMessageBox.Yes:
                return
        try:
            store = SQLiteStore(self._paper_database_path)
            store.initialize()
            snapshot = PaperSessionSnapshotRepository(store).latest()
            if snapshot is None:
                self.paper_portfolio.show_persistence_result(
                    "La base locale ne contient aucune sauvegarde de simulation.",
                    error=True,
                )
                return
            restored = PaperSessionService.from_checkpoint_state(
                decode_paper_session_state(snapshot.payload)
            )
            restored.record_restore(snapshot.snapshot_id)
        except (
            CorruptPaperSnapshotError,
            MigrationError,
            OSError,
            RuntimeError,
            sqlite3.DatabaseError,
            UnsupportedSchemaError,
            ValueError,
        ) as exc:
            LOGGER.error("Explicit Paper restore failed: %s", exc)
            self.paper_portfolio.show_persistence_result(
                f"Restauration de la simulation refusée : {exc}",
                error=True,
            )
            return
        self._paper_session = restored
        self._refresh_paper_session_views()
        self._publish_runtime_projections()
        message = (
            "Dernière session de simulation restaurée explicitement; aucune transmission à IG."
        )
        self.paper_portfolio.show_persistence_result(message)
        self.statusBar().showMessage(message, 10000)

    @QtCore.pyqtSlot(object)
    def _on_stream_chart(self, chart_update: object) -> None:
        if isinstance(chart_update, ChartCandleUpdate):
            if self._active_connection is not None:
                try:
                    self._scanner_session_candles.ingest_m1_update(
                        environment=self._active_connection.environment,
                        account_id=self._active_connection.current_account_id,
                        chart_update=chart_update,
                        resolution_seconds=60,
                        price_basis=ChartPriceBasis.MID,
                    )
                except (MarketNavigationCatalogError, ValueError) as exc:
                    LOGGER.debug(
                        "Scanner session candle ignored epic=%s error=%s",
                        chart_update.epic,
                        exc,
                    )
            chart_product = self._chart_product or self._selected_product
            if chart_product is None or chart_update.epic != chart_product.epic:
                return
            if self._active_connection is None or self._selected_product is None:
                return
            chart_series = self._candle_history_service.apply_session_m1_update(
                environment=self._active_connection.environment,
                account_id=self._active_connection.current_account_id,
                selected_product_epic=self._selected_product.epic,
                chart_source_epic=chart_product.epic,
                resolution_seconds=self.chart_view.current_interval_seconds(),
                price_basis=self.chart_view.current_price_basis(),
                chart_update=chart_update,
            )
            self._chart_candle_series = chart_series
            self.chart_view.set_candles(chart_series.candles, preserve_view=True)
            gap_key = _latest_series_gap_key(chart_series)
            if gap_key is not None and gap_key != self._last_history_gap_refresh_key:
                self._last_history_gap_refresh_key = gap_key
                self.statusBar().showMessage(
                    "Trou détecté dans les bougies de session : indicateurs techniques dégradés; "
                    "aucun rattrapage historique n'est tenté.",
                    15000,
                )
            live_quote = _quote_from_chart_update(chart_update)
            if live_quote is not None:
                self.chart_view.set_live_quote(live_quote)
                if (
                    self._selected_product is not None
                    and live_quote.epic == self._selected_product.epic
                ):
                    self.product_selector.set_live_quote(live_quote)

    @QtCore.pyqtSlot(str)
    def _on_stream_status(self, status: str) -> None:
        normalized = status.strip().lower()
        if normalized.startswith("connected"):
            self._stream_projection_status = "connected"
        elif normalized.startswith("subscribed"):
            self._stream_projection_status = "subscribed"
        elif normalized.startswith("live"):
            self._stream_projection_status = "live"
        elif normalized.startswith("reconnecting"):
            self._stream_projection_status = "connecting"
        elif normalized.startswith("disconnected"):
            self._stream_projection_status = "disconnected"
        self.chart_view.set_stream_status(status)
        self._publish_runtime_projections()
        LOGGER.debug("Streaming status update status=%s", status)

    @QtCore.pyqtSlot(str)
    def _on_stream_error(self, message: str) -> None:
        LOGGER.debug("Streaming error message=%s", message)
        self._stream_projection_status = "error"
        self._publish_runtime_projections()
        if (
            self._streaming_adapter is not None
            and "INSUFFICIENT PERMISSIONS" in message.upper()
            and len(self._chart_stream_epics) > 1
            and f"CHART:{len(self._chart_stream_epics)}-MARKETS:" in message.upper()
            and not self._chart_stream_permission_fallback_attempted
        ):
            chart_product = self._chart_product or self._selected_product
            if chart_product is not None:
                self._chart_stream_permission_fallback_attempted = True
                try:
                    self._streaming_adapter.subscribe_charts(
                        [chart_product.epic],
                        "1MINUTE",
                    )
                    self._chart_stream_epics = (chart_product.epic,)
                    self._scanner_session_candles = MultiMarketSessionCandleService(
                        self._scanner_binding_registry,
                        candle_history_service=self._scanner_candle_history_service,
                        reference_epics=self._chart_stream_epics,
                    )
                    LOGGER.debug(
                        "Streaming multi-chart permission fallback selected_epic=%s",
                        chart_product.epic,
                    )
                    self.statusBar().showMessage(
                        "IG refuse au moins un flux Scanner de fond ; le graphique sélectionné "
                        "continue seul et l'analyse multi-marchés est dégradée.",
                        15000,
                    )
                    return
                except Exception as exc:
                    LOGGER.debug(
                        "Streaming selected-chart permission fallback failed error=%s",
                        exc,
                    )
        chart_product = self._chart_product or self._selected_product
        if (
            self._streaming_adapter is not None
            and self._selected_product is not None
            and chart_product is not None
            and "INSUFFICIENT PERMISSIONS" in message.upper()
            and f"CHART:{chart_product.epic}:" in message.upper()
            and len(self._chart_stream_epics) <= 1
        ):
            self._chart_quote_candle_fallback_active = True
            self._chart_product = self._selected_product
            self._chart_source_resolution_method = "selected PRICE candle fallback"
            self._chart_candle_series = None
            self._candle_history_service.reset_active_series()
            self.product_selector.set_chart_source(self._selected_product)
            self.chart_view.set_selected_product(self._selected_product)
            self.chart_view.set_stream_status("PRICE CANDLES (DEGRADED)")
            LOGGER.debug(
                "Streaming selected CHART denied; direct PRICE candle fallback active "
                "selected_product_epic=%s denied_chart_epic=%s scanner_reference_degraded=true",
                self._selected_product.epic,
                chart_product.epic,
            )
            self.statusBar().showMessage(
                "IG refuse les bougies du marché de référence ; graphique construit depuis "
                "les cotations directes du produit. Scanner technique indisponible pour ce "
                "mapping.",
                15000,
            )
            return
        if (
            self._streaming_adapter is not None
            and "CHART:" in message.upper()
            and self._live_chart_scale_actual != "1MINUTE"
            and not self._chart_stream_scale_fallback_attempted
        ):
            chart_product = self._chart_product or self._selected_product
            if chart_product is not None:
                self._chart_stream_scale_fallback_attempted = True
                self._live_chart_scale_actual = "1MINUTE"
                self._aggregation_mode = _aggregation_mode_for_interval(
                    self.chart_view.current_interval_seconds()
                )
                LOGGER.debug(
                    "Streaming chart scale fallback selected_product_epic=%s "
                    "chart_source_epic=%s live_chart_scale_requested=%s "
                    "live_chart_scale_actual=%s aggregation_mode=%s",
                    self._selected_product.epic if self._selected_product else "<none>",
                    chart_product.epic,
                    self._live_chart_scale_requested,
                    self._live_chart_scale_actual,
                    self._aggregation_mode,
                )
                try:
                    self._streaming_adapter.subscribe_charts(
                        list(self._chart_stream_epics or (chart_product.epic,)),
                        "1MINUTE",
                    )
                    self.statusBar().showMessage(
                        "Direct chart scale unavailable; "
                        "using 1-minute stream with local aggregation.",
                        12000,
                    )
                    return
                except Exception as exc:
                    LOGGER.debug("Streaming chart fallback subscribe failed error=%s", exc)
        self.statusBar().showMessage(f"Streaming: {message}", 12000)

    def _restart_streaming(self) -> None:
        self._stop_streaming()
        if self._active_connection is None:
            return
        session = self._active_connection.adapter.session
        if session is None:
            return
        if not session.lightstreamer_endpoint:
            self.chart_view.set_stream_status("STREAMING UNAVAILABLE")
            return
        if not self._active_connection.current_account_id:
            self.chart_view.set_stream_status("NO ACTIVE ACCOUNT")
            return
        stream_product = self._chart_product or self._selected_product
        if stream_product is None:
            return
        try:
            self._stream_projection_status = "connecting"
            self._publish_runtime_projections()
            requested_scale = "1MINUTE"
            self._live_chart_scale_requested = requested_scale
            self._live_chart_scale_actual = requested_scale
            self._aggregation_mode = "session_m1"
            self._chart_stream_scale_fallback_attempted = False
            self._chart_stream_permission_fallback_attempted = False
            bridge = StreamingEventBridge(self._stream_generation)
            bridge.quote_received.connect(self._on_current_stream_quote)
            bridge.chart_received.connect(self._on_current_stream_chart)
            bridge.status_changed.connect(self._on_current_stream_status)
            bridge.error_received.connect(self._on_current_stream_error)
            self._streaming_bridge = bridge
            adapter = IGStreamingAdapter(
                session=session,
                account_id=self._active_connection.current_account_id,
                event_sink=self._streaming_bridge,
            )
            self.chart_view.set_stream_status("CONNECTING")
            adapter.start()
            price_epics = _prioritized_price_epics(
                self._selected_product,
                self._visible_price_epics,
                stream_product,
            )
            adapter.subscribe_markets(price_epics[:PRODUCT_STREAM_ITEMS_LIMIT])
            chart_epics = _prioritized_chart_epics(
                stream_product,
                initial_ig_reference_epics(),
            )
            self._scanner_session_candles = MultiMarketSessionCandleService(
                self._scanner_binding_registry,
                candle_history_service=self._scanner_candle_history_service,
                reference_epics=tuple(chart_epics),
            )
            adapter.subscribe_charts(chart_epics, requested_scale)
            self._chart_stream_epics = tuple(chart_epics)
            self._streaming_adapter = adapter
            LOGGER.debug(
                "Streaming restarted selected_epic=%s source_epic=%s visible_prices=%s account=%s "
                "chart_streams=%s live_chart_scale_requested=%s "
                "live_chart_scale_actual=%s aggregation_mode=%s",
                self._selected_product.epic,
                stream_product.epic,
                len(price_epics[:PRODUCT_STREAM_ITEMS_LIMIT]),
                mask_identifier(self._active_connection.current_account_id),
                len(chart_epics),
                self._live_chart_scale_requested,
                self._live_chart_scale_actual,
                self._aggregation_mode,
            )
        except Exception as exc:
            LOGGER.debug("Streaming restart failed error=%s", exc)
            self.chart_view.set_stream_status("ERROR")
            self.statusBar().showMessage(f"Streaming unavailable: {exc}", 10000)

    def _refresh_selected_product_after_connection(self) -> None:
        if self._selected_product is None:
            return
        LOGGER.debug(
            "Refreshing selected product after connection epic=%s",
            self._selected_product.epic,
        )
        self._apply_selected_product_state()

    def _render_history_entry(
        self,
        product: TradableProduct,
        *,
        cached_entry: CachedHistoryEntry,
        source: CandleSource,
        anchor_price: float | None,
        status_message: str | None = None,
    ) -> None:
        if self._selected_product is None:
            return
        chart_series = self._candle_history_service.merge_price_series(
            selected_product_epic=self._selected_product.epic,
            chart_source_epic=product.epic,
            resolution_seconds=self.chart_view.current_interval_seconds(),
            resolution=_api_resolution_for_interval(self.chart_view.current_interval_seconds()),
            price_basis=self.chart_view.current_price_basis(),
            series=cached_entry.series,
            source=source,
        )
        self._chart_candle_series = chart_series
        self.chart_view.set_candles(chart_series.candles)
        if anchor_price is not None:
            self.chart_view.set_live_quote(
                Quote(
                    epic=product.epic,
                    bid=anchor_price,
                    offer=anchor_price,
                )
            )
        if status_message:
            self.statusBar().showMessage(status_message, 12000)

    def _history_candidate_products(self) -> list[TradableProduct]:
        if self._selected_product is None:
            return []
        candidates: list[TradableProduct] = []
        if self._chart_product is not None:
            candidates.append(self._chart_product)
        if all(product.epic != self._selected_product.epic for product in candidates):
            candidates.append(self._selected_product)
        if (
            self._active_connection is not None
            and self._selected_product.product_type in {ProductType.BARRIER, ProductType.OPTION}
            and all(product.product_type != ProductType.CASH_OR_DFB for product in candidates)
        ):
            resolved = _resolve_chart_source(
                self._selected_product,
                self.product_selector.results(),
                self._active_connection.adapter,
                chart_source_overrides=_chart_source_overrides_from_config(self._config),
            )
            if all(product.epic != resolved.product.epic for product in candidates):
                candidates.insert(0, resolved.product)
            self._chart_product = resolved.product
            self._chart_source_resolution_method = resolved.method
        return candidates

    def _load_selected_product_history(self, *, force_refresh: bool = False) -> None:
        if self._active_connection is None:
            return
        if self._selected_product is None:
            return
        if SESSION_ONLY_CANDLES:
            self._price_history_generation += 1
            chart_product = self._chart_product or self._selected_product
            price_basis = self.chart_view.current_price_basis()
            self._last_history_reload_price_basis = price_basis
            self._candle_history_service.reset_active_series()
            chart_series = self._candle_history_service.session_series(
                environment=self._active_connection.environment,
                account_id=self._active_connection.current_account_id,
                selected_product_epic=self._selected_product.epic,
                chart_source_epic=chart_product.epic,
                resolution_seconds=self.chart_view.current_interval_seconds(),
                price_basis=price_basis,
            )
            self._chart_candle_series = chart_series
            self.chart_view.set_candles(chart_series.candles)
            LOGGER.debug(
                "Session-only chart selected_product_epic=%s chart_source_epic=%s "
                "timeframe_seconds=%s candles=%s; historical REST/cache disabled",
                self._selected_product.epic,
                chart_product.epic,
                chart_series.resolution_seconds,
                len(chart_series.candles),
            )
            self.statusBar().showMessage(
                "Mode session : bougies construites depuis le flux M1; "
                "aucun historique REST/cache.",
                12000,
            )
            return

        # Dormant path retained for a future, explicitly selected history provider.
        self._price_history_generation += 1
        try:
            interval_seconds = self.chart_view.current_interval_seconds()
            range_key = self.chart_view.current_range_key()
            price_basis = self.chart_view.current_price_basis()
            self._last_history_reload_price_basis = price_basis
            time_axis_mode = self.chart_view.current_time_axis_mode()
            resolution, max_points = _history_request_spec(interval_seconds, range_key)
            account_id = self._active_connection.current_account_id
            history_candidates = self._history_candidate_products()
            if not history_candidates:
                return
            if not force_refresh:
                self._chart_candle_series = None
                self._candle_history_service.reset_active_series()
            displayed_from_cache = False
            for product in history_candidates:
                anchor_price = _product_anchor_price(product)
                cache_key = (product.epic, resolution, range_key, price_basis.value, max_points)
                LOGGER.debug(
                    "History request selected_product_epic=%s selected_product_type=%s "
                    "chart_source_epic=%s chart_source_type=%s "
                    "chart_source_resolution_method=%s history_epic=%s history_account=%s "
                    "timeframe_seconds=%s range_key=%s price_basis=%s time_axis_mode=%s "
                    "history_resolution=%s history_max_points=%s",
                    self._selected_product.epic,
                    getattr(self._selected_product.product_type, "value", "unknown"),
                    (self._chart_product or self._selected_product).epic,
                    getattr(
                        getattr(
                            self._chart_product or self._selected_product,
                            "product_type",
                            None,
                        ),
                        "value",
                        "unknown",
                    ),
                    self._chart_source_resolution_method,
                    product.epic,
                    mask_identifier(account_id),
                    interval_seconds,
                    range_key,
                    price_basis.value,
                    time_axis_mode.value,
                    resolution,
                    max_points,
                )
                cached_entry = self._price_history_cache.get(cache_key)
                if cached_entry is None:
                    cached_entry = _load_history_cache(
                        environment=self._active_connection.environment,
                        account_id=account_id,
                        epic=product.epic,
                        resolution=resolution,
                        range_key=range_key,
                        price_basis=price_basis.value,
                        max_points=max_points,
                    )
                    if cached_entry is not None:
                        self._price_history_cache[cache_key] = cached_entry
                cache_age = (
                    datetime.now(UTC) - cached_entry.saved_at.astimezone(UTC)
                    if cached_entry is not None
                    else None
                )
                current_chart_source = (
                    self._chart_candle_series.chart_source_epic
                    if self._chart_candle_series is not None
                    else None
                )
                if (
                    cached_entry is not None
                    and cache_age is not None
                    and cache_age <= HISTORY_CACHE_REFRESH_TTL
                    and not force_refresh
                    and (not displayed_from_cache or current_chart_source == product.epic)
                ):
                    self._render_history_entry(
                        product,
                        cached_entry=cached_entry,
                        source=CandleSource.CACHE,
                        anchor_price=anchor_price,
                        status_message=(
                            "Using cached history from "
                            f"{cached_entry.saved_at.strftime('%Y-%m-%d %H:%M:%S')}."
                        ),
                    )
                    displayed_from_cache = True
                    LOGGER.debug(
                        "History cache hit selected_product_epic=%s chart_source_epic=%s "
                        "cache_hit=true cache_miss=false historical_candles_loaded=%s "
                        "display_candles=%s cached_at=%s",
                        self._selected_product.epic,
                        product.epic,
                        len(cached_entry.series.prices),
                        self.chart_view.display_bar_count(),
                        cached_entry.saved_at.isoformat(),
                    )
                    self.statusBar().showMessage(
                        "Recent historical snapshot reused; live chart continues.",
                        12000,
                    )
                    LOGGER.debug(
                        "Recent history snapshot reused epic=%s age_seconds=%.3f",
                        product.epic,
                        cache_age.total_seconds(),
                    )
                    return
                elif cached_entry is not None:
                    LOGGER.debug(
                        "Stale historical snapshot ignored epic=%s age_seconds=%.3f",
                        product.epic,
                        cache_age.total_seconds() if cache_age is not None else -1,
                    )
                elif cached_entry is None:
                    LOGGER.debug(
                        "History cache miss selected_product_epic=%s chart_source_epic=%s "
                        "cache_hit=false cache_miss=true",
                        self._selected_product.epic,
                        product.epic,
                    )

                if self._history_allowance_state.is_blocked(
                    account_id=account_id,
                    epic=product.epic,
                ):
                    LOGGER.debug(
                        "Price history skipped epic=%s due to historical allowance pause "
                        "account=%s exhausted_at=%s last_error=%s",
                        product.epic,
                        mask_identifier(account_id),
                        self._history_allowance_state.exhausted_at.isoformat()
                        if self._history_allowance_state.exhausted_at
                        else None,
                        self._history_allowance_state.last_error,
                    )
                    if displayed_from_cache:
                        self.statusBar().showMessage(
                            "Using cached history; live chart continues.",
                            15000,
                        )
                    else:
                        retry_at = self._history_allowance_state.blocked_until
                        retry_text = (
                            retry_at.astimezone().strftime("%Y-%m-%d %H:%M")
                            if retry_at is not None
                            else "the next IG allowance window"
                        )
                        self.statusBar().showMessage(
                            "IG historical REST allowance reached. "
                            f"Automatic retry paused until {retry_text}; "
                            "current live candles only.",
                            15000,
                        )
                    return

            if self._api_allowance_exceeded:
                LOGGER.debug(
                    "Price history REST skipped selected_product_epic=%s "
                    "due to global allowance block; local cache remains available",
                    self._selected_product.epic,
                )
                if displayed_from_cache:
                    self.statusBar().showMessage(
                        "Using cached history; live chart continues.",
                        15000,
                    )
                return

            if self._price_history_thread is not None:
                self._pending_history_reload = True
                self._pending_history_force_refresh = (
                    self._pending_history_force_refresh or force_refresh
                )
                LOGGER.debug(
                    "Price history reload queued selected_product_epic=%s",
                    self._selected_product.epic,
                )
                return

            request = PriceHistoryRequest(
                generation=self._price_history_generation,
                environment=self._active_connection.environment,
                account_id=account_id,
                selected_product_epic=self._selected_product.epic,
                products=tuple(history_candidates),
                resolution=resolution,
                range_key=range_key,
                price_basis=price_basis,
                max_points=max_points,
            )
            self._start_price_history_worker(request)
        except Exception as exc:
            if _is_api_allowance_exceeded(exc):
                self._mark_api_allowance_exceeded()
            LOGGER.debug(
                "Price history load failed epic=%s error=%s",
                self._selected_product.epic if self._selected_product else "<none>",
                exc,
            )
            self.statusBar().showMessage(
                "Historical backfill unavailable; live chart is running.",
                10000,
            )

    def _start_price_history_worker(self, request: PriceHistoryRequest) -> None:
        if self._active_connection is None or self._price_history_thread is not None:
            return
        self._pending_history_reload = False
        self._pending_history_force_refresh = False
        self._price_history_thread = QtCore.QThread(self)
        self._price_history_worker = PriceHistoryWorker(
            self._active_connection.adapter,
            request,
        )
        self._price_history_worker.moveToThread(self._price_history_thread)
        self._price_history_thread.started.connect(self._price_history_worker.run)
        self._price_history_worker.succeeded.connect(self._on_price_history_success)
        self._price_history_worker.failed.connect(self._on_price_history_failure)
        self._price_history_worker.finished.connect(self._price_history_thread.quit)
        self._price_history_worker.finished.connect(self._price_history_worker.deleteLater)
        self._price_history_thread.finished.connect(self._price_history_thread.deleteLater)
        self._price_history_thread.finished.connect(self._clear_price_history_worker)
        self._price_history_thread.start()

    @QtCore.pyqtSlot(object)
    def _on_price_history_success(self, result: object) -> None:
        if not isinstance(result, PriceHistoryLoadResult):
            return
        request = result.request
        if not self._history_request_is_current(request):
            LOGGER.debug(
                "Stale price history result ignored selected_product_epic=%s generation=%s",
                request.selected_product_epic,
                request.generation,
            )
            return
        for history_attempt in result.attempts:
            product = history_attempt.product
            fallback_result = history_attempt.result
            if fallback_result.series is None:
                fallback_reason = _history_fallback_reason(fallback_result)
                LOGGER.debug(
                    "Price history fallback exhausted selected_product_epic=%s "
                    "chart_source_epic=%s history_epic=%s history_requested_points=%s "
                    "history_attempted_points=%s history_final_points=%s "
                    "historical_candles_loaded=0 fallback_reason=%s history_success=false",
                    request.selected_product_epic,
                    (self._chart_product or self._selected_product).epic,
                    product.epic,
                    request.max_points,
                    [attempt.max_points for attempt in fallback_result.attempts],
                    None,
                    fallback_reason,
                )
                if (
                    _history_fallback_is_historical_allowance(fallback_result)
                    and product.product_type == ProductType.CASH_OR_DFB
                ):
                    failed_points = (
                        fallback_result.attempts[0].max_points
                        if fallback_result.attempts
                        else request.max_points
                    )
                    LOGGER.debug(
                        "historical_rest_blocked=true reason=historical-data-allowance "
                        "failed_epic=%s failed_resolution=%s failed_points=%s",
                        product.epic,
                        request.resolution,
                        failed_points,
                    )
                    observed_at = datetime.now(UTC)
                    self._history_allowance_state = HistoricalAllowanceState(
                        exhausted=True,
                        exhausted_at=observed_at,
                        last_error=_history_fallback_last_error(fallback_result),
                        blocked_until=observed_at + HISTORY_ALLOWANCE_PROBE_COOLDOWN,
                        affected_account_id=request.account_id,
                        affected_epic="*",
                        remaining_points=0,
                    )
                    _save_history_allowance_state(
                        environment=request.environment,
                        account_id=request.account_id,
                        state=self._history_allowance_state,
                    )
                    self.statusBar().showMessage(
                        "IG historical REST allowance reached. "
                        "No automatic retry for 6 hours; current live candles only.",
                        15000,
                    )
                    return
                continue

            cache_key = (
                product.epic,
                request.resolution,
                request.range_key,
                request.price_basis.value,
                request.max_points,
            )
            cached_entry = CachedHistoryEntry(
                series=fallback_result.series,
                saved_at=datetime.now(UTC),
            )
            allowance = _extract_history_allowance(getattr(cached_entry.series, "raw", {}))
            if allowance is not None:
                remaining_points, total_points, expiry_seconds = allowance
                observed_at = datetime.now(UTC)
                exhausted = remaining_points < HISTORY_SNAPSHOT_POINTS
                self._history_allowance_state = HistoricalAllowanceState(
                    exhausted=exhausted,
                    exhausted_at=observed_at if exhausted else None,
                    last_error=None,
                    blocked_until=(
                        observed_at + timedelta(seconds=expiry_seconds)
                        if exhausted and expiry_seconds is not None
                        else None
                    ),
                    affected_account_id=request.account_id,
                    affected_epic="*",
                    remaining_points=remaining_points,
                    total_points=total_points,
                )
                _save_history_allowance_state(
                    environment=request.environment,
                    account_id=request.account_id,
                    state=self._history_allowance_state,
                )
            self._price_history_cache[cache_key] = cached_entry
            _save_history_cache(
                environment=request.environment,
                account_id=request.account_id,
                epic=product.epic,
                resolution=request.resolution,
                range_key=request.range_key,
                price_basis=request.price_basis.value,
                max_points=request.max_points,
                entry=cached_entry,
            )
            self._render_history_entry(
                product,
                cached_entry=cached_entry,
                source=CandleSource.REST,
                anchor_price=_product_anchor_price(product),
            )
            self.statusBar().showMessage(
                f"{len(cached_entry.series.prices)} recent {request.resolution} candles "
                "loaded from IG; direct live stream continues.",
                12000,
            )
            LOGGER.debug(
                "Price history loaded selected_product_epic=%s chart_source_epic=%s "
                "history_epic=%s history_requested_points=%s history_attempted_points=%s "
                "history_final_points=%s historical_candles_loaded=%s display_candles=%s "
                "resolution=%s range_key=%s history_success=true",
                request.selected_product_epic,
                (self._chart_product or self._selected_product).epic,
                product.epic,
                request.max_points,
                [attempt.max_points for attempt in fallback_result.attempts],
                fallback_result.selected_max_points,
                len(cached_entry.series.prices),
                self.chart_view.display_bar_count(),
                request.resolution,
                request.range_key,
            )
            return

        if self._chart_candle_series is not None:
            self.statusBar().showMessage(
                "Recent historical snapshot remains available; live chart continues.", 15000
            )
        else:
            self.statusBar().showMessage(
                "No fresh historical snapshot. Current live candles only until REST refresh.",
                10000,
            )

    @QtCore.pyqtSlot(object)
    def _on_price_history_failure(self, failure: object) -> None:
        if not isinstance(failure, PriceHistoryFailure):
            return
        if not self._history_request_is_current(failure.request):
            return
        if _is_api_allowance_exceeded(failure.message):
            self._mark_api_allowance_exceeded()
        LOGGER.debug(
            "Price history load failed selected_product_epic=%s error=%s",
            failure.request.selected_product_epic,
            failure.message,
        )
        self.statusBar().showMessage(
            "Historical backfill unavailable; live chart is running.",
            10000,
        )

    def _history_request_is_current(self, request: PriceHistoryRequest) -> bool:
        return (
            self._active_connection is not None
            and self._selected_product is not None
            and request.generation == self._price_history_generation
            and request.environment == self._active_connection.environment
            and request.account_id == self._active_connection.current_account_id
            and request.selected_product_epic == self._selected_product.epic
        )

    @QtCore.pyqtSlot()
    def _clear_price_history_worker(self) -> None:
        self._price_history_thread = None
        self._price_history_worker = None
        if self._pending_history_reload:
            force_refresh = self._pending_history_force_refresh
            self._pending_history_reload = False
            self._pending_history_force_refresh = False
            QtCore.QTimer.singleShot(
                0,
                lambda: self._load_selected_product_history(force_refresh=force_refresh),
            )

    @QtCore.pyqtSlot()
    def _refresh_history_after_gap(self) -> None:
        self._load_selected_product_history()

    @QtCore.pyqtSlot()
    def _reload_selected_product_history(self) -> None:
        self._load_selected_product_history()

    @QtCore.pyqtSlot(int)
    def _on_chart_resolution_changed(self, _interval_seconds: int) -> None:
        if self._selected_product is None:
            return
        self._load_selected_product_history()

    @QtCore.pyqtSlot(str)
    def _on_chart_range_changed(self, _range_key: str) -> None:
        if self._selected_product is None:
            return
        self._load_selected_product_history()

    @QtCore.pyqtSlot(object)
    def _on_chart_price_basis_changed(self, price_basis: object) -> None:
        if not hasattr(self, "chart_view"):
            return
        if self._active_connection is None:
            return
        if self._selected_product is None:
            return
        current_price_basis = self.chart_view.current_price_basis()
        if price_basis != current_price_basis:
            return
        if current_price_basis == self._last_history_reload_price_basis:
            return
        self._last_history_reload_price_basis = current_price_basis
        self._load_selected_product_history()

    def _stop_streaming(self) -> None:
        self._stream_generation += 1
        self._streaming_bridge = None
        self._stream_projection_status = "disconnected"
        self._publish_runtime_projections()
        if self._streaming_adapter is None:
            return
        try:
            self._streaming_adapter.stop()
        except Exception as exc:
            LOGGER.debug("Streaming stop ignored error=%s", exc)
        finally:
            self._streaming_adapter = None

    @QtCore.pyqtSlot()
    def _show_help(self) -> None:
        QtWidgets.QMessageBox.information(
            self,
            "TradingIG Help",
            "Help content will be loaded from a Markdown file in a future update.",
        )

    @QtCore.pyqtSlot()
    def _show_log(self) -> None:
        LOGGER.debug("Log viewer open")
        LogViewDialog(parent=self).exec()

    @QtCore.pyqtSlot()
    def _show_about(self) -> None:
        AboutDialog(self).exec()

    def closeEvent(self, event: QtCore.QEvent) -> None:
        self._paper_freshness_timer.stop()
        self._official_news_refresh_timer.stop()
        self._openai_context_refresh_timer.stop()
        self._calendar_refresh_timer.stop()
        if self._official_news_thread is not None:
            self._official_news_thread.quit()
            if not self._official_news_thread.wait(11_000):
                LOGGER.warning("Official news worker did not stop before GUI shutdown")
        if self._openai_context_thread is not None:
            self._openai_context_thread.quit()
            if not self._openai_context_thread.wait(31_000):
                LOGGER.warning("OpenAI context worker did not stop before GUI shutdown")
        if self._calendar_context_thread is not None:
            self._calendar_context_thread.quit()
            if not self._calendar_context_thread.wait(11_000):
                LOGGER.warning("Calendar context worker did not stop before GUI shutdown")
        if self._workspace_persistence:
            self._config.workspace = self._capture_workspace_state()
            try:
                save_config(self._config, self._config_path)
            except OSError as exc:
                LOGGER.warning("Workspace settings could not be saved: %s", exc)
        self._stop_streaming()
        self._logout_active_connection()
        super().closeEvent(event)

    def _mark_api_allowance_exceeded(self) -> None:
        if self._api_allowance_exceeded:
            return
        self._api_allowance_exceeded = True
        LOGGER.debug("IG public API allowance exceeded; further REST backfill is paused")
        self.statusBar().showMessage(
            "IG API allowance exceeded. Product discovery fallback and price history "
            "backfill are paused for this session.",
            15000,
        )

    def _load_cached_discovery_results(self) -> None:
        cache_path = _discovery_cache_path(self._config.environment)
        results = read_discovery_report(cache_path)
        if not results:
            if self._loaded_cache_environment != self._config.environment:
                self.product_selector.set_results([])
            self._loaded_cache_environment = self._config.environment
            return
        self._loaded_cache_environment = self._config.environment
        LOGGER.debug(
            "Product discovery cache loaded environment=%s results=%s products=%s",
            self._config.environment.value,
            len(results),
            sum(len(result.products) for result in results),
        )
        self.product_selector.set_results(results)
        if self._config.last_selected_product_epic:
            cached_product = _find_product_by_epic(results, self._config.last_selected_product_epic)
            if cached_product is not None:
                self._on_product_selected(cached_product)

    def _save_discovery_cache(self, results: list[ProductDiscoveryResult]) -> None:
        cache_path = _discovery_cache_path(self._config.environment)
        write_discovery_report(results, cache_path)
        self._loaded_cache_environment = self._config.environment
        LOGGER.debug(
            "Product discovery cache saved environment=%s path=%s results=%s",
            self._config.environment.value,
            cache_path,
            len(results),
        )

    def _apply_selected_product_state(self) -> None:
        if self._selected_product is None:
            return
        product = self._selected_product
        resolved_chart_source = _resolve_chart_source(
            product,
            self.product_selector.results(),
            self._active_connection.adapter
            if self._active_connection is not None and not self._api_allowance_exceeded
            else None,
            chart_source_overrides=_chart_source_overrides_from_config(self._config),
        )
        self._chart_product = resolved_chart_source.product
        self._chart_source_resolution_method = resolved_chart_source.method
        self._chart_candle_series = None
        self._chart_quote_candle_fallback_active = False
        LOGGER.debug(
            "Selected product state applied selected_epic=%s selected_product_type=%s "
            "chart_source_epic=%s chart_source_type=%s chart_source_resolution_method=%s",
            product.epic,
            getattr(getattr(product, "product_type", None), "value", "unknown"),
            (self._chart_product or product).epic,
            getattr(
                getattr((self._chart_product or product), "product_type", None),
                "value",
                "unknown",
            ),
            self._chart_source_resolution_method,
        )
        self.product_selector.set_selected_product(product)
        self.product_selector.set_chart_source(self._chart_product or product)
        self.chart_view.set_selected_product(self._chart_product or product)
        self._load_selected_product_history()
        self._restart_streaming()


def run_gui() -> int:
    configure_logging()
    session_id = emit_session_banner()
    if session_id:
        LOGGER.debug("GUI session banner emitted session_id=%s", session_id)
    LOGGER.debug("GUI launch start")
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    window = MainWindow(
        workspace_persistence=True,
        official_news_providers=(
            federal_reserve_monetary_news_provider(),
            ecb_press_news_provider(),
        ),
    )
    window.show()
    try:
        return app.exec()
    finally:
        logging.getLogger("trading_ig_assistant.session").info("=" * 86)
        logging.getLogger("trading_ig_assistant.session").info("TradingIG session end")
        logging.getLogger("trading_ig_assistant.session").info("=" * 86)


def humanize_ig_error(message: str) -> str:
    if "exceeded-api-key-allowance" in message:
        return (
            "IG public API allowance exceeded. Stop discovery retries for now and reconnect "
            "later before requesting history again."
        )
    if "api-key-invalid" in message:
        return (
            "API key invalid for this request. Check that the environment matches the key: "
            "demo key with demo, live key with live. If this key was exposed, revoke it and "
            "generate a new one."
        )
    if "api-key-restricted" in message:
        return "API key restricted to another account/environment."
    if "api-key-disabled" in message:
        return "API key disabled in IG settings."
    if "api-key-revoked" in message:
        return "API key revoked. Generate a new key in IG settings."
    if "failure-invalid-client-security-token" in message:
        return (
            "IG rejected the client security token during login. Verify the selected "
            "environment, the API key for that environment, and whether the key is still "
            "enabled in My IG."
        )
    if "stopbrock" in message or "stockbroking-not-supported" in message:
        return (
            "IG rejected the demo connection. Verify that the demo API identifier, demo "
            "password, and demo API key were created in the demo tab, not reused from live."
        )
    if "validation.pattern.invalid.auth.identifier" in message:
        return (
            "Invalid API identifier format. For demo, use the demo API identifier you chose "
            "in the IG demo API tab, not your email address."
        )
    if (
        "authentication.timeout" in message
        or "get.session.timeout" in message
        or "timed out" in message
    ):
        return "IG authentication timed out. Retry once, then verify environment and credentials."
    if "invalid-details" in message:
        return "Invalid API identifier/password for the selected IG environment."
    if "client-suspended" in message:
        return (
            "IG reports this API client is suspended. Stop retrying for now, verify that you can "
            "log in to the IG web platform with the same demo API credentials, check whether IG "
            "requires agreements/KYC/API activation, then contact IG support if the account "
            "remains blocked."
        )
    if "too-many-failed-attempts" in message:
        return (
            "IG reports too many failed login attempts. Stop retrying and wait for the lock "
            "to clear before trying again."
        )
    if "invalid-security-token" in message or "client-token-invalid" in message:
        return (
            "IG rejected the session security token. Disconnect/reconnect and verify that the "
            "selected account belongs to the selected live/demo environment."
        )
    return message


def _is_api_allowance_exceeded(error: Exception | str) -> bool:
    return "exceeded-api-key-allowance" in str(error)


def _api_resolution_for_interval(interval_seconds: int) -> str:
    mapping = {
        60: "MINUTE",
        300: "MINUTE_5",
        600: "MINUTE_10",
        900: "MINUTE_15",
        1800: "MINUTE_30",
        3600: "HOUR",
        7200: "HOUR_2",
        14_400: "HOUR_4",
        86_400: "DAY",
    }
    return mapping.get(interval_seconds, "MINUTE")


def _history_request_spec(interval_seconds: int, range_key: str) -> tuple[str, int]:
    del range_key
    resolution = _api_resolution_for_interval(interval_seconds)
    return (resolution, HISTORY_SNAPSHOT_POINTS)


def _latest_series_gap_key(
    series: ChartCandleSeries,
) -> tuple[str, int, str, str] | None:
    if len(series.candles) < 2:
        return None
    previous, current = series.candles[-2:]
    expected = timedelta(seconds=series.resolution_seconds)
    if current.timestamp - previous.timestamp <= expected:
        return None
    return (
        series.chart_source_epic,
        series.resolution_seconds,
        previous.timestamp.isoformat(),
        current.timestamp.isoformat(),
    )


def _resolve_account_id(
    accounts: list[Account],
    preferred_account_id: str | None,
    fallback_account_id: str | None,
) -> str | None:
    known_ids = {account.account_id for account in accounts}
    if preferred_account_id in known_ids:
        return preferred_account_id
    if fallback_account_id in known_ids:
        return fallback_account_id
    for account in accounts:
        if account.preferred:
            return account.account_id
    return accounts[0].account_id if accounts else None


def _results_contain_invalid_security_token(results: list[ProductDiscoveryResult]) -> bool:
    has_token_error = any(
        is_invalid_security_token_error(error.message)
        for result in results
        for error in result.errors
    )
    has_products = any(result.products for result in results)
    return has_token_error and not has_products


def _first_discovered_product(results: list[ProductDiscoveryResult]) -> TradableProduct | None:
    for result in results:
        if result.products:
            return result.products[0]
    return None


def _find_product_by_epic(
    results: list[ProductDiscoveryResult],
    epic: str,
) -> TradableProduct | None:
    for result in results:
        for product in result.products:
            if product.epic == epic:
                return product
    return None


def _scanner_runtime_products(
    results: list[ProductDiscoveryResult],
    selected: TradableProduct,
) -> tuple[TradableProduct, ...]:
    """Return one exact product identity per EPIC, prioritizing the active selection."""

    by_epic = {
        product.epic: product for result in results for product in result.products if product.epic
    }
    by_epic[selected.epic] = selected
    return tuple(by_epic[epic] for epic in sorted(by_epic))


def _discovery_cache_path(environment: IGEnvironment) -> Path:
    return Path.home() / ".trading_ig_assistant" / f"product_discovery_{environment.value}.json"


def _history_cache_root() -> Path:
    return Path.home() / ".trading_ig_assistant" / "cache" / "history"


def _history_allowance_state_path(
    *,
    environment: IGEnvironment,
    account_id: str | None,
) -> Path:
    account_marker = _history_account_marker(account_id)
    return _history_cache_root() / environment.value / f"allowance_{account_marker}.json"


def _load_history_allowance_state(
    *,
    environment: IGEnvironment,
    account_id: str | None,
) -> HistoricalAllowanceState:
    path = _history_allowance_state_path(environment=environment, account_id=account_id)
    if not path.exists():
        return HistoricalAllowanceState()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        exhausted_at = _optional_aware_datetime(payload.get("exhausted_at"))
        blocked_until = _optional_aware_datetime(payload.get("blocked_until"))
        return HistoricalAllowanceState(
            exhausted=bool(payload.get("exhausted", False)),
            exhausted_at=exhausted_at,
            last_error=str(payload.get("last_error") or "") or None,
            blocked_until=blocked_until,
            affected_account_id=account_id,
            affected_epic="*",
            remaining_points=_optional_int(payload.get("remaining_points")),
            total_points=_optional_int(payload.get("total_points")),
        )
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        LOGGER.debug("History allowance state read failed path=%s error=%s", path, exc)
        return HistoricalAllowanceState()


def _save_history_allowance_state(
    *,
    environment: IGEnvironment,
    account_id: str | None,
    state: HistoricalAllowanceState,
) -> None:
    path = _history_allowance_state_path(environment=environment, account_id=account_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "exhausted": state.exhausted,
        "exhausted_at": state.exhausted_at.isoformat() if state.exhausted_at else None,
        "blocked_until": state.blocked_until.isoformat() if state.blocked_until else None,
        "last_error": state.last_error,
        "remaining_points": state.remaining_points,
        "total_points": state.total_points,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _extract_history_allowance(
    raw: dict[str, object],
) -> tuple[int, int | None, int | None] | None:
    metadata = raw.get("metadata")
    allowance = metadata.get("allowance") if isinstance(metadata, dict) else None
    if not isinstance(allowance, dict):
        direct = raw.get("allowance")
        allowance = direct if isinstance(direct, dict) else None
    if allowance is None:
        return None
    remaining = _optional_int(allowance.get("remainingAllowance"))
    if remaining is None:
        return None
    return (
        remaining,
        _optional_int(allowance.get("totalAllowance")),
        _optional_int(allowance.get("allowanceExpiry")),
    )


def _optional_aware_datetime(value: object) -> datetime | None:
    if value in (None, ""):
        return None
    parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        raise ValueError("allowance datetime must be timezone-aware")
    return parsed.astimezone(UTC)


def _optional_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _history_cache_path(
    *,
    environment: IGEnvironment,
    account_id: str | None,
    epic: str,
    resolution: str,
    range_key: str,
    price_basis: str,
    max_points: int,
) -> Path:
    account_marker = _history_account_marker(account_id)
    payload = json.dumps(
        {
            "environment": environment.value,
            "account": account_marker,
            "epic": epic,
            "resolution": resolution,
            "range_key": range_key,
            "price_basis": price_basis,
            "max_points": max_points,
        },
        sort_keys=True,
    )
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()
    return _history_cache_root() / environment.value / f"{digest}.json"


def _history_account_marker(account_id: str | None) -> str:
    if not account_id:
        return "no-account"
    return hashlib.sha1(account_id.encode("utf-8")).hexdigest()[:12]


def _load_history_cache(
    *,
    environment: IGEnvironment,
    account_id: str | None,
    epic: str,
    resolution: str,
    range_key: str,
    price_basis: str,
    max_points: int,
) -> CachedHistoryEntry | None:
    cache_path = _history_cache_path(
        environment=environment,
        account_id=account_id,
        epic=epic,
        resolution=resolution,
        range_key=range_key,
        price_basis=price_basis,
        max_points=max_points,
    )
    if not cache_path.exists():
        return None
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        LOGGER.debug("History cache read failed path=%s error=%s", cache_path, exc)
        return None
    prices = payload.get("prices", [])
    saved_at_text = payload.get("saved_at")
    if not isinstance(prices, list) or not saved_at_text:
        return None
    try:
        saved_at = datetime.fromisoformat(str(saved_at_text))
    except ValueError:
        saved_at = datetime.now(UTC)
    return CachedHistoryEntry(
        series=PriceSeries(epic=epic, prices=prices, raw={"cache": True}),
        saved_at=saved_at,
    )


def _save_history_cache(
    *,
    environment: IGEnvironment,
    account_id: str | None,
    epic: str,
    resolution: str,
    range_key: str,
    price_basis: str,
    max_points: int,
    entry: CachedHistoryEntry,
) -> None:
    cache_path = _history_cache_path(
        environment=environment,
        account_id=account_id,
        epic=epic,
        resolution=resolution,
        range_key=range_key,
        price_basis=price_basis,
        max_points=max_points,
    )
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "saved_at": entry.saved_at.isoformat(),
        "epic": epic,
        "resolution": resolution,
        "range_key": range_key,
        "price_basis": price_basis,
        "max_points": max_points,
        "prices": entry.series.prices,
    }
    cache_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _product_anchor_price(product: TradableProduct) -> float | None:
    for value in (product.offer, product.bid, product.ko_level, product.strike):
        if isinstance(value, (int, float)) and value > 0:
            return float(value)
    return None


def _quote_from_chart_update(chart_update: ChartCandleUpdate) -> Quote | None:
    raw = chart_update.raw or {}
    bid = _optional_float(raw.get("BID_CLOSE"))
    offer = _optional_float(raw.get("OFR_CLOSE"))
    if bid is None and offer is None and chart_update.close is None:
        return None
    if bid is None:
        bid = chart_update.close
    if offer is None:
        offer = chart_update.close
    return Quote(
        epic=chart_update.epic,
        bid=bid,
        offer=offer,
        net_change=_optional_float(raw.get("DAY_NET_CHG_MID")),
        percent_change=_optional_float(raw.get("DAY_PERC_CHG_MID")),
        timestamp_ms=chart_update.timestamp_ms,
        snapshot=chart_update.snapshot,
        raw=dict(raw),
    )


def _scanner_quote_spread(quote: Quote | None) -> Decimal | None:
    if quote is None or quote.delayed is True or quote.bid is None or quote.offer is None:
        return None
    return Decimal(str(quote.offer)) - Decimal(str(quote.bid))


def _scanner_fee_for_product(
    config: AppConfig,
    product: TradableProduct,
) -> Decimal | None:
    """Return only fees representable by the flat per-unit scanner model."""

    if product.asset_class is AssetClass.SHARES:
        return None
    return config.scanner_execution_costs.fee_for_product_type(product.product_type)


def _resolve_chart_source(
    selected_product: TradableProduct,
    results: list[ProductDiscoveryResult],
    adapter: IGRestAdapter | None = None,
    *,
    chart_source_overrides: dict[str, str] | None = None,
) -> ResolvedChartSource:
    resolved_product = _resolve_chart_source_product(
        selected_product,
        results,
        adapter,
        chart_source_overrides=chart_source_overrides,
    )
    method = _chart_source_resolution_method(
        selected_product,
        resolved_product,
        chart_source_overrides or {},
    )
    return ResolvedChartSource(product=resolved_product, method=method)


def _resolve_chart_source_product(
    selected_product: TradableProduct,
    results: list[ProductDiscoveryResult],
    _adapter: IGRestAdapter | None = None,
    *,
    chart_source_overrides: dict[str, str] | None = None,
) -> TradableProduct:
    if selected_product.product_type == ProductType.CASH_OR_DFB:
        LOGGER.debug(
            "Chart source already cash selected_product_epic=%s selected_product_type=%s "
            "chart_source_epic=%s chart_source_type=%s",
            selected_product.epic,
            selected_product.product_type.value,
            selected_product.epic,
            selected_product.product_type.value,
        )
        return selected_product

    candidates: list[TradableProduct] = []
    for result in results:
        candidates.extend(result.products)

    override_product = _resolve_chart_source_override(
        selected_product,
        candidates,
        chart_source_overrides or {},
    )
    if override_product is not None:
        LOGGER.debug(
            "Chart source resolved via override selected_product_epic=%s "
            "selected_product_type=%s chart_source_epic=%s chart_source_type=%s",
            selected_product.epic,
            selected_product.product_type.value,
            override_product.epic,
            override_product.product_type.value,
        )
        return override_product

    LOGGER.debug(
        "No explicit underlying chart mapping; using selected product EPIC for chart "
        "selected_product_epic=%s selected_product_type=%s chart_source_epic=%s "
        "chart_source_type=%s",
        selected_product.epic,
        selected_product.product_type.value,
        selected_product.epic,
        selected_product.product_type.value,
    )
    return selected_product


def _chart_source_resolution_method(
    selected_product: TradableProduct,
    resolved_product: TradableProduct,
    chart_source_overrides: dict[str, str],
) -> str:
    override_product = _resolve_chart_source_override(selected_product, [], chart_source_overrides)
    if override_product is not None and override_product.epic == resolved_product.epic:
        return "override"
    return "selected fallback"


def _resolve_chart_source_override(
    selected_product: TradableProduct,
    candidates: list[TradableProduct],
    chart_source_overrides: dict[str, str],
) -> TradableProduct | None:
    if not chart_source_overrides:
        return None
    override_keys = [
        selected_product.epic,
        selected_product.name,
        _strip_chart_suffixes(selected_product.name),
        _normalize_chart_base_name(selected_product.name),
    ]
    override_epic = None
    lowered_overrides = {
        str(key).strip().lower(): value for key, value in chart_source_overrides.items()
    }
    for key in override_keys:
        override_epic = lowered_overrides.get(str(key).strip().lower())
        if override_epic:
            break
    if not override_epic:
        return None
    for candidate in candidates:
        if candidate.epic == override_epic:
            return candidate
    return TradableProduct(
        epic=override_epic,
        name=_strip_chart_suffixes(selected_product.name),
        product_type=ProductType.CASH_OR_DFB,
        instrument_type=selected_product.instrument_type,
        asset_class=selected_product.asset_class,
        status="TRADEABLE",
    )


def _strip_chart_suffixes(name: str) -> str:
    text = " ".join(str(name).split()).strip()
    text = re.sub(r"\s*\((?:S1|E1)\)\s*$", "", text, flags=re.IGNORECASE)
    suffix_patterns = [
        r"\s+barri\S*\s+achat$",
        r"\s+barri\S*\s+vente$",
        r"\s+barrier\s+call$",
        r"\s+barrier\s+put$",
        r"\s+call$",
        r"\s+put$",
    ]
    previous = None
    while previous != text:
        previous = text
        for pattern in suffix_patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    return text.strip()


def _normalize_chart_base_name(name: str) -> str:
    return _strip_chart_suffixes(name).lower()


def _optional_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _history_fallback_reason(result: HistoricalPriceFetchResult) -> str:
    if _history_fallback_is_historical_allowance(result):
        return "historical-data-allowance"
    last_error = _history_fallback_last_error(result)
    if last_error:
        return last_error
    return "empty-price-list"


def _history_fallback_is_historical_allowance(result: HistoricalPriceFetchResult) -> bool:
    return bool(result.attempts) and all(
        (attempt.error is not None and is_historical_allowance_error(attempt.error))
        or attempt.error == "empty-price-list"
        for attempt in result.attempts
        if not attempt.success
    )


def _history_fallback_last_error(result: HistoricalPriceFetchResult) -> str:
    for attempt in reversed(result.attempts):
        if attempt.error:
            return attempt.error
    return ""


def _merge_candle_sources(
    existing_sources: tuple[CandleSource, ...],
    new_source: CandleSource,
) -> tuple[CandleSource, ...]:
    merged = list(existing_sources)
    if new_source not in merged:
        merged.append(new_source)
    return tuple(merged)


def _aggregation_mode_for_interval(interval_seconds: int) -> str:
    if interval_seconds <= 60:
        return "direct"
    whole_minutes = max(1, interval_seconds // 60)
    if interval_seconds % 3600 == 0:
        return f"local_1min_to_{max(1, interval_seconds // 3600)}h"
    return f"local_1min_to_{whole_minutes}min"
