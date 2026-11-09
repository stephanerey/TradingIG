"""Deterministically project scheduled high-impact events into traceable risk flags."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from trading_ig_assistant.domain.context_sources import (
    ContextImportance,
    MacroEvent,
    MarketContextFlag,
)
from trading_ig_assistant.domain.macro_context import ContextSeverity


def build_scheduled_event_risk_flags(
    events: Sequence[MacroEvent],
    *,
    generated_at_utc: datetime,
    pre_event_window: timedelta,
    post_event_window: timedelta,
) -> tuple[MarketContextFlag, ...]:
    """Return red, non-directional flags for explicit HIGH events inside configured windows."""

    _require_utc(generated_at_utc)
    if pre_event_window <= timedelta(0):
        raise ValueError("pre-event warning window must be positive")
    if post_event_window <= timedelta(0):
        raise ValueError("post-event risk window must be positive")

    event_ids: set[str] = set()
    eligible: list[MacroEvent] = []
    for event in events:
        if event.event_id in event_ids:
            raise ValueError(f"duplicate macro event ID: {event.event_id}")
        event_ids.add(event.event_id)
        if event.observed_at_utc > generated_at_utc:
            raise ValueError(f"macro event observation is future-dated: {event.event_id}")
        if event.importance is not ContextImportance.HIGH:
            continue
        if event.scheduled_at_utc > generated_at_utc + pre_event_window:
            continue
        if event.scheduled_at_utc + post_event_window <= generated_at_utc:
            continue
        eligible.append(event)

    flags = [
        MarketContextFlag(
            schema_version=1,
            flag_id=f"scheduled-event-risk:{event.event_id}",
            label="High-impact scheduled event",
            summary=_event_summary(event, generated_at_utc),
            category=event.category,
            severity=ContextSeverity.RED,
            score=Decimal("0"),
            confidence=None,
            source_record_ids=(event.event_id,),
            observed_at_utc=generated_at_utc,
            valid_until_utc=event.scheduled_at_utc + post_event_window,
            tags=("event", "scheduled_event", "high_event_risk"),
        )
        for event in sorted(eligible, key=lambda item: (item.scheduled_at_utc, item.event_id))
    ]
    return tuple(flags)


def _event_summary(event: MacroEvent, generated_at_utc: datetime) -> str:
    delta_seconds = int((event.scheduled_at_utc - generated_at_utc).total_seconds())
    timing = (
        f"in {delta_seconds} seconds" if delta_seconds >= 0 else f"{-delta_seconds} seconds ago"
    )
    return (
        f"{event.title} is explicitly classified high impact and scheduled {timing} "
        f"at {event.scheduled_at_utc.isoformat()}."
    )


def _require_utc(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("scheduled-event risk generation must use UTC")
