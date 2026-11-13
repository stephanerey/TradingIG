"""Read-only GUI V2 watchlist backed by reference-market session streams."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

from PyQt5 import QtCore, QtWidgets

from trading_ig_assistant.app.projections.catalogue import CatalogueVM, ProductRowVM
from trading_ig_assistant.app.projections.common import Availability
from trading_ig_assistant.app.projections.macro import MacroVM
from trading_ig_assistant.app.projections.paper_ticket import build_paper_ticket_preparation
from trading_ig_assistant.app.projections.scanner import (
    ScannerIndicatorVM,
    ScannerMarketRowVM,
    ScannerSignalVM,
    ScannerVM,
)
from trading_ig_assistant.domain.analysis import (
    AnalysisCandle,
    DataState,
    IndicatorInput,
    IndicatorSeriesPoint,
)
from trading_ig_assistant.domain.market_data import (
    ChartCandleUpdate,
    ChartPriceBasis,
    Quote,
)
from trading_ig_assistant.domain.market_navigation import IGProductMarketBinding
from trading_ig_assistant.domain.products import (
    AssetClass,
    ProductDirection,
    ProductType,
    TradableProduct,
)
from trading_ig_assistant.services.candle_aggregation_service import chart_update_ohlc
from trading_ig_assistant.services.indicator_service import (
    atr_series,
    ema_series,
    macd_series,
    rsi_series,
)
from trading_ig_assistant.ui.chart_view import (
    ChartIndicatorPanel,
    ChartOverlayLevel,
    ChartOverlaySeries,
    ChartView,
)
from trading_ig_assistant.ui.i18n.language_manager import LanguageManager
from trading_ig_assistant.ui.pages.paper_ticket_preparation import (
    PaperTicketPreparationWidget,
)
from trading_ig_assistant.ui.shell.page_specs import PAGE_SPEC_BY_KEY


class WatchlistPage(QtWidgets.QWidget):
    paper_submission_requested = QtCore.pyqtSignal(object)
    macro_open_requested = QtCore.pyqtSignal()
    product_remove_requested = QtCore.pyqtSignal(str)

    def __init__(
        self,
        language: LanguageManager,
        environment: str = "DEMO",
        product_market_bindings: tuple[IGProductMarketBinding, ...] = (),
    ) -> None:
        super().__init__()
        self._language = language
        self._snapshot: ScannerVM | None = None
        self._macro_snapshot: MacroVM | None = None
        self._selected_epic: str | None = None
        self._selected_product: ProductRowVM | None = None
        self._selected_product_binding: IGProductMarketBinding | None = None
        self._product_market_bindings = {
            binding.product_epic: binding for binding in product_market_bindings
        }
        self._tracked_products: dict[str, ProductRowVM] = {}
        self._managed_watchlist = False
        self._environment = environment.strip().upper() or "INCONNU"
        self._chart_updates: dict[str, list[ChartCandleUpdate]] = {}
        self._pending_chart_update: ChartCandleUpdate | None = None
        self._analysis_signature: tuple[object, ...] | None = None
        self._current_signal_rows: tuple[ScannerSignalVM, ...] = ()
        self._selected_signal: ScannerSignalVM | None = None
        self._selected_strategy_by_epic: dict[str, str] = {}
        self._indicator_panel_by_signal_key: dict[tuple[str, str], str] = {}
        self._overlay_availability_signature: tuple[object, ...] | None = None
        self._chart_flush_timer = QtCore.QTimer(self)
        self._chart_flush_timer.setSingleShot(True)
        self._chart_flush_timer.setInterval(250)
        self._chart_flush_timer.timeout.connect(self._flush_chart_update)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        self.title = QtWidgets.QLabel()
        font = self.title.font()
        font.setPointSize(16)
        font.setBold(True)
        self.title.setFont(font)
        layout.addWidget(self.title)
        self.tabs = QtWidgets.QTabWidget()
        self.chart_panel = QtWidgets.QWidget()
        chart_layout = QtWidgets.QHBoxLayout(self.chart_panel)
        self.market_list = QtWidgets.QListWidget()
        self.market_list.setMinimumWidth(180)
        self.market_list.setMaximumWidth(260)
        self.market_list.currentItemChanged.connect(self._on_market_selected)
        market_column = QtWidgets.QVBoxLayout()
        market_column.addWidget(self.market_list, stretch=1)
        self.remove_product_button = QtWidgets.QPushButton()
        self.remove_product_button.setEnabled(False)
        self.remove_product_button.clicked.connect(self._request_selected_product_removal)
        market_column.addWidget(self.remove_product_button)
        chart_layout.addLayout(market_column)
        chart_column = QtWidgets.QVBoxLayout()
        overlay_row = QtWidgets.QGridLayout()
        overlay_row.setContentsMargins(0, 0, 0, 0)
        overlay_row.setHorizontalSpacing(4)
        overlay_row.setVerticalSpacing(2)
        self.overlay_title = QtWidgets.QLabel()
        self.overlay_title.setMinimumWidth(0)
        self.overlay_title.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Preferred,
        )
        self.signal_overlay_combo = QtWidgets.QComboBox()
        self.signal_overlay_combo.setEnabled(False)
        self.signal_overlay_combo.setMinimumWidth(150)
        self.signal_overlay_combo.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Fixed,
        )
        self.signal_overlay_combo.currentIndexChanged.connect(
            self._on_overlay_signal_selected
        )
        self.entry_overlay_check = QtWidgets.QCheckBox()
        self.invalidation_overlay_check = QtWidgets.QCheckBox()
        self.target_overlay_check = QtWidgets.QCheckBox()
        self.ema_overlay_check = QtWidgets.QCheckBox()
        self.structure_overlay_check = QtWidgets.QCheckBox()
        for checkbox in (
            self.entry_overlay_check,
            self.invalidation_overlay_check,
            self.target_overlay_check,
            self.ema_overlay_check,
            self.structure_overlay_check,
        ):
            checkbox.setChecked(True)
            checkbox.setEnabled(False)
            checkbox.setMinimumWidth(0)
            checkbox.setSizePolicy(
                QtWidgets.QSizePolicy.Preferred,
                QtWidgets.QSizePolicy.Fixed,
            )
            checkbox.toggled.connect(self._apply_selected_signal_overlay)
        overlay_row.addWidget(self.overlay_title, 0, 0)
        overlay_row.addWidget(self.signal_overlay_combo, 0, 1, 1, 6)
        overlay_row.addWidget(self.entry_overlay_check, 1, 0)
        overlay_row.addWidget(self.invalidation_overlay_check, 1, 1)
        overlay_row.addWidget(self.target_overlay_check, 1, 2)
        overlay_row.addWidget(self.ema_overlay_check, 1, 3)
        overlay_row.addWidget(self.structure_overlay_check, 1, 4)
        self.indicator_panel_label = QtWidgets.QLabel()
        self.indicator_panel_combo = QtWidgets.QComboBox()
        self.indicator_panel_combo.setMinimumWidth(145)
        self.indicator_panel_combo.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Fixed,
        )
        self.indicator_panel_combo.currentIndexChanged.connect(
            self._on_indicator_panel_selected
        )
        overlay_row.addWidget(self.indicator_panel_label, 1, 5)
        overlay_row.addWidget(self.indicator_panel_combo, 1, 6)
        overlay_row.setColumnStretch(7, 1)
        chart_column.addLayout(overlay_row)
        self.indicator_snapshot_label = QtWidgets.QLabel()
        self.indicator_snapshot_label.setWordWrap(True)
        self.indicator_snapshot_label.setStyleSheet(
            "color: #8fb3d9; font-size: 11px;"
        )
        chart_column.addWidget(self.indicator_snapshot_label)
        self.chart = ChartView()
        self.chart.resolution_changed.connect(self._on_chart_configuration_changed)
        self.chart.price_basis_changed.connect(self._on_chart_configuration_changed)
        chart_column.addWidget(self.chart, stretch=1)
        chart_layout.addLayout(chart_column, stretch=1)
        self.tabs.addTab(self.chart_panel, "")
        for index, _key in enumerate(PAGE_SPEC_BY_KEY["watchlist"].tab_keys[1:], start=1):
            if index == 1:
                self.technical_panel = self._build_technical_panel()
                self.tabs.addTab(self.technical_panel, "")
                continue
            if index == 2:
                self.ai_panel = self._build_ai_panel()
                self.tabs.addTab(self.ai_panel, "")
                continue
            if index == 3:
                self.trade_plan_panel = self._build_trade_plan_panel()
                self.tabs.addTab(self.trade_plan_panel, "")
                continue
            self.history_panel = self._build_history_panel()
            self.tabs.addTab(self.history_panel, "")
        layout.addWidget(self.tabs, stretch=1)
        self.retranslate_ui()

    def set_scanner_snapshot(self, snapshot: ScannerVM) -> None:
        self._snapshot = snapshot
        if self._managed_watchlist:
            self._refresh_analysis_panels()
            return
        selected = self._selected_epic
        new_epics = tuple(row.reference_epic for row in snapshot.rows)
        current_epics = tuple(
            str(self.market_list.item(index).data(QtCore.Qt.UserRole))
            for index in range(self.market_list.count())
        )
        if new_epics == current_epics:
            for index, row in enumerate(snapshot.rows):
                self.market_list.item(index).setText(f"{row.name}  {_change_text(row)}")
            self._refresh_selected_quote()
            self._refresh_analysis_panels()
            return
        self.market_list.blockSignals(True)
        self.market_list.clear()
        for row in snapshot.rows:
            item = QtWidgets.QListWidgetItem(f"{row.name}  {_change_text(row)}")
            item.setData(QtCore.Qt.UserRole, row.reference_epic)
            self.market_list.addItem(item)
        self.market_list.blockSignals(False)
        target = next(
            (
                index
                for index in range(self.market_list.count())
                if self.market_list.item(index).data(QtCore.Qt.UserRole) == selected
            ),
            0,
        )
        if self.market_list.count():
            self.market_list.setCurrentRow(target)
        self._refresh_analysis_panels()

    def set_macro_snapshot(self, snapshot: MacroVM) -> None:
        """Project the latest advisory macro/AI result into the selected market."""

        self._macro_snapshot = snapshot
        self._refresh_ai_panel(self._row_for_epic(self._selected_epic or ""))

    def set_tracked_products(self, products: tuple[ProductRowVM, ...]) -> None:
        """Render only exact catalogue products followed in the active account context."""

        self._managed_watchlist = True
        selected = self._selected_epic
        self._tracked_products = {product.epic: product for product in products}
        new_epics = tuple(product.epic for product in products)
        current_epics = tuple(
            str(self.market_list.item(index).data(QtCore.Qt.UserRole))
            for index in range(self.market_list.count())
        )
        if new_epics == current_epics:
            for index, product in enumerate(products):
                self.market_list.item(index).setText(_product_list_text(product))
            self._refresh_selected_quote()
            self._refresh_analysis_panels()
            return

        self.market_list.blockSignals(True)
        self.market_list.clear()
        for product in products:
            item = QtWidgets.QListWidgetItem(_product_list_text(product))
            item.setData(QtCore.Qt.UserRole, product.epic)
            item.setToolTip(f"{product.name}\n{product.epic}")
            self.market_list.addItem(item)
        self.market_list.blockSignals(False)
        target = next(
            (
                index
                for index in range(self.market_list.count())
                if self.market_list.item(index).data(QtCore.Qt.UserRole) == selected
            ),
            0,
        )
        if self.market_list.count():
            self.market_list.setCurrentRow(target)
        else:
            self._clear_selection()

    def select_reference_epic(self, epic: str) -> None:
        for index in range(self.market_list.count()):
            if self.market_list.item(index).data(QtCore.Qt.UserRole) == epic:
                self.market_list.setCurrentRow(index)
                return

    def set_environment(self, environment: str) -> None:
        self._chart_flush_timer.stop()
        self._pending_chart_update = None
        self._chart_updates.clear()
        self._analysis_signature = None
        self._environment = environment.strip().upper() or "INCONNU"
        if self._selected_epic is not None:
            self.chart.set_data_context(self._environment, self._selected_epic)
        self._render_selected_history()
        self.chart.set_stream_status("WARMING_UP")
        self._refresh_history_panel()

    def select_catalogue_product(
        self,
        product: ProductRowVM,
        binding: IGProductMarketBinding | None,
    ) -> None:
        self._selected_product = product
        self._selected_product_binding = binding
        self._refresh_paper_ticket()
        self.tabs.setCurrentIndex(3)

    def set_catalogue_snapshot(self, snapshot: CatalogueVM) -> None:
        if self._managed_watchlist:
            replacements = {row.epic: row for row in snapshot.rows}
            products = tuple(
                replacements.get(epic, product)
                for epic, product in self._tracked_products.items()
            )
            self.set_tracked_products(products)
            return
        selected = self._selected_product
        if selected is None:
            return
        replacement = next((row for row in snapshot.rows if row.epic == selected.epic), None)
        if replacement is not None:
            self._selected_product = replacement
            self._refresh_paper_ticket()

    def apply_chart_update(self, update: ChartCandleUpdate) -> None:
        updates = self._chart_updates.setdefault(update.epic, [])
        if updates and updates[-1].timestamp_ms == update.timestamp_ms:
            updates[-1] = update
        else:
            updates.append(update)
            if len(updates) > 500:
                del updates[:-500]
        if update.epic == self._selected_epic:
            self._pending_chart_update = update
            self._refresh_history_panel()
            if self.isVisible() and not self._chart_flush_timer.isActive():
                self._chart_flush_timer.start()

    def retranslate_ui(self) -> None:
        self.title.setText(self._language.text("nav.watchlist"))
        spec = PAGE_SPEC_BY_KEY["watchlist"]
        for index, key in enumerate(spec.tab_keys):
            self.tabs.setTabText(index, self._language.text(key))
        self.indicator_heading.setText(
            self._language.text("watchlist.indicators.heading")
        )
        self.indicator_table.setHorizontalHeaderLabels(
            [
                self._language.text("watchlist.indicator.column.name"),
                self._language.text("watchlist.indicator.column.value"),
                self._language.text("watchlist.indicator.column.params"),
                self._language.text("watchlist.indicator.column.state"),
                self._language.text("watchlist.indicator.column.candles"),
                self._language.text("watchlist.indicator.column.source"),
            ]
        )
        self.technical_table.setHorizontalHeaderLabels(
            [
                self._language.text("watchlist.signal.strategy"),
                self._language.text("watchlist.signal.product"),
                self._language.text("watchlist.signal.direction"),
                self._language.text("watchlist.signal.state"),
                self._language.text("watchlist.signal.entry"),
                self._language.text("watchlist.signal.invalidation"),
                self._language.text("watchlist.signal.target"),
                self._language.text("watchlist.signal.valid_until"),
            ]
        )
        for box, title_key in (
            (self.long_plan_group, "watchlist.plan.long"),
            (self.short_plan_group, "watchlist.plan.short"),
            (self.no_trade_group, "watchlist.plan.no_trade"),
        ):
            box.setTitle(self._language.text(title_key))
        self.overlay_title.setText(self._language.text("watchlist.overlay.title"))
        self._populate_signal_overlay_combo(
            self._current_signal_rows,
            self.signal_overlay_combo.currentIndex(),
        )
        self.entry_overlay_check.setText(
            self._language.text("watchlist.overlay.entry")
        )
        self.invalidation_overlay_check.setText(
            self._language.text("watchlist.overlay.invalidation")
        )
        self.target_overlay_check.setText(
            self._language.text("watchlist.overlay.target")
        )
        self.ema_overlay_check.setText(self._language.text("watchlist.overlay.ema"))
        self.structure_overlay_check.setText(
            self._language.text("watchlist.overlay.structure")
        )
        self.indicator_panel_label.setText(
            self._language.text("watchlist.overlay.indicator_panel")
        )
        self._retranslate_indicator_panel_combo()
        overlay_tooltip = self._language.text("watchlist.overlay.availability_tooltip")
        for checkbox in (
            self.entry_overlay_check,
            self.invalidation_overlay_check,
            self.target_overlay_check,
            self.ema_overlay_check,
            self.structure_overlay_check,
        ):
            checkbox.setToolTip(overlay_tooltip)
        self.indicator_panel_combo.setToolTip(
            self._language.text("watchlist.overlay.indicator_panel_tooltip")
        )
        signal_selector_tooltip = self._language.text(
            "watchlist.overlay.signal_selector_tooltip"
        )
        self.overlay_title.setToolTip(signal_selector_tooltip)
        self.signal_overlay_combo.setToolTip(signal_selector_tooltip)
        self.ai_open_button.setText(self._language.text("watchlist.ai.open_macro"))
        self.remove_product_button.setText(
            self._language.text("watchlist.remove_product")
        )
        self.paper_ticket_preparation.retranslate_ui()
        self._refresh_analysis_panels()

    def _on_market_selected(self, current: object, _previous: object) -> None:
        if isinstance(current, QtWidgets.QListWidgetItem):
            self._select_epic(str(current.data(QtCore.Qt.UserRole)))
            self.remove_product_button.setEnabled(self._managed_watchlist)
            return
        self.remove_product_button.setEnabled(False)

    @QtCore.pyqtSlot()
    def _request_selected_product_removal(self) -> None:
        if self._managed_watchlist and self._selected_epic is not None:
            self.product_remove_requested.emit(self._selected_epic)

    def _on_overlay_signal_selected(self, index: int) -> None:
        if index < 0 or index >= len(self._current_signal_rows):
            return
        self.technical_table.selectRow(index)
        self._show_signal_detail(index)

    def _on_indicator_panel_selected(self, index: int) -> None:
        if index >= 0 and self._selected_signal is not None:
            signal_key = (
                self._selected_signal.product_epic,
                self._selected_signal.strategy_id,
            )
            self._indicator_panel_by_signal_key[signal_key] = str(
                self.indicator_panel_combo.itemData(index) or "none"
            )
        self._apply_selected_signal_overlay()

    def _select_epic(self, epic: str) -> None:
        self._chart_flush_timer.stop()
        self._pending_chart_update = None
        self._selected_epic = epic
        self._analysis_signature = None
        product = self._tracked_products.get(epic) if self._managed_watchlist else None
        if product is not None:
            self._selected_product = product
            self._selected_product_binding = self._product_market_bindings.get(epic)
            self.chart.set_data_context(self._environment, product.epic)
            self.chart.set_selected_product(_tradable_product_from_row(product))
            self._render_selected_history()
            self._refresh_selected_quote()
            self._refresh_analysis_panels()
            self._refresh_paper_ticket()
            return
        row = self._row_for_epic(epic)
        if row is None:
            return
        self.chart.set_data_context(self._environment, row.reference_epic)
        self.chart.set_selected_product(
            TradableProduct(
                epic=row.reference_epic,
                name=row.name,
                product_type=ProductType.CASH_OR_DFB,
                asset_class=(
                    AssetClass.COMMODITIES
                    if row.asset_class == "commodities"
                    else AssetClass.INDICES
                ),
                bid=float(row.bid) if row.bid is not None else None,
                offer=float(row.offer) if row.offer is not None else None,
                net_change=float(row.net_change) if row.net_change is not None else None,
                percent_change=(
                    float(row.percent_change) if row.percent_change is not None else None
                ),
            )
        )
        self._render_selected_history()
        self._refresh_selected_quote()
        self._refresh_analysis_panels()

    def _refresh_selected_quote(self) -> None:
        epic = self._selected_epic
        if epic is None:
            return
        if self._managed_watchlist:
            product = self._tracked_products.get(epic)
            if product is None:
                return
            self.chart.set_live_quote(_quote_from_product_row(product))
            self.chart.set_stream_status(
                "LIVE"
                if product.provenance.source == "ig-lightstreamer"
                or self._chart_updates.get(epic)
                else "WARMING_UP"
            )
            return
        row = self._row_for_epic(epic)
        if row is None:
            return
        self.chart.set_live_quote(
            Quote(
                epic=epic,
                bid=float(row.bid) if row.bid is not None else None,
                offer=float(row.offer) if row.offer is not None else None,
                net_change=float(row.net_change) if row.net_change is not None else None,
                percent_change=(
                    float(row.percent_change) if row.percent_change is not None else None
                ),
            )
        )
        self.chart.set_stream_status(
            "LIVE"
            if row.quote_provenance.source == "ig-lightstreamer"
            or self._chart_updates.get(epic)
            else "WARMING_UP"
        )

    @QtCore.pyqtSlot()
    def _flush_chart_update(self) -> None:
        update = self._pending_chart_update
        self._pending_chart_update = None
        if update is None or update.epic != self._selected_epic or not self.isVisible():
            return
        self.chart.apply_chart_update(update)
        self.chart.set_stream_status("LIVE")
        self._configure_overlay_controls(self._selected_signal)
        self._apply_selected_signal_overlay()

    def _on_chart_configuration_changed(self, _value: object) -> None:
        self._render_selected_history()
        self._configure_overlay_controls(self._selected_signal)
        self._apply_selected_signal_overlay()

    def _render_selected_history(self) -> None:
        epic = self._selected_epic
        if epic is None:
            self.chart.set_bars([])
            return
        self.chart.set_chart_updates(self._chart_updates.get(epic, ()))

    def showEvent(self, event: QtCore.QEvent) -> None:  # noqa: N802
        super().showEvent(event)
        self._render_selected_history()
        self._refresh_selected_quote()

    def _row_for_epic(self, epic: str) -> ScannerMarketRowVM | None:
        if self._snapshot is None:
            return None
        if self._managed_watchlist:
            binding = self._product_market_bindings.get(epic)
            if binding is None:
                return None
            row = next(
                (
                    candidate
                    for candidate in self._snapshot.rows
                    if candidate.reference_epic == binding.reference_epic
                ),
                None,
            )
            if row is None:
                return None
            return replace(
                row,
                strategy_signals=tuple(
                    signal for signal in row.strategy_signals if signal.product_epic == epic
                ),
            )
        return next((row for row in self._snapshot.rows if row.reference_epic == epic), None)

    def _clear_selection(self) -> None:
        self._chart_flush_timer.stop()
        self._pending_chart_update = None
        self._selected_epic = None
        self._selected_product = None
        self._selected_product_binding = None
        self._analysis_signature = None
        self.remove_product_button.setEnabled(False)
        self.chart.clear_selected_product(self._language.text("watchlist.no_product"))
        self.chart.set_stream_status("WARMING_UP")
        self._refresh_analysis_panels()

    def _refresh_paper_ticket(self) -> None:
        product = self._selected_product
        if product is None:
            return
        self.paper_ticket_preparation.set_snapshot(
            build_paper_ticket_preparation(
                product=product,
                binding=self._selected_product_binding,
                evaluated_at_utc=datetime.now(UTC),
            )
        )

    def _build_technical_panel(self) -> QtWidgets.QWidget:
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(panel)
        self.technical_summary = QtWidgets.QLabel()
        self.technical_summary.setWordWrap(True)
        self.technical_summary.setMinimumWidth(0)
        self.technical_summary.setSizePolicy(
            QtWidgets.QSizePolicy.Ignored,
            QtWidgets.QSizePolicy.Preferred,
        )
        layout.addWidget(self.technical_summary)
        self.indicator_heading = QtWidgets.QLabel()
        self.indicator_heading.setProperty("role", "sectionHeading")
        layout.addWidget(self.indicator_heading)
        self.indicator_table = QtWidgets.QTableWidget(0, 6)
        self.indicator_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.indicator_table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.indicator_table.setAlternatingRowColors(True)
        self.indicator_table.setMinimumWidth(0)
        self.indicator_table.setMaximumHeight(190)
        self.indicator_table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustIgnored)
        self.indicator_table.setHorizontalScrollMode(
            QtWidgets.QAbstractItemView.ScrollPerPixel
        )
        self.indicator_table.verticalHeader().setVisible(False)
        self.indicator_table.horizontalHeader().setStretchLastSection(True)
        for column, width in enumerate((155, 105, 115, 100, 90, 190)):
            self.indicator_table.setColumnWidth(column, width)
        layout.addWidget(self.indicator_table)
        self.technical_table = QtWidgets.QTableWidget(0, 8)
        self.technical_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.technical_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.technical_table.setAlternatingRowColors(True)
        self.technical_table.setMinimumWidth(0)
        self.technical_table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustIgnored)
        self.technical_table.setHorizontalScrollMode(
            QtWidgets.QAbstractItemView.ScrollPerPixel
        )
        self.technical_table.verticalHeader().setVisible(False)
        self.technical_table.horizontalHeader().setStretchLastSection(True)
        for column, width in enumerate((110, 165, 105, 100, 115, 105, 105, 145)):
            self.technical_table.setColumnWidth(column, width)
        layout.addWidget(self.technical_table, stretch=1)
        self.technical_detail = QtWidgets.QPlainTextEdit()
        self.technical_detail.setReadOnly(True)
        self.technical_detail.setMaximumHeight(165)
        self.technical_table.currentCellChanged.connect(
            lambda row, _column, _previous_row, _previous_column: self._show_signal_detail(row)
        )
        layout.addWidget(self.technical_detail)
        return panel

    def _build_ai_panel(self) -> QtWidgets.QWidget:
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(panel)
        self.ai_status = QtWidgets.QLabel()
        self.ai_status.setWordWrap(True)
        self.ai_status.setMinimumWidth(0)
        self.ai_status.setSizePolicy(
            QtWidgets.QSizePolicy.Ignored,
            QtWidgets.QSizePolicy.Preferred,
        )
        self.ai_status.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        self.ai_status.setProperty("role", "card")
        layout.addWidget(self.ai_status)
        self.ai_sources = QtWidgets.QLabel()
        self.ai_sources.setWordWrap(True)
        self.ai_sources.setMinimumWidth(0)
        self.ai_sources.setSizePolicy(
            QtWidgets.QSizePolicy.Ignored,
            QtWidgets.QSizePolicy.Preferred,
        )
        self.ai_sources.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        self.ai_sources.setProperty("role", "muted")
        layout.addWidget(self.ai_sources)
        self.ai_open_button = QtWidgets.QPushButton()
        self.ai_open_button.clicked.connect(self.macro_open_requested)
        layout.addWidget(self.ai_open_button)
        layout.addStretch(1)
        return panel

    def _build_history_panel(self) -> QtWidgets.QWidget:
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(panel)
        self.history_summary = QtWidgets.QLabel()
        self.history_summary.setWordWrap(True)
        self.history_summary.setMinimumWidth(0)
        self.history_summary.setSizePolicy(
            QtWidgets.QSizePolicy.Ignored,
            QtWidgets.QSizePolicy.Preferred,
        )
        self.history_summary.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        layout.addWidget(self.history_summary)
        layout.addStretch(1)
        return panel

    def _build_trade_plan_panel(self) -> QtWidgets.QWidget:
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(panel)
        scenario_row = QtWidgets.QHBoxLayout()
        self.long_plan_group, self.long_plan_text = self._scenario_group()
        self.short_plan_group, self.short_plan_text = self._scenario_group()
        self.no_trade_group, self.no_trade_text = self._scenario_group()
        scenario_row.addWidget(self.long_plan_group)
        scenario_row.addWidget(self.short_plan_group)
        scenario_row.addWidget(self.no_trade_group)
        layout.addLayout(scenario_row)
        self.paper_ticket_preparation = PaperTicketPreparationWidget(self._language)
        self.paper_ticket_preparation.paper_submission_requested.connect(
            self.paper_submission_requested
        )
        layout.addWidget(self.paper_ticket_preparation, stretch=1)
        return panel

    @staticmethod
    def _scenario_group() -> tuple[QtWidgets.QGroupBox, QtWidgets.QLabel]:
        group = QtWidgets.QGroupBox()
        group_layout = QtWidgets.QVBoxLayout(group)
        label = QtWidgets.QLabel()
        label.setWordWrap(True)
        label.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        label.setMinimumWidth(0)
        label.setSizePolicy(
            QtWidgets.QSizePolicy.Ignored,
            QtWidgets.QSizePolicy.Preferred,
        )
        group.setMinimumWidth(0)
        group.setSizePolicy(
            QtWidgets.QSizePolicy.Ignored,
            QtWidgets.QSizePolicy.Preferred,
        )
        group_layout.addWidget(label)
        return group, label

    def _refresh_analysis_panels(self) -> None:
        row = self._row_for_epic(self._selected_epic or "")
        if row is None:
            self.technical_summary.setText(self._language.text("watchlist.no_market"))
            self.indicator_table.setRowCount(0)
            self.technical_table.setRowCount(0)
            self.technical_detail.clear()
            self._selected_signal = None
            self._populate_signal_overlay_combo((), -1)
            self.chart.set_analysis_levels(())
            self.chart.set_analysis_series(())
            self._refresh_ai_panel(None)
            self._refresh_trade_plan(None)
            self._refresh_history_panel()
            return
        signature = (
            row.reference_epic,
            row.technical_score,
            row.context_score,
            row.context_level,
            row.context_components,
            row.context_reason_codes,
            row.context_provenance,
            row.context_safety_veto,
            row.signal_direction,
            row.recommendation,
            row.observed_candles,
            row.required_candles,
            row.reason_codes,
            row.evaluated_at_utc,
            row.strategy_signals,
            row.indicators,
            self._language.locale,
        )
        if signature == self._analysis_signature:
            self._refresh_history_panel()
            return
        self._analysis_signature = signature
        technical = _optional_text(row.technical_score)
        context = self._context_text(row)
        evaluated = _datetime_text(row.evaluated_at_utc)
        technical_summary = self._language.text("watchlist.technical.summary").format(
                market=row.name,
                direction=row.signal_direction.upper(),
                decision=row.recommendation.upper(),
                technical=technical,
                context=context,
                observed=row.observed_candles,
                required=row.required_candles,
                evaluated=evaluated,
                reasons=", ".join(row.reason_codes) or "N/A",
            )
        if any(
            "gui-v2:exact-product-price-candle-fallback" in signal.provenance
            for signal in row.strategy_signals
        ):
            technical_summary = (
                f"{technical_summary}\n"
                f"{self._language.text('watchlist.technical.product_fallback')}"
            )
        self.technical_summary.setText(
            technical_summary
        )
        self.technical_summary.setToolTip(self._context_tooltip(row))
        self._populate_indicator_table(row.indicators)
        self.technical_table.setRowCount(len(row.strategy_signals))
        self._current_signal_rows = row.strategy_signals
        for index, signal in enumerate(row.strategy_signals):
            values = (
                signal.strategy_id,
                signal.product_epic,
                signal.side.upper(),
                signal.data_state.upper(),
                _entry_text(signal.entry_low, signal.entry_high),
                _optional_text(signal.invalidation),
                _optional_text(signal.target),
                _datetime_text(signal.valid_until_utc),
            )
            for column, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                if signal.reason_codes:
                    item.setToolTip(", ".join(signal.reason_codes))
                self.technical_table.setItem(index, column, item)
        if row.strategy_signals:
            remembered_strategy = self._selected_strategy_by_epic.get(
                self._selected_epic or ""
            )
            selected_row = next(
                (
                    index
                    for index, signal in enumerate(row.strategy_signals)
                    if signal.strategy_id == remembered_strategy
                ),
                _preferred_signal_row(row.strategy_signals),
            )
            self._populate_signal_overlay_combo(row.strategy_signals, selected_row)
            self.technical_table.selectRow(selected_row)
            self._show_signal_detail(selected_row)
        else:
            self._populate_signal_overlay_combo((), -1)
            self.technical_detail.setPlainText(
                self._language.text("watchlist.technical.no_signal")
            )
            self._selected_signal = None
            self._apply_selected_signal_overlay()
        self._refresh_ai_panel(row)
        self._refresh_trade_plan(row)
        self._refresh_history_panel()

    def _populate_indicator_table(
        self,
        indicators: tuple[ScannerIndicatorVM, ...],
    ) -> None:
        self.indicator_table.setRowCount(len(indicators))
        for index, indicator in enumerate(indicators):
            name_key = f"watchlist.indicator.name.{indicator.name}"
            name = self._language.text(name_key)
            if indicator.component is not None:
                component_key = (
                    f"watchlist.indicator.component.{indicator.component}"
                )
                name = f"{name} · {self._language.text(component_key)}"
            state = self._language.text(
                f"watchlist.indicator.state.{indicator.state}"
            )
            values = (
                name,
                _optional_text(indicator.value),
                _indicator_parameters_text(indicator.parameters),
                state,
                f"{indicator.observed_points}/{indicator.required_points}",
                _indicator_source_text(indicator.provenance),
            )
            tooltip = self._language.text("watchlist.indicator.tooltip").format(
                reasons=", ".join(indicator.reason_codes) or "N/A",
                provenance="\n".join(indicator.provenance) or "N/A",
            )
            for column, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                item.setToolTip(tooltip)
                self.indicator_table.setItem(index, column, item)

    def _context_text(self, row: ScannerMarketRowVM) -> str:
        if row.context_level is None:
            return self._language.text("scanner.context.unknown")
        label = self._language.text(f"scanner.context.{row.context_level}")
        return label if row.context_score is None else f"{label} · {row.context_score}/100"

    def _context_tooltip(self, row: ScannerMarketRowVM) -> str:
        if row.context_level is None:
            return self._language.text("scanner.context.no_evidence")
        return self._language.text("scanner.context.tooltip").format(
            components="\n".join(f"• {item}" for item in row.context_components) or "N/A",
            reasons=", ".join(row.context_reason_codes) or "N/A",
            provenance=", ".join(row.context_provenance) or "N/A",
            veto=self._language.text(
                "scanner.context.veto_yes"
                if row.context_safety_veto
                else "scanner.context.veto_no"
            ),
        )

    def _refresh_ai_panel(self, row: ScannerMarketRowVM | None) -> None:
        if row is None:
            self.ai_status.setText(self._language.text("watchlist.no_market"))
            self.ai_sources.clear()
            return
        snapshot = self._macro_snapshot
        if snapshot is None or snapshot.ai_status is Availability.UNAVAILABLE:
            self.ai_status.setText(
                self._language.text("watchlist.ai.unavailable").format(
                    market=row.name,
                    epic=row.reference_epic,
                )
            )
            self.ai_sources.setText(
                self._language.text("watchlist.ai.unavailable_reasons").format(
                    reasons=(
                        ", ".join(snapshot.ai_reason_codes)
                        if snapshot is not None
                        else "AI_NOT_REQUESTED"
                    )
                )
            )
            return
        scope = snapshot.ai_scope or "N/A"
        scope_display = (
            self._language.text("watchlist.ai.scope_global")
            if scope == "GLOBAL-MARKET-CONTEXT"
            else scope
        )
        selected_epic = self._selected_epic or ""
        applies = scope in {
            "GLOBAL-MARKET-CONTEXT",
            row.reference_epic,
            selected_epic,
        }
        if not applies:
            self.ai_status.setText(
                self._language.text("watchlist.ai.scope_mismatch").format(
                    market=row.name,
                    scope=scope_display,
                )
            )
            self.ai_sources.setText(
                self._language.text("watchlist.ai.scope_mismatch_detail")
            )
            return
        generated = _datetime_text(snapshot.ai_generated_at_utc)
        valid_until = _datetime_text(snapshot.ai_valid_until_utc)
        if snapshot.ai_status is Availability.STALE:
            self.ai_status.setText(
                self._language.text("watchlist.ai.stale").format(
                    market=row.name,
                    scope=scope_display,
                    generated=generated,
                    valid_until=valid_until,
                )
            )
        else:
            self.ai_status.setText(
                self._language.text("watchlist.ai.summary").format(
                    market=row.name,
                    scope=scope_display,
                    bias=(snapshot.ai_directional_bias or "UNKNOWN").upper(),
                    risk=(snapshot.ai_event_risk or "UNKNOWN").upper(),
                    confidence=(
                        f"{snapshot.ai_confidence * 100:.1f}%"
                        if snapshot.ai_confidence is not None
                        else "N/A"
                    ),
                    generated=generated,
                    valid_until=valid_until,
                    summary=snapshot.ai_summary or "N/A",
                    flags=", ".join(snapshot.ai_risk_flags) or "N/A",
                )
            )
        sources = tuple(
            dict.fromkeys(
                f"{evidence.source} — {evidence.headline}"
                for evidence in snapshot.ai_evidence_rows
            )
        )
        self.ai_sources.setText(
            self._language.text("watchlist.ai.sources").format(
                count=len(sources),
                sources="\n".join(f"• {source}" for source in sources) or "N/A",
            )
        )

    def _show_signal_detail(self, row: int) -> None:
        if row < 0 or row >= len(self._current_signal_rows):
            self.technical_detail.clear()
            self._selected_signal = None
            self._configure_overlay_controls(None)
            self._apply_selected_signal_overlay()
            return
        signal = self._current_signal_rows[row]
        self._selected_signal = signal
        if self._selected_epic is not None:
            self._selected_strategy_by_epic[self._selected_epic] = signal.strategy_id
        if self.signal_overlay_combo.currentIndex() != row:
            self.signal_overlay_combo.blockSignals(True)
            self.signal_overlay_combo.setCurrentIndex(row)
            self.signal_overlay_combo.blockSignals(False)
        features = "\n".join(
            f"  • {name}: {_optional_text(value)}" for name, value in signal.features
        )
        if not features:
            features = "  • N/A"
        self.technical_detail.setPlainText(
            self._language.text("watchlist.technical.detail").format(
                signal_id=signal.signal_id,
                confidence=_optional_text(signal.confidence),
                quality=_optional_text(signal.data_quality),
                generated=_datetime_text(signal.generated_at_utc),
                valid_until=_datetime_text(signal.valid_until_utc),
                reasons=", ".join(signal.reason_codes) or "N/A",
                provenance=" · ".join(signal.provenance) or "N/A",
                features=features,
            )
        )
        self._configure_overlay_controls(signal)
        self._apply_selected_signal_overlay()

    def _populate_signal_overlay_combo(
        self,
        signals: tuple[ScannerSignalVM, ...],
        selected_row: int,
    ) -> None:
        self.signal_overlay_combo.blockSignals(True)
        self.signal_overlay_combo.clear()
        for signal in signals:
            self.signal_overlay_combo.addItem(
                self._language.text("watchlist.overlay.signal_option").format(
                    strategy=signal.strategy_id,
                    direction=signal.side.upper(),
                    state=self._language.text(
                        f"watchlist.indicator.state.{signal.data_state}"
                    ),
                ),
                signal.signal_id,
            )
        self.signal_overlay_combo.setEnabled(bool(signals))
        self.signal_overlay_combo.setCurrentIndex(selected_row)
        self.signal_overlay_combo.blockSignals(False)

    def _apply_selected_signal_overlay(self) -> None:
        signal = self._selected_signal
        if signal is None:
            self.indicator_snapshot_label.setText(
                self._language.text("watchlist.indicators.unavailable")
            )
            self.chart.set_analysis_levels(())
            self.chart.set_analysis_series(())
            self.chart.set_indicator_panel(None)
            return
        ema_curves = self._ema_overlay_series(signal)
        indicator_panels = self._indicator_panels(signal)
        selected_panel_key = str(self.indicator_panel_combo.currentData() or "none")
        self.indicator_snapshot_label.setText(_indicator_snapshot_text(signal, self._language))
        self.chart.set_analysis_levels(
            _signal_overlay_levels(
                signal,
                self._language,
                include_entry=self.entry_overlay_check.isChecked(),
                include_invalidation=self.invalidation_overlay_check.isChecked(),
                include_target=self.target_overlay_check.isChecked(),
                include_structure=self.structure_overlay_check.isChecked(),
            ),
            source_label=signal.signal_id,
        )
        self.chart.set_analysis_series(
            ema_curves if self.ema_overlay_check.isChecked() else (),
            source_label=signal.signal_id,
        )
        self.chart.set_indicator_panel(indicator_panels.get(selected_panel_key))

    def _ema_overlay_series(
        self,
        signal: ScannerSignalVM,
    ) -> tuple[ChartOverlaySeries, ...]:
        features = dict(signal.features)
        if not any(
            name in features
            for name in ("fast_ema", "slow_ema", "ema_fast", "ema_slow")
        ):
            return ()
        periods = _ema_periods_from_signal(signal)
        epic = self._selected_epic
        if periods is None or epic is None:
            return ()
        indicator_input = _closed_indicator_input_from_updates(
            epic=epic,
            updates=tuple(self._chart_updates.get(epic, ())),
            interval_seconds=self.chart.current_interval_seconds(),
            price_basis=self.chart.current_price_basis(),
        )
        fast = ema_series(indicator_input, periods[0])
        slow = ema_series(indicator_input, periods[1])
        if fast.state is not DataState.READY or slow.state is not DataState.READY:
            return ()
        return (
            _chart_series_from_indicator(
                self._language.text("chart.overlay.fast_ema"),
                fast.points,
                "#20b8cd",
            ),
            _chart_series_from_indicator(
                self._language.text("chart.overlay.slow_ema"),
                slow.points,
                "#7a6ff0",
            ),
        )

    def _rsi_indicator_panel(
        self,
        signal: ScannerSignalVM,
    ) -> ChartIndicatorPanel | None:
        features = dict(signal.features)
        if "rsi" not in features:
            return None
        period = _positive_config_period(signal, "rsi_period")
        epic = self._selected_epic
        if period is None or epic is None:
            return None
        indicator_input = _closed_indicator_input_from_updates(
            epic=epic,
            updates=tuple(self._chart_updates.get(epic, ())),
            interval_seconds=self.chart.current_interval_seconds(),
            price_basis=self.chart.current_price_basis(),
        )
        result = rsi_series(indicator_input, period)
        if result.state is not DataState.READY:
            return None
        return ChartIndicatorPanel(
            label=f"RSI {period}",
            series=(
                _chart_series_from_indicator(
                    f"RSI {period}",
                    result.points,
                    "#d7a93b",
                ),
            ),
            minimum=0.0,
            maximum=100.0,
            reference_levels=(
                (30.0, self._language.text("chart.panel.rsi.oversold"), "#2ca56c"),
                (50.0, "50", "#526784"),
                (70.0, self._language.text("chart.panel.rsi.overbought"), "#d75a5a"),
            ),
        )

    def _atr_indicator_panel(
        self,
        signal: ScannerSignalVM,
    ) -> ChartIndicatorPanel | None:
        features = dict(signal.features)
        if "atr" not in features:
            return None
        period = _positive_config_period(signal, "atr_period")
        epic = self._selected_epic
        if period is None or epic is None:
            return None
        indicator_input = _closed_indicator_input_from_updates(
            epic=epic,
            updates=tuple(self._chart_updates.get(epic, ())),
            interval_seconds=self.chart.current_interval_seconds(),
            price_basis=self.chart.current_price_basis(),
        )
        result = atr_series(indicator_input, period)
        if result.state is not DataState.READY:
            return None
        maximum = max(float(point.value) for point in result.points)
        maximum = max(maximum * 1.15, 1e-9)
        return ChartIndicatorPanel(
            label=f"ATR {period}",
            series=(
                _chart_series_from_indicator(
                    f"ATR {period}",
                    result.points,
                    "#20b8cd",
                ),
            ),
            minimum=0.0,
            maximum=maximum,
        )

    def _macd_indicator_panel(
        self,
        signal: ScannerSignalVM,
    ) -> ChartIndicatorPanel | None:
        features = dict(signal.features)
        if not any(name.startswith("macd") for name in features):
            return None
        periods = _macd_periods_from_signal(signal)
        epic = self._selected_epic
        if periods is None or epic is None:
            return None
        indicator_input = _closed_indicator_input_from_updates(
            epic=epic,
            updates=tuple(self._chart_updates.get(epic, ())),
            interval_seconds=self.chart.current_interval_seconds(),
            price_basis=self.chart.current_price_basis(),
        )
        result = macd_series(
            indicator_input,
            fast_period=periods[0],
            slow_period=periods[1],
            signal_period=periods[2],
        )
        if result.state is not DataState.READY:
            return None
        components = {series.name: series for series in result.series}
        if set(components) != {"line", "signal", "histogram"}:
            return None
        values = tuple(
            float(point.value)
            for series in result.series
            for point in series.points
        )
        amplitude = max((abs(value) for value in values), default=0.0)
        amplitude = max(amplitude * 1.15, 1e-9)
        return ChartIndicatorPanel(
            label=f"MACD {periods[0]}/{periods[1]}/{periods[2]}",
            series=(
                _chart_series_from_indicator(
                    self._language.text("chart.panel.macd.line"),
                    components["line"].points,
                    "#20b8cd",
                ),
                _chart_series_from_indicator(
                    self._language.text("chart.panel.macd.signal"),
                    components["signal"].points,
                    "#d7a93b",
                ),
                _chart_series_from_indicator(
                    self._language.text("chart.panel.macd.histogram"),
                    components["histogram"].points,
                    "#7a6ff0",
                ),
            ),
            minimum=-amplitude,
            maximum=amplitude,
            reference_levels=((0.0, "0", "#526784"),),
        )

    def _indicator_panels(
        self,
        signal: ScannerSignalVM,
    ) -> dict[str, ChartIndicatorPanel]:
        candidates = (
            ("rsi", self._rsi_indicator_panel(signal)),
            ("atr", self._atr_indicator_panel(signal)),
            ("macd", self._macd_indicator_panel(signal)),
        )
        return {
            key: panel
            for key, panel in candidates
            if panel is not None
        }

    def _retranslate_indicator_panel_combo(self) -> None:
        preferred = str(self.indicator_panel_combo.currentData() or "none")
        self._configure_indicator_panel_selector(self._selected_signal, preferred=preferred)

    def _configure_indicator_panel_selector(
        self,
        signal: ScannerSignalVM | None,
        *,
        preferred: str | None = None,
    ) -> None:
        panels = {} if signal is None else self._indicator_panels(signal)
        remembered = (
            self._indicator_panel_by_signal_key.get(
                (signal.product_epic, signal.strategy_id)
            )
            if signal is not None
            else None
        )
        available_keys = tuple(panels)
        if preferred is not None:
            current = preferred
        elif remembered is not None:
            current = remembered
        else:
            displayed = str(self.indicator_panel_combo.currentData() or "none")
            current = (
                displayed
                if displayed != "none" and displayed in panels
                else next(
                    (key for key in ("rsi", "atr", "macd") if key in panels),
                    "none",
                )
            )
        # ``none`` is always a valid explicit user choice even though it is not an
        # indicator panel key.  Treating it as unavailable made every projection
        # refresh silently select the first computed panel again.
        if current != "none" and current not in available_keys:
            current = next(
                (key for key in ("rsi", "atr", "macd") if key in panels),
                "none",
            )
        options = [("none", self._language.text("watchlist.panel.none"))]
        for key in available_keys:
            options.append((key, panels[key].label))
        self.indicator_panel_combo.blockSignals(True)
        self.indicator_panel_combo.clear()
        for key, label in options:
            self.indicator_panel_combo.addItem(label, key)
        selected_index = self.indicator_panel_combo.findData(current)
        self.indicator_panel_combo.setCurrentIndex(max(selected_index, 0))
        self.indicator_panel_combo.setEnabled(bool(panels))
        self.indicator_panel_combo.blockSignals(False)

    def _configure_overlay_controls(self, signal: ScannerSignalVM | None) -> None:
        features = {} if signal is None else dict(signal.features)
        indicator_panels = {} if signal is None else self._indicator_panels(signal)
        availability = (
            (
                self.entry_overlay_check,
                signal is not None
                and (signal.entry_low is not None or signal.entry_high is not None),
            ),
            (
                self.invalidation_overlay_check,
                signal is not None and signal.invalidation is not None,
            ),
            (
                self.target_overlay_check,
                signal is not None and signal.target is not None,
            ),
            (
                self.ema_overlay_check,
                signal is not None and bool(self._ema_overlay_series(signal)),
            ),
            (
                self.structure_overlay_check,
                "support" in features or "resistance" in features,
            ),
        )
        availability_signature = (
            None if signal is None else signal.signal_id,
            *(available for _checkbox, available in availability),
            *indicator_panels,
        )
        selection_changed = availability_signature != self._overlay_availability_signature
        self._overlay_availability_signature = availability_signature
        for checkbox, available in availability:
            checkbox.blockSignals(True)
            checkbox.setEnabled(available)
            if selection_changed or not available:
                checkbox.setChecked(available)
            checkbox.blockSignals(False)
        self._configure_indicator_panel_selector(signal)

    def _refresh_trade_plan(self, row: ScannerMarketRowVM | None) -> None:
        if row is None:
            text = self._language.text("watchlist.no_market")
            self.long_plan_text.setText(text)
            self.short_plan_text.setText(text)
            self.no_trade_text.setText(text)
            return
        long_signals = tuple(signal for signal in row.strategy_signals if signal.side == "buy")
        short_signals = tuple(signal for signal in row.strategy_signals if signal.side == "sell")
        flat_signals = tuple(signal for signal in row.strategy_signals if signal.side == "flat")
        self.long_plan_text.setText(self._scenario_text(long_signals, "LONG"))
        self.short_plan_text.setText(self._scenario_text(short_signals, "SHORT"))
        blockers = tuple(
            dict.fromkeys(
                (
                    *row.reason_codes,
                    *(
                        reason
                        for signal in flat_signals
                        for reason in signal.reason_codes
                    ),
                )
            )
        )
        self.no_trade_text.setText(
            self._language.text("watchlist.plan.blockers").format(
                decision=row.recommendation.upper(),
                blockers=", ".join(blockers) or "N/A",
            )
        )

    def _scenario_text(
        self,
        signals: tuple[ScannerSignalVM, ...],
        direction: str,
    ) -> str:
        ready = tuple(signal for signal in signals if signal.data_state == "ready")
        if not ready:
            return self._language.text("watchlist.plan.unavailable").format(
                direction=direction
            )
        signal = max(
            ready,
            key=lambda item: (
                item.confidence if item.confidence is not None else -1,
                item.data_quality if item.data_quality is not None else -1,
            ),
        )
        return self._language.text("watchlist.plan.scenario").format(
            direction=direction,
            strategy=signal.strategy_id,
            product=signal.product_epic,
            entry=_entry_text(signal.entry_low, signal.entry_high),
            invalidation=_optional_text(signal.invalidation),
            target=_optional_text(signal.target),
            validity=_datetime_text(signal.valid_until_utc),
        )

    def _refresh_history_panel(self) -> None:
        epic = self._selected_epic
        updates = () if epic is None else tuple(self._chart_updates.get(epic, ()))
        if epic is None:
            self.history_summary.setText(self._language.text("watchlist.no_market"))
            return
        timestamps = tuple(
            update.timestamp_ms for update in updates if update.timestamp_ms is not None
        )
        first = _timestamp_text(min(timestamps)) if timestamps else "N/A"
        last = _timestamp_text(max(timestamps)) if timestamps else "N/A"
        self.history_summary.setText(
            self._language.text("watchlist.history.session_only").format(
                epic=epic,
                candles=len({timestamp for timestamp in timestamps}),
                first=first,
                last=last,
            )
        )

    def show_paper_submission_result(self, record: object) -> None:
        self.paper_ticket_preparation.show_submission_result(record)

    def show_paper_submission_cancelled(self) -> None:
        self.paper_ticket_preparation.show_submission_cancelled()


def _change_text(row: ScannerMarketRowVM) -> str:
    if row.percent_change is None:
        return "N/A"
    prefix = "+" if row.percent_change >= 0 else ""
    return f"{prefix}{row.percent_change}%"


def _product_list_text(product: ProductRowVM) -> str:
    if product.percent_change is None:
        change = "N/A"
    else:
        prefix = "+" if product.percent_change >= 0 else ""
        change = f"{prefix}{product.percent_change}%"
    return f"{product.name}  {change}"


def _quote_from_product_row(product: ProductRowVM) -> Quote:
    observed = product.provenance.observed_at_utc
    timestamp_ms = None if observed is None else int(observed.timestamp() * 1000)
    return Quote(
        epic=product.epic,
        bid=float(product.bid) if product.bid is not None else None,
        offer=float(product.offer) if product.offer is not None else None,
        net_change=(
            float(product.net_change) if product.net_change is not None else None
        ),
        percent_change=(
            float(product.percent_change)
            if product.percent_change is not None
            else None
        ),
        market_state=product.status,
        timestamp_ms=timestamp_ms,
    )


def _tradable_product_from_row(product: ProductRowVM) -> TradableProduct:
    return TradableProduct(
        epic=product.epic,
        name=product.name,
        product_type=ProductType(product.product_type),
        direction=ProductDirection(product.direction),
        asset_class=AssetClass(product.asset_class),
        currency=product.currency,
        status=product.status,
        min_size=float(product.min_size) if product.min_size is not None else None,
        max_size=float(product.max_size) if product.max_size is not None else None,
        lot_size=float(product.lot_size) if product.lot_size is not None else None,
        ko_level=float(product.ko_level) if product.ko_level is not None else None,
        strike=float(product.strike) if product.strike is not None else None,
        bid=float(product.bid) if product.bid is not None else None,
        offer=float(product.offer) if product.offer is not None else None,
        net_change=float(product.net_change) if product.net_change is not None else None,
        percent_change=(
            float(product.percent_change)
            if product.percent_change is not None
            else None
        ),
    )


def _optional_text(value: object) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, Decimal):
        rounded = value.quantize(Decimal("0.0001"))
        return format(rounded, "f").rstrip("0").rstrip(".") or "0"
    return str(value)


def _entry_text(low: object, high: object) -> str:
    if low is None or high is None:
        return "N/A"
    return f"{_optional_text(low)} – {_optional_text(high)}"


def _datetime_text(value: datetime | None) -> str:
    if value is None:
        return "N/A"
    return value.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


def _timestamp_text(value: int) -> str:
    return datetime.fromtimestamp(value / 1000.0, tz=UTC).astimezone().strftime(
        "%Y-%m-%d %H:%M:%S %Z"
    )


def _indicator_parameters_text(parameters: tuple[str, ...]) -> str:
    if not parameters:
        return "—"
    return " · ".join(
        parameter.replace("_period:", "=").replace("period:", "P=")
        for parameter in parameters
    )


def _indicator_source_text(provenance: tuple[str, ...]) -> str:
    parts = []
    for prefix, label in (
        ("timeframe:", ""),
        ("price_basis:", ""),
        ("source:", ""),
    ):
        value = next(
            (item.removeprefix(prefix) for item in provenance if item.startswith(prefix)),
            None,
        )
        if value:
            parts.append(f"{label}{value}")
    return " · ".join(parts) or "N/A"


def _preferred_signal_row(signals: tuple[ScannerSignalVM, ...]) -> int:
    """Choose the most useful initial chart signal without changing its decision."""

    if not signals:
        return -1
    actionable = tuple(
        (index, signal)
        for index, signal in enumerate(signals)
        if signal.data_state == "ready" and signal.side in {"buy", "sell"}
    )
    ready = tuple(
        (index, signal)
        for index, signal in enumerate(signals)
        if signal.data_state == "ready"
    )
    candidates = actionable or ready or tuple(enumerate(signals))
    return max(
        candidates,
        key=lambda item: (
            item[1].confidence if item[1].confidence is not None else Decimal("-1"),
            item[1].data_quality if item[1].data_quality is not None else Decimal("-1"),
            -item[0],
        ),
    )[0]


def _indicator_snapshot_text(
    signal: ScannerSignalVM,
    language: LanguageManager,
) -> str:
    features = dict(signal.features)
    provenance_config = _provenance_config(signal.provenance)
    values: list[str] = []
    indicator_specs = (
        ("atr", "watchlist.indicators.atr", "atr_period"),
        ("rsi", "watchlist.indicators.rsi", "rsi_period"),
        ("fast_ema", "watchlist.indicators.fast_ema", "fast_ema_period"),
        ("slow_ema", "watchlist.indicators.slow_ema", "slow_ema_period"),
        ("support", "watchlist.indicators.support", "level_lookback"),
        ("resistance", "watchlist.indicators.resistance", "level_lookback"),
    )
    aliases = {"fast_ema": "ema_fast", "slow_ema": "ema_slow"}
    for feature_name, label_key, period_key in indicator_specs:
        value = features.get(feature_name, features.get(aliases.get(feature_name, "")))
        if value is None:
            continue
        period = provenance_config.get(period_key)
        label = language.text(label_key)
        if period:
            label = f"{label} {period}"
        values.append(f"{label} : {_optional_text(value)}")
    if not values:
        values.append(language.text("watchlist.indicators.none_for_signal"))
    return language.text("watchlist.indicators.snapshot_detailed").format(
        strategy=signal.strategy_id,
        values=" · ".join(values),
    )


def _provenance_config(provenance: tuple[str, ...]) -> dict[str, str]:
    config: dict[str, str] = {}
    for item in provenance:
        if not item.startswith("config:") or "=" not in item:
            continue
        key, value = item.removeprefix("config:").split("=", 1)
        config[key] = value
    return config


def _signal_overlay_levels(
    signal: ScannerSignalVM,
    language: LanguageManager,
    *,
    include_entry: bool,
    include_invalidation: bool,
    include_target: bool,
    include_structure: bool,
) -> tuple[ChartOverlayLevel, ...]:
    features = dict(signal.features)
    candidates = (
        (include_entry, "chart.overlay.entry_min", signal.entry_low, "#d7a93b", 0.62),
        (include_entry, "chart.overlay.entry_max", signal.entry_high, "#d7a93b", 0.70),
        (
            include_invalidation,
            "chart.overlay.invalidation",
            signal.invalidation,
            "#a61b1b",
            0.78,
        ),
        (include_target, "chart.overlay.target", signal.target, "#0f7b45", 0.86),
        (
            include_structure,
            "chart.overlay.support",
            features.get("support"),
            "#2ca56c",
            0.86,
        ),
        (
            include_structure,
            "chart.overlay.resistance",
            features.get("resistance"),
            "#d75a5a",
            0.94,
        ),
    )
    return tuple(
        ChartOverlayLevel(
            label=language.text(label_key),
            value=float(value),
            color=color,
            label_position=label_position,
        )
        for include, label_key, value, color, label_position in candidates
        if include and isinstance(value, Decimal)
    )


def _ema_periods_from_signal(signal: ScannerSignalVM) -> tuple[int, int] | None:
    config = _provenance_config(signal.provenance)
    try:
        fast = int(config["fast_ema_period"])
        slow = int(config["slow_ema_period"])
    except (KeyError, TypeError, ValueError):
        return None
    if fast <= 0 or slow <= fast:
        return None
    return fast, slow


def _positive_config_period(
    signal: ScannerSignalVM,
    config_key: str,
) -> int | None:
    try:
        period = int(_provenance_config(signal.provenance)[config_key])
    except (KeyError, TypeError, ValueError):
        return None
    return period if period > 0 else None


def _macd_periods_from_signal(
    signal: ScannerSignalVM,
) -> tuple[int, int, int] | None:
    config = _provenance_config(signal.provenance)
    try:
        fast = int(config["macd_fast_period"])
        slow = int(config["macd_slow_period"])
        signal_period = int(config["macd_signal_period"])
    except (KeyError, TypeError, ValueError):
        return None
    if fast <= 0 or slow <= fast or signal_period <= 0:
        return None
    return fast, slow, signal_period


def _closed_indicator_input_from_updates(
    *,
    epic: str,
    updates: tuple[ChartCandleUpdate, ...],
    interval_seconds: int,
    price_basis: ChartPriceBasis,
) -> IndicatorInput:
    """Project only the continuous, closed chart suffix used for GUI indicators."""

    buckets: dict[
        int,
        tuple[Decimal, Decimal, Decimal, Decimal, Decimal | None],
    ] = {}
    for update in sorted(
        (item for item in updates if item.timestamp_ms is not None),
        key=lambda item: int(item.timestamp_ms or 0),
    ):
        ohlc = chart_update_ohlc(update, price_basis=price_basis)
        if ohlc is None or update.timestamp_ms is None:
            continue
        bucket_ms = (
            (update.timestamp_ms // 1000 // interval_seconds) * interval_seconds * 1000
        )
        open_price, high_price, low_price, close_price = (
            Decimal(str(value)) for value in ohlc
        )
        volume = Decimal(str(update.volume)) if update.volume is not None else None
        existing = buckets.get(bucket_ms)
        if existing is None:
            buckets[bucket_ms] = (
                open_price,
                high_price,
                low_price,
                close_price,
                volume,
            )
            continue
        buckets[bucket_ms] = (
            existing[0],
            max(existing[1], high_price),
            min(existing[2], low_price),
            close_price,
            volume if volume is not None else existing[4],
        )
    ordered = sorted(buckets.items())
    closed = ordered[:-1] if ordered else []
    if closed:
        start = len(closed) - 1
        interval_ms = interval_seconds * 1000
        while start > 0 and closed[start][0] - closed[start - 1][0] == interval_ms:
            start -= 1
        closed = closed[start:]
    candles = tuple(
        AnalysisCandle(
            timestamp_utc=datetime.fromtimestamp(timestamp_ms / 1000.0, tz=UTC),
            open=values[0],
            high=values[1],
            low=values[2],
            close=values[3],
            volume=values[4],
            closed=True,
        )
        for timestamp_ms, values in closed
    )
    return IndicatorInput(
        instrument_id=epic,
        timeframe=_timeframe_for_seconds(interval_seconds),
        source="chart:watchlist-session:trailing-candle-excluded:continuous-suffix-only",
        price_basis=price_basis.value,
        candles=candles,
    )


def _chart_series_from_indicator(
    label: str,
    points: tuple[IndicatorSeriesPoint, ...],
    color: str,
) -> ChartOverlaySeries:
    return ChartOverlaySeries(
        label=label,
        points=tuple(
            (
                int(point.timestamp_utc.timestamp() * 1000),
                float(point.value),
            )
            for point in points
        ),
        color=color,
    )


def _timeframe_for_seconds(interval_seconds: int) -> str:
    if interval_seconds % 3600 == 0:
        return f"H{interval_seconds // 3600}"
    if interval_seconds % 60 == 0:
        return f"M{interval_seconds // 60}"
    return f"S{interval_seconds}"
