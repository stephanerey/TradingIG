"""Application boundary for append-only journal recording."""

from __future__ import annotations

from trading_ig_assistant.domain.journal import JournalEvent
from trading_ig_assistant.persistence.repositories import JournalEventRepository


class JournalService:
    def __init__(self, repository: JournalEventRepository) -> None:
        self._repository = repository

    def record(self, event: JournalEvent) -> None:
        self._repository.append(event)

    def history(self) -> tuple[JournalEvent, ...]:
        return self._repository.list_events()
