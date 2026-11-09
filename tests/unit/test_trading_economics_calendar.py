import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from trading_ig_assistant.adapters.trading_economics_calendar import (
    TRADING_ECONOMICS_API_ORIGIN,
    CalendarHttpResponse,
    TradingEconomicsCalendarConfig,
    TradingEconomicsCalendarError,
    TradingEconomicsCalendarProvider,
)
from trading_ig_assistant.domain.context_sources import (
    ContextCategory,
    ContextImportance,
    SourceUsageRights,
)
from trading_ig_assistant.domain.macro_context import ContextSeverity, EventRisk
from trading_ig_assistant.services.context_source_service import normalize_context_flags
from trading_ig_assistant.services.macro_context_service import MacroContextService
from trading_ig_assistant.services.macro_event_risk_service import (
    build_scheduled_event_risk_flags,
)

NOW = datetime(2026, 11, 5, 10, 0, tzinfo=UTC)
START = datetime(2026, 11, 5, 0, 0, tzinfo=UTC)
END = datetime(2026, 11, 6, 23, 59, tzinfo=UTC)
FAKE_KEY = "synthetic-trading-economics-key"


def _raw_event(
    event_id: str = "412969",
    *,
    scheduled: str = "2026-11-05T13:30:00",
    category: str = "Inflation Rate",
    importance: int = 3,
    date_span: str = "0",
    source_url: str = "https://official.example/inflation",
) -> dict[str, object]:
    return {
        "CalendarId": event_id,
        "Date": scheduled,
        "Country": "United States",
        "Category": category,
        "Event": f"Synthetic event {event_id}",
        "Source": "Official Statistical Agency",
        "SourceURL": source_url,
        "DateSpan": date_span,
        "Importance": importance,
        "LastUpdate": "2026-11-05T09:00:00",
    }


def _response(payload: object, *, final_url: str) -> CalendarHttpResponse:
    return CalendarHttpResponse(
        body=json.dumps(payload).encode(),
        final_url=final_url,
        content_type="application/json; charset=utf-8",
    )


def _config(**changes) -> TradingEconomicsCalendarConfig:
    values = {
        "api_key": FAKE_KEY,
        "countries": ("united states", "euro area"),
        "category_map": (
            ("Inflation Rate", ContextCategory.INFLATION),
            ("Non Farm Payrolls", ContextCategory.EMPLOYMENT),
        ),
        "usage_rights": SourceUsageRights.METADATA_ONLY,
    }
    values.update(changes)
    return TradingEconomicsCalendarConfig(**values)


def test_provider_uses_header_secret_and_normalizes_bounded_calendar() -> None:
    captured: dict[str, object] = {}

    def transport(url, headers, timeout, max_bytes):
        captured.update(url=url, headers=dict(headers), timeout=timeout, max_bytes=max_bytes)
        return _response(
            [
                _raw_event(),
                _raw_event(
                    "LOW-OTHER",
                    scheduled="2026-11-05T15:00:00Z",
                    category="Unmapped Category",
                    importance=1,
                    date_span="1",
                    source_url="http://legacy.example/event",
                ),
            ],
            final_url=url,
        )

    provider = TradingEconomicsCalendarProvider(
        _config(),
        transport=transport,
        clock=lambda: NOW,
    )

    events = provider.fetch_events(window_start_utc=START, window_end_utc=END)

    assert provider.provider_id == "trading-economics-calendar"
    assert captured["url"] == (
        f"{TRADING_ECONOMICS_API_ORIGIN}/calendar/country/"
        "united%20states,euro%20area/2026-11-05/2026-11-06?f=json"
    )
    assert FAKE_KEY not in captured["url"]
    assert captured["headers"]["Authorization"] == FAKE_KEY
    assert captured["timeout"] == 8.0
    assert captured["max_bytes"] == 1_000_000
    assert events[0].event_id == "trading-economics:412969"
    assert events[0].scheduled_at_utc == datetime(2026, 11, 5, 13, 30, tzinfo=UTC)
    assert events[0].category is ContextCategory.INFLATION
    assert events[0].importance is ContextImportance.HIGH
    assert events[0].usage_rights is SourceUsageRights.METADATA_ONLY
    assert "scheduled_time_exact" in events[0].tags
    assert events[1].category is ContextCategory.OTHER
    assert events[1].importance is ContextImportance.LOW
    assert events[1].source_url is None
    assert "scheduled_time_estimated" in events[1].tags


