"""Immutable metadata-only macro/news read models for GUI V2."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from trading_ig_assistant.app.projections.common import Availability


@dataclass(frozen=True)
class NewsRowVM:
    item_id: str
    headline: str
    source: str
    published_at_utc: datetime
    category: str
    importance: str
    usage_rights: str
    source_url: str | None
    provider_id: str = "unknown"

    def __post_init__(self) -> None:
        if not self.item_id.strip() or not self.headline.strip() or not self.source.strip():
            raise ValueError("news projection identity is required")
        _require_utc(self.published_at_utc)


@dataclass(frozen=True)
class IntelligenceEventRowVM:
    event_id: str
    headline: str
    published_at_utc: datetime
    publication_time_status: str
    verification_status: str
    category: str
    sources: tuple[str, ...]
    source_urls: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.event_id.strip() or not self.headline.strip() or not self.sources:
            raise ValueError("market intelligence event projection identity is required")
        _require_utc(self.published_at_utc)


@dataclass(frozen=True)
class AIEvidenceRowVM:
    signal_id: str
    headline: str
    source: str
    source_url: str
    excerpt: str
    content_origin: str
    published_at_utc: datetime

    def __post_init__(self) -> None:
        if any(
            not value.strip()
            for value in (
                self.signal_id,
                self.headline,
                self.source,
                self.source_url,
                self.content_origin,
            )
        ):
            raise ValueError("AI evidence projection identity is required")
        _require_utc(self.published_at_utc)


@dataclass(frozen=True)
class MacroVM:
    generation_id: int
    generated_at_utc: datetime
    news_status: Availability
    news_rows: tuple[NewsRowVM, ...]
    news_provider_count: int
    news_reason_codes: tuple[str, ...]
    news_collected_at_utc: datetime | None = None
    calendar_status: Availability = Availability.UNAVAILABLE
    calendar_reason_codes: tuple[str, ...] = ("CALENDAR_NOT_CONFIGURED",)
    ai_status: Availability = Availability.UNAVAILABLE
    ai_model_id: str | None = None
    ai_prompt_version: str | None = None
    ai_scope: str | None = None
    ai_summary: str | None = None
    ai_directional_bias: str | None = None
    ai_event_risk: str | None = None
    ai_confidence: Decimal | None = None
    ai_risk_flags: tuple[str, ...] = ()
    ai_source_signal_ids: tuple[str, ...] = ()
    ai_generated_at_utc: datetime | None = None
    ai_valid_until_utc: datetime | None = None
    ai_reason_codes: tuple[str, ...] = ("AI_NOT_REQUESTED",)
    intelligence_status: Availability = Availability.UNAVAILABLE
    intelligence_events: tuple[IntelligenceEventRowVM, ...] = ()
    intelligence_reason_codes: tuple[str, ...] = ("MARKET_INTELLIGENCE_NOT_COLLECTED",)
    tavily_status: Availability = Availability.UNAVAILABLE
    gdelt_status: Availability = Availability.UNAVAILABLE
    tavily_credits_used: int = 0
    tavily_credits_today: int = 0
    tavily_credits_remaining: int = 900
    tavily_monthly_limit: int = 900
    official_news_count: int = 0
    tavily_news_count: int = 0
    gdelt_news_count: int = 0
    category_counts: tuple[tuple[str, int], ...] = ()
    ai_evidence_rows: tuple[AIEvidenceRowVM, ...] = ()
    ai_estimated_input_tokens: int = 0
    ai_estimated_output_tokens: int = 0
    ai_estimated_cost_usd: float = 0.0
    ai_tavily_extract_credits: int = 0
    ai_preview_source_count: int = 0
    ai_preview_input_tokens: int = 0
    ai_preview_estimated_cost_usd: float = 0.0
    ai_preview_tavily_extract_credits: int = 0

    def __post_init__(self) -> None:
        if self.generation_id < 0 or min(
            self.news_provider_count,
            self.official_news_count,
            self.tavily_news_count,
            self.gdelt_news_count,
        ) < 0:
            raise ValueError("macro projection generation and counts are invalid")
        if min(
            self.tavily_credits_used,
            self.tavily_credits_today,
            self.tavily_credits_remaining,
            self.tavily_monthly_limit,
            self.ai_estimated_input_tokens,
            self.ai_estimated_output_tokens,
            self.ai_estimated_cost_usd,
            self.ai_tavily_extract_credits,
            self.ai_preview_source_count,
            self.ai_preview_input_tokens,
            self.ai_preview_estimated_cost_usd,
            self.ai_preview_tavily_extract_credits,
        ) < 0:
            raise ValueError("market intelligence quota values cannot be negative")
        _require_utc(self.generated_at_utc)
        for timestamp in (
            self.news_collected_at_utc,
            self.ai_generated_at_utc,
            self.ai_valid_until_utc,
        ):
            if timestamp is not None:
                _require_utc(timestamp)
        if self.ai_status is Availability.READY:
            required = (
                self.ai_model_id,
                self.ai_prompt_version,
                self.ai_scope,
                self.ai_summary,
                self.ai_directional_bias,
                self.ai_event_risk,
            )
            if any(value is None or not value.strip() for value in required):
                raise ValueError("available AI projection requires identity and result")
            if (
                self.ai_confidence is None
                or not self.ai_source_signal_ids
                or self.ai_generated_at_utc is None
                or self.ai_valid_until_utc is None
            ):
                raise ValueError("available AI projection requires confidence, sources and TTL")


def empty_macro_projection(generation_id: int, generated_at_utc: datetime) -> MacroVM:
    return MacroVM(
        generation_id=generation_id,
        generated_at_utc=generated_at_utc,
        news_status=Availability.UNAVAILABLE,
        news_rows=(),
        news_provider_count=0,
        news_reason_codes=("NEWS_NOT_COLLECTED",),
    )


def _require_utc(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("macro projection timestamp must use UTC")
