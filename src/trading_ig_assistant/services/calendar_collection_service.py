"""Collect normalized calendar events while degrading provider failures explicitly."""

from __future__ import annotations

from datetime import UTC, datetime

from trading_ig_assistant.adapters.economic_calendar import EconomicCalendarProvider
from trading_ig_assistant.domain.context_sources import (
    CalendarCollectionSnapshot,
    MacroEvent,
    ProviderCollectionStatus,
)


def collect_calendar(
    provider: EconomicCalendarProvider,
    *,
    window_start_utc: datetime,
    window_end_utc: datetime,
    collected_at_utc: datetime,
) -> CalendarCollectionSnapshot:
    _require_utc(window_start_utc, "calendar collection window start")
    _require_utc(window_end_utc, "calendar collection window end")
    _require_utc(collected_at_utc, "calendar collection")
    if window_end_utc <= window_start_utc:
        raise ValueError("calendar collection window end must follow its start")
    try:
        provider_id = provider.provider_id
    except Exception:
        return _unavailable(
            "invalid-calendar-provider",
            window_start_utc,
            window_end_utc,
            collected_at_utc,
            "CALENDAR_PROVIDER_ERROR",
        )
    if not isinstance(provider_id, str) or not provider_id.strip():
        return _unavailable(
            "invalid-calendar-provider",
            window_start_utc,
            window_end_utc,
            collected_at_utc,
            "CALENDAR_PROVIDER_INVALID",
        )
    try:
        events = tuple(
            provider.fetch_events(
                window_start_utc=window_start_utc,
                window_end_utc=window_end_utc,
            )
        )
        if any(not isinstance(event, MacroEvent) for event in events):
            raise TypeError("provider returned a non-calendar record")
        return CalendarCollectionSnapshot(
            schema_version=1,
            provider_id=provider_id,
            status=ProviderCollectionStatus.AVAILABLE,
            events=events,
            collected_at_utc=collected_at_utc,
            window_start_utc=window_start_utc,
            window_end_utc=window_end_utc,
            reason_codes=(),
        )
    except Exception:
        return _unavailable(
            provider_id,
            window_start_utc,
            window_end_utc,
            collected_at_utc,
            "CALENDAR_PROVIDER_ERROR",
        )


def _unavailable(
    provider_id: str,
    window_start_utc: datetime,
    window_end_utc: datetime,
    collected_at_utc: datetime,
    reason_code: str,
) -> CalendarCollectionSnapshot:
    return CalendarCollectionSnapshot(
        schema_version=1,
        provider_id=provider_id,
        status=ProviderCollectionStatus.UNAVAILABLE,
        events=(),
        collected_at_utc=collected_at_utc,
        window_start_utc=window_start_utc,
        window_end_utc=window_end_utc,
        reason_codes=(reason_code,),
    )


def _require_utc(value: datetime, label: str) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"{label} timestamp must use UTC")