def test_calendar_events_compose_with_existing_high_event_risk_service() -> None:
    def transport(url, *_args):
        return _response([_raw_event(scheduled="2026-11-05T10:30:00")], final_url=url)

    provider = TradingEconomicsCalendarProvider(
        _config(),
        transport=transport,
        clock=lambda: NOW,
    )
    events = provider.fetch_events(window_start_utc=START, window_end_utc=END)
    flags = build_scheduled_event_risk_flags(
        events,
        generated_at_utc=NOW,
        pre_event_window=timedelta(hours=1),
        post_event_window=timedelta(minutes=15),
    )
    signals = normalize_context_flags(
        macro_events=events,
        news_items=(),
        flags=flags,
        generated_at_utc=NOW,
    )
    state = MacroContextService().build_state(signals, NOW)

    assert state.event_risk is EventRisk.HIGH
    assert state.signals[0].severity is ContextSeverity.RED
    assert "source_record:trading-economics:412969" in state.signals[0].tags


def test_default_unknown_rights_preserve_gray_unknown_event_risk() -> None:
    def transport(url, *_args):
        return _response([_raw_event(scheduled="2026-11-05T10:30:00")], final_url=url)

    provider = TradingEconomicsCalendarProvider(
        _config(usage_rights=SourceUsageRights.UNKNOWN),
        transport=transport,
        clock=lambda: NOW,
    )
    events = provider.fetch_events(window_start_utc=START, window_end_utc=END)
    flags = build_scheduled_event_risk_flags(
        events,
        generated_at_utc=NOW,
        pre_event_window=timedelta(hours=1),
        post_event_window=timedelta(minutes=15),
    )
    signal = normalize_context_flags(
        macro_events=events,
        news_items=(),
        flags=flags,
        generated_at_utc=NOW,
    )[0]

    assert signal.severity is ContextSeverity.GRAY
    assert MacroContextService().build_state((signal,), NOW).event_risk is EventRisk.UNKNOWN


def test_events_outside_precise_requested_window_are_filtered() -> None:
    def transport(url, *_args):
        return _response(
            [
                _raw_event("BEFORE", scheduled="2026-11-04T23:59:59"),
                _raw_event("INSIDE", scheduled="2026-11-05T00:00:00"),
                _raw_event("AFTER", scheduled="2026-11-07T00:00:00"),
            ],
            final_url=url,
        )

    events = TradingEconomicsCalendarProvider(
        _config(), transport=transport, clock=lambda: NOW
    ).fetch_events(window_start_utc=START, window_end_utc=END)

    assert tuple(event.event_id for event in events) == ("trading-economics:INSIDE",)


@pytest.mark.parametrize(
    ("change", "match"),
    (
        ({"endpoint_origin": "https://example.invalid"}, "pinned official"),
        ({"countries": ()}, "explicit countries"),
        ({"countries": ("US", "us")}, "unique and bounded"),
        (
            {
                "category_map": (
                    ("Inflation", ContextCategory.INFLATION),
                    ("inflation", ContextCategory.OTHER),
                )
            },
            "non-empty and unique",
        ),
        ({"timeout_seconds": 0}, "limits must be positive"),
        ({"max_window": timedelta(0)}, "maximum window must be positive"),
    ),
)
def test_invalid_provider_configuration_is_rejected(change, match) -> None:
    with pytest.raises(ValueError, match=match):
        _config(**change)


