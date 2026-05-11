"""Minimal GUI shell for P01."""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from pathlib import Path

from PyQt5 import QtCore, QtWidgets

from trading_ig_assistant.adapters.credentials import build_default_credential_store
from trading_ig_assistant.adapters.ig_rest import (
    IGAPIError,
    IGRestAdapter,
    is_invalid_security_token_error,
)
from trading_ig_assistant.adapters.ig_streaming import IGStreamingAdapter
from trading_ig_assistant.app.config import (
    AppConfig,
    IGConnectionProfileConfig,
    IGEnvironment,
    default_config_path,
    load_config,
    save_config,
)
from trading_ig_assistant.app.streaming_bridge import StreamingEventBridge
from trading_ig_assistant.domain.instruments import Account
from trading_ig_assistant.domain.market_data import ChartCandleUpdate, PriceSeries, Quote
from trading_ig_assistant.domain.products import ProductType, TradableProduct
from trading_ig_assistant.services.ig_connection_service import IGConnectionRequest
from trading_ig_assistant.services.product_discovery_service import (
    ProductDiscoveryResult,
    ProductDiscoveryService,
    read_discovery_report,
    write_discovery_report,
)
from trading_ig_assistant.ui.about_dialog import AboutDialog
from trading_ig_assistant.ui.account_status_widget import AccountStatusRibbonWidget
from trading_ig_assistant.ui.chart_view import ChartView
from trading_ig_assistant.ui.log_view_dialog import LogViewDialog
from trading_ig_assistant.ui.macro_ribbon_widget import MacroRibbonWidget
from trading_ig_assistant.ui.product_selector import ProductSelectorWidget
from trading_ig_assistant.ui.settings_dialog import SettingsDialog
from trading_ig_assistant.utils.logging_config import configure_logging, emit_session_banner
from trading_ig_assistant.utils.redaction import mask_identifier

LOGGER = logging.getLogger(__name__)
PRICE_HISTORY_POINTS = 240
PRODUCT_STREAM_ITEMS_LIMIT = 20


@dataclass
class ActiveIGConnection:
    environment: IGEnvironment
    current_account_id: str | None
    accounts: list[Account]
    adapter: IGRestAdapter


