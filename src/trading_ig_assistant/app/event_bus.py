"""Minimal in-process event bus placeholder."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class EventBus:
    def __init__(self) -> None:
        self._subscribers: list[Callable[[Any], None]] = []

    def subscribe(self, callback: Callable[[Any], None]) -> None:
        self._subscribers.append(callback)

    def publish(self, event: Any) -> None:
        for subscriber in list(self._subscribers):
            subscriber(event)
