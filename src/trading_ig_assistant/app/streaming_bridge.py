"""Qt bridge for background streaming callbacks."""

from __future__ import annotations

from PyQt5 import QtCore

from trading_ig_assistant.domain.market_data import ChartCandleUpdate, Quote


class StreamingEventBridge(QtCore.QObject):
    quote_received = QtCore.pyqtSignal(int, object)
    chart_received = QtCore.pyqtSignal(int, object)
    status_changed = QtCore.pyqtSignal(int, str)
    error_received = QtCore.pyqtSignal(int, str)

    def __init__(self, generation: int) -> None:
        super().__init__()
        self._generation = generation

    def on_stream_status(self, status: str) -> None:
        self.status_changed.emit(self._generation, status)

    def on_quote(self, quote: Quote) -> None:
        self.quote_received.emit(self._generation, quote)

    def on_chart(self, chart_update: ChartCandleUpdate) -> None:
        self.chart_received.emit(self._generation, chart_update)

    def on_stream_error(self, message: str) -> None:
        self.error_received.emit(self._generation, message)
