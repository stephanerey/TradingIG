"""V2 Scanner page with cached inventory, local filtering and bounded live quotes."""

from __future__ import annotations

import unicodedata

from PyQt5 import QtCore, QtWidgets

from trading_ig_assistant.app.projections.catalogue import (
    CatalogueVM,
    ProductRowVM,
)
from trading_ig_assistant.app.projections.scanner import ScannerVM
from trading_ig_assistant.ui.i18n.language_manager import LanguageManager
from trading_ig_assistant.ui.models.product_table_model import ProductTableModel
from trading_ig_assistant.ui.models.scanner_market_table_model import ScannerMarketTableModel
from trading_ig_assistant.ui.shell.page_specs import PAGE_SPEC_BY_KEY

_FEATURED_MARKET_ALIASES = (
    ("US Tech 100",),
    ("France 40",),
    ("Allemagne 40", "Germany 40"),
    ("Wall Street",),
    ("US 500",),
    ("FTSE 100", "UK 100"),
    ("Spot Or", "Or Spot", "Spot Gold"),
    ("Pétrole US", "US Crude", "US Oil"),
    ("EUR/USD",),
    ("GBP/USD",),
)


def _fold_catalogue_text(value: object) -> str:
    normalized = unicodedata.normalize("NFKD", str(value))
    unaccented = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return unaccented.casefold()


def _featured_product_rank(row: ProductRowVM) -> tuple[int, int] | None:
    if row.product_type not in {"barrier", "cash_or_dfb"}:
        return None
    name = _fold_catalogue_text(row.name)
    market_rank = next(
        (
            index
            for index, aliases in enumerate(_FEATURED_MARKET_ALIASES)
            if any(name.startswith(_fold_catalogue_text(alias)) for alias in aliases)
        ),
        None,
    )
    if market_rank is None:
        return None
    if "achat" in name or "buy" in name:
        product_rank = 0
    elif row.product_type == "cash_or_dfb":
        product_rank = 1
    else:
        product_rank = 2
    return market_rank, product_rank


def _prioritize_catalogue_rows(rows: tuple[ProductRowVM, ...]) -> tuple[ProductRowVM, ...]:
    """Keep one stable source order with direct major markets ahead of option chains."""

    ranked = tuple(
        (index, row, _featured_product_rank(row)) for index, row in enumerate(rows)
    )
    return tuple(
        row
        for _index, row, _rank in sorted(
            ranked,
            key=lambda item: (
                0 if item[2] is not None else 1,
                item[2] or (len(_FEATURED_MARKET_ALIASES), 0),
                item[0],
            ),
        )
    )


class _CatalogueFilterProxy(QtCore.QSortFilterProxyModel):
    """Immediate accent-insensitive local filtering without an IG request."""

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._tokens: tuple[str, ...] = ()
        self.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.setDynamicSortFilter(True)

    def set_text_filter(self, text: str) -> None:
        self._tokens = tuple(_fold_catalogue_text(text).split())
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QtCore.QModelIndex) -> bool:
        if not self._tokens:
            return True
        model = self.sourceModel()
        if not isinstance(model, ProductTableModel):
            return False
        row = model.row_at(source_row)
        if row is None:
            return False
        searchable = _fold_catalogue_text(
            " ".join(
                (
                    row.name,
                    row.epic,
                    row.product_type,
                    row.direction,
                    row.asset_class,
                    row.status or "",
                )
            )
        )
        return all(token in searchable for token in self._tokens)


