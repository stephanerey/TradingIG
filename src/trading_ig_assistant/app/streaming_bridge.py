"""Qt bridge for background streaming callbacks."""

from __future__ import annotations

from PyQt5 import QtCore

from trading_ig_assistant.domain.market_data import ChartCandleUpdate, Quote


class StreamingEventBridge(QtCore.QObject):
    quote_received = QtCore.pyqtSignal(object)
    chart_received = QtCore.pyqtSignal(object)
    status_changed = QtCore.pyqtSignal(str)
    error_received = QtCore.pyqtSignal(str)

    def on_stream_status(self, status: str) -> None:
        self.status_changed.emit(status)

    def on_quote(self, quote: Quote) -> None:
        self.quote_received.emit(quote)

    def on_chart(self, chart_update: ChartCandleUpdate) -> None:
        self.chart_received.emit(chart_update)

    def on_stream_error(self, message: str) -> None:
        self.error_received.emit(message)
