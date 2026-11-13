"""Immutable contracts for traceable, non-executing market intelligence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from trading_ig_assistant.domain.context_sources import (
    ContextCategory,
    ContextImportance,
    NewsItem,
)


class IntelligenceProviderKind(StrEnum):
    OFFICIAL = "official"
    TAVILY = "tavily"
    GDELT = "gdelt"


class PublicationTimeStatus(StrEnum):
    REPORTED = "reported"
    PROVIDER_ESTIMATE = "provider_estimate"
    UNKNOWN = "unknown"


class VerificationStatus(StrEnum):
    OFFICIAL = "official"
    UNCONFIRMED = "unconfirmed"
    SINGLE_SOURCE = "single_source"
    CORROBORATED = "corroborated"


class ArticleContentOrigin(StrEnum):
    SEARCH_SNIPPET = "search_snippet"
    TAVILY_EXTRACT_BASIC = "tavily_extract_basic"
    METADATA_ONLY = "metadata_only"


class IntelligenceCoverageStatus(StrEnum):
    FRESH = "fresh"
    STALE = "stale"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class ResearchTrigger(StrEnum):
    SCHEDULED = "scheduled"
    MARKET_EVENT = "market_event"
    MACRO_EVENT = "macro_event"
    MANUAL = "manual"


class ResearchQuotaStatus(StrEnum):
    AVAILABLE = "available"
    RESERVE_ONLY = "reserve_only"
    EXHAUSTED = "exhausted"


@dataclass(frozen=True)
class ResearchQuotaState:
    month_key: str
    used_credits: int
    daily_credits: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        try:
            datetime.strptime(self.month_key, "%Y-%m")
        except ValueError as exc:
            raise ValueError("quota month key must use YYYY-MM") from exc
        if self.used_credits < 0:
            raise ValueError("quota usage cannot be negative")
        days = tuple(day for day, _credits in self.daily_credits)
        if len(days) != len(set(days)):
            raise ValueError("quota daily entries must be unique")
        for day, credits in self.daily_credits:
            try:
                datetime.strptime(day, "%Y-%m-%d")
            except ValueError as exc:
                raise ValueError("quota day key must use YYYY-MM-DD") from exc
            if not day.startswith(f"{self.month_key}-") or credits < 0:
                raise ValueError("quota daily usage must belong to its month")


@dataclass(frozen=True)
class ResearchQuotaView:
    month_key: str
    used_credits: int
    used_today: int
    planned_budget: int
    hard_limit: int
    remaining_credits: int
    status: ResearchQuotaStatus

    def __post_init__(self) -> None:
        if not 0 <= self.planned_budget <= self.hard_limit:
            raise ValueError("quota planned budget must fit the hard limit")
        if min(self.used_credits, self.used_today, self.remaining_credits) < 0:
            raise ValueError("quota view values cannot be negative")


@dataclass(frozen=True)
class NewsSearchRequest:
    query: str
    category: ContextCategory
    max_results: int = 10
    start_at_utc: datetime | None = None
    end_at_utc: datetime | None = None
    recent_window: timedelta | None = timedelta(hours=24)

    def __post_init__(self) -> None:
        if not self.query.strip() or len(self.query) > 500:
            raise ValueError("news search query must contain at most 500 characters")
        if not 1 <= self.max_results <= 10:
            raise ValueError("news search max_results must be between 1 and 10")
        for value in (self.start_at_utc, self.end_at_utc):
            if value is not None:
                _require_utc(value, "news search boundary")
        if self.start_at_utc and self.end_at_utc and self.end_at_utc <= self.start_at_utc:
            raise ValueError("news search end must follow start")
        if self.recent_window is not None and self.recent_window < timedelta(minutes=15):
            raise ValueError("news search recent window must be at least 15 minutes")
        if (self.start_at_utc or self.end_at_utc) and self.recent_window is not None:
            raise ValueError("news search uses either explicit boundaries or a recent window")


@dataclass(frozen=True)
class ProviderUsage:
    credits: int

    def __post_init__(self) -> None:
        if self.credits < 0:
            raise ValueError("provider credits cannot be negative")


@dataclass(frozen=True)
class IntelligenceNewsRecord:
    news: NewsItem
    provider_id: str
    provider_kind: IntelligenceProviderKind
    publication_time_status: PublicationTimeStatus
    verification_status: VerificationStatus
    relevance_score: float | None = None
    search_excerpt: str | None = None

    def __post_init__(self) -> None:
        if not self.provider_id.strip():
            raise ValueError("intelligence provider identity is required")
        if self.relevance_score is not None and not 0 <= self.relevance_score <= 1:
            raise ValueError("news relevance score must be between 0 and 1")
        if self.search_excerpt is not None:
            normalized = " ".join(self.search_excerpt.split())
            if not normalized or len(normalized) > 4_000:
                raise ValueError("search excerpt must contain at most 4000 characters")
        if self.provider_kind is IntelligenceProviderKind.GDELT:
            if self.verification_status is not VerificationStatus.UNCONFIRMED:
                raise ValueError("GDELT discoveries must remain unconfirmed at ingestion")
        if self.provider_kind is IntelligenceProviderKind.OFFICIAL:
            if self.verification_status is not VerificationStatus.OFFICIAL:
                raise ValueError("official records require official verification status")


@dataclass(frozen=True, repr=False)
class ArticleEvidence:
    """Memory-only article material selected for one advisory AI request."""

    signal_id: str
    headline: str
    source: str
    source_url: str
    provider_id: str
    category: ContextCategory
    verification_status: VerificationStatus
    published_at_utc: datetime
    observed_at_utc: datetime
    valid_until_utc: datetime
    excerpt: str | None
    content_origin: ArticleContentOrigin
    relevance_score: float | None = None

    def __post_init__(self) -> None:
        required = (
            self.signal_id,
            self.headline,
            self.source,
            self.source_url,
            self.provider_id,
        )
        if any(not value.strip() for value in required):
            raise ValueError("article evidence identity is required")
        for value, label in (
            (self.published_at_utc, "article publication"),
            (self.observed_at_utc, "article observation"),
            (self.valid_until_utc, "article validity"),
        ):
            _require_utc(value, label)
        if self.valid_until_utc <= self.observed_at_utc:
            raise ValueError("article evidence validity must follow observation")
        if self.excerpt is not None:
            normalized = " ".join(self.excerpt.split())
            if not normalized or len(normalized) > 12_000:
                raise ValueError("article excerpt must contain at most 12000 characters")
        if self.relevance_score is not None and not 0 <= self.relevance_score <= 1:
            raise ValueError("article evidence relevance must be between 0 and 1")


@dataclass(frozen=True, repr=False)
class ArticleEvidenceBundle:
    """Bounded evidence and transparent pre-call usage estimates."""

    articles: tuple[ArticleEvidence, ...]
    generated_at_utc: datetime
    estimated_input_tokens: int
    estimated_output_tokens: int
    estimated_openai_cost_usd: float
    tavily_extract_credits: int
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_utc(self.generated_at_utc, "article evidence generation")
        if not 1 <= len(self.articles) <= 5:
            raise ValueError("AI article evidence requires between one and five articles")
        if len({article.signal_id for article in self.articles}) != len(self.articles):
            raise ValueError("AI article evidence signal IDs must be unique")
        if min(
            self.estimated_input_tokens,
            self.estimated_output_tokens,
            self.estimated_openai_cost_usd,
            self.tavily_extract_credits,
        ) < 0:
            raise ValueError("AI evidence estimates cannot be negative")


@dataclass(frozen=True)
class IntelligenceProviderResult:
    provider_id: str
    provider_kind: IntelligenceProviderKind
    query: str
    records: tuple[IntelligenceNewsRecord, ...]
    observed_at_utc: datetime
    usage: ProviderUsage | None = None
    request_id: str | None = None

    def __post_init__(self) -> None:
        if not self.provider_id.strip() or not self.query.strip():
            raise ValueError("provider result identity and query are required")
        _require_utc(self.observed_at_utc, "provider result observation")
        if any(record.provider_id != self.provider_id for record in self.records):
            raise ValueError("provider result contains a foreign provider record")
        if any(record.provider_kind is not self.provider_kind for record in self.records):
            raise ValueError("provider result contains a foreign provider kind")
        ids = tuple(record.news.item_id for record in self.records)
        if len(ids) != len(set(ids)):
            raise ValueError("provider result record IDs must be unique")
        if self.request_id is not None and not self.request_id.strip():
            raise ValueError("provider request ID must be non-empty when supplied")


@dataclass(frozen=True)
class MarketIntelligenceEvent:
    event_id: str
    headline: str
    category: ContextCategory
    importance: ContextImportance
    published_at_utc: datetime
    observed_at_utc: datetime
    publication_time_status: PublicationTimeStatus
    verification_status: VerificationStatus
    source_names: tuple[str, ...]
    source_urls: tuple[str, ...]
    provider_ids: tuple[str, ...]
    source_record_ids: tuple[str, ...]
    tags: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.event_id.strip() or not self.headline.strip():
            raise ValueError("market intelligence event identity is required")
        _require_utc(self.published_at_utc, "market intelligence publication")
        _require_utc(self.observed_at_utc, "market intelligence observation")
        if self.published_at_utc > self.observed_at_utc:
            raise ValueError("market intelligence publication cannot follow observation")
        for values, label in (
            (self.source_names, "source names"),
            (self.provider_ids, "provider IDs"),
            (self.source_record_ids, "source record IDs"),
        ):
            _require_unique(values, label, required=True)
        _require_unique(self.source_urls, "source URLs")
        _require_unique(self.tags, "event tags")
        if self.verification_status is VerificationStatus.CORROBORATED:
            if len(self.source_names) < 2:
                raise ValueError("corroboration requires at least two distinct sources")


@dataclass(frozen=True)
class MarketIntelligenceSnapshot:
    generated_at_utc: datetime
    coverage_status: IntelligenceCoverageStatus
    events: tuple[MarketIntelligenceEvent, ...]
    provider_ids: tuple[str, ...]
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_utc(self.generated_at_utc, "market intelligence snapshot")
        _require_unique(self.provider_ids, "snapshot provider IDs")
        _require_unique(self.reason_codes, "snapshot reason codes")
        ids = tuple(event.event_id for event in self.events)
        if len(ids) != len(set(ids)):
            raise ValueError("market intelligence event IDs must be unique")
        if self.coverage_status is IntelligenceCoverageStatus.UNAVAILABLE and self.events:
            raise ValueError("unavailable intelligence snapshot cannot contain events")


def _require_utc(value: datetime, label: str) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"{label} timestamp must use UTC")


def _require_unique(values: tuple[str, ...], label: str, *, required: bool = False) -> None:
    if required and not values:
        raise ValueError(f"{label} are required")
    if any(not value.strip() for value in values) or len(values) != len(set(values)):
        raise ValueError(f"{label} must be non-empty and unique")