class ScannerPage(QtWidgets.QWidget):
    search_requested = QtCore.pyqtSignal(str)
    stream_scope_changed = QtCore.pyqtSignal(object, int)
    market_open_requested = QtCore.pyqtSignal(str)
    product_open_requested = QtCore.pyqtSignal(object)

    def __init__(self, language: LanguageManager) -> None:
        super().__init__()
        self.setMinimumSize(0, 0)
        self.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        self._language = language
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        self.title = QtWidgets.QLabel()
        font = self.title.font()
        font.setPointSize(16)
        font.setBold(True)
        self.title.setFont(font)
        layout.addWidget(self.title)
        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setMinimumSize(0, 0)
        self.tabs.setUsesScrollButtons(True)
        self.tabs.setElideMode(QtCore.Qt.ElideRight)
        self.tabs.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        self._market_panels: list[_ScannerMarketPanel] = []
        catalogue = QtWidgets.QWidget()
        catalogue_layout = QtWidgets.QVBoxLayout(catalogue)
        controls = QtWidgets.QHBoxLayout()
        self.query = QtWidgets.QLineEdit()
        self.search_button = QtWidgets.QPushButton()
        self.follow_button = QtWidgets.QPushButton()
        self.follow_button.setEnabled(False)
        self.search_button.clicked.connect(lambda: self.search_requested.emit(self.query.text()))
        self.query.returnPressed.connect(lambda: self.search_requested.emit(self.query.text()))
        self.query.textChanged.connect(self._on_filter_changed)
        self.follow_button.clicked.connect(self._open_selected_product)
        controls.addWidget(self.query, stretch=1)
        controls.addWidget(self.search_button)
        controls.addWidget(self.follow_button)
        catalogue_layout.addLayout(controls)
        self.status = QtWidgets.QLabel()
        catalogue_layout.addWidget(self.status)
        self.stream_status = QtWidgets.QLabel()
        self.stream_status.setWordWrap(True)
        catalogue_layout.addWidget(self.stream_status)
        self.model = ProductTableModel(language)
        self.proxy = _CatalogueFilterProxy(self)
        self.proxy.setSourceModel(self.model)
        self.table = QtWidgets.QTableView()
        self.table.setMinimumSize(0, 0)
        self.table.setModel(self.proxy)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(-1, QtCore.Qt.AscendingOrder)
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setMinimumSectionSize(24)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        header.resizeSection(0, 30)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Interactive)
        header.resizeSection(1, 320)
        self.table.verticalScrollBar().valueChanged.connect(self._schedule_stream_scope)
        self.table.viewport().installEventFilter(self)
        self.table.doubleClicked.connect(self._open_product)
        self.table.selectionModel().selectionChanged.connect(
            lambda _selected, _deselected: self.follow_button.setEnabled(
                self._selected_epic() is not None
            )
        )
        catalogue_layout.addWidget(self.table, stretch=1)
        self.tabs.addTab(catalogue, "")
        for mode in ("all", "long", "short", "watch"):
            panel = _ScannerMarketPanel(language, mode)
            panel.market_open_requested.connect(self.market_open_requested)
            self._market_panels.append(panel)
            self.tabs.addTab(panel, "")
        layout.addWidget(self.tabs, stretch=1)
        self._snapshot: CatalogueVM | None = None
        self._catalogue_source_epics: tuple[str, ...] = ()
        self._catalogue_display_epics: tuple[str, ...] = ()
        self._scanner_snapshot: ScannerVM | None = None
        self._stream_state = "disconnected"
        self._stream_subscribed = 0
        self._stream_total = 0
        self._stream_priority = 0
        self._stream_scope_active = False
        self._scope_timer = QtCore.QTimer(self)
        self._scope_timer.setSingleShot(True)
        self._scope_timer.setInterval(250)
        self._scope_timer.timeout.connect(self._emit_stream_scope)
        self.proxy.layoutChanged.connect(self._schedule_stream_scope)
        self.retranslate_ui()

    def set_snapshot(self, snapshot: CatalogueVM) -> None:
        selected_epic = self._selected_epic()
        self._snapshot = snapshot
        source_epics = tuple(row.epic for row in snapshot.rows)
        if source_epics != self._catalogue_source_epics:
            display_rows = _prioritize_catalogue_rows(snapshot.rows)
            self._catalogue_source_epics = source_epics
            self._catalogue_display_epics = tuple(row.epic for row in display_rows)
        else:
            by_epic = {row.epic: row for row in snapshot.rows}
            display_rows = tuple(
                by_epic[epic]
                for epic in self._catalogue_display_epics
                if epic in by_epic
            )
        self.model.set_rows(display_rows)
        if selected_epic is not None:
            row = self.model.row_for_epic(selected_epic)
            if row is not None:
                source_index = self.model.index(row, 0)
                proxy_index = self.proxy.mapFromSource(source_index)
                if proxy_index.isValid():
                    self.table.selectRow(proxy_index.row())
        self._render_catalogue_status()
        self._schedule_stream_scope()

    def set_stream_scope_active(self, active: bool) -> None:
        """Request visible catalogue quotes only while the Scanner page is active."""

        normalized = bool(active)
        if normalized == self._stream_scope_active:
            return
        self._stream_scope_active = normalized
        if normalized:
            self._schedule_stream_scope()
            return
        self._scope_timer.stop()
        self.stream_scope_changed.emit((), self.proxy.rowCount())

    def set_scanner_snapshot(self, snapshot: ScannerVM) -> None:
        self._scanner_snapshot = snapshot
        for panel in self._market_panels:
            panel.set_snapshot(snapshot)

    def _render_catalogue_status(self) -> None:
        snapshot = self._snapshot
        if snapshot is None or not snapshot.rows:
            self.status.setText(self._language.text("catalogue.empty"))
            return
        visible = self.proxy.rowCount()
        if snapshot.kind == "inventory":
            self.status.setText(
                self._language.text("catalogue.inventory").format(
                    count=len(snapshot.rows),
                    visible=visible,
                    timestamp=snapshot.generated_at_utc.strftime("%H:%M:%S UTC"),
                )
            )
            return
        self.status.setText(
            self._language.text("catalogue.results").format(
                count=len(snapshot.rows),
                visible=visible,
                query=snapshot.query or "",
                timestamp=snapshot.generated_at_utc.strftime("%H:%M:%S UTC"),
            )
        )

    def set_busy(self, busy: bool) -> None:
        self.search_button.setEnabled(not busy)
        self.query.setEnabled(not busy)

    def set_stream_coverage(
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
        self._render_stream_state()

    @QtCore.pyqtSlot(str)
    def _on_filter_changed(self, text: str) -> None:
        self.proxy.set_text_filter(text)
        self._render_catalogue_status()
        self._schedule_stream_scope()

    @QtCore.pyqtSlot()
    def _schedule_stream_scope(self) -> None:
        if not self._stream_scope_active:
            return
        # Live catalogue ticks can arrive more often than this timer interval.  Restarting the
        # single-shot timer for every model refresh postpones scope publication forever, leaving
        # only already-followed products subscribed.  Keep the first pending publication and let
        # subsequent ticks be covered by the next scope calculation.
        if not self._scope_timer.isActive():
            self._scope_timer.start()

    @QtCore.pyqtSlot()
    def _emit_stream_scope(self) -> None:
        if not self._stream_scope_active:
            return
        count = self.proxy.rowCount()
        if count == 0:
            self.stream_scope_changed.emit((), 0)
            return
        first = self.table.rowAt(0)
        first = 0 if first < 0 else first
        last = min(count, first + 40)
        epics = tuple(
            str(self.proxy.index(row, 0).data(QtCore.Qt.UserRole) or "")
            for row in range(first, last)
        )
        self.stream_scope_changed.emit(epics, count)

    def _selected_epic(self) -> str | None:
        rows = self.table.selectionModel().selectedRows()
        return str(rows[0].data(QtCore.Qt.UserRole)) if rows else None

    @QtCore.pyqtSlot(QtCore.QModelIndex)
    def _open_product(self, index: QtCore.QModelIndex) -> None:
        source = self.proxy.mapToSource(index)
        row = self.model.row_at(source.row())
        if row is not None:
            self.product_open_requested.emit(row)

    @QtCore.pyqtSlot()
    def _open_selected_product(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if rows:
            self._open_product(rows[0])

    def _render_stream_state(self) -> None:
        state_key = f"stream.short.{self._stream_state}"
        state = self._language.text(state_key)
        if state == state_key:
            state = self._stream_state
        self.stream_status.setText(
            self._language.text("stream.coverage").format(
                state=state,
                subscribed=self._stream_subscribed,
                total=self._stream_total,
                priority=self._stream_priority,
            )
        )

    def eventFilter(self, watched: object, event: QtCore.QEvent) -> bool:
        if watched is self.table.viewport() and event.type() in {
            QtCore.QEvent.Resize,
            QtCore.QEvent.Show,
        }:
            self._schedule_stream_scope()
        return super().eventFilter(watched, event)

    def retranslate_ui(self) -> None:
        self.title.setText(self._language.text("nav.scanner"))
        spec = PAGE_SPEC_BY_KEY["scanner"]
        for index, key in enumerate(spec.tab_keys):
            self.tabs.setTabText(index, self._language.text(key))
        for panel in self._market_panels:
            panel.retranslate_ui()
        self.query.setPlaceholderText(self._language.text("catalogue.query_placeholder"))
        self.search_button.setText(self._language.text("catalogue.search"))
        self.follow_button.setText(self._language.text("catalogue.follow"))
        self._render_stream_state()
        self.model.retranslate_ui()


class _ScannerFilterProxy(QtCore.QSortFilterProxyModel):
    def __init__(self, mode: str, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._mode = mode

    def filterAcceptsRow(self, source_row: int, source_parent: QtCore.QModelIndex) -> bool:
        model = self.sourceModel()
        if not isinstance(model, ScannerMarketTableModel):
            return False
        row = model.rows[source_row]
        if self._mode == "all":
            return True
        if self._mode == "long":
            return row.signal_direction == "bullish" and row.recommendation == "candidate"
        if self._mode == "short":
            return row.signal_direction == "bearish" and row.recommendation == "candidate"
        return row.recommendation in {"watch", "unavailable"}


class _ScannerMarketPanel(QtWidgets.QWidget):
    market_open_requested = QtCore.pyqtSignal(str)

    def __init__(self, language: LanguageManager, mode: str) -> None:
        super().__init__()
        self._language = language
        self._mode = mode
        self._snapshot: ScannerVM | None = None
        layout = QtWidgets.QVBoxLayout(self)
        self.status = QtWidgets.QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.model = ScannerMarketTableModel(language)
        self.proxy = _ScannerFilterProxy(mode, self)
        self.proxy.setSourceModel(self.model)
        self.table = QtWidgets.QTableView()
        self.table.setModel(self.proxy)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSortingEnabled(True)
        self.table.doubleClicked.connect(self._open_market)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().resizeSection(0, 190)
        layout.addWidget(self.table, stretch=1)

    def set_snapshot(self, snapshot: ScannerVM) -> None:
        self._snapshot = snapshot
        self.model.set_rows(snapshot.rows)
        self.proxy.invalidateFilter()
        self._render_status()

    def retranslate_ui(self) -> None:
        self.model.retranslate_ui()
        self._render_status()

    def _render_status(self) -> None:
        snapshot = self._snapshot
        if snapshot is None:
            self.status.setText(self._language.text("scanner.status.unavailable"))
            return
        self.status.setText(
            self._language.text("scanner.status.summary").format(
                visible=self.proxy.rowCount(),
                configured=len(snapshot.rows),
                state=snapshot.availability.value.upper(),
                timestamp=snapshot.generated_at_utc.strftime("%H:%M:%S UTC"),
            )
        )

    @QtCore.pyqtSlot(QtCore.QModelIndex)
    def _open_market(self, index: QtCore.QModelIndex) -> None:
        source = self.proxy.mapToSource(index)
        epic = self.model.data(source, QtCore.Qt.UserRole + 1)
        if epic:
            self.market_open_requested.emit(str(epic))
