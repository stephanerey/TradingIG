"""Thin product selector and ticket placeholder panel."""

from __future__ import annotations

from pathlib import Path

from PyQt5 import QtCore, QtWidgets

from trading_ig_assistant.domain.market_data import Quote
from trading_ig_assistant.domain.products import AssetClass, ProductType, TradableProduct
from trading_ig_assistant.services.product_discovery_service import ProductDiscoveryResult

PRODUCT_COLUMNS = [
    "Name",
    "Vente",
    "Achat",
    "Variation",
    "% Variation",
    "Direction",
    "Epic",
    "Type",
    "Expiry",
    "Status",
    "Currency",
    "KO",
    "Strike",
]

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
    export_requested = QtCore.pyqtSignal(object)
    product_selected = QtCore.pyqtSignal(object)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._results: list[ProductDiscoveryResult] = []
        self._filter_text = ""
        self._tables: dict[tuple[str, str], QtWidgets.QTableWidget] = {}
        self._rows_by_epic: dict[str, list[tuple[QtWidgets.QTableWidget, int]]] = {}
        self._live_quotes: dict[str, Quote] = {}
        self._selected_product: TradableProduct | None = None
        layout = QtWidgets.QVBoxLayout(self)

        title = QtWidgets.QLabel("Product discovery")
        title.setStyleSheet("font-weight: 700; font-size: 15px;")

        controls = QtWidgets.QHBoxLayout()
        self.filter_box = QtWidgets.QLineEdit()
        self.filter_box.setPlaceholderText("Filter displayed products")
        self.filter_box.textChanged.connect(self._apply_filter)
        self.tradeable_only_box = QtWidgets.QCheckBox("Tradeable only")
        self.tradeable_only_box.toggled.connect(lambda _checked: self._render_table())
        self.discover_button = QtWidgets.QPushButton("Discover all products")
        self.export_button = QtWidgets.QPushButton("Export report")
        self.export_button.setEnabled(False)
        self.discover_button.clicked.connect(self._emit_discover_requested)
        self.export_button.clicked.connect(self._emit_export_requested)
        controls.addWidget(self.filter_box, stretch=1)
        controls.addWidget(self.tradeable_only_box)
        controls.addWidget(self.discover_button)
        controls.addWidget(self.export_button)

        self.summary_label = QtWidgets.QLabel("No product discovery run yet.")
        self.summary_label.setWordWrap(True)

        self.product_tabs = QtWidgets.QTabWidget()
        self.product_table = self._build_product_tabs()

        market_title = QtWidgets.QLabel("Market details")
        market_title.setStyleSheet("font-weight: 700; font-size: 15px; margin-top: 12px;")

        self.market_summary = QtWidgets.QTextEdit()
        self.market_summary.setReadOnly(True)
        self.market_summary.setMinimumHeight(140)
        self.market_summary.setPlainText("Select a product to see market details.")

        ticket_title = QtWidgets.QLabel("Ticket placeholder")
        ticket_title.setStyleSheet("font-weight: 700; font-size: 15px; margin-top: 12px;")

        self.ticket_summary = QtWidgets.QTextEdit()
        self.ticket_summary.setReadOnly(True)
        self.ticket_summary.setPlainText(
            "Ticket builder is not implemented in P01.\n"
            "No order execution path exists in the GUI."
        )

        self.trade_button = QtWidgets.QPushButton("Trade - not implemented")
        self.trade_button.setEnabled(False)

        layout.addWidget(title)
        layout.addLayout(controls)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.product_tabs, stretch=1)
        layout.addWidget(market_title)
        layout.addWidget(self.market_summary)
        layout.addWidget(ticket_title)
        layout.addWidget(self.ticket_summary)
        layout.addWidget(self.trade_button)

    def set_busy(self, busy: bool) -> None:
        self.discover_button.setEnabled(not busy)
        self.export_button.setEnabled(bool(self._results) and not busy)
        if busy:
            self.summary_label.setText(
                "Discovering IG products in read-only mode..."
            )

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

    def results(self) -> list[ProductDiscoveryResult]:
        return list(self._results)

    def set_selected_product(self, product: TradableProduct | None) -> None:
        self._selected_product = product
        self._render_market_summary()

    def set_live_quote(self, quote: Quote | None) -> None:
        if quote is None:
            return
        self._live_quotes[quote.epic] = quote
        for table, row_index in self._rows_by_epic.get(quote.epic, []):
            self._set_table_value(table, row_index, 1, _format_number(quote.bid))
            self._set_table_value(table, row_index, 2, _format_number(quote.offer))
            self._set_table_value(table, row_index, 3, _format_signed_number(quote.net_change))
            self._set_table_value(
                table,
                row_index,
                4,
                _format_signed_number(quote.percent_change),
            )
        if self._selected_product is not None and self._selected_product.epic == quote.epic:
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
        return (
            self._filter_text in " ".join(str(field).lower() for field in fields)
            and self._matches_status_filter(product)
        )

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
            self.product_tabs.addTab(asset_tabs, product_type_label)
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
            values = [
                product.name,
                _format_number(product.bid),
                _format_number(product.offer),
                _format_signed_number(product.net_change),
                _format_signed_number(product.percent_change),
                product.direction.value,
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
                if column_index in {1, 2, 3, 4, 11, 12}:
                    item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                table.setItem(row_index, column_index, item)
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
            self._selected_product = product
            self._render_market_summary()
            self.product_selected.emit(product)

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
            f"Snapshot variation: {_format_signed_number(product.net_change)}",
            f"Snapshot % variation: {_format_signed_number(product.percent_change)}",
        ]
        if quote is not None:
            lines.extend(
                [
                    "",
                    f"Live vente: {_format_number(quote.bid)}",
                    f"Live achat: {_format_number(quote.offer)}",
                    f"Live variation: {_format_signed_number(quote.net_change)}",
                    f"Live % variation: {_format_signed_number(quote.percent_change)}",
                    f"Live market state: {quote.market_state or '-'}",
                ]
            )
        self.market_summary.setPlainText("\n".join(lines))

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


def _matches_asset_class(product: TradableProduct, asset_class_filter: str) -> bool:
    if asset_class_filter == "all":
        return True
    return product.asset_class.value == asset_class_filter
