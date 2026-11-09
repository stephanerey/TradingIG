"""Bounded Trading Economics calendar refresh and deterministic context projection."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from trading_ig_assistant.adapters.credentials import SecretValue
from trading_ig_assistant.adapters.trading_economics_calendar import (
    CalendarTransport,
    TradingEconomicsCalendarConfig,
    TradingEconomicsCalendarProvider,
)
from trading_ig_assistant.domain.context_sources import (
    CalendarCollectionSnapshot,
    ContextCategory,
    ProviderCollectionStatus,
    SourceUsageRights,
)
from trading_ig_assistant.domain.macro_context import ContextSignal
from trading_ig_assistant.services.calendar_collection_service import collect_calendar
from trading_ig_assistant.services.calendar_context_health_service import (
    build_calendar_source_health_signal,
)
from trading_ig_assistant.services.context_source_service import normalize_context_flags
from trading_ig_assistant.services.macro_event_risk_service import (
    build_scheduled_event_risk_flags,
)

DEFAULT_CATEGORY_MAP = (
    ("Interest Rate Decision", ContextCategory.CENTRAL_BANK),
    ("Inflation Rate", ContextCategory.INFLATION),
    ("Core Inflation Rate", ContextCategory.INFLATION),
    ("Non Farm Payrolls", ContextCategory.EMPLOYMENT),
    ("Unemployment Rate", ContextCategory.EMPLOYMENT),
    ("Initial Jobless Claims", ContextCategory.EMPLOYMENT),
    ("GDP Growth Rate", ContextCategory.GROWTH),
    ("Crude Oil Stocks Change", ContextCategory.ENERGY),
)


@dataclass(frozen=True)
class TradingEconomicsRuntimeConfig:
    countries: tuple[str, ...]
    lookahead: timedelta
    pre_event_window: timedelta
    post_event_window: timedelta

    def __init__(
        self,
        *,
        countries: Sequence[str],
        lookahead: timedelta = timedelta(hours=48),
        pre_event_window: timedelta = timedelta(minutes=60),
        post_event_window: timedelta = timedelta(minutes=15),
    ) -> None:
        normalized = tuple(country.strip() for country in countries)
        if not normalized or any(not country for country in normalized):
            raise ValueError("calendar runtime requires explicit countries")
        if len(normalized) > 10 or len({country.casefold() for country in normalized}) != len(
            normalized
        ):
            raise ValueError("calendar runtime countries must be unique and bounded")
        if not timedelta(0) < lookahead <= timedelta(days=30):
            raise ValueError("calendar runtime lookahead must be between zero and 30 days")
        if pre_event_window <= timedelta(0) or post_event_window <= timedelta(0):
            raise ValueError("calendar runtime risk windows must be positive")
        object.__setattr__(self, "countries", normalized)
        object.__setattr__(self, "lookahead", lookahead)
        object.__setattr__(self, "pre_event_window", pre_event_window)
        object.__setattr__(self, "post_event_window", post_event_window)


@dataclass(frozen=True)
class TradingEconomicsRuntimeResult:
    config: TradingEconomicsRuntimeConfig
    snapshot: CalendarCollectionSnapshot
    signals: tuple[ContextSignal, ...]


def refresh_trading_economics_calendar(
    *,
    api_key: SecretValue,
    config: TradingEconomicsRuntimeConfig,
    transport: CalendarTransport | None = None,
    clock: Callable[[], datetime] | None = None,
) -> TradingEconomicsRuntimeResult:
    now = (clock or (lambda: datetime.now(UTC)))()
    _require_utc(now)
    window_start = now - config.post_event_window
    window_end = now + config.lookahead
    provider = TradingEconomicsCalendarProvider(
        TradingEconomicsCalendarConfig(
            api_key=api_key,
            countries=config.countries,
            category_map=DEFAULT_CATEGORY_MAP,
            usage_rights=SourceUsageRights.UNKNOWN,
        ),
        transport=transport,
        clock=lambda: now,
    )
    snapshot = collect_calendar(
        provider,
        window_start_utc=window_start,
        window_end_utc=window_end,
        collected_at_utc=now,
    )
    signals = [
        build_calendar_source_health_signal(
            snapshot,
            generated_at_utc=now,
            valid_for=timedelta(minutes=15),
        )
    ]
    if snapshot.status is ProviderCollectionStatus.AVAILABLE:
        flags = build_scheduled_event_risk_flags(
            snapshot.events,
            generated_at_utc=now,
            pre_event_window=config.pre_event_window,
            post_event_window=config.post_event_window,
        )
        signals.extend(
            normalize_context_flags(
                macro_events=snapshot.events,
                news_items=(),
                flags=flags,
                generated_at_utc=now,
            )
        )
    return TradingEconomicsRuntimeResult(
        config=config,
        snapshot=snapshot,
        signals=tuple(signals),
    )


def _require_utc(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("calendar runtime clock must use UTC")
