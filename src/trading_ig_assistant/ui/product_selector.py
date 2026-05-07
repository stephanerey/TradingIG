"""Thin product selector and ticket placeholder panel."""

from __future__ import annotations

from PyQt5 import QtWidgets


class ProductSelectorWidget(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)

        title = QtWidgets.QLabel("Product discovery")
        title.setStyleSheet("font-weight: 700; font-size: 15px;")

        self.search_box = QtWidgets.QLineEdit()
        self.search_box.setPlaceholderText("Read-only search term")

        self.product_list = QtWidgets.QListWidget()
        self.product_list.addItem("No products loaded in GUI placeholder")

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
        layout.addWidget(self.search_box)
        layout.addWidget(self.product_list, stretch=1)
        layout.addWidget(ticket_title)
        layout.addWidget(self.ticket_summary)
        layout.addWidget(self.trade_button)
