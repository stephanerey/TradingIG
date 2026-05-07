"""Thin product selector and ticket placeholder panel."""

from __future__ import annotations

from pathlib import Path

from PyQt5 import QtCore, QtWidgets

from trading_ig_assistant.services.product_discovery_service import (
    DEFAULT_WATCHLIST_SEARCH_TERMS,
    ProductDiscoveryResult,
)

PRODUCT_COLUMNS = [
    "Search",
    "Name",
    "Epic",
    "Type",
    "Direction",
    "Expiry",
    "Status",
    "Currency",
    "Min",
    "KO",
    "Strike",
]


class ProductSelectorWidget(QtWidgets.QWidget):
    discover_requested = QtCore.pyqtSignal(object)
    export_requested = QtCore.pyqtSignal(object)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._results: list[ProductDiscoveryResult] = []
        layout = QtWidgets.QVBoxLayout(self)

        title = QtWidgets.QLabel("Product discovery")
        title.setStyleSheet("font-weight: 700; font-size: 15px;")

        controls = QtWidgets.QHBoxLayout()
        self.search_box = QtWidgets.QLineEdit()
        self.search_box.setPlaceholderText("Optional comma-separated search terms")
        self.discover_button = QtWidgets.QPushButton("Discover watchlist")
        self.export_button = QtWidgets.QPushButton("Export report")
        self.export_button.setEnabled(False)
        self.discover_button.clicked.connect(self._emit_discover_requested)
        self.export_button.clicked.connect(self._emit_export_requested)
        controls.addWidget(self.search_box, stretch=1)
        controls.addWidget(self.discover_button)
        controls.addWidget(self.export_button)

        self.summary_label = QtWidgets.QLabel(
            "Watchlist: " + ", ".join(DEFAULT_WATCHLIST_SEARCH_TERMS)
        )
        self.summary_label.setWordWrap(True)

        self.product_table = QtWidgets.QTableWidget(0, len(PRODUCT_COLUMNS))
        self.product_table.setHorizontalHeaderLabels(PRODUCT_COLUMNS)
        self.product_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.product_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.product_table.horizontalHeader().setStretchLastSection(True)

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
        layout.addWidget(self.product_table, stretch=1)
        layout.addWidget(ticket_title)
        layout.addWidget(self.ticket_summary)
        layout.addWidget(self.trade_button)

    def set_busy(self, busy: bool) -> None:
        self.discover_button.setEnabled(not busy)
        self.export_button.setEnabled(bool(self._results) and not busy)
        if busy:
            self.summary_label.setText("Discovering IG products in read-only mode...")

    def set_results(self, results: list[ProductDiscoveryResult]) -> None:
        self._results = list(results)
        rows = [
            (result.search_term, product)
            for result in self._results
            for product in result.products
        ]
        self.product_table.setRowCount(len(rows))
        for row_index, (search_term, product) in enumerate(rows):
            values = [
                search_term,
                product.name,
                product.epic,
                product.product_type.value,
                product.direction.value,
                product.expiry or "",
                product.status or "",
                product.currency or "",
                _format_number(product.min_size),
                _format_number(product.ko_level),
                _format_number(product.strike),
            ]
            for column_index, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                self.product_table.setItem(row_index, column_index, item)
        self.product_table.resizeColumnsToContents()

        candidate_count = sum(result.candidates_count for result in self._results)
        error_count = sum(len(result.errors) for result in self._results)
        self.summary_label.setText(
            f"Discovery complete: {candidate_count} candidates, "
            f"{len(rows)} products, {error_count} errors."
        )
        self.export_button.setEnabled(bool(self._results))

    def results(self) -> list[ProductDiscoveryResult]:
        return list(self._results)

    def search_terms(self) -> list[str]:
        raw = self.search_box.text().strip()
        if not raw:
            return DEFAULT_WATCHLIST_SEARCH_TERMS
        return [term.strip() for term in raw.split(",") if term.strip()]

    def _emit_discover_requested(self) -> None:
        self.discover_requested.emit(self.search_terms())

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
