from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from trading_ig_assistant.domain.context_sources import (
    ContextCategory,
    ContextImportance,
    MacroEvent,
    MarketContextFlag,
    NewsItem,
    SourceUsageRights,
)
from trading_ig_assistant.domain.macro_context import ContextSeverity, EventRisk, MarketRegime
from trading_ig_assistant.services.context_source_service import normalize_context_flags
from trading_ig_assistant.services.macro_context_service import MacroContextService

NOW = datetime(2026, 10, 23, 14, 0, tzinfo=UTC)


def _event(
    event_id: str,
    category: ContextCategory,
    importance: ContextImportance,
    *,
    rights: SourceUsageRights = SourceUsageRights.METADATA_ONLY,
) -> MacroEvent:
    return MacroEvent(
        schema_version=1,
        event_id=event_id,
        title=f"Synthetic {event_id}",
        category=category,
        importance=importance,
        scheduled_at_utc=NOW + timedelta(minutes=30),
        observed_at_utc=NOW - timedelta(minutes=5),
        source="synthetic-calendar",
        source_url=f"https://example.invalid/events/{event_id}",
        usage_rights=rights,
        tags=(category.value,),
    )


def _news(
    item_id: str,
    category: ContextCategory,
    importance: ContextImportance,
    *,
    rights: SourceUsageRights = SourceUsageRights.SUMMARY_ALLOWED,
) -> NewsItem:
    return NewsItem(
        schema_version=1,
        item_id=item_id,
        headline=f"Synthetic {item_id}",
        summary="Synthetic summary" if rights is SourceUsageRights.SUMMARY_ALLOWED else None,
        category=category,
        importance=importance,
        published_at_utc=NOW - timedelta(minutes=10),
        observed_at_utc=NOW - timedelta(minutes=5),
        source="synthetic-news",
        source_url=f"https://example.invalid/news/{item_id}",
        usage_rights=rights,
        tags=(category.value,),
    )


def _flag(
    flag_id: str,
    category: ContextCategory,
    severity: ContextSeverity,
    score: str,
    source_record_ids: tuple[str, ...],
    tags: tuple[str, ...],
    *,
    valid_until: datetime | None = None,
) -> MarketContextFlag:
    return MarketContextFlag(
        schema_version=1,
        flag_id=flag_id,
        label=f"Synthetic {flag_id}",
        summary=f"Synthetic assessment for {flag_id}.",
        category=category,
        severity=severity,
        score=Decimal(score),
        confidence=Decimal("0.8"),
        source_record_ids=source_record_ids,
        observed_at_utc=NOW,
        valid_until_utc=valid_until or NOW + timedelta(hours=1),
        tags=tags,
    )


def test_fed_and_cpi_events_become_traceable_event_risk() -> None:
    events = (
        _event("FOMC", ContextCategory.CENTRAL_BANK, ContextImportance.HIGH),
        _event("CPI", ContextCategory.INFLATION, ContextImportance.MEDIUM),
    )
    flags = (
        _flag(
            "FED-RISK",
            ContextCategory.CENTRAL_BANK,
            ContextSeverity.RED,
            "0",
            ("FOMC",),
            ("event", "fed"),
        ),
        _flag(
            "CPI-RISK",
            ContextCategory.INFLATION,
            ContextSeverity.YELLOW,
            "0",
            ("CPI",),
            ("event", "cpi"),
        ),
    )

    signals = normalize_context_flags(
        macro_events=events,
        news_items=(),
        flags=flags,
        generated_at_utc=NOW,
    )
    state = MacroContextService().build_state(signals, NOW)

    assert state.event_risk is EventRisk.HIGH
    assert signals[0].signal_id == "CPI-RISK"
    assert "source_record:CPI" in signals[0].tags
    assert signals[1].source == "synthetic-calendar"


def test_geopolitical_and_oil_flags_preserve_explicit_assessment() -> None:
    news = (
        _news("GEO", ContextCategory.GEOPOLITICAL, ContextImportance.HIGH),
        _news("OIL", ContextCategory.ENERGY, ContextImportance.HIGH),
    )
    flags = (
        _flag(
            "RISK-OFF",
            ContextCategory.GEOPOLITICAL,
            ContextSeverity.RED,
            "-70",
            ("GEO", "OIL"),
            ("risk", "index", "geopolitical", "oil"),
        ),
    )

    signals = normalize_context_flags(
        macro_events=(),
        news_items=news,
        flags=flags,
        generated_at_utc=NOW,
    )
    state = MacroContextService().build_state(signals, NOW)

    assert state.regime is MarketRegime.RISK_OFF
    assert signals[0].source == "synthetic-news"
    assert signals[0].source_url is None
    assert "source_record:GEO" in signals[0].tags
    assert "source_record:OIL" in signals[0].tags


