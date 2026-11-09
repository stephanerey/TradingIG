"""Project calendar collection health without inventing market direction."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from trading_ig_assistant.domain.context_sources import (
    CalendarCollectionSnapshot,
    ProviderCollectionStatus,
)
from trading_ig_assistant.domain.macro_context import ContextSeverity, ContextSignal


def build_calendar_source_health_signal(
    snapshot: CalendarCollectionSnapshot,
    *,
    generated_at_utc: datetime,
    valid_for: timedelta,
) -> ContextSignal:
    _require_utc(generated_at_utc)
    if valid_for <= timedelta(0):
        raise ValueError("calendar source-health validity must be positive")
    available = snapshot.status is ProviderCollectionStatus.AVAILABLE
    if available:
        severity = ContextSeverity.GREEN
        summary = (
            f"Calendar source available; normalized events in window: {len(snapshot.events)}. "
            "Usage rights remain independently qualified."
        )
    else:
        severity = ContextSeverity.GRAY
        diagnostic = ", ".join(snapshot.reason_codes) or "CALENDAR_PROVIDER_ERROR"
        summary = f"Calendar source unavailable. Diagnostic: {diagnostic}."
    return ContextSignal(
        signal_id="economic-calendar-source-health",
        label="Economic calendar source",
        severity=severity,
        score=None,
        summary=summary,
        source=snapshot.provider_id,
        source_url=None,
        observed_at_utc=generated_at_utc,
        valid_until_utc=generated_at_utc + valid_for,
        confidence=None,
        tags=("data_health", "economic_calendar"),
    )


def _require_utc(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("calendar source-health timestamp must use UTC")