class ConnectionWorker(QtCore.QObject):
    succeeded = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()

    def __init__(self, request: IGConnectionRequest) -> None:
        super().__init__()
        self._request = request

    @QtCore.pyqtSlot()
    def run(self) -> None:
        LOGGER.debug("Connection worker start environment=%s", self._request.environment.value)
        adapter = IGRestAdapter(environment=self._request.environment, read_only=True)
        try:
            credentials = _credentials_from_request(self._request)
            session = adapter.login(credentials)
            accounts = adapter.get_accounts()
            if self._request.selected_account_id and _account_id_exists(
                accounts,
                self._request.selected_account_id,
            ):
                session = adapter.switch_account(self._request.selected_account_id)
            result = ActiveIGConnection(
                environment=self._request.environment,
                current_account_id=session.current_account_id,
                accounts=accounts,
                adapter=adapter,
            )
            LOGGER.debug(
                "Connection worker success environment=%s accounts=%s",
                result.environment.value,
                len(result.accounts),
            )
            self.succeeded.emit(result)
        except Exception as exc:
            try:
                adapter.logout()
            except IGAPIError:
                pass
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
    ) -> None:
        super().__init__()
        self._adapter = adapter
        self._environment = environment

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
            results = [service.discover_all_products(max_details=0)]
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
    failed = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()

    def __init__(self, adapter: IGRestAdapter, epic: str) -> None:
        super().__init__()
        self._adapter = adapter
        self._epic = epic

    @QtCore.pyqtSlot()
    def run(self) -> None:
        try:
            LOGGER.debug("Price history worker start epic=%s", self._epic)
            series = self._adapter.get_prices(
                self._epic,
                resolution="MINUTE",
                max_points=PRICE_HISTORY_POINTS,
            )
            LOGGER.debug(
                "Price history worker success epic=%s points=%s",
                self._epic,
                len(series.prices),
            )
            self.succeeded.emit(series)
        except Exception as exc:
            LOGGER.debug("Price history worker failed epic=%s error=%s", self._epic, exc)
            self.failed.emit(str(exc))
        finally:
            LOGGER.debug("Price history worker finished epic=%s", self._epic)
            self.finished.emit()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        LOGGER.debug("MainWindow initialization start")
        self.setWindowTitle("Trading IG Assistant - P01 read-only shell")
        self.resize(1280, 820)
        self._config_path = default_config_path()
        self._config = load_config(self._config_path)
        self._credential_store = self._build_credential_store()
        self._active_connection: ActiveIGConnection | None = None
        self._connection_thread: QtCore.QThread | None = None
        self._connection_worker: ConnectionWorker | None = None
        self._discovery_thread: QtCore.QThread | None = None
        self._discovery_worker: ProductDiscoveryWorker | None = None
        self._price_history_thread: QtCore.QThread | None = None
        self._price_history_worker: PriceHistoryWorker | None = None
        self._price_history_cache: dict[str, PriceSeries] = {}
        self._price_history_blocked_epics: set[str] = set()
        self._api_allowance_exceeded = False
        self._auth_locked_out = False
        self._selected_product: TradableProduct | None = None
        self._chart_product: TradableProduct | None = None
        self._visible_price_epics: list[str] = []
        self._loaded_cache_environment: IGEnvironment | None = None
        self._streaming_adapter: IGStreamingAdapter | None = None
        self._streaming_bridge = StreamingEventBridge()
        self._build_menu()
        self._build_layout()
        self._streaming_bridge.quote_received.connect(self._on_stream_quote)
        self._streaming_bridge.chart_received.connect(self._on_stream_chart)
        self._streaming_bridge.status_changed.connect(self._on_stream_status)
        self._streaming_bridge.error_received.connect(self._on_stream_error)
        self._load_cached_discovery_results()
        LOGGER.debug("MainWindow initialization complete")

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        quit_action = file_menu.addAction("Quit")
        quit_action.triggered.connect(self.close)

        tools_menu = self.menuBar().addMenu("&Tools")
        settings_action = tools_menu.addAction("Settings")
        settings_action.triggered.connect(self._open_settings)
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

        self.account_status = AccountStatusRibbonWidget()
        self.account_status.connect_requested.connect(self._connect_environment)
        self.account_status.disconnect_requested.connect(self._disconnect)
        self.account_status.settings_requested.connect(self._open_settings)
        self.account_status.account_selected.connect(self._select_account)
        root_layout.addWidget(self.account_status)
        root_layout.addWidget(MacroRibbonWidget())

        body = QtWidgets.QSplitter()
        body.setOrientation(QtCore.Qt.Horizontal)
        self.chart_view = ChartView()
        body.addWidget(self.chart_view)

        right_tabs = QtWidgets.QTabWidget()
        self.product_selector = ProductSelectorWidget()
        self.product_selector.discover_requested.connect(self._discover_products)
        self.product_selector.export_requested.connect(self._export_discovery_report)
        self.product_selector.product_selected.connect(self._on_product_selected)
        self.product_selector.visible_epics_changed.connect(self._on_visible_epics_changed)
        right_tabs.addTab(self.product_selector, "Products / Ticket")
        right_tabs.setMinimumWidth(760)
        body.addWidget(right_tabs)
        body.setStretchFactor(0, 1)
        body.setStretchFactor(1, 3)

        root_layout.addWidget(body, stretch=1)
        self.setCentralWidget(root)

    @staticmethod
    def _build_credential_store() -> object | None:
        return build_default_credential_store()

    @QtCore.pyqtSlot()
    def _open_settings(self) -> None:
        LOGGER.debug("Settings dialog open")
        dialog = SettingsDialog(self._config, self._credential_store, self)
        dialog.config_applied.connect(self._apply_config)
        dialog.exec()

    @QtCore.pyqtSlot(object)
    def _apply_config(self, config: AppConfig) -> None:
        LOGGER.debug("Settings applied environment=%s", config.environment.value)
        self._config = config
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
    def _disconnect(self) -> None:
        LOGGER.debug("Disconnect requested")
        if self._connection_thread is not None:
            self.statusBar().showMessage("Connection is busy; wait before disconnecting.", 5000)
            return
        if self._discovery_thread is not None:
            self.statusBar().showMessage("Discovery is running; wait before disconnecting.", 5000)
            return
        self._stop_streaming()
        self._logout_active_connection()
        self.account_status.set_disconnected()
        self.product_selector.set_selected_product(None)
        self.chart_view.set_stream_status("DISCONNECTED")
        self.chart_view.set_live_quote(None)
        self.statusBar().showMessage("Disconnected from IG.", 5000)

    @QtCore.pyqtSlot(object)
    def _connect_read_only(self, request: IGConnectionRequest) -> None:
        LOGGER.debug("Connect read-only start environment=%s", request.environment.value)
        if self._connection_thread is not None:
            LOGGER.debug("Connect read-only ignored because worker is already running")
            return
        if self._active_connection is not None:
            self._logout_active_connection()
        self.statusBar().showMessage(
            f"Connecting to IG {request.environment.value} in read-only mode...",
            0,
        )
        self._connection_thread = QtCore.QThread(self)
        self._connection_worker = ConnectionWorker(request)
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
        self._auth_locked_out = False
        self._api_allowance_exceeded = False
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
        self._set_profile_account(result.environment, selected_account_id)
        if self._loaded_cache_environment != result.environment:
            self._load_cached_discovery_results()
        if self._selected_product is not None:
            self._refresh_selected_product_after_connection()
        else:
            self.chart_view.set_stream_status("STREAM READY")
            self._restart_streaming()
        message = (
            f"Connected to IG {result.environment.value}. "
            f"Accounts fetched: {len(result.accounts)}."
        )
        self.statusBar().showMessage(
            message,
            7000,
        )

    @QtCore.pyqtSlot(str)
    def _on_connection_failure(self, message: str) -> None:
        LOGGER.debug("Connection failure message=%s", message)
        if "too-many-failed-attempts" in message:
            self._auth_locked_out = True
            self.account_status.set_auth_locked(
                "IG authentication locked: too many failed attempts. "
                "Wait before trying again."
            )
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
        if selected_account_id and self._switch_active_account(selected_account_id):
            self._restart_streaming()
        self._set_profile_account(self._config.environment, selected_account_id)

    def _switch_active_account(self, account_id: str) -> bool:
        if self._active_connection is None:
            return False
        if self._active_connection.current_account_id == account_id:
            return True
        try:
            session = self._active_connection.adapter.switch_account(account_id)
            self._active_connection.current_account_id = session.current_account_id
            LOGGER.debug("Active IG account switched account=%s", mask_identifier(account_id))
            return True
        except IGAPIError as exc:
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
            self._active_connection.adapter.logout()
        except IGAPIError as exc:
            LOGGER.debug("Active IG logout failed ignored error=%s", exc)
        self._active_connection = None
        LOGGER.debug("Active IG logout complete")

    @QtCore.pyqtSlot(object)
    def _on_product_selected(self, product: object) -> None:
        if not isinstance(product, TradableProduct):
            return
        self._selected_product = product
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

    @QtCore.pyqtSlot(object)
    def _on_stream_quote(self, quote: object) -> None:
        if isinstance(quote, Quote):
            self.product_selector.set_live_quote(quote)
            self.chart_view.set_live_quote(quote)

    @QtCore.pyqtSlot(object)
    def _on_stream_chart(self, chart_update: object) -> None:
        if isinstance(chart_update, ChartCandleUpdate):
            self.chart_view.apply_chart_update(chart_update)
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
        self.chart_view.set_stream_status(status)
        LOGGER.debug("Streaming status update status=%s", status)

    @QtCore.pyqtSlot(str)
    def _on_stream_error(self, message: str) -> None:
        LOGGER.debug("Streaming error message=%s", message)
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
            adapter = IGStreamingAdapter(
                session=session,
                account_id=self._active_connection.current_account_id,
                event_sink=self._streaming_bridge,
            )
            self.chart_view.set_stream_status("CONNECTING")
            adapter.start()
            price_epics = list(dict.fromkeys([*self._visible_price_epics, stream_product.epic]))
            adapter.subscribe_markets(price_epics[:PRODUCT_STREAM_ITEMS_LIMIT])
            adapter.subscribe_chart(stream_product.epic, "1MINUTE")
            self._streaming_adapter = adapter
            LOGGER.debug(
                "Streaming restarted selected_epic=%s source_epic=%s visible_prices=%s account=%s",
                self._selected_product.epic,
                stream_product.epic,
                len(price_epics[:PRODUCT_STREAM_ITEMS_LIMIT]),
                mask_identifier(self._active_connection.current_account_id),
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

    def _load_selected_product_history(self) -> None:
        if self._active_connection is None:
            return
        product = self._chart_product or self._selected_product
        if product is None:
            return
        try:
            cache_key = product.epic
            if self._api_allowance_exceeded:
                LOGGER.debug(
                    "Price history skipped epic=%s due to global allowance block",
                    cache_key,
                )
                return
            if cache_key in self._price_history_blocked_epics:
                LOGGER.debug(
                    "Price history skipped epic=%s due to cached allowance block",
                    cache_key,
                )
                return
            cached_series = self._price_history_cache.get(cache_key)
            if cached_series is not None:
                series = cached_series
            else:
                series = self._active_connection.adapter.get_prices(
                    product.epic,
                    resolution="MINUTE",
                    max_points=PRICE_HISTORY_POINTS,
                )
                self._price_history_cache[cache_key] = series
            anchor_price = _product_anchor_price(product)
            self.chart_view.set_price_series(series, anchor_price=anchor_price)
            LOGGER.debug(
                "Price history loaded epic=%s points=%s",
                product.epic,
                len(series.prices),
            )
        except Exception as exc:
            if _is_api_allowance_exceeded(exc):
                self._price_history_blocked_epics.add(product.epic)
                self._mark_api_allowance_exceeded()
            LOGGER.debug(
                "Price history load failed epic=%s error=%s",
                product.epic,
                exc,
            )
            self.statusBar().showMessage(
                f"Price history unavailable: {humanize_ig_error(str(exc))}",
                10000,
            )

    @QtCore.pyqtSlot()
    def _reload_selected_product_history(self) -> None:
        self._load_selected_product_history()

    def _stop_streaming(self) -> None:
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
        self._chart_product = _resolve_chart_source_product(
            product,
            self.product_selector.results(),
            self._active_connection.adapter
            if self._active_connection is not None and not self._api_allowance_exceeded
            else None,
        )
        LOGGER.debug(
            "Selected product state applied selected_epic=%s source_epic=%s",
            product.epic,
            (self._chart_product or product).epic,
        )
        self.product_selector.set_selected_product(product)
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
    window = MainWindow()
    window.show()
    try:
        return app.exec()
    finally:
        logging.getLogger("trading_ig_assistant.session").info("=" * 86)
        logging.getLogger("trading_ig_assistant.session").info("TradingIG session end")
        logging.getLogger("trading_ig_assistant.session").info("=" * 86)


def _credentials_from_request(request: IGConnectionRequest):
    from trading_ig_assistant.adapters.credentials import IGCredentials

    return IGCredentials(
        username=request.username,
        password=request.password,
        api_key=request.api_key,
    )


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


def _account_id_exists(accounts: list[Account], account_id: str) -> bool:
    return any(account.account_id == account_id for account in accounts)


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


def _discovery_cache_path(environment: IGEnvironment) -> Path:
    return Path.home() / ".trading_ig_assistant" / f"product_discovery_{environment.value}.json"


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


def _resolve_chart_source_product(
    selected_product: TradableProduct,
    results: list[ProductDiscoveryResult],
    adapter: IGRestAdapter | None = None,
) -> TradableProduct:
    if selected_product.product_type == ProductType.CASH_OR_DFB:
        return selected_product

    candidates: list[TradableProduct] = []
    for result in results:
        candidates.extend(result.products)

    resolved = _resolve_chart_source_from_candidates(selected_product, candidates)
    if resolved.epic != selected_product.epic:
        return resolved

    if adapter is None:
        return selected_product

    try:
        search_term = _normalize_chart_base_name(selected_product.name)
        service = ProductDiscoveryService(adapter)
        live_candidates = [
            service.classify_product(summary, details=None)
            for summary in adapter.search_markets(search_term)
        ]
        resolved = _resolve_chart_source_from_candidates(selected_product, live_candidates)
        if resolved.epic != selected_product.epic:
            LOGGER.debug(
                "Chart source resolved via targeted search selected_epic=%s source_epic=%s",
                selected_product.epic,
                resolved.epic,
            )
            return resolved
    except Exception as exc:
        LOGGER.debug(
            "Chart source targeted search failed selected_epic=%s error=%s",
            selected_product.epic,
            exc,
        )

    return selected_product


def _resolve_chart_source_from_candidates(
    selected_product: TradableProduct,
    candidates: list[TradableProduct],
) -> TradableProduct:
    target_name = _normalize_chart_base_name(selected_product.name)

    exact_matches = [
        product
        for product in candidates
        if _normalize_chart_base_name(product.name) == target_name
        and product.epic != selected_product.epic
        and product.product_type == ProductType.CASH_OR_DFB
    ]
    if exact_matches:
        return exact_matches[0]

    fallback_matches = [
        product
        for product in candidates
        if product.epic != selected_product.epic
        and _normalize_chart_base_name(product.name).startswith(target_name)
        and product.product_type == ProductType.CASH_OR_DFB
    ]
    if fallback_matches:
        return fallback_matches[0]

    return selected_product


def _normalize_chart_base_name(name: str) -> str:
    text = " ".join(str(name).split()).strip()
    replacements = [
        " Barrières Achat",
        " Barrières Vente",
        " Barrier Call",
        " Barrier Put",
        " Barrière Achat",
        " Barrière Vente",
        " Call",
        " Put",
    ]
    for replacement in replacements:
        if text.endswith(replacement):
            text = text[: -len(replacement)]
    text = text.replace("(S1)", "").replace("(E1)", "").strip()
    return text.lower()


def _optional_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None
