"""Provider-neutral macro/news records and traceable context assessments."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from trading_ig_assistant.domain.macro_context import ContextSeverity


class SourceUsageRights(StrEnum):
    UNKNOWN = "unknown"
    METADATA_ONLY = "metadata_only"
    SUMMARY_ALLOWED = "summary_allowed"


class ContextCategory(StrEnum):
    CENTRAL_BANK = "central_bank"
    INFLATION = "inflation"
    EMPLOYMENT = "employment"
    GROWTH = "growth"
    GEOPOLITICAL = "geopolitical"
    ENERGY = "energy"
    FX = "fx"
    RATES = "rates"
    VOLATILITY = "volatility"
    OTHER = "other"


class ContextImportance(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class ProviderCollectionStatus(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class MacroEvent:
    schema_version: int
    event_id: str
    title: str
    category: ContextCategory
    importance: ContextImportance
    scheduled_at_utc: datetime
    observed_at_utc: datetime
    source: str
    source_url: str | None
    usage_rights: SourceUsageRights
    tags: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_version_and_identity(self.schema_version, self.event_id, self.title, self.source)
        _require_utc(self.scheduled_at_utc, "macro event schedule")
        _require_utc(self.observed_at_utc, "macro event observation")
        _require_metadata(self.title, self.source_url, self.tags)


@dataclass(frozen=True)
class NewsItem:
    schema_version: int
    item_id: str
    headline: str
    summary: str | None
    category: ContextCategory
    importance: ContextImportance
    published_at_utc: datetime
    observed_at_utc: datetime
    source: str
    source_url: str | None
    usage_rights: SourceUsageRights
    tags: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_version_and_identity(self.schema_version, self.item_id, self.headline, self.source)
        _require_utc(self.published_at_utc, "news publication")
        _require_utc(self.observed_at_utc, "news observation")
        if self.published_at_utc > self.observed_at_utc:
            raise ValueError("news publication cannot follow its observation")
        _require_metadata(self.headline, self.source_url, self.tags)
        if self.summary is not None:
            if not self.summary.strip():
                raise ValueError("news summary must be non-empty when supplied")
            if len(self.summary) > 1_000:
                raise ValueError("news summary exceeds the bounded metadata contract")
            if self.usage_rights is not SourceUsageRights.SUMMARY_ALLOWED:
                raise ValueError("news summary requires explicit summary usage rights")


@dataclass(frozen=True)
class NewsCollectionSnapshot:
    schema_version: int
    provider_id: str
    status: ProviderCollectionStatus
    items: tuple[NewsItem, ...]
    collected_at_utc: datetime
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.schema_version <= 0:
            raise ValueError("news collection schema version must be positive")
        if not self.provider_id.strip():
            raise ValueError("news collection provider identity is required")
        _require_utc(self.collected_at_utc, "news collection")
        item_ids = tuple(item.item_id for item in self.items)
        if len(set(item_ids)) != len(item_ids):
            raise ValueError("news collection item IDs must be unique")
        if any(item.observed_at_utc > self.collected_at_utc for item in self.items):
            raise ValueError("news collection cannot contain future observations")
        _require_unique_text(self.reason_codes, "news collection reason codes")
        if self.status is ProviderCollectionStatus.UNAVAILABLE:
            if self.items or not self.reason_codes:
                raise ValueError("unavailable news collection must be empty and explained")


@dataclass(frozen=True)
class CalendarCollectionSnapshot:
    schema_version: int
    provider_id: str
    status: ProviderCollectionStatus
    events: tuple[MacroEvent, ...]
    collected_at_utc: datetime
    window_start_utc: datetime
    window_end_utc: datetime
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.schema_version <= 0:
            raise ValueError("calendar collection schema version must be positive")
        if not self.provider_id.strip():
            raise ValueError("calendar collection provider identity is required")
        _require_utc(self.collected_at_utc, "calendar collection")
        _require_utc(self.window_start_utc, "calendar collection window start")
        _require_utc(self.window_end_utc, "calendar collection window end")
        if self.window_end_utc <= self.window_start_utc:
            raise ValueError("calendar collection window end must follow its start")
        event_ids = tuple(event.event_id for event in self.events)
        if len(set(event_ids)) != len(event_ids):
            raise ValueError("calendar collection event IDs must be unique")
        if any(event.observed_at_utc > self.collected_at_utc for event in self.events):
            raise ValueError("calendar collection cannot contain future observations")
        if any(
            not self.window_start_utc <= event.scheduled_at_utc <= self.window_end_utc
            for event in self.events
        ):
            raise ValueError("calendar collection contains an event outside its window")
        _require_unique_text(self.reason_codes, "calendar collection reason codes")
        if self.status is ProviderCollectionStatus.UNAVAILABLE:
            if self.events or not self.reason_codes:
                raise ValueError("unavailable calendar collection must be empty and explained")


@dataclass(frozen=True)
class MarketContextFlag:
    schema_version: int
    flag_id: str
    label: str
    summary: str
    category: ContextCategory
    severity: ContextSeverity
    score: Decimal | None
    confidence: Decimal | None
    source_record_ids: tuple[str, ...]
    observed_at_utc: datetime
    valid_until_utc: datetime
    tags: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_version_and_identity(self.schema_version, self.flag_id, self.label, self.summary)
        _require_utc(self.observed_at_utc, "context flag observation")
        _require_utc(self.valid_until_utc, "context flag validity")
        if self.valid_until_utc <= self.observed_at_utc:
            raise ValueError("context flag validity must follow observation")
        if self.score is not None and not Decimal("-100") <= self.score <= Decimal("100"):
            raise ValueError("context flag score must be between -100 and 100")
        if self.confidence is not None and not Decimal("0") <= self.confidence <= Decimal("1"):
            raise ValueError("context flag confidence must be between 0 and 1")
        _require_unique_text(
            self.source_record_ids, "context flag source record IDs", required=True
        )
        _require_unique_text(self.tags, "context flag tags")


def _require_version_and_identity(
    schema_version: int,
    record_id: str,
    display_text: str,
    source: str,
) -> None:
    if schema_version <= 0:
        raise ValueError("context source schema version must be positive")
    if not record_id.strip() or not display_text.strip() or not source.strip():
        raise ValueError("context source identity, display text and source are required")


def _require_metadata(text: str, source_url: str | None, tags: tuple[str, ...]) -> None:
    if len(text) > 300:
        raise ValueError("context source display text exceeds the metadata contract")
    if source_url is not None and not source_url.strip():
        raise ValueError("context source URL must be non-empty when supplied")
    _require_unique_text(tags, "context source tags")


def _require_unique_text(values: tuple[str, ...], label: str, *, required: bool = False) -> None:
    if required and not values:
        raise ValueError(f"{label} are required")
    if any(not value.strip() for value in values) or len(set(values)) != len(values):
        raise ValueError(f"{label} must be non-empty and unique")


def _require_utc(value: datetime, label: str) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"{label} timestamp must use UTC")
