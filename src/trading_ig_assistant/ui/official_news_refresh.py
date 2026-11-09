"""Qt worker for bounded official-news collection outside the GUI event loop."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from PyQt5 import QtCore

from trading_ig_assistant.adapters.news_provider import NewsProvider
from trading_ig_assistant.domain.context_sources import NewsCollectionSnapshot
from trading_ig_assistant.services.news_collection_service import collect_news

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class OfficialNewsRefreshResult:
    collected_at_utc: datetime
    snapshots: tuple[NewsCollectionSnapshot, ...]


class OfficialNewsRefreshWorker(QtCore.QObject):
    succeeded = QtCore.pyqtSignal(object)
    finished = QtCore.pyqtSignal()

    def __init__(self, providers: tuple[NewsProvider, ...]) -> None:
        super().__init__()
        self._providers = providers

    @QtCore.pyqtSlot()
    def run(self) -> None:
        collected_at_utc = datetime.now(UTC)
        try:
            snapshots = tuple(
                collect_news(provider, as_of_utc=collected_at_utc) for provider in self._providers
            )
            self.succeeded.emit(
                OfficialNewsRefreshResult(
                    collected_at_utc=collected_at_utc,
                    snapshots=snapshots,
                )
            )
        finally:
            LOGGER.debug("Official news refresh worker finished")
            self.finished.emit()
