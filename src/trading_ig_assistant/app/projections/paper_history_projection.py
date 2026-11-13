"""Build a display-safe Paper journal projection from audited domain events."""

from __future__ import annotations

from datetime import datetime

from trading_ig_assistant.app.projections.paper_history import (
    PaperHistoryVM,
    PaperJournalRowVM,
)
from trading_ig_assistant.domain.journal import JournalEvent


def build_paper_history_projection(
    *,
    generation_id: int,
    events: tuple[JournalEvent, ...],
    generated_at_utc: datetime,
) -> PaperHistoryVM:
    rows = tuple(
        PaperJournalRowVM(
            generation_id=generation_id,
            event_id=event.event_id,
            timestamp_utc=event.timestamp_utc,
            event_type=event.event_type,
            correlation_id=event.correlation_id,
            instrument_id=event.instrument_id,
            pnl_amount=event.pnl_amount,
            pnl_currency=event.pnl_currency,
            pnl_status=event.pnl_status,
        )
        for event in sorted(events, key=lambda item: item.timestamp_utc, reverse=True)
    )
    return PaperHistoryVM(
        generation_id=generation_id,
        generated_at_utc=generated_at_utc,
        rows=rows,
    )
