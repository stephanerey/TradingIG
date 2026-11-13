"""Opt-in GUI V2 shell; it owns no IG/OpenAI/SQLite connector."""

from __future__ import annotations

import logging
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from PyQt5 import QtCore, QtWidgets

from trading_ig_assistant.adapters.api_connection_testers import (
    BoundedJsonConnectionTester,
    GdeltConnectionTester,
    TavilyConnectionTester,
)
from trading_ig_assistant.adapters.credentials import (
    KeyringApiKeyStore,
    build_default_credential_store,
)
from trading_ig_assistant.adapters.gdelt_news import GdeltNewsProvider
from trading_ig_assistant.adapters.official_rss_news import (
    ecb_press_news_provider,
    federal_reserve_monetary_news_provider,
)
from trading_ig_assistant.adapters.tavily_extract import (
    TavilyExtractConfig,
    TavilyExtractProvider,
)
from trading_ig_assistant.adapters.tavily_news import TavilyNewsConfig, TavilyNewsProvider
from trading_ig_assistant.app.config import (
    ApiProviderConfig,
    AppConfig,
    WorkspaceState,
    default_config_path,
    default_paper_database_path,
    load_config,
    save_config,
)
from trading_ig_assistant.app.qt_api_credentials_controller import ApiCredentialsController
from trading_ig_assistant.app.qt_catalogue_controller import CatalogueSearchController
from trading_ig_assistant.app.qt_connection_controller import ReadOnlyConnectionController
from trading_ig_assistant.app.qt_macro_context_controller import MacroContextController
from trading_ig_assistant.app.qt_market_stream_controller import (
    DEFAULT_PRIORITY_REFERENCE_EPICS,
    CatalogueMarketStreamController,
)
from trading_ig_assistant.app.qt_paper_session_controller import PaperSessionController
from trading_ig_assistant.app.qt_runtime_bridge import RuntimeQtBridge
from trading_ig_assistant.app.qt_scanner_session_controller import ScannerSessionController
from trading_ig_assistant.app.runtime.trading_runtime import TradingRuntime
from trading_ig_assistant.app.ui_facade import (
    RuntimeUIFacade,
    TradingUIFacade,
    build_empty_ui_facade,
)
from trading_ig_assistant.domain.market_navigation import initial_ig_reference_epics
from trading_ig_assistant.persistence.repositories import MarketAIAnalysisRepository
from trading_ig_assistant.persistence.research_quota_store import (
    JsonResearchQuotaStore,
    default_research_quota_path,
)
from trading_ig_assistant.persistence.sqlite_store import SQLiteStore
from trading_ig_assistant.services.api_credential_manager import ApiCredentialManager
from trading_ig_assistant.services.market_intelligence_runtime import (
    MarketIntelligenceRuntime,
)
from trading_ig_assistant.services.market_intelligence_scheduler import (
    IntelligenceFreshnessPolicy,
)
from trading_ig_assistant.services.market_navigation_catalog_service import (
    IGProductMarketBindingRegistry,
)
from trading_ig_assistant.services.quote_candle_fallback_service import (
    QuoteCandleFallbackService,
)
from trading_ig_assistant.services.research_quota_service import ResearchQuotaManager
from trading_ig_assistant.services.technical_research_journal import (
    TechnicalResearchRecorder,
)
from trading_ig_assistant.ui.i18n.language_manager import LanguageManager
from trading_ig_assistant.ui.shell.account_header import AccountHeader
from trading_ig_assistant.ui.shell.macro_compact_bar import MacroCompactBar
from trading_ig_assistant.ui.shell.nav_sidebar import NavSidebar
from trading_ig_assistant.ui.shell.page_router import PageRouter
from trading_ig_assistant.ui.shell.page_specs import PAGE_SPEC_BY_KEY
from trading_ig_assistant.ui.theme.theme_manager import ThemeManager
from trading_ig_assistant.utils.logging_config import configure_logging, emit_session_banner

LOGGER = logging.getLogger(__name__)


