"""Queued Qt signal boundary for immutable runtime projections."""

from __future__ import annotations

from PyQt5 import QtCore

from trading_ig_assistant.app.runtime.trading_runtime import RuntimeSubscription
from trading_ig_assistant.app.ui_facade import TradingUIFacade


class RuntimeQtBridge(QtCore.QObject):
    account_header_changed = QtCore.pyqtSignal(object)
    catalogue_changed = QtCore.pyqtSignal(object)
    dashboard_changed = QtCore.pyqtSignal(object)
    health_changed = QtCore.pyqtSignal(object)
    macro_changed = QtCore.pyqtSignal(object)
    optimization_changed = QtCore.pyqtSignal(object)
    paper_history_changed = QtCore.pyqtSignal(object)
    scanner_changed = QtCore.pyqtSignal(object)

    def __init__(self, facade: TradingUIFacade) -> None:
        super().__init__()
        self._subscriptions: tuple[RuntimeSubscription, ...] = (
            facade.subscribe("account_header", self.account_header_changed.emit),
            facade.subscribe("catalogue", self.catalogue_changed.emit),
            facade.subscribe("dashboard", self.dashboard_changed.emit),
            facade.subscribe("health", self.health_changed.emit),
            facade.subscribe("macro", self.macro_changed.emit),
            facade.subscribe("optimization", self.optimization_changed.emit),
            facade.subscribe("paper_history", self.paper_history_changed.emit),
            facade.subscribe("scanner", self.scanner_changed.emit),
        )

    def close(self) -> None:
        for subscription in self._subscriptions:
            subscription.close()
        self._subscriptions = ()
