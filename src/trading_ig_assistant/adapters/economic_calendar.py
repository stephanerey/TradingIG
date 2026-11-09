"""Provider-neutral contract for normalized economic-calendar events."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from trading_ig_assistant.domain.context_sources import MacroEvent


class EconomicCalendarProvider(Protocol):
    @property
    def provider_id(self) -> str:
        """Return a stable provider identity."""

    def fetch_events(
        self,
        *,
        window_start_utc: datetime,
        window_end_utc: datetime,
    ) -> Sequence[MacroEvent]:
        """Return normalized events whose schedule intersects the requested UTC window."""
