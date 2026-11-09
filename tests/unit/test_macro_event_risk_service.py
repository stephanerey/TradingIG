from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from trading_ig_assistant.domain.context_sources import (
    ContextCategory,
    ContextImportance,
    MacroEvent,
    SourceUsageRights,
)
from trading_ig_assistant.domain.macro_context import ContextSeverity, EventRisk
from trading_ig_assistant.services.context_source_service import normalize_context_flags
from trading_ig_assistant.services.macro_context_service import MacroContextService
from trading_ig_assistant.services.macro_event_risk_service import (
    build_scheduled_event_risk_flags,
)

NOW = datetime(2026, 11, 5, 10, 0, tzinfo=UTC)


def _event(
    event_id: str,
    *,
    importance: ContextImportance = ContextImportance.HIGH,
    scheduled_delta: timedelta = timedelta(minutes=30),
    rights: SourceUsageRights = SourceUsageRights.METADATA_ONLY,
) -> MacroEvent:
    return MacroEvent(
        schema_version=1,
        event_id=event_id,
        title=f"Synthetic {event_id}",
        category=ContextCategory.INFLATION,
        importance=importance,
        scheduled_at_utc=NOW + scheduled_delta,
        observed_at_utc=NOW - timedelta(minutes=5),
        source="synthetic-calendar",
        source_url=f"https://example.invalid/events/{event_id}",
        usage_rights=rights,
        tags=("synthetic",),
    )


def _flags(*events: MacroEvent):
    return build_scheduled_event_risk_flags(
        events,
        generated_at_utc=NOW,
        pre_event_window=timedelta(hours=1),
        post_event_window=timedelta(minutes=15),
    )


def test_high_impact_event_in_window_becomes_traceable_high_event_risk() -> None:
    event = _event("CPI")

    flags = _flags(event)
    signals = normalize_context_flags(
        macro_events=(event,),
        news_items=(),
        flags=flags,
        generated_at_utc=NOW,
    )
    state = MacroContextService().build_state(signals, NOW)

    assert len(flags) == 1
    assert flags[0].severity is ContextSeverity.RED
    assert flags[0].score == 0
    assert flags[0].source_record_ids == ("CPI",)
    assert "in 1800 seconds" in flags[0].summary
    assert "high_event_risk" in flags[0].tags
    assert state.event_risk is EventRisk.HIGH
    assert "source_record:CPI" in state.signals[0].tags


def test_only_explicit_high_importance_inside_temporal_window_is_projected() -> None:
    events = (
        _event("MEDIUM", importance=ContextImportance.MEDIUM),
        _event("UNKNOWN", importance=ContextImportance.UNKNOWN),
        _event("TOO-EARLY", scheduled_delta=timedelta(hours=2)),
        _event("TOO-LATE", scheduled_delta=-timedelta(minutes=15)),
        _event("RECENT", scheduled_delta=-timedelta(minutes=14)),
    )

    flags = _flags(*events)

    assert tuple(flag.source_record_ids for flag in flags) == (("RECENT",),)
    assert "840 seconds ago" in flags[0].summary


def test_flags_are_ordered_by_schedule_then_stable_event_id() -> None:
    flags = _flags(
        _event("B", scheduled_delta=timedelta(minutes=20)),
        _event("C", scheduled_delta=timedelta(minutes=10)),
        _event("A", scheduled_delta=timedelta(minutes=20)),
    )

    assert tuple(flag.source_record_ids[0] for flag in flags) == ("C", "A", "B")


def test_unknown_rights_degrade_high_event_to_gray_unknown() -> None:
    event = _event("UNVERIFIED", rights=SourceUsageRights.UNKNOWN)

    signal = normalize_context_flags(
        macro_events=(event,),
        news_items=(),
        flags=_flags(event),
        generated_at_utc=NOW,
    )[0]
    state = MacroContextService().build_state((signal,), NOW)

    assert signal.severity is ContextSeverity.GRAY
    assert signal.score is None
    assert state.event_risk is EventRisk.UNKNOWN


def test_invalid_windows_duplicate_ids_and_future_observation_are_rejected() -> None:
    event = _event("CPI")
    with pytest.raises(ValueError, match="pre-event"):
        build_scheduled_event_risk_flags(
            (event,),
            generated_at_utc=NOW,
            pre_event_window=timedelta(0),
            post_event_window=timedelta(minutes=15),
        )
    with pytest.raises(ValueError, match="post-event"):
        build_scheduled_event_risk_flags(
            (event,),
            generated_at_utc=NOW,
            pre_event_window=timedelta(hours=1),
            post_event_window=timedelta(0),
        )
    with pytest.raises(ValueError, match="duplicate macro event"):
        _flags(event, event)
    with pytest.raises(ValueError, match="future-dated"):
        _flags(replace(event, observed_at_utc=NOW + timedelta(seconds=1)))


def test_generation_timestamp_must_be_utc() -> None:
    with pytest.raises(ValueError, match="must use UTC"):
        build_scheduled_event_risk_flags(
            (),
            generated_at_utc=NOW.replace(tzinfo=None),
            pre_event_window=timedelta(hours=1),
            post_event_window=timedelta(minutes=15),
        )
