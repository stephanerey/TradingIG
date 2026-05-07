"""Thin product selector and ticket placeholder panel."""

from __future__ import annotations

from pathlib import Path

from PyQt5 import QtCore, QtWidgets

from trading_ig_assistant.services.product_discovery_service import ProductDiscoveryResult

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
        self._filter_text = ""
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
            self.summary_label.setText(
                "Discovering IG products in read-only mode..."
            )

    def set_results(self, results: list[ProductDiscoveryResult]) -> None:
        self._results = list(results)
        self._render_table()
        self.export_button.setEnabled(bool(self._results))

    def _render_table(self) -> None:
        rows = [
            (result.search_term, product)
            for result in self._results
            for product in result.products
            if self._matches_filter(product)
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

        total_product_count = sum(len(result.products) for result in self._results)
        candidate_count = sum(result.candidates_count for result in self._results)
        error_count = sum(len(result.errors) for result in self._results)
        self.summary_label.setText(
            f"Discovery complete: {candidate_count} candidates, "
            f"{total_product_count} products, {len(rows)} displayed, {error_count} errors. "
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
        ]
        return self._filter_text in " ".join(str(field).lower() for field in fields)

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
