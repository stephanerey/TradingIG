"""Provider-neutral contract for normalized news metadata."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from trading_ig_assistant.domain.context_sources import NewsItem


class NewsProvider(Protocol):
    @property
    def provider_id(self) -> str:
        """Return a stable provider identity."""

    def fetch_news(self, *, as_of_utc: datetime) -> Sequence[NewsItem]:
        """Return normalized metadata available no later than ``as_of_utc``."""
