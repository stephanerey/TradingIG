"""Product selector with market details and a paper-only ticket proposal."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets

from trading_ig_assistant.domain.ai_context import MarketContextSnapshot
from trading_ig_assistant.domain.analysis import ScoreBand, StrategySignal
from trading_ig_assistant.domain.macro_context import MacroRibbonState
from trading_ig_assistant.domain.market_data import QUOTE_FRESHNESS_SECONDS, Quote
from trading_ig_assistant.domain.market_navigation import IGProductMarketBinding
from trading_ig_assistant.domain.products import (
    AssetClass,
    ProductDirection,
    ProductType,
    TradableProduct,
)
from trading_ig_assistant.services.product_context_projection_service import (
    ProductContextLevel,
    ProductContextProjection,
    ProductContextProjectionService,
)
from trading_ig_assistant.services.product_discovery_service import ProductDiscoveryResult
from trading_ig_assistant.ui.score_palette import SCORE_BAND_COLORS
from trading_ig_assistant.ui.ticket_view import PaperTicketWidget

PRODUCT_COLUMNS = [
    "Name",
    "Vente",
    "Achat",
    "Variation",
    "% Variation",
    "Direction",
    "Contexte",
    "Epic",
    "Type",
    "Expiry",
    "Status",
    "Currency",
    "KO",
    "Strike",
]

PRODUCT_CONTEXT_COLUMN = 6
OPTION_CHANGE_TOOLTIP = (
    "Variation indisponible : la signification des données IG pour cette option n'est pas vérifiée."
)
SNAPSHOT_QUOTE_TOOLTIP = "Snapshot de découverte IG : la fraîcheur n'est pas vérifiée."
SESSION_QUOTE_TOOLTIP = "Dernière cotation reçue en session : la fraîcheur n'est pas vérifiée ici."
PRODUCT_CONTEXT_COLORS = {
    level: SCORE_BAND_COLORS[band]
    for level, band in {
        ProductContextLevel.CATALYST: ScoreBand.EXCEPTIONAL,
        ProductContextLevel.ALIGNED: ScoreBand.FAVORABLE,
        ProductContextLevel.CAUTION: ScoreBand.CAUTION,
        ProductContextLevel.UNFAVORABLE: ScoreBand.UNFAVORABLE,
        ProductContextLevel.UNKNOWN: ScoreBand.UNKNOWN,
    }.items()
}

PRODUCT_TYPE_TABS: list[tuple[str, str]] = [
    ("all", "Tous"),
    (ProductType.BARRIER.value, "Barrières"),
    (ProductType.OPTION.value, "Options"),
    ("other", "Autres"),
]

ASSET_CLASS_TABS: list[tuple[str, str]] = [
    ("all", "Tous"),
    (AssetClass.INDICES.value, "Indices"),
    (AssetClass.FOREX.value, "Forex"),
    (AssetClass.COMMODITIES.value, "Matières premières"),
    (AssetClass.CRYPTO.value, "Crypto-monnaies"),
    (AssetClass.SHARES.value, "Actions"),
    (AssetClass.OTHER.value, "Autres"),
]


class ProductSelectorWidget(QtWidgets.QWidget):
    discover_requested = QtCore.pyqtSignal(object)
    targeted_search_requested = QtCore.pyqtSignal(str)
    export_requested = QtCore.pyqtSignal(object)
    product_selected = QtCore.pyqtSignal(object)
    visible_epics_changed = QtCore.pyqtSignal(object)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._results: list[ProductDiscoveryResult] = []
        self._filter_text = ""
        self._tables: dict[tuple[str, str], QtWidgets.QTableWidget] = {}
        self._asset_tabs: list[QtWidgets.QTabWidget] = []
        self._rows_by_epic: dict[str, list[tuple[QtWidgets.QTableWidget, int]]] = {}
        self._live_quotes: dict[str, Quote] = {}
        self._live_quote_received_at: dict[str, datetime] = {}
        self._selected_product: TradableProduct | None = None
        self._macro_state: MacroRibbonState | None = None
        self._ai_context_snapshot: MarketContextSnapshot | None = None
        self._market_bindings: dict[str, IGProductMarketBinding] = {}
        self._qualified_event_signals: dict[str, StrategySignal] = {}
        self._context_service = ProductContextProjectionService()
        layout = QtWidgets.QVBoxLayout(self)
        self.main_layout = layout

        title = QtWidgets.QLabel("Product discovery")
        title.setStyleSheet("font-weight: 700; font-size: 15px;")

        controls = QtWidgets.QHBoxLayout()
        self.filter_box = QtWidgets.QLineEdit()
        self.filter_box.setPlaceholderText("Filter displayed products")
        self.filter_box.textChanged.connect(self._apply_filter)
        self.tradeable_only_box = QtWidgets.QCheckBox("Tradeable only")
        self.tradeable_only_box.toggled.connect(lambda _checked: self._render_table())
        self.discover_button = QtWidgets.QPushButton("Discover all products")
        self.targeted_search_button = QtWidgets.QPushButton("Rechercher sur IG")
        self.targeted_search_button.setToolTip(
            "Recherche IG explicite avec le texte du filtre : une requête, "
            "sans détails par produit."
        )
        self.export_button = QtWidgets.QPushButton("Export report")
        self.export_button.setEnabled(False)
        self.discover_button.clicked.connect(self._emit_discover_requested)
        self.targeted_search_button.clicked.connect(
            lambda: self.targeted_search_requested.emit(self.filter_box.text().strip())
        )
        self.export_button.clicked.connect(self._emit_export_requested)
        controls.addWidget(self.filter_box, stretch=1)
        controls.addWidget(self.tradeable_only_box)
        controls.addWidget(self.discover_button)
        controls.addWidget(self.targeted_search_button)
        controls.addWidget(self.export_button)

        self.summary_label = QtWidgets.QLabel("No product discovery run yet.")
        self.summary_label.setWordWrap(True)

        self.product_tabs = QtWidgets.QTabWidget()
        self.product_table = self._build_product_tabs()

        self.market_summary = QtWidgets.QTextEdit()
        self.market_summary.setReadOnly(True)
        self.market_summary.setPlainText("Select a product to see market details.")
        self.market_summary.setMinimumSize(0, 0)
        self.market_summary.setSizePolicy(
            QtWidgets.QSizePolicy.Ignored,
            QtWidgets.QSizePolicy.Ignored,
        )

        self.paper_ticket = PaperTicketWidget()
        self.ticket_summary = self.paper_ticket.summary
        self.trade_button = self.paper_ticket.evaluate_button
        self.details_tabs = QtWidgets.QTabWidget()
        self.details_tabs.setMinimumSize(0, 0)
        self.details_tabs.setSizePolicy(
            QtWidgets.QSizePolicy.Ignored,
            QtWidgets.QSizePolicy.Ignored,
        )
        self.details_tabs.addTab(self.market_summary, "Marché")
        self.details_tabs.addTab(self.paper_ticket, "Simulation")
        self.details_tabs.currentChanged.connect(self._on_details_tab_changed)

        layout.addWidget(title)
        layout.addLayout(controls)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.product_tabs, stretch=2)
        layout.addWidget(self.details_tabs, stretch=1)

    @QtCore.pyqtSlot(int)
    def _on_details_tab_changed(self, index: int) -> None:
        ticket_visible = index == 1
        self.product_tabs.setVisible(not ticket_visible)
        self.main_layout.setStretchFactor(self.product_tabs, 1 if ticket_visible else 2)
        self.main_layout.setStretchFactor(self.details_tabs, 2 if ticket_visible else 1)

    def set_busy(self, busy: bool) -> None:
        self.discover_button.setEnabled(not busy)
        self.targeted_search_button.setEnabled(not busy)
        self.export_button.setEnabled(bool(self._results) and not busy)
        if busy:
            self.summary_label.setText("Discovering IG products in read-only mode...")

    def set_results(self, results: list[ProductDiscoveryResult]) -> None:
        self._results = list(results)
        self._rows_by_epic.clear()
        self._render_table()
        self.export_button.setEnabled(bool(self._results))

    def _render_table(self) -> None:
        self._rows_by_epic.clear()
        all_rows = [
            (result.search_term, product)
            for result in self._results
            for product in result.products
            if self._matches_filter(product)
        ]
        for (product_type_filter, asset_class_filter), table in self._tables.items():
            rows = [
                row
                for row in all_rows
                if _matches_product_type(row[1], product_type_filter)
                and _matches_asset_class(row[1], asset_class_filter)
            ]
            self._fill_table(table, rows)

        total_product_count = sum(len(result.products) for result in self._results)
        candidate_count = sum(result.candidates_count for result in self._results)
        error_count = sum(len(result.errors) for result in self._results)
        self.summary_label.setText(
            f"Discovery complete: {candidate_count} candidates, "
            f"{total_product_count} products, {len(all_rows)} displayed, {error_count} errors. "
            "If market navigation is unavailable, search fallback is used. Detailed EPIC metadata "
            "is not bulk-fetched to avoid IG token rejection."
        )
        self._render_market_summary()
        self.visible_epics_changed.emit(self.visible_price_epics())

    def results(self) -> list[ProductDiscoveryResult]:
        return list(self._results)

    def visible_price_epics(self, max_items: int = 80) -> list[str]:
        table = self._active_table()
        if table is None:
            return []
        epics: list[str] = []
        for row_index in range(table.rowCount()):
            item = table.item(row_index, 0)
            if item is None:
                continue
            product = item.data(QtCore.Qt.UserRole)
            if not isinstance(product, TradableProduct):
                continue
            if not product.epic or product.epic in epics:
                continue
            epics.append(product.epic)
            if len(epics) >= max_items:
                break
        return epics

    def set_selected_product(self, product: TradableProduct | None) -> None:
        self._selected_product = product
        self.paper_ticket.set_product(product)
        self._render_market_summary()

    def set_chart_source(self, product: TradableProduct | None) -> None:
        self.paper_ticket.set_chart_source(product)

    def set_market_context(
        self,
        state: MacroRibbonState,
        ai_snapshot: MarketContextSnapshot | None = None,
        qualified_event_signals: Mapping[str, StrategySignal] | None = None,
    ) -> None:
        """Refresh per-row context without changing the active filters or selection."""

        self._macro_state = state
        self._ai_context_snapshot = ai_snapshot
        self._qualified_event_signals = dict(qualified_event_signals or {})
        for table in self._tables.values():
            for row_index in range(table.rowCount()):
                item = table.item(row_index, 0)
                product = item.data(QtCore.Qt.UserRole) if item is not None else None
                if isinstance(product, TradableProduct):
                    self._set_context_cell(table, row_index, product)
        self._render_market_summary()

    def set_market_bindings(self, bindings: tuple[IGProductMarketBinding, ...]) -> None:
        self._market_bindings = {binding.product_epic: binding for binding in bindings}
        if self._macro_state is not None:
            self.set_market_context(
                self._macro_state, self._ai_context_snapshot, self._qualified_event_signals
            )

    def set_live_quote(self, quote: Quote | None) -> None:
        if quote is None:
            return
        self._live_quotes[quote.epic] = quote
        self._live_quote_received_at[quote.epic] = datetime.now(UTC)
        for table, row_index in self._rows_by_epic.get(quote.epic, []):
            self._set_table_value(table, row_index, 1, _format_number(quote.bid))
            self._set_table_value(table, row_index, 2, _format_number(quote.offer))
            for column_index in (1, 2):
                table.item(row_index, column_index).setToolTip(SESSION_QUOTE_TOOLTIP)
            item = table.item(row_index, 0)
            product = item.data(QtCore.Qt.UserRole) if item is not None else None
            is_option = (
                isinstance(product, TradableProduct) and product.product_type is ProductType.OPTION
            )
            self._set_table_value(
                table, row_index, 3, "-" if is_option else _format_signed_number(quote.net_change)
            )
            self._set_table_value(
                table,
                row_index,
                4,
                "-" if is_option else _format_signed_number(quote.percent_change),
            )
        if self._selected_product is not None and self._selected_product.epic == quote.epic:
            self.paper_ticket.set_quote(quote)
            self._render_market_summary()

    def live_quote_for_epic(self, epic: str) -> Quote | None:
        """Return the latest session quote without falling back to discovery snapshots."""

        return self._live_quotes.get(epic)

    def fresh_live_quote_for_epic(self, epic: str, *, now: datetime) -> Quote | None:
        """Return a non-delayed session quote only within the existing freshness window."""
        quote = self._live_quotes.get(epic)
        received_at = self._live_quote_received_at.get(epic)
        if quote is None or received_at is None or quote.delayed is True:
            return None
        age = (now - received_at).total_seconds()
        return quote if 0 <= age <= QUOTE_FRESHNESS_SECONDS else None

    def clear_live_quotes(self) -> None:
        """Invalidate quotes from a previous connection or account."""
        self._live_quotes.clear()
        self._live_quote_received_at.clear()
        self.paper_ticket.set_quote(None)
        for entries in self._rows_by_epic.values():
            for table, row_index in entries:
                for column_index in (1, 2, 3, 4):
                    self._set_table_value(table, row_index, column_index, "-")
                for column_index in (1, 2):
                    table.item(row_index, column_index).setToolTip("Cotation de session invalidée.")
        self._render_market_summary()

    def _emit_discover_requested(self) -> None:
        self.discover_requested.emit(None)

    def _apply_filter(self, text: str) -> None:
        self._filter_text = text.strip().lower()
        self._render_table()

    def _matches_filter(self, product: object) -> bool:
        if not self._filter_text:
            return self._matches_status_filter(product)
        fields = [
            getattr(product, "name", ""),
            getattr(product, "epic", ""),
            getattr(getattr(product, "product_type", ""), "value", ""),
            getattr(getattr(product, "direction", ""), "value", ""),
            getattr(product, "expiry", ""),
            getattr(product, "status", ""),
            getattr(product, "currency", ""),
            getattr(getattr(product, "asset_class", ""), "value", ""),
            getattr(product, "bid", ""),
            getattr(product, "offer", ""),
            getattr(product, "net_change", ""),
            getattr(product, "percent_change", ""),
        ]
        return self._filter_text in " ".join(
            str(field).lower() for field in fields
        ) and self._matches_status_filter(product)

    def _matches_status_filter(self, product: object) -> bool:
        if not self.tradeable_only_box.isChecked():
            return True
        return str(getattr(product, "status", "")).upper() == "TRADEABLE"

    def _build_product_tabs(self) -> QtWidgets.QTableWidget:
        first_table: QtWidgets.QTableWidget | None = None
        for product_type_key, product_type_label in PRODUCT_TYPE_TABS:
            asset_tabs = QtWidgets.QTabWidget()
            for asset_key, asset_label in ASSET_CLASS_TABS:
                table = _create_product_table()
                self._tables[(product_type_key, asset_key)] = table
                table.itemSelectionChanged.connect(
                    lambda table=table: self._emit_selected_product(table)
                )
                if first_table is None:
                    first_table = table
                asset_tabs.addTab(table, asset_label)
            asset_tabs.currentChanged.connect(lambda _index: self._emit_visible_epics_changed())
            self._asset_tabs.append(asset_tabs)
            self.product_tabs.addTab(asset_tabs, product_type_label)
        self.product_tabs.currentChanged.connect(lambda _index: self._emit_visible_epics_changed())
        if first_table is None:
            raise RuntimeError("Product table initialization failed.")
        return first_table

    def _fill_table(
        self,
        table: QtWidgets.QTableWidget,
        rows: list[tuple[str, TradableProduct]],
    ) -> None:
        table.setRowCount(len(rows))
        for row_index, (_search_term, product) in enumerate(rows):
            session_quote = self._live_quotes.get(product.epic)
            displayed_quote = session_quote if session_quote is not None else product
            values = [
                product.name,
                _format_number(displayed_quote.bid),
                _format_number(displayed_quote.offer),
                "-"
                if product.product_type is ProductType.OPTION
                else _format_signed_number(displayed_quote.net_change),
                "-"
                if product.product_type is ProductType.OPTION
                else _format_signed_number(displayed_quote.percent_change),
                _display_product_direction(product),
                "",
                product.epic,
                product.product_type.value,
                product.expiry or "",
                product.status or "",
                product.currency or "",
                _format_number(product.ko_level),
                _format_number(product.strike),
            ]
            for column_index, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                if column_index == 0:
                    item.setData(QtCore.Qt.UserRole, product)
                if column_index in {1, 2, 3, 4, 12, 13}:
                    item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                if column_index in {3, 4} and product.product_type is ProductType.OPTION:
                    item.setToolTip(OPTION_CHANGE_TOOLTIP)
                if column_index == 5 and product.direction is ProductDirection.UNKNOWN:
                    item.setToolTip(
                        "Exposition déduite du nom affiché si indiqué ; "
                        "elle ne confirme ni les métadonnées IG ni le sens d'un ordre."
                    )
                if column_index in {1, 2}:
                    item.setToolTip(
                        SESSION_QUOTE_TOOLTIP
                        if session_quote is not None
                        else SNAPSHOT_QUOTE_TOOLTIP
                    )
                table.setItem(row_index, column_index, item)
            self._set_context_cell(table, row_index, product)
            if product.epic:
                self._rows_by_epic.setdefault(product.epic, []).append((table, row_index))
        table.resizeColumnsToContents()

    def _emit_export_requested(self) -> None:
        default_path = str(Path.home() / "trading_ig_product_discovery.local.json")
        output_path, _selected_filter = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export sanitized product discovery report",
            default_path,
            "JSON files (*.json)",
        )
        if output_path:
            self.export_requested.emit(Path(output_path))

    def _emit_selected_product(self, table: QtWidgets.QTableWidget) -> None:
        current_row = table.currentRow()
        if current_row < 0:
            return
        item = table.item(current_row, 0)
        if item is None:
            return
        product = item.data(QtCore.Qt.UserRole)
        if product is not None:
            self.set_selected_product(product)
            self.product_selected.emit(product)

    def _emit_visible_epics_changed(self) -> None:
        self.visible_epics_changed.emit(self.visible_price_epics())

    def _active_table(self) -> QtWidgets.QTableWidget | None:
        asset_tabs = self.product_tabs.currentWidget()
        if not isinstance(asset_tabs, QtWidgets.QTabWidget):
            return None
        table = asset_tabs.currentWidget()
        if not isinstance(table, QtWidgets.QTableWidget):
            return None
        return table

    def _render_market_summary(self) -> None:
        product = self._selected_product
        if product is None:
            self.market_summary.setPlainText("Select a product to see market details.")
            return
        quote = self._live_quotes.get(product.epic)
        lines = [
            f"Name: {product.name}",
            f"Epic: {product.epic}",
            f"Type: {product.product_type.value}",
            f"Direction: {product.direction.value}",
            f"Expiry: {product.expiry or '-'}",
            f"Status: {product.status or '-'}",
            f"Currency: {product.currency or '-'}",
            f"KO: {_format_number(product.ko_level)}",
            f"Strike: {_format_number(product.strike)}",
            f"Min size: {_format_number(product.min_size)}",
            f"Max size: {_format_number(product.max_size)}",
            f"Lot size: {_format_number(product.lot_size)}",
            "",
            f"Snapshot vente: {_format_number(product.bid)}",
            f"Snapshot achat: {_format_number(product.offer)}",
            f"Snapshot variation: {_display_product_change(product, product.net_change)}",
            f"Snapshot % variation: {_display_product_change(product, product.percent_change)}",
        ]
        projection = self._project_context(product)
        if projection is not None:
            lines.extend(
                [
                    "",
                    f"Contexte agrégé: {projection.compact_text}",
                    "Contexte indicatif uniquement — ni recommandation, ni probabilité.",
                ]
            )
        if quote is not None:
            lines.extend(
                [
                    "",
                    f"Live vente: {_format_number(quote.bid)}",
                    f"Live achat: {_format_number(quote.offer)}",
                    f"Live variation: {_display_product_change(product, quote.net_change)}",
                    f"Live % variation: {_display_product_change(product, quote.percent_change)}",
                    f"Live market state: {quote.market_state or '-'}",
                ]
            )
        self.market_summary.setPlainText("\n".join(lines))

    def _project_context(self, product: TradableProduct) -> ProductContextProjection | None:
        if self._macro_state is None:
            return None
        return self._context_service.project(
            product,
            self._macro_state,
            evaluated_at_utc=datetime.now(UTC),
            ai_snapshot=self._ai_context_snapshot,
            qualified_event_signal=self._qualified_event_signals.get(product.epic),
            ai_reference_binding=self._market_bindings.get(product.epic),
        )

    def _set_context_cell(
        self,
        table: QtWidgets.QTableWidget,
        row_index: int,
        product: TradableProduct,
    ) -> None:
        projection = self._project_context(product)
        item = table.item(row_index, PRODUCT_CONTEXT_COLUMN)
        if item is None:
            item = QtWidgets.QTableWidgetItem()
            table.setItem(row_index, PRODUCT_CONTEXT_COLUMN, item)
        if projection is None:
            item.setText("INCONNU | contexte non initialisé")
            item.setToolTip("Contexte indisponible.")
            level = ProductContextLevel.UNKNOWN
        else:
            item.setText(projection.compact_text)
            item.setToolTip(projection.tooltip)
            level = projection.level
        foreground, background = PRODUCT_CONTEXT_COLORS[level]
        item.setForeground(QtGui.QBrush(QtGui.QColor(foreground)))
        item.setBackground(QtGui.QBrush(QtGui.QColor(background)))
        item.setData(QtCore.Qt.AccessibleTextRole, f"Contexte produit {level.value}")

    def _set_table_value(
        self,
        table: QtWidgets.QTableWidget,
        row_index: int,
        column_index: int,
        value: str,
    ) -> None:
        item = table.item(row_index, column_index)
        if item is None:
            item = QtWidgets.QTableWidgetItem()
            table.setItem(row_index, column_index, item)
        item.setText(value)


def _format_number(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:g}"


def _format_signed_number(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:g}"


def _display_product_change(product: TradableProduct, value: float | None) -> str:
    if product.product_type is ProductType.OPTION:
        return "indisponible (signification IG non vérifiée)"
    return _format_signed_number(value)


def _create_product_table() -> QtWidgets.QTableWidget:
    table = QtWidgets.QTableWidget(0, len(PRODUCT_COLUMNS))
    table.setHorizontalHeaderLabels(PRODUCT_COLUMNS)
    table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
    table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
    table.horizontalHeader().setStretchLastSection(True)
    return table


def _matches_product_type(product: TradableProduct, product_type_filter: str) -> bool:
    if product_type_filter == "all":
        return True
    if product_type_filter == "other":
        return product.product_type not in {ProductType.BARRIER, ProductType.OPTION}
    return product.product_type.value == product_type_filter


def _display_product_direction(product: TradableProduct) -> str:
    if product.direction is not ProductDirection.UNKNOWN:
        return product.direction.value
    if product.product_type is ProductType.BARRIER:
        name = product.name.strip().casefold()
        if name.endswith(("barrières achat", "barrière achat")):
            return "haussière (nom)"
        if name.endswith(("barrières vente", "barrière vente")):
            return "baissière (nom)"
    return product.direction.value


def _matches_asset_class(product: TradableProduct, asset_class_filter: str) -> bool:
    if asset_class_filter == "all":
        return True
    return product.asset_class.value == asset_class_filter
