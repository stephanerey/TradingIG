"""Lazy, stable page routing without runtime recreation."""

from __future__ import annotations

from PyQt5 import QtCore, QtWidgets

from trading_ig_assistant.app.config import AppConfig
from trading_ig_assistant.app.projections.catalogue import CatalogueVM, ProductRowVM
from trading_ig_assistant.app.projections.dashboard import DashboardVM
from trading_ig_assistant.app.projections.health import HealthServiceVM
from trading_ig_assistant.app.projections.macro import MacroVM
from trading_ig_assistant.app.projections.optimization import OptimizationReviewVM
from trading_ig_assistant.app.projections.paper_history import PaperHistoryVM
from trading_ig_assistant.app.projections.scanner import ScannerVM
from trading_ig_assistant.app.qt_api_credentials_controller import ApiCredentialsController
from trading_ig_assistant.ui.i18n.language_manager import LanguageManager
from trading_ig_assistant.ui.pages.dashboard_page import DashboardPage
from trading_ig_assistant.ui.pages.diagnostics_page import DiagnosticsPage
from trading_ig_assistant.ui.pages.history_page import HistoryPage
from trading_ig_assistant.ui.pages.macro_page import MacroPage
from trading_ig_assistant.ui.pages.positions_page import PositionsPage
from trading_ig_assistant.ui.pages.scanner_page import ScannerPage
from trading_ig_assistant.ui.pages.settings_page import SettingsPage
from trading_ig_assistant.ui.pages.watchlist_page import WatchlistPage
from trading_ig_assistant.ui.shell.empty_page import EmptyPage
from trading_ig_assistant.ui.shell.page_specs import PAGE_SPEC_BY_KEY, PAGE_SPECS


