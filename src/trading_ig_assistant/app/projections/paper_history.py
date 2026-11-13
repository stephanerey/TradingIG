"""Immutable, redacted Paper journal projection for GUI V2."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from trading_ig_assistant.domain.journal import PnlStatus


@dataclass(frozen=True)
class PaperJournalRowVM:
    generation_id: int
    event_id: str
    timestamp_utc: datetime
    event_type: str
    correlation_id: str
    instrument_id: str | None
    pnl_amount: Decimal | None
    pnl_currency: str | None
    pnl_status: PnlStatus

    def __post_init__(self) -> None:
        if self.generation_id < 0 or not all(
            value.strip()
            for value in (self.event_id, self.event_type, self.correlation_id)
        ):
            raise ValueError("Paper journal projection identity is required")
        _require_utc(self.timestamp_utc)


@dataclass(frozen=True)
class PaperHistoryVM:
    generation_id: int
    generated_at_utc: datetime
    rows: tuple[PaperJournalRowVM, ...]

    def __post_init__(self) -> None:
        if self.generation_id < 0:
            raise ValueError("Paper history generation must be non-negative")
        _require_utc(self.generated_at_utc)
        if any(row.generation_id != self.generation_id for row in self.rows):
            raise ValueError("Paper history rows must share one generation")


def empty_paper_history_projection(
    generation_id: int,
    generated_at_utc: datetime,
) -> PaperHistoryVM:
    return PaperHistoryVM(
        generation_id=generation_id,
        generated_at_utc=generated_at_utc,
        rows=(),
    )


def _require_utc(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("Paper history timestamp must use UTC")
