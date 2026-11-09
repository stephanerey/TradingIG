"""Qt worker for an explicitly requested OpenAI context analysis."""

from __future__ import annotations

from collections.abc import Callable

from PyQt5 import QtCore

from trading_ig_assistant.adapters.credentials import SecretValue
from trading_ig_assistant.domain.ai_context import MarketContextSnapshot
from trading_ig_assistant.domain.macro_context import MacroRibbonState
from trading_ig_assistant.services.openai_context_runtime_service import (
    run_openai_market_context,
)

OpenAIContextRunner = Callable[..., MarketContextSnapshot]


class OpenAIContextRefreshWorker(QtCore.QObject):
    succeeded = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()

    def __init__(
        self,
        *,
        model: str,
        api_key: SecretValue,
        max_output_tokens: int,
        macro_state: MacroRibbonState,
        instrument_id: str,
        runner: OpenAIContextRunner = run_openai_market_context,
    ) -> None:
        super().__init__()
        self._model = model
        self._api_key = api_key
        self._max_output_tokens = max_output_tokens
        self._macro_state = macro_state
        self._instrument_id = instrument_id
        self._runner = runner

    @QtCore.pyqtSlot()
    def run(self) -> None:
        try:
            result = self._runner(
                model=self._model,
                api_key=self._api_key,
                max_output_tokens=self._max_output_tokens,
                macro_state=self._macro_state,
                instrument_id=self._instrument_id,
            )
            self.succeeded.emit(result)
        except Exception:
            self.failed.emit(
                "L'analyse OpenAI a échoué avant validation. Aucun détail sensible n'est affiché."
            )
        finally:
            self.finished.emit()