def test_unknown_source_rights_degrade_to_gray_unavailable_context() -> None:
    item = _news(
        "UNVERIFIED",
        ContextCategory.GEOPOLITICAL,
        ContextImportance.HIGH,
        rights=SourceUsageRights.UNKNOWN,
    )
    flag = _flag(
        "UNVERIFIED-RISK",
        ContextCategory.GEOPOLITICAL,
        ContextSeverity.GREEN,
        "80",
        ("UNVERIFIED",),
        ("risk",),
    )

    signal = normalize_context_flags(
        macro_events=(),
        news_items=(item,),
        flags=(flag,),
        generated_at_utc=NOW,
    )[0]
    state = MacroContextService().build_state((signal,), NOW)

    assert signal.severity is ContextSeverity.GRAY
    assert signal.score is None
    assert signal.confidence is None
    assert "rights:unknown" in signal.tags
    assert state.regime is MarketRegime.UNKNOWN


def test_summary_requires_explicit_usage_rights() -> None:
    with pytest.raises(ValueError, match="summary usage rights"):
        replace(
            _news(
                "METADATA",
                ContextCategory.OTHER,
                ContextImportance.LOW,
                rights=SourceUsageRights.METADATA_ONLY,
            ),
            summary="Not authorized by the declared rights",
        )


def test_unknown_missing_and_future_lineage_is_rejected() -> None:
    item = _news("KNOWN", ContextCategory.OTHER, ContextImportance.LOW)
    flag = _flag(
        "FLAG",
        ContextCategory.OTHER,
        ContextSeverity.YELLOW,
        "0",
        ("MISSING",),
        ("risk",),
    )
    with pytest.raises(ValueError, match="unknown source record"):
        normalize_context_flags(
            macro_events=(), news_items=(item,), flags=(flag,), generated_at_utc=NOW
        )

    with pytest.raises(ValueError, match="future-dated"):
        normalize_context_flags(
            macro_events=(),
            news_items=(replace(item, observed_at_utc=NOW + timedelta(seconds=1)),),
            flags=(),
            generated_at_utc=NOW,
        )


def test_duplicate_source_and_flag_ids_are_rejected() -> None:
    item = _news("DUPLICATE", ContextCategory.OTHER, ContextImportance.LOW)
    with pytest.raises(ValueError, match="duplicate context source"):
        normalize_context_flags(
            macro_events=(),
            news_items=(item, item),
            flags=(),
            generated_at_utc=NOW,
        )

    flag = _flag(
        "DUPLICATE-FLAG",
        ContextCategory.OTHER,
        ContextSeverity.GREEN,
        "0",
        ("DUPLICATE",),
        ("event",),
    )
    with pytest.raises(ValueError, match="duplicate context flag"):
        normalize_context_flags(
            macro_events=(),
            news_items=(item,),
            flags=(flag, flag),
            generated_at_utc=NOW,
        )


def test_stale_normalized_flag_degrades_in_existing_macro_service() -> None:
    item = _news("OLD", ContextCategory.INFLATION, ContextImportance.HIGH)
    flag = _flag(
        "OLD-CPI",
        ContextCategory.INFLATION,
        ContextSeverity.RED,
        "0",
        ("OLD",),
        ("event",),
        valid_until=NOW + timedelta(seconds=1),
    )
    signal = normalize_context_flags(
        macro_events=(), news_items=(item,), flags=(flag,), generated_at_utc=NOW
    )[0]

    state = MacroContextService().build_state((signal,), NOW + timedelta(seconds=2))

    assert state.signals[0].severity is ContextSeverity.GRAY
    assert state.event_risk is EventRisk.UNKNOWN
    assert "STALE:OLD-CPI" in state.reason_codes


def test_flag_cannot_predate_source_evidence() -> None:
    item = _news("LATE", ContextCategory.OTHER, ContextImportance.LOW)
    flag = replace(
        _flag(
            "EARLY-FLAG",
            ContextCategory.OTHER,
            ContextSeverity.YELLOW,
            "0",
            ("LATE",),
            ("risk",),
        ),
        observed_at_utc=NOW - timedelta(minutes=6),
    )

    with pytest.raises(ValueError, match="predates its source"):
        normalize_context_flags(
            macro_events=(), news_items=(item,), flags=(flag,), generated_at_utc=NOW
        )