@pytest.mark.parametrize(
    ("mutator", "match"),
    (
        (lambda item: {**item, "CalendarId": ""}, "CalendarId"),
        (lambda item: {**item, "Date": "not-a-date"}, "timestamp"),
        (lambda item: {**item, "DateSpan": "2"}, "timing precision"),
        (lambda item: {**item, "Importance": 4}, "importance"),
        (lambda item: {**item, "Importance": "3"}, "importance"),
        (lambda item: {**item, "Source": None}, "Source"),
        (lambda item: {**item, "Source": 123}, "Source"),
        (lambda item: {**item, "SourceURL": 42}, "source URL"),
    ),
)
def test_invalid_event_contract_is_rejected(mutator, match) -> None:
    def transport(url, *_args):
        return _response([mutator(_raw_event())], final_url=url)

    provider = TradingEconomicsCalendarProvider(_config(), transport=transport, clock=lambda: NOW)
    with pytest.raises(TradingEconomicsCalendarError, match=match):
        provider.fetch_events(window_start_utc=START, window_end_utc=END)


def test_duplicate_redirect_content_type_payload_and_event_limits_are_rejected() -> None:
    provider = TradingEconomicsCalendarProvider(
        _config(),
        transport=lambda url, *_args: _response([_raw_event(), _raw_event()], final_url=url),
        clock=lambda: NOW,
    )
    with pytest.raises(TradingEconomicsCalendarError, match="duplicate"):
        provider.fetch_events(window_start_utc=START, window_end_utc=END)

    provider = TradingEconomicsCalendarProvider(
        _config(),
        transport=lambda *_args: _response([], final_url="https://example.invalid"),
        clock=lambda: NOW,
    )
    with pytest.raises(TradingEconomicsCalendarError, match="redirected"):
        provider.fetch_events(window_start_utc=START, window_end_utc=END)

    provider = TradingEconomicsCalendarProvider(
        _config(),
        transport=lambda url, *_args: replace(
            _response([], final_url=url), content_type="text/html"
        ),
        clock=lambda: NOW,
    )
    with pytest.raises(TradingEconomicsCalendarError, match="content type"):
        provider.fetch_events(window_start_utc=START, window_end_utc=END)

    provider = TradingEconomicsCalendarProvider(
        _config(max_payload_bytes=5),
        transport=lambda url, *_args: CalendarHttpResponse(
            body=b"123456", final_url=url, content_type="application/json"
        ),
        clock=lambda: NOW,
    )
    with pytest.raises(TradingEconomicsCalendarError, match="payload size"):
        provider.fetch_events(window_start_utc=START, window_end_utc=END)

    provider = TradingEconomicsCalendarProvider(
        _config(max_events=1),
        transport=lambda url, *_args: _response(
            [_raw_event("ONE"), _raw_event("TWO")], final_url=url
        ),
        clock=lambda: NOW,
    )
    with pytest.raises(TradingEconomicsCalendarError, match="event limit"):
        provider.fetch_events(window_start_utc=START, window_end_utc=END)


def test_window_and_clock_must_be_valid_utc_and_bounded() -> None:
    provider = TradingEconomicsCalendarProvider(
        _config(max_window=timedelta(days=2)),
        transport=lambda url, *_args: _response([], final_url=url),
        clock=lambda: NOW,
    )
    with pytest.raises(ValueError, match="must use UTC"):
        provider.fetch_events(window_start_utc=START.replace(tzinfo=None), window_end_utc=END)
    with pytest.raises(ValueError, match="must follow"):
        provider.fetch_events(window_start_utc=END, window_end_utc=START)
    with pytest.raises(ValueError, match="configured maximum"):
        provider.fetch_events(
            window_start_utc=START,
            window_end_utc=START + timedelta(days=3),
        )

    provider = TradingEconomicsCalendarProvider(
        _config(),
        transport=lambda url, *_args: _response([], final_url=url),
        clock=lambda: NOW.replace(tzinfo=None),
    )
    with pytest.raises(ValueError, match="observation must use UTC"):
        provider.fetch_events(window_start_utc=START, window_end_utc=END)


def test_provider_configuration_and_errors_do_not_expose_secret() -> None:
    config = _config()
    provider = TradingEconomicsCalendarProvider(
        config,
        transport=lambda *_args: (_ for _ in ()).throw(RuntimeError(FAKE_KEY)),
        clock=lambda: NOW,
    )

    with pytest.raises(TradingEconomicsCalendarError) as captured:
        provider.fetch_events(window_start_utc=START, window_end_utc=END)

    assert FAKE_KEY not in repr(config)
    assert FAKE_KEY not in repr(provider)
    assert FAKE_KEY not in str(captured.value)