class MainWindowV2(QtWidgets.QMainWindow):
    def __init__(
        self,
        *,
        config: AppConfig | None = None,
        config_path: Path | None = None,
        facade: TradingUIFacade | None = None,
        connection_controller: ReadOnlyConnectionController | None = None,
        catalogue_controller: CatalogueSearchController | None = None,
        market_stream_controller: CatalogueMarketStreamController | None = None,
        scanner_session_controller: ScannerSessionController | None = None,
        paper_session_controller: PaperSessionController | None = None,
        macro_context_controller: MacroContextController | None = None,
        api_credentials_controller: ApiCredentialsController | None = None,
        workspace_persistence: bool = False,
    ) -> None:
        super().__init__()
        self._config = config or AppConfig()
        self._config_path = config_path or default_config_path()
        self._workspace_persistence = workspace_persistence
        self._facade = facade or build_empty_ui_facade()
        self._connection_controller = connection_controller
        self._catalogue_controller = catalogue_controller
        self._market_stream_controller = market_stream_controller
        self._scanner_session_controller = scanner_session_controller
        self._paper_session_controller = paper_session_controller
        self._macro_context_controller = macro_context_controller
        self._api_credentials_controller = api_credentials_controller
        self._quote_candle_fallback_service = QuoteCandleFallbackService()
        self._watchlist_environment = self._config.environment
        self._watchlist_account_id = self._initial_watchlist_account_id()
        self.language = LanguageManager(self._config.workspace.locale)
        self.language.language_changed.connect(self.retranslate_ui)
        self._bridge = RuntimeQtBridge(self._facade)
        self._bridge.account_header_changed.connect(self._on_account_header)
        self._bridge.catalogue_changed.connect(self._on_catalogue)
        self._bridge.dashboard_changed.connect(self._on_dashboard)
        self._bridge.scanner_changed.connect(self._on_scanner)
        self._bridge.health_changed.connect(self._on_health)
        self._bridge.paper_history_changed.connect(self._on_paper_history)
        self._bridge.macro_changed.connect(self._on_macro)
        self._bridge.optimization_changed.connect(self._on_optimization)

        self.resize(1280, 820)
        self._build_layout()
        self.router.followed_product_epics_changed.connect(
            self._on_followed_product_epics_changed
        )
        self._activate_watchlist_context(
            self._watchlist_environment,
            self._watchlist_account_id,
        )
        self._bind_connection_controller()
        self._bind_catalogue_controller()
        self._bind_market_stream_controller()
        self._bind_paper_session_controller()
        self._bind_macro_context_controller()
        self._bind_api_credentials_controller()
        self._restore_workspace_state()
        self.account_header.set_snapshot(self._facade.read_account_header())
        self.router.set_dashboard_snapshot(self._facade.read_dashboard())
        self.router.set_catalogue_snapshot(self._facade.read_catalogue())
        self.router.set_scanner_snapshot(self._facade.read_scanner())
        self.router.set_health_snapshot(self._facade.read_health())
        self.router.set_paper_history_snapshot(self._facade.read_paper_history())
        macro_snapshot = self._facade.read_macro()
        self.router.set_macro_snapshot(macro_snapshot)
        self.macro_bar.set_snapshot(macro_snapshot)
        self.router.set_optimization_snapshot(self._facade.read_optimization())
        self.retranslate_ui()

    def _bind_connection_controller(self) -> None:
        controller = self._connection_controller
        self.account_header.set_connection_controls_available(controller is not None)
        if controller is None:
            return
        self.account_header.connect_demo_requested.connect(controller.connect_demo)
        self.account_header.connect_live_requested.connect(controller.connect_live)
        self.account_header.disconnect_requested.connect(self._disconnect_read_only)
        self.account_header.account_selected.connect(self._switch_read_only_account)
        controller.busy_changed.connect(self.account_header.set_busy)
        controller.accounts_changed.connect(self.account_header.set_accounts)
        controller.error.connect(self._on_connection_error)
        controller.connection_changed.connect(self._on_runtime_connection_changed)
        controller.ready_to_close.connect(self.close)
        active = controller.active_connection
        if active is not None:
            self.account_header.set_accounts(
                tuple(active.accounts),
                active.current_account_id,
            )

    def _bind_catalogue_controller(self) -> None:
        controller = self._catalogue_controller
        if controller is None:
            return
        self.router.catalogue_search_requested.connect(self._search_catalogue)
        self.router.catalogue_product_details_requested.connect(
            controller.resolve_product_details
        )
        controller.busy_changed.connect(self.router.set_catalogue_busy)
        controller.error.connect(self._on_connection_error)

    def _bind_market_stream_controller(self) -> None:
        controller = self._market_stream_controller
        if controller is None:
            return
        self.router.catalogue_stream_scope_changed.connect(controller.sync_scope)
        controller.coverage_changed.connect(self.router.set_catalogue_stream_coverage)
        controller.error.connect(self._on_connection_error)
        if self._scanner_session_controller is not None:
            controller.chart_update_received.connect(
                self._scanner_session_controller.ingest_chart_update
            )
            controller.chart_market_unavailable.connect(
                self._scanner_session_controller.enable_product_quote_fallback
            )
            self._scanner_session_controller.error.connect(self._on_connection_error)
        controller.chart_update_received.connect(self.router.apply_chart_update)
        controller.quote_received.connect(self._on_market_quote)
        if self._paper_session_controller is not None:
            controller.quote_received.connect(
                self._paper_session_controller.process_market_quote
            )

    def _bind_paper_session_controller(self) -> None:
        controller = self._paper_session_controller
        if controller is None:
            return
        self.router.paper_save_requested.connect(controller.save)
        self.router.paper_restore_requested.connect(controller.request_restore)
        self.router.paper_stop_requested.connect(controller.move_stop)
        self.router.paper_close_requested.connect(controller.request_close)
        self.router.paper_submission_requested.connect(self._confirm_paper_submission)
        controller.message.connect(self._on_paper_message)
        controller.error.connect(self._on_paper_message)
        controller.submission_completed.connect(self.router.show_paper_submission_result)
        controller.state_changed.connect(lambda _has_state: self._sync_paper_stream_scope())
        controller.restore_confirmation_required.connect(self._confirm_paper_restore)
        controller.close_confirmation_required.connect(self._confirm_paper_close)
        self._sync_paper_stream_scope()

    def _bind_macro_context_controller(self) -> None:
        controller = self._macro_context_controller
        if controller is None:
            return
        self.router.macro_news_refresh_requested.connect(controller.refresh_news)
        self.router.macro_ai_analysis_requested.connect(controller.run_ai_analysis)
        controller.busy_changed.connect(self.router.set_macro_busy)
        controller.ai_busy_changed.connect(self.router.set_macro_ai_busy)
        controller.ai_failed.connect(self.router.set_macro_ai_error)
        controller.error.connect(self._on_connection_error)
        controller.ready_to_close.connect(self.close)
        controller.publish_current()
        self.router.set_macro_ai_key_present(controller.openai_key_present)

    def _bind_api_credentials_controller(self) -> None:
        controller = self._api_credentials_controller
        if controller is None:
            return
        controller.provider_configuration_changed.connect(
            self._on_api_provider_configuration_changed
        )
        controller.error.connect(
            lambda provider_id, reason: self._on_connection_error(
                f"{provider_id}: {reason}"
            )
        )

    @QtCore.pyqtSlot(str)
    def _on_api_provider_configuration_changed(self, provider_id: str) -> None:
        controller = self._api_credentials_controller
        macro = self._macro_context_controller
        if controller is None or macro is None:
            return
        settings = self._config.api_providers.get(provider_id)
        enabled = settings is not None and settings.enabled
        if provider_id == "tavily":
            key = controller.manager.get_api_key("tavily") if enabled else None
            macro.set_tavily_provider(
                TavilyNewsProvider(TavilyNewsConfig(api_key=key))
                if key is not None
                else None
            )
            macro.set_tavily_extractor(
                TavilyExtractProvider(TavilyExtractConfig(api_key=key))
                if key is not None
                else None
            )
        if provider_id == "gdelt":
            macro.set_gdelt_provider(GdeltNewsProvider() if enabled else None)
        if provider_id == "openai":
            self.router.set_macro_ai_key_present(macro.openai_key_present)

    @QtCore.pyqtSlot(str)
    def _search_catalogue(self, query: str) -> None:
        if self._catalogue_controller is not None:
            self._catalogue_controller.search(query)

    @QtCore.pyqtSlot(object)
    def _on_runtime_connection_changed(self, connection: object) -> None:
        from trading_ig_assistant.app.runtime.ig_session_runtime import ActiveIGConnection

        environment = (
            connection.environment
            if isinstance(connection, ActiveIGConnection)
            else self._config.environment
        )
        account_id = (
            connection.current_account_id
            if isinstance(connection, ActiveIGConnection)
            else self._config.connection_profiles[environment].selected_account_id
        )
        self._activate_watchlist_context(environment, account_id)
        if self._scanner_session_controller is not None:
            self._scanner_session_controller.reset_context()
        self.router.set_chart_environment(environment.value.upper())
        if self._catalogue_controller is not None:
            self._catalogue_controller.load_cached_inventory(environment)
        if self._paper_session_controller is not None:
            self._paper_session_controller.publish_projection()
        if self._macro_context_controller is not None:
            self._macro_context_controller.publish_current()
        if self._market_stream_controller is not None:
            self._market_stream_controller.set_connection_ready(
                isinstance(connection, ActiveIGConnection)
            )

    @QtCore.pyqtSlot()
    def _disconnect_read_only(self) -> None:
        if self._market_stream_controller is not None:
            self._market_stream_controller.set_connection_ready(False)
        if self._paper_session_controller is not None:
            self._paper_session_controller.invalidate_market_quotes()
        if self._connection_controller is not None:
            self._connection_controller.disconnect()

    @QtCore.pyqtSlot(str)
    def _switch_read_only_account(self, account_id: str) -> None:
        if self._market_stream_controller is not None:
            self._market_stream_controller.set_connection_ready(False)
        if self._paper_session_controller is not None:
            self._paper_session_controller.invalidate_market_quotes()
        if self._connection_controller is not None:
            self._connection_controller.switch_account(account_id)

    def _build_layout(self) -> None:
        root = QtWidgets.QWidget()
        root.setObjectName("AppShell")
        root_layout = QtWidgets.QVBoxLayout(root)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(6)

        self.account_header = AccountHeader(self.language)
        root_layout.addWidget(self.account_header)
        self.macro_bar = MacroCompactBar(self.language)
        root_layout.addWidget(self.macro_bar)

        body = QtWidgets.QWidget()
        body_layout = QtWidgets.QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(6)
        self.sidebar = NavSidebar(
            self.language,
            collapsed=self._config.workspace.sidebar_collapsed,
        )
        self.stack = QtWidgets.QStackedWidget()
        self.router = PageRouter(
            self.stack,
            self.language,
            self._config,
            self._api_credentials_controller,
        )
        self.router.locale_requested.connect(self.set_locale)
        self.sidebar.page_selected.connect(self.router.open_page)
        self.router.page_changed.connect(self.sidebar.select_page)
        body_layout.addWidget(self.sidebar)
        body_layout.addWidget(self.stack, stretch=1)
        root_layout.addWidget(body, stretch=1)
        self.setCentralWidget(root)

    def set_locale(self, locale: str) -> None:
        self.language.set_locale(locale)

    def retranslate_ui(self) -> None:
        self.setWindowTitle(self.language.text("app.title"))
        self.sidebar.retranslate_ui()
        self.account_header.retranslate_ui()
        self.macro_bar.retranslate_ui()
        self.router.retranslate_ui()

    @QtCore.pyqtSlot(object)
    def _on_account_header(self, snapshot: object) -> None:
        from trading_ig_assistant.app.projections.account import AccountHeaderVM

        if isinstance(snapshot, AccountHeaderVM):
            self.account_header.set_snapshot(snapshot)

    @QtCore.pyqtSlot(object)
    def _on_dashboard(self, snapshot: object) -> None:
        from trading_ig_assistant.app.projections.dashboard import DashboardVM

        if isinstance(snapshot, DashboardVM):
            self.router.set_dashboard_snapshot(snapshot)

    @QtCore.pyqtSlot(object)
    def _on_catalogue(self, snapshot: object) -> None:
        from trading_ig_assistant.app.projections.catalogue import CatalogueVM

        if isinstance(snapshot, CatalogueVM):
            self.router.set_catalogue_snapshot(snapshot)
            if self._market_stream_controller is not None:
                self._market_stream_controller.sync_inventory(snapshot)

    @QtCore.pyqtSlot(object)
    def _on_market_quote(self, value: object) -> None:
        from trading_ig_assistant.domain.market_data import Quote

        if not isinstance(value, Quote):
            return
        followed = self._config.followed_epics_for(
            self._watchlist_environment,
            self._watchlist_account_id,
        )
        if value.epic not in followed:
            return
        update = self._quote_candle_fallback_service.update(
            value,
            observed_at_utc=datetime.now(UTC),
            environment=self._watchlist_environment.value,
            account_id=self._watchlist_account_id or "",
        )
        if update is not None:
            self.router.apply_chart_update(update)
            if self._scanner_session_controller is not None:
                self._scanner_session_controller.ingest_product_chart_update(update)

    @QtCore.pyqtSlot(object)
    def _on_followed_product_epics_changed(self, epics: object) -> None:
        normalized = self._config.set_followed_epics(
            self._watchlist_environment,
            self._watchlist_account_id,
            epics,
        )
        if self._market_stream_controller is not None:
            self._market_stream_controller.track_epics(normalized)
        if self._workspace_persistence and self._watchlist_account_id:
            try:
                save_config(self._config, self._config_path)
            except OSError as exc:
                LOGGER.warning("GUI V2 followed products could not be saved: %s", exc)

    def _activate_watchlist_context(
        self,
        environment: object,
        account_id: str | None,
    ) -> None:
        from trading_ig_assistant.app.config import IGEnvironment

        normalized_environment = (
            environment
            if isinstance(environment, IGEnvironment)
            else IGEnvironment(str(environment).lower())
        )
        self._watchlist_environment = normalized_environment
        self._watchlist_account_id = account_id
        epics = self._config.followed_epics_for(normalized_environment, account_id)
        self.router.set_followed_product_epics(epics)
        if self._market_stream_controller is not None:
            self._market_stream_controller.track_epics(epics)

    def _initial_watchlist_account_id(self) -> str | None:
        profile = self._config.connection_profiles.get(self._config.environment)
        if profile is not None and profile.selected_account_id:
            return profile.selected_account_id
        return self._config.selected_account_id

    @QtCore.pyqtSlot(object)
    def _on_scanner(self, snapshot: object) -> None:
        from trading_ig_assistant.app.projections.scanner import ScannerVM

        if isinstance(snapshot, ScannerVM):
            self.router.set_scanner_snapshot(snapshot)

    @QtCore.pyqtSlot(object)
    def _on_health(self, snapshot: object) -> None:
        if isinstance(snapshot, tuple):
            self.router.set_health_snapshot(snapshot)

    @QtCore.pyqtSlot(object)
    def _on_paper_history(self, snapshot: object) -> None:
        from trading_ig_assistant.app.projections.paper_history import PaperHistoryVM

        if isinstance(snapshot, PaperHistoryVM):
            self.router.set_paper_history_snapshot(snapshot)

    @QtCore.pyqtSlot(object)
    def _on_macro(self, snapshot: object) -> None:
        from trading_ig_assistant.app.projections.macro import MacroVM

        if isinstance(snapshot, MacroVM):
            self.router.set_macro_snapshot(snapshot)
            self.macro_bar.set_snapshot(snapshot)

    @QtCore.pyqtSlot(object)
    def _on_optimization(self, snapshot: object) -> None:
        from trading_ig_assistant.app.projections.optimization import OptimizationReviewVM

        if isinstance(snapshot, OptimizationReviewVM):
            self.router.set_optimization_snapshot(snapshot)

    @QtCore.pyqtSlot(str)
    def _on_connection_error(self, message: str) -> None:
        if self._paper_session_controller is not None:
            self._paper_session_controller.publish_projection()
        rendered = (
            self.language.text(message)
            if message.startswith(("connection.", "catalogue.", "stream.", "macro."))
            else message
        )
        self.statusBar().showMessage(rendered, 12000)

    @QtCore.pyqtSlot(str)
    def _on_paper_message(self, message: str) -> None:
        message_id, separator, detail = message.partition("|")
        rendered = self.language.text(message_id)
        if separator:
            rendered = rendered.format(detail=detail)
        self.statusBar().showMessage(rendered, 12000)

    @QtCore.pyqtSlot()
    def _confirm_paper_restore(self) -> None:
        controller = self._paper_session_controller
        if controller is None:
            return
        answer = QtWidgets.QMessageBox.question(
            self,
            self.language.text("paper.restore_title"),
            self.language.text("paper.restore_question"),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        controller.confirm_restore(answer == QtWidgets.QMessageBox.Yes)

    @QtCore.pyqtSlot(str)
    def _confirm_paper_close(self, position_id: str) -> None:
        controller = self._paper_session_controller
        if controller is None:
            return
        answer = QtWidgets.QMessageBox.question(
            self,
            self.language.text("paper.close_title"),
            self.language.text("paper.close_question").format(position_id=position_id),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        controller.confirm_close(position_id, answer == QtWidgets.QMessageBox.Yes)

    @QtCore.pyqtSlot(object)
    def _confirm_paper_submission(self, value: object) -> None:
        from trading_ig_assistant.services.paper_session import PaperTicketSubmission

        controller = self._paper_session_controller
        if controller is None or not isinstance(value, PaperTicketSubmission):
            self.router.show_paper_submission_cancelled()
            return
        ticket = value.ticket
        intent = ticket.intent
        question = self.language.text("paper.open_question").format(
            product=intent.product_id,
            underlying=intent.underlying_id,
            direction=intent.direction.value,
            quantity=intent.quantity,
            entry=ticket.entry_price,
            stop=intent.requested_stop,
            target=intent.requested_target or "N/A",
            knockout=intent.requested_ko or "N/A",
            loss=ticket.estimated_loss,
            costs=ticket.spread_cost + ticket.fee_estimate + ticket.slippage_estimate,
            currency=value.quote.currency,
            source=value.quote.provenance,
            timestamp=value.quote.observed_at_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
        )
        answer = QtWidgets.QMessageBox.question(
            self,
            self.language.text("paper.open_title"),
            question,
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        if answer != QtWidgets.QMessageBox.Yes:
            self.router.show_paper_submission_cancelled()
            return
        controller.submit(value)

    @QtCore.pyqtSlot()
    def _sync_paper_stream_scope(self) -> None:
        paper = self._paper_session_controller
        market = self._market_stream_controller
        if paper is None or market is None:
            return
        epics = tuple(
            dict.fromkeys(
                snapshot.position.product_id
                for snapshot in paper.session.position_snapshots()
            )
        )
        market.protect_epics(epics)

    def _restore_workspace_state(self) -> None:
        workspace = self._config.workspace
        geometry_restored = False
        if workspace.window_geometry:
            encoded = workspace.window_geometry.encode("ascii", errors="ignore")
            geometry_restored = self.restoreGeometry(QtCore.QByteArray.fromBase64(encoded))
        if (
            not geometry_restored
            and workspace.window_width is not None
            and workspace.window_height is not None
        ):
            self.resize(workspace.window_width, workspace.window_height)
        page = workspace.active_page
        self.router.open_page(page if page in PAGE_SPEC_BY_KEY else "dashboard")

    def _capture_workspace_state(self) -> WorkspaceState:
        previous = self._config.workspace
        return WorkspaceState(
            window_width=self.width(),
            window_height=self.height(),
            splitter_sizes=previous.splitter_sizes,
            layout_version=2,
            window_geometry=bytes(self.saveGeometry().toBase64()).decode("ascii"),
            active_page=self.router.current_key or "dashboard",
            active_subtabs=previous.active_subtabs,
            sidebar_collapsed=self.sidebar.collapsed,
            theme="dark",
            locale=self.language.locale,
        )

    def closeEvent(self, event: QtCore.QEvent) -> None:
        if self._market_stream_controller is not None:
            self._market_stream_controller.stop()
        if self._connection_controller is not None and not self._connection_controller.close():
            self.statusBar().showMessage(self.language.text("connection.closing"), 0)
            event.ignore()
            return
        if (
            self._macro_context_controller is not None
            and not self._macro_context_controller.close()
        ):
            self.statusBar().showMessage(self.language.text("connection.closing"), 0)
            event.ignore()
            return
        self._bridge.close()
        if self._workspace_persistence:
            self._config.workspace = self._capture_workspace_state()
            try:
                save_config(self._config, self._config_path)
            except OSError as exc:
                LOGGER.warning("GUI V2 workspace settings could not be saved: %s", exc)
        self.language.close()
        super().closeEvent(event)


def run_gui_v2() -> int:
    configure_logging()
    session_id = emit_session_banner()
    if session_id:
        LOGGER.debug("GUI V2 session banner emitted session_id=%s", session_id)
    application = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    config_path = default_config_path()
    config = load_config(config_path)
    api_credentials = ApiCredentialManager(
        KeyringApiKeyStore(),
        testers={
            "tavily": TavilyConnectionTester(),
            "gdelt": GdeltConnectionTester(),
            "fred": BoundedJsonConnectionTester(),
            "eia": BoundedJsonConnectionTester(),
            "openai": BoundedJsonConnectionTester(),
        },
    )
    for provider_id, default_enabled in (
        ("ig", True),
        ("gdelt", True),
        ("tavily", api_credentials.has_api_key("tavily")),
        ("openai", api_credentials.has_api_key("openai")),
    ):
        config.api_providers.setdefault(
            provider_id,
            ApiProviderConfig(enabled=default_enabled),
        )

    def enabled_api_key(provider_id: str) -> str:
        settings = config.api_providers.get(provider_id)
        if settings is None or not settings.enabled:
            return ""
        secret = api_credentials.get_api_key(provider_id)
        return secret.reveal() if secret is not None else ""

    api_credentials_controller = ApiCredentialsController(
        api_credentials,
        config,
        config_path,
    )
    runtime = TradingRuntime()
    facade = RuntimeUIFacade(runtime)
    connection_controller = ReadOnlyConnectionController(
        runtime=runtime,
        config=config,
        config_path=config_path,
        credential_store=build_default_credential_store(),
        api_key_reader=lambda: enabled_api_key("ig"),
    )
    catalogue_controller = CatalogueSearchController(runtime)
    catalogue_controller.load_cached_inventory(config.environment)
    priority_epics = tuple(
        dict.fromkeys(
            (
                *DEFAULT_PRIORITY_REFERENCE_EPICS,
                *(binding.reference_epic for binding in config.product_market_bindings),
            )
        )
    )
    market_stream_controller = CatalogueMarketStreamController(
        runtime,
        priority_epics=priority_epics,
        chart_epics=initial_ig_reference_epics(),
    )
    scanner_session_controller = ScannerSessionController(
        runtime,
        IGProductMarketBindingRegistry(config.product_market_bindings),
        config,
        reference_epics=initial_ig_reference_epics(),
        research_recorder=TechnicalResearchRecorder(
            SQLiteStore(default_paper_database_path())
        ),
    )
    paper_session_controller = PaperSessionController(
        runtime=runtime,
        database_path=default_paper_database_path(),
    )
    official_news_providers = (
        federal_reserve_monetary_news_provider(),
        ecb_press_news_provider(),
    )
    tavily_enabled = config.api_providers["tavily"].enabled
    tavily_api_key = (
        api_credentials.get_api_key("tavily") if tavily_enabled else None
    )
    intelligence_runtime = MarketIntelligenceRuntime(
        official_providers=official_news_providers,
        gdelt_provider=(
            GdeltNewsProvider() if config.api_providers["gdelt"].enabled else None
        ),
        tavily_provider=(
            TavilyNewsProvider(TavilyNewsConfig(api_key=tavily_api_key))
            if tavily_api_key is not None
            else None
        ),
        tavily_extractor=(
            TavilyExtractProvider(TavilyExtractConfig(api_key=tavily_api_key))
            if tavily_api_key is not None
            else None
        ),
        quota_manager=ResearchQuotaManager(
            JsonResearchQuotaStore(default_research_quota_path(config_path))
        ),
        freshness_policy=IntelligenceFreshnessPolicy(
            breaking_news=timedelta(
                hours=config.market_intelligence.breaking_news_hours
            ),
            macroeconomics=timedelta(
                hours=config.market_intelligence.macroeconomics_hours
            ),
            monetary_policy=timedelta(
                hours=config.market_intelligence.monetary_policy_hours
            ),
            geopolitics=timedelta(
                hours=config.market_intelligence.geopolitics_hours
            ),
        ),
    )
    macro_context_controller = MacroContextController(
        runtime=runtime,
        providers=official_news_providers,
        openai_key_reader=lambda: enabled_api_key("openai"),
        intelligence_runtime=intelligence_runtime,
        analysis_repository=MarketAIAnalysisRepository(
            SQLiteStore(default_paper_database_path())
        ),
    )
    ThemeManager().apply(application)
    window = MainWindowV2(
        config=config,
        config_path=config_path,
        facade=facade,
        connection_controller=connection_controller,
        catalogue_controller=catalogue_controller,
        market_stream_controller=market_stream_controller,
        scanner_session_controller=scanner_session_controller,
        paper_session_controller=paper_session_controller,
        macro_context_controller=macro_context_controller,
        api_credentials_controller=api_credentials_controller,
        workspace_persistence=True,
    )
    window.show()
    return application.exec()
