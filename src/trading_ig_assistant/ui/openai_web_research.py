"""Temporary manual UI for sourced market research."""

from __future__ import annotations

from datetime import UTC, datetime
from html import escape

from PyQt5 import QtCore, QtWidgets

from trading_ig_assistant.adapters.credentials import SecretValue
from trading_ig_assistant.domain.ai_context import AIAnalysisStatus, MarketContextSnapshot
from trading_ig_assistant.services.openai_web_research import (
    WebResearchError,
    WebResearchResult,
    research_market,
)
from trading_ig_assistant.services.web_research_context import analyze_web_research

_DIAGNOSTICS = {
    "AUTH": "Authentification OpenAI refusée. Vérifiez la clé API configurée.",
    "ACCESS": "Accès OpenAI refusé pour ce compte, ce modèle ou la recherche web.",
    "RATE_LIMIT": "OpenAI a refusé temporairement l'appel : quota, facturation ou limite atteinte.",
    "HTTP": "Le service OpenAI a refusé l'appel.",
    "NETWORK": "Communication avec OpenAI impossible ou délai dépassé.",
    "OUTPUT_LIMIT": "Réponse incomplète : la limite de sortie a été atteinte.",
    "INCOMPLETE": "OpenAI a rendu une réponse incomplète.",
    "NO_SEARCH": "OpenAI n'a pas terminé de recherche web.",
    "NO_CITATIONS": "La recherche ne contient pas de synthèse et de sources utilisables.",
    "INVALID_RESPONSE": "La réponse OpenAI est invalide ou inexploitable.",
}


class ResearchWorker(QtCore.QObject):
    succeeded = QtCore.pyqtSignal(object)
    context_ready = QtCore.pyqtSignal(object)
    context_failed = QtCore.pyqtSignal()
    failed = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()

    def __init__(self, market: str, instrument_id: str, model: str, key: str) -> None:
        super().__init__()
        self.market, self.model, self.key = market, model, SecretValue(key)
        self.instrument_id = instrument_id

    @QtCore.pyqtSlot()
    def run(self) -> None:
        try:
            research = research_market(market=self.market, model=self.model, api_key=self.key)
            self.succeeded.emit(research)
            try:
                context = analyze_web_research(
                    research, instrument_id=self.instrument_id, api_key=self.key
                )
                self.context_ready.emit(context)
            except Exception:
                self.context_failed.emit()
        except WebResearchError as exc:
            self.failed.emit(exc.code)
        except Exception:
            self.failed.emit("INVALID_RESPONSE")
        finally:
            self.finished.emit()


class WebResearchDialog(QtWidgets.QDialog):
    context_ready = QtCore.pyqtSignal(object)

    def __init__(
        self, *, market: str, instrument_id: str, model: str, key: str, parent=None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Recherche marché OpenAI")
        self.resize(760, 600)
        self._market, self._instrument_id, self._model, self._key = (
            market,
            instrument_id,
            model,
            key,
        )
        self._thread: QtCore.QThread | None = None
        self._worker: ResearchWorker | None = None
        layout = QtWidgets.QVBoxLayout(self)
        label = QtWidgets.QLabel(
            f"Marché : {market}\nRecherche et analyse consultatives : jusqu'à deux appels OpenAI "
            "et les recherches web peuvent être facturés. Aucun ordre n'est créé."
        )
        label.setWordWrap(True)
        layout.addWidget(label)
        self._button = QtWidgets.QPushButton("Lancer une recherche web OpenAI")
        self._button.clicked.connect(self._start)
        layout.addWidget(self._button)
        self._status = QtWidgets.QLabel("Indicateur IA : en attente de recherche.")
        layout.addWidget(self._status)
        self._result = QtWidgets.QTextBrowser()
        self._result.setOpenExternalLinks(True)
        self._result.setPlainText("Aucune recherche lancée.")
        layout.addWidget(self._result)

    @QtCore.pyqtSlot()
    def _start(self) -> None:
        if self._thread is not None:
            return
        self._button.setEnabled(False)
        self._result.setPlainText("Recherche en cours…")
        thread = QtCore.QThread(self)
        self._status.setText("Indicateur IA : recherche en cours…")
        worker = ResearchWorker(self._market, self._instrument_id, self._model, self._key)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.succeeded.connect(self._show_result)
        worker.context_ready.connect(self._on_context_ready)
        worker.context_failed.connect(self._on_context_failed)
        worker.failed.connect(self._show_failure)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(self._finished)
        thread.finished.connect(thread.deleteLater)
        self._thread, self._worker = thread, worker
        thread.start()

    @QtCore.pyqtSlot(object)
    def _show_result(self, result: object) -> None:
        if not isinstance(result, WebResearchResult):
            self._show_failure("INVALID_RESPONSE")
            return
        sources = "".join(
            f'<li><a href="{escape(url, quote=True)}">{escape(title)}</a></li>'
            for url, title in result.sources
        )
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
        self._result.setHtml(
            f"<p>Recherche reçue : {timestamp} · Modèle : {escape(result.model)}</p>"
            f"<p>{escape(result.summary).replace(chr(10), '<br>')}</p>"
            f"<h3>Sources citées</h3><ul>{sources}</ul>"
        )
        self._status.setText("Recherche reçue ; analyse de l'indicateur IA en cours…")

    @QtCore.pyqtSlot(object)
    def _on_context_ready(self, context: object) -> None:
        if not isinstance(context, MarketContextSnapshot):
            self._on_context_failed()
            return
        if context.ai_analysis.status is AIAnalysisStatus.AVAILABLE:
            self._status.setText("Indicateur IA mis à jour pour ce produit (consultatif).")
        else:
            self._status.setText("Indicateur IA indisponible ; recherche consultable ci-dessous.")
        self.context_ready.emit(context)

    @QtCore.pyqtSlot()
    def _on_context_failed(self) -> None:
        self._status.setText("Analyse IA indisponible ; recherche consultable ci-dessous.")

    @QtCore.pyqtSlot(str)
    def _show_failure(self, code: str) -> None:
        self._status.setText("Indicateur IA : recherche indisponible.")
        self._result.setPlainText(
            f"Recherche indisponible ({code}). "
            + _DIAGNOSTICS.get(code, _DIAGNOSTICS["INVALID_RESPONSE"])
        )

    @QtCore.pyqtSlot()
    def _finished(self) -> None:
        self._thread = None
        self._worker = None
        self._button.setEnabled(True)

    def reject(self) -> None:
        if self._thread is None:
            super().reject()

    def closeEvent(self, event) -> None:
        if self._thread is not None:
            event.ignore()
        else:
            super().closeEvent(event)
