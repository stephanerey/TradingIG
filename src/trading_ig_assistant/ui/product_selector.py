"""Thin product selector and ticket placeholder panel."""

from __future__ import annotations

from pathlib import Path

from PyQt5 import QtCore, QtWidgets

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

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._results: list[ProductDiscoveryResult] = []
        self._filter_text = ""
        self._tables: dict[tuple[str, str], QtWidgets.QTableWidget] = {}
        layout = QtWidgets.QVBoxLayout(self)

        title = QtWidgets.QLabel("Product discovery")
        title.setStyleSheet("font-weight: 700; font-size: 15px;")

        controls = QtWidgets.QHBoxLayout()
        self.filter_box = QtWidgets.QLineEdit()
        self.filter_box.setPlaceholderText("Filter displayed products")
        self.filter_box.textChanged.connect(self._apply_filter)
        self.discover_button = QtWidgets.QPushButton("Discover all products")
        self.export_button = QtWidgets.QPushButton("Export report")
        self.export_button.setEnabled(False)
        self.discover_button.clicked.connect(self._emit_discover_requested)
        self.export_button.clicked.connect(self._emit_export_requested)
        controls.addWidget(self.filter_box, stretch=1)
        controls.addWidget(self.discover_button)
        controls.addWidget(self.export_button)

        self.summary_label = QtWidgets.QLabel("No product discovery run yet.")
        self.summary_label.setWordWrap(True)

        self.product_tabs = QtWidgets.QTabWidget()
        self.product_table = self._build_product_tabs()

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
        self._render_table()
        self.export_button.setEnabled(bool(self._results))

    def _render_table(self) -> None:
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

    def results(self) -> list[ProductDiscoveryResult]:
        return list(self._results)

    def _emit_discover_requested(self) -> None:
        self.discover_requested.emit(None)

    def _apply_filter(self, text: str) -> None:
        self._filter_text = text.strip().lower()
        self._render_table()

    def _matches_filter(self, product: object) -> bool:
        if not self._filter_text:
            return True
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
        return self._filter_text in " ".join(str(field).lower() for field in fields)

    def _build_product_tabs(self) -> QtWidgets.QTableWidget:
        first_table: QtWidgets.QTableWidget | None = None
        for product_type_key, product_type_label in PRODUCT_TYPE_TABS:
            asset_tabs = QtWidgets.QTabWidget()
            for asset_key, asset_label in ASSET_CLASS_TABS:
                table = _create_product_table()
                self._tables[(product_type_key, asset_key)] = table
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
                if column_index in {1, 2, 3, 4, 11, 12}:
                    item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                table.setItem(row_index, column_index, item)
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
