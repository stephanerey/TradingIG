"""Qt worker for a bounded Trading Economics calendar refresh."""

from __future__ import annotations

from collections.abc import Callable

from PyQt5 import QtCore

from trading_ig_assistant.adapters.credentials import SecretValue
from trading_ig_assistant.services.trading_economics_calendar_runtime import (
    TradingEconomicsRuntimeConfig,
    TradingEconomicsRuntimeResult,
    refresh_trading_economics_calendar,
)

CalendarRuntimeRunner = Callable[..., TradingEconomicsRuntimeResult]


class EconomicCalendarRefreshWorker(QtCore.QObject):
    completed = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()

    def __init__(
        self,
        *,
        api_key: SecretValue,
        config: TradingEconomicsRuntimeConfig,
        runner: CalendarRuntimeRunner = refresh_trading_economics_calendar,
    ) -> None:
        super().__init__()
        self._api_key = api_key
        self._config = config
        self._runner = runner

    @QtCore.pyqtSlot()
    def run(self) -> None:
        try:
            result = self._runner(api_key=self._api_key, config=self._config)
            self.completed.emit(result)
        except Exception:
            self.failed.emit(
                "Le calendrier Trading Economics a échoué avant validation. "
                "Aucun détail sensible n'est affiché."
            )
        finally:
            self.finished.emit()