class PageRouter(QtCore.QObject):
    page_changed = QtCore.pyqtSignal(str)
    catalogue_search_requested = QtCore.pyqtSignal(str)
    catalogue_product_details_requested = QtCore.pyqtSignal(object)
    catalogue_stream_scope_changed = QtCore.pyqtSignal(object, int)
    followed_product_epics_changed = QtCore.pyqtSignal(object)
    locale_requested = QtCore.pyqtSignal(str)
    paper_save_requested = QtCore.pyqtSignal()
    paper_restore_requested = QtCore.pyqtSignal()
    paper_stop_requested = QtCore.pyqtSignal(str, str)
    paper_close_requested = QtCore.pyqtSignal(str)
    paper_submission_requested = QtCore.pyqtSignal(object)
    macro_news_refresh_requested = QtCore.pyqtSignal()
    macro_ai_analysis_requested = QtCore.pyqtSignal(str, int, str)

    def __init__(
        self,
        stack: QtWidgets.QStackedWidget,
        language: LanguageManager,
        config: AppConfig | None = None,
        api_credentials_controller: ApiCredentialsController | None = None,
    ) -> None:
        super().__init__(stack)
        self._stack = stack
        self._language = language
        self._config = config or AppConfig()
        self._api_credentials_controller = api_credentials_controller
        self._pages: dict[str, QtWidgets.QWidget] = {}
        self._current_key = ""
        self._dashboard_snapshot: DashboardVM | None = None
        self._catalogue_snapshot: CatalogueVM | None = None
        self._scanner_snapshot: ScannerVM | None = None
        self._health_snapshot: tuple[HealthServiceVM, ...] = ()
        self._paper_history_snapshot: PaperHistoryVM | None = None
        self._macro_snapshot: MacroVM | None = None
        self._optimization_snapshot: OptimizationReviewVM | None = None
        self._macro_ai_key_present = False
        self._stream_state = "disconnected"
        self._stream_subscribed = 0
        self._stream_total = 0
        self._stream_priority = 0
        self._chart_environment = self._config.environment.value.upper()
        self._followed_product_epics: tuple[str, ...] = ()

    @property
    def current_key(self) -> str:
        return self._current_key

    def open_page(self, key: str) -> None:
        if key not in PAGE_SPEC_BY_KEY:
            key = PAGE_SPECS[0].key
        page = self._pages.get(key)
        if page is None:
            if key == "dashboard":
                dashboard = DashboardPage(self._language)
                if self._dashboard_snapshot is not None:
                    dashboard.set_snapshot(self._dashboard_snapshot)
                if self._optimization_snapshot is not None:
                    dashboard.set_optimization(self._optimization_snapshot)
                page = dashboard
            elif key == "scanner":
                scanner = ScannerPage(self._language)
                scanner.search_requested.connect(self.catalogue_search_requested)
                scanner.stream_scope_changed.connect(self.catalogue_stream_scope_changed)
                scanner.market_open_requested.connect(self._open_watchlist_market)
                scanner.product_open_requested.connect(self._open_watchlist_product)
                scanner.set_stream_coverage(
                    self._stream_state,
                    self._stream_subscribed,
                    self._stream_total,
                    self._stream_priority,
                )
                if self._catalogue_snapshot is not None:
                    scanner.set_snapshot(self._catalogue_snapshot)
                if self._scanner_snapshot is not None:
                    scanner.set_scanner_snapshot(self._scanner_snapshot)
                page = scanner
            elif key == "watchlist":
                watchlist = WatchlistPage(
                    self._language,
                    self._chart_environment,
                    self._config.product_market_bindings,
                )
                watchlist.paper_submission_requested.connect(self.paper_submission_requested)
                watchlist.macro_open_requested.connect(lambda: self.open_page("macro"))
                watchlist.product_remove_requested.connect(
                    self._remove_followed_product
                )
                if self._scanner_snapshot is not None:
                    watchlist.set_scanner_snapshot(self._scanner_snapshot)
                if self._catalogue_snapshot is not None:
                    watchlist.set_catalogue_snapshot(self._catalogue_snapshot)
                if self._macro_snapshot is not None:
                    watchlist.set_macro_snapshot(self._macro_snapshot)
                watchlist.set_tracked_products(self._resolved_followed_products())
                page = watchlist
            elif key == "positions":
                positions = PositionsPage(self._language)
                positions.paper_save_requested.connect(self.paper_save_requested)
                positions.paper_restore_requested.connect(self.paper_restore_requested)
                positions.paper_stop_requested.connect(self.paper_stop_requested)
                positions.paper_close_requested.connect(self.paper_close_requested)
                if self._dashboard_snapshot is not None:
                    positions.set_snapshot(self._dashboard_snapshot)
                page = positions
            elif key == "diagnostics":
                diagnostics = DiagnosticsPage(self._language)
                diagnostics.set_health(self._health_snapshot)
                page = diagnostics
            elif key == "history":
                history = HistoryPage(self._language)
                if self._dashboard_snapshot is not None:
                    history.set_snapshot(self._dashboard_snapshot)
                if self._paper_history_snapshot is not None:
                    history.set_paper_history(self._paper_history_snapshot)
                if self._optimization_snapshot is not None:
                    history.set_optimization(self._optimization_snapshot)
                page = history
            elif key == "macro":
                macro = MacroPage(self._language)
                macro.news_refresh_requested.connect(self.macro_news_refresh_requested)
                macro.ai_analysis_requested.connect(self.macro_ai_analysis_requested)
                if self._macro_snapshot is not None:
                    macro.set_snapshot(self._macro_snapshot)
                macro.set_ai_key_present(self._macro_ai_key_present)
                page = macro
            elif key == "settings":
                settings = SettingsPage(
                    self._language,
                    self._config,
                    self._api_credentials_controller,
                )
                settings.locale_requested.connect(self.locale_requested)
                page = settings
            else:
                page = EmptyPage(PAGE_SPEC_BY_KEY[key], self._language)
            self._pages[key] = page
            self._stack.addWidget(page)
        self._stack.setCurrentWidget(page)
        scanner_page = self._pages.get("scanner")
        if isinstance(scanner_page, ScannerPage):
            scanner_page.set_stream_scope_active(key == "scanner")
        if key != self._current_key:
            self._current_key = key
            self.page_changed.emit(key)

    def set_dashboard_snapshot(self, snapshot: DashboardVM) -> None:
        self._dashboard_snapshot = snapshot
        page = self._pages.get("dashboard")
        if isinstance(page, DashboardPage):
            page.set_snapshot(snapshot)
        positions = self._pages.get("positions")
        if isinstance(positions, PositionsPage):
            positions.set_snapshot(snapshot)
        history = self._pages.get("history")
        if isinstance(history, HistoryPage):
            history.set_snapshot(snapshot)

    def set_catalogue_snapshot(self, snapshot: CatalogueVM) -> None:
        self._catalogue_snapshot = snapshot
        page = self._pages.get("scanner")
        if isinstance(page, ScannerPage):
            page.set_snapshot(snapshot)
        watchlist = self._pages.get("watchlist")
        if isinstance(watchlist, WatchlistPage):
            watchlist.set_catalogue_snapshot(snapshot)
            watchlist.set_tracked_products(self._resolved_followed_products())

    def set_followed_product_epics(self, epics: object) -> None:
        self._followed_product_epics = tuple(
            dict.fromkeys(
                text
                for epic in epics
                if (text := str(epic).strip())
            )
        )
        page = self._pages.get("watchlist")
        if isinstance(page, WatchlistPage):
            page.set_tracked_products(self._resolved_followed_products())

    def set_scanner_snapshot(self, snapshot: ScannerVM) -> None:
        self._scanner_snapshot = snapshot
        page = self._pages.get("scanner")
        if isinstance(page, ScannerPage):
            page.set_scanner_snapshot(snapshot)
        watchlist = self._pages.get("watchlist")
        if isinstance(watchlist, WatchlistPage):
            watchlist.set_scanner_snapshot(snapshot)

    def apply_chart_update(self, value: object) -> None:
        from trading_ig_assistant.domain.market_data import ChartCandleUpdate

        if not isinstance(value, ChartCandleUpdate):
            return
        page = self._pages.get("watchlist")
        if isinstance(page, WatchlistPage):
            page.apply_chart_update(value)

    def set_chart_environment(self, environment: str) -> None:
        self._chart_environment = environment.strip().upper() or "INCONNU"
        page = self._pages.get("watchlist")
        if isinstance(page, WatchlistPage):
            page.set_environment(self._chart_environment)

    def set_health_snapshot(self, snapshots: tuple[HealthServiceVM, ...]) -> None:
        self._health_snapshot = snapshots
        page = self._pages.get("diagnostics")
        if isinstance(page, DiagnosticsPage):
            page.set_health(snapshots)

    def set_paper_history_snapshot(self, snapshot: PaperHistoryVM) -> None:
        self._paper_history_snapshot = snapshot
        page = self._pages.get("history")
        if isinstance(page, HistoryPage):
            page.set_paper_history(snapshot)

    def set_macro_snapshot(self, snapshot: MacroVM) -> None:
        self._macro_snapshot = snapshot
        page = self._pages.get("macro")
        if isinstance(page, MacroPage):
            page.set_snapshot(snapshot)
        watchlist = self._pages.get("watchlist")
        if isinstance(watchlist, WatchlistPage):
            watchlist.set_macro_snapshot(snapshot)

    def set_optimization_snapshot(self, snapshot: OptimizationReviewVM) -> None:
        self._optimization_snapshot = snapshot
        dashboard = self._pages.get("dashboard")
        if isinstance(dashboard, DashboardPage):
            dashboard.set_optimization(snapshot)
        history = self._pages.get("history")
        if isinstance(history, HistoryPage):
            history.set_optimization(snapshot)

    def set_macro_busy(self, busy: bool) -> None:
        page = self._pages.get("macro")
        if isinstance(page, MacroPage):
            page.set_news_busy(busy)

    def set_macro_ai_key_present(self, present: bool) -> None:
        self._macro_ai_key_present = present
        page = self._pages.get("macro")
        if isinstance(page, MacroPage):
            page.set_ai_key_present(present)

    def set_macro_ai_busy(self, busy: bool) -> None:
        page = self._pages.get("macro")
        if isinstance(page, MacroPage):
            page.set_ai_busy(busy)

    def set_macro_ai_error(self, reason: str) -> None:
        page = self._pages.get("macro")
        if isinstance(page, MacroPage):
            page.set_ai_error(reason)

    def show_paper_submission_result(self, record: object) -> None:
        page = self._pages.get("watchlist")
        if isinstance(page, WatchlistPage):
            page.show_paper_submission_result(record)

    def show_paper_submission_cancelled(self) -> None:
        page = self._pages.get("watchlist")
        if isinstance(page, WatchlistPage):
            page.show_paper_submission_cancelled()

    @QtCore.pyqtSlot(str)
    def _open_watchlist_market(self, epic: str) -> None:
        self.open_page("watchlist")
        page = self._pages.get("watchlist")
        if isinstance(page, WatchlistPage):
            page.select_reference_epic(epic)

    @QtCore.pyqtSlot(object)
    def _open_watchlist_product(self, value: object) -> None:
        if not isinstance(value, ProductRowVM):
            return
        binding = next(
            (
                item
                for item in self._config.product_market_bindings
                if item.product_epic == value.epic
            ),
            None,
        )
        if self._catalogue_snapshot is None:
            if binding is not None:
                self.catalogue_product_details_requested.emit(value)
            return
        if not any(
            row.epic == value.epic for row in self._catalogue_snapshot.rows
        ):
            return
        if value.epic not in self._followed_product_epics:
            self._followed_product_epics = (*self._followed_product_epics, value.epic)
            self.followed_product_epics_changed.emit(self._followed_product_epics)
        self.open_page("watchlist")
        page = self._pages.get("watchlist")
        if isinstance(page, WatchlistPage):
            page.set_tracked_products(self._resolved_followed_products())
            page.select_reference_epic(value.epic)
        if binding is not None:
            self.catalogue_product_details_requested.emit(value)

    @QtCore.pyqtSlot(str)
    def _remove_followed_product(self, epic: str) -> None:
        normalized = epic.strip()
        if normalized not in self._followed_product_epics:
            return
        self._followed_product_epics = tuple(
            item for item in self._followed_product_epics if item != normalized
        )
        page = self._pages.get("watchlist")
        if isinstance(page, WatchlistPage):
            page.set_tracked_products(self._resolved_followed_products())
        self.followed_product_epics_changed.emit(self._followed_product_epics)

    def _resolved_followed_products(self) -> tuple[ProductRowVM, ...]:
        snapshot = self._catalogue_snapshot
        if snapshot is None:
            return ()
        by_epic = {row.epic: row for row in snapshot.rows}
        return tuple(
            by_epic[epic]
            for epic in self._followed_product_epics
            if epic in by_epic
        )

    def set_catalogue_busy(self, busy: bool) -> None:
        page = self._pages.get("scanner")
        if isinstance(page, ScannerPage):
            page.set_busy(busy)

    def set_catalogue_stream_coverage(
        self,
        state: str,
        subscribed: int,
        total: int,
        priority: int,
    ) -> None:
        self._stream_state = state
        self._stream_subscribed = subscribed
        self._stream_total = total
        self._stream_priority = priority
        page = self._pages.get("scanner")
        if isinstance(page, ScannerPage):
            page.set_stream_coverage(state, subscribed, total, priority)

    def retranslate_ui(self) -> None:
        for page in self._pages.values():
            retranslate = getattr(page, "retranslate_ui", None)
            if callable(retranslate):
                retranslate()
