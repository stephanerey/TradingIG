"""Minimal GUI shell for P01."""

from __future__ import annotations

import sys

from PyQt5 import QtCore, QtWidgets

from trading_ig_assistant.ui.chart_view import ChartView
from trading_ig_assistant.ui.macro_ribbon_widget import MacroRibbonWidget
from trading_ig_assistant.ui.product_selector import ProductSelectorWidget
from trading_ig_assistant.ui.settings_view import SettingsView


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Trading IG Assistant - P01 read-only shell")
        self.resize(1280, 820)
        self._build_menu()
        self._build_layout()

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        quit_action = file_menu.addAction("Quit")
        quit_action.triggered.connect(self.close)

        tools_menu = self.menuBar().addMenu("&Tools")
        disabled_action = tools_menu.addAction("Live trading disabled")
        disabled_action.setEnabled(False)

    def _build_layout(self) -> None:
        root = QtWidgets.QWidget()
        root_layout = QtWidgets.QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)

        root_layout.addWidget(MacroRibbonWidget())

        body = QtWidgets.QSplitter()
        body.setOrientation(QtCore.Qt.Horizontal)
        body.addWidget(ChartView())

        right_tabs = QtWidgets.QTabWidget()
        right_tabs.addTab(ProductSelectorWidget(), "Products / Ticket")
        right_tabs.addTab(SettingsView(), "Settings")
        right_tabs.setMinimumWidth(360)
        body.addWidget(right_tabs)
        body.setStretchFactor(0, 4)
        body.setStretchFactor(1, 1)

        root_layout.addWidget(body, stretch=1)
        self.setCentralWidget(root)


def run_gui() -> int:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
